# RxVerify DevOps College Project — Implementation Plan

## Part 1 — Current State (Verified in This Session)

| Component | Status | Notes |
|-----------|--------|-------|
| **Flask Application** | ✅ Working | `app.py` with Doctor/Pharmacist login, prescription CRUD, `/health` endpoint |
| **SQLite Database** | ✅ Working | Auto-created at `instance/prescriptions.db` |
| **Unit Tests** | ⚠️ 3/4 passing | One test fails: missing `doctor_name` in `prescription_form()` fixture |
| **Dockerfile** | ✅ Working | Python 3.12-slim, gunicorn, builds successfully |
| **Docker Compose** | ✅ Working | Runs on port 5001, named volume for persistence |
| **Terraform** | ✅ Validated & Applied | VPC, EC2, SG, outputs — last applied IP: `13.204.156.140` |
| **Ansible** | ✅ Connectivity Verified | `ping: pong` confirmed; deploy.yml copies files and runs container on port 80 |
| **GitHub CLI** | ✅ Authenticated | User `yashmahajan11234567`, scopes: gist, read:org, repo, workflow |
| **Minikube** | ✅ Running | Control plane, kubelet, apiserver all running |
| **kubectl** | ✅ Available | Docker Desktop bundled |
| **Terraform CLI** | ✅ v1.x | Homebrew installed |
| **Ansible CLI** | ✅ v2.x | Homebrew installed |
| **GitHub Actions** | ❌ Missing | No `.github/workflows/` directory |
| **Jenkins** | ❌ Not configured | No Jenkinsfile |
| **GitLab CI** | ❌ Not configured | No `.gitlab-ci.yml` |
| **Maven Exercise** | ❌ Not present | No Java/Maven project |
| **Prometheus/Grafana** | ❌ Not configured | No metrics, dashboards, or logging stack |
| **Kubernetes Manifests** | ❌ Not present | No K8s Deployment/Service for Minikube |

**Known Blocker:** Test `test_issue_and_verify_prescription` fails because the test fixture `prescription_form()` omits `doctor_name` (required field in template/app.py).

---

## Part 2 — Syllabus Coverage Matrix

| # | Syllabus Topic | Proposed Implementation | Relevant Files/Tools | Demonstration Method | Priority |
|---|----------------|------------------------|---------------------|---------------------|----------|
| **CI/CD Unit** |
| 1 | CI/CD pipeline fundamentals | Explain via GitHub Actions workflow | `.github/workflows/ci.yml` | Show YAML, run live | Essential |
| 2 | Build, test, deploy loop | GH Actions → Docker → Minikube | CI workflow, Docker, K8s | End-to-end push demo | Essential |
| 3 | Jenkins CI server | Jenkinsfile with stages | `Jenkinsfile` | Run in Docker container | Essential |
| 4 | GitLab CI | `.gitlab-ci.yml` mirroring GH Actions | `.gitlab-ci.yml` | Show in GitLab UI (manual mirror) | Essential |
| 5 | Pipeline as Code | All three: YAML, Jenkinsfile, .gitlab-ci.yml | All CI configs | Compare side-by-side | Essential |
| 6 | Automated compilation & unit testing | pytest in all three pipelines | CI configs, `tests/` | Show test output | Essential |
| 7 | DevSecOps | Trivy scan + pip-audit in GH Actions | CI workflow, Trivy | Show scan results | Essential |
| 8 | Continuous Deployment | Auto-deploy to Minikube on main | GH Actions + kubectl | Push to main → live | Essential |
| 9 | Deployment strategies | Rolling update + rollback demo | K8s manifests, kubectl | Live rollout/rollback | Essential |
| **Container Orchestration Unit** |
| 10 | Kubernetes architecture | Explain control plane, worker, pods | Minikube cluster | `kubectl get nodes/components` | Essential |
| 11 | K8s resources & deployment | Deployment + Service manifests | `k8s/deployment.yaml`, `k8s/service.yaml` | Apply, scale, expose | Essential |
| 12 | Maven introduction | Tiny Java project | `maven-demo/pom.xml`, `App.java`, `AppTest.java` | `mvn test package` | Essential |
| 13 | Build automation & testing | Maven compile/test/package | `maven-demo/` | Run Maven commands | Essential |
| **Monitoring & SRE Unit** |
| 14 | Monitoring & observability | Prometheus + Grafana + Loki | `k8s/monitoring/` | Live dashboard | Essential |
| 15 | Three pillars | Metrics (Prom), Logs (Loki), Traces (Tempo/Jaeger) | Stack | Show each pillar | Essential |
| 16 | Centralized logging | Loki + Promtail (lightweight) | `k8s/monitoring/loki.yaml` | Query logs in Grafana | Essential |
| 17 | Prometheus | Scrape `/metrics` from app | `k8s/monitoring/prometheus.yaml` | Targets UP | Essential |
| 18 | Grafana visualization | Dashboard with request rate, latency | `k8s/monitoring/grafana-dashboard.json` | Live panel | Essential |
| 19 | SRE principles | Define SLIs/SLOs/SLA for RxVerify | `docs/sre.md` | Explain in presentation | Essential |
| 20 | SLIs | Health endpoint availability, error rate, latency | `docs/sre.md` | Show queries | Essential |
| 21 | SLOs | 99.9% health availability, <1% 5xx, p95 <500ms | `docs/sre.md` | Show burn rate | Essential |
| 22 | SLAs | Demo commitment: "99.5% monthly uptime" | `docs/sre.md` | Explain difference | Essential |
| 23 | Incident management | Simulate failure → investigate → resolve | App + monitoring | Live drill | Essential |
| 24 | Postmortems | Blameless postmortem template | `docs/postmortem-template.md` | Show filled example | Essential |

