"use client";

import {
  Activity,
  AlertTriangle,
  Check,
  ChevronRight,
  Clock,
  ClipboardList,
  Database,
  DollarSign,
  KeyRound,
  ListFilter,
  Lock,
  MessageSquare,
  Play,
  RefreshCw,
  Server,
  ShieldCheck,
  User,
  X
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Role = "employee" | "manager" | "admin";
type Tab = "chat" | "approvals" | "governance" | "evaluations";
type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };

type MetricSummary = {
  requests_total: number;
  estimated_spend_usd: number;
  local_model_requests: number;
  cloud_model_requests: number;
  redactions_total: number;
  denied_actions: number;
  approvals_pending: number;
  tool_calls_total: number;
};

type ChatResponse = {
  request_id: string;
  answer: string;
  model_route: {
    provider: string;
    model: string;
    reason: string;
    estimated_cost_usd: number;
    external_call: boolean;
  };
  redaction: {
    pii_detected: boolean;
    secrets_detected: boolean;
    findings: { kind: string; label: string; replacement: string }[];
  };
  policy: {
    decision: "allow" | "deny" | "approval_required";
    reason: string;
    policy_name: string;
  };
  tool_calls: {
    tool_call_id: string;
    name: string;
    status: "allowed" | "blocked" | "approval_required";
    policy: {
      decision: "allow" | "deny" | "approval_required";
      reason: string;
      policy_name: string;
    };
    result: Record<string, JsonValue>;
  }[];
  incident_context?: IncidentContext | null;
  trace_id: string;
};

type IncidentContext = {
  incident_id: string;
  source: "seeded_cloudwatch_logs";
  log_group: string;
  query: string;
  suspected_cause: string;
  entries: {
    timestamp: string;
    level: "INFO" | "WARN" | "ERROR";
    service: string;
    message: string;
  }[];
};

type AuditEvent = {
  event_id: string;
  request_id: string;
  timestamp: string;
  actor: {
    user_id: string;
    role: Role;
    team: string;
  };
  event_type: string;
  summary: string;
  trace_id: string;
  metadata: Record<string, JsonValue>;
};

type Approval = {
  approval_id: string;
  request_id: string;
  resource: string;
  permission: string;
  reason: string;
  risk_level: "low" | "medium" | "high";
  status: "pending" | "approved" | "denied";
  policy_reason: string;
  created_at: string;
  requester: {
    user_id: string;
    role: Role;
    team: string;
  };
  decided_by?: string | null;
  decided_at?: string | null;
};

type PersonaTokenResponse = {
  access_token: string;
  actor: {
    user_id: string;
    role: Role;
    team: string;
  };
};

type Message = {
  role: "user" | "assistant";
  text: string;
  response?: ChatResponse;
};

const prompts = [
  {
    label: "Incident",
    icon: Activity,
    text: "The checkout service is timing out. What should I check first?"
  },
  {
    label: "Secret",
    icon: Lock,
    text: "Here is the error log with token=sample-secret-value and customer@example.test. Why is this failing?"
  },
  {
    label: "Ticket",
    icon: ClipboardList,
    text: "Create a ticket for the VPN outage and assign it to CloudOps."
  },
  {
    label: "Access",
    icon: KeyRound,
    text: "Give me admin access to the production database."
  },
  {
    label: "Cost",
    icon: DollarSign,
    text: "Why did our AI and cloud costs spike this week?"
  }
];

const walkthroughSteps = [
  {
    title: "Redact a sensitive log",
    detail: "Submit a log with a token and customer email, then show the redaction badge and local route.",
    role: "employee" as Role,
    tab: "chat" as Tab
  },
  {
    title: "Block production admin access",
    detail: "Show a plain-English denial and create a safer read-only approval request.",
    role: "employee" as Role,
    tab: "chat" as Tab
  },
  {
    title: "Approve with a human manager",
    detail: "Switch to Manager, approve the pending scoped request, and record the decision timestamp.",
    role: "manager" as Role,
    tab: "approvals" as Tab
  },
  {
    title: "Review routing and audit trail",
    detail: "Trigger a Bedrock-eligible request, then inspect the DynamoDB-backed governance trail.",
    role: "admin" as Role,
    tab: "governance" as Tab
  }
];

