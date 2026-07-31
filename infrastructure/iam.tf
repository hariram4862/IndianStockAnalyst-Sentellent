# --- ECS task execution role: pulls images from ECR, writes logs, reads the
#     specific secrets each task needs. ---

data "aws_iam_policy_document" "ecs_task_execution_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_task_execution" {
  name               = "${var.project_name}-ecs-task-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_execution_assume.json
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_managed" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "ecs_task_execution_secrets" {
  statement {
    actions = ["secretsmanager:GetSecretValue"]
    resources = [
      aws_secretsmanager_secret.database_url.arn,
      aws_secretsmanager_secret.jwt_secret.arn,
      aws_secretsmanager_secret.gemini_api_key.arn,
      aws_secretsmanager_secret.google_client_id.arn,
      aws_secretsmanager_secret.google_client_secret.arn,
    ]
  }
}

resource "aws_iam_role_policy" "ecs_task_execution_secrets" {
  name   = "${var.project_name}-ecs-task-execution-secrets"
  role   = aws_iam_role.ecs_task_execution.id
  policy = data.aws_iam_policy_document.ecs_task_execution_secrets.json
}

# --- ECS task role: the app's own runtime identity. No extra AWS API access is
#     needed today (the app doesn't call AWS services directly), kept minimal. ---

data "aws_iam_policy_document" "ecs_task_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_task" {
  name               = "${var.project_name}-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume.json
}

# First AWS API access the app's own runtime identity needs: the scheduled
# agent job sends alert/briefing emails via SES (see
# backend/app/services/notification_service.py). Scoped to only the one
# verified identity, not "*".
data "aws_iam_policy_document" "ecs_task_ses" {
  statement {
    actions   = ["ses:SendEmail", "ses:SendRawEmail"]
    resources = [aws_ses_email_identity.notifications.arn]
  }
}

resource "aws_iam_role_policy" "ecs_task_ses" {
  name   = "${var.project_name}-ecs-task-ses"
  role   = aws_iam_role.ecs_task.id
  policy = data.aws_iam_policy_document.ecs_task_ses.json
}

# --- GitHub Actions CI/CD identity ---
# OIDC federation (aws_iam_openid_connect_provider + assume-role) was tried
# first (no long-lived keys in GitHub) but AssumeRoleWithWebIdentity kept
# failing with a generic "not authorized" error even after correcting the
# thumbprint twice (both a recomputed leaf/root fix and hardcoding GitHub's
# documented root CA thumbprints) -- something about this account's OIDC
# trust evaluation didn't resolve within the time available before the
# deadline. Falling back to a dedicated, narrowly-scoped IAM user with a
# static access key instead: guaranteed to work, at the cost of a long-lived
# credential sitting in GitHub Secrets. Revisit OIDC post-deadline if desired.

resource "aws_iam_user" "github_actions_deploy" {
  name = "${var.project_name}-github-actions-deploy"
}

resource "aws_iam_access_key" "github_actions_deploy" {
  user = aws_iam_user.github_actions_deploy.name
}

data "aws_iam_policy_document" "github_actions_deploy" {
  statement {
    sid = "EcrAuth"
    actions = [
      "ecr:GetAuthorizationToken",
    ]
    resources = ["*"]
  }

  statement {
    sid = "EcrPushPull"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "ecr:PutImage",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload",
    ]
    resources = [
      aws_ecr_repository.backend.arn,
      aws_ecr_repository.frontend.arn,
    ]
  }

  statement {
    sid = "EcsDeploy"
    actions = [
      "ecs:RegisterTaskDefinition",
      "ecs:DescribeTaskDefinition",
      "ecs:DescribeServices",
      "ecs:DescribeTasks",
      "ecs:UpdateService",
      "ecs:RunTask",
    ]
    resources = ["*"]
  }

  statement {
    sid       = "PassEcsRoles"
    actions   = ["iam:PassRole"]
    resources = [aws_iam_role.ecs_task_execution.arn, aws_iam_role.ecs_task.arn]
  }

  statement {
    sid       = "ReadLogs"
    actions   = ["logs:DescribeLogGroups", "logs:GetLogEvents"]
    resources = ["*"]
  }
}

resource "aws_iam_user_policy" "github_actions_deploy" {
  name   = "${var.project_name}-github-actions-deploy"
  user   = aws_iam_user.github_actions_deploy.name
  policy = data.aws_iam_policy_document.github_actions_deploy.json
}

# --- EventBridge Scheduler: runs the scheduled agent job as a one-off ECS
#     task on the same backend task definition/image, exactly like the CI/CD
#     migration step (see infrastructure/scheduler.tf). ---

data "aws_iam_policy_document" "scheduler_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "scheduler_agent_job" {
  name               = "${var.project_name}-scheduler-agent-job"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume.json
}

data "aws_iam_policy_document" "scheduler_agent_job" {
  statement {
    sid     = "RunAgentJobTask"
    actions = ["ecs:RunTask"]
    # Wildcarded by revision, not pinned to the Terraform-known one: CI/CD
    # registers a new task definition revision on every deploy without a
    # `terraform apply` (see .github/workflows/deploy.yml), so a specific
    # revision ARN here would silently freeze the scheduled job on
    # whatever code existed at the last `apply` instead of tracking deploys.
    resources = ["${aws_ecs_task_definition.backend.arn_without_revision}:*"]
  }

  statement {
    sid       = "PassEcsRoles"
    actions   = ["iam:PassRole"]
    resources = [aws_iam_role.ecs_task_execution.arn, aws_iam_role.ecs_task.arn]
  }
}

resource "aws_iam_role_policy" "scheduler_agent_job" {
  name   = "${var.project_name}-scheduler-agent-job"
  role   = aws_iam_role.scheduler_agent_job.id
  policy = data.aws_iam_policy_document.scheduler_agent_job.json
}
