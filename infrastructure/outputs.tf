output "alb_dns_name" {
  description = "Raw ALB DNS name (useful for debugging before DNS propagates)."
  value       = aws_lb.main.dns_name
}

output "route53_name_servers" {
  description = "NS records to add at Namecheap as a delegation for the 'stocks' subdomain."
  value       = aws_route53_zone.app.name_servers
}

output "ecr_backend_repository_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_repository_url" {
  value = aws_ecr_repository.frontend.repository_url
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "ecs_backend_service_name" {
  value = aws_ecs_service.backend.name
}

output "ecs_frontend_service_name" {
  value = aws_ecs_service.frontend.name
}

output "github_actions_role_arn" {
  description = "Role ARN GitHub Actions assumes via OIDC — set as AWS_DEPLOY_ROLE_ARN in the repo."
  value       = aws_iam_role.github_actions_deploy.arn
}

output "ecs_task_subnet_ids" {
  description = "Subnets ECS tasks run in (public, no NAT — see network.tf). Used by the CI/CD migration one-off task."
  value       = aws_subnet.public[*].id
}

output "ecs_tasks_security_group_id" {
  value = aws_security_group.ecs_tasks.id
}

output "api_url" {
  value = "https://${var.api_subdomain}"
}

output "app_url" {
  value = "https://${var.app_subdomain}"
}
