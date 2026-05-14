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
  SearchCheck,
  ShieldCheck,
  Siren,
  Sparkles,
  UsersRound
} from "lucide-react";

const useCases = [
  {
    icon: Siren,
    title: "During an incident",
    text: "Operators ask what to check next, receive runbook-backed guidance, and see whether logs, policy, model routing, or internal knowledge shaped the answer."
  },
  {
    icon: KeyRound,
    title: "When access is needed",
    text: "Employees request scoped production access from the same workspace. Unsafe admin access is denied, safer temporary access moves to a manager approval queue."
  },
  {
    icon: BadgeDollarSign,
    title: "When spend spikes",
    text: "Managers review AWS cost summaries with role-based access, cached Cost Explorer data, model-use evidence, and quota controls to reduce duplicate spend."
  }
];

const activeIntegrations = ["AWS Bedrock", "AWS Cost Explorer", "Amazon Cognito", "DynamoDB audit", "OPA/Rego policy"];

const adapterIntegrations = ["CloudWatch Logs", "Datadog", "Jira", "ServiceNow", "Okta", "Microsoft Entra ID", "Slack", "Microsoft Teams", "MCP agent clients"];

const architecture = [
  "Verify identity",
  "Redact sensitive data",
  "Check policy",
  "Route the model",
  "Control tools",
  "Capture approval",
  "Write audit trail"
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
          <a href="#why">Why AegisDesk</a>
          <a href="#workflow">Workflow</a>
          <a href="#security">Security</a>
          <a href="#integrations">Integrations</a>
        </nav>
        <a className="marketingNavCta" href="/">
          Open AegisDesk
        </a>
      </header>

      <section className="marketingHero">
        <div className="marketingHeroContent">
          <p>
            <Sparkles size={14} />
            AI support for CloudOps teams
          </p>
          <h1>AI help for CloudOps, with company controls built in.</h1>
          <span>
            AegisDesk gives employees one place to ask about incidents, tickets, access, and cloud cost while your policies decide what
            can be answered, approved, routed to a model, or recorded for audit.
          </span>
          <div className="marketingActions">
            <a className="marketingPrimary" href="/">
              Open AegisDesk
              <ArrowRight size={18} />
            </a>
            <a className="marketingSecondary" href="https://github.com/manynames3/aegisdesk-cloudops-control-plane/tree/main/docs">
              Read self-hosting docs
            </a>
          </div>
          <div className="marketingProofPills" aria-label="Platform capabilities">
            <span>Ask operational questions</span>
            <span>Redact sensitive data</span>
            <span>Route approved requests</span>
            <span>Audit every action</span>
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
          <strong>Operators</strong>
          Get guided incident and access help.
        </span>
        <span>
          <strong>Managers</strong>
          Approve scoped requests with evidence.
        </span>
        <span>
          <strong>Security</strong>
          Keep redaction, policy, and audit visible.
        </span>
        <span>
          <strong>FinOps</strong>
          Review cloud spend with model-use context.
        </span>
      </section>

      <section className="marketingProblem" id="problem">
        <div>
          <p>Problem</p>
          <h2>Your teams already want AI during operational work. The hard part is control.</h2>
        </div>
        <p>
          A public chatbot cannot know who the employee is, which production actions they are allowed to request, what should be
          redacted, when manager approval is required, or which audit record a security reviewer will need later. AegisDesk adds that
          governed workflow around the AI experience.
        </p>
      </section>

      <section className="marketingScreens">
        <div className="marketingSectionHeader">
          <p>Product surfaces</p>
          <h2>The workspace for operators, approvers, governance reviewers, and control owners.</h2>
        </div>
        <div className="screenshotGrid">
          <figure>
            <img alt="Manager approval workflow" src="/screenshots/manager-approvals.png" />
            <figcaption>Managers review scoped access requests with requester, status, approver, and timestamp evidence.</figcaption>
          </figure>
          <figure>
            <img alt="Governance dashboard and audit explorer" src="/screenshots/governance-dashboard.png" />
            <figcaption>Governance reviewers filter audit events and inspect request replay details.</figcaption>
          </figure>
          <figure>
            <img alt="Policy and safety evaluations" src="/screenshots/evaluations.png" />
            <figcaption>Control owners verify that redaction, access denial, approvals, ticket gating, and cost checks are working.</figcaption>
          </figure>
        </div>
      </section>

      <section className="marketingUseCases" id="use-cases">
        <div className="marketingSectionHeader">
          <p>Use Cases</p>
          <h2>Give employees useful answers without bypassing how the company operates.</h2>
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

      <section className="marketingWhy" id="why">
        <div className="marketingSectionHeader">
          <p>Why AegisDesk</p>
          <h2>Not another open chat box. A governed workflow around the answer.</h2>
        </div>
        <div className="whyGrid">
          <article>
            <MessageSquare size={22} />
            <h3>Unmanaged AI answers the prompt.</h3>
            <p>It usually cannot verify the employee, apply internal policy, open an approval, cite company runbooks, or preserve a replayable audit trail.</p>
          </article>
          <article>
            <ShieldCheck size={22} />
            <h3>AegisDesk controls the request.</h3>
            <p>Identity, redaction, policy, source evidence, approvals, model route, tool calls, and audit events are handled before and after the model response.</p>
          </article>
          <article>
            <UsersRound size={22} />
            <h3>Teams keep their workflow.</h3>
            <p>Operators get practical help, managers approve only scoped actions, and reviewers can inspect exactly why each decision was made.</p>
          </article>
        </div>
      </section>

      <section className="marketingArchitecture" id="workflow">
        <div className="marketingSectionHeader">
          <p>Workflow</p>
          <h2>Every request moves through the same control path.</h2>
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
            Connect ticketing, incident context, access, and agent clients through adapter interfaces.
          </span>
          <span>
            <GitBranch size={18} />
            Keep policy decisions outside the model response.
          </span>
        </div>
      </section>

      <section className="marketingSecurity" id="security">
        <div className="marketingSectionHeader">
          <p>Security</p>
          <h2>The controls companies need before AI becomes part of daily operations.</h2>
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
          <h2>Connect AegisDesk to the systems CloudOps teams already use.</h2>
        </div>
        <div className="integrationGroups">
          <div>
            <h3>Available in the hosted build</h3>
            <div className="integrationList">
              {activeIntegrations.map((integration) => (
                <span key={integration}>
                  <CheckCircle2 size={16} />
                  {integration}
                </span>
              ))}
            </div>
          </div>
          <div>
            <h3>Adapter-ready for customer environments</h3>
            <div className="integrationList">
              {adapterIntegrations.map((integration) => (
                <span key={integration}>
                  <SearchCheck size={16} />
                  {integration}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="marketingCta">
        <div className="marketingCtaIcon">
          <Bot size={28} />
          <Layers3 size={28} />
        </div>
        <div>
          <h2>Use AI in CloudOps without losing control of data, cost, access, or auditability.</h2>
          <p>Start with the hosted control plane, then connect your identity provider, ticketing system, logs, approvals, and model policy.</p>
        </div>
        <a className="marketingPrimary" href="/">
          Open AegisDesk
          <MessageSquare size={18} />
        </a>
      </section>

      <footer className="marketingFooter">©2026 SUPREME AI VENTURES LLC</footer>
    </main>
  );
}
