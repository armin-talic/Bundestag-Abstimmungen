"""Extract individual MP votes for selected historical roll calls from BTVote.

Source (second source of the project, used only for votes that predate or are
missing from abgeordnetenwatch.de):
  BTVote V2 datasets, Sieberer et al., Harvard Dataverse, license CC0 1.0
  - Voting behavior: doi:10.7910/DVN/24U1FR (file voting_behavior_V2_19492021.dta)
  - Vote characteristics: doi:10.7910/DVN/AHBBXY

Requires the raw files in data/btvote/ (downloaded via the Dataverse API, see
README) and pandas. Writes data/btvote_votes_selected.csv.

Run from anywhere:  python -u scripts/extract_btvote.py
"""

import csv
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW = DATA_DIR / "btvote" / "voting_behavior_V2_19492021.dta"
CHARACTERISTICS = DATA_DIR / "btvote" / "vote_characteristics_V2_19492021.tab"
OUT = DATA_DIR / "btvote_votes_selected.csv"

# LGBT+ rights milestone roll calls (vote_id in BTVote V2)
SELECTED_VOTE_IDS = {
    5013,   # 1969-05-07  2. StrRG, second reading, § 12 committee version
    5014,   # 1969-05-09  1. StrRG final passage (incl. partial decriminalization
            #             of adult male homosexuality, reform of § 175 StGB)
    5015,   # 1969-05-09  2. StrRG final passage
    7003,   # 1973-06-07  4. StrRG final passage (sexual criminal law reform,
            #             lowered age of consent for homosexual acts)
    16021,  # 2006-06-29  AGG / General Equal Treatment Act final passage
    18213,  # 2017-06-30  Ehe fuer alle (also in abgeordnetenwatch; kept here to
            #             cross-validate the two sources)
}

COLUMNS = ["vote_id", "vote_date", "id_de_parliament", "lastname", "firstname",
           "elecper", "ppg", "party_text", "vote_beh"]


def main() -> None:
    titles = {}
    with open(CHARACTERISTICS, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            titles[int(row["vote_id"])] = row["vote_title"]

    # single full read (not chunked) so Stata value labels resolve consistently
    df = pd.read_stata(RAW, columns=COLUMNS)
    df = df[df["vote_id"].isin(SELECTED_VOTE_IDS)].copy()

    df["vote_id"] = df["vote_id"].astype(int)
    df["id_de_parliament"] = df["id_de_parliament"].astype("int64")
    df["vote_title"] = df["vote_id"].map(titles)
    df = df.rename(columns={"ppg": "party_group", "vote_beh": "vote"})
    df = df[["vote_id", "vote_date", "vote_title", "id_de_parliament",
             "lastname", "firstname", "elecper", "party_group", "party_text", "vote"]]
    df = df.sort_values(["vote_date", "lastname", "firstname"])
    df.to_csv(OUT, index=False, encoding="utf-8")
    print(f"wrote {OUT} ({len(df)} rows)")
    print(df.groupby(["vote_date", "vote"], observed=True).size())


if __name__ == "__main__":
    main()
