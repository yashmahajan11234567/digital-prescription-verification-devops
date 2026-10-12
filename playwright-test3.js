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
  
  // 1. Pharmacist login - check actual redirect
  try {
    await page.goto('http://127.0.0.1:5003/login/pharmacist', { waitUntil: 'networkidle' });
    await page.fill('input[name="email"]', 'pharmacist@rxverify.local');
    await page.fill('input[name="password"]', 'pharmacist123');
    await page.click('button[type="submit"]');
    await page.waitForLoadState('networkidle');
    results.pharmacistLogin = { status: 'ok', url: page.url() };
  } catch (e) {
    results.pharmacistLogin = { status: 'failed', error: e.message, url: page.url() };
  }
  
  // 2. Issue prescription with correct fields
  try {
    await page.goto('http://127.0.0.1:5003/prescriptions/new', { waitUntil: 'networkidle' });
    await page.fill('input[name="patient_name"]', 'Test Patient');
    await page.fill('input[name="patient_reference"]', 'REF123');
    await page.fill('input[name="doctor_name"]', 'Dr. Test');
    await page.fill('input[name="clinic_name"]', 'Test Clinic');
    await page.fill('input[name="medicine_name"]', 'Test Medicine');
    await page.fill('input[name="dosage"]', '10mg');
    await page.fill('textarea[name="instructions"]', 'Take twice daily');
    await page.fill('input[name="issue_date"]', '2026-10-09');
    await page.click('button[type="submit"]');
    await page.waitForLoadState('networkidle');
    results.issuePrescription = { status: 'ok', url: page.url() };
  } catch (e) {
    results.issuePrescription = { status: 'failed', error: e.message, url: page.url() };
  }
  
  // 3. Test verification flow
  try {
    await page.goto('http://127.0.0.1:5003/verify', { waitUntil: 'networkidle' });
    const formFields = await page.evaluate(() => {
      const inputs = document.querySelectorAll('form input, form select, form textarea');
      return Array.from(inputs).map(i => ({ name: i.name, type: i.type, tag: i.tagName }));
    });
    results.verifyPage = { status: 'ok', fields: formFields };
  } catch (e) {
    results.verifyPage = { status: 'failed', error: e.message };
  }
  
  // 4. Admin dashboard - check stats
  try {
    await page.goto('http://127.0.0.1:5003/admin/', { waitUntil: 'networkidle' });
    const content = await page.content();
    const statCards = await page.evaluate(() => {
      const cards = document.querySelectorAll('.stat-card, [class*="stat"]');
      return Array.from(cards).map(c => c.textContent.trim());
    });
    results.adminDashboard = { status: 'ok', statCards, hasStats: content.includes('Total Hospitals') };
  } catch (e) {
    results.adminDashboard = { status: 'failed', error: e.message };
  }
  
  // 5. Admin hospitals list
  try {
    await page.goto('http://127.0.0.1:5003/admin/hospitals', { waitUntil: 'networkidle' });
    results.adminHospitals = { status: 'ok', url: page.url() };
  } catch (e) {
    results.adminHospitals = { status: 'failed', error: e.message };
  }
  
  // 6. Doctor prescriptions list
  try {
    await page.goto('http://127.0.0.1:5003/prescriptions', { waitUntil: 'networkidle' });
    results.doctorPrescriptions = { status: 'ok', url: page.url() };
  } catch (e) {
    results.doctorPrescriptions = { status: 'failed', error: e.message };
  }
  
  await browser.close();
  
  console.log(JSON.stringify({ results, errors }, null, 2));
}

runTests().catch(console.error);
