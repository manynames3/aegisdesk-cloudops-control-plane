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

output "artifact_bucket_name" {
  description = "Private S3 bucket for Lambda deployment artifacts."
  value       = aws_s3_bucket.artifacts.bucket
}

output "state_table_name" {
  description = "DynamoDB table used for durable application state."
  value       = aws_dynamodb_table.state.name
}

output "jwks_url" {
  description = "Public Cognito JWKS endpoint used for JWT verification."
  value       = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.main.id}/.well-known/jwks.json"
}

output "cognito_user_pool_id" {
  description = "Cognito User Pool ID."
  value       = aws_cognito_user_pool.main.id
}

output "cognito_user_pool_client_id" {
  description = "Cognito User Pool app client ID."
  value       = aws_cognito_user_pool_client.web.id
}

output "monthly_budget_name" {
  description = "AWS Budget guardrail resource name."
  value       = aws_budgets_budget.portfolio_guardrail.name
}
