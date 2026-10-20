#!/usr/bin/env node
'use strict';

// Local HTML -> PDF. No application server, npm install, or network is required.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { pathToFileURL } = require('node:url');

function chromePath() {
  if (process.env.CHROME_PATH) {
    const supplied = path.resolve(process.env.CHROME_PATH);
    if (!fs.existsSync(supplied)) throw new Error(`CHROME_PATH does not exist: ${supplied}`);
    return supplied;
  }
  const candidates = [
    process.env.PROGRAMFILES && path.join(process.env.PROGRAMFILES, 'Google/Chrome/Application/chrome.exe'),
    process.env['PROGRAMFILES(X86)'] && path.join(process.env['PROGRAMFILES(X86)'], 'Google/Chrome/Application/chrome.exe'),
    process.env.LOCALAPPDATA && path.join(process.env.LOCALAPPDATA, 'Google/Chrome/Application/chrome.exe'),
    process.env.PROGRAMFILES && path.join(process.env.PROGRAMFILES, 'Microsoft/Edge/Application/msedge.exe'),
    process.env['PROGRAMFILES(X86)'] && path.join(process.env['PROGRAMFILES(X86)'], 'Microsoft/Edge/Application/msedge.exe'),
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    '/usr/bin/google-chrome',
    '/usr/bin/google-chrome-stable',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
  ];
  // Playwright's bundled browser can be selected without importing Playwright.
  const cache = process.env.PLAYWRIGHT_BROWSERS_PATH || (process.platform === 'win32'
    ? process.env.LOCALAPPDATA && path.join(process.env.LOCALAPPDATA, 'ms-playwright')
    : path.join(os.homedir(), process.platform === 'darwin' ? 'Library/Caches/ms-playwright' : '.cache/ms-playwright'));
  if (cache && fs.existsSync(cache)) {
    for (const entry of fs.readdirSync(cache).filter(name => /^chromium-\d+$/.test(name)).sort().reverse()) {
      for (const executable of ['chrome-win/chrome.exe', 'chrome-win64/chrome.exe',
        'chrome-linux/chrome', 'chrome-linux64/chrome',
        'chrome-mac/Chromium.app/Contents/MacOS/Chromium']) {
        candidates.push(path.join(cache, entry, executable));
      }
    }
  }
  const found = candidates.find(candidate => candidate && fs.existsSync(candidate));
  if (!found) throw new Error('Chrome/Chromium/Edge not found. Set CHROME_PATH to its executable.');
  return found;
}

function generatePdf() {
  if (process.argv.includes('--help')) {
    console.log('node scripts/generate_slides_pdf.js\nOptional: CHROME_PATH, PDF_OUTPUT. Uses local HTML and print CSS; outputs six slides.\nFor a trusted local deck inside a restricted container only: PDF_CHROME_NO_SANDBOX=1.');
    return;
  }
  if (process.argv.length > 2) throw new Error('Unknown argument. Use --help.');
  const root = path.resolve(__dirname, '..');
  const source = path.join(root, 'presentation/slides.html');
  const output = path.resolve(process.env.PDF_OUTPUT || path.join(root, 'presentation/slides.pdf'));
  const html = fs.readFileSync(source, 'utf8');
  const slides = html.match(/<section\b[^>]*class="slide(?:\s[^"]*)?"/g) || [];
  if (slides.length !== 6) throw new Error(`Expected six source slides, found ${slides.length}.`);
  if (!fs.existsSync(path.dirname(output))) throw new Error('PDF output directory does not exist.');
  const chrome = chromePath();
  const parent = path.resolve(os.tmpdir());
  const scratch = fs.mkdtempSync(path.join(parent, 'telegis-pdf-'));
  try {
    const input = path.join(scratch, 'slides.html');
    const temporaryPdf = path.join(scratch, 'slides.pdf');
    // The deck is self-contained. External font links are omitted for offline
    // rendering; its existing system-font fallback and print design are kept.
    fs.writeFileSync(input, html.replace(/<link\b[^>]*href=["']https?:\/\/[^>]*>/gi, '')
      .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, ''), 'utf8');
    const args = [
      '--headless=new', '--disable-gpu', '--disable-software-rasterizer',
      '--no-first-run', '--no-default-browser-check',
      '--disable-extensions', '--no-pdf-header-footer',
      `--user-data-dir=${path.join(scratch, 'profile')}`,
      `--print-to-pdf=${temporaryPdf}`,
      '--run-all-compositor-stages-before-draw', '--virtual-time-budget=1000',
      pathToFileURL(input).href,
    ];
    // Opt-in only: some container process restrictions prevent Chrome's own
    // sandbox subprocesses from starting. The normal browser is never changed.
    if (process.env.PDF_CHROME_NO_SANDBOX === '1') args.unshift('--no-sandbox');
    const result = spawnSync(chrome, args, { encoding: 'utf8', timeout: 60000, windowsHide: true });
    if (result.error) throw result.error;
    if (result.status !== 0) throw new Error(`Chrome exited ${result.status}: ${(result.stderr || '').slice(-1200)}`);
    if (!fs.existsSync(temporaryPdf)) throw new Error('Chrome did not create a PDF.');
    const bytes = fs.readFileSync(temporaryPdf);
    if (bytes.length < 1000 || bytes.subarray(0, 5).toString() !== '%PDF-') {
      throw new Error('Chrome output is not a valid PDF container.');
    }
    // Preserve the previous delivery if rendering fails before this point.
    fs.copyFileSync(temporaryPdf, output);
    console.log(`PDF exported: ${output}\nBrowser: ${chrome}\nSource slides: ${slides.length}. Render all PDF pages to verify layout.`);
  } finally {
    const resolved = path.resolve(scratch);
    if (path.dirname(resolved) === parent && path.basename(resolved).startsWith('telegis-pdf-')) {
      fs.rmSync(resolved, { recursive: true, force: true, maxRetries: 3, retryDelay: 100 });
    }
  }
}

try {
  generatePdf();
} catch (error) {
  console.error(`PDF export failed: ${error.message}`);
  process.exitCode = 1;
}
