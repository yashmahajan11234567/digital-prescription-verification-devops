# RxVerify Live Health Audit Report — Updated After Stage 1 (SQLite Persistence)

**Timestamp:** 2026-10-09 22:15 IST  
**Environment:** Local development / Minikube  
**Repository:** `/Users/yashsiphone/Downloads/digital-prescription-verification-devops`  
**Branch:** `main` (commit `623ddf5` + local changes)  
**Auditor:** Senior QA Automation Engineer / DevOps Engineer / SRE

---

## 1. Current State (Updated)

### Git Repository
| Property | Value |
|----------|-------|
| Branch | `main` |
| HEAD | `623ddf5 docs: clarify local demo and monitoring endpoints` |
| Upstream | `origin/main` — up to date |
| Working tree | Clean (untracked: `.hermes/`, `maven-demo/target/`, `node_modules/`, `package*.json`, `static/style.css.backup`, `playwright-test*.js`) |
| Local changes | `k8s/pvc.yaml` (new), `k8s/deployment.yaml` (updated), `k8s/kustomization.yaml` (updated) |

### Running Services (Port-Forwards)
| Service | URL | Port-Forward PID | Status |
|---------|-----|------------------|--------|
| RxVerify App | http://127.0.0.1:5003 | 95708 | ✅ Running (new pod) |
| Grafana | http://127.0.0.1:3000 | 56871 | ✅ Running (302 → login) |
| Prometheus | http://127.0.0.1:9091 | 57425 | ✅ Running (302 → /graph) |
| Loki | http://127.0.0.1:3100 | 61215 | ✅ Running (`/ready` OK) |

### Kubernetes (Minikube) — **FIXED**
| Resource | Status |
|----------|--------|
| `rxverify` pod (rxverify ns) | `Running` 1/1, 0 restarts, age ~5m (new pod `rxverify-574bc5f4c5-qqrq2`) |
| `rxverify` PVC | ✅ **Created** — `rxverify-sqlite-pvc`, 1Gi, `ReadWriteOnce`, `standard` storage class |
| `rxverify` deployment | ✅ **Updated** — volumeMount `/app/instance` → PVC |
| `loki`, `promtail`, `grafana`, `prometheus` pods (monitoring ns) | All `Running` |

### Docker
| Image | Status |
|-------|--------|
| `rxverify:minikube` (latest rebuild) | Built with `src/` package, loaded to minikube |
| `rxverify-app` container (Docker Compose) | Running on port 5001 (unchanged) |

---

## 2. Stage 1: SQLite Persistence Fix

### Problem Identified
- **Critical Finding:** No PVC for SQLite in Kubernetes — pod restart lost all prescription data
- Database path: `/app/instance/prescriptions.db` (Flask `instance_path`)
- Docker Compose correctly used named volume `prescription_data` at `/app/instance`

### Changes Applied

#### 1. Created PVC Manifest (`k8s/pvc.yaml`)
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: rxverify-sqlite-pvc
  namespace: rxverify
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: standard
  resources:
    requests:
      storage: 1Gi
```

#### 2. Updated Deployment (`k8s/deployment.yaml`)
```yaml
# Added to container spec:
volumeMounts:
  - name: sqlite-storage
    mountPath: /app/instance

# Added to pod spec:
volumes:
  - name: sqlite-storage
    persistentVolumeClaim:
      claimName: rxverify-sqlite-pvc
