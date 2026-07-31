# Infrastructure (Terraform, AWS)

Provisions everything the app needs on AWS `ap-south-1`: VPC (2 public + 2 private
subnets, no NAT gateway), ECR (backend + frontend), RDS Postgres 16 with pgvector,
Secrets Manager entries for app secrets, an ECS Fargate cluster running both
services, an ALB with host-based routing behind a wildcard ACM cert, a Route53
hosted zone for the delegated `stocks.hariram.me` subdomain, and a dedicated
IAM user so CI/CD can deploy.

## Cost profile (tuned for a free-tier/student AWS account)

Roughly **$30-50/month** if left running continuously — destroy it with
`terraform destroy` any time between working sessions to spend closer to $0:

- RDS `db.t4g.micro`: free-tier eligible (750 hrs/mo for 12 months on a new
  account); otherwise ~$13/mo.
- ALB: ~$16-20/mo (partially covered by some free-tier offers).
- 2x ECS Fargate tasks (256 CPU / 512 MB each): ~$15/mo.
- **No NAT gateway** (~$32+/mo avoided) — see below.
- Route53 hosted zone: ~$0.50/mo. Secrets Manager: ~$2/mo for 5 secrets.

## Known limitations (deliberate scope cuts)

- **State is local** (`terraform.tfstate`, gitignored). This is a solo-operator
  project; if that changes, migrate to an S3+DynamoDB backend before making
  further changes — don't let two people `apply` against local state.
- **No NAT gateway.** RDS lives in the private subnets and never needs outbound
  internet, so nothing in this VPC actually requires one. ECS tasks instead run
  in the *public* subnets with public IPs, locked down by
  `aws_security_group.ecs_tasks` (inbound only from the ALB's security group —
  not reachable directly from the internet on any port). Trade-off: if a future
  requirement needs tasks with literally no public IP, reintroduce a NAT
  gateway (or a free-tier-eligible NAT *instance*) and move the ECS
  `network_configuration` back to the private subnets.
- **No CloudFront** — the ALB serves HTTPS directly via the wildcard ACM cert.
  CloudFront in front of the frontend is a stretch goal, not required for a
  working deployment.
- **CI/CD auth is a static IAM user access key, not OIDC.** OIDC federation
  (`aws_iam_openid_connect_provider` + assume-role) was the original design —
  no long-lived key sitting in GitHub Secrets — but `AssumeRoleWithWebIdentity`
  kept failing with a generic "not authorized" error in this AWS account even
  after correcting the provider's thumbprint twice (once via a leaf-vs-root
  cert fix, once by hardcoding GitHub's documented thumbprints). Given the
  deadline, fell back to `aws_iam_user` + `aws_iam_access_key`, scoped to only
  the ECR/ECS/PassRole/logs actions CI needs. Worth revisiting post-deadline —
  rotate this key periodically in the meantime (`terraform apply -replace
  aws_iam_access_key.github_actions_deploy`, then update the two GitHub
  secrets with the new output values).

## One-time setup

1. **AWS credentials**: configure locally (`aws configure` or an SSO profile)
   with permissions to create the resources above. This is only needed for
   `terraform apply` — after the first apply, GitHub Actions deploys via OIDC
   and never needs static AWS keys.
2. **`terraform.tfvars`**: copy `terraform.tfvars.example` → `terraform.tfvars`
   and fill in real values (`github_repo`, `jwt_secret`, `gemini_api_key`,
   `google_client_id`, `google_client_secret`). This file is gitignored —
   never commit it.
3. Init and apply:
   ```
   terraform init
   terraform plan
   terraform apply
   ```
4. **Namecheap DNS delegation** (one-time, has propagation lag — do this early):
   ```
   terraform output route53_name_servers
   ```
   In the Namecheap dashboard for `hariram.me`, add an NS record for the host
   `stocks` pointing at those 4 values. Until this propagates, `app.stocks.hariram.me`
   / `api.stocks.hariram.me` won't resolve — you can still hit the app via
   `terraform output alb_dns_name` directly (over plain HTTP; the ACM cert only
   covers the real domain).
5. **GitHub repo secrets/vars** (for the CI/CD workflow — see `.github/workflows/deploy.yml`
   for exactly how each is used):

   Secrets (Settings → Secrets and variables → Actions → Secrets):
   - `AWS_ACCESS_KEY_ID` = `terraform output github_actions_access_key_id`
   - `AWS_SECRET_ACCESS_KEY` = `terraform output -raw github_actions_secret_access_key`
   - `ECR_BACKEND_REPOSITORY` = `terraform output ecr_backend_repository_url`
   - `ECR_FRONTEND_REPOSITORY` = `terraform output ecr_frontend_repository_url`
   - `ECS_CLUSTER` = `terraform output ecs_cluster_name`
   - `ECS_BACKEND_SERVICE` = `terraform output ecs_backend_service_name`
   - `ECS_FRONTEND_SERVICE` = `terraform output ecs_frontend_service_name`
   - `ECS_TASK_SUBNET_IDS` = `terraform output ecs_task_subnet_ids` (join the list with commas)
   - `ECS_TASKS_SECURITY_GROUP_ID` = `terraform output ecs_tasks_security_group_id`
   - `NEXT_PUBLIC_GOOGLE_CLIENT_ID` = same Google OAuth client ID used above

   Variables (Settings → Secrets and variables → Actions → Variables):
   - `AWS_REGION` = `ap-south-1`
   - `NEXT_PUBLIC_API_URL` = `terraform output api_url`

## Redeploying infra changes

`terraform apply` again. ECS *services* are set to ignore task-definition drift
(CI/CD owns that via `register-task-definition` + `update-service`), so
re-applying Terraform after a normal code deploy won't roll the service back to
the bootstrap image.

## Tearing down

`terraform destroy`. RDS has `skip_final_snapshot = true` and
`deletion_protection = false` — intentional for a project on a hard deadline,
but it means destroying the stack loses the database with no snapshot. Export
anything worth keeping first.
