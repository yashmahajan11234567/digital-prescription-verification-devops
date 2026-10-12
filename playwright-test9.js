const { chromium } = require('playwright');

async function runTests() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();
  
  const results = {};
  
  // 1. Test persistence: verify the prescription created before restart
  try {
    await page.goto('http://127.0.0.1:5003/login/pharmacist', { waitUntil: 'networkidle' });
    await page.fill('input[name="email"]', 'pharmacist@rxverify.local');
    await page.fill('input[name="password"]', 'pharmacist123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/verify', { timeout: 5000 });
    
    // Verify with the prescription ID that survived restart
    await page.goto('http://127.0.0.1:5003/verify', { waitUntil: 'networkidle' });
    await page.fill('input[name="verification_id"]', 'RX-2F2D443F7D');
    await page.click('button[type="submit"]');
    await page.waitForLoadState('networkidle');
    const content = await page.content();
    
    results.persistenceVerify = { 
      status: 'ok', 
      url: page.url(),
      hasValidResult: content.includes('Valid') || content.includes('Active') || content.includes('Persistence Test'),
      contentLength: content.length
    };
  } catch (e) {
    results.persistenceVerify = { status: 'failed', error: e.message };
  }
  
  // 2. Verify admin hospital persists
  try {
    await page.goto('http://127.0.0.1:5003/login/admin', { waitUntil: 'networkidle' });
    await page.fill('input[name="email"]', 'admin@rxverify.local');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/admin/', { timeout: 5000 });
    
    await page.goto('http://127.0.0.1:5003/admin/hospitals', { waitUntil: 'networkidle' });
    const content = await page.content();
    
    results.persistenceHospital = { 
      status: 'ok', 
      hasPersistenceHospital: content.includes('Persistence Test Hospital'),
      url: page.url()
    };
  } catch (e) {
    results.persistenceHospital = { status: 'failed', error: e.message };
  }
  
  await browser.close();
  console.log(JSON.stringify({ results }, null, 2));
}

runTests().catch(console.error);
