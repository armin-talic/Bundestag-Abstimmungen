"""Build web/data.js for the D3.js vote explorer (web/index.html).

Packages every poll with locally collected individual votes (data/
votes_selected.csv + data/votes_2026.csv) into one JS file:
  window.VOTE_DATA = { parties: {...}, polls: [...] }

Each poll carries: id, date, year, German title, English title, topics,
result, per-party tallies, and the individual seats (party + vote per MP)
used to draw the hemicycle.

Run from the project root:  python -u scripts/build_web_data.py
"""

import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "web" / "data.js"

PARTY_COLORS = {
    "CDU/CSU": "#000000",
    "SPD": "#E3000F",
    "Grüne": "#1AA037",
    "FDP": "#FFCC00",
    "Die Linke": "#BE3075",
    "AfD": "#009EE0",
    "BSW": "#7D254F",
    "Fraktionslos": "#9E9E9E",
}
SEATING_ORDER = ["Die Linke", "BSW", "SPD", "Grüne", "FDP",
                 "CDU/CSU", "AfD", "Fraktionslos"]
VOTE_ORDER = ["yes", "no", "abstain", "no_show"]

# topic tags per poll (hand-curated; a poll can have several)
TOPICS = {
    # Afghanistan mandate series
    **{pid: ["Defense & foreign policy"] for pid in
       [661, 679, 699, 731, 766, 712, 910, 977, 1011, 1082, 1146, 1208,
        1245, 1284, 1660, 3571, 4085]},
    # LGBT+ rights roll calls
    929: ["Society & rights"], 1048: ["Society & rights"],
    1232: ["Society & rights"], 4146: ["Society & rights"],
    5496: ["Society & rights"],
    # majors
    878: ["Climate & energy"], 1052: ["Social policy", "Economy & taxes"],
    1106: ["Economy & taxes"], 4539: ["Health"],
    4646: ["Defense & foreign policy"], 4826: ["Social policy"],
    5418: ["Society & rights", "Health"], 5864: ["Migration"],
    5957: ["Economy & taxes"],
    # 2026 (collected so far)
    6388: ["Defense & foreign policy"], 6391: ["Society & rights"],
    6419: ["Migration"], 6422: ["Social policy"],
    6451: ["Climate & energy", "Economy & taxes"], 6452: ["Migration"],
    6455: ["Economy & taxes"], 6495: ["Economy & taxes"],
    6496: ["Economy & taxes"], 6497: ["Economy & taxes"],
    6498: ["Economy & taxes", "Climate & energy"],
    6511: ["Economy & taxes"], 6528: ["Health"],
    6540: ["Defense & foreign policy"], 6541: ["Defense & foreign policy"],
    6551: ["Social policy"], 6552: ["Climate & energy"],
    6566: ["Society & rights"], 6575: ["Defense & foreign policy"],
    6598: ["Defense & foreign policy"], 6600: ["Climate & energy"],
    6601: ["Health"], 6605: ["Climate & energy"], 6606: ["Social policy"],
    # 2025 polls of the 2025-2029 term
    6147: ["Defense & foreign policy"], 6165: ["Climate & energy"],
    6146: ["Defense & foreign policy"], 6148: ["Defense & foreign policy"],
    6151: ["Climate & energy"], 6155: ["Migration"], 6170: ["Health"],
    6249: ["Climate & energy"], 6250: ["Economy & taxes"],
    6251: ["Economy & taxes"], 6280: ["Migration"],
    6284: ["Defense & foreign policy"], 6285: ["Defense & foreign policy"],
    6286: ["Climate & energy"],
    6278: ["Economy & taxes", "Climate & energy"], 6311: ["Social policy"],
    6315: ["Health"], 6316: ["Health", "Migration"],
    6318: ["Defense & foreign policy"], 6319: ["Defense & foreign policy"],
    6323: ["Economy & taxes"], 6324: ["Economy & taxes", "Climate & energy"],
    6326: ["Climate & energy"], 6327: ["Climate & energy"],
    6329: ["Climate & energy"], 6330: ["Health"],
    6346: ["Economy & taxes"], 6351: ["Economy & taxes"],
    6353: ["Migration"], 6354: ["Economy & taxes", "Climate & energy"],
    6355: ["Climate & energy"], 6356: ["Social policy"],
    6357: ["Migration"], 6359: ["Defense & foreign policy"],
    6360: ["Defense & foreign policy"], 6361: ["Defense & foreign policy"],
    6371: ["Society & rights"], 6372: ["Economy & taxes"],
    6373: ["Society & rights"],
}

