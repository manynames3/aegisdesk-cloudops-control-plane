data "aws_caller_identity" "current" {}

locals {
  name            = "${var.project_name}-${var.environment}"
  account_id      = data.aws_caller_identity.current.account_id
  web_bucket      = "${local.name}-${local.account_id}-web"
  artifact_bucket = "${local.name}-${local.account_id}-artifacts"
  lambda_package  = abspath("${path.module}/${var.lambda_package_path}")

  tags = {
    Project     = "AegisDesk"
    Environment = var.environment
    ManagedBy   = "Terraform"
    CostOwner   = "cloudops"
  }
}

resource "random_password" "persona_password_seed" {
  length  = 32
  special = false
}

resource "aws_cognito_user_pool" "main" {
  name = "${local.name}-users"

  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = true
    require_uppercase                = true
    temporary_password_validity_days = 7
  }

  schema {
    name                = "team"
    attribute_data_type = "String"
    mutable             = true
    required            = false

    string_attribute_constraints {
      min_length = 1
      max_length = 32
    }
  }
}

resource "aws_cognito_user_group" "role" {
  for_each = {
    admin    = 0
    manager  = 1
    employee = 2
  }

  name         = each.key
  user_pool_id = aws_cognito_user_pool.main.id
  precedence   = each.value
}

resource "aws_cognito_user_pool_client" "web" {
  name         = "${local.name}-web"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret                      = false
  prevent_user_existence_errors        = "ENABLED"
  explicit_auth_flows                  = ["ALLOW_ADMIN_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["email", "openid", "profile"]
  supported_identity_providers         = ["COGNITO"]
  callback_urls                        = concat(var.allowed_cors_origins, ["https://${aws_cloudfront_distribution.web.domain_name}"])
  logout_urls                          = concat(var.allowed_cors_origins, ["https://${aws_cloudfront_distribution.web.domain_name}"])
  access_token_validity                = 1
  id_token_validity                    = 1
  refresh_token_validity               = 1

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }
}

resource "aws_cognito_user_pool_domain" "main" {
  domain       = "${local.name}-${local.account_id}"
  user_pool_id = aws_cognito_user_pool.main.id
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/${local.name}-api"
  retention_in_days = 7
}

resource "aws_dynamodb_table" "state" {
  name         = "${local.name}-state"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  server_side_encryption {
    enabled = true
  }
}

resource "aws_s3_bucket" "artifacts" {
  bucket        = local.artifact_bucket
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    id     = "expire-lambda-build-artifacts"
    status = "Enabled"

    filter {
      prefix = "lambda/"
    }

    expiration {
      days = 14
    }
  }
}

resource "aws_s3_object" "api_lambda_package" {
  bucket       = aws_s3_bucket.artifacts.id
  key          = "lambda/aegisdesk-api-lambda.zip"
  source       = local.lambda_package
  source_hash  = fileexists(local.lambda_package) ? filebase64sha256(local.lambda_package) : null
  content_type = "application/zip"
}

resource "aws_iam_role" "api_lambda" {
  name = "${local.name}-api-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "api_lambda" {
  name = "${local.name}-api-runtime"
  role = aws_iam_role.api_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "WriteOwnLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "${aws_cloudwatch_log_group.api.arn}:*"
      },
      {
        Sid    = "UseStateTable"
        Effect = "Allow"
        Action = [
          "dynamodb:BatchWriteItem",
          "dynamodb:DeleteItem",
          "dynamodb:DescribeTable",
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:Query",
          "dynamodb:UpdateItem"
        ]
        Resource = aws_dynamodb_table.state.arn
      },
      {
        Sid    = "ManagePortfolioPersonas"
        Effect = "Allow"
        Action = [
          "cognito-idp:AdminAddUserToGroup",
          "cognito-idp:AdminCreateUser",
          "cognito-idp:AdminGetUser",
          "cognito-idp:AdminInitiateAuth",
          "cognito-idp:AdminSetUserPassword",
          "cognito-idp:AdminUpdateUserAttributes"
        ]
        Resource = aws_cognito_user_pool.main.arn
      },
      {
        Sid      = "ReadCostExplorer"
        Effect   = "Allow"
        Action   = "ce:GetCostAndUsage"
        Resource = "*"
      },
      {
        Sid    = "InvokeApprovedBedrockModel"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          "arn:aws:bedrock:*::foundation-model/amazon.nova-lite-v1:0",
          "arn:aws:bedrock:*:${local.account_id}:inference-profile/${var.bedrock_model_id}"
        ]
      }
    ]
  })
}