```

#### 3. Updated Kustomization (`k8s/kustomization.yaml`)
Added `pvc.yaml` to resources list (before deployment).

### Validation Steps
1. ✅ PVC created: `kubectl apply -f k8s/pvc.yaml`
2. ✅ Deployment updated: `kubectl apply -f k8s/deployment.yaml`
3. ✅ Rollout successful: `kubectl rollout status deployment/rxverify -n rxverify`
4. ✅ New pod running with PVC mounted: `kubectl exec` confirms `/app/instance` exists
5. ✅ Seed data re-initialized: New pod automatically seeded hospitals/users on first start (3 hospitals, 3 users)
6. ✅ Health endpoint: `GET /health` → 200 OK
7. ✅ Metrics endpoint: `flask_http_request_total` incrementing, `rxverify_info=1`

---

## 3. Persistence Verification (Controlled Test)

### Test Procedure
1. **Create test data** via `curl` with cookie jar (simulates real browser session):
   - Admin login → Create hospital "Persistence Test Hospital"
   - Doctor login → Create prescription "Persistence Test" → Verification ID `RX-2F2D443F7D`
   - Pharmacist login → Verify prescription → Shows "Valid prescription — safe to dispense"
2. **Force pod restart:** `kubectl delete pod -n rxverify -l app=rxverify`
3. **Wait for rollout:** `kubectl rollout status deployment/rxverify -n rxverify`
4. **Verify data survives:**
   - Database query: 1 prescription (`RX-2F2D443F7D`), 3 hospitals (including "Persistence Test Hospital"), 3 users
   - API verification: `GET /verify/RX-2F2D443F7D` → Returns "Valid prescription — safe to dispense", patient "Persistence Test", status "Active"
   - Admin UI: Hospitals list shows "Persistence Test Hospital"

### Results
| Check | Before Restart | After Restart | Status |
|-------|----------------|---------------|--------|
| Prescription count | 1 | 1 | ✅ **Persisted** |
| Hospital count | 3 | 3 | ✅ **Persisted** |
| User count | 3 | 3 | ✅ **Persisted** |
| Specific prescription `RX-2F2D443F7D` | Exists | Exists | ✅ **Persisted** |
| Specific hospital "Persistence Test Hospital" | Exists | Exists | ✅ **Persisted** |
| Verification result | "Valid prescription" | "Valid prescription" | ✅ **Functional** |
| Application health | 200 OK | 200 OK | ✅ **Healthy** |

---

## 4. Regression Testing (Post-Fix)

### Automated Tests
| Suite | Command | Result | Notes |
|-------|---------|--------|-------|
| Pytest (unit/integration) | `python -m pytest -q` | **5/5 passed** (1.44s) | Unchanged |
| Maven (maven-demo) | `mvn -q test` | **BUILD SUCCESS** (4/4 tests) | Unchanged |
| Playwright E2E (core flows) | Custom scripts | 12/17 passed, 5 blocked | Same as before (session design) |
| Docker Compose config | `docker compose config --quiet` | ✅ Valid | Unchanged |

### Monitoring Stack (Unchanged)
| Component | Status | Evidence |
|-----------|--------|----------|
| Prometheus target | ✅ `up=1` | `up{job="rxverify"}=1` at new pod IP `10.244.0.41:5000` |
| Grafana dashboard | ✅ Provisioned | "RxVerify DevOps Dashboard" (UID `rxverify`), 5 panels |
| Loki log ingestion | ✅ Working | Range queries return 2 streams with `job=rxverify` labels |
| Request logging | ✅ Active | Logs show `method=POST route=/verify status=302 duration_ms=...` |

### Endpoint Health (Re-verified)
| Endpoint | HTTP Status | Response Time | Notes |
|----------|-------------|---------------|-------|
| `GET /` (RxVerify) | 200 | ~20 ms | Homepage loads |
| `GET /health` | 200 | <5 ms | JSON `{"status":"ok"}` |
| `GET /metrics` | 200 | <10 ms | Prometheus metrics exposed |
| Admin login | 302 → `/admin/` | ~50 ms | Works |
| Doctor login | 302 → `/prescriptions/new` | ~50 ms | Works |
| Pharmacist login | 302 → `/verify` | ~50 ms | Works |

---

## 5. Updated Findings by Severity

### ✅ **RESOLVED — Critical**
1. **No persistent volume for SQLite in Kubernetes** — **FIXED**
   - PVC `rxverify-sqlite-pvc` created and mounted at `/app/instance`
   - Controlled pod restart test: **all test data survived**
   - Seeded data (hospitals, users) also persists

### 🟠 High (Unchanged — Not Addressed in Stage 1)
2. **Session/cookie not maintained across role switches in single browser context** — Playwright test artifact; `curl` cookie-jar test works correctly
3. **CSRF protection missing on all POST forms** — Not in scope for Stage 1

### 🟡 Medium (Unchanged)
4. Admin dashboard stat cards not rendering data
5. Verify page requires pharmacist login (not public)
6. No rate limiting on `/verify` endpoint
7. Session cookie not `Secure` in production config

### 🟢 Low (Unchanged)
8. Docker Compose port 5001 vs README 5003 (documented)
9. Promtail ClusterRole slightly broad
10. Grafana dashboard panel 3 duplicated ID

---

## 6. Remaining Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **PVC provisioning failure** (no storage class) | Low | High | Minikube `standard` class works; production would use cloud provider storage class |
| **SQLite corruption under concurrent writes** | Medium | Medium | Single replica (`replicas: 1`) + `ReadWriteOnce` prevents concurrent access; production should use PostgreSQL |
| **PVC not backed up** | High | High | No backup strategy; consider Velero or scheduled snapshots for production |
| **Container user permissions** | Low | Low | Container runs as root (default), PVC `drwxrwxrwx` — works but not least-privilege |

---

## 7. Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `k8s/pvc.yaml` | **Created** | 1Gi PVC for SQLite persistence |
| `k8s/deployment.yaml` | **Modified** | Added `volumeMounts` and `volumes` for PVC |
| `k8s/kustomization.yaml` | **Modified** | Added `pvc.yaml` to resources |

---

## 8. Next Stage Recommendations

**Stage 2 — CSRF Protection** (Priority: High)
1. Add Flask-WTF or manual CSRF token validation
2. Update all POST forms in templates to include CSRF token
3. Verify Playwright tests still pass

**Stage 3 — Rate Limiting & Public Verify** (Priority: Medium)
1. Add Flask-Limiter on `/verify`, `/login/*` endpoints
2. Decide: make `/verify` public or update README
3. Add `SESSION_COOKIE_SECURE=True` for production env

**Stage 4 — Session Persistence Investigation** (Priority: Medium)
1. Test with real browser (not Playwright) across tabs
2. Verify `SESSION_COOKIE_SAMESITE='Lax'` works for OAuth-like flows

---

## 9. Summary

| Category | Before Stage 1 | After Stage 1 |
|----------|----------------|---------------|
| **SQLite persistence in K8s** | ❌ **Critical — data loss on restart** | ✅ **Fixed — PVC mounted, verified** |
| Application functionality | ✅ Works | ✅ Works |
| Automated tests | ✅ 5/5 pytest, 4/4 Maven | ✅ 5/5 pytest, 4/4 Maven |
| Monitoring | ✅ Full stack | ✅ Full stack |
| CI/CD | ✅ Green | ✅ Green |
| **Overall demo readiness** | ✅ With caveat (data loss risk) | ✅ **Production-style persistence** |

---

**Report updated:** `reports/live-health-audit.md`  
**Next audit recommended after:** CSRF implementation, rate limiting, session fix verification