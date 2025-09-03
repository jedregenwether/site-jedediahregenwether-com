#!/usr/bin/env python3
import os
import json
from datetime import datetime, timedelta, timezone


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


def write_digest(items: list):
    now = datetime.now(timezone.utc)
    iso = now.isocalendar()
    year, week = iso.year, iso.week
    content_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "content", "digest"))
    os.makedirs(content_dir, exist_ok=True)
    out_path = os.path.join(content_dir, f"{year}-w{week:02d}.md")

    header = [
        "---",
        f"title: 'Weekly Digest — AI/ML, SWE, Strategy (Week {year}-W{week:02d})'",
        f"date: {now.date().isoformat()}",
        "draft: false",
        "---",
        "",
    ]

    lines = header
    if not items:
        lines.append("No items found this week.")
    else:
        for it in items[:30]:
            title = it.get("title", "").replace("\n", " ")
            link = it.get("link", "")
            src = it.get("source", "")
            lines.append(f"- [{title}]({link}) — {src}")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote digest page: {out_path}")


def main():
    items = load_items()
    window = weekly_window(items)
    if not window:
        window = items[:30]
    write_digest(window)


if __name__ == "__main__":
    main()