resource "aws_lambda_function" "api" {
  function_name    = "${local.name}-api"
  s3_bucket        = aws_s3_bucket.artifacts.id
  s3_key           = aws_s3_object.api_lambda_package.key
  source_code_hash = fileexists(local.lambda_package) ? filebase64sha256(local.lambda_package) : null
  handler          = "app.lambda_handler.handler"
  runtime          = "python3.12"
  architectures    = ["x86_64"]
  role             = aws_iam_role.api_lambda.arn
  memory_size      = 512
  timeout          = 30

  environment {
    variables = {
      AEGISDESK_AUTH_MODE                = "cognito"
      AEGISDESK_PERSONA_ISSUER_ENABLED   = "true"
      AEGISDESK_DB_PATH                  = "/tmp/aegisdesk.db"
      AEGISDESK_COGNITO_CLIENT_ID        = aws_cognito_user_pool_client.web.id
      AEGISDESK_COGNITO_HOSTED_UI_DOMAIN = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${var.aws_region}.amazoncognito.com"
      AEGISDESK_COGNITO_REGION           = var.aws_region
      AEGISDESK_COGNITO_USER_POOL_ID     = aws_cognito_user_pool.main.id
      AEGISDESK_JWT_AUDIENCE             = aws_cognito_user_pool_client.web.id
      AEGISDESK_JWT_ISSUER               = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.main.id}"
      AEGISDESK_PERSONA_PASSWORD_SEED    = random_password.persona_password_seed.result
      AEGISDESK_POLICY_MODE              = "opa"
      AEGISDESK_OPA_EXECUTABLE           = "/var/task/bin/opa"
      AEGISDESK_OPA_POLICY_PATH          = "/var/task/policies"
      AEGISDESK_OPA_TIMEOUT_SECONDS      = "3"
      AEGISDESK_STORE_BACKEND            = "dynamodb"
      AEGISDESK_DYNAMODB_TABLE           = aws_dynamodb_table.state.name
      AEGISDESK_ENABLE_BEDROCK           = "true"
      AEGISDESK_BEDROCK_MODEL_ID         = var.bedrock_model_id
      AEGISDESK_BEDROCK_MAX_TOKENS       = "180"
      AEGISDESK_API_THROTTLE_RATE_LIMIT  = tostring(var.api_throttling_rate_limit)
      AEGISDESK_API_THROTTLE_BURST_LIMIT = tostring(var.api_throttling_burst_limit)
      AEGISDESK_MAX_REQUEST_CHARS        = tostring(var.max_request_chars)
      AEGISDESK_CLOUD_MODEL_KILL_SWITCH  = tostring(var.cloud_model_kill_switch)
      AEGISDESK_ENABLE_COST_EXPLORER     = "true"
      AEGISDESK_COST_CACHE_TTL_SECONDS   = "21600"
      AEGISDESK_COST_EXPLORER_SCOPE      = "tagged"
      AEGISDESK_COST_EXPLORER_TAG_KEY    = "Project"
      AEGISDESK_COST_EXPLORER_TAG_VALUE  = "AegisDesk"
      AEGISDESK_CORS_ORIGINS             = join(",", concat(var.allowed_cors_origins, ["https://${aws_cloudfront_distribution.web.domain_name}"]))
      OTEL_SERVICE_NAME                  = "aegisdesk-api"
    }
  }

  depends_on = [aws_cloudwatch_log_group.api, aws_dynamodb_table.state, aws_cognito_user_group.role, aws_s3_object.api_lambda_package]
}

resource "aws_apigatewayv2_api" "http" {
  name          = "${local.name}-http"
  protocol_type = "HTTP"

  cors_configuration {
    allow_headers = ["authorization", "content-type"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_origins = concat(var.allowed_cors_origins, ["https://${aws_cloudfront_distribution.web.domain_name}"])
    max_age       = 300
  }
}

resource "aws_apigatewayv2_integration" "api_lambda" {
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "api_root" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "ANY /"
  target    = "integrations/${aws_apigatewayv2_integration.api_lambda.id}"
}

resource "aws_apigatewayv2_route" "api_proxy" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.api_lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = var.api_throttling_burst_limit
    throttling_rate_limit  = var.api_throttling_rate_limit
  }
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowHttpApiInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}

resource "aws_s3_bucket" "web" {
  bucket        = local.web_bucket
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "web" {
  bucket = aws_s3_bucket.web.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "web" {
  bucket = aws_s3_bucket.web.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "web" {
  bucket = aws_s3_bucket.web.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "web" {
  bucket = aws_s3_bucket.web.id

  rule {
    id     = "expire-old-static-asset-versions"
    status = "Enabled"

    filter {
      prefix = ""
    }

    noncurrent_version_expiration {
      noncurrent_days = 7
    }
  }

  depends_on = [aws_s3_bucket_versioning.web]
}

resource "aws_cloudfront_origin_access_control" "web" {
  name                              = "${local.name}-web-oac"
  description                       = "Private S3 origin access for AegisDesk static frontend."
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "web" {
  enabled             = true
  default_root_object = "index.html"
  comment             = "AegisDesk static frontend"
  price_class         = "PriceClass_100"

  origin {
    domain_name              = aws_s3_bucket.web.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.web.id
    origin_id                = "aegisdesk-web"
  }

  default_cache_behavior {
    target_origin_id       = "aegisdesk-web"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true
    cache_policy_id        = "658327ea-f89d-4fab-a63d-7e88639e58f6"
  }

  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }

  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

resource "aws_s3_bucket_policy" "web" {
  bucket = aws_s3_bucket.web.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontRead"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.web.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.web.arn
          }
        }
      }
    ]
  })
}

resource "aws_budgets_budget" "portfolio_guardrail" {
  name         = "${local.name}-monthly-guardrail"
  budget_type  = "COST"
  limit_amount = var.monthly_budget_usd
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
}
