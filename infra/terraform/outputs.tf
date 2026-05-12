output "api_gateway_url" {
  description = "HTTP API Gateway invoke URL."
  value       = aws_apigatewayv2_api.http.api_endpoint
}

output "frontend_distribution_domain" {
  description = "CloudFront distribution domain for the static frontend."
  value       = aws_cloudfront_distribution.web.domain_name
}

output "frontend_distribution_id" {
  description = "CloudFront distribution ID for cache invalidation."
  value       = aws_cloudfront_distribution.web.id
}

output "frontend_bucket_name" {
  description = "Private S3 bucket for the exported static frontend."
  value       = aws_s3_bucket.web.bucket
}

output "monthly_budget_name" {
  description = "AWS Budget guardrail resource name."
  value       = aws_budgets_budget.portfolio_guardrail.name
}
