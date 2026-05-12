terraform {
  backend "s3" {
    bucket       = "aegisdesk-terraform-state-636305658578-us-east-1"
    key          = "aegisdesk/portfolio/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}
