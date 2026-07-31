variable "aws_region" {
  description = "AWS region for all resources except CloudFront ACM certs."
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Short name used to prefix/tag resources."
  type        = string
  default     = "stock-analyst"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "production"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.42.0.0/20"
}

# --- Domain / DNS ---
# Delegated subdomain (hariram.me stays at Namecheap; only this subdomain's NS
# records point to the Route53 zone created below). See infrastructure/README.md
# for the one-time Namecheap delegation step.
variable "domain_zone_name" {
  description = "Subdomain Route53 will manage (delegated from Namecheap)."
  type        = string
  default     = "stocks.hariram.me"
}

variable "api_subdomain" {
  description = "Full hostname for the backend API."
  type        = string
  default     = "api.stocks.hariram.me"
}

variable "app_subdomain" {
  description = "Full hostname for the frontend app."
  type        = string
  default     = "app.stocks.hariram.me"
}

# --- GitHub OIDC / CI-CD ---
variable "github_repo" {
  description = "GitHub \"owner/repo\" allowed to assume the deploy role via OIDC. PLACEHOLDER — replace once the repo exists, before relying on CI/CD."
  type        = string
  default     = "YOUR_GH_USERNAME/indian-stock-analyst"
}

# --- Database ---
variable "db_name" {
  description = "Postgres database name."
  type        = string
  default     = "stock_analyst"
}

variable "db_username" {
  description = "Postgres master username."
  type        = string
  default     = "stock_analyst_app"
}

variable "db_instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t4g.micro"
}

# --- Application secrets (no defaults — supply via terraform.tfvars, gitignored) ---
variable "jwt_secret" {
  description = "Secret used to sign application JWTs."
  type        = string
  sensitive   = true
}

variable "gemini_api_key" {
  description = "Google Gemini API key."
  type        = string
  sensitive   = true
}

variable "google_client_id" {
  description = "Google OAuth client ID."
  type        = string
  sensitive   = true
}

variable "google_client_secret" {
  description = "Google OAuth client secret."
  type        = string
  sensitive   = true
}

# --- Container images ---
# CI/CD registers new task definition revisions with real commit-SHA tags after
# every deploy; this default only matters for the very first `terraform apply`
# before any image has been pushed to ECR.
variable "backend_image_tag" {
  description = "Initial backend image tag (CI/CD manages this afterward)."
  type        = string
  default     = "latest"
}

variable "frontend_image_tag" {
  description = "Initial frontend image tag (CI/CD manages this afterward)."
  type        = string
  default     = "latest"
}

# --- Agentic actions (scheduled refresh / alerts / daily briefings) ---
variable "ses_notification_email" {
  description = "Address used as both sender and recipient for alert/briefing emails (same address for both sidesteps SES sandbox-mode recipient verification entirely). AWS emails a verification link here after apply -- must be clicked before mail actually sends; everything else (in-app alerts, decisions, refresh) works regardless."
  type        = string
}

variable "agent_job_schedule_expression" {
  description = "EventBridge Scheduler rate/cron expression for the scheduled agent job (refresh + alerts + daily briefings)."
  type        = string
  default     = "rate(6 hours)"
}
