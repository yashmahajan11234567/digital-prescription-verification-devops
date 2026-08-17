# Ansible deployment

This playbook configures the EC2 server and deploys RxVerify:

1. Installs and starts Docker.
2. Copies only the application files required for the Docker image.
3. Builds the image on EC2.
4. Runs it on port 80 with a persistent Docker volume for SQLite data.

## Prepare local-only files

```bash
cp inventory.ini.example inventory.ini
cp secrets.yml.example secrets.yml
openssl rand -hex 32
```

Put the generated value after `app_secret_key:` in `secrets.yml`. Both files are ignored by Git.

## Check connection and deploy

```bash
ansible all -m ping
ansible-playbook deploy.yml
```

Open the `website_url` printed by Terraform after the playbook completes.
