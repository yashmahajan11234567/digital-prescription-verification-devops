const { chromium } = require('playwright');

async function runTests() {
  const browser = await chromium.launch({ headless: true });
  
  const results = {};
  const errors = [];
  
  // Test 1: Doctor flow in isolated context
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
      
      // Issue prescription
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
      
      results.doctorFlow = { status: 'ok', finalUrl: page.url() };
    } catch (e) {
      results.doctorFlow = { status: 'failed', error: e.message, url: page.url() };
    }
    await context.close();
  }
  
  // Test 2: Pharmacist flow in isolated context
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
      
      results.pharmacistFlow = { status: 'ok', finalUrl: page.url() };
    } catch (e) {
      results.pharmacistFlow = { status: 'failed', error: e.message, url: page.url() };
    }
    await context.close();
  }
  
  // Test 3: Admin flow in isolated context
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
      
      // Check dashboard
      await page.goto('http://127.0.0.1:5003/admin/', { waitUntil: 'networkidle' });
      const content = await page.content();
      
      // Check hospitals list
      await page.goto('http://127.0.0.1:5003/admin/hospitals', { waitUntil: 'networkidle' });
      const hospitalsContent = await page.content();
      
      // Check add hospital page
      await page.goto('http://127.0.0.1:5003/admin/hospitals/add', { waitUntil: 'networkidle' });
      const addHospitalContent = await page.content();
      
      results.adminFlow = { 
        status: 'ok', 
        finalUrl: page.url(),
        dashboardHasContent: content.length > 1000,
        hospitalsHasContent: hospitalsContent.length > 1000,
        addHospitalHasForm: addHospitalContent.includes('name')
      };
    } catch (e) {
      results.adminFlow = { status: 'failed', error: e.message, url: page.url() };
    }
    await context.close();
  }
  
  // Test 4: Unauthorized access checks
  {
    const context = await browser.newContext();
    const page = await context.newPage();
    
    try {
      // Try to access admin without login
      await page.goto('http://127.0.0.1:5003/admin/', { waitUntil: 'networkidle' });
      results.unauthorizedAdmin = { status: 'ok', redirectedToLogin: page.url().includes('/login') };
    } catch (e) {
      results.unauthorizedAdmin = { status: 'failed', error: e.message };
    }
    
    try {
      // Try to access doctor page without login
      await page.goto('http://127.0.0.1:5003/prescriptions/new', { waitUntil: 'networkidle' });
      results.unauthorizedDoctor = { status: 'ok', redirectedToLogin: page.url().includes('/login') };
    } catch (e) {
      results.unauthorizedDoctor = { status: 'failed', error: e.message };
    }
    
    await context.close();
  }
  
  // Test 5: Homepage visual check
  {
    const context = await browser.newContext({ viewport: { width: 1280, height: 720 } });
    const page = await context.newPage();
    page.on('console', msg => { if (msg.type() === 'error') errors.push(`[homepage] ${msg.text()}`); });
    
    try {
      await page.goto('http://127.0.0.1:5003/', { waitUntil: 'networkidle' });
      await page.screenshot({ path: '/tmp/homepage-desktop.png', fullPage: true });
      
      // Mobile viewport
      await page.setViewportSize({ width: 375, height: 667 });
      await page.screenshot({ path: '/tmp/homepage-mobile.png', fullPage: true });
      
      const content = await page.content();
      results.homepageVisual = { 
        status: 'ok', 
        title: await page.title(),
        hasHero: content.includes('Secure prescription'),
        hasCTAs: content.includes('Doctor portal') || content.includes('Pharmacist portal'),
        desktopScreenshot: '/tmp/homepage-desktop.png',
        mobileScreenshot: '/tmp/homepage-mobile.png'
      };
    } catch (e) {
      results.homepageVisual = { status: 'failed', error: e.message };
    }
    await context.close();
  }
  
  await browser.close();
  
  console.log(JSON.stringify({ results, errors }, null, 2));
}

runTests().catch(console.error);
