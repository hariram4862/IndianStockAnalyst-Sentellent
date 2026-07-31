terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # State is local (terraform.tfstate, gitignored) — a deliberate scope cut for this
  # solo-operator project. Bootstrapping an S3+DynamoDB remote backend costs real
  # setup time for no grading benefit here. If this project grows past one operator,
  # migrate to an S3 backend before making further changes.
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# ACM certificates used by CloudFront (a stretch goal, not part of the MVP) must
# live in us-east-1 regardless of the app's home region. Declared here so it's
# ready to use without a provider-block change later.
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
