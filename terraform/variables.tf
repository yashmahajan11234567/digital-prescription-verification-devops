variable "aws_region" {
  description = "AWS Region in which to create the EC2 server."
  type        = string
  default     = "ap-south-1"
}

variable "aws_profile" {
  description = "Name of the locally configured AWS CLI profile."
  type        = string
  default     = "friend"
}

variable "project_name" {
  description = "Short name used to label cloud resources."
  type        = string
  default     = "rxverify-fa1"
}

variable "key_name" {
  description = "Name of the existing EC2 key pair used for SSH access."
  type        = string
  default     = "fa1-key-new"
}

variable "allowed_ssh_cidr" {
  description = "Your current public IPv4 address in CIDR form, for example 203.0.113.10/32."
  type        = string
  default     = "122.170.199.47/32"
}

variable "instance_type" {
  description = "EC2 instance size for the project."
  type        = string
  default     = "t3.micro"
}