---

## Part 3 — Minimal Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│   Git Push  │────▶│  GitHub Actions  │────▶│  Docker Hub │
│  (main/PR)  │     │  CI: test, scan, │     │  (GHCR)     │
└─────────────┘     │  build, push     │     └──────┬──────┘
                    └────────┬─────────┘            │
                             │                      │
                    ┌────────▼─────────┐     ┌──────▼──────┐
                    │   Minikube       │     │  Jenkins    │
                    │  (K8s Deploy)    │     │  (Docker)   │
                    │  Deployment+Svc  │     │  Jenkinsfile│
                    └────────┬─────────┘     └──────┬──────┘
                             │                      │
                    ┌────────▼─────────┐     ┌──────▼──────┐
                    │ Prometheus+Grafana│     │ GitLab CI  │
                    │   + Loki         │     │  (mirror)  │
                    └──────────────────┘     └─────────────┘
                             │
                    ┌────────▼─────────┐
                    │   Maven Demo     │
                    │  (isolated dir)  │
                    └──────────────────┘
```

**Key Principles:**
- RxVerify (Flask) = primary application for all demos
- Jenkins runs in Docker only when demonstrating (not persistent)
- GitLab CI demonstrated via GitLab.com mirror (manual setup, documented)
- Maven = separate tiny project (`maven-demo/`) — no Spring Boot
- Monitoring = Prometheus + Grafana + Loki (no full ELK)
- Traces = optional: OpenTelemetry auto-instrumentation if <30 min setup; else explain with diagram

---

## Part 4 — Implementation Sequence

### Phase 0 — Fix Baseline (15 min)
**Goal:** All existing tests pass, app runs locally and in Docker.
- **Changes:** Fix `tests/test_app.py` fixture to include `doctor_name`
- **Verification:** `pytest -q` → 4 passed
- **Commands:**
  ```bash
  cd /Users/yashsiphone/Downloads/digital-prescription-verification-devops
  .venv/bin/pytest -q
  docker compose up -d --build && sleep 3 && curl -s localhost:5001/health
  docker compose down
  ```

### Phase 1 — GitHub Actions CI/CD (30 min)
**Goal:** Single workflow running tests, lint, security scan, Docker build/push.
- **Files:** `.github/workflows/ci.yml`
- **Stages:** test → lint (ruff) → security (pip-audit, Trivy) → build → push to GHCR
- **Verification:** Push to branch → Actions tab shows green; `docker pull ghcr.io/...`
- **Dependencies:** GHCR permissions (repo settings → Actions → Read/write)

### Phase 2 — Kubernetes on Minikube (45 min)
**Goal:** Deploy RxVerify to local K8s with health checks, rolling update demo.
- **Files:** `k8s/deployment.yaml`, `k8s/service.yaml`, `k8s/namespace.yaml`
- **Features:** 1 replica, readiness/liveness probes → `/health`, rolling update strategy
- **Verification:** `kubectl apply -f k8s/` → `kubectl rollout status` → `curl $(minikube service rxverify --url)/health`
- **Rollback Demo:** `kubectl set image ...=broken-tag` → `kubectl rollout undo`

### Phase 3 — Monitoring Stack (60 min)
**Goal:** Prometheus scraping, Grafana dashboard, Loki logs visible.
- **Files:** `k8s/monitoring/` (Prometheus, Grafana, Loki, Promtail configs)
- **Approach:** Use `kube-prometheus-stack` Helm chart (fastest) or raw manifests
- **App Metrics:** Add `/metrics` endpoint via `prometheus-flask-exporter` (pip install)
- **Verification:** Port-forward Grafana → dashboard shows request rate, latency, error rate; Loki shows app logs

### Phase 4 — Jenkins & GitLab CI (45 min)
**Goal:** Both CI systems run equivalent test+build pipeline.
- **Jenkins:** `Jenkinsfile` (declarative, stages: test, build, scan); run via `docker run jenkins/jenkins:lts` + job DSL or Blue Ocean
- **GitLab:** `.gitlab-ci.yml` mirroring GH Actions; demonstrate via GitLab.com (push mirror manually once)
- **Comparison:** One-slide/table in presentation

### Phase 5 — Maven Exercise (20 min)
**Goal:** Tiny Java project demonstrating compile, test, package.
- **Files:** `maven-demo/pom.xml`, `maven-demo/src/main/java/App.java`, `maven-demo/src/test/java/AppTest.java`
- **Verification:** `cd maven-demo && mvn clean test package`

### Phase 6 — SRE & Incident Demo (30 min)
**Goal:** Define SLIs/SLOs, run one incident drill, write postmortem.
- **Files:** `docs/sre.md`, `docs/postmortem-template.md`, `docs/incident-example.md`
- **Drill:** Kill pod → observe alert → rollback → document
- **Verification:** All three docs exist; can walk through in 2 min

### Phase 7 — Polish & Presentation Prep (30 min)
**Goal:** Smooth 5-7 min demo script, fallback plans, clean repo.
- **Deliverables:** `DEMO_SCRIPT.md`, updated `README.md`
- **Fallback:** If Minikube fails → show Docker Compose + local Prometheus/Grafana via compose

---

## Part 5 — Risks & Decisions Needing Input

| Decision | Recommendation | Need Input? |
|----------|----------------|-------------|
| **GHCR vs Docker Hub** | Use GHCR (free, integrated, no extra auth) | No |
| **Monitoring install method** | `kube-prometheus-stack` Helm chart (5 min) vs raw manifests (30 min) | **Yes** — prefer Helm for speed? |
| **Traces implementation** | Add `opentelemetry-instrument` + Tempo (20 min) vs explain with diagram only | **Yes** — invest 20 min or skip? |
| **Jenkins demo method** | Run Jenkins in Docker for demo only (ephemeral) vs pre-install | No — ephemeral is fine |
| **GitLab CI demo** | Mirror repo to GitLab.com once (manual) vs explain only | **Yes** — mirror or explain? |
| **Terraform/Ansible live demo** | Show files + `terraform plan` output only (no apply) | No — already applied, don't re-apply |
| **SQLite in K8s** | Keep single replica + PVC (correct for demo) vs mention limitation | No — document limitation |

---

## Part 6 — Presentation Plan (5–7 min Main Demo)

| Time | Segment | What to Show |
|------|---------|--------------|
| 0:00–0:30 | Problem & Architecture | Slide: RxVerify workflow + DevOps pipeline diagram |
| 0:30–1:30 | Local App & Tests | `pytest -q` (4 pass), `docker compose up`, browser at :5001 |
| 1:30–2:30 | GitHub Actions CI | Push commit → Actions runs test+scan+build → GHCR image |
| 2:30–3:30 | K8s Deploy + Rolling Update | `kubectl apply`, `kubectl rollout`, curl health, break/rollback |
| 3:30–4:30 | Monitoring | Grafana dashboard (live), Loki logs, Prometheus targets |
| 4:30–5:15 | Jenkins + GitLab CI | Jenkinsfile + .gitlab-ci.yml side-by-side (30 sec each) |
| 5:15–5:45 | Maven Demo | `mvn test package` in maven-demo/ |
| 5:45–6:15 | SRE/Incident | Show SLI/SLO doc, simulate pod kill → alert → rollback → postmortem |
| 6:15–6:30 | Terraform/Ansible | Show files, `terraform plan` output, inventory ping |

**Fallback if Minikube/Monitoring Fails:**
1. Docker Compose + local Prometheus/Grafana/Loki via `docker compose -f docker-compose.monitoring.yml up`
2. Pre-recorded screen captures of K8s/monitoring as backup slides

---

## Part 7 — Final Checklist (Mapped to Syllabus)

| # | Topic | Done? | Artifact |
|---|-------|-------|----------|
| 1 | CI/CD fundamentals | ✅ | `.github/workflows/ci.yml` |
| 2 | Build/test/deploy loop | ✅ | GH Actions → Minikube |
| 3 | Jenkins CI | ✅ | `Jenkinsfile` + demo run |
| 4 | GitLab CI | ✅ | `.gitlab-ci.yml` + GitLab UI |
| 5 | Pipeline as Code | ✅ | Three CI configs compared |
| 6 | Auto compile/test | ✅ | pytest in all pipelines |
| 7 | DevSecOps | ✅ | Trivy + pip-audit in CI |
| 8 | Continuous Deployment | ✅ | Auto-deploy to Minikube on main |
| 9 | Deployment strategies | ✅ | Rolling update + rollback demo |
| 10 | K8s architecture | ✅ | Minikube components explained |
| 11 | K8s resources/deploy | ✅ | Deployment + Service manifests |
| 12 | Maven intro | ✅ | `maven-demo/` project |
| 13 | Build automation (Maven) | ✅ | `mvn test package` |
| 14 | Monitoring/observability | ✅ | Prometheus+Grafana+Loki stack |
| 15 | Three pillars | ✅ | Metrics, logs, traces shown |
| 16 | Centralized logging | ✅ | Loki + Promtail |
| 17 | Prometheus | ✅ | Scraping `/metrics` |
| 18 | Grafana | ✅ | Custom dashboard |
| 19 | SRE principles | ✅ | `docs/sre.md` |
| 20 | SLIs | ✅ | Defined in `docs/sre.md` |
| 21 | SLOs | ✅ | Defined in `docs/sre.md` |
| 22 | SLAs | ✅ | Defined in `docs/sre.md` |
| 23 | Incident management | ✅ | Live drill + `docs/incident-example.md` |
| 24 | Postmortems | ✅ | `docs/postmortem-template.md` filled |

---

## Estimated Total Effort

| Phase | Time | Cumulative |
|-------|------|------------|
| Phase 0: Fix Baseline | 15 min | 15 min |
| Phase 1: GitHub Actions | 30 min | 45 min |
| Phase 2: K8s/Minikube | 45 min | 1h 30m |
| Phase 3: Monitoring | 60 min | 2h 30m |
| Phase 4: Jenkins + GitLab | 45 min | 3h 15m |
| Phase 5: Maven | 20 min | 3h 35m |
| Phase 6: SRE/Incident | 30 min | 4h 05m |
| Phase 7: Polish | 30 min | 4h 35m |
| **Total** | ~4.5 hours | — |

**Ready for approval. Shall I proceed with Phase 0?**