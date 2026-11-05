"""Capture screenshots of the major screens at 1440px and 1024px with Playwright.

Usage: python scripts/capture_screenshots.py --base http://127.0.0.1:5173 --email ... --password ...
"""
import argparse
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

SCREENS = [
    ("01-login", "/login", None), ("02-dashboard", "/", None), ("03-projects", "/projects", None),
    ("04-project-workspace", "/projects/1", None), ("05-requirements", "/requirements", None),
    ("06-requirement-detail", "/requirements/1", None), ("07-requirement-versions", "/requirements/1?tab=versions", None),
    ("08-requirement-analysis", "/requirements/1?tab=analysis", None), ("09-acceptance-criteria", "/requirements/1?tab=criteria", None),
    ("10-change-impact", "/requirements/1?tab=impact", None), ("11-tests", "/tests", None), ("12-test-detail", "/tests/1", None),
    ("13-approval-workspace", "/tests/review", None), ("14-suites", "/suites", None), ("15-suite-detail", "/suites/1", None),
    ("16-executions", "/executions", None), ("17-execution-detail", "/executions/1", "row"), ("18-defects", "/defects", None),
    ("19-defect-detail", "/defects/1", None), ("20-traceability", "/traceability", None), ("21-analytics", "/analytics", None),
    ("22-evaluations", "/evaluations", None), ("23-audit", "/audit", None), ("24-integrations", "/integrations", None),
    ("25-settings", "/settings", None),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:5173")
    ap.add_argument("--email", default="admin@northwind-hcm.example")
    ap.add_argument("--password", default="NorthwindAdmin2026!Secure")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "docs" / "screenshots"))
    ap.add_argument("--chrome", default=None, help="Path to a Chrome/Chromium executable")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    problems = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=a.chrome) if a.chrome else p.chromium.launch()
        for width in (1440, 1024):
            ctx = browser.new_context(viewport={"width": width, "height": 900})
            page = ctx.new_page()
            errors: list[str] = []
            page.on("console", lambda m, e=errors: e.append(m.text) if m.type == "error" else None)
            for name, path, action in SCREENS:
                if name == "01-login":
                    # Capture pristine login view without local auto-redirect
                    page.route("**/api/v1/auth/me", lambda r: r.fulfill(status=401, json={"error": "unauthenticated"}))
                    page.goto(a.base + "/login")
                    page.wait_for_load_state("networkidle")
                    page.wait_for_timeout(500)
                    overflow = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
                    if overflow:
                        problems.append(f"{name}@{width}: horizontal page overflow")
                    page.screenshot(path=str(out / f"{name}-{width}.png"))
                    page.unroute("**/api/v1/auth/me")
                    continue

                page.goto(a.base + path)
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(600)
                if action == "row":
                    rows = page.locator("tbody tr")
                    if rows.count():
                        rows.nth(min(1, rows.count() - 1)).click()
                        page.wait_for_timeout(300)
                overflow = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
                if overflow:
                    problems.append(f"{name}@{width}: horizontal page overflow")
                page.screenshot(path=str(out / f"{name}-{width}.png"))
            if errors:
                problems.append(f"console errors at {width}px: {errors[:5]}")
            ctx.close()
        browser.close()
    print("captured", len(SCREENS) * 2, "screenshots in", out)
    print("\n".join(problems) if problems else "no layout overflow or console errors detected")


if __name__ == "__main__":
    main()
