package aegisdesk.tool_authorization

default decision := {
  "decision": "deny",
  "reason": "tool_action_not_allowed",
}

decision := {
  "decision": "allow",
  "reason": "employees_can_create_support_tickets",
} if {
  input.tool == "ticket"
  input.action == "create_ticket"
  input.role in {"employee", "manager", "admin"}
}

decision := {
  "decision": "deny",
  "reason": "production_admin_access_is_not_self_service",
} if {
  input.tool == "access"
  input.action == "grant_production_admin"
}

decision := {
  "decision": "approval_required",
  "reason": "temporary_production_access_requires_manager_approval",
} if {
  input.tool == "access"
  input.action == "request_temporary_read_only"
}

decision := {
  "decision": "allow",
  "reason": "managers_and_admins_can_view_cost_summary",
} if {
  input.tool == "cost"
  input.action == "view_summary"
  input.role in {"manager", "admin"}
}

decision := {
  "decision": "approval_required",
  "reason": "cost_summary_requires_manager_or_admin",
} if {
  input.tool == "cost"
  input.action == "view_summary"
  input.role == "employee"
}