ENGLISH = {
    878: "Nuclear phase-out by 2022",
    1052: "Nationwide minimum wage of 8.50 euros",
    1106: "86 billion euro credit package for Greece",
    1232: "Marriage for all (same-sex marriage)",
    4539: "Covid vaccine mandate for people 60 and older",
    4646: "100 billion euro special fund for the Bundeswehr",
    4826: "Introduction of the Buergergeld benefit system",
    5418: "Cannabis legalization act",
    5496: "Self-Determination Act (gender self-identification)",
    5864: "Migration Influx Limitation Act",
    5957: "Loosening of the constitutional debt brake",
    929: "Right to marriage for same-sex couples (motion, rejected)",
    1048: "Successive adoption by registered partners (amendment, rejected)",
    4146: "Repeal of the Transsexuals Act / self-determination bill (rejected)",
    661: "Extension of the Afghanistan mission (ISAF), 2006",
    679: "Extension of the Afghanistan mission (ISAF, Tornado), 2007",
    699: "Extension of the Afghanistan mission (ISAF), 2008",
    731: "Extension of the Afghanistan mission (ISAF), 2009",
    766: "Extension of the Afghanistan mission (ISAF), 2010",
    712: "Extension of the Afghanistan mission (ISAF), 2011",
    910: "Extension of the Afghanistan mission (ISAF), 2012",
    977: "Extension of the Afghanistan mission (ISAF), 2013",
    1011: "Continuation of the Afghanistan mission (ISAF), Feb 2014",
    1082: "Bundeswehr mission in Afghanistan (Resolute Support), Dec 2014",
    1146: "Extension of the Afghanistan mission, 2015",
    1208: "Extension of the Afghanistan mission, 2016",
    1245: "Extension of the Afghanistan mission, 2017",
    1284: "Expansion of the Bundeswehr training mission in Afghanistan, 2018",
    1660: "Extension of the Afghanistan mission, 2019",
    3571: "Continuation of the Afghanistan mission, 2020",
    4085: "Continuation of the Afghanistan mission, 2021",
    6388: "Extension of the Bundeswehr mission in Iraq (committee recommendation)",
    6391: "Abolishing the criminal offence of insulting politicians",
    6419: "Adapting national law to the reformed Common European Asylum System",
    6422: "Restructuring Buergergeld into the new basic income support (SGB II)",
    6452: "No further reform of citizenship law (committee recommendation)",
    6451: "Motion on energy price shocks from the Iran war (committee recommendation)",
    6455: "Raising the workplace threshold for appointing safety officers",
    6495: "Temporary cut of the energy tax on motor fuels",
    6496: "Rejection of a motion against a windfall profits tax (committee recommendation)",
    6497: "Rejection of a motion to raise the commuter allowance (committee recommendation)",
    6498: "Amendment of the Electricity Tax Act and other provisions",
    6511: "No stronger safeguarding of the EU funding programme LEADER (committee recommendation)",
    6528: "Initiative on the future of pharmacy services rejected (committee recommendation)",
    6540: "Continuation of Bundeswehr participation in EUFOR ALTHEA in Bosnia and Herzegovina",
    6541: "Continuation of the Bundeswehr KFOR mission in Kosovo",
    6551: "Rejection of a comprehensive BAfoeG student aid reform (committee recommendation)",
    6552: "New emission caps for the years 2031 to 2040",
    6566: "Stricter rules for acknowledgment of paternity",
    6575: "Final extension of the Bundeswehr mission in Lebanon",
    6598: "Additional military and humanitarian support for Ukraine",
    6600: "Introduction of a general speed limit",
    6601: "Statutory health insurance (GKV) reform",
    6605: "Building Modernization Act",
    6606: "Sports Funding Act",
    6147: "Continuation of the Bundeswehr mission in Bosnia and Herzegovina (EUFOR ALTHEA), 2025",
    6165: "Rejection of the Green motion against reactivating the Nord Stream pipelines",
    6146: "Continuation of the Bundeswehr mission off the Lebanese coast (UNIFIL)",
    6148: "Continued Bundeswehr participation in KFOR in Kosovo, 2025",
    6151: "Amendment of the General Railway Act",
    6155: "Suspension of family reunification for persons with subsidiary protection",
    6170: "No committee of inquiry into the handling of the Covid pandemic (committee recommendation)",
    6249: "No halt to dismantling shut-down nuclear power plants (committee recommendation)",
    6250: "Budget of the Chancellor and the Chancellery, 2025",
    6251: "Budget Act 2025",
    6280: "Amendment of the Citizenship Act",
    6284: "Continuation of the Bundeswehr mission in the Red Sea (EUNAVFOR ASPIDES)",
    6285: "Extension of the Bundeswehr mission in South Sudan (UNMISS)",
    6286: "No repeal of the combustion-engine ban (committee recommendation)",
    6278: "No reintroduction of the agricultural diesel rebate (committee recommendation)",
    6311: "Rent usury act",
    6315: "Amendment of the International Health Regulations",
    6316: "No restriction of medical care for foreigners (committee recommendation)",
    6318: "Extension of Bundeswehr participation in Operation SEA GUARDIAN in the Mediterranean",
    6319: "Continued Bundeswehr participation in EUNAVFOR MED IRINI in the Mediterranean",
    6323: "Modernization and digitalization of the fight against undeclared work",
    6324: "Energy Tax and Electricity Tax Act (amendment motion)",
    6326: "Act to remove climate protection measures and restore energy infrastructure",
    6327: "Constitutional amendment on climate policy rollback",
    6329: "Subsidy for transmission grid costs for 2026",
    6330: "Amendment of the Veterinary Medicines Act and the Pharmacy Act",
    6346: "Budget of the Chancellor and the Chancellery, 2026",
    6351: "Final vote on the Budget Act 2026",
    6353: "Issue visas to Afghan nationals with admission commitments",
    6354: "Taxation of luxury flights",
    6355: "No abolition of CO2 pricing (committee recommendation)",
    6356: "Stabilization of the pension level and equal treatment of child-raising periods",
    6357: "New rules on safe countries of origin and abolition of legal counsel in deportation detention",
    6359: "Modernization of military service",
    6360: "Frozen Russian state assets not to be made available to Ukraine (committee recommendation)",
    6361: "Not banning Russian nuclear business in Germany (committee recommendation)",
    6371: "Rejection of objections against the 2025 federal election (committee recommendation)",
    6372: "Rejection of removing tax privileges for the largest inheritances (committee recommendation)",
    6373: "Strengthening consumer rights in digital contracts",
}


