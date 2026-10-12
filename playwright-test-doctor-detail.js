const { chromium } = require('playwright');

async function runTest() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();
  
  const results = {};
  
  try {
    // Admin login
    await page.goto('http://127.0.0.1:5003/login/admin', { waitUntil: 'networkidle' });
    await page.fill('input[name="email"]', 'admin@rxverify.local');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/admin/', { timeout: 5000 });
    
    // Go to hospital detail
    await page.goto('http://127.0.0.1:5003/admin/hospitals/10', { waitUntil: 'networkidle' });
    
    // Click View button for doctor 4
    await page.click('a[href="/admin/hospitals/10/doctors/4"]');
    await page.waitForLoadState('networkidle');
    
    // Check doctor detail page
    const title = await page.title();
    const content = await page.content();
    
    results.doctorDetail = {
      status: 'ok',
      title,
      hasDoctorName: content.includes('Wakubaby'),
      hasHospitalName: content.includes('polo hospital'),
      hasPrescriptionsSection: content.includes('Prescriptions'),
      hasBackLink: content.includes('Back to Hospital'),
      url: page.url()
    };
  } catch (e) {
    results.doctorDetail = { status: 'failed', error: e.message };
  }
  
  await browser.close();
  console.log(JSON.stringify({ results }, null, 2));
}

runTest().catch(console.error);
