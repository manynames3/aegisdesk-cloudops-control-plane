"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  ArrowLeft,
  Check,
  ChevronRight,
  FileText,
  Plus,
  RefreshCw,
  Search,
  Send,
  ShieldCheck,
  X,
} from "lucide-react";

type Identity = { user_id: string; role: string; team: string };
type Action = {
  action_id: string;
  operation: string;
  target: string;
  arguments: Record<string, string>;
  requester: Identity;
  state: string;
  fingerprint: string;
  action_version: number;
  expires_at: string;
  policy: { decision: string; reason: string };
  approval: { approver: Identity; approved_at: string } | null;
  outcome: { ticket_id?: string; external_url?: string; error?: string } | null;
};
type Incident = {
  incident_id: string;
  title: string;
  description: string;
  severity: string;
  service: string;
  resource: string;
  environment: string;
  owner: string;
  team: string;
  status: string;
  created_at: string;
  updated_at: string;
  version: number;
  evidence_state: string;
  evidence_error: string | null;
  evidence_checked_at: string | null;
  evidence: {
    loaded_at: string;
    lookback_minutes: number;
    region: string;
    context: {
      source: string;
      log_group: string;
      query: string;
      suspected_cause: string;
      entries: {
        timestamp: string;
        service: string;
        level: string;
        message: string;
      }[];
    };
  } | null;
  runbooks: {
    doc_id: string;
    title: string;
    excerpt: string;
    source_path: string;
    last_reviewed: string;
  }[];
  notes: { text: string; kind: string; author: string; timestamp: string }[];
  actions: Action[];
  external_ticket: { ticket_id: string; external_url: string } | null;
  timeline: {
    event_id: string;
    event: string;
    timestamp: string;
    actor: Identity;
    trace_id: string;
    correlation_id: string;
    detail: Record<string, unknown>;
  }[];
};
type Section =
  "Overview" | "Evidence" | "Investigation" | "Actions" | "Ticket" | "Timeline";
const label = (value: string) => value.replaceAll("_", " ");
const timestamp = (value: string) => new Date(value).toLocaleString();

