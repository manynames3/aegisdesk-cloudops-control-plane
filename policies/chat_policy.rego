package aegisdesk.chat_policy

decision := {
  "decision": "deny",
  "reason": "employees_cannot_request_production_admin_access",
} if {
  input.intent == "production_admin_access"
}

decision := {
  "decision": "approval_required",
  "reason": "cost_investigation_requires_manager_or_admin",
} if {
  input.intent == "cost_investigation"
  input.role == "employee"
}

decision := {
  "decision": "allow",
  "reason": reason,
} if {
  input.intent != "production_admin_access"
  not employee_cost_investigation
  reason := sprintf("%s_allowed_for_%s", [input.intent, input.role])
}

employee_cost_investigation if {
  input.intent == "cost_investigation"
  input.role == "employee"
}
