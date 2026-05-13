"use client";

import {
  Activity,
  AlertTriangle,
  Check,
  ChevronRight,
  Clock,
  ClipboardList,
  Copy,
  Database,
  DollarSign,
  KeyRound,
  ListFilter,
  LogIn,
  LogOut,
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
const AUTH_TOKEN_KEY = "aegisdesk.cognito.idToken";
const AUTH_ACTOR_KEY = "aegisdesk.cognito.actor";
const PKCE_VERIFIER_KEY = "aegisdesk.pkce.verifier";
const PKCE_STATE_KEY = "aegisdesk.pkce.state";
const PKCE_REDIRECT_KEY = "aegisdesk.pkce.redirectUri";

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

type Actor = {
  user_id: string;
  role: Role;
  team: string;
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
    input_tokens?: number;
    output_tokens?: number;
  };
  redaction: {
    pii_detected: boolean;
    secrets_detected: boolean;
    redacted_text?: string;
    findings: { kind: string; label: string; replacement: string }[];
  };
  policy: {
    decision: "allow" | "deny" | "approval_required";
    reason: string;
    policy_name: string;
    metadata?: Record<string, JsonValue>;
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
  knowledge_citations: KnowledgeCitation[];
  answer_sources: AnswerSource[];
  trusted_source_score?: TrustedSourceScore;
  trace_id: string;
};

type TrustedSourceScore = {
  score: number;
  trusted_source_found: boolean;
  source_freshness: "fresh" | "stale" | "unknown";
  external_model_used: boolean;
  sensitive_data_sent_externally: boolean;
  policy_result: string;
  rationale: string[];
};

type AnswerSource = {
  kind: "deterministic" | "model" | "knowledge" | "operational_context" | "tool" | "policy" | "cost";
  name: string;
  detail: string;
  trusted: boolean;
};

type KnowledgeCitation = {
  doc_id: string;
  title: string;
  source_path: string;
  section: string;
  owner: string;
  last_reviewed: string;
  excerpt: string;
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
  actor: Actor;
  event_type: string;
  summary: string;
  trace_id: string;
  metadata: Record<string, JsonValue>;
};

type RequestReplay = {
  request_id: string;
  trace_id: string;
  actor?: Actor | null;
  prompt?: string | null;
  sanitized_prompt?: string | null;
  redaction?: ChatResponse["redaction"] | null;
  policy_input: Record<string, JsonValue>;
  policy?: ChatResponse["policy"] | null;
  model_route?: ChatResponse["model_route"] | null;
  tool_calls: ChatResponse["tool_calls"];
  answer_sources: AnswerSource[];
  knowledge_citations: KnowledgeCitation[];
  trusted_source_score?: TrustedSourceScore | null;
  answer_preview?: string | null;
  audit_events: AuditEvent[];
};

type AbuseControls = {
  api_gateway_throttling_rate_limit: number;
  api_gateway_throttling_burst_limit: number;
  max_request_chars: number;
  quota_window_seconds: number;
  role_quotas: Record<string, number>;
  cloud_model_kill_switch: boolean;
  bedrock_enabled: boolean;
  request_body_limit_note: string;
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

type AuthActor = PersonaTokenResponse["actor"];

type HostedAuthConfig = {
  client_id: string;
  authorization_endpoint: string;
  logout_endpoint: string;
  scopes: string[];
};

type HostedLogin = {
  actor: AuthActor;
  username: string;
  password: string;
  config: HostedAuthConfig;
  authorizationUrl: string;
};

type OAuthExchangeResponse = {
  id_token: string;
  actor: AuthActor;
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
  const [abuseControls, setAbuseControls] = useState<AbuseControls | null>(null);
  const [selectedReplay, setSelectedReplay] = useState<RequestReplay | null>(null);
  const [isReplayLoading, setIsReplayLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [apiStatus, setApiStatus] = useState<"checking" | "ok" | "offline">("checking");
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [authActor, setAuthActor] = useState<AuthActor | null>(null);
  const [hostedLogin, setHostedLogin] = useState<HostedLogin | null>(null);
  const [authNotice, setAuthNotice] = useState("");
  const [isPreparingLogin, setIsPreparingLogin] = useState(false);
  const [walkthroughOpen, setWalkthroughOpen] = useState(false);
  const [walkthroughStep, setWalkthroughStep] = useState(0);
  const [eventFilters, setEventFilters] = useState({
    requestId: "",
    user: "",
    decision: "any",
    route: "any",
    tool: ""
  });

  const activeRole = authActor?.role ?? role;
  const canApprove = activeRole === "manager" || activeRole === "admin";
  const canManageState = activeRole === "admin";

  async function authHeaders(selectedRole = activeRole): Promise<HeadersInit> {
    if (authToken && authActor?.role === selectedRole) {
      return {
        Authorization: `Bearer ${authToken}`,
        "Content-Type": "application/json"
      };
    }

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

  async function refreshData(selectedRole = activeRole) {
    try {
      const headers = await authHeaders(selectedRole);
      const [healthRes, metricsRes, eventsRes, approvalsRes, controlsRes] = await Promise.all([
        fetch(`${API_BASE}/health`),
        fetch(`${API_BASE}/metrics/summary`, { headers }),
        fetch(`${API_BASE}/events`, { headers }),
        fetch(`${API_BASE}/approvals`, { headers }),
        fetch(`${API_BASE}/controls/abuse`, { headers })
      ]);

      setApiStatus(healthRes.ok ? "ok" : "offline");
      setMetrics(metricsRes.ok ? await metricsRes.json() : initialMetrics);
      setEvents(eventsRes.ok ? (await eventsRes.json()).events : []);
      setApprovals(approvalsRes.ok ? (await approvalsRes.json()).approvals : []);
      setAbuseControls(controlsRes.ok ? await controlsRes.json() : null);
    } catch {
      setApiStatus("offline");
    }
  }

  useEffect(() => {
    initializeHostedAuth();
  }, []);

  useEffect(() => {
    refreshData();
  }, [role, authToken]);

  async function initializeHostedAuth() {
    const params = new URLSearchParams(window.location.search);
    const error = params.get("error");
    const code = params.get("code");
    const state = params.get("state");

    if (error) {
      setAuthNotice(`Cognito sign-in failed: ${error}`);
      window.history.replaceState({}, document.title, window.location.pathname);
      return;
    }

    if (code) {
      const expectedState = sessionStorage.getItem(PKCE_STATE_KEY);
      const verifier = sessionStorage.getItem(PKCE_VERIFIER_KEY);
      const redirectUri = sessionStorage.getItem(PKCE_REDIRECT_KEY) ?? window.location.origin;

      if (!verifier || !expectedState || state !== expectedState) {
        setAuthNotice("Cognito callback could not be verified. Start sign-in again.");
        return;
      }

      try {
        const response = await fetch(`${API_BASE}/auth/oauth/exchange`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code, code_verifier: verifier, redirect_uri: redirectUri })
        });

        if (!response.ok) throw new Error("oauth_exchange_failed");

        const body = (await response.json()) as OAuthExchangeResponse;
        localStorage.setItem(AUTH_TOKEN_KEY, body.id_token);
        localStorage.setItem(AUTH_ACTOR_KEY, JSON.stringify(body.actor));
        sessionStorage.removeItem(PKCE_VERIFIER_KEY);
        sessionStorage.removeItem(PKCE_STATE_KEY);
        sessionStorage.removeItem(PKCE_REDIRECT_KEY);
        setAuthToken(body.id_token);
        setAuthActor(body.actor);
        setRole(body.actor.role);
        setAuthNotice("Signed in through Cognito Hosted UI. Backend API calls now use the Cognito ID token.");
      } catch {
        setAuthNotice("Cognito code exchange failed. Start sign-in again.");
      } finally {
        window.history.replaceState({}, document.title, window.location.pathname);
      }
      return;
    }

    const storedToken = localStorage.getItem(AUTH_TOKEN_KEY);
    const storedActor = localStorage.getItem(AUTH_ACTOR_KEY);
    if (storedToken && storedActor) {
      try {
        const actor = JSON.parse(storedActor) as AuthActor;
        setAuthToken(storedToken);
        setAuthActor(actor);
        setRole(actor.role);
      } catch {
        localStorage.removeItem(AUTH_TOKEN_KEY);
        localStorage.removeItem(AUTH_ACTOR_KEY);
      }
    }
  }

  async function prepareHostedLogin(selectedRole: Role) {
    setIsPreparingLogin(true);
    setAuthNotice("");
    try {
      const verifier = randomBase64Url(64);
      const state = randomBase64Url(32);
      const challenge = await pkceChallenge(verifier);
      const redirectUri = window.location.origin;
      const response = await fetch(`${API_BASE}/auth/hosted-ui-login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          role: selectedRole,
          team: selectedRole === "admin" ? "platform" : "payments"
        })
      });

      if (!response.ok) throw new Error("hosted_login_failed");

      const body = (await response.json()) as Omit<HostedLogin, "authorizationUrl">;
      const params = new URLSearchParams({
        client_id: body.config.client_id,
        code_challenge: challenge,
        code_challenge_method: "S256",
        login_hint: body.username,
        redirect_uri: redirectUri,
        response_type: "code",
        scope: body.config.scopes.join(" "),
        state
      });

      sessionStorage.setItem(PKCE_VERIFIER_KEY, verifier);
      sessionStorage.setItem(PKCE_STATE_KEY, state);
      sessionStorage.setItem(PKCE_REDIRECT_KEY, redirectUri);
      setHostedLogin({ ...body, authorizationUrl: `${body.config.authorization_endpoint}?${params.toString()}` });
      setRole(selectedRole);
      setAuthNotice("Reviewer credentials are ready. Open Cognito Hosted UI and sign in there.");
    } catch {
      setAuthNotice("Could not prepare Cognito Hosted UI sign-in.");
    } finally {
      setIsPreparingLogin(false);
    }
  }

  async function signOut() {
    const logoutEndpoint = await getHostedLogoutEndpoint();
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_ACTOR_KEY);
    setAuthToken(null);
    setAuthActor(null);
    setAuthNotice("Signed out locally.");

    if (logoutEndpoint) {
      const params = new URLSearchParams({
        client_id: logoutEndpoint.clientId,
        logout_uri: window.location.origin
      });
      window.location.assign(`${logoutEndpoint.url}?${params.toString()}`);
    }
  }

  async function getHostedLogoutEndpoint(): Promise<{ url: string; clientId: string } | null> {
    try {
      const response = await fetch(`${API_BASE}/auth/hosted-ui-config`);
      if (!response.ok) return null;
      const config = (await response.json()) as HostedAuthConfig;
      return { url: config.logout_endpoint, clientId: config.client_id };
    } catch {
      return null;
    }
  }

  function openHostedLogin() {
    if (hostedLogin) {
      window.location.assign(hostedLogin.authorizationUrl);
    }
  }

  async function submitMessage(text: string, selectedRole = activeRole) {
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

  async function loadReplay(requestId: string) {
    setIsReplayLoading(true);
    try {
      const headers = await authHeaders(activeRole);
      const response = await fetch(`${API_BASE}/requests/${requestId}/replay`, { headers });
      if (!response.ok) throw new Error("replay_failed");
      setSelectedReplay((await response.json()) as RequestReplay);
    } catch {
      setSelectedReplay(null);
    } finally {
      setIsReplayLoading(false);
    }
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

  async function decideApproval(approvalId: string, action: "approve" | "deny", selectedRole = activeRole) {
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

        <div className="identityPanel">
          <span>Identity</span>
          {authActor ? (
            <div className="signedIdentity">
              <strong>Cognito Hosted UI</strong>
              <small>{authActor.user_id}</small>
              <small>{authActor.role} - {authActor.team}</small>
              <button onClick={signOut} type="button">
                <LogOut size={15} />
                Sign out
              </button>
            </div>
          ) : (
            <>
              <div className="hostedButtons">
                {(["employee", "manager", "admin"] as Role[]).map((option) => (
                  <button disabled={isPreparingLogin} key={option} onClick={() => prepareHostedLogin(option)} type="button">
                    <LogIn size={15} />
                    {option}
                  </button>
                ))}
              </div>
              {hostedLogin && (
                <div className="credentialBox">
                  <strong>Cognito credentials</strong>
                  <span>{hostedLogin.username}</span>
                  <code>{hostedLogin.password}</code>
                  <button onClick={() => navigator.clipboard.writeText(`${hostedLogin.username}\n${hostedLogin.password}`)} type="button">
                    <Copy size={15} />
                    Copy
                  </button>
                  <button className="primaryMini" onClick={openHostedLogin} type="button">
                    <LogIn size={15} />
                    Open Hosted UI
                  </button>
                </div>
              )}
              <details className="shortcutPanel">
                <summary>Reviewer shortcut</summary>
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
              </details>
            </>
          )}
          {authNotice && <small className="authNotice">{authNotice}</small>}
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
                    {item.response?.trusted_source_score && <TrustedScore score={item.response.trusted_source_score} compact />}
                    {item.response?.answer_sources?.length ? <AnswerSources sources={item.response.answer_sources} /> : null}
                    {item.response?.knowledge_citations?.length ? (
                      <KnowledgeCitations citations={item.response.knowledge_citations} />
                    ) : null}
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
                      <span>{formatPermission(approval.permission)} access - {explainApprovalReason(approval.policy_reason)}</span>
                    </div>
                    <div className="approvalFacts">
                      <span><User size={14} /> Requester {approval.requester.user_id}</span>
                      <span><Clock size={14} /> Created {formatTime(approval.created_at)}</span>
                      <span><Database size={14} /> Request {approval.request_id}</span>
                      {approval.decided_by && <span><Check size={14} /> {approval.decided_by} at {formatTime(approval.decided_at)}</span>}
                    </div>
                    <ApprovalTimeline
                      approval={approval}
                      events={events.filter((event) => event.request_id === approval.request_id)}
                      showTechnical={activeRole === "admin"}
                    />
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
            <Metric icon={DollarSign} label="Spend" value={formatUsd(metrics.estimated_spend_usd)} />
            <Metric icon={Lock} label="Redactions" value={metrics.redactions_total} />
            <Metric icon={AlertTriangle} label="Denied" value={metrics.denied_actions} />
            <Metric icon={KeyRound} label="Pending" value={metrics.approvals_pending} />
            <Metric icon={ClipboardList} label="Tools" value={metrics.tool_calls_total} />
            {abuseControls && <AbuseControlsPanel controls={abuseControls} />}

            <section className="panel eventPanel">
              <div className="sectionHeader">
                <h2>Audit Event Explorer</h2>
                <span>{filteredEvents.length} of {events.length} shown</span>
              </div>
              <EventFilters filters={eventFilters} onChange={setEventFilters} />
              <div className="eventExplorerLayout">
                <div className="eventList">
                  {filteredEvents.length === 0 && <div className="emptyRow">No matching audit events.</div>}
                  {filteredEvents.map((event) => (
                    <button
                      className={selectedReplay?.request_id === event.request_id ? "eventItem selected" : "eventItem"}
                      key={event.event_id}
                      onClick={() => loadReplay(event.request_id)}
                      type="button"
                    >
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
                    </button>
                  ))}
                </div>
                <RequestReplayPanel isLoading={isReplayLoading} replay={selectedReplay} />
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

function TrustedScore({ score, compact = false }: { score: TrustedSourceScore; compact?: boolean }) {
  const tone = score.score >= 80 ? "good" : score.score >= 60 ? "warn" : "bad";
  const facts = [
    score.trusted_source_found ? "Trusted source found" : "No trusted source",
    `Freshness: ${score.source_freshness}`,
    score.external_model_used ? "External model used" : "No external model",
    score.sensitive_data_sent_externally ? "Sensitive external data" : "No sensitive external data",
    `Policy: ${score.policy_result}`
  ];

  return (
    <div className={compact ? "trustScore compact" : "trustScore"}>
      <div className="trustScoreHeader">
        <div>
          <ShieldCheck size={16} />
          <strong>Trusted source score</strong>
        </div>
        <Badge tone={tone}>{score.score}/100</Badge>
      </div>
      <div className="trustFacts">
        {facts.map((fact) => (
          <span key={fact}>{fact}</span>
        ))}
      </div>
      {!compact && (
        <ul>
          {score.rationale.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function AbuseControlsPanel({ controls }: { controls: AbuseControls }) {
  return (
    <section className="panel abusePanel">
      <div className="sectionHeader">
        <h2>Abuse Controls</h2>
        <Badge tone={controls.cloud_model_kill_switch ? "bad" : "good"}>
          {controls.cloud_model_kill_switch ? "kill switch on" : "cloud route enabled"}
        </Badge>
      </div>
      <div className="abuseGrid">
        <div>
          <span>API Gateway throttle</span>
          <strong>{controls.api_gateway_throttling_rate_limit}/sec</strong>
          <small>Burst {controls.api_gateway_throttling_burst_limit}</small>
        </div>
        <div>
          <span>Request size limit</span>
          <strong>{controls.max_request_chars.toLocaleString()} chars</strong>
          <small>Rejected before model routing</small>
        </div>
        <div>
          <span>Role quotas</span>
          <strong>{Object.entries(controls.role_quotas).map(([role, limit]) => `${role} ${limit}`).join(" / ")}</strong>
          <small>{formatQuotaWindow(controls.quota_window_seconds)}</small>
        </div>
        <div>
          <span>Bedrock access</span>
          <strong>{controls.bedrock_enabled ? "Enabled" : "Disabled"}</strong>
          <small>{controls.request_body_limit_note}</small>
        </div>
      </div>
    </section>
  );
}

function RequestReplayPanel({ replay, isLoading }: { replay: RequestReplay | null; isLoading: boolean }) {
  if (isLoading) {
    return (
      <aside className="replayPanel">
        <strong>Loading request replay...</strong>
      </aside>
    );
  }

  if (!replay) {
    return (
      <aside className="replayPanel emptyReplay">
        <strong>Request replay</strong>
        <span>Click any audit event to inspect the prompt, redaction, policy, route, tool calls, sources, and trace.</span>
      </aside>
    );
  }

  return (
    <aside className="replayPanel">
      <div className="replayHeader">
        <div>
          <strong>Request replay</strong>
          <span>{replay.request_id}</span>
        </div>
        <Badge tone="neutral">{replay.actor?.role ?? "unknown"}</Badge>
      </div>
      {replay.trusted_source_score && <TrustedScore score={replay.trusted_source_score} />}
      <ReplayBlock title="Prompt stored for replay" value={replay.sanitized_prompt ?? replay.prompt ?? "Unavailable"} />
      <ReplayBlock title="Answer preview" value={replay.answer_preview ?? "Unavailable"} />
      <div className="replayFacts">
        <span>Trace ID <strong>{replay.trace_id}</strong></span>
        <span>Redaction <strong>{describeReplayRedaction(replay)}</strong></span>
        <span>Model route <strong>{replay.model_route ? `${replay.model_route.provider} / ${replay.model_route.model}` : "unknown"}</strong></span>
        <span>Tool calls <strong>{replay.tool_calls.length ? replay.tool_calls.map((tool) => tool.name).join(", ") : "none"}</strong></span>
      </div>
      <details className="replayDetails" open>
        <summary>Policy input and output</summary>
        <pre>{formatJson({ input: replay.policy_input, output: replay.policy })}</pre>
      </details>
      <details className="replayDetails">
        <summary>Answer sources</summary>
        <pre>{formatJson({ sources: replay.answer_sources, citations: replay.knowledge_citations })}</pre>
      </details>
      <details className="replayDetails">
        <summary>Audit events</summary>
        <div className="auditMiniList">
          {replay.audit_events.map((event) => (
            <div key={event.event_id}>
              <Badge tone={event.event_type.includes("denied") || event.event_type.includes("blocked") ? "bad" : "neutral"}>
                {event.event_type}
              </Badge>
              <span>{event.summary}</span>
            </div>
          ))}
        </div>
      </details>
    </aside>
  );
}

function ReplayBlock({ title, value }: { title: string; value: string }) {
  return (
    <div className="replayBlock">
      <span>{title}</span>
      <p>{value}</p>
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

function AnswerSources({ sources }: { sources: AnswerSource[] }) {
  return (
    <div className="answerSources">
      <div className="sourceHeader">
        <ListFilter size={16} />
        <strong>Answer sources</strong>
      </div>
      {sources.map((source) => (
        <div className="sourceRow" key={`${source.kind}-${source.name}`}>
          <Badge tone={source.kind === "model" ? "warn" : source.kind === "policy" ? "neutral" : "good"}>
            {source.kind.replaceAll("_", " ")}
          </Badge>
          <div>
            <strong>{source.name}</strong>
            <span>{source.detail}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function KnowledgeCitations({ citations }: { citations: KnowledgeCitation[] }) {
  return (
    <div className="knowledgeCitations">
      <div className="sourceHeader">
        <ClipboardList size={16} />
        <strong>Trusted citations</strong>
      </div>
      {citations.map((citation) => (
        <div className="citationRow" key={citation.doc_id}>
          <div>
            <strong>{citation.title}</strong>
            <span>{citation.doc_id} - {citation.section} - {citation.source_path}</span>
          </div>
          <p>{citation.excerpt}</p>
        </div>
      ))}
    </div>
  );
}

function DecisionTrail({ response }: { response: ChatResponse }) {
  const plainDecision = explainDecision(response);
  const redaction = response.redaction.findings.length
    ? response.redaction.findings.map((finding) => finding.kind).join(", ")
    : "No sensitive values detected.";
  const sourceSummary = response.answer_sources?.length
    ? response.answer_sources.map((source) => source.name).join(" + ")
    : "No source metadata returned.";

  return (
    <div className="decisionStack">
      <DecisionItem label="Decision" value={plainDecision} emphasis />
      <DecisionItem label="Answer source" value={sourceSummary} />
      {response.trusted_source_score && (
        <DecisionItem label="Trusted source score" value={`${response.trusted_source_score.score}/100 - ${response.trusted_source_score.source_freshness}`} />
      )}
      <DecisionItem label="Technical policy" value={`${response.policy.policy_name}: ${response.policy.reason}`} />
      <DecisionItem label="Route" value={explainRoute(response)} />
      <DecisionItem label="Redaction" value={redaction} />
      <DecisionItem label="Cost" value={formatUsd(response.model_route.estimated_cost_usd)} />
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

function ApprovalTimeline({
  approval,
  events,
  showTechnical
}: {
  approval: Approval;
  events: AuditEvent[];
  showTechnical: boolean;
}) {
  const requested = events.find((event) => event.event_type === "approval.requested");
  const decided = events.find((event) => event.event_type === "approval.granted" || event.event_type === "approval.denied");
  const decisionLabel =
    approval.status === "pending"
      ? "Waiting for manager decision."
      : `${capitalize(approval.status)} by ${approval.decided_by ?? "manager"} at ${formatTime(approval.decided_at)}.`;
  const requestLabel = `Temporary ${formatPermission(approval.permission)} access requested for ${approval.resource}. Manager approval is required before access is granted.`;

  return (
    <div className="approvalTimeline">
      <strong>Approval timeline</strong>
      <div className="timelineItem">
        <Clock size={15} />
        <div>
          <span>Request opened</span>
          <p>{requestLabel}</p>
        </div>
      </div>
      <div className="timelineItem">
        {approval.status === "approved" ? <Check size={15} /> : approval.status === "denied" ? <X size={15} /> : <Clock size={15} />}
        <div>
          <span>{approval.status === "pending" ? "Current status" : "Decision"}</span>
          <p>{decisionLabel}</p>
        </div>
      </div>
      {showTechnical && (
        <details className="technicalTrail">
          <summary>Technical audit details</summary>
          <code>{requested?.event_type ?? "approval.requested"}</code>
          <code>{decided?.event_type ?? "decision.pending"}</code>
          <code>{approval.request_id}</code>
        </details>
      )}
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

function describeReplayRedaction(replay: RequestReplay) {
  if (!replay.redaction) return "unknown";
  if (replay.redaction.secrets_detected && replay.redaction.pii_detected) return "secret and PII removed";
  if (replay.redaction.secrets_detected) return "secret removed";
  if (replay.redaction.pii_detected) return "PII removed";
  return "none";
}

function formatJson(value: unknown) {
  return JSON.stringify(value, null, 2);
}

function formatQuotaWindow(seconds: number) {
  if (seconds >= 86400) return `${Math.round(seconds / 86400)} day window`;
  if (seconds >= 3600) return `${Math.round(seconds / 3600)} hour window`;
  return `${seconds} second window`;
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

function formatUsd(value: number) {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(value);
}

function capitalize(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function formatPermission(value: string) {
  return value.replaceAll("_", " ");
}

function explainApprovalReason(reason: string) {
  if (reason === "temporary_production_access_requires_manager_approval") {
    return "Manager approval required for temporary production access.";
  }
  return reason.replaceAll("_", " ");
}

function randomBase64Url(byteLength: number) {
  const bytes = new Uint8Array(byteLength);
  window.crypto.getRandomValues(bytes);
  return base64Url(bytes);
}

async function pkceChallenge(verifier: string) {
  const digest = await window.crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  return base64Url(new Uint8Array(digest));
}

function base64Url(bytes: Uint8Array) {
  let binary = "";
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });
  return window.btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
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
