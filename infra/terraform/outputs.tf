output "splunk_detector_id" {
  value       = signalfx_detector.dynamodb_read_capacity.id
  description = "Splunk Observability detector id"
}

output "splunk_detector_name" {
  value       = signalfx_detector.dynamodb_read_capacity.name
  description = "Splunk Observability detector name"
}
