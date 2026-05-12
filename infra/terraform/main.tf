data "aws_caller_identity" "current" {}

locals {
  name           = "${var.project_name}-${var.environment}"
  account_id     = data.aws_caller_identity.current.account_id
  web_bucket     = "${local.name}-${local.account_id}-web"
  lambda_package = abspath("${path.module}/${var.lambda_package_path}")

  tags = {
    Project     = "AegisDesk"
    Environment = var.environment
    ManagedBy   = "Terraform"
    CostOwner   = "portfolio-demo"
  }
}

resource "tls_private_key" "demo_jwks" {
  algorithm = "RSA"
  rsa_bits  = 2048
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
        Sid    = "UseDemoStateTable"
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
  filename         = local.lambda_package
  source_code_hash = fileexists(local.lambda_package) ? filebase64sha256(local.lambda_package) : null
  handler          = "app.lambda_handler.handler"
  runtime          = "python3.12"
  architectures    = ["x86_64"]
  role             = aws_iam_role.api_lambda.arn
  memory_size      = 512
  timeout          = 30

  environment {
    variables = {
      DEMO_MODE                      = "true"
      AEGISDESK_AUTH_MODE            = "jwks"
      AEGISDESK_DB_PATH              = "/tmp/aegisdesk.db"
      AEGISDESK_JWKS_KEY_ID          = "${local.name}-demo-rs256"
      AEGISDESK_JWKS_PRIVATE_KEY_PEM = tls_private_key.demo_jwks.private_key_pem
      AEGISDESK_JWKS_PUBLIC_KEY_PEM  = tls_private_key.demo_jwks.public_key_pem
      AEGISDESK_JWT_ISSUER           = "${local.name}-issuer"
      AEGISDESK_POLICY_MODE          = "python"
      AEGISDESK_STORE_BACKEND        = "dynamodb"
      AEGISDESK_DYNAMODB_TABLE       = aws_dynamodb_table.state.name
      AEGISDESK_ENABLE_BEDROCK       = "true"
      AEGISDESK_BEDROCK_MODEL_ID     = var.bedrock_model_id
      AEGISDESK_BEDROCK_MAX_TOKENS   = "180"
      OTEL_SERVICE_NAME              = "aegisdesk-api"
    }
  }

  depends_on = [aws_cloudwatch_log_group.api, aws_dynamodb_table.state]
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
  comment             = "AegisDesk portfolio static frontend"
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
