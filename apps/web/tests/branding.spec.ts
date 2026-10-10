import { expect, test } from "@playwright/test";

for (const route of ["/", "/marketing"]) {
  for (const width of [1440, 1024, 375]) {
    test(`precision wordmark fits ${route} at ${width}px`, async ({ page }, testInfo) => {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(route);
      const logo = page.getByRole("img", { name: "AegisDesk", exact: true });
      await expect(logo).toBeVisible();
      await expect(logo).toHaveAttribute("src", "/brand/aegisdesk-wordmark.svg");
      await expect.poll(() => logo.evaluate(image => (image as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
      const bounds = await logo.boundingBox();
      expect(bounds).not.toBeNull();
      expect(bounds!.width).toBeGreaterThan(100);
      expect(bounds!.x).toBeGreaterThanOrEqual(0);
      expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(width);
      expect(bounds!.width / bounds!.height).toBeCloseTo(1174 / 224, 1);
      const header = page.locator(route === "/" ? ".brand" : ".marketingNav");
      if (route === "/marketing") {
        const cta = await page.locator(".marketingNavCta").boundingBox();
        expect(bounds!.x + bounds!.width).toBeLessThan(cta!.x);
      }
      await header.screenshot({ path: testInfo.outputPath("precision-wordmark.png") });
    });
  }
}

test("matching A favicon is served and registered", async ({ page, request }) => {
  await page.goto("/");
  const icon = page.locator('link[rel="icon"][type="image/svg+xml"]');
  await expect(icon).toHaveAttribute("href", /\/icon\.svg/);
  const response = await request.get((await icon.getAttribute("href"))!);
  expect(response.ok()).toBeTruthy();
  expect(response.headers()["content-type"]).toContain("image/svg+xml");
  expect(await response.text()).toContain("prefers-color-scheme: dark");
});

test("divided A keeps its motif with straight edges in both assets", async ({ page, request }) => {
  const wordmark = await request.get("/brand/aegisdesk-wordmark.svg");
  const favicon = await request.get("/icon.svg");
  expect(wordmark.ok()).toBeTruthy();
  expect(favicon.ok()).toBeTruthy();
  await page.goto("/");
  const geometry = await page.evaluate(([wordmarkSvg, faviconSvg]) => {
    const parser = new DOMParser();
    const a = parser.parseFromString(wordmarkSvg, "image/svg+xml").querySelector("g > path")!;
    const icon = parser.parseFromString(faviconSvg, "image/svg+xml").querySelector("svg > path")!;
    const path = new Path2D(a.getAttribute("d")!);
    const context = document.createElement("canvas").getContext("2d")!;
    const ink = (x: number, y: number) => context.isPointInPath(path, x, y, "evenodd");
    return {
      sameOutline: a.getAttribute("d") === icon.getAttribute("d"),
      sameFillRule: a.getAttribute("fill-rule") === "evenodd" && icon.getAttribute("fill-rule") === "evenodd",
      leftSplit: [86, 91, 97].every(y => !ink(50, y)),
      crossbar: [56, 72, 90.5, 102].every(x => ink(x, 120)),
      barSeparation: !ink(112, 120),
      openCounter: !ink(90.5, 70),
      straightOuter: [40, 70, 84, 99, 120, 145, 170].every(y => {
        const edge = 70 * (1 - y / 171);
        return !ink(edge - 0.1, y) && ink(edge + 0.1, y);
      }),
      straightInner: [60, 84, 145, 170].every(y => {
        const edge = 90.5 - 48.5 * (y - 44) / 127;
        return ink(edge - 0.1, y) && !ink(edge + 0.1, y);
      }),
      rightLeg: [60, 90, 120, 145, 170].every(y => ink(181 - (70 * (1 - y / 171) + 20), y))
    };
  }, [await wordmark.text(), await favicon.text()]);
  expect(geometry).toEqual({
    sameOutline: true,
    sameFillRule: true,
    leftSplit: true,
    crossbar: true,
    barSeparation: true,
    openCounter: true,
    straightOuter: true,
    straightInner: true,
    rightLeg: true
  });
});
