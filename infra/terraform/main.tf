terraform {
  required_version = "~> 1.6"

  backend "local" {}

  required_providers {
    signalfx = {
      source  = "splunk-terraform/signalfx"
      version = "~> 9.1.6"
    }
  }
}

provider "signalfx" {
  auth_token = var.splunk_auth_token
  api_url    = var.splunk_api_url
}
