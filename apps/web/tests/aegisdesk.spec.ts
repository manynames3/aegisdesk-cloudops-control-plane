import { expect, request, test, type APIRequestContext, type Page } from "@playwright/test";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

async function adminHeaders(api: APIRequestContext) {
  const tokenResponse = await api.post(`${API_BASE}/auth/persona-token`, {
    data: { role: "admin", team: "platform" }
  });
  expect(tokenResponse.ok()).toBeTruthy();
  const token = await tokenResponse.json();
  return {
    Authorization: `Bearer ${token.access_token}`,
    "Content-Type": "application/json"
  };
}

async function resetState() {
  const api = await request.newContext();
  try {
    await api.post(`${API_BASE}/admin/reset`, { headers: await adminHeaders(api) });
  } finally {
    await api.dispose();
  }
}

async function useShortcutRole(page: Page, role: "employee" | "manager" | "admin") {
  const shortcut = page.locator(".shortcutPanel");
  if (!(await shortcut.locator(".segmented").isVisible())) {
    await shortcut.getByText("Evaluation shortcut").click();
  }
  await shortcut.getByRole("button", { name: role }).click();
}

async function sendPrompt(page: Page, prompt: string) {
  await page.locator("textarea").fill(prompt);
  await page.getByRole("button", { name: /^Send$/ }).click();
}

test.beforeEach(async () => {
  await resetState();
});

test("chat shows governed response evidence and request sources", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Chat", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Chat" })).toBeVisible();
  await expect(page.getByText("API ok")).toBeVisible();

  await sendPrompt(
    page,
    "Here is the checkout log with token=sample-secret-value and customer@example.test for INC-1042. Why is this timing out?"
  );

  await expect(page.getByText("Trusted source score").first()).toBeVisible();
  await expect(page.getByText("Answer sources").first()).toBeVisible();
  await expect(page.getByText("Trusted citations").first()).toBeVisible();
  await expect(page.getByText("Incident context points to").first()).toBeVisible();
  await expect(page.getByText("REDACTED").first()).toBeVisible();
  await expect(page.getByText("Decision Trail")).toBeVisible();
});

test("approval workflow moves from employee request to manager decision", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Chat", exact: true }).click();

  await sendPrompt(
    page,
    "I need temporary read-only access to the production payments database for INC-1042. Duration: 2 hours. Business reason: inspect connection pool metrics during active incident."
  );
  await expect(page.getByText("approval_required").first()).toBeVisible();

  await useShortcutRole(page, "manager");
  await page.getByRole("button", { name: "Approvals" }).click();
  await expect(page.getByRole("heading", { name: "Approval Queue" })).toBeVisible();
  await expect(page.locator(".approvalRow").filter({ hasText: "prod-payments-db" }).first()).toBeVisible();

  await page.getByTitle("Approve").click();
  await expect(page.getByText("approved").first()).toBeVisible();
  await expect(page.getByText(/Manager approved|Approved by/)).toBeVisible();
});

test("governance supports replay inspection and audit export", async ({ page }) => {
  await page.goto("/");
  await useShortcutRole(page, "admin");

  await page.getByRole("button", { name: "Seed data" }).click();
  await page.getByRole("button", { name: "Governance" }).click();

  await expect(page.getByRole("heading", { name: "Admin setup checklist" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Audit Export" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Audit Event Explorer" })).toBeVisible();

  await page.locator(".eventItem").first().click();
  await expect(page.getByText("Request replay").first()).toBeVisible();
  await expect(page.getByText("Prompt stored for replay")).toBeVisible();
  await expect(page.getByText("Policy input and output")).toBeVisible();

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "CSV" }).click()
  ]);

  expect(download.suggestedFilename()).toBe("aegisdesk-audit-export.csv");
  await expect(page.getByText("Audit CSV export generated")).toBeVisible();
});

test("incident investigation completes a governed Jira action against a controlled HTTP fixture", async ({ page }) => {
  page.on("dialog", dialog => dialog.accept());
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Incidents", exact: true })).toBeVisible();
  await expect(page.getByText("No incident cases in this team.")).toBeVisible();
  await page.getByRole("button", { name: "New incident" }).click();
  const dialog = page.getByRole("dialog", { name: "New incident" });
  await dialog.getByLabel("Title", { exact: true }).fill("Checkout error investigation");
  await dialog.getByLabel("Description").fill("Controlled workflow test. Review CloudWatch evidence before selecting mitigation.");
  await dialog.getByLabel("AWS service").fill("Lambda");
  await dialog.getByLabel("Affected resource").fill("checkout-api");
  await dialog.getByLabel("Environment").fill("test");
  await dialog.getByLabel("Severity").selectOption("high");
  await dialog.getByRole("button", { name: "Create incident" }).click();
  await expect(page.getByRole("heading", { name: "Checkout error investigation", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Evidence", exact: true }).click();
  await page.getByRole("button", { name: "Refresh evidence" }).click();
  await expect(page.getByText("Fixture evidence is not used in incident cases.", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "Investigation", exact: true }).click();
  await page.getByLabel("Entry type").selectOption("hypothesis");
  await page.getByLabel("Investigation entry").fill("A recent deployment may be related; evidence is currently unavailable.");
  await page.getByRole("button", { name: "Add entry" }).click();
  await expect(page.getByText("hypothesis / operator supplied")).toBeVisible();
  await page.getByRole("button", { name: "Actions", exact: true }).last().click();
  await page.getByRole("button", { name: "Propose Jira ticket" }).click();
  await page.getByRole("button", { name: "Request approval", exact: true }).click();
  await expect(page.getByText("pending approval", { exact: true })).toBeVisible();
  await useShortcutRole(page, "manager");
  await page.getByRole("button", { name: /Checkout error investigation/ }).click();
  await page.getByRole("button", { name: "Actions", exact: true }).last().click();
  await page.getByRole("button", { name: "Approve exact action" }).click();
  await expect(page.getByText("approved", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Execute approved action" }).click();
  await expect(page.getByText("succeeded", { exact: true })).toBeVisible();
  await page.screenshot({ path: "../../docs/evidence/screenshots/incident-actions-controlled-desktop.png", fullPage: true });
  await page.getByRole("button", { name: "Ticket", exact: true }).click();
  await expect(page.getByRole("link", { name: /^OPS-\d+$/ })).toHaveAttribute("href", /127\.0\.0\.1:8766\/browse\/OPS-/);
  await page.getByRole("button", { name: "Timeline", exact: true }).click();
  await expect(page.getByText("action succeeded", { exact: true })).toBeVisible();
  await page.setViewportSize({ width: 1024, height: 768 });
  await page.screenshot({ path: "../../docs/evidence/screenshots/incident-timeline-controlled-tablet.png", fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await page.getByRole("button", { name: "Incident queue", exact: true }).click();
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({ path: "../../docs/evidence/screenshots/incident-queue-controlled-desktop.png", fullPage: true });
});

test("incident queue distinguishes API failure from an empty team queue", async ({ page }) => {
  await page.route(`${API_BASE}/incidents`, route => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "storage_unavailable" }) }));
  await page.goto("/");
  await expect(page.locator(".incidentError")).toContainText("storage unavailable");
  await expect(page.getByText("No incident cases in this team.")).not.toBeVisible();
  await page.unroute(`${API_BASE}/incidents`);
  await page.locator(".incidentError").getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(page.getByText("No incident cases in this team.")).toBeVisible();
});
