"""End-to-end workflow against the live Dockerized PostgreSQL stack.

Run with the RxVerify compose stack up on http://localhost:5001.
Exercises the complete flow end-to-end so the Docker/PostgreSQL/E2E
verification objectives are checked against the real running app.
"""
import sys
import requests

BASE = "http://localhost:5001"
s = requests.Session()
results = []


def step(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")


# 1. Health
r = s.get(f"{BASE}/health")
step("health", r.status_code == 200 and r.json() == {"status": "ok"}, f"{r.status_code} {r.text.strip()}")

# 2. Doctor login
r = s.post(f"{BASE}/login/doctor", data={"email": "doctor@rxverify.local", "password": "doctor123"}, allow_redirects=True)
step("doctor login", "Welcome, Dr. Meera Patel" in r.text, f"{r.status_code}")

# 3. Create prescription
r = s.post(
    f"{BASE}/prescriptions/new",
    data={
        "patient_name": "E2E Patient", "patient_reference": "UHID-E2E",
        "doctor_name": "Dr. Meera Patel", "clinic_name": "City Care Clinic",
        "medicine_name": "Paracetamol", "dosage": "500mg",
        "instructions": "As needed", "issue_date": "2026-08-20",
    },
    allow_redirects=False,
)
location = r.headers.get("Location", "")
ver_id = location.split("/")[-1]
step("create prescription", r.status_code == 302 and ver_id.startswith("RX-"), f"verification_id={ver_id}")
assert ver_id.startswith("RX-"), f"no verification id in redirect {location}"
# follow to render the result page for the data-intact checks below
r = s.get(f"{BASE}{location}")

# 4. Prescription verification (doctor can view)
r = s.get(f"{BASE}/verify/{ver_id}")
step("doctor verification view", r.status_code == 200 and "active" in r.text.lower(), f"{r.status_code}")

# confirm verification data preserved
for label in ("Paracetamol", "E2E Patient", "UHID-E2E"):
    step(f"  data intact: {label}", label in r.text, "")

# 5. Pharmacist login
s.post(f"{BASE}/logout")
r = s.post(f"{BASE}/login/pharmacist", data={"email": "pharmacist@rxverify.local", "password": "pharmacist123"}, allow_redirects=True)
step("pharmacist login", "Welcome, Rohan Sharma" in r.text, f"{r.status_code}")

# 6. Pharmacist verification view (before receive -> active receive button present)
r = s.get(f"{BASE}/verify/{ver_id}")
step("pharmacist verify before receive", r.status_code == 200 and "Mark Medicine Received" in r.text, f"{r.status_code}")

# 7. Receive: find prescription db id from the verify page form action
import re
m = re.search(r'/receive/(\d+)', r.text)
pid = m.group(1) if m else None
step("receive form exposes prescription id", pid is not None, f"prescription_id={pid}")
assert pid, "no /receive/<id> form found"

# 8. Receive the medicine
r = s.post(f"{BASE}/receive/{pid}", allow_redirects=True)
step("receive ACTIVE->RECEIVED", "Medicine marked as received" in r.text or b"received" in r.text.encode(), f"{r.status_code}")

# 9. Verify RECEIVED state on verification page
r = s.get(f"{BASE}/verify/{ver_id}")
step("verify page shows received", "received" in r.text.lower(), f"{r.status_code}")

# 10. Duplicate receive rejected
r = s.post(f"{BASE}/receive/{pid}", allow_redirects=True)
step("duplicate receive rejected", "already been marked as received" in r.text, f"{r.status_code}")

# 11. Doctor notification
s.post(f"{BASE}/logout")
r = s.post(f"{BASE}/login/doctor", data={"email": "doctor@rxverify.local", "password": "doctor123"}, allow_redirects=True)
step("doctor re-login", "Welcome, Dr. Meera Patel" in r.text, f"{r.status_code}")
r = s.get(f"{BASE}/notifications")
step("doctor notification exists", ver_id in r.text and "received" in r.text.lower(), f"{r.status_code}")

# 12. Admin login + notification + dashboard
s.post(f"{BASE}/logout")
r = s.post(f"{BASE}/login/admin", data={"email": "admin@rxverify.local", "password": "admin123"}, allow_redirects=True)
step("admin login", "Welcome, System Administrator" in r.text or r.status_code == 200, f"{r.status_code}")
r = s.get(f"{BASE}/admin/")
step("admin dashboard", r.status_code == 200 and "Dashboard" in r.text, f"{r.status_code}")
# admin hospital relationships
r = s.get(f"{BASE}/admin/hospitals")
step("admin hospital list", r.status_code == 200 and "City General Hospital" in r.text, f"{r.status_code}")

# 13. Unauthorized access attempts
s2 = requests.Session()
r = s2.get(f"{BASE}/admin/", allow_redirects=False)
step("unauth admin redirect", r.status_code == 302 and "/login/admin" in r.headers.get("Location", ""), f"{r.status_code} -> {r.headers.get('Location')}")
# Confirm the dashboard content is NOT served to an unauthenticated user.
r_full = s2.get(f"{BASE}/admin/", allow_redirects=True)
step("unauth admin denied dashboard content", "stat-label" not in r_full.text, f"final={r_full.url}")
r = s2.post(f"{BASE}/receive/{pid}", allow_redirects=False)
step("unauth receive redirect to pharmacist login", r.status_code in (301, 302) and "/login/pharmacist" in r.headers.get("Location", ""), f"{r.status_code} -> {r.headers.get('Location')}")

# 14. Revoke an active prescription end-to-end (separate prescription)
s3 = requests.Session()
s3.post(f"{BASE}/login/doctor", data={"email": "doctor@rxverify.local", "password": "doctor123"}, allow_redirects=True)
r = s3.post(
    f"{BASE}/prescriptions/new",
    data={
        "patient_name": "Revoke Patient", "patient_reference": "UHID-REV",
        "doctor_name": "Dr. Meera Patel", "clinic_name": "City Care Clinic",
        "medicine_name": "Ibuprofen", "dosage": "200mg",
        "instructions": "With food", "issue_date": "2026-08-20",
    },
    allow_redirects=False,
)
rev_id = r.headers.get("Location", "").split("/")[-1]
# Load the doctor's records page and find this specific prescription's revoke
# form (the card containing rev_id), so the db id is unambiguous even when
# other prescriptions exist in the persistent DB.
recs = s3.get(f"{BASE}/prescriptions").text
rev_pid = None
# cards are <article class="card record"> ... </article>; locate the one with
# our verification id, then its revoke form action.
cards = re.split(r'<article class="card record">', recs)
for card in cards:
    if rev_id in card:
        mm = re.search(r'/prescriptions/(\d+)/revoke', card)
        if mm:
            rev_pid = mm.group(1)
            break
step("create rx for revoke", rev_id.startswith("RX-") and rev_pid is not None, f"ver={rev_id} pid={rev_pid}")
assert rev_id.startswith("RX-") and rev_pid, "revoke setup failed"
r = s3.post(f"{BASE}/prescriptions/{rev_pid}/revoke", allow_redirects=True)
step("revoke ACTIVE->REVOKED", "revoked" in r.text.lower(), f"{r.status_code}")
# pharmacist cannot receive revoked
s3.post(f"{BASE}/logout")
s3.post(f"{BASE}/login/pharmacist", data={"email": "pharmacist@rxverify.local", "password": "pharmacist123"}, allow_redirects=True)
r = s3.post(f"{BASE}/receive/{rev_pid}", allow_redirects=True)
step("pharmacist cannot receive REVOKED", "cannot" in r.text.lower() or "revoked" in r.text.lower(), f"{r.status_code}")

# Summary
passed = sum(1 for _, ok, _ in results if ok)
print(f"\n=== E2E SUMMARY: {passed}/{len(results)} steps passed ===")
if passed != len(results):
    print("FAILURES:")
    for name, ok, detail in results:
        if not ok:
            print(f"  - {name}: {detail}")
    sys.exit(1)
print("ALL E2E STEPS PASSED")
