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
  
  // 3. Issue prescription
  try {
    await page.goto('http://127.0.0.1:5003/prescriptions/new', { waitUntil: 'networkidle' });
    await page.fill('input[name="patient_name"]', 'Test Patient');
    await page.fill('input[name="medicine_name"]', 'Test Medicine');
    await page.fill('input[name="dosage"]', '10mg');
    await page.fill('input[name="frequency"]', 'Twice daily');
    await page.fill('input[name="duration_days"]', '7');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/prescriptions', { timeout: 5000 });
    results.issuePrescription = { status: 'ok', url: page.url() };
  } catch (e) {
    results.issuePrescription = { status: 'failed', error: e.message };
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
  
  await browser.close();
  
  console.log(JSON.stringify({ results, errors }, null, 2));
}

runTests().catch(console.error);
