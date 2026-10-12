const { chromium } = require('playwright');

async function runTests() {
  const browser = await chromium.launch({ headless: true });
  
  const results = {};
  const errors = [];
  
  // Test 1: Verify page - check if it requires login
  {
    const context = await browser.newContext();
    const page = await context.newPage();
    page.on('console', msg => { if (msg.type() === 'error') errors.push(`[verify] ${msg.text()}`); });
    
    try {
      await page.goto('http://127.0.0.1:5003/verify', { waitUntil: 'networkidle' });
      const content = await page.content();
      const url = page.url();
      results.verifyPage = { 
        status: 'ok', 
        url, 
        hasForm: content.includes('verification_id'),
        hasLoginRedirect: content.includes('login'),
        title: await page.title()
      };
    } catch (e) {
      results.verifyPage = { status: 'failed', error: e.message };
    }
    await context.close();
  }
  
  // Test 2: Admin hospital creation - check response
  {
    const context = await browser.newContext();
    const page = await context.newPage();
    page.on('console', msg => { if (msg.type() === 'error') errors.push(`[admin2] ${msg.text()}`); });
    
    try {
      await page.goto('http://127.0.0.1:5003/login/admin', { waitUntil: 'networkidle' });
      await page.fill('input[name="email"]', 'admin@rxverify.local');
      await page.fill('input[name="password"]', 'admin123');
      await page.click('button[type="submit"]');
      await page.waitForURL('**/admin/', { timeout: 5000 });
      
      // Add hospital
      await page.goto('http://127.0.0.1:5003/admin/hospitals/add', { waitUntil: 'networkidle' });
      await page.fill('input[name="name"]', 'Test Hospital');
      await page.fill('textarea[name="address"]', '123 Test St, Test City');
      await page.fill('input[name="phone"]', '+1-555-0123');
      await page.fill('input[name="email"]', 'test@hospital.com');
      await page.click('button[type="submit"]');
      await page.waitForLoadState('networkidle');
      const afterSubmitUrl = page.url();
      const afterSubmitContent = await page.content();
      
      // Check hospitals list
      await page.goto('http://127.0.0.1:5003/admin/hospitals', { waitUntil: 'networkidle' });
      const hospitalsContent = await page.content();
      
      results.adminHospitalCreate = { 
        status: 'ok', 
        afterSubmitUrl,
        afterSubmitHasSuccess: afterSubmitContent.includes('success') || afterSubmitContent.includes('created'),
        afterSubmitHasError: afterSubmitContent.includes('error') || afterSubmitContent.includes('Error'),
        hospitalsListHasTest: hospitalsContent.includes('Test Hospital'),
        hospitalsListContent: hospitalsContent.substring(0, 2000)
      };
    } catch (e) {
      results.adminHospitalCreate = { status: 'failed', error: e.message };
    }
    await context.close();
  }
  
  // Test 3: Doctor prescriptions - check for actual prescriptions
  {
    const context = await browser.newContext();
    const page = await context.newPage();
    
    try {
      await page.goto('http://127.0.0.1:5003/login/doctor', { waitUntil: 'networkidle' });
      await page.fill('input[name="email"]', 'doctor@rxverify.local');
      await page.fill('input[name="password"]', 'doctor123');
      await page.click('button[type="submit"]');
      await page.waitForURL('**/prescriptions/new', { timeout: 5000 });
      
      await page.goto('http://127.0.0.1:5003/prescriptions', { waitUntil: 'networkidle' });
      const content = await page.content();
      
      // Check for prescription rows/links
      const prescriptions = await page.evaluate(() => {
        const rows = document.querySelectorAll('table tbody tr, .record-item, [class*="prescription"]');
        return Array.from(rows).map(r => r.textContent.trim().substring(0, 200));
      });
      
      results.doctorPrescriptionsDetail = { 
        status: 'ok', 
        url: page.url(),
        prescriptionCount: prescriptions.length,
        prescriptions
      };
    } catch (e) {
      results.doctorPrescriptionsDetail = { status: 'failed', error: e.message };
    }
    await context.close();
  }
  
  // Test 4: Full verification flow with valid prescription
  {
    const context = await browser.newContext();
    const page = await context.newPage();
    
    try {
      // First create a prescription as doctor
      await page.goto('http://127.0.0.1:5003/login/doctor', { waitUntil: 'networkidle' });
      await page.fill('input[name="email"]', 'doctor@rxverify.local');
      await page.fill('input[name="password"]', 'doctor123');
      await page.click('button[type="submit"]');
      await page.waitForURL('**/prescriptions/new', { timeout: 5000 });
      
      await page.goto('http://127.0.0.1:5003/prescriptions/new', { waitUntil: 'networkidle' });
      await page.fill('input[name="patient_name"]', 'Verify Patient');
      await page.fill('input[name="patient_reference"]', 'VERIFY123');
      await page.fill('input[name="clinic_name"]', 'Verify Clinic');
      await page.fill('input[name="medicine_name"]', 'Verify Medicine');
      await page.fill('input[name="dosage"]', '20mg');
      await page.fill('textarea[name="instructions"]', 'Once daily');
      await page.fill('input[name="issue_date"]', '2026-10-09');
      await page.click('button[type="submit"]');
      await page.waitForLoadState('networkidle');
      
      // Get prescriptions list to find the verification ID
      await page.goto('http://127.0.0.1:5003/prescriptions', { waitUntil: 'networkidle' });
      const prescriptionsContent = await page.content();
      
      // Extract verification ID from the page
      const verificationId = await page.evaluate(() => {
        const text = document.body.textContent;
        const match = text.match(/RX-[A-Z0-9]{10}/);
        return match ? match[0] : null;
      });
      
      results.createAndFindVerification = { 
        status: 'ok', 
        verificationId,
        prescriptionsContent: prescriptionsContent.substring(0, 3000)
      };
    } catch (e) {
      results.createAndFindVerification = { status: 'failed', error: e.message };
    }
    await context.close();
  }
  
  await browser.close();
  
  console.log(JSON.stringify({ results, errors }, null, 2));
}

runTests().catch(console.error);
