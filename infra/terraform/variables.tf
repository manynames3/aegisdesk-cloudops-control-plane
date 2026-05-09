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

variable "api_image_uri" {
  description = "Container image URI for the FastAPI Lambda package. Placeholder value keeps validate plan-only."
  type        = string
  default     = "123456789012.dkr.ecr.us-east-1.amazonaws.com/aegisdesk-api:placeholder"
}

variable "monthly_budget_usd" {
  description = "Portfolio monthly budget guardrail."
  type        = string
  default     = "1"
}

variable "allowed_cors_origins" {
  description = "Allowed browser origins for the API Gateway CORS policy."
  type        = list(string)
  default     = ["http://localhost:3000"]
}
