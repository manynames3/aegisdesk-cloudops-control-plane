"use client";

import {
  Activity,
  AlertTriangle,
  Check,
  ClipboardList,
  Database,
  DollarSign,
  KeyRound,
  Lock,
  MessageSquare,
  RefreshCw,
  ShieldCheck,
  X
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Role = "employee" | "manager" | "admin";
type Tab = "chat" | "approvals" | "governance" | "evaluations";

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
    result: Record<string, string | number | boolean>;
  }[];
  trace_id: string;
};

type AuditEvent = {
  event_id: string;
  request_id: string;
  timestamp: string;
  event_type: string;
  summary: string;
  trace_id: string;
  metadata: Record<string, string | number | boolean | string[]>;
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
};

type DemoTokenResponse = {
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
    text: "Here is the error log with token=demo-secret-value and customer@example.test. Why is this failing?"
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

  const canApprove = role === "manager" || role === "admin";
  const canSeedDemo = role === "admin";

  async function authHeaders(selectedRole = role): Promise<HeadersInit> {
    const response = await fetch(`${API_BASE}/auth/demo-token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        role: selectedRole,
        team: selectedRole === "admin" ? "platform" : "payments"
      })
    });

    if (!response.ok) {
      throw new Error("demo_token_failed");
    }

    const token = (await response.json()) as DemoTokenResponse;
    return {
      Authorization: `Bearer ${token.access_token}`,
      "Content-Type": "application/json"
    };
  }

  async function refreshData() {
    try {
      const headers = await authHeaders();
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

  async function sendChat(event?: FormEvent) {
    event?.preventDefault();
    const trimmed = message.trim();
    if (!trimmed || isSending) return;

    setIsSending(true);
    setMessages((current) => [...current, { role: "user", text: trimmed }]);

    try {
      const headers = await authHeaders();
      const response = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          message: trimmed,
          context: { incident_id: "INC-1042" }
        })
      });

      if (!response.ok) {
        throw new Error("chat_failed");
      }

      const body = (await response.json()) as ChatResponse;
      setMessages((current) => [...current, { role: "assistant", text: body.answer, response: body }]);
      await refreshData();
    } catch {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          text: "API is offline. Start the FastAPI service on port 8000 and retry."
        }
      ]);
      setApiStatus("offline");
    } finally {
      setIsSending(false);
    }
  }

  async function decideApproval(approvalId: string, action: "approve" | "deny") {
    const headers = await authHeaders();
    await fetch(`${API_BASE}/approvals/${approvalId}/${action}`, {
      method: "POST",
      headers
    });
    await refreshData();
  }

  async function resetDemo() {
    if (!canSeedDemo) return;
    const headers = await authHeaders("admin");
    await fetch(`${API_BASE}/demo/reset`, { method: "POST", headers });
    setMessages([]);
    await refreshData();
  }

  async function seedDemo() {
    if (!canSeedDemo) return;
    const headers = await authHeaders("admin");
    await fetch(`${API_BASE}/demo/seed`, { method: "POST", headers });
    setMessages([]);
    await refreshData();
  }

  const latestResponse = useMemo(
    () => [...messages].reverse().find((item) => item.response)?.response,
    [messages]
  );

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
            <p>Local demo</p>
            <h1>{tabTitle(tab)}</h1>
          </div>
          <div className="topActions">
            <button className="iconButton" onClick={refreshData} title="Refresh" type="button">
              <RefreshCw size={18} />
            </button>
            <button className="secondary" disabled={!canSeedDemo} onClick={seedDemo} title="Admin demo role required" type="button">
              Seed
            </button>
            <button className="secondary" disabled={!canSeedDemo} onClick={resetDemo} title="Admin demo role required" type="button">
              Reset
            </button>
          </div>
        </header>

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
                  <div>
                    <strong>{approval.resource}</strong>
                    <span>{approval.permission} - {approval.policy_reason}</span>
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
                <h2>Audit Events</h2>
                <span>{events.length} shown</span>
              </div>
              <div className="eventList">
                {events.length === 0 && <div className="emptyRow">No audit events.</div>}
                {events.map((event) => (
                  <div className="eventItem" key={event.event_id}>
                    <Badge tone={event.event_type.includes("denied") || event.event_type.includes("blocked") ? "bad" : "neutral"}>
                      {event.event_type}
                    </Badge>
                    <div>
                      <strong>{event.summary}</strong>
                      <span>{event.trace_id}</span>
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

function DecisionTrail({ response }: { response: ChatResponse }) {
  return (
    <div className="decisionStack">
      <DecisionItem label="Policy" value={response.policy.reason} />
      <DecisionItem label="Route" value={`${response.model_route.model} - ${response.model_route.reason}`} />
      <DecisionItem label="Cost" value={`$${response.model_route.estimated_cost_usd.toFixed(4)}`} />
      <DecisionItem label="Trace" value={response.trace_id} />
      <DecisionItem
        label="Redaction"
        value={
          response.redaction.findings.length
            ? response.redaction.findings.map((finding) => finding.kind).join(", ")
            : "none"
        }
      />
    </div>
  );
}

function DecisionItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="decisionItem">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
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
