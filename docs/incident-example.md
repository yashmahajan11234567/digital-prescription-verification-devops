# Example Incident: RxVerify Health Endpoint Failure

**Date:** 2026-10-09
**Duration:** 12 minutes (13:15 - 13:27 IST)
**Severity:** SEV-2
**Status:** Resolved
**Author:** Yash Mahajan
**Reviewers:** Faculty Reviewer

---

## Executive Summary

**What happened:** RxVerify health endpoint (`/health`) returned HTTP 500 for 12 minutes, causing Kubernetes liveness probes to fail and triggering pod restarts. Prometheus alert `RxVerifyDown` fired, Grafana dashboard showed "DOWN" status.

**Root Cause:** A bad Docker image (`rxverify:broken`) was deployed via `kubectl set image`, which contained a syntax error in `app.py` causing Flask to fail on startup.

**Resolution:** Rolled back deployment using `kubectl rollout undo deployment/rxverify -n rxverify`, restoring the previous working image (`rxverify:minikube`).

**Impact:** 100% of health checks failed for 12 minutes. Application was unavailable (pods restarting). No prescriptions could be issued or verified during this window.

---

## Timeline (UTC)

| Time (UTC) | Event | Notes |
|------------|-------|-------|
| 07:45 | Deployment | `kubectl set image deployment/rxverify rxverify=rxverify:broken -n rxverify` executed for demo |
| 07:45 | Rollout Starts | New ReplicaSet created, pods begin starting |
| 07:46 | Liveness Probe Fails | New pods fail `/health` check, Kubernetes kills them |
| 07:47 | Prometheus Alert Fires | `RxVerifyDown` alert triggers (up{job="rxverify"} == 0) |
| 07:47 | Grafana Dashboard | Shows "DOWN" status for RxVerify |
| 07:48 | Detection | Observed alert in Prometheus, dashboard in Grafana |
| 07:49 | Triage | Checked pod logs: `ModuleNotFoundError` / syntax error in app.py |
| 07:50 | Decision | Roll back to previous version |
| 07:50 | Mitigation | `kubectl rollout undo deployment/rxverify -n rxverify` |
| 07:52 | Rollback Complete | Old ReplicaSet scaled up, new pods pass health checks |
| 07:57 | Resolution | All pods healthy, health endpoint returning 200, alerts clear |

---

## Root Cause Analysis

### What happened technically?
The `rxverify:broken` image was built from a version of `app.py` with a syntax error (missing import). When the new pods started, Flask failed to import the app module, causing the `/health` endpoint to return 500. Kubernetes liveness probe detected this and restarted the pods repeatedly (CrashLoopBackOff).

### Why did it happen? (5 Whys)
1. **Why did the health endpoint return 500?** Flask app failed to start due to import error.
2. **Why did Flask fail to start?** `app.py` had a syntax error (missing `PrometheusMetrics` import).
3. **Why was there a syntax error?** The `rxverify:broken` image was built from broken code intentionally for the demo.
4. **Why was broken code deployed?** It was a deliberate deployment of a known-bad image to demonstrate rollback.
5. **Why demonstrate with a known-bad image?** To show the rollback capability for the faculty presentation.

### Contributing Factors
- No pre-deployment validation (image not tested before deploy)
- No canary/blue-green deployment to catch bad releases early
- Liveness probe correctly detected failure but couldn't prevent rollout

---

## What Went Well
- Kubernetes liveness/readiness probes correctly detected unhealthy pods
- Prometheus alerting fired immediately (< 1 minute)
- Grafana dashboard provided instant visibility
- `kubectl rollout undo` worked flawlessly, restoring service in ~2 minutes
- Zero data loss (SQLite persisted in PVC)

## What Could Be Improved
- Add pre-deployment smoke test in CI/CD (run container locally, hit /health)
- Implement canary deployment for production
- Add automated rollback on metric degradation (e.g., Argo Rollouts)
- Improve alert routing to on-call (currently just dashboard)

---

## Action Items (Preventive)

| # | Action | Owner | Due Date | Ticket/Link |
|---|--------|-------|----------|-------------|
| 1 | Add Docker image smoke test in GitHub Actions (run container, curl /health) | Yash | 2026-10-16 | - |
| 2 | Document canary deployment procedure for Minikube | Yash | 2026-10-16 | - |
| 3 | Add PrometheusRule for automated rollback alert | Yash | 2026-10-16 | - |

---

## Supporting Evidence
- **Grafana Dashboard:** http://localhost:3000/d/rxverify/rxverify-devops-dashboard (snapshot at 07:47)
- **Prometheus Alerts:** `RxVerifyDown` firing 07:47-07:57
- **Logs:** `kubectl -n rxverify logs rxverify-<pod> --previous` shows `ModuleNotFoundError`
- **Deployment History:** `kubectl -n rxverify rollout history deployment/rxverify`
- **Rollback Command:** `kubectl -n rxverify rollout undo deployment/rxverify`

---

## Appendix
- Related incidents: None (first incident)
- Architecture diagram: See `README.md`
- Runbook followed: [Incident Runbook](./incident-runbook.md)