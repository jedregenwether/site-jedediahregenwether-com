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


def devto_existing_titles(api_key: str) -> set:
    titles = set()
    page = 1
    while True:
        r = requests.get(
            "https://dev.to/api/articles/me",
            headers={"api-key": api_key},
            params={"per_page": 100, "page": page},
            timeout=30,
        )
        if r.status_code != 200:
            break
        arr = r.json() or []
        if not arr:
            break
        for a in arr:
            t = a.get("title")
            if t:
                titles.add(t)
        page += 1
    return titles


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
    api_key = os.environ.get("DEVTO_API_KEY", "").strip()
    if not api_key:
        print("DEVTO_API_KEY not set; skipping.")
        return 0

    baseurl = read_baseurl()
    items = load_items()
    if not items:
        print("No items loaded; skipping.")
        return 0

    now = datetime.now(timezone.utc)
    iso = now.isocalendar()
    title = f"Weekly Digest: AI/ML & Strategy — Week {iso.year}-W{iso.week:02d}"

    existing = devto_existing_titles(api_key)
    if title in existing:
        print("Digest already published on Dev.to; skipping.")
        return 0

    window = weekly_window(items)
    if not window:
        window = items[:15]

    body = build_markdown(baseurl, window, iso.year, iso.week)

    payload = {
        "article": {
            "title": title,
            "published": True,
            "body_markdown": body,
            "tags": ["ai", "machine-learning", "software", "strategy"],
            "series": "weekly-digest",
            "canonical_url": baseurl or None,
        }
    }

    r = requests.post(
        "https://dev.to/api/articles",
        headers={"api-key": api_key, "Content-Type": "application/json"},
        data=json.dumps(payload),
        timeout=60,
    )
    if r.status_code not in (200, 201):
        print(f"Dev.to publish failed: {r.status_code} {r.text}", file=sys.stderr)
        return 1
    print("Published digest to Dev.to")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

