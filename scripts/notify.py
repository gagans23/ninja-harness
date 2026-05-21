#!/usr/bin/env python3
"""
Relay a Ninja Harness eval summary to Slack and/or Telegram (and/or a generic
webhook). Standard library only — no SDKs, no bundled credentials.

Reads the summary text from a file argument or stdin, then posts to whichever
channels are configured via environment variables:

  Slack    — NINJA_SLACK_WEBHOOK        (Slack Incoming Webhook URL)
  Telegram — NINJA_TELEGRAM_BOT_TOKEN  + NINJA_TELEGRAM_CHAT_ID
  Generic  — NINJA_NOTIFY_WEBHOOK       (any endpoint that accepts {"text": ...})

Usage:
  ninja-harness suite --suite scenarios/suite.yaml --format summary | python scripts/notify.py
  python scripts/notify.py summary.txt

If no channels are configured it prints the summary and exits 0 (no-op), so it
is safe to call unconditionally in CI.

WhatsApp note: the WhatsApp Cloud API requires Meta app setup (phone number id,
recipient opt-in, message templates). Point NINJA_NOTIFY_WEBHOOK at a small
relay you control that forwards {"text": ...} to the Graph API, or use Slack /
Telegram which work out of the box here.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request


def _post(url: str, payload: dict, headers: dict | None = None) -> int:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status


def _read_summary() -> str:
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            return f.read().strip()
    return sys.stdin.read().strip()


def main() -> int:
    text = _read_summary()
    if not text:
        print("No summary text provided; nothing to send.")
        return 0

    sent: list[str] = []
    failures: list[str] = []

    slack = os.environ.get("NINJA_SLACK_WEBHOOK")
    if slack:
        try:
            _post(slack, {"text": text})
            sent.append("slack")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"slack: {exc}")

    tg_token = os.environ.get("NINJA_TELEGRAM_BOT_TOKEN")
    tg_chat = os.environ.get("NINJA_TELEGRAM_CHAT_ID")
    if tg_token and tg_chat:
        try:
            _post(
                f"https://api.telegram.org/bot{tg_token}/sendMessage",
                {"chat_id": tg_chat, "text": text},
            )
            sent.append("telegram")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"telegram: {exc}")

    generic = os.environ.get("NINJA_NOTIFY_WEBHOOK")
    if generic:
        try:
            _post(generic, {"text": text})
            sent.append("webhook")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"webhook: {exc}")

    if not (slack or (tg_token and tg_chat) or generic):
        print("No notification channels configured. Summary was:\n")
        print(text)
        return 0

    if sent:
        print("Notification sent to: " + ", ".join(sent))
    for f in failures:
        print(f"Notification failed — {f}")
    # Don't fail the CI job just because a notification couldn't be delivered.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