def normalize_party(fraction: str) -> str:
    f = (fraction or "").upper()
    if "CDU" in f:
        return "CDU/CSU"
    if "SPD" in f:
        return "SPD"
    if "90" in f or "GRÜN" in f:
        return "Grüne"
    if "FDP" in f:
        return "FDP"
    if "LINKE" in f:
        return "Die Linke"
    if "AFD" in f:
        return "AfD"
    if "BSW" in f:
        return "BSW"
    return "Fraktionslos"


def main() -> None:
    polls_meta = {}
    with open(DATA / "polls_all.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            polls_meta[int(row["poll_id"])] = row

    # official abgeordnetenwatch taxonomy + bill context (scripts/collect_poll_meta.py)
    official = {}
    meta_path = DATA / "polls_meta.csv"
    if meta_path.exists():
        with open(meta_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                official[int(row["poll_id"])] = row

    votes = []
    for name in ["votes_selected.csv", "votes_2026.csv", "votes_backfill.csv"]:
        path = DATA / name
        if path.exists():
            with open(path, encoding="utf-8") as f:
                votes.extend(csv.DictReader(f))

    by_poll = {}
    for v in votes:
        by_poll.setdefault(int(v["poll_id"]), []).append(v)

    name_ids: dict[str, int] = {}
    polls_out = []
    for pid, rows in sorted(by_poll.items(), key=lambda kv: polls_meta[kv[0]]["date"]):
        meta = polls_meta[pid]
        seating_rank = {p: i for i, p in enumerate(SEATING_ORDER)}
        vote_rank = {"yes": 0, "no": 1, "abstain": 2, "no_show": 3}
        seats = sorted(
            ({"party": normalize_party(v["fraction"]),
              "vote": v["vote"],
              "name": v["politician"]} for v in rows),
            key=lambda s: (seating_rank[s["party"]], vote_rank.get(s["vote"], 9), s["name"]),
        )
        party_tally = {}
        for s in seats:
            party_tally.setdefault(s["party"], Counter())[s["vote"]] += 1
        # strip soft hyphens that appear in some Bundestag titles
        title = re.sub("­", "", meta["title"]).strip()
        om = official.get(pid, {})
        # prefer the official abgeordnetenwatch taxonomy; fall back to the
        # hand-curated tags for anything it does not classify
        topics = [t for t in (om.get("topics") or "").split("|") if t] \
            or TOPICS.get(pid, ["Other"])
        for s in seats:                       # intern the seat strings
            name_ids.setdefault(s["name"], len(name_ids))
        polls_out.append({
            "id": pid,
            "date": meta["date"],
            "year": int(meta["date"][:4]),
            "title_de": title,
            "title_en": ENGLISH.get(pid, ""),
            "topics": topics,
            "accepted": meta["accepted"].lower() in ("true", "1"),
            "url": meta.get("url", ""),   # abgeordnetenwatch page for the vote
            "legislature": meta.get("legislature", ""),  # e.g. "Bundestag 2021 - 2025"
            "intro": om.get("intro", "")[:600],
            "drucksache": om.get("drucksache_pdf", ""),
            "committees": [c for c in (om.get("committees") or "").split("|") if c],
            "parties": [
                {"party": p, **{k: c.get(k, 0) for k in vote_rank}}
                for p, c in sorted(party_tally.items(),
                                   key=lambda kv: seating_rank[kv[0]])
            ],
            # packed as [partyIdx, voteIdx, nameIdx] triples; index.html expands
            # these back into objects on load. Keeps the file a third of the
            # size once all 666 polls are in.
            "seats_packed": [
                [SEATING_ORDER.index(s["party"]),
                 VOTE_ORDER.index(s["vote"]) if s["vote"] in VOTE_ORDER else 3,
                 name_ids[s["name"]]]
                for s in seats
            ],
        })

    # data coverage: how many roll calls exist per legislature in polls_all
    # vs how many have individual votes collected locally
    total_per_leg = Counter(m["legislature"] for m in polls_meta.values())
    collected_per_leg = Counter(polls_meta[p["id"]]["legislature"] for p in polls_out)
    coverage = [
        {"legislature": leg, "total": total_per_leg[leg],
         "collected": collected_per_leg.get(leg, 0)}
        for leg in sorted(total_per_leg)
    ]

    payload = {
        "generated_from": "abgeordnetenwatch.de API v2 (CC0)",
        "party_colors": PARTY_COLORS,
        "seating_order": SEATING_ORDER,
        "vote_order": VOTE_ORDER,
        "name_table": list(name_ids),      # dicts keep insertion order
        "coverage": coverage,
        "polls": polls_out,
    }
    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("window.VOTE_DATA = ")
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.1f} MB, {len(polls_out)} polls)")


if __name__ == "__main__":
    main()
