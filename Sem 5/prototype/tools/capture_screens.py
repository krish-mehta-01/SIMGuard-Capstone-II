"""Drives the live SIMGuard console in Chrome and saves report screenshots to results/screens/.

Panels are captured as element crops (not whole pages) so that text stays legible when the figure is scaled to a page width.
Also fails loudly on any JavaScript console error, so it doubles as a smoke test of the dashboard."""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import RESULTS_DIR  # noqa: E402

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8051"
OUT = RESULTS_DIR / "screens"
OUT.mkdir(parents=True, exist_ok=True)


def crop(page, selector, name, max_height=None, pad=6):
    box = page.locator(selector).bounding_box()
    h = box["height"] if not max_height else min(box["height"], max_height)
    page.screenshot(path=str(OUT / name), clip={"x": max(box["x"] - pad, 0), "y": max(box["y"] - pad, 0),
                                                 "width": box["width"] + 2 * pad, "height": h + 2 * pad}, full_page=True)


def main():
    errors = []
    for old in OUT.glob("*.png"):
        old.unlink()
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1500, "height": 1000}, device_scale_factor=2)
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))

        for key in ["legitimate", "suspicious", "attack", "blacklisted"]:
            page.goto(f"{BASE}/?scenario={key}")
            page.wait_for_selector("#decBody:not([hidden])")
            page.wait_for_selector("#chainBody:not([hidden])")
            page.wait_for_timeout(300)
            crop(page, "#cardDecision", f"eval_{key}_decision.png")
            if key == "attack":
                crop(page, "main", "eval_attack_full.png", max_height=1180)
                crop(page, "#cardRequest", "eval_attack_request.png")
                crop(page, "#cardChain", "eval_attack_chain.png")

        page.goto(f"{BASE}/?tab=log")
        page.wait_for_selector("#logTable tbody tr")
        crop(page, "#tab-log", "decision_log.png", max_height=640)

        btn = page.locator("#logTable button:has-text('Resolve')").first
        if btn.count():
            btn.click()
            page.fill("#resolveNote", "Called the registered number; customer confirmed the request.")
            page.wait_for_timeout(200)
            box = page.locator("#resolveDialog").bounding_box()
            page.screenshot(path=str(OUT / "resolve_dialog.png"), clip={"x": box["x"] - 12, "y": box["y"] - 12,
                                                                        "width": box["width"] + 24, "height": box["height"] + 24})
            page.keyboard.press("Escape")

        page.goto(f"{BASE}/?tab=ledger")
        page.wait_for_selector("#ledgerTable tbody tr")
        crop(page, "#tab-ledger", "ledger.png", max_height=700)

        page.goto(f"{BASE}/?tab=audit")
        page.wait_for_selector("#tamperTarget option", state="attached")
        page.click("#btnVerify")
        page.wait_for_selector("#auditResult .result-box")
        for kind in ["tamper_payload", "replay", "stale", "unknown_device"]:
            page.click(f"[data-edge={kind}]")
            page.wait_for_timeout(250)
        crop(page, "#tab-audit", "audit_clean.png")

        page.click("[data-tamper=decision]")
        page.wait_for_selector("#tamperResult .result-box.bad")
        crop(page, "#tab-audit", "audit_tampered.png")
        page.click("#btnRestore")
        page.wait_for_selector("#tamperResult .result-box.ok")

        page.goto(f"{BASE}/?tab=model")
        page.wait_for_selector("#modelTable tbody tr")
        page.wait_for_timeout(600)
        crop(page, "#tab-model", "model.png", max_height=820)
        browser.close()

    print("screenshots:", sorted(p.name for p in OUT.glob("*.png")))
    if errors:
        print("JAVASCRIPT ERRORS:")
        for e in errors:
            print("  ", e)
        sys.exit(1)
    print("no JavaScript console errors")


if __name__ == "__main__":
    main()