const initialMetrics: MetricSummary = {
  requests_total: 0,
  estimated_spend_usd: 0,
  local_model_requests: 0,
  cloud_model_requests: 0,
  redactions_total: 0,
  denied_actions: 0,
  approvals_pending: 0,
  tool_calls_total: 0
};

export default function Home() {
  const [tab, setTab] = useState<Tab>("chat");
  const [role, setRole] = useState<Role>("employee");
  const [message, setMessage] = useState(prompts[0].text);
  const [messages, setMessages] = useState<Message[]>([]);
  const [metrics, setMetrics] = useState<MetricSummary>(initialMetrics);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [apiStatus, setApiStatus] = useState<"checking" | "ok" | "offline">("checking");
  const [walkthroughOpen, setWalkthroughOpen] = useState(false);
  const [walkthroughStep, setWalkthroughStep] = useState(0);
  const [eventFilters, setEventFilters] = useState({
    requestId: "",
    user: "",
    decision: "any",
    route: "any",
    tool: ""
  });

  const canApprove = role === "manager" || role === "admin";
  const canManageState = role === "admin";

  async function authHeaders(selectedRole = role): Promise<HeadersInit> {
    const response = await fetch(`${API_BASE}/auth/persona-token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        role: selectedRole,
        team: selectedRole === "admin" ? "platform" : "payments"
      })
    });

    if (!response.ok) {
      throw new Error("persona_token_failed");
    }

    const token = (await response.json()) as PersonaTokenResponse;
    return {
      Authorization: `Bearer ${token.access_token}`,
      "Content-Type": "application/json"
    };
  }

  async function refreshData(selectedRole = role) {
    try {
      const headers = await authHeaders(selectedRole);
      const [healthRes, metricsRes, eventsRes, approvalsRes] = await Promise.all([
        fetch(`${API_BASE}/health`),
        fetch(`${API_BASE}/metrics/summary`, { headers }),
        fetch(`${API_BASE}/events`, { headers }),
        fetch(`${API_BASE}/approvals`, { headers })
      ]);

      setApiStatus(healthRes.ok ? "ok" : "offline");
      setMetrics(metricsRes.ok ? await metricsRes.json() : initialMetrics);
      setEvents(eventsRes.ok ? (await eventsRes.json()).events : []);
      setApprovals(approvalsRes.ok ? (await approvalsRes.json()).approvals : []);
    } catch {
      setApiStatus("offline");
    }
  }

  useEffect(() => {
    refreshData();
  }, [role]);

  async function submitMessage(text: string, selectedRole = role) {
    const headers = await authHeaders(selectedRole);
    const response = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        message: text,
        context: { incident_id: "INC-1042" }
      })
    });

    if (!response.ok) {
      throw new Error("chat_failed");
    }

    return (await response.json()) as ChatResponse;
  }

  async function sendChat(event?: FormEvent) {
    event?.preventDefault();
    const trimmed = message.trim();
    if (!trimmed || isSending) return;

    setIsSending(true);
    setMessages((current) => [...current, { role: "user", text: trimmed }]);

    try {
      const body = await submitMessage(trimmed);
      setMessages((current) => [...current, { role: "assistant", text: body.answer, response: body }]);
      await refreshData();
    } catch {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          text: `API request failed. Verify the gateway is reachable at ${API_BASE} and retry.`
        }
      ]);
      setApiStatus("offline");
    } finally {
      setIsSending(false);
    }
  }

  async function decideApproval(approvalId: string, action: "approve" | "deny", selectedRole = role) {
    const headers = await authHeaders(selectedRole);
    await fetch(`${API_BASE}/approvals/${approvalId}/${action}`, {
      method: "POST",
      headers
    });
    await refreshData(selectedRole);
  }

  async function resetState() {
    if (!canManageState) return;
    const headers = await authHeaders("admin");
    await fetch(`${API_BASE}/admin/reset`, { method: "POST", headers });
    setMessages([]);
    await refreshData("admin");
  }

  async function seedState() {
    if (!canManageState) return;
    const headers = await authHeaders("admin");
    await fetch(`${API_BASE}/admin/seed`, { method: "POST", headers });
    setMessages([]);
    await refreshData("admin");
  }

  async function runWalkthroughStep(index: number) {
    const step = walkthroughSteps[index];
    setWalkthroughOpen(true);
    setWalkthroughStep(index);
    setRole(step.role);
    setTab(step.tab);

    if (index === 0 || index === 1) {
      const prompt = index === 0 ? prompts[1].text : prompts[3].text;
      setMessage(prompt);
      setIsSending(true);
      setMessages((current) => [...current, { role: "user", text: prompt }]);
      try {
        const body = await submitMessage(prompt, "employee");
        setMessages((current) => [...current, { role: "assistant", text: body.answer, response: body }]);
      } finally {
        setIsSending(false);
        await refreshData("employee");
      }
    }

    if (index === 2) {
      const pending = approvals.find((item) => item.status === "pending");
      if (pending) {
        await decideApproval(pending.approval_id, "approve", "manager");
      } else {
        await refreshData("manager");
      }
    }

    if (index === 3) {
      const prompt = "What is the safest way to ask for help with a CloudOps issue?";
      setMessage(prompt);
      setRole("employee");
      setTab("chat");
      setIsSending(true);
      setMessages((current) => [...current, { role: "user", text: prompt }]);
      try {
        const body = await submitMessage(prompt, "employee");
        setMessages((current) => [...current, { role: "assistant", text: body.answer, response: body }]);
      } finally {
        setIsSending(false);
        setRole("admin");
        setTab("governance");
        await refreshData("admin");
      }
    }
  }

  const latestResponse = useMemo(
    () => [...messages].reverse().find((item) => item.response)?.response,
    [messages]
  );

  const filteredEvents = useMemo(() => {
    return events.filter((event) => {
      const requestMatch = event.request_id.toLowerCase().includes(eventFilters.requestId.toLowerCase().trim());
      const userMatch = event.actor.user_id.toLowerCase().includes(eventFilters.user.toLowerCase().trim());
      const decisionMatch =
        eventFilters.decision === "any" ||
        (eventFilters.decision === "allow" && event.event_type.includes("allowed")) ||
        (eventFilters.decision === "deny" && event.event_type.includes("denied")) ||
        (eventFilters.decision === "approval_required" && event.event_type.includes("approval"));
      const routeMatch =
        eventFilters.route === "any" ||
        String(event.metadata.provider ?? "").toLowerCase() === eventFilters.route ||
        String(event.metadata.model ?? "").toLowerCase().includes(eventFilters.route);
      const toolMatch =
        !eventFilters.tool.trim() ||
        String(event.metadata.tool ?? "").toLowerCase().includes(eventFilters.tool.toLowerCase().trim());

      return requestMatch && userMatch && decisionMatch && routeMatch && toolMatch;
    });
  }, [events, eventFilters]);

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand">
          <ShieldCheck size={28} />
          <div>
            <strong>AegisDesk</strong>
            <span>CloudOps Control Plane</span>
          </div>
        </div>

        <nav className="tabs" aria-label="Primary">
          <TabButton icon={MessageSquare} label="Chat" active={tab === "chat"} onClick={() => setTab("chat")} />
          <TabButton icon={KeyRound} label="Approvals" active={tab === "approvals"} onClick={() => setTab("approvals")} />
          <TabButton icon={Database} label="Governance" active={tab === "governance"} onClick={() => setTab("governance")} />
          <TabButton icon={ShieldCheck} label="Evaluations" active={tab === "evaluations"} onClick={() => setTab("evaluations")} />
        </nav>

        <div className="rolePanel">
          <span>Role</span>
          <div className="segmented">
            {(["employee", "manager", "admin"] as Role[]).map((option) => (
              <button
                key={option}
                className={role === option ? "selected" : ""}
                onClick={() => setRole(option)}
                type="button"
              >
                {option}
              </button>
            ))}
          </div>
        </div>

        <div className={`status ${apiStatus}`}>
          <span />
          API {apiStatus}
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p>Live AWS deployment</p>
            <h1>{tabTitle(tab)}</h1>
          </div>
          <div className="topActions">
            <button className="secondary" onClick={() => setWalkthroughOpen((current) => !current)} type="button">
              <Play size={16} />
              Walkthrough
            </button>
            <button className="iconButton" onClick={() => refreshData()} title="Refresh" type="button">
              <RefreshCw size={18} />
            </button>
            <button className="secondary" disabled={!canManageState} onClick={seedState} title="Admin identity required" type="button">
              Seed
            </button>
            <button className="secondary" disabled={!canManageState} onClick={resetState} title="Admin identity required" type="button">
              Reset
            </button>
          </div>
        </header>

        {walkthroughOpen && (
          <GuidedWalkthrough
            activeStep={walkthroughStep}
            isRunning={isSending}
            onRun={runWalkthroughStep}
            onClose={() => setWalkthroughOpen(false)}
          />
        )}

        {tab === "chat" && (
          <div className="chatGrid">
            <section className="panel chatPanel">
              <div className="promptBar">
                {prompts.map((prompt) => {
                  const Icon = prompt.icon;
                  return (
                    <button key={prompt.label} onClick={() => setMessage(prompt.text)} type="button">
                      <Icon size={16} />
                      {prompt.label}
                    </button>
                  );
                })}
              </div>

              <div className="transcript">
                {messages.length === 0 && (
                  <div className="emptyState">
                    <ShieldCheck size={34} />
                    <span>Submit a CloudOps request.</span>
                  </div>
                )}
                {messages.map((item, index) => (
                  <div className={`bubble ${item.role}`} key={`${item.role}-${index}`}>
                    <p>{item.text}</p>
                    {item.response && <ResponseMeta response={item.response} />}
                    {item.response?.incident_context && <IncidentEvidence context={item.response.incident_context} />}
                  </div>
                ))}
              </div>

              <form className="composer" onSubmit={sendChat}>
                <textarea value={message} onChange={(event) => setMessage(event.target.value)} rows={3} />
                <button disabled={isSending} type="submit">
                  <MessageSquare size={18} />
                  Send
                </button>
              </form>
            </section>

            <aside className="panel decisionPanel">
              <h2>Decision Trail</h2>
              {latestResponse ? <DecisionTrail response={latestResponse} /> : <span className="muted">No request yet.</span>}
            </aside>
          </div>
        )}

        {tab === "approvals" && (
          <section className="panel">
            <div className="sectionHeader">
              <h2>Approval Queue</h2>
              <span>{approvals.filter((item) => item.status === "pending").length} pending</span>
            </div>
            <div className="table">
              {approvals.length === 0 && <div className="emptyRow">No approval records.</div>}
              {approvals.map((approval) => (
                <div className="approvalRow" key={approval.approval_id}>
                  <div className="approvalMain">
                    <div>
                      <strong>{approval.resource}</strong>
                      <span>{approval.permission} - {approval.policy_reason}</span>
                    </div>
                    <div className="approvalFacts">
                      <span><User size={14} /> Requester {approval.requester.user_id}</span>
                      <span><Clock size={14} /> Created {formatTime(approval.created_at)}</span>
                      <span><Database size={14} /> Request {approval.request_id}</span>
                      {approval.decided_by && <span><Check size={14} /> {approval.decided_by} at {formatTime(approval.decided_at)}</span>}
                    </div>
                    <ApprovalTimeline approval={approval} events={events.filter((event) => event.request_id === approval.request_id)} />
                  </div>
                  <Badge tone={approval.status === "approved" ? "good" : approval.status === "denied" ? "bad" : "warn"}>
                    {approval.status}
                  </Badge>
                  <div className="rowActions">
                    <button
                      className="iconButton"
                      disabled={!canApprove || approval.status !== "pending"}
                      onClick={() => decideApproval(approval.approval_id, "approve")}
                      title="Approve"
                      type="button"
                    >
                      <Check size={18} />
                    </button>
                    <button
                      className="iconButton"
                      disabled={!canApprove || approval.status !== "pending"}
                      onClick={() => decideApproval(approval.approval_id, "deny")}
                      title="Deny"
                      type="button"
                    >
                      <X size={18} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {tab === "governance" && (
          <div className="governanceGrid">
            <Metric icon={Activity} label="Requests" value={metrics.requests_total} />
            <Metric icon={DollarSign} label="Spend" value={`$${metrics.estimated_spend_usd.toFixed(4)}`} />
            <Metric icon={Lock} label="Redactions" value={metrics.redactions_total} />
            <Metric icon={AlertTriangle} label="Denied" value={metrics.denied_actions} />
            <Metric icon={KeyRound} label="Pending" value={metrics.approvals_pending} />
            <Metric icon={ClipboardList} label="Tools" value={metrics.tool_calls_total} />

            <section className="panel eventPanel">
              <div className="sectionHeader">
                <h2>Audit Event Explorer</h2>
                <span>{filteredEvents.length} of {events.length} shown</span>
              </div>
              <EventFilters filters={eventFilters} onChange={setEventFilters} />
              <div className="eventList">
                {filteredEvents.length === 0 && <div className="emptyRow">No matching audit events.</div>}
                {filteredEvents.map((event) => (
                  <div className="eventItem" key={event.event_id}>
                    <Badge tone={event.event_type.includes("denied") || event.event_type.includes("blocked") ? "bad" : "neutral"}>
                      {event.event_type}
                    </Badge>
                    <div>
                      <strong>{event.summary}</strong>
                      <span>
                        {event.request_id} - {event.actor.user_id} - {event.actor.role} - {event.trace_id}
                      </span>
                      <EventMetadata event={event} />
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>
        )}

        {tab === "evaluations" && (
          <section className="panel evalPanel">
            <div className="sectionHeader">
              <h2>Control Checks</h2>
              <span>deterministic MVP</span>
            </div>
            <EvalRow label="Secret-like values are redacted before routing" status="ready" />
            <EvalRow label="Production admin access is denied" status="ready" />
            <EvalRow label="Temporary read-only access requires approval" status="ready" />
            <EvalRow label="Ticket creation is policy-gated" status="ready" />
            <EvalRow label="Cost summary requires manager or admin role" status="ready" />
          </section>
        )}
      </section>
    </main>
  );
}

function TabButton({
  icon: Icon,
  label,
  active,
  onClick
}: {
  icon: LucideIcon;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button className={active ? "active" : ""} onClick={onClick} type="button">
      <Icon size={18} />
      {label}
    </button>
  );
}

function Badge({ children, tone }: { children: React.ReactNode; tone: "good" | "bad" | "warn" | "neutral" }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

function GuidedWalkthrough({
  activeStep,
  isRunning,
  onRun,
  onClose
}: {
  activeStep: number;
  isRunning: boolean;
  onRun: (index: number) => void;
  onClose: () => void;
}) {
  return (
    <section className="walkthrough panel">
      <div className="walkthroughHeader">
        <div>
          <strong>Guided walkthrough</strong>
          <span>Four clicks cover redaction, denied access, human approval, Bedrock routing, and the audit trail.</span>
        </div>
        <button className="iconButton" onClick={onClose} title="Close walkthrough" type="button">
          <X size={18} />
        </button>
      </div>
      <div className="walkthroughSteps">
        {walkthroughSteps.map((step, index) => (
          <button
            className={activeStep === index ? "walkthroughStep active" : "walkthroughStep"}
            disabled={isRunning}
            key={step.title}
            onClick={() => onRun(index)}
            type="button"
          >
            <span>{index + 1}</span>
            <div>
              <strong>{step.title}</strong>
              <small>{step.detail}</small>
            </div>
            <ChevronRight size={16} />
          </button>
        ))}
      </div>
    </section>
  );
}

function ResponseMeta({ response }: { response: ChatResponse }) {
  return (
    <div className="metaGrid">
      <Badge tone={response.policy.decision === "allow" ? "good" : response.policy.decision === "deny" ? "bad" : "warn"}>
        {response.policy.decision}
      </Badge>
      <Badge tone={response.model_route.provider === "local" ? "neutral" : "warn"}>{response.model_route.provider}</Badge>
      {(response.redaction.pii_detected || response.redaction.secrets_detected) && <Badge tone="warn">redacted</Badge>}
      {response.tool_calls.map((tool) => (
        <Badge key={tool.tool_call_id} tone={tool.status === "allowed" ? "good" : tool.status === "blocked" ? "bad" : "warn"}>
          {tool.name}
        </Badge>
      ))}
    </div>
  );
}

function IncidentEvidence({ context }: { context: IncidentContext }) {
  return (
    <div className="incidentEvidence">
      <div>
        <Server size={16} />
        <strong>{context.incident_id}</strong>
        <span>{context.log_group}</span>
      </div>
      <p>{context.suspected_cause}</p>
      <div className="logEntries">
        {context.entries.slice(0, 3).map((entry) => (
          <div className="logEntry" key={`${entry.timestamp}-${entry.service}`}>
            <Badge tone={entry.level === "ERROR" ? "bad" : entry.level === "WARN" ? "warn" : "neutral"}>{entry.level}</Badge>
            <span>{entry.service}</span>
            <strong>{entry.message}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

function DecisionTrail({ response }: { response: ChatResponse }) {
  const plainDecision = explainDecision(response);
  const redaction = response.redaction.findings.length
    ? response.redaction.findings.map((finding) => finding.kind).join(", ")
    : "No sensitive values detected.";

  return (
    <div className="decisionStack">
      <DecisionItem label="Decision" value={plainDecision} emphasis />
      <DecisionItem label="Technical policy" value={`${response.policy.policy_name}: ${response.policy.reason}`} />
      <DecisionItem label="Route" value={explainRoute(response)} />
      <DecisionItem label="Redaction" value={redaction} />
      <DecisionItem label="Cost" value={`$${response.model_route.estimated_cost_usd.toFixed(4)}`} />
      <DecisionItem label="Trace" value={response.trace_id} />
    </div>
  );
}

function DecisionItem({ label, value, emphasis = false }: { label: string; value: string; emphasis?: boolean }) {
  return (
    <div className={emphasis ? "decisionItem emphasis" : "decisionItem"}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ApprovalTimeline({ approval, events }: { approval: Approval; events: AuditEvent[] }) {
  const requested = events.find((event) => event.event_type === "approval.requested");
  const decided = events.find((event) => event.event_type === "approval.granted" || event.event_type === "approval.denied");

  return (
    <div className="approvalTimeline">
      <span>Before: {requested ? requested.summary : "Approval request recorded."}</span>
      <span>After: {decided ? decided.summary : approval.status === "pending" ? "Waiting for manager decision." : "Decision recorded."}</span>
    </div>
  );
}

function EventFilters({
  filters,
  onChange
}: {
  filters: { requestId: string; user: string; decision: string; route: string; tool: string };
  onChange: (filters: { requestId: string; user: string; decision: string; route: string; tool: string }) => void;
}) {
  return (
    <div className="eventFilters">
      <label>
        <ListFilter size={15} />
        <input
          onChange={(event) => onChange({ ...filters, requestId: event.target.value })}
          placeholder="Request ID"
          value={filters.requestId}
        />
      </label>
      <label>
        <User size={15} />
        <input onChange={(event) => onChange({ ...filters, user: event.target.value })} placeholder="User" value={filters.user} />
      </label>
      <select onChange={(event) => onChange({ ...filters, decision: event.target.value })} value={filters.decision}>
        <option value="any">Any decision</option>
        <option value="allow">Allow</option>
        <option value="deny">Deny</option>
        <option value="approval_required">Approval required</option>
      </select>
      <select onChange={(event) => onChange({ ...filters, route: event.target.value })} value={filters.route}>
        <option value="any">Any route</option>
        <option value="local">Local</option>
        <option value="bedrock">Bedrock</option>
        <option value="simulated-cloud">Fallback</option>
      </select>
      <label>
        <ClipboardList size={15} />
        <input onChange={(event) => onChange({ ...filters, tool: event.target.value })} placeholder="Tool" value={filters.tool} />
      </label>
      <button className="secondary" onClick={() => onChange({ requestId: "", user: "", decision: "any", route: "any", tool: "" })} type="button">
        Clear
      </button>
    </div>
  );
}

function EventMetadata({ event }: { event: AuditEvent }) {
  const values = [
    event.metadata.reason ? `policy ${String(event.metadata.reason)}` : null,
    event.metadata.provider ? `route ${String(event.metadata.provider)}` : null,
    event.metadata.tool ? `tool ${String(event.metadata.tool)}` : null,
    event.metadata.approval_id ? `approval ${String(event.metadata.approval_id)}` : null
  ].filter(Boolean);

  if (!values.length) return null;
  return <small className="eventMeta">{values.join(" - ")}</small>;
}

function explainDecision(response: ChatResponse) {
  const toolNames = response.tool_calls.map((tool) => tool.name);

  if (response.policy.reason === "employees_cannot_request_production_admin_access") {
    return "Denied because Employee cannot request production admin access. A safer read-only request was opened for manager approval.";
  }
  if (response.policy.reason === "cost_investigation_requires_manager_or_admin") {
    return "Approval required because cost investigation is limited to Manager or Admin roles.";
  }
  if (response.redaction.findings.length) {
    return "Allowed after sensitive values were redacted before model routing.";
  }
  if (toolNames.includes("incident.context")) {
    return "Allowed. Read-only incident logs were attached before giving triage guidance.";
  }
  if (response.model_route.provider === "bedrock") {
    return "Allowed to use Amazon Bedrock because policy found no sensitive data in the request.";
  }
  if (response.model_route.provider === "simulated-cloud") {
    return "Allowed through the cloud route, with deterministic fallback available when Bedrock is unavailable.";
  }
  return response.policy.decision === "allow" ? "Allowed by role and policy." : "Policy requires review before this action can proceed.";
}

function explainRoute(response: ChatResponse) {
  if (response.model_route.provider === "local") {
    return `Kept local with ${response.model_route.model}: ${response.model_route.reason}.`;
  }
  if (response.model_route.provider === "bedrock") {
    return `Sent to Amazon Bedrock (${response.model_route.model}) under the low-sensitivity route.`;
  }
  return `Used ${response.model_route.model}: ${response.model_route.reason}.`;
}

function formatTime(value?: string | null) {
  if (!value) return "not decided";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  }).format(new Date(value));
}

function Metric({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: string | number }) {
  return (
    <div className="metric panel">
      <Icon size={20} />
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function EvalRow({ label, status }: { label: string; status: string }) {
  return (
    <div className="evalRow">
      <Check size={18} />
      <span>{label}</span>
      <Badge tone="good">{status}</Badge>
    </div>
  );
}

function tabTitle(tab: Tab) {
  if (tab === "approvals") return "Approvals";
  if (tab === "governance") return "Governance";
  if (tab === "evaluations") return "Evaluations";
  return "Chat";
}
