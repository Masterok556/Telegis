const puppeteer = require('puppeteer-core');
const path = require('path');
const CHROME_PATH = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

async function generatePdf() {
  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });
  const fileUrl = 'http://127.0.0.1:8000/presentation/slides.html';
  await page.goto(fileUrl, { waitUntil: 'networkidle2' });
  await new Promise(r => setTimeout(r, 1000));

  await page.pdf({
    path: path.join(__dirname, '../presentation/slides.pdf'),
    format: 'A4',
    landscape: true,
    printBackground: true
  });

  console.log('PDF updated at presentation/slides.pdf');
  await browser.close();
}

generatePdf().catch(err => console.error(err));
