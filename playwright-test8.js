const { chromium } = require('playwright');

async function runTests() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();
  
  const results = {};
  
  // 1. Admin login and create hospital
  try {
    await page.goto('http://127.0.0.1:5003/login/admin', { waitUntil: 'networkidle' });
    await page.fill('input[name="email"]', 'admin@rxverify.local');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/admin/', { timeout: 5000 });
    
    await page.goto('http://127.0.0.1:5003/admin/hospitals/add', { waitUntil: 'networkidle' });
    await page.fill('input[name="name"]', 'PVC Test Hospital');
    await page.fill('textarea[name="address"]', '789 PVC St');
    await page.fill('input[name="phone"]', '+1-555-0789');
    await page.fill('input[name="email"]', 'pvc@hospital.com');
    await page.click('button[type="submit"]');
    await page.waitForLoadState('networkidle');
    
    results.adminCreateHospital = { status: 'ok', url: page.url() };
  } catch (e) {
    results.adminCreateHospital = { status: 'failed', error: e.message };
  }
  
  // 2. Doctor login and create prescription
  try {
    await page.goto('http://127.0.0.1:5003/login/doctor', { waitUntil: 'networkidle' });
    await page.fill('input[name="email"]', 'doctor@rxverify.local');
    await page.fill('input[name="password"]', 'doctor123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/prescriptions/new', { timeout: 5000 });
    
    await page.goto('http://127.0.0.1:5003/prescriptions/new', { waitUntil: 'networkidle' });
    await page.fill('input[name="patient_name"]', 'PVC Test Patient');
    await page.fill('input[name="patient_reference"]', 'PVC-TEST-001');
    await page.fill('input[name="clinic_name"]', 'PVC Clinic');
    await page.fill('input[name="medicine_name"]', 'PVC Medicine');
    await page.fill('input[name="dosage"]', '50mg');
    await page.fill('textarea[name="instructions"]', 'Test persistence');
    await page.fill('input[name="issue_date"]', '2026-10-09');
    await page.click('button[type="submit"]');
    await page.waitForLoadState('networkidle');
    
    // Get verification ID from prescriptions list
    await page.goto('http://127.0.0.1:5003/prescriptions', { waitUntil: 'networkidle' });
    const verificationId = await page.evaluate(() => {
      const text = document.body.textContent;
      const match = text.match(/RX-[A-Z0-9]{10}/);
      return match ? match[0] : null;
    });
    
    results.doctorCreatePrescription = { status: 'ok', verificationId, url: page.url() };
  } catch (e) {
    results.doctorCreatePrescription = { status: 'failed', error: e.message };
  }
  
  await browser.close();
  console.log(JSON.stringify({ results }, null, 2));
}

runTests().catch(console.error);
