# Terraform infrastructure

This folder creates the AWS infrastructure for RxVerify:

- Project-specific VPC, public subnet, route table, and internet gateway
- Ubuntu 24.04 EC2 instance in that public subnet
- Security group: SSH limited to your public IP, HTTP open for the website

## Before applying

1. Confirm the AWS CLI profile works:

   ```bash
   aws sts get-caller-identity --profile fa1
   ```

2. Find your public IP address:

   ```bash
   curl -4 ifconfig.me
   ```

3. Create `terraform.tfvars` from `terraform.tfvars.example`, replacing `YOUR_PUBLIC_IP/32` with the displayed address, for example `203.0.113.10/32`.

## Provision

```bash
terraform init
terraform fmt -check
terraform validate
terraform plan
terraform apply
```

After `apply`, copy the `instance_public_ip` output. It becomes the host address for the Ansible inventory in the next step.

## Clean up

After faculty evaluation, remove the cloud resources to prevent further charges:

```bash
terraform destroy
```
