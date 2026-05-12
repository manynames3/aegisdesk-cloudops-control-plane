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

variable "allowed_cors_origins" {
  description = "Allowed browser origins for the API Gateway CORS policy."
  type        = list(string)
  default     = ["http://localhost:3000", "http://127.0.0.1:3000"]
}
