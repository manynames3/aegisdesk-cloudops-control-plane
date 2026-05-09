output "api_repository_url" {
  description = "ECR repository for the FastAPI image."
  value       = aws_ecr_repository.api.repository_url
}

output "api_gateway_url" {
  description = "HTTP API Gateway invoke URL."
  value       = aws_apigatewayv2_api.http.api_endpoint
}

output "frontend_distribution_domain" {
  description = "CloudFront distribution domain for the static frontend."
  value       = aws_cloudfront_distribution.web.domain_name
}

output "monthly_budget_name" {
  description = "AWS Budget guardrail resource name."
  value       = aws_budgets_budget.portfolio_guardrail.name
}
