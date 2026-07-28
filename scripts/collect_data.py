"""Collect Bundestag roll-call vote data from the abgeordnetenwatch.de API v2.

Single data source (simplest option from the project plan):
  https://www.abgeordnetenwatch.de/api  (JSON, no auth, CC0 license, ~30 req/min)

Downloads:
  1. Metadata for all roll-call polls of the Bundestag legislatures since 2005
     -> data/polls_all.csv
  2. Individual MP votes (with party) for a curated set of polls
     -> data/votes_selected.csv, data/selected_polls.csv

Votes are saved incrementally (one poll at a time), so the script can be
interrupted and re-run; already-downloaded polls are skipped.

Run from the project root:  python -u scripts/collect_data.py

Note: uses curl for HTTP (with --compressed). Plain urllib was extremely slow
for the large votes responses on this machine; curl needs --ssl-no-revoke here
because schannel cannot reach the certificate revocation servers.
"""

import csv
import json
import subprocess
import sys
import time
from pathlib import Path

API = "https://www.abgeordnetenwatch.de/api/v2"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SLEEP_SECONDS = 2.2  # stay under the 30 requests/minute rate limit

# Bundestag legislature period IDs on abgeordnetenwatch (2005 -> present)
LEGISLATURES = {
    67: "Bundestag 2005 - 2009",
    83: "Bundestag 2009 - 2013",
    97: "Bundestag 2013 - 2017",
    111: "Bundestag 2017 - 2021",
    132: "Bundestag 2021 - 2025",
    161: "Bundestag 2025 - 2029",
}

# Curated polls. Categories:
#   spotlight   - chart 1: one issue, individual votes colored by party
#   major       - chart 2: landmark votes, party-level comparison
#   afghanistan - chart 3: recurring issue with the longest time span in the API
#                 (ISAF / Resolute Support mandate extension votes, 2006-2021)
#   lgbt        - LGBT+ rights milestone votes available as roll calls in the API
#                 (pre-2005 milestones and non-roll-call laws are NOT here; see
#                 data/lgbt_rights_milestones.csv for the full milestone list)
SELECTED_POLLS = {
    5496: ["spotlight", "major", "lgbt"],  # Selbstbestimmungsgesetz (2024-04-12)
    878: ["major"],    # Atomausstieg bis 2022 (2011-06-30)
    1052: ["major"],   # Flaechendeckender Mindestlohn 8,50 Euro (2014-07-03)
    1106: ["major"],   # 86 Mrd. Euro Kreditpaket fuer Griechenland (2015-08-19)
    1232: ["major", "lgbt"],  # Ehe fuer Alle (2017-06-30)
    4539: ["major"],   # Corona-Impfpflicht ab 60 (2022-04-07)
    4646: ["major"],   # Sondervermoegen Bundeswehr (2022-06-03)
    4826: ["major"],   # Einfuehrung des Buergergeldes (2022-11-10)
    5418: ["major"],   # Cannabisgesetz (2024-02-23)
    5864: ["major"],   # Zustrombegrenzungsgesetz (2025-01-31)
    5957: ["major"],   # Lockerung der Schuldenbremse (2025-03-18)
    # LGBT+ rights roll calls (beyond the two above)
    929: ["lgbt"],   # Recht auf Eheschliessung fuer gleichgeschl. Paare (2012-06-28)
    1048: ["lgbt"],  # Aenderungsantrag Sukzessivadoption durch Lebenspartner (2014-05-22)
    4146: ["lgbt"],  # Aufhebung Transsexuellengesetz / Selbstbestimmung (2021-05-19)
    # Afghanistan mandate extensions (ISAF, then Resolute Support)
    661: ["afghanistan"],   # 2006-09-28
    679: ["afghanistan"],   # 2007-10-12
    699: ["afghanistan"],   # 2008-10-16
    731: ["afghanistan"],   # 2009-12-03
    766: ["afghanistan"],   # 2010-02-26
    712: ["afghanistan"],   # 2011-01-28
    910: ["afghanistan"],   # 2012-01-26
    977: ["afghanistan"],   # 2013-01-31
    1011: ["afghanistan"],  # 2014-02-20
    1082: ["afghanistan"],  # 2014-12-19
    1146: ["afghanistan"],  # 2015-12-17
    1208: ["afghanistan"],  # 2016-12-15
    1245: ["afghanistan"],  # 2017-12-12
    1284: ["afghanistan"],  # 2018-03-22
    1660: ["afghanistan"],  # 2019-03-21
    3571: ["afghanistan"],  # 2020-03-13
    4085: ["afghanistan"],  # 2021-03-25
}

VOTE_FIELDS = ["poll_id", "mandate_id", "politician", "fraction", "vote"]


def get_json(url: str, retries: int = 3) -> dict:
    for attempt in range(retries):
        r = subprocess.run(
            ["curl", "-sS", "--ssl-no-revoke", "--compressed", "-m", "120", url],
            capture_output=True, text=True, encoding="utf-8",
        )
        if r.returncode == 0:
            try:
                return json.loads(r.stdout)
            except json.JSONDecodeError as e:
                err = str(e)
        else:
            err = r.stderr.strip()
        print(f"  retry {attempt + 1}/{retries} after error: {err}", flush=True)
        time.sleep(5)
    raise RuntimeError(f"failed after {retries} attempts: {url}")


def fetch_paginated(endpoint: str, params: str) -> list:
    results, page = [], 0
    while True:
        payload = get_json(f"{API}/{endpoint}?{params}&pager_limit=500&page={page}")
        results.extend(payload["data"])
        total = payload["meta"]["result"]["total"]
        if (page + 1) * 500 >= total or not payload["data"]:
            return results
        page += 1
        time.sleep(SLEEP_SECONDS)


def strip_period_suffix(label: str) -> str:
    """'SPD (Bundestag 2021 - 2025)' -> 'SPD'"""
    return label.split(" (Bundestag")[0].strip() if label else ""


def collect_polls(path: Path) -> None:
    if path.exists():
        print(f"skip (exists): {path.name}", flush=True)
        return
    rows = []
    for leg_id, leg_label in LEGISLATURES.items():
        polls = fetch_paginated("polls", f"field_legislature%5Bentity.id%5D={leg_id}")
        print(f"{leg_label}: {len(polls)} polls", flush=True)
        for p in polls:
            rows.append({
                "poll_id": p["id"],
                "date": p.get("field_poll_date", ""),
                "legislature_id": leg_id,
                "legislature": leg_label,
                "title": p.get("label", ""),
                "accepted": p.get("field_accepted", ""),
                "url": (p.get("abgeordnetenwatch_url") or ""),
            })
        time.sleep(SLEEP_SECONDS)
    rows.sort(key=lambda r: (r["date"], r["poll_id"]))
    write_csv(path, rows)


def already_downloaded(votes_path: Path) -> set:
    if not votes_path.exists():
        return set()
    with open(votes_path, encoding="utf-8") as f:
        return {int(row["poll_id"]) for row in csv.DictReader(f)}


def collect_votes(votes_path: Path, selected_path: Path) -> None:
    done = already_downloaded(votes_path)
    poll_meta = []
    new_file = not votes_path.exists()
    with open(votes_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=VOTE_FIELDS)
        if new_file:
            writer.writeheader()
        for i, (poll_id, categories) in enumerate(SELECTED_POLLS.items(), 1):
            if poll_id in done:
                print(f"[{i}/{len(SELECTED_POLLS)}] poll {poll_id}: already downloaded", flush=True)
                continue
            # The votes endpoint caps pager_limit at 100, so page through
            votes, page = [], 0
            while True:
                payload = get_json(f"{API}/votes?poll={poll_id}&pager_limit=100&page={page}")
                votes.extend(payload["data"])
                total = payload["meta"]["result"]["total"]
                if not payload["data"] or len(votes) >= total:
                    break
                page += 1
                time.sleep(SLEEP_SECONDS)
            poll_label = (votes[0].get("poll") or {}).get("label", "") if votes else ""
            print(f"[{i}/{len(SELECTED_POLLS)}] poll {poll_id} ({poll_label}): {len(votes)} votes", flush=True)
            for v in votes:
                writer.writerow({
                    "poll_id": poll_id,
                    "mandate_id": (v.get("mandate") or {}).get("id", ""),
                    "politician": strip_period_suffix((v.get("mandate") or {}).get("label", "")),
                    "fraction": strip_period_suffix((v.get("fraction") or {}).get("label", "")),
                    "vote": v.get("vote", ""),
                })
            f.flush()
            time.sleep(SLEEP_SECONDS)
    # (re)write the curated poll list with categories, titles from polls_all.csv
    titles = {}
    with open(DATA_DIR / "polls_all.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            titles[int(row["poll_id"])] = (row["title"], row["date"])
    for poll_id, categories in SELECTED_POLLS.items():
        title, date = titles.get(poll_id, ("", ""))
        poll_meta.append({
            "poll_id": poll_id,
            "date": date,
            "title": title,
            "categories": ";".join(categories),
        })
    poll_meta.sort(key=lambda r: r["date"])
    write_csv(selected_path, poll_meta)


def write_csv(path: Path, rows: list) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {path} ({len(rows)} rows)", flush=True)


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    collect_polls(DATA_DIR / "polls_all.csv")
    collect_votes(DATA_DIR / "votes_selected.csv", DATA_DIR / "selected_polls.csv")
    print("done", flush=True)


if __name__ == "__main__":
    sys.exit(main())
