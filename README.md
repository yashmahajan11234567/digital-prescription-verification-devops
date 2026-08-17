# Digital Prescription Verification System

A local-first MVP for the DevOps FA1 project. It lets an authorised clinic issue a digital prescription and lets a pharmacist or patient verify it using a unique prescription ID.

## MVP features

- Separate Doctor and Pharmacist login portals.
- Doctors create and revoke prescriptions; pharmacists verify them.
- Store records locally in SQLite.
- Generate a non-sequential verification ID.
- Verify a prescription from a public-looking verification page.
- Revoke a prescription to demonstrate an invalid/expired verification result.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app run --debug
```

Then open `http://127.0.0.1:5000`.

The SQLite file is created automatically at `instance/prescriptions.db`. It is local development data and is intentionally not committed.

### Local demo accounts

| Role | Email | Password |
| --- | --- | --- |
| Doctor | `doctor@rxverify.local` | `doctor123` |
| Pharmacist | `pharmacist@rxverify.local` | `pharmacist123` |

These credentials are only for the local demo. An Admin portal is planned for a later phase.

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

Open `http://localhost:5001`. The application database is saved in the named Docker volume `prescription_data`, so created prescriptions remain after a normal container restart.

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