export function IncidentWorkspace({
  apiBase,
  headers,
  identityKey,
  mode = "incidents",
}: {
  apiBase: string;
  headers: () => Promise<HeadersInit>;
  identityKey: string;
  mode?: "incidents" | "investigations" | "actions" | "runbooks";
}) {
  const [cases, setCases] = useState<Incident[] | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [section, setSection] = useState<Section>(
    mode === "actions" ? "Actions" : "Overview",
  );
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [severity, setSeverity] = useState("");
  const [service, setService] = useState("");
  const [environment, setEnvironment] = useState("");
  const [owner, setOwner] = useState("");
  const [sort, setSort] = useState("updated_at");
  const [creating, setCreating] = useState(false);
  const [note, setNote] = useState("");
  const [kind, setKind] = useState("note");
  const [ticketKey, setTicketKey] = useState("");
  const selected = cases?.find((item) => item.incident_id === selectedId);

  async function request<T>(
    path: string,
    method = "GET",
    body?: unknown,
  ): Promise<T> {
    const response = await fetch(`${apiBase}${path}`, {
      method,
      headers: await headers(),
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const data = await response.json();
    if (!response.ok)
      throw new Error(
        `${response.status === 403 ? "Permission denied: " : ""}${label(String(data.detail ?? `API ${response.status}`))}${data.error_id ? ` (${data.error_id})` : ""}`,
      );
    return data;
  }

  async function refresh() {
    setLoading(true);
    setError("");
    try {
      setCases(
        (await request<{ incidents: Incident[] }>("/incidents")).incidents,
      );
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : "Incident queue unavailable",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    setCases(null);
    setSelectedId(null);
    void refresh();
  }, [identityKey]);

  useEffect(() => {
    if (!creating) return;
    const previous = document.activeElement as HTMLElement | null;
    const dialog = document.querySelector<HTMLElement>(".incidentModal");
    dialog?.querySelector<HTMLInputElement>("input")?.focus();
    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setCreating(false);
        return;
      }
      if (event.key !== "Tab" || !dialog) return;
      const controls = Array.from(
        dialog.querySelectorAll<HTMLElement>(
          "button:not(:disabled), input, textarea, select",
        ),
      );
      const first = controls[0],
        last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    }
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("keydown", handleKey);
      previous?.focus();
    };
  }, [creating]);

  async function mutate(
    path: string,
    extra: Record<string, unknown> = {},
    method = "POST",
  ) {
    if (!selected) return;
    setBusy(true);
    setError("");
    try {
      const updated = await request<Incident>(
        `/incidents/${selected.incident_id}${path}`,
        method,
        { version: selected.version, ...extra },
      );
      setCases(
        (current) =>
          current?.map((item) =>
            item.incident_id === updated.incident_id ? updated : item,
          ) ?? [updated],
      );
      return true;
    } catch (failure) {
      setError(
        failure instanceof Error ? failure.message : "Action unavailable",
      );
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    setBusy(true);
    setError("");
    try {
      const incident = await request<Incident>("/incidents", "POST", data);
      setCases((current) => [incident, ...(current ?? [])]);
      setSelectedId(incident.incident_id);
      setCreating(false);
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : "Could not create incident",
      );
    } finally {
      setBusy(false);
    }
  }

  const filtered = useMemo(
    () =>
      (cases ?? [])
        .filter(
          (item) =>
            `${item.title} ${item.incident_id} ${item.resource}`
              .toLowerCase()
              .includes(query.toLowerCase()) &&
            (!severity || item.severity === severity) &&
            (!service || item.service === service) &&
            (!environment || item.environment === environment) &&
            (!owner || item.owner === owner) &&
            (mode !== "investigations" || item.status !== "resolved") &&
            (mode !== "actions" || item.actions.length > 0),
        )
        .sort((a, b) =>
          sort === "severity"
            ? ["critical", "high", "medium", "low"].indexOf(a.severity) -
              ["critical", "high", "medium", "low"].indexOf(b.severity)
            : b.updated_at.localeCompare(a.updated_at),
        ),
    [cases, query, severity, service, environment, owner, sort, mode],
  );

  return (
    <div className="incidentWorkspace">
      {error && (
        <div className="incidentError" role="alert">
          {error}
          <button
            type="button"
            onClick={() => void refresh()}
            disabled={loading || busy}
          >
            <RefreshCw size={15} />
            Refresh
          </button>
        </div>
      )}
      {loading && <p role="status">Loading incident cases...</p>}
      {!selected && (
        <>
          <div className="incidentToolbar">
            <div>
              <h2>
                {mode === "actions"
                  ? "Incident actions"
                  : mode === "runbooks"
                    ? "Related runbooks"
                    : "Incident queue"}
              </h2>
              <span>
                {cases === null
                  ? "Operational data unavailable"
                  : `${cases.length} team cases`}
                {error && cases ? " - previously loaded data" : ""}
              </span>
            </div>
            <div className="incidentCommands">
              <button
                type="button"
                title="Refresh incident queue"
                aria-label="Refresh incident queue"
                disabled={loading}
                onClick={() => void refresh()}
              >
                <RefreshCw size={16} />
              </button>
              <button type="button" onClick={() => setCreating(true)}>
                <Plus size={16} />
                New incident
              </button>
            </div>
          </div>
          {cases && mode !== "runbooks" && (
            <>
              <dl className="incidentCounts">
                <div>
                  <dt>Active</dt>
                  <dd>
                    {cases.filter((item) => item.status !== "resolved").length}
                  </dd>
                </div>
                <div>
                  <dt>Needs attention</dt>
                  <dd>
                    {
                      cases.filter(
                        (item) =>
                          item.severity === "critical" ||
                          item.actions.some((action) =>
                            [
                              "failed",
                              "outcome_uncertain",
                              "executing",
                            ].includes(action.state),
                          ),
                      ).length
                    }
                  </dd>
                </div>
                <div>
                  <dt>Pending approvals</dt>
                  <dd>
                    {
                      cases
                        .flatMap((item) => item.actions)
                        .filter((action) => action.state === "pending_approval")
                        .length
                    }
                  </dd>
                </div>
                <div>
                  <dt>Resolved</dt>
                  <dd>
                    {cases.filter((item) => item.status === "resolved").length}
                  </dd>
                </div>
              </dl>
              <div className="incidentFilters">
                <label className="incidentSearch">
                  <Search size={16} />
                  <input
                    aria-label="Search incidents"
                    placeholder="Search incidents"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                  />
                </label>
                <select
                  aria-label="Severity filter"
                  value={severity}
                  onChange={(event) => setSeverity(event.target.value)}
                >
                  <option value="">All severities</option>
                  {["critical", "high", "medium", "low"].map((value) => (
                    <option key={value}>{value}</option>
                  ))}
                </select>
                {(
                  [
                    ["Service", service, setService, "service"],
                    ["Environment", environment, setEnvironment, "environment"],
                    ["Owner", owner, setOwner, "owner"],
                  ] as const
                ).map(([name, value, setter, field]) => (
                  <select
                    aria-label={`${name} filter`}
                    key={name}
                    value={value}
                    onChange={(event) => setter(event.target.value)}
                  >
                    <option value="">All {name.toLowerCase()}s</option>
                    {Array.from(new Set(cases.map((item) => item[field]))).map(
                      (option) => (
                        <option key={option}>{option}</option>
                      ),
                    )}
                  </select>
                ))}
                <select
                  aria-label="Sort incidents"
                  value={sort}
                  onChange={(event) => setSort(event.target.value)}
                >
                  <option value="updated_at">Last updated</option>
                  <option value="severity">Severity</option>
                </select>
              </div>
              <div className="incidentTableScroll">
                <table className="incidentTable">
                  <thead>
                    <tr>
                      <th>Incident</th>
                      <th>Severity</th>
                      <th>Service / environment</th>
                      <th>Status</th>
                      <th>Owner</th>
                      <th>Last update</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((item) => (
                      <tr key={item.incident_id}>
                        <td>
                          <button
                            type="button"
                            className="incidentLink"
                            onClick={() => {
                              setSelectedId(item.incident_id);
                              setSection(
                                mode === "actions" ? "Actions" : "Overview",
                              );
                            }}
                          >
                            <small>{item.incident_id}</small>
                            <strong>{item.title}</strong>
                          </button>
                        </td>
                        <td>
                          <span
                            className={`incidentBadge severity-${item.severity}`}
                          >
                            {item.severity}
                          </span>
                        </td>
                        <td>
                          {item.service}
                          <small>{item.environment}</small>
                        </td>
                        <td>
                          <span className="incidentBadge">
                            {label(item.status)}
                          </span>
                        </td>
                        <td>{item.owner}</td>
                        <td>{timestamp(item.updated_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {filtered.length === 0 && !loading && (
                <p className="incidentEmpty">
                  {cases.length
                    ? "No incidents match these filters."
                    : "No incident cases in this team."}
                </p>
              )}
            </>
          )}
          {mode === "runbooks" &&
            cases &&
            Array.from(
              new Map(
                cases
                  .flatMap((item) => item.runbooks)
                  .map((book) => [book.doc_id, book]),
              ).values(),
            ).map((book) => (
              <article className="incidentRunbook" key={book.doc_id}>
                <h3>
                  <FileText size={16} />
                  {book.title}
                </h3>
                <p>{book.excerpt}</p>
                <small>
                  {book.doc_id} / {book.source_path} / Reviewed{" "}
                  {book.last_reviewed}
                </small>
              </article>
            ))}
          {mode === "runbooks" && cases?.length === 0 && (
            <p>No case-linked runbooks yet.</p>
          )}
        </>
      )}
      {selected && (
        <>
          <button
            className="incidentBack"
            type="button"
            onClick={() => setSelectedId(null)}
          >
            <ArrowLeft size={16} />
            Incident queue
          </button>
          <header className="incidentHeader">
            <div>
              <p>
                {selected.incident_id} / {selected.team}
              </p>
              <h2>{selected.title}</h2>
              <span>
                {selected.service} / {selected.environment} /{" "}
                {selected.resource}
              </span>
            </div>
            <div>
              <span className={`incidentBadge severity-${selected.severity}`}>
                {selected.severity}
              </span>
              <span className="incidentBadge">{label(selected.status)}</span>
            </div>
          </header>
          <div className="incidentMetadata">
            <span>Owner: {selected.owner}</span>
            <span>Opened {timestamp(selected.created_at)}</span>
            <span>Updated {timestamp(selected.updated_at)}</span>
          </div>
          <nav className="incidentSections" aria-label="Incident sections">
            {(
              [
                "Overview",
                "Evidence",
                "Investigation",
                "Actions",
                "Ticket",
                "Timeline",
              ] as Section[]
            ).map((item) => (
              <button
                type="button"
                key={item}
                aria-current={section === item ? "page" : undefined}
                onClick={() => setSection(item)}
              >
                {item}
              </button>
            ))}
          </nav>
          {section === "Overview" && (
            <div className="incidentSplit">
              <section>
                <h3>Incident summary</h3>
                <p>{selected.description}</p>
                <div className="incidentCommands">
                  {["open", "resolved", "mitigating"].includes(
                    selected.status,
                  ) && (
                    <button
                      disabled={busy}
                      type="button"
                      onClick={() =>
                        void mutate("", { status: "investigating" }, "PATCH")
                      }
                    >
                      <ChevronRight size={16} />
                      {selected.status === "resolved"
                        ? "Reopen investigation"
                        : "Investigate"}
                    </button>
                  )}
                  {["investigating", "mitigating"].includes(
                    selected.status,
                  ) && (
                    <button
                      disabled={busy}
                      type="button"
                      onClick={() => {
                        if (
                          window.confirm(
                            "Resolve this incident? Confirm mitigation was verified outside AegisDesk.",
                          )
                        )
                          void mutate("", { status: "resolved" }, "PATCH");
                      }}
                    >
                      <Check size={16} />
                      Resolve incident
                    </button>
                  )}
                </div>
                <h3>Operational evidence</h3>
                <p>
                  {label(selected.evidence_state)}
                  {selected.evidence?.loaded_at
                    ? ` - collected ${timestamp(selected.evidence.loaded_at)}`
                    : " - no collected CloudWatch evidence"}
                </p>
                <p>{selected.evidence_error}</p>
              </section>
              <aside>
                <h3>Supporting runbooks</h3>
                {selected.runbooks.map((book) => (
                  <article className="incidentRunbook" key={book.doc_id}>
                    <h4>{book.title}</h4>
                    <p>{book.excerpt}</p>
                    <small>
                      {book.doc_id} / Reviewed {book.last_reviewed}
                    </small>
                  </article>
                ))}
              </aside>
            </div>
          )}
          {section === "Evidence" && (
            <section>
              <div className="incidentToolbar">
                <h3>CloudWatch evidence</h3>
                <button
                  disabled={busy}
                  type="button"
                  onClick={() => void mutate("/evidence")}
                >
                  <RefreshCw size={16} />
                  Refresh evidence
                </button>
              </div>
              <p role="status">
                {busy ? "Loading evidence..." : label(selected.evidence_state)}
                {selected.evidence_checked_at &&
                  ` - checked ${timestamp(selected.evidence_checked_at)}`}
              </p>
              {selected.evidence_error && (
                <p className="incidentError">{selected.evidence_error}</p>
              )}
              {selected.evidence && (
                <>
                  <dl className="incidentFacts">
                    <dt>Source</dt>
                    <dd>{selected.evidence.context.source}</dd>
                    <dt>Log group</dt>
                    <dd>{selected.evidence.context.log_group}</dd>
                    <dt>Region / window</dt>
                    <dd>
                      {selected.evidence.region} /{" "}
                      {selected.evidence.lookback_minutes} minutes before
                      collection
                    </dd>
                    <dt>Collected</dt>
                    <dd>{timestamp(selected.evidence.loaded_at)}</dd>
                  </dl>
                  <details>
                    <summary>Query details</summary>
                    <pre>{selected.evidence.context.query}</pre>
                  </details>
                  <div className="incidentLogs">
                    {selected.evidence.context.entries.map((entry, index) => (
                      <article key={index}>
                        <small>
                          {entry.timestamp} / {entry.service} / {entry.level}
                        </small>
                        <pre>{entry.message}</pre>
                      </article>
                    ))}
                  </div>
                  {selected.evidence.context.entries.length === 0 && (
                    <p>No matching events in the queried window.</p>
                  )}
                  <p className="incidentHint">
                    Unverified heuristic:{" "}
                    {selected.evidence.context.suspected_cause}
                  </p>
                </>
              )}
            </section>
          )}
          {section === "Investigation" && (
            <section>
              <h3>Findings and next steps</h3>
              {selected.notes.map((item, index) => (
                <article className="incidentNote" key={index}>
                  <span className="incidentBadge">
                    {label(item.kind)} / operator supplied
                  </span>
                  <p>{item.text}</p>
                  <small>
                    {item.author} / {timestamp(item.timestamp)}
                  </small>
                </article>
              ))}
              <form
                className="incidentNoteForm"
                onSubmit={async (event) => {
                  event.preventDefault();
                  if (await mutate("/notes", { text: note, kind })) setNote("");
                }}
              >
                <label>
                  Entry type
                  <select
                    value={kind}
                    onChange={(event) => setKind(event.target.value)}
                  >
                    <option value="note">Investigation note</option>
                    <option value="hypothesis">Unverified hypothesis</option>
                    <option value="next_step">Recommended next step</option>
                  </select>
                </label>
                <label>
                  Investigation entry
                  <textarea
                    required
                    maxLength={4000}
                    value={note}
                    onChange={(event) => setNote(event.target.value)}
                  />
                </label>
                <button type="submit" disabled={busy}>
                  <Send size={16} />
                  Add entry
                </button>
              </form>
            </section>
          )}
          {section === "Actions" && (
            <section>
              <div className="incidentToolbar">
                <h3>Governed responses</h3>
                <button
                  disabled={
                    busy || !["open", "investigating"].includes(selected.status)
                  }
                  type="button"
                  onClick={() => {
                    if (
                      window.confirm(
                        "Propose a Jira ticket for this incident? An independent team manager must approve the exact action before dispatch.",
                      )
                    )
                      void mutate("/actions");
                  }}
                >
                  <Plus size={16} />
                  Propose Jira ticket
                </button>
              </div>
              {selected.actions.length === 0 && <p>No proposed actions.</p>}
              {selected.actions.map((action) => (
                <article className="incidentAction" key={action.action_id}>
                  <div className="incidentToolbar">
                    <h4>{action.operation}</h4>
                    <span className="incidentBadge">{label(action.state)}</span>
                  </div>
                  <dl className="incidentFacts">
                    <dt>Target</dt>
                    <dd>{action.target}</dd>
                    <dt>Requested by</dt>
                    <dd>
                      {action.requester.user_id} / {action.requester.role} /{" "}
                      {action.requester.team}
                    </dd>
                    <dt>Ticket title</dt>
                    <dd>{action.arguments.title}</dd>
                    <dt>Team / severity</dt>
                    <dd>
                      {action.arguments.team} / {action.arguments.severity}
                    </dd>
                    <dt>Policy</dt>
                    <dd>
                      {action.policy.decision}: {label(action.policy.reason)}
                    </dd>
                    <dt>Expires</dt>
                    <dd>{timestamp(action.expires_at)}</dd>
                    <dt>Approved by</dt>
                    <dd>
                      {action.approval
                        ? `${action.approval.approver.user_id} at ${timestamp(action.approval.approved_at)}`
                        : "Awaiting independent approval"}
                    </dd>
                  </dl>
                  <details>
                    <summary>Exact arguments and provenance</summary>
                    <pre>{JSON.stringify(action.arguments, null, 2)}</pre>
                    <p>Action version {action.action_version}</p>
                    <code>{action.fingerprint}</code>
                  </details>
                  {action.outcome?.error && (
                    <p role="status">{label(action.outcome.error)}</p>
                  )}
                  <div className="incidentCommands">
                    {action.state === "proposed" && (
                      <button
                        disabled={busy}
                        type="button"
                        onClick={() =>
                          void mutate(
                            `/actions/${action.action_id}/request-approval`,
                          )
                        }
                      >
                        <ShieldCheck size={16} />
                        Request approval
                      </button>
                    )}
                    {action.state === "pending_approval" && (
                      <button
                        disabled={busy}
                        type="button"
                        onClick={() => {
                          if (
                            window.confirm(
                              `Approve ${action.operation} on ${action.target} with the displayed arguments?`,
                            )
                          )
                            void mutate(`/actions/${action.action_id}/approve`);
                        }}
                      >
                        <ShieldCheck size={16} />
                        Approve exact action
                      </button>
                    )}
                    {action.state === "approved" && (
                      <button
                        disabled={busy}
                        type="button"
                        onClick={() => {
                          if (
                            window.confirm(
                              "Dispatch this approved ticket creation to Jira now?",
                            )
                          )
                            void mutate(`/actions/${action.action_id}/execute`);
                        }}
                      >
                        <Send size={16} />
                        Execute approved action
                      </button>
                    )}
                    {["proposed", "pending_approval", "approved"].includes(
                      action.state,
                    ) && (
                      <button
                        disabled={busy}
                        type="button"
                        onClick={() =>
                          void mutate(`/actions/${action.action_id}/cancel`)
                        }
                      >
                        <X size={16} />
                        Cancel action
                      </button>
                    )}
                  </div>
                  {["outcome_uncertain", "executing"].includes(
                    action.state,
                  ) && (
                    <form
                      className="incidentReconcile"
                      onSubmit={(event) => {
                        event.preventDefault();
                        void mutate(`/actions/${action.action_id}/reconcile`, {
                          ticket_key: ticketKey,
                        });
                      }}
                    >
                      <label>
                        Jira key to verify
                        <input
                          required
                          pattern="[A-Z][A-Z0-9_]*-[0-9]+"
                          value={ticketKey}
                          onChange={(event) => setTicketKey(event.target.value)}
                          placeholder="OPS-123"
                        />
                      </label>
                      <button disabled={busy} type="submit">
                        <RefreshCw size={16} />
                        Reconcile outcome
                      </button>
                    </form>
                  )}
                </article>
              ))}
            </section>
          )}
          {section === "Ticket" && (
            <section>
              <h3>External ticket</h3>
              {selected.external_ticket ? (
                <a
                  href={selected.external_ticket.external_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  {selected.external_ticket.ticket_id}
                </a>
              ) : (
                <p>
                  No verified external ticket. Approval alone does not create a
                  ticket.
                </p>
              )}
            </section>
          )}
          {section === "Timeline" && (
            <section>
              <h3>Investigation timeline</h3>
              <ol className="incidentTimeline">
                {selected.timeline.map((event) => (
                  <li key={event.event_id}>
                    <strong>{label(event.event.replaceAll(".", " "))}</strong>
                    <small>
                      {timestamp(event.timestamp)} / {event.actor.user_id}
                    </small>
                    <details>
                      <summary>Decision details</summary>
                      <pre>{JSON.stringify(event.detail, null, 2)}</pre>
                      <code>Trace: {event.trace_id}</code>
                      <p>
                        <code>Request correlation: {event.correlation_id}</code>
                      </p>
                    </details>
                  </li>
                ))}
              </ol>
            </section>
          )}
        </>
      )}
      {creating && (
        <div className="incidentModalBackdrop">
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="newIncidentTitle"
            className="incidentModal"
          >
            <div className="incidentToolbar">
              <h2 id="newIncidentTitle">New incident</h2>
              <button
                type="button"
                aria-label="Close new incident"
                onClick={() => setCreating(false)}
              >
                <X size={18} />
              </button>
            </div>
            <form onSubmit={create} className="incidentCreateForm">
              {[
                ["title", "Title", 160],
                ["description", "Description", 4000],
                ["service", "AWS service", 100],
                ["resource", "Affected resource", 300],
                ["environment", "Environment", 80],
                ["evidence_filter", "Log search reference (optional)", 80],
              ].map(([name, title, length]) => (
                <label key={name}>
                  {title}
                  {name === "description" ? (
                    <textarea
                      required
                      name={String(name)}
                      maxLength={Number(length)}
                    />
                  ) : (
                    <input
                      autoFocus={name === "title"}
                      required={name !== "evidence_filter"}
                      name={String(name)}
                      maxLength={Number(length)}
                    />
                  )}
                </label>
              ))}
              <label>
                Severity
                <select name="severity" defaultValue="medium">
                  {["critical", "high", "medium", "low"].map((value) => (
                    <option key={value}>{value}</option>
                  ))}
                </select>
              </label>
              {error && <p role="alert">{error}</p>}
              <button type="submit" disabled={busy}>
                <Plus size={16} />
                Create incident
              </button>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}
