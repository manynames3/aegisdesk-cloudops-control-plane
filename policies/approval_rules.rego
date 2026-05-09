package aegisdesk.approval_rules

default requires_approval := false

requires_approval if {
  input.action == "request_temporary_read_only"
  input.resource == "prod-payments-db"
}

requires_approval if {
  input.action == "view_cost_summary"
  input.role == "employee"
}

