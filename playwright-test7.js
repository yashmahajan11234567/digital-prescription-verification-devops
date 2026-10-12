const { chromium } = require('playwright');

async function runTests() {
  const browser = await chromium.launch({ headless: true });
  
  const results = {};
  const errors = [];
  
  // Single context to maintain session cookies
  const context = await browser.newContext();
  const page = await context.newPage();
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));
  
  // 1. Admin login and full flow
  try {
    await page.goto('http://127.0.0.1:5003/login/admin', { waitUntil: 'networkidle' });
    await page.fill('input[name="email"]', 'admin@rxverify.local');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/admin/', { timeout: 5000 });
    results.adminLogin = { status: 'ok', url: page.url() };
    
    // 2. Admin dashboard
    await page.goto('http://127.0.0.1:5003/admin/', { waitUntil: 'networkidle' });
    const dashContent = await page.content();
    results.adminDashboard = { status: 'ok', hasStats: dashContent.includes('Total Hospitals'), url: page.url() };
    
    // 3. Admin hospitals list
    await page.goto('http://127.0.0.1:5003/admin/hospitals', { waitUntil: 'networkidle' });
    const hospitalsContent = await page.content();
    results.adminHospitalsList = { status: 'ok', hasTable: hospitalsContent.includes('table'), url: page.url() };
    
    // 4. Add hospital
    await page.goto('http://127.0.0.1:5003/admin/hospitals/add', { waitUntil: 'networkidle' });
    await page.fill('input[name="name"]', 'Test Hospital Playwright');
    await page.fill('textarea[name="address"]', '456 Playwright Ave, Test City');
    await page.fill('input[name="phone"]', '+1-555-0456');
    await page.fill('input[name="email"]', 'playwright@hospital.com');
    await page.click('button[type="submit"]');
    await page.waitForLoadState('networkidle');
    results.adminAddHospital = { status: 'ok', url: page.url(), content: page.url() };
    
    // 5. Check hospitals list again
    await page.goto('http://127.0.0.1:5003/admin/hospitals', { waitUntil: 'networkidle' });
    const hospitalsContent2 = await page.content();
    results.adminHospitalsList2 = { status: 'ok', hasTestHospital: hospitalsContent2.includes('Test Hospital Playwright'), url: page.url() };
    
  } catch (e) {
    results.adminFlow = { status: 'failed', error: e.message, url: page.url() };
  }
  
  // 6. Doctor login and flow
  try {
    await page.goto('http://127.0.0.1:5003/login/doctor', { waitUntil: 'networkidle' });
    await page.fill('input[name="email"]', 'doctor@rxverify.local');
    await page.fill('input[name="password"]', 'doctor123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/prescriptions/new', { timeout: 5000 });
    results.doctorLogin = { status: 'ok', url: page.url() };
    
    // 7. Issue prescription
    await page.goto('http://127.0.0.1:5003/prescriptions/new', { waitUntil: 'networkidle' });
    await page.fill('input[name="patient_name"]', 'PW Test Patient');
    await page.fill('input[name="patient_reference"]', 'PW123');
    await page.fill('input[name="clinic_name"]', 'PW Clinic');
    await page.fill('input[name="medicine_name"]', 'PW Medicine');
    await page.fill('input[name="dosage"]', '30mg');
    await page.fill('textarea[name="instructions"]', 'Three times daily');
    await page.fill('input[name="issue_date"]', '2026-10-09');
    await page.click('button[type="submit"]');
    await page.waitForLoadState('networkidle');
    results.doctorIssue = { status: 'ok', url: page.url() };
    
    // 8. Doctor prescriptions list
    await page.goto('http://127.0.0.1:5003/prescriptions', { waitUntil: 'networkidle' });
    const docPrescContent = await page.content();
    
    // Extract verification ID
    const verificationId = await page.evaluate(() => {
      const text = document.body.textContent;
      const match = text.match(/RX-[A-Z0-9]{10}/);
      return match ? match[0] : null;
    });
    
    results.doctorPrescriptions = { status: 'ok', url: page.url(), verificationId, contentLength: docPrescContent.length };
    
    // 9. Pharmacist login
    await page.goto('http://127.0.0.1:5003/login/pharmacist', { waitUntil: 'networkidle' });
    await page.fill('input[name="email"]', 'pharmacist@rxverify.local');
    await page.fill('input[name="password"]', 'pharmacist123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/verify', { timeout: 5000 });
    results.pharmacistLogin = { status: 'ok', url: page.url() };
    
    // 10. Verify with valid ID
    if (verificationId) {
      await page.goto('http://127.0.0.1:5003/verify', { waitUntil: 'networkidle' });
      await page.fill('input[name="verification_id"]', verificationId);
      await page.click('button[type="submit"]');
      await page.waitForLoadState('networkidle');
      const verifyContent = await page.content();
      results.pharmacistVerify = { status: 'ok', url: page.url(), hasValidResult: verifyContent.includes('Valid') || verifyContent.includes('Active') };
    } else {
      results.pharmacistVerify = { status: 'skipped', reason: 'No verification ID found' };
    }
    
  } catch (e) {
    results.doctorPharmacistFlow = { status: 'failed', error: e.message, url: page.url() };
  }
  
  await browser.close();
  
  console.log(JSON.stringify({ results, errors }, null, 2));
}

runTests().catch(console.error);
