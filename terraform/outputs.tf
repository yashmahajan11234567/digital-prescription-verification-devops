output "instance_public_ip" {
  description = "Public IPv4 address used by Ansible and your browser."
  value       = aws_instance.rxverify.public_ip
}

output "instance_public_dns" {
  description = "Public DNS name of the EC2 instance."
  value       = aws_instance.rxverify.public_dns
}

output "website_url" {
  description = "Open this URL after the Ansible deployment is complete."
  value       = "http://${aws_instance.rxverify.public_ip}"
}
