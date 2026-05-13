variable "project_name" {
  description = "Short project name used in resource names and tags."
  type        = string
  default     = "aegisdesk"
}

variable "environment" {
  description = "Deployment environment label."
  type        = string
  default     = "portfolio"
}

variable "aws_region" {
  description = "AWS region for regional resources."
  type        = string
  default     = "us-east-1"
}

variable "lambda_package_path" {
  description = "Path to the Lambda zip package built by scripts/build-lambda-package.sh."
  type        = string
  default     = "../../build/aegisdesk-api-lambda.zip"
}

variable "monthly_budget_usd" {
  description = "Portfolio monthly budget guardrail."
  type        = string
  default     = "1"
}

variable "bedrock_model_id" {
  description = "Amazon Bedrock model or inference profile used for approved low-sensitivity prompts."
  type        = string
  default     = "us.amazon.nova-lite-v1:0"
}

variable "api_throttling_rate_limit" {
  description = "Default HTTP API Gateway steady-state request rate limit per second."
  type        = number
  default     = 5
}

variable "api_throttling_burst_limit" {
  description = "Default HTTP API Gateway burst request limit."
  type        = number
  default     = 20
}

variable "max_request_chars" {
  description = "Application-level prompt size limit before policy and model routing."
  type        = number
  default     = 2000
}

variable "cloud_model_kill_switch" {
  description = "When true, force approved cloud model routes back to local control handling."
  type        = bool
  default     = false
}

variable "allowed_cors_origins" {
  description = "Allowed browser origins for the API Gateway CORS policy."
  type        = list(string)
  default     = ["http://localhost:3000", "http://127.0.0.1:3000"]
}

variable "github_repository" {
  description = "GitHub repository allowed to assume the AWS deployment role through GitHub Actions OIDC."
  type        = string
  default     = "manynames3/aegisdesk-cloudops-control-plane"
}

variable "github_deploy_environment" {
  description = "GitHub environment name used for the manually gated AWS apply job."
  type        = string
  default     = "aws-portfolio"
}
