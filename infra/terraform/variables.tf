variable "environment" {
  description = "Environment name displayed in detector resources"
  type        = string
  default     = "PIAM-PREVIEW"
}

variable "environment_prefix" {
  description = "Environment prefix used in naming"
  type        = string
  default     = "dev"
}

variable "rca_service_name" {
  description = "Service label for RCA execution context"
  type        = string
  default     = "piam-preview-dynamodb"
}

variable "splunk_api_url" {
  description = "Splunk Observability API URL"
  type        = string
  default     = "https://api.us1.signalfx.com"
}

variable "splunk_auth_token" {
  description = "Splunk Observability auth token"
  type        = string
  sensitive   = true
  default     = ""
}

variable "dynamodb_table_prefix" {
  description = "DynamoDB table prefix used in the detector filter"
  type        = string
  default     = "staging"
}
