resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "disabled" # cost-conscious default; flip to "enabled" if debugging needs it
  }
}

resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/${var.project_name}/backend"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/ecs/${var.project_name}/frontend"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "migrate" {
  name              = "/ecs/${var.project_name}/migrate"
  retention_in_days = 14
}

resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.project_name}-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "backend"
      image     = "${aws_ecr_repository.backend.repository_url}:${var.backend_image_tag}"
      essential = true
      portMappings = [
        { containerPort = 8000, protocol = "tcp" }
      ]
      environment = [
        { name = "APP_NAME", value = "Sentellent Indian Stock Analyst" },
        { name = "APP_VERSION", value = "1.0.0" },
        { name = "ENVIRONMENT", value = var.environment },
        { name = "JWT_ALGORITHM", value = "HS256" },
        { name = "ACCESS_TOKEN_EXPIRE_MINUTES", value = "1440" },
        { name = "FRONTEND_URL", value = "https://${var.app_subdomain}" },
        { name = "GEMINI_MODEL", value = "gemini-flash-latest" },
        { name = "GEMINI_EMBEDDING_MODEL", value = "gemini-embedding-001" },
        { name = "EMBEDDING_DIMENSIONS", value = "1536" },
        { name = "SES_SENDER_EMAIL", value = var.ses_notification_email },
        { name = "AWS_REGION", value = var.aws_region },
      ]
      secrets = [
        { name = "DATABASE_URL", valueFrom = aws_secretsmanager_secret.database_url.arn },
        { name = "JWT_SECRET", valueFrom = aws_secretsmanager_secret.jwt_secret.arn },
        { name = "GEMINI_API_KEY", valueFrom = aws_secretsmanager_secret.gemini_api_key.arn },
        { name = "GOOGLE_CLIENT_ID", valueFrom = aws_secretsmanager_secret.google_client_id.arn },
        { name = "GOOGLE_CLIENT_SECRET", valueFrom = aws_secretsmanager_secret.google_client_secret.arn },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.backend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "backend"
        }
      }
    }
  ])
}

resource "aws_ecs_task_definition" "frontend" {
  family                   = "${var.project_name}-frontend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "frontend"
      image     = "${aws_ecr_repository.frontend.repository_url}:${var.frontend_image_tag}"
      essential = true
      portMappings = [
        { containerPort = 3000, protocol = "tcp" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.frontend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "frontend"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "backend" {
  name            = "${var.project_name}-backend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    # Public subnets, no NAT gateway (see network.tf) — locked down by
    # aws_security_group.ecs_tasks, not actually open to the internet.
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener_rule.api]

  # CI/CD registers new task definition revisions and force-deploys them
  # directly; don't let `terraform apply` fight that back to the bootstrap image.
  lifecycle {
    ignore_changes = [task_definition]
  }
}

resource "aws_ecs_service" "frontend" {
  name            = "${var.project_name}-frontend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    # Public subnets, no NAT gateway (see network.tf) — locked down by
    # aws_security_group.ecs_tasks, not actually open to the internet.
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = 3000
  }

  depends_on = [aws_lb_listener_rule.app]

  lifecycle {
    ignore_changes = [task_definition]
  }
}
