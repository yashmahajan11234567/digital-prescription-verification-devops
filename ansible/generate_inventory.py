#!/usr/bin/env python3
"""Generate Ansible inventory from Terraform outputs.

Usage:
    python generate_inventory.py --tf-output-dir ../terraform > inventory.ini

This script reads Terraform outputs and generates an Ansible inventory file.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def get_terraform_output(tf_dir: Path, output_name: str) -> str:
    """Get a Terraform output value."""
    try:
        result = subprocess.run(
            ["terraform", "output", "-raw", output_name],
            cwd=tf_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error getting Terraform output '{output_name}': {e.stderr}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Generate Ansible inventory from Terraform outputs")
    parser.add_argument("--tf-output-dir", required=True, help="Path to Terraform output directory")
    parser.add_argument("--key-file", default="~/.ssh/your-key.pem", help="SSH private key file path")
    args = parser.parse_args()

    tf_dir = Path(args.tf_output_dir).resolve()

    if not (tf_dir / "main.tf").exists():
        print(f"Error: No Terraform configuration found in {tf_dir}", file=sys.stderr)
        sys.exit(1)

    # Get EC2 public IP from Terraform
    public_ip = get_terraform_output(tf_dir, "instance_public_ip")

    # Get key name from Terraform variables (optional)
    try:
        key_name = get_terraform_output(tf_dir, "key_name")
    except SystemExit:
        key_name = "your-key"

    # Generate inventory
    inventory = f"""[web]
{public_ip} ansible_user=ubuntu ansible_ssh_private_key_file={args.key_file} ansible_ssh_common_args='-o StrictHostKeyChecking=accept-new'

# Terraform outputs:
# instance_public_ip = {public_ip}
# instance_public_dns = {get_terraform_output(tf_dir, "instance_public_dns")}
# website_url = {get_terraform_output(tf_dir, "website_url")}
"""

    print(inventory)


if __name__ == "__main__":
    main()