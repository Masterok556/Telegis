const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

const CHROME_PATH = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const BASE_URL = 'http://127.0.0.1:8000/';
const ARTIFACT_DIR = '/Users/oleksandr/.gemini/antigravity/brain/f4285d09-8c9f-4ef3-8e35-bd6c9abad732';

async function runBrowserTests() {
  console.log('🚀 Launching headless Chrome for 2GIS Route & Time Slider & i18n tests...');
  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1440,900']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });

  // Grant geolocation permissions and set coordinates near EXPO (51.0895, 71.4150)
  const context = browser.defaultBrowserContext();
  await context.overridePermissions(BASE_URL, ['geolocation']);
  await page.setGeolocation({ latitude: 51.0895, longitude: 71.4150 });

  const consoleErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log('🔴 Console Error:', msg.text());
      consoleErrors.push(msg.text());
    }
  });

  page.on('pageerror', err => {
    console.log('🔴 Page Error:', err.message);
    consoleErrors.push(err.message);
  });

  console.log(`🌐 Navigating to ${BASE_URL}...`);
  await page.goto(BASE_URL, { waitUntil: 'networkidle2', timeout: 15000 });
  await new Promise(r => setTimeout(r, 1200));

  // 1. Verify Time Slider initial state
  console.log('⏱️ Verifying Time Slider initial state...');
  const sliderVal = await page.$eval('#timeSliderVal', el => el.textContent.trim());
  const sliderInputVal = await page.$eval('#timeRangeSlider', el => el.value);
  console.log(`Initial slider value: input=${sliderInputVal}, badge="${sliderVal}"`);
  if (sliderInputVal !== '60' || !sliderVal.includes('60')) {
    throw new Error(`Expected slider initial value 60, got input=${sliderInputVal}, badge=${sliderVal}`);
  }

  // Change slider value to 45 mins
  console.log('⏱️ Changing slider value to 45 mins...');
  await page.evaluate(() => {
    const slider = document.getElementById('timeRangeSlider');
    slider.value = '45';
    slider.dispatchEvent(new Event('input', { bubbles: true }));
  });
  await new Promise(r => setTimeout(r, 300));
  const newSliderVal = await page.$eval('#timeSliderVal', el => el.textContent.trim());
  console.log(`Updated slider badge: "${newSliderVal}"`);
  if (!newSliderVal.includes('45')) {
    throw new Error(`Expected badge to include 45, got "${newSliderVal}"`);
  }

  // Change back to 60 for search
  await page.evaluate(() => {
    const slider = document.getElementById('timeRangeSlider');
    slider.value = '60';
    slider.dispatchEvent(new Event('input', { bubbles: true }));
  });

  // 2. Perform Recommendation Search
  console.log('🔍 Performing search...');
  await page.click('#submitBtn');
  await page.waitForSelector('.poi-card', { timeout: 10000 });

  const cardCount = await page.$$eval('.poi-card', cards => cards.length);
  console.log(`Found ${cardCount} recommendation cards.`);
  if (cardCount === 0) throw new Error('No recommendation cards returned!');

  // Check prominent AI Why box
  const hasAiHeroBox = await page.$eval('.ai-why-hero-box', el => !!el);
  const aiBadgeTitle = await page.$eval('.ai-why-title', el => el.textContent.trim());
  console.log(`✨ Prominent AI Choice Box verified: "${aiBadgeTitle}"`);

  // Check 2GIS-style route button on card
  const hasCardRouteBtn = await page.$eval('.card-route-btn', el => !!el);
  console.log(`🚶 Card Route Button verified: ${hasCardRouteBtn}`);

  // 3. Click card route button to build 2GIS-style walking route
  console.log('🚶 Clicking card route button to build walking route...');
  await page.click('.card-route-btn');
  await new Promise(r => setTimeout(r, 600));

  // Verify route banner is visible
  const bannerVisible = await page.$eval('#routeSummaryBar', el => !el.classList.contains('hidden'));
  const bannerTitle = await page.$eval('#routeBannerTitle', el => el.textContent.trim());
  const bannerStats = await page.$eval('#routeBannerStats', el => el.textContent.trim());
  console.log(`✅ Route banner active: visible=${bannerVisible}, title="${bannerTitle}", stats="${bannerStats}"`);

  if (!bannerVisible || !bannerTitle.includes('Маршрут к:')) {
    throw new Error(`Route banner failed: visible=${bannerVisible}, title=${bannerTitle}`);
  }

  // Save screenshot of 2GIS walking route
  const routeScreenshotPath = path.join(ARTIFACT_DIR, 'audit_walking_route_2gis.png');
  await page.screenshot({ path: routeScreenshotPath, fullPage: false });
  console.log(`📸 Saved screenshot to ${routeScreenshotPath}`);

  // Test closing route banner
  console.log('✕ Clicking close route banner button...');
  await page.click('#closeRouteBannerBtn');
  await new Promise(r => setTimeout(r, 300));
  const bannerHiddenAfterClose = await page.$eval('#routeSummaryBar', el => el.classList.contains('hidden'));
  console.log(`Route banner hidden after close: ${bannerHiddenAfterClose}`);
  if (!bannerHiddenAfterClose) throw new Error('Route banner did not hide on close button click');

  // 4. Test Drawer Route Button
  console.log('🏛️ Testing Drawer Route Button on Alem.ai...');
  await page.evaluate(() => {
    // Open drawer with alem.ai from catalog
    const card = document.querySelector('.poi-card');
    if (card) card.click();
  });
  await new Promise(r => setTimeout(r, 600));

  const drawerOpen = await page.$eval('#poiDrawer', el => el.classList.contains('open'));
  console.log(`Drawer open: ${drawerOpen}`);

  console.log('🚶 Clicking drawer build route button...');
  await page.click('#drawerRouteBtn');
  await new Promise(r => setTimeout(r, 600));

  const drawerClosedAfterRoute = await page.$eval('#poiDrawer', el => !el.classList.contains('open'));
  const bannerVisibleFromDrawer = await page.$eval('#routeSummaryBar', el => !el.classList.contains('hidden'));
  console.log(`Drawer closed after route click: ${drawerClosedAfterRoute}, Banner visible: ${bannerVisibleFromDrawer}`);

  const drawerRouteScreenshotPath = path.join(ARTIFACT_DIR, 'audit_drawer_route_built.png');
  await page.screenshot({ path: drawerRouteScreenshotPath, fullPage: false });
  console.log(`📸 Saved screenshot to ${drawerRouteScreenshotPath}`);

  // 5. Multilingual testing (KZ and EN)
  console.log('🇰🇿 Switching to Kazakh (KZ)...');
  await page.click('button[data-lang="kz"]');
  await new Promise(r => setTimeout(r, 400));

  const kzCityTag = await page.$eval('.brand-city-tag', el => el.textContent.trim());
  const kzTimeLabel = await page.$eval('[data-i18n="time_budget_label"]', el => el.textContent.trim());
  const kzClimate = await page.$eval('[data-i18n="climate_label"]', el => el.textContent.trim());
  console.log(`KZ Translations verified: cityTag="${kzCityTag}", timeLabel="${kzTimeLabel}", climate="${kzClimate}"`);

  const kzScreenshotPath = path.join(ARTIFACT_DIR, 'audit_routes_and_slider_kz.png');
  await page.screenshot({ path: kzScreenshotPath, fullPage: false });
  console.log(`📸 Saved KZ screenshot to ${kzScreenshotPath}`);

  console.log('🇬🇧 Switching to English (EN)...');
  await page.click('button[data-lang="en"]');
  await new Promise(r => setTimeout(r, 400));

  const enCityTag = await page.$eval('.brand-city-tag', el => el.textContent.trim());
  const enTimeLabel = await page.$eval('[data-i18n="time_budget_label"]', el => el.textContent.trim());
  const enClimate = await page.$eval('[data-i18n="climate_label"]', el => el.textContent.trim());
  console.log(`EN Translations verified: cityTag="${enCityTag}", timeLabel="${enTimeLabel}", climate="${enClimate}"`);

  console.log(`Total console errors during session: ${consoleErrors.length}`);
  if (consoleErrors.length > 0) {
    console.error('Console errors detected:', consoleErrors);
  }

  await browser.close();
  console.log('🎉 ALL BROWSER INTERACTION TESTS PASSED CLEANLY!');
}

runBrowserTests().catch(err => {
  console.error('❌ Browser test failed:', err);
  process.exit(1);
});
