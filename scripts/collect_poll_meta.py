"""Re-collect poll metadata with the fields the first pass discarded.

The abgeordnetenwatch `polls` list endpoint returns three fields we were not
storing, at no extra request cost:

  field_topics      official topic taxonomy per poll (answers the Notion open
                    question "define the unified topic taxonomy" for 2005+)
  field_intro       HTML summary of the vote, usually linking the Drucksache
                    PDF on dserver.bundestag.de ("read the bill" context)
  field_committees  the committee(s) that handled the bill

Writes data/polls_meta.csv (one row per poll, topics/committees pipe-joined,
intro stripped of HTML). Cheap: ~7 requests, under a minute.

Run from the project root:  python -u scripts/collect_poll_meta.py
"""

import csv
import html
import json
import re
import subprocess
import time
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
API = "https://www.abgeordnetenwatch.de/api/v2"
OUT = DATA / "polls_meta.csv"
LEGISLATURES = [67, 83, 97, 111, 132, 161]


def get(url):
    r = subprocess.run(
        ["curl", "-sS", "--ssl-no-revoke", "--compressed", "-m", "120", url],
        capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(r.stderr)
    return json.loads(r.stdout)


def clean(raw: str) -> str:
    """HTML intro -> plain text."""
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def first_pdf(raw: str) -> str:
    """The Drucksache PDF the intro links to, if any."""
    m = re.search(r'href="(https?://[^"]*?\.pdf)"', raw or "")
    return m.group(1) if m else ""


def main():
    rows = []
    for leg in LEGISLATURES:
        page = 0
        while True:
            d = get(f"{API}/polls?field_legislature%5Bentity.id%5D={leg}"
                    f"&pager_limit=500&page={page}")
            for p in d["data"]:
                intro = p.get("field_intro") or ""
                rows.append({
                    "poll_id": p["id"],
                    "date": p.get("field_poll_date", ""),
                    "title": p.get("label", ""),
                    "topics": "|".join(t["label"] for t in p.get("field_topics") or []),
                    "committees": "|".join(c["label"] for c in p.get("field_committees") or []),
                    "drucksache_pdf": first_pdf(intro),
                    "intro": clean(intro),
                })
            total = d["meta"]["result"]["total"]
            if (page + 1) * 500 >= total or not d["data"]:
                break
            page += 1
            time.sleep(2.2)
        print(f"legislature {leg}: {len(rows)} rows so far", flush=True)
        time.sleep(2.2)

    rows.sort(key=lambda r: (r["date"], r["poll_id"]))
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    topics = {t for r in rows for t in r["topics"].split("|") if t}
    print(f"wrote {OUT} ({len(rows)} polls, {len(topics)} distinct topics)")
    print(f"polls with a Drucksache PDF link: {sum(1 for r in rows if r['drucksache_pdf'])}")


if __name__ == "__main__":
    main()
