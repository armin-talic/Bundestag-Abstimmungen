"""Backfill individual votes for every remaining roll-call poll (2005-present).

Fetches all polls in data/polls_all.csv that are not yet in any local vote
cache and appends them to data/votes_backfill.csv. Resumable: re-running
skips everything already downloaded. Rate-limited to ~25 requests/minute,
full backfill of ~570 polls takes roughly 2.5 hours.

Run from the project root:  python -u scripts/collect_backfill.py
"""

import csv
import json
import subprocess
import time
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
API = "https://www.abgeordnetenwatch.de/api/v2"
OUT = DATA / "votes_backfill.csv"
FIELDS = ["poll_id", "mandate_id", "politician", "fraction", "vote"]


def get(url: str, retries: int = 4):
    for attempt in range(retries):
        r = subprocess.run(
            ["curl", "-sS", "--ssl-no-revoke", "--compressed", "-m", "120", url],
            capture_output=True, text=True, encoding="utf-8")
        if r.returncode == 0:
            try:
                return json.loads(r.stdout)
            except json.JSONDecodeError:
                pass
        time.sleep(8)
    raise RuntimeError(f"failed after {retries} attempts: {url}")


def strip(label):
    return label.split(" (Bundestag")[0].strip() if label else ""


def main():
    polls = list(csv.DictReader(open(DATA / "polls_all.csv", encoding="utf-8")))
    have = set()
    for name in ["votes_selected.csv", "votes_2026.csv", "votes_backfill.csv"]:
        path = DATA / name
        if path.exists():
            have |= {r["poll_id"] for r in csv.DictReader(open(path, encoding="utf-8"))}
    todo = [p["poll_id"] for p in polls if p["poll_id"] not in have]
    print(f"{len(todo)} polls to fetch ({len(have)} already cached)", flush=True)

    new_file = not OUT.exists()
    with open(OUT, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        for i, pid in enumerate(todo, 1):
            votes, page = [], 0
            while True:
                d = get(f"{API}/votes?poll={pid}&pager_limit=100&page={page}")
                votes += d["data"]
                if not d["data"] or len(votes) >= d["meta"]["result"]["total"]:
                    break
                page += 1
                time.sleep(2.2)
            print(f"[{i}/{len(todo)}] poll {pid}: {len(votes)} votes", flush=True)
            for v in votes:
                w.writerow({
                    "poll_id": pid,
                    "mandate_id": (v.get("mandate") or {}).get("id", ""),
                    "politician": strip((v.get("mandate") or {}).get("label", "")),
                    "fraction": strip((v.get("fraction") or {}).get("label", "")),
                    "vote": v.get("vote", ""),
                })
            f.flush()
            time.sleep(2.2)
    print("done", flush=True)


if __name__ == "__main__":
    main()
