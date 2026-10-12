const { chromium } = require('playwright');

async function runTests() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();
  
  const errors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') errors.push(msg.text());
  });
  page.on('pageerror', err => errors.push(err.message));
  
  const results = {};
  
  // 1. Homepage
  try {
    await page.goto('http://127.0.0.1:5003/', { waitUntil: 'networkidle', timeout: 10000 });
    results.homepage = { status: 'ok', title: await page.title() };
  } catch (e) {
    results.homepage = { status: 'failed', error: e.message };
  }
  
  // 2. Doctor login
  try {
    await page.goto('http://127.0.0.1:5003/login/doctor', { waitUntil: 'networkidle' });
    await page.fill('input[name="email"]', 'doctor@rxverify.local');
    await page.fill('input[name="password"]', 'doctor123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/prescriptions/new', { timeout: 5000 });
    results.doctorLogin = { status: 'ok', url: page.url() };
  } catch (e) {
    results.doctorLogin = { status: 'failed', error: e.message };
  }
  
  // 3. Issue prescription - inspect form first
  try {
    await page.goto('http://127.0.0.1:5003/prescriptions/new', { waitUntil: 'networkidle' });
    const formFields = await page.evaluate(() => {
      const inputs = document.querySelectorAll('form input, form select, form textarea');
      return Array.from(inputs).map(i => ({ name: i.name, type: i.type, tag: i.tagName }));
    });
    results.issuePrescriptionForm = { status: 'ok', fields: formFields };
  } catch (e) {
    results.issuePrescriptionForm = { status: 'failed', error: e.message };
  }
  
  // 4. Pharmacist login
  try {
    await page.goto('http://127.0.0.1:5003/login/pharmacist', { waitUntil: 'networkidle' });
    await page.fill('input[name="email"]', 'pharmacist@rxverify.local');
    await page.fill('input[name="password"]', 'pharmacist123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/verify', { timeout: 5000 });
    results.pharmacistLogin = { status: 'ok', url: page.url() };
  } catch (e) {
    results.pharmacistLogin = { status: 'failed', error: e.message };
  }
  
  // 5. Admin login
  try {
    await page.goto('http://127.0.0.1:5003/login/admin', { waitUntil: 'networkidle' });
    await page.fill('input[name="email"]', 'admin@rxverify.local');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/admin/', { timeout: 5000 });
    results.adminLogin = { status: 'ok', url: page.url() };
  } catch (e) {
    results.adminLogin = { status: 'failed', error: e.message };
  }
  
  // 6. Admin dashboard
  try {
    await page.goto('http://127.0.0.1:5003/admin/', { waitUntil: 'networkidle' });
    const content = await page.content();
    results.adminDashboard = { status: 'ok', hasStats: content.includes('Total Hospitals'), hasNav: content.includes('Hospitals') };
  } catch (e) {
    results.adminDashboard = { status: 'failed', error: e.message };
  }
  
  // 7. Admin add hospital
  try {
    await page.goto('http://127.0.0.1:5003/admin/hospitals/add', { waitUntil: 'networkidle' });
    const formFields = await page.evaluate(() => {
      const inputs = document.querySelectorAll('form input, form select, form textarea');
      return Array.from(inputs).map(i => ({ name: i.name, type: i.type, tag: i.tagName }));
    });
    results.adminAddHospital = { status: 'ok', fields: formFields };
  } catch (e) {
    results.adminAddHospital = { status: 'failed', error: e.message };
  }
  
  await browser.close();
  
  console.log(JSON.stringify({ results, errors }, null, 2));
}

runTests().catch(console.error);
