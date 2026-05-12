package aegisdesk.model_routing

default decision := {
  "decision": "allow",
  "provider": "bedrock",
  "reason": "low_sensitivity_request_can_use_bedrock_route",
}

decision := {
  "decision": "allow",
  "provider": "local",
  "reason": "secrets_redacted_before_local_model_route",
} if {
  input.secrets_detected == true
}

decision := {
  "decision": "allow",
  "provider": "local",
  "reason": "pii_redacted_before_local_model_route",
} if {
  input.pii_detected == true
  input.secrets_detected == false
}

decision := {
  "decision": "allow",
  "provider": "local",
  "reason": "internal_operational_context_uses_local_route",
} if {
  input.intent in {"incident_triage", "production_admin_access", "temporary_read_only_access"}
  input.pii_detected == false
  input.secrets_detected == false
}
