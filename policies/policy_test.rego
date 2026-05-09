package aegisdesk_test

import data.aegisdesk.chat_policy
import data.aegisdesk.approval_rules
import data.aegisdesk.model_routing
import data.aegisdesk.tool_authorization

test_chat_denies_production_admin_access if {
  result := chat_policy.decision with input as {
    "intent": "production_admin_access",
    "role": "employee",
    "team": "payments",
  }

  result.decision == "deny"
  result.reason == "employees_cannot_request_production_admin_access"
}

test_chat_requires_employee_cost_approval if {
  result := chat_policy.decision with input as {
    "intent": "cost_investigation",
    "role": "employee",
    "team": "payments",
  }

  result.decision == "approval_required"
}

test_model_routes_secrets_local if {
  result := model_routing.decision with input as {
    "intent": "incident_triage",
    "pii_detected": false,
    "secrets_detected": true,
  }

  result.provider == "local"
}

test_employee_can_create_ticket if {
  result := tool_authorization.decision with input as {
    "tool": "ticket",
    "action": "create_ticket",
    "role": "employee",
  }

  result.decision == "allow"
}

test_employee_cost_summary_requires_approval if {
  result := tool_authorization.decision with input as {
    "tool": "cost",
    "action": "view_summary",
    "role": "employee",
  }

  result.decision == "approval_required"
}

test_approval_rules_match_cost_action if {
  approval_rules.requires_approval with input as {
    "action": "view_summary",
    "role": "employee",
  }
}
