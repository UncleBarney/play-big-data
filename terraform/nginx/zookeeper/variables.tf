variable "aws_access_key" {
  default = "AKIAIQSVQ42XIFSO3WPQ"
}

variable "aws_secret_key" {
  default = "8YwYG5kM/8C0Vj6fB7cVVTiCU4phZi5Lf7g9A9EM"
}

variable "ami_image" {
	default = "ami-40d28157"
}

variable "key_name" {
  description = "Name of your AWS key pair"
  default = "test"
}

variable "key_path" {
  description = "path to your private key file"
  default = "test.pem"
}