# Public hosted zone for the delegated subdomain. hariram.me itself stays at
# Namecheap; only the NS records for this subdomain need to point here.
# See infrastructure/README.md for the one-time Namecheap delegation step —
# `terraform output route53_name_servers` gives the values to paste in.
resource "aws_route53_zone" "app" {
  name = var.domain_zone_name
}

resource "aws_acm_certificate" "app" {
  domain_name = var.domain_zone_name
  subject_alternative_names = [
    "*.${var.domain_zone_name}",
  ]
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "cert_validation" {
  # Keyed by the actual validation record name, not domain_name: ACM sometimes
  # issues the SAME validation CNAME for the apex and its wildcard SAN, and
  # keying by domain_name would then try to create that identical record
  # twice and fail with "already exists".
  for_each = {
    for dvo in aws_acm_certificate.app.domain_validation_options : dvo.resource_record_name => {
      name   = dvo.resource_record_name
      type   = dvo.resource_record_type
      record = dvo.resource_record_value
    }...
  }

  zone_id = aws_route53_zone.app.zone_id
  name    = each.value[0].name
  type    = each.value[0].type
  records = [each.value[0].record]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "app" {
  certificate_arn         = aws_acm_certificate.app.arn
  validation_record_fqdns = [for r in aws_route53_record.cert_validation : r.fqdn]
}

resource "aws_route53_record" "api" {
  zone_id = aws_route53_zone.app.zone_id
  name    = var.api_subdomain
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "app" {
  zone_id = aws_route53_zone.app.zone_id
  name    = var.app_subdomain
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}
