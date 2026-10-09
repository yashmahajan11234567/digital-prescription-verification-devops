# Digital Prescription Verification System

A local-first MVP for the DevOps FA1 project. It lets an authorised clinic issue a digital prescription and lets a pharmacist or patient verify it using a unique prescription ID.

## MVP features

- Separate Doctor, Pharmacist, and **Admin** login portals.
- Doctors create and revoke prescriptions; pharmacists verify them; admins manage hospitals, doctors, and pharmacists.
- Store records locally in SQLite (dev) or PostgreSQL (prod).
- Generate a non-sequential verification ID (RX-XXXXXXXXXX format).
- Verify a prescription from a public-looking verification page.
- Revoke a prescription to demonstrate an invalid/expired verification result.
- **Admin portal:** Hospital CRUD, doctor/pharmacist management, notifications.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app run --debug
```

Then open `http://127.0.0.1:5003`.

The SQLite file is created automatically at `instance/prescriptions.db`. It is local development data and is intentionally not committed.

### Local demo accounts

| Role | Email | Password |
| --- | --- | --- |
| Doctor | `doctor@rxverify.local` | `doctor123` |
| Pharmacist | `pharmacist@rxverify.local` | `pharmacist123` |
| Admin | `admin@rxverify.local` | `admin123` |

These credentials are only for the local demo.

## Check the MVP

```bash
pip install -r requirements-dev.txt
pytest -q
```

This is a classroom prototype: use fictional patient details only. Authentication, encryption, audit logging, and production-grade access control belong in a later hardening phase.

## Run with Docker

Install and start Docker Desktop, then run this from the project folder:

```bash
docker compose up --build
```

Open `http://localhost:5003`. The application database is saved in the named Docker volume `prescription_data`, so created prescriptions remain after a normal container restart.

Useful commands:

```bash
# Start in the background
docker compose up --build -d

# View application logs
docker compose logs -f

# Stop the container (keeps prescription data)
docker compose down
```

To remove the local Docker database as well, run `docker compose down -v`. This permanently deletes the local demo prescriptions.

## Kubernetes (Minikube) — Verified Demo Environment

The production-style deployment runs on Minikube with full monitoring:

```bash
# Start Minikube
minikube start

# Build and load image
docker build -t rxverify:latest .
minikube image load rxverify:latest

# Deploy (kustomize)
kubectl apply -k k8s/

# Port-forwards for demo
kubectl -n rxverify port-forward svc/rxverify 5003:80 --address 0.0.0.0 &
kubectl -n monitoring port-forward svc/monitoring-kube-prometheus-prometheus 9091:9090 --address 0.0.0.0 &
kubectl -n monitoring port-forward svc/monitoring-grafana 3000:80 --address 0.0.0.0 &
kubectl -n monitoring port-forward svc/loki 3100:3100 --address 0.0.0.0 &
```

### Verified Demo URLs (after port-forwards)

| Service | URL | Purpose |
| --- | --- | --- |
| **RxVerify App** | http://127.0.0.1:5003 | Main application |
| **Prometheus** | http://localhost:9091 | Metrics (`up{job="rxverify"}=1`) |
| **Grafana** | http://127.0.0.1:3000 | Dashboards (5-panel RxVerify dashboard provisioned) |
| **Loki** | http://localhost:3100 | Log aggregation (range queries via `/loki/api/v1/query_range`) |

Grafana admin password: `kubectl -n monitoring get secret monitoring-grafana -o jsonpath="{.data.admin-password}" | base64 -d`

## Monitoring Stack (Prometheus, Grafana, Loki)

- **Prometheus** scrapes `/metrics` from RxVerify via `ServiceMonitor` (job=`rxverify`, port=5000)
- **Grafana** dashboards provisioned via ConfigMap; includes RxVerify DevOps Dashboard (5 panels)
- **Loki** + **Promtail** DaemonSet aggregate application logs with labels `job=rxverify`, `filename`

## Later DevOps path

The application boundary is intentionally simple: one Flask service plus a persisted SQLite file. The later phases will add:

1. Docker image and Docker Compose for the application.
2. Terraform to provision an AWS EC2 instance and security group.
3. Ansible to install Docker and deploy the image on that EC2 instance.

No AWS managed application backend services are required.

## AWS Terraform deployment

The Terraform configuration is in [`terraform/`](terraform/). It provisions an Ubuntu EC2 instance, allows HTTP traffic for the website, and restricts SSH to your current public IP. Follow [`terraform/README.md`](terraform/README.md) to preview the changes before creating anything in AWS.

## Ansible deployment

The Ansible configuration is in [`ansible/`](ansible/). After Terraform provisions EC2, the playbook installs Docker, builds RxVerify on the server, and runs it on port 80.