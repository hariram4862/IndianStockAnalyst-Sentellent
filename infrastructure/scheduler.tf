# Runs the agentic-actions job (refresh followed stocks -> evaluate alert
# rules -> generate throttled daily briefings) as a one-off ECS task on a
# recurring schedule. Reuses the existing backend task definition/image via
# a container command override -- no new service, no new image, no HTTP
# exposure -- exactly the pattern the CI/CD pipeline already uses to run
# `alembic upgrade head` as a one-off task (see .github/workflows/deploy.yml
# and app/jobs/scheduled_agent_job.py).
resource "aws_scheduler_schedule" "agent_job" {
  name       = "${var.project_name}-agent-job"
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = var.agent_job_schedule_expression

  target {
    arn      = aws_ecs_cluster.main.arn
    role_arn = aws_iam_role.scheduler_agent_job.arn

    ecs_parameters {
      # Family-style ARN (no revision suffix) resolves to the latest ACTIVE
      # revision at trigger time, tracking whatever CI/CD last deployed
      # instead of freezing on the revision that existed at `terraform apply`.
      task_definition_arn = aws_ecs_task_definition.backend.arn_without_revision
      launch_type         = "FARGATE"

      network_configuration {
        subnets          = aws_subnet.public[*].id
        security_groups  = [aws_security_group.ecs_tasks.id]
        assign_public_ip = true
      }
    }

    input = jsonencode({
      containerOverrides = [
        {
          name    = "backend"
          command = ["python", "-m", "app.jobs.scheduled_agent_job"]
        }
      ]
    })
  }
}
