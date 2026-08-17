# RxVerify FA1 continuation handoff

## Current status

- Application: Flask + SQLite, with Doctor and Pharmacist login flows.
- Local Docker: working at `http://localhost:5001`.
- Terraform: validated and applied; the project now uses its own VPC, public subnet, internet gateway, route table, security group, and Ubuntu EC2 instance.
- Current EC2 public IP: `13.204.156.140`.
- Ansible connectivity: `ping: pong` confirmed.
- Docker installation on EC2: complete and active.

## Last issue and fix

The first Ansible run stopped while copying files because `copy` resolved paths from the `ansible/` folder. `ansible/deploy.yml` now uses `../app.py`, `../requirements.txt`, and `../Dockerfile`. Re-run the playbook; do not recreate Terraform resources.

## Next command

From the project’s `ansible/` folder:

```bash
$HOME/Library/Python/3.12/bin/ansible-playbook deploy.yml
```

After it completes, open:

```text
http://13.204.156.140
```

Expected final Ansible result is a health response with `status: ok`.

## Important files

- `app.py`, `templates/`, `static/`: application
- `Dockerfile`, `docker-compose.yml`: local containerization
- `terraform/`: AWS infrastructure
- `ansible/inventory.ini`: local-only EC2 inventory (ignored by Git)
- `ansible/secrets.yml`: local-only Flask secret (ignored by Git)

Never upload `ansible/secrets.yml`, `terraform/terraform.tfvars`, `.pem` files, AWS credentials, `.terraform/`, or Terraform state to GitHub.

## Faculty demonstration sequence

1. Show the problem statement and workflow diagram.
2. Show the Flask application locally.
3. Show `docker compose up --build` and the container.
4. Show Terraform files and the successful EC2 apply.
5. Show `ansible all -m ping` returning `pong`.
6. Show `ansible-playbook deploy.yml` and the Docker deployment.
7. Open the public EC2 URL.
8. Show the GitHub repository.

After the demonstration, run `terraform destroy` from `terraform/` to stop AWS charges.
