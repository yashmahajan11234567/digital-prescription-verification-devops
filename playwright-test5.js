const { chromium } = require('playwright');

async function runTests() {
  const browser = await chromium.launch({ headless: true });
  
  const results = {};
  const errors = [];
  
  // Test 1: Doctor flow - correct fields (doctor_name is readonly)
  {
    const context = await browser.newContext();
    const page = await context.newPage();
    page.on('console', msg => { if (msg.type() === 'error') errors.push(`[doctor] ${msg.text()}`); });
    page.on('pageerror', err => errors.push(`[doctor] ${err.message}`));
    
    try {
      await page.goto('http://127.0.0.1:5003/login/doctor', { waitUntil: 'networkidle' });
      await page.fill('input[name="email"]', 'doctor@rxverify.local');
      await page.fill('input[name="password"]', 'doctor123');
      await page.click('button[type="submit"]');
      await page.waitForURL('**/prescriptions/new', { timeout: 5000 });
      
      // Issue prescription - doctor_name is readonly, pre-filled
      await page.goto('http://127.0.0.1:5003/prescriptions/new', { waitUntil: 'networkidle' });
      await page.fill('input[name="patient_name"]', 'Test Patient');
      await page.fill('input[name="patient_reference"]', 'REF123');
      await page.fill('input[name="clinic_name"]', 'Test Clinic');
      await page.fill('input[name="medicine_name"]', 'Test Medicine');
      await page.fill('input[name="dosage"]', '10mg');
      await page.fill('textarea[name="instructions"]', 'Take twice daily');
      await page.fill('input[name="issue_date"]', '2026-10-09');
      await page.click('button[type="submit"]');
      await page.waitForLoadState('networkidle');
      
      results.doctorFlow = { status: 'ok', finalUrl: page.url() };
    } catch (e) {
      results.doctorFlow = { status: 'failed', error: e.message, url: page.url() };
    }
    await context.close();
  }
  
  // Test 2: Pharmacist verification flow
  {
    const context = await browser.newContext();
    const page = await context.newPage();
    page.on('console', msg => { if (msg.type() === 'error') errors.push(`[pharmacist] ${msg.text()}`); });
    page.on('pageerror', err => errors.push(`[pharmacist] ${err.message}`));
    
    try {
      await page.goto('http://127.0.0.1:5003/login/pharmacist', { waitUntil: 'networkidle' });
      await page.fill('input[name="email"]', 'pharmacist@rxverify.local');
      await page.fill('input[name="password"]', 'pharmacist123');
      await page.click('button[type="submit"]');
      await page.waitForURL('**/verify', { timeout: 5000 });
      
      // Get a valid prescription ID from the database via API or create one first
      // For now, test invalid/nonexistent verification
      await page.goto('http://127.0.0.1:5003/verify', { waitUntil: 'networkidle' });
      await page.fill('input[name="verification_id"]', 'RX-INVALID123');
      await page.click('button[type="submit"]');
      await page.waitForLoadState('networkidle');
      
      results.pharmacistVerifyInvalid = { status: 'ok', finalUrl: page.url() };
    } catch (e) {
      results.pharmacistVerifyInvalid = { status: 'failed', error: e.message, url: page.url() };
    }
    await context.close();
  }
  
  // Test 3: Admin full CRUD
  {
    const context = await browser.newContext();
    const page = await context.newPage();
    page.on('console', msg => { if (msg.type() === 'error') errors.push(`[admin] ${msg.text()}`); });
    page.on('pageerror', err => errors.push(`[admin] ${err.message}`));
    
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
      
      // Verify hospital appears in list
      await page.goto('http://127.0.0.1:5003/admin/hospitals', { waitUntil: 'networkidle' });
      const hospitalsContent = await page.content();
      
      results.adminFlow = { 
        status: 'ok', 
        finalUrl: page.url(),
        hospitalsListHasTest: hospitalsContent.includes('Test Hospital')
      };
    } catch (e) {
      results.adminFlow = { status: 'failed', error: e.message, url: page.url() };
    }
    await context.close();
  }
  
  // Test 4: Verification page result view (need valid ID)
  {
    const context = await browser.newContext();
    const page = await context.newPage();
    
    try {
      await page.goto('http://127.0.0.1:5003/verify', { waitUntil: 'networkidle' });
      const content = await page.content();
      results.verifyPageContent = { status: 'ok', hasForm: content.includes('verification_id') };
    } catch (e) {
      results.verifyPageContent = { status: 'failed', error: e.message };
    }
    await context.close();
  }
  
  // Test 5: Doctor prescriptions list
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
      results.doctorPrescriptions = { status: 'ok', url: page.url(), hasContent: content.length > 1000 };
    } catch (e) {
      results.doctorPrescriptions = { status: 'failed', error: e.message };
    }
    await context.close();
  }
  
  // Test 6: Logout flows
  {
    const context = await browser.newContext();
    const page = await context.newPage();
    
    try {
      await page.goto('http://127.0.0.1:5003/login/admin', { waitUntil: 'networkidle' });
      await page.fill('input[name="email"]', 'admin@rxverify.local');
      await page.fill('input[name="password"]', 'admin123');
      await page.click('button[type="submit"]');
      await page.waitForURL('**/admin/', { timeout: 5000 });
      
      // Find and click logout
      const logoutLink = await page.$('a[href*="logout"], button[name="logout"], form[action*="logout"]');
      if (logoutLink) {
        await logoutLink.click();
        await page.waitForLoadState('networkidle');
        results.adminLogout = { status: 'ok', finalUrl: page.url() };
      } else {
        results.adminLogout = { status: 'skipped', reason: 'No logout control found' };
      }
    } catch (e) {
      results.adminLogout = { status: 'failed', error: e.message };
    }
    await context.close();
  }
  
  await browser.close();
  
  console.log(JSON.stringify({ results, errors }, null, 2));
}

runTests().catch(console.error);
