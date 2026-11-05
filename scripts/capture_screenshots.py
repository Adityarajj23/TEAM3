"""Capture responsive screenshots across major screens at 1440px, 1280px, 1024px, 768px, 390px, 360px.

Usage: python scripts/capture_screenshots.py --base http://127.0.0.1:5173 --chrome /usr/bin/chromium
"""
import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

SCREENS = [
    ("01-overview", "/", None),
    ("02-requirements", "/requirements", None),
    ("03-tests", "/tests", None),
    ("04-approval-workspace", "/tests/review", None),
    ("05-suites", "/suites", None),
    ("06-executions", "/executions", None),
    ("07-defects", "/defects", None),
    ("08-traceability", "/traceability", None),
    ("09-analytics", "/analytics", None),
    ("10-settings", "/settings", None),
]

VIEWPORTS = [
    (1440, 900, "desktop-large"),
    (1280, 800, "desktop-standard"),
    (1024, 768, "tablet-landscape"),
    (768, 1024, "tablet-portrait"),
    (390, 844, "mobile-standard"),
    (360, 800, "mobile-compact"),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:5173")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "docs" / "screenshots"))
    ap.add_argument("--chrome", default="/usr/bin/chromium", help="Path to Chromium executable")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    problems = []

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=a.chrome) if a.chrome else p.chromium.launch()
        for width, height, _name in VIEWPORTS:
            ctx = browser.new_context(viewport={"width": width, "height": height})
            page = ctx.new_page()
            errors: list[str] = []
            page.on("console", lambda m, e=errors: e.append(m.text) if m.type == "error" else None)

            for sname, path, action in SCREENS:
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
                    problems.append(f"{sname}@{width}: horizontal page overflow")
                page.screenshot(path=str(out / f"{sname}-{width}.png"))

            if errors:
                problems.append(f"console errors at {width}px: {errors[:5]}")
            ctx.close()
        browser.close()

    total_captured = len(SCREENS) * len(VIEWPORTS)
    print(f"Captured {total_captured} screenshots across {len(VIEWPORTS)} viewports in {out}")
    print("\n".join(problems) if problems else "Verification passed: No layout overflow or console errors detected across all viewports.")


if __name__ == "__main__":
    main()
