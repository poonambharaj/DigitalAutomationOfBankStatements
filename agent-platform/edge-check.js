const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    headless: false,
    channel: 'msedge'
  });

  const page = await browser.newPage();
  await page.goto('https://app-web.statementrec.com/app/index#allreports', {
    waitUntil: 'networkidle'
  });

  console.log('Title:', await page.title());
  console.log('Digital report visible:', await page.locator('text=Digital (Not Auto-Processed)').isVisible().catch(() => false));

  await browser.close();
})();