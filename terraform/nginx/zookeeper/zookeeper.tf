provider "aws" {
  access_key = "${var.aws_access_key}"
  secret_key = "${var.aws_secret_key}"
  region = "us-east-1"
}

resource "aws_instance" "zookeeper" {
	ami = "${var.ami_image}"
	instance_type = "t2.medium"
	security_groups = ["${aws_security_group.allow-all.name}"]
	key_name = "${var.key_name}"

	connection {
		user = "ubuntu"
		private_key = "${file(var.key_path)}"
	}

	provisioner "remote-exec" {
		inline = [
			"sudo apt-get -y update",
			"sudo apt-get install -y python-minimal",
		]
	}

	provisioner "local-exec" {
		command = "ansible -u ubuntu -m ping --private-key ${var.key_path} tag_Name_zookeeper* && ansible-playbook zookeeper.yml --private-key ${var.key_path}"
	}

	tags {
		Name = "zookeeper"
	}
}

resource "aws_security_group" "allow-all" {
	name = "allow-all-sg"
	ingress {
		from_port = 0
		to_port = 0
		protocol = "-1"
		cidr_blocks = ["0.0.0.0/0"]
	}

	egress {
		from_port = 0
		to_port = 0
		protocol = "-1"
		cidr_blocks = ["0.0.0.0/0"]
	}
}