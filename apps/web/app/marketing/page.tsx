import {
  ArrowRight,
  BadgeDollarSign,
  Bot,
  Building2,
  CheckCircle2,
  CloudCog,
  FileText,
  GitBranch,
  KeyRound,
  Layers3,
  LockKeyhole,
  MessageSquare,
  Network,
  ShieldCheck,
  Siren,
  Sparkles
} from "lucide-react";

const useCases = [
  {
    icon: Siren,
    title: "Incident Triage",
    text: "Employees ask for help on live service issues while the control plane attaches runbooks, operational context, redacts secrets, and records the decision trail."
  },
  {
    icon: KeyRound,
    title: "Production Access",
    text: "Unsafe admin requests are denied, safer scoped requests move through approval, and every before/after decision is written to audit history."
  },
  {
    icon: BadgeDollarSign,
    title: "Cloud Cost Review",
    text: "Managers inspect AWS spend through Cost Explorer, cached summaries, policy gates, model routing evidence, and team-level quota controls."
  }
];

const integrations = [
  "AWS Bedrock",
  "AWS Cost Explorer",
  "CloudWatch Logs",
  "Datadog",
  "Jira",
  "ServiceNow",
  "Cognito",
  "Okta",
  "Microsoft Entra ID",
  "Slack",
  "Microsoft Teams",
  "MCP agent clients"
];

const architecture = [
  "SSO identity",
  "API gateway",
  "Redaction",
  "OPA policy",
  "Model routing",
  "Tool adapters",
  "DynamoDB audit"
];

export default function MarketingPage() {
  return (
    <main className="marketing">
      <header className="marketingNav">
        <a className="marketingBrand" href="/">
          <ShieldCheck size={18} />
          AegisDesk
        </a>
        <nav aria-label="Product navigation">
          <a href="#use-cases">Use cases</a>
          <a href="#architecture">Architecture</a>
          <a href="#security">Security</a>
          <a href="#integrations">Integrations</a>
        </nav>
        <a className="marketingNavCta" href="/">
          Open control plane
        </a>
      </header>

      <section className="marketingHero">
        <div className="marketingHeroContent">
          <p>
            <Sparkles size={14} />
            Self-hosted CloudOps AI control
          </p>
          <h1>Self-hosted CloudOps AI control plane</h1>
          <span>
            Give employees AI help for incidents, tickets, access requests, and cloud cost questions while enforcing identity, policy,
            redaction, approval, model routing, and audit trails.
          </span>
          <div className="marketingActions">
            <a className="marketingPrimary" href="/">
              Open control plane
              <ArrowRight size={18} />
            </a>
            <a className="marketingSecondary" href="https://github.com/manynames3/aegisdesk-cloudops-control-plane/tree/main/docs">
              Read product docs
            </a>
          </div>
          <div className="marketingProofPills" aria-label="Platform capabilities">
            <span>Cognito identity</span>
            <span>OPA/Rego policy</span>
            <span>Bedrock routing</span>
            <span>DynamoDB audit</span>
          </div>
        </div>
        <figure className="marketingProductFrame">
          <div className="marketingWindowChrome">
            <span />
            <span />
            <span />
            <strong>Policy-aware CloudOps chat</strong>
          </div>
          <img alt="AegisDesk policy-aware CloudOps chat" src="/screenshots/policy-aware-chat.png" />
        </figure>
      </section>

      <section className="marketingSignal">
        <span>
          <strong>Identity</strong>
          Verified user, role, and team claims.
        </span>
        <span>
          <strong>Policy</strong>
          OPA decides before model or tool execution.
        </span>
        <span>
          <strong>Audit</strong>
          Request replay, source evidence, and cost records.
        </span>
        <span>
          <strong>Control</strong>
          External model kill switch and approval gates.
        </span>
      </section>

      <section className="marketingProblem" id="problem">
        <div>
          <p>Problem</p>
          <h2>AI is useful in CloudOps, but unmanaged AI creates governance risk.</h2>
        </div>
        <p>
          Teams need faster answers during incidents and cost reviews, but companies also need proof of who asked, what data was
          redacted, which policy allowed the request, which model answered, which tools were called, and where the audit record lives.
          AegisDesk puts that control layer in front of employee-facing AI workflows.
        </p>
      </section>

      <section className="marketingScreens">
        <div className="marketingSectionHeader">
          <p>Product surfaces</p>
          <h2>One control plane for operators, approvers, and governance reviewers.</h2>
        </div>
        <div className="screenshotGrid">
          <figure>
            <img alt="Policy-aware CloudOps chat" src="/screenshots/policy-aware-chat.png" />
            <figcaption>Chat responses show policy decisions, model routing, answer sources, and trusted citations.</figcaption>
          </figure>
          <figure>
            <img alt="Governance dashboard and audit explorer" src="/screenshots/governance-dashboard.png" />
            <figcaption>Governance reviewers filter audit events and inspect request replay details.</figcaption>
          </figure>
          <figure>
            <img alt="Manager approval workflow" src="/screenshots/manager-approvals.png" />
            <figcaption>Managers review scoped access requests with requester, status, approver, and timestamp evidence.</figcaption>
          </figure>
        </div>
      </section>

      <section className="marketingUseCases" id="use-cases">
        <div className="marketingSectionHeader">
          <p>Use Cases</p>
          <h2>Operational AI with enterprise controls built in.</h2>
        </div>
        <div className="useCaseGrid">
          {useCases.map((useCase) => {
            const Icon = useCase.icon;
            return (
              <article key={useCase.title}>
                <Icon size={22} />
                <h3>{useCase.title}</h3>
                <p>{useCase.text}</p>
              </article>
            );
          })}
        </div>
      </section>

      <section className="marketingArchitecture" id="architecture">
        <div className="marketingSectionHeader">
          <p>Architecture</p>
          <h2>A control path between users, models, policies, tools, and audit storage.</h2>
        </div>
        <div className="architectureFlow" aria-label="Architecture flow">
          {architecture.map((item, index) => (
            <div key={item}>
              <span>{index + 1}</span>
              <strong>{item}</strong>
            </div>
          ))}
        </div>
        <div className="architectureNotes">
          <span>
            <Building2 size={18} />
            Self-host with Docker Compose or AWS Terraform.
          </span>
          <span>
            <Network size={18} />
            Adapter interfaces isolate ticketing, incident context, access, and agent clients.
          </span>
          <span>
            <GitBranch size={18} />
            OPA/Rego policy stays outside the model response.
          </span>
        </div>
      </section>

      <section className="marketingSecurity" id="security">
        <div className="marketingSectionHeader">
          <p>Security Posture</p>
          <h2>Designed around identity, least privilege, and auditability.</h2>
        </div>
        <div className="securityGrid">
          <span>
            <ShieldCheck size={20} />
            SSO/JWKS verified identity and role claims
          </span>
          <span>
            <LockKeyhole size={20} />
            Secret and PII redaction before model routing
          </span>
          <span>
            <CloudCog size={20} />
            External model kill switch and low-cost fallback path
          </span>
          <span>
            <FileText size={20} />
            DynamoDB audit trail and request replay packet
          </span>
        </div>
      </section>

      <section className="marketingIntegrations" id="integrations">
        <div className="marketingSectionHeader">
          <p>Integrations</p>
          <h2>Connect the control plane to the systems CloudOps teams already use.</h2>
        </div>
        <div className="integrationList">
          {integrations.map((integration) => (
            <span key={integration}>
              <CheckCircle2 size={16} />
              {integration}
            </span>
          ))}
        </div>
      </section>

      <section className="marketingCta">
        <div className="marketingCtaIcon">
          <Bot size={28} />
          <Layers3 size={28} />
        </div>
        <div>
          <h2>Use AI for CloudOps without losing control of data, cost, or access.</h2>
          <p>Start with the hosted control plane, then connect your identity provider, ticket system, logs, and model policy.</p>
        </div>
        <a className="marketingPrimary" href="/">
          Launch app
          <MessageSquare size={18} />
        </a>
      </section>
    </main>
  );
}
