terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
  default_tags {
    tags = {
      Project = "twin-cities-east-housing"
      Owner   = "anthony"
    }
  }
}

resource "aws_s3_bucket" "twin-cities-east-housing-built-by-anthony" {
  bucket = "twin-cities-east-housing-built-by-anthony"

}

resource "aws_s3_bucket_public_access_block" "main" {
  bucket = aws_s3_bucket.twin-cities-east-housing-built-by-anthony.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}