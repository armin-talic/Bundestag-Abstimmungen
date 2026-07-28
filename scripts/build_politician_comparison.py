"""Build a key-politician comparison across LGBT+ rights milestone roll calls.

Reads the two individual-vote datasets (abgeordnetenwatch + BTVote) and writes
data/key_politicians_milestone_votes.csv: one row per politician per milestone
roll call, with the recorded vote or 'not in Bundestag'.

Only roll-call votes can appear here. Milestones that never had a roll call
(Civil Partnerships 2000, Conversion Therapy Ban 2020, etc.) have no recorded
individual votes at all - see data/lgbt_rights_milestones.csv.

Run after collect_data.py and extract_btvote.py:
  python -u scripts/build_politician_comparison.py
"""

import csv
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

POLITICIANS = [
    ("Olaf", "Scholz"),
    ("Angela", "Merkel"),
    ("Friedrich", "Merz"),
    ("Christian", "Lindner"),
    ("Annalena", "Baerbock"),
    ("Robert", "Habeck"),
    ("Alice", "Weidel"),
    ("Jens", "Spahn"),
]

# (source, id, date, short label) - chronological
MILESTONE_VOTES = [
    ("btvote", "5014", "1969-05-09", "Partial decriminalization Paragraph 175 (1. StrRG)"),
    ("btvote", "7003", "1973-06-07", "Sexual criminal law reform (4. StrRG)"),
    ("btvote", "16021", "2006-06-29", "General Equal Treatment Act (AGG)"),
    ("aw", "929", "2012-06-28", "Same-sex marriage motion (rejected)"),
    ("aw", "1048", "2014-05-22", "Successive adoption amendment (rejected)"),
    ("aw", "1232", "2017-06-30", "Marriage for all (Ehe fuer alle)"),
    ("aw", "4146", "2021-05-19", "TSG repeal / self-determination bill (rejected)"),
    ("aw", "5496", "2024-04-12", "Self-Determination Act (SBGG)"),
]


def load_aw() -> dict:
    """{(poll_id, 'First Last'): (vote, fraction)}"""
    out = {}
    with open(DATA_DIR / "votes_selected.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out[(row["poll_id"], row["politician"])] = (row["vote"], row["fraction"])
    return out


def load_btvote() -> dict:
    out = {}
    with open(DATA_DIR / "btvote_votes_selected.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = f'{row["firstname"]} {row["lastname"]}'
            out[(row["vote_id"], name)] = (row["vote"], row["party_group"])
    return out


def main() -> None:
    aw, bt = load_aw(), load_btvote()
    rows = []
    for source, vote_id, date, label in MILESTONE_VOTES:
        lookup = aw if source == "aw" else bt
        for first, last in POLITICIANS:
            name = f"{first} {last}"
            vote, party = lookup.get((vote_id, name), ("not in Bundestag", ""))
            rows.append({
                "vote_date": date,
                "milestone": label,
                "source": "abgeordnetenwatch" if source == "aw" else "btvote",
                "vote_id": vote_id,
                "politician": name,
                "party": party,
                "vote": vote,
            })
    out = DATA_DIR / "key_politicians_milestone_votes.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
