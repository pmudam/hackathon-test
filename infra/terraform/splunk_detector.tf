locals {
  detector_name = "${var.environment}:Test DynamoDB Read Capacity"
  detector_tags = [
    "environment:${var.environment}",
    "environment_prefix:${var.environment_prefix}",
    "service:${var.rca_service_name}",
  ]
}

resource "signalfx_detector" "dynamodb_read_capacity" {
  name = local.detector_name

  authorized_writer_teams = []
  tags                    = local.detector_tags

  program_text = <<-EOF
    A = data('ConsumedReadCapacityUnits', filter=filter('namespace', 'AWS/DynamoDB') and filter('stat', 'mean') and filter('TableName', '${var.dynamodb_table_prefix}-prometheus*')).sum(by=['TableName']).mean(over='10m').publish(label='A')
    B = data('AccountMaxTableLevelReads', filter=filter('stat', 'count') and filter('namespace', 'AWS/DynamoDB')).sum(over='10m').mean().publish(label='B')
    detect(when(A/B * 100 > threshold(90), '2m'), off=when(A/B * 100 <= threshold(90), '5m')).publish('WARN:PIAM-PREVIEW:High DynamoDB Read Capacity')
    detect(when(A/B * 100 > threshold(95), '2m'), off=when(A/B * 100 <= threshold(95), '5m')).publish('ALERT:PIAM-PREVIEW:High DynamoDB Read Capacity')
  EOF

  rule {
    description        = "Warn when DynamoDB read capacity exceeds 90% for two minutes."
    detect_label       = "WARN:PIAM-PREVIEW:High DynamoDB Read Capacity"
    severity           = "Warning"
    notifications      = []
    runbook_url        = "https://example.internal/runbooks/dynamodb-read-capacity"
    tip                = "Check autoscaling, burst traffic, and partition distribution."
    parameterized_body = "${var.environment} ${var.rca_service_name} DynamoDB read capacity is above 90%."
  }

  rule {
    description        = "Alert when DynamoDB read capacity exceeds 95% for two minutes."
    detect_label       = "ALERT:PIAM-PREVIEW:High DynamoDB Read Capacity"
    severity           = "Critical"
    notifications      = []
    runbook_url        = "https://example.internal/runbooks/dynamodb-read-capacity"
    tip                = "Increase capacity or mitigate hot partitions immediately."
    parameterized_body = "${var.environment} ${var.rca_service_name} DynamoDB read capacity is above 95%."
  }
}
