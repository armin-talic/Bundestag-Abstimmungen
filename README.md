# Bundestag Abstimmungen

Interaktiver Explorer der namentlichen Abstimmungen im Deutschen Bundestag,
gebaut aus jeder einzeln erfassten Stimme seit 2005.

**➡️ [Dashboard öffnen](https://armin-talic.github.io/Bundestag-Abstimmungen/web/)**

## Inhalt

**Tab „Abstimmungen"** – das Plenum als Sitzverteilung (ein Punkt je
Abgeordnete/r), die Sitzverteilung als Balken, Ja-Stimmen je Fraktion
(absolut oder als Anteil) sowie Ranglisten der einigsten und der
umstrittensten Abstimmungen. Wird eine einzelne Abstimmung gewählt, zeigt der
Sitzplan genau diese Abstimmung: die Seite, die sich durchgesetzt hat, bleibt
farbig, der Rest wird abgeblendet.

**Tab „Partei"** – das Abstimmungsverhalten je Fraktion (Ja / Nein /
Enthaltung / Nicht abgegeben als Anteil aller Mandate), die Erfolgsquote jeder
Fraktion (wie oft das Ergebnis ihrer Mehrheitsposition entsprach) und ein
Venn-Raster der paarweisen Übereinstimmung. Ein Klick auf ein Paar listet die
Abstimmungen, bei denen beide einig bzw. uneinig waren.

Filter durchgehend: Wahlperiode, Thema (offizielle abgeordnetenwatch-
Taxonomie), Ergebnis und die einzelne Abstimmung.

## Daten

**666 namentliche Abstimmungen, 2005–2026, vollständig** – alle namentlichen
Abstimmungen des 16. bis 21. Bundestages mit der Einzelstimme jeder/jedes
Abgeordneten (rund 420.000 Stimmdatensätze).

| Wahlperiode | Abstimmungen |
|---|---|
| 2005–2009 | 50 |
| 2009–2013 | 94 |
| 2013–2017 | 121 |
| 2017–2021 | 176 |
| 2021–2025 | 162 |
| 2025–2029 | 63 |

### Quellen

- **[abgeordnetenwatch.de API v2](https://www.abgeordnetenwatch.de/api)** (CC0)
  – Hauptquelle. Einzelstimmen je Abgeordnete/r, offizielle Themen-Tags,
  Kurzbeschreibungen und Links auf die Drucksache (PDF) bei
  dserver.bundestag.de.
- **[BTVote V2](https://dataverse.harvard.edu/dataverse/btvote)**
  (Sieberer et al., Harvard Dataverse, CC0) – für einzelne historische
  Abstimmungen vor der API-Abdeckung (§175-Reformen 1969 und 1973, AGG 2006).
  Deckt 1949–2021 vollständig ab und ist der naheliegende Weg, das Projekt
  weiter zurück zu erweitern.

Der BTVote-Rohdatensatz liegt **nicht** im Repository: die Datei mit dem
Abstimmungsverhalten ist 224 MB groß und überschreitet das 100-MB-Limit von
GitHub. Bei Bedarf von Dataverse nachladen (`doi:10.7910/DVN/24U1FR`,
File-ID 6402445) nach `data/btvote/`. Der tatsächlich genutzte Auszug liegt
als `data/btvote_votes_selected.csv` im Repository.

## Aufbau

```
web/
  index.html            das Dashboard (diese Datei öffnen)
  data.js               vorberechnete Daten, generiert – nicht von Hand ändern
scripts/
  collect_data.py       kuratierte Abstimmungen aus der abgeordnetenwatch-API
  collect_backfill.py   alle übrigen Abstimmungen (fortsetzbar, rate-limitiert)
  collect_poll_meta.py  offizielle Themen, Kurztexte, Drucksachen-Links
  extract_btvote.py     historische Abstimmungen aus dem BTVote-Datensatz
  build_web_data.py     erzeugt web/data.js aus den CSV-Dateien
  build_politician_comparison.py
data/                   gesammelte CSV-Dateien
```

## Neu aufbauen

```bash
python -u scripts/collect_backfill.py    # fehlende Stimmen nachladen (fortsetzbar)
python -u scripts/collect_poll_meta.py   # Themen + Drucksachen-Links
python -u scripts/build_web_data.py      # web/data.js neu erzeugen
```

`build_web_data.py` gibt die Abdeckung je Wahlperiode aus, sodass sichtbar
ist, was noch fehlt. Nach dem Neuaufbau den `?v=`-Parameter am `data.js`-
Script-Tag in `index.html` hochzählen, damit der Browser-Cache nicht greift.

## Hinweise

- Nur namentliche Abstimmungen werden je Abgeordnete/r erfasst. Die meisten
  Entscheidungen fallen per Handzeichen und hinterlassen keinen Einzelnachweis;
  mehrere zentrale Gesetze (Lebenspartnerschaft 2001, Verbot der
  Konversionstherapie 2020 u. a.) haben deshalb nirgends personenscharfe Daten.
  `data/lgbt_rights_milestones.csv` hält fest, welche Meilensteine eine
  namentliche Abstimmung hatten und welche nicht.
- Prozentwerte folgen der amtlichen Bezugsgröße: *abgegebene Stimmen* =
  Ja + Nein + Enthaltung. Nach Art. 42 Abs. 2 GG werden Enthaltungen erfasst,
  zählen aber nicht für die Mehrheit; nicht abgegebene Stimmen liegen außerhalb
  der Wertung.
- Verbreitete Zusammenfassungen weichen teils vom amtlichen Ergebnis ab (das
  Selbstbestimmungsgesetz 2024 lautete 372/251/11, nicht 408/272). Hier gelten
  die amtlichen Zahlen.

## Lizenz

Code MIT. Die zugrunde liegenden Abstimmungsdaten stehen unter CC0
(abgeordnetenwatch.de, BTVote); Bundestagsprotokolle sind amtliche Werke nach
§ 5 UrhG.
