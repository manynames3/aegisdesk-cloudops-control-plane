package aegisdesk.quota

limits := {
  "employee": 25,
  "manager": 50,
  "admin": 100,
}

default decision := {
  "decision": "deny",
  "reason": "unknown_role_quota_denied",
  "limit": 0,
}

decision := {
  "decision": "allow",
  "reason": "daily_role_quota_available",
  "limit": limit,
  "current_count": input.current_count,
  "window": "daily",
} if {
  limit := limits[input.role]
  input.current_count < limit
}

decision := {
  "decision": "deny",
  "reason": "daily_role_quota_exceeded",
  "limit": limit,
  "current_count": input.current_count,
  "window": "daily",
} if {
  limit := limits[input.role]
  input.current_count >= limit
}
