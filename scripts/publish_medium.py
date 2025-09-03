#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests


def read_baseurl() -> str:
    here = os.path.dirname(__file__)
    for fname in (os.path.join(here, "..", "hugo.toml"), os.path.join(here, "..", "config.toml")):
        try:
            with open(fname, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.lower().startswith("baseurl"):
                        parts = line.split("=", 1)
                        if len(parts) == 2:
                            url = parts[1].strip().strip("'\"")
                            return url
        except FileNotFoundError:
            continue
    return ""


def load_items() -> list:
    data_path = os.path.join(os.path.dirname(__file__), "..", "data", "feeds.json")
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
    return data.get("items", [])


def weekly_window(items: list) -> list:
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    sel = []
    for it in items:
        ts = it.get("published")
        try:
            dt = datetime.fromisoformat(ts)
        except Exception:
            dt = now
        if dt >= week_ago:
            sel.append((dt, it))
    sel.sort(key=lambda x: x[0], reverse=True)
    return [it for _, it in sel]


def build_markdown(baseurl: str, items: list, year: int, week: int) -> str:
    lines = []
    lines.append(f"Weekly Digest — AI/ML, SWE, Strategy (Week {year}-W{week:02d})\n")
    lines.append(f"Curated links from reputable sources. More at {baseurl}\n")
    for it in items[:15]:
        title = it.get("title", "")
        link = it.get("link", "")
        src = it.get("source", "")
        lines.append(f"- [{title}]({link}) — {src}")
    lines.append("\n—\n")
    lines.append(f"Canonical: {baseurl}")
    return "\n".join(lines)


def main():
    # Only post once per week (Monday) unless forced
    if os.environ.get("FORCE_WEEKLY_POST", "") != "1":
        if datetime.now(timezone.utc).weekday() != 0:
            print("Not weekly posting day; skipping Medium.")
            return 0
    token = os.environ.get("MEDIUM_TOKEN", "").strip()
    if not token:
        print("MEDIUM_TOKEN not set; skipping.")
        return 0

    baseurl = read_baseurl()
    items = load_items()
    if not items:
        print("No items loaded; skipping.")
        return 0

    now = datetime.now(timezone.utc)
    iso = now.isocalendar()
    title = f"Weekly Digest: AI/ML & Strategy — Week {iso.year}-W{iso.week:02d}"

    # Get user id
    me = requests.get(
        "https://api.medium.com/v1/me",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        timeout=30,
    )
    if me.status_code != 200:
        print(f"Medium /me failed: {me.status_code} {me.text}", file=sys.stderr)
        return 1
    user_id = me.json().get("data", {}).get("id")
    if not user_id:
        print("Medium user id not found", file=sys.stderr)
        return 1

    window = weekly_window(items)
    if not window:
        window = items[:15]

    body = build_markdown(baseurl, window, iso.year, iso.week)

    payload = {
        "title": title,
        "contentFormat": "markdown",
        "content": body,
        "tags": ["ai", "machine-learning", "software", "strategy"],
        "publishStatus": "public",
        "canonicalUrl": baseurl or None,
        "license": "all-rights-reserved",
    }

    r = requests.post(
        f"https://api.medium.com/v1/users/{user_id}/posts",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        data=json.dumps(payload),
        timeout=60,
    )
    if r.status_code not in (200, 201):
        print(f"Medium publish failed: {r.status_code} {r.text}", file=sys.stderr)
        return 1
    print("Published digest to Medium")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
