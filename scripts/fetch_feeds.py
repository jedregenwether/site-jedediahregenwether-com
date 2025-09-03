#!/usr/bin/env python3
"""
Fetch multiple RSS/Atom feeds, normalize, dedupe, and write to data/feeds.json.
Intended to run in CI prior to Hugo build.
"""
import json
import os
import sys
from datetime import datetime, timezone

try:
    import feedparser  # type: ignore
except Exception:
    print("feedparser not installed. Run: pip install -r scripts/requirements.txt", file=sys.stderr)
    sys.exit(1)

FEEDS = [
    ("https://ai.googleblog.com/atom.xml", "Google AI"),
    ("https://thegradient.pub/rss/", "The Gradient"),
    ("https://machinelearningmastery.com/blog/feed/", "Machine Learning Mastery"),
    ("https://aws.amazon.com/blogs/machine-learning/feed/", "AWS ML Blog"),
    ("https://stackoverflow.blog/feed/", "Stack Overflow Blog"),
    ("https://www.oreilly.com/radar/feed/", "O'Reilly Radar"),
    ("http://export.arxiv.org/rss/cs.LG", "arXiv cs.LG"),
    ("https://deepmind.google/discover/rss/", "Google DeepMind"),
    ("https://www.microsoft.com/en-us/research/feed/", "Microsoft Research"),
    ("https://blogs.nvidia.com/blog/category/ai/feed/", "NVIDIA AI Blog"),
    ("https://www.technologyreview.com/topic/artificial-intelligence/feed/", "MIT Tech Review AI"),
    ("https://engineering.atspotify.com/feed/", "Spotify Engineering"),
    ("https://dropbox.tech/feed.xml", "Dropbox Tech"),
    ("https://lilianweng.github.io/lil-log/atom.xml", "Lilian Weng"),
    ("https://hai.stanford.edu/news/rss.xml", "Stanford HAI"),
    ("https://blog.paperswithcode.com/rss/", "Papers with Code Blog"),
    ("https://www.thoughtworks.com/insights/rss.xml", "Thoughtworks Insights"),
    ("https://openai.com/blog/rss", "OpenAI Blog"),
    ("https://ai.facebook.com/blog/rss/", "Meta AI Blog"),
    ("https://research.google/blog/rss/", "Google Research"),
]


def parse_date(entry):
    for key in ("published_parsed", "updated_parsed"):
        dt = entry.get(key)
        if dt:
            try:
                return datetime(*dt[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def main():
    items = []
    seen = set()
    for url, source in FEEDS:
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"Failed to fetch {url}: {e}", file=sys.stderr)
            continue
        for e in feed.entries[:50]:
            link = e.get("link")
            title = (e.get("title") or "").strip()
            if not link or not title:
                continue
            key = (title, link)
            if key in seen:
                continue
            seen.add(key)
            dt = parse_date(e) or datetime.now(timezone.utc)
            items.append({
                "title": title,
                "link": link,
                "source": source,
                "published": dt.isoformat(),
            })

    # sort newest first
    items.sort(key=lambda x: x.get("published", ""), reverse=True)

    out = {"items": items[:200]}

    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    out_path = os.path.abspath(os.path.join(data_dir, "feeds.json"))
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(out['items'])} items to {out_path}")


if __name__ == "__main__":
    main()
