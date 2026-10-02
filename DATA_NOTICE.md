# Data notice

Data: Sportmonks. Transfermarkt for squad values and verification; premierleague.com for verification.

- Everything in `data/` is in our own derived CSV format (the analysis outputs also as JSON, Markdown and PNG). No raw
  provider files are distributed: no Sportmonks API responses, no Transfermarkt pages, squad pages or transfer
  histories, no premierleague.com match pages or extracts of them.
- Reconciliation against Transfermarkt and premierleague.com was run on the providers' pages; every correction is listed in the ledger with its source URL; the published inputs are the reconciled ones. (The ledger is `data/inputs/reconciled/ledger.csv`, column `source_url`. Twelve corrections rest on Sportmonks' own matchday namings rather than an outside page; for them the ledger's `basis` and `verdict` columns give the evidence.)
- The files shipped:
  - `data/tables/`: club and player tables per season, 2018/19-2025/26, sideways adjustment on and off.
  - `data/calibration/`, `data/analyses/`: the calibration and the analysis battery on the 7-season set (2018/19, 2019/20,
    2021/22-2025/26) and its 2020/21 variant.
  - `data/abstract_numbers.csv`: every number in the submitted abstract, with the file and line it is read from.
  - `data/inputs/reconciled/`: the reconciled inputs (late set: squads, transfers, appearances, events, contracts), the
    exclusions (`retention_overrides.csv`), the origin fills (`origin_overrides.csv`), `placeholder_origin_arrivals.csv`
    and the ledger.
  - `data/inputs/sportmonks/`: the Sportmonks tables of the late set before reconciliation (appearances, events,
    fixtures, squads, transfers, contracts, contracts_no_dated_record, teams), and `standings.csv`, `league_seasons.csv`,
    `team_transfers.csv` (final positions and points, season ids, the countries of the clubs in transfer records).
  - `data/inputs/matchday/late/`: appearances, events and fixtures corrected against premierleague.com match pages.
  - `data/inputs/transfermarkt/`: `club_season_values.csv` (squad values on 1 July) and the Sportmonks-Transfermarkt
    club id files `club_ids_primary.csv`, `club_ids_secondary.csv`.
  - `data/inputs/review/`: the verdict files (`verdicts/round1.csv`, `round2.csv`, `gapfill.csv`, `gapfill_cases.csv`)
    and `player_names_verified.csv`.
  - `data/inputs/tests/transfers_testC_5rows.csv`: a five-row synthetic test input.
- Sources:
  - Sportmonks football API (https://www.sportmonks.com): fixtures, matchday squads, minutes, events, teams, squads,
    transfers, contracts, standings.
  - Transfermarkt (https://www.transfermarkt.co.uk): squad market values on 1 July of each season (the dated competition
    pages listed in `data/DATA_DICTIONARY.md`); squad pages and transfer histories, used to check Sportmonks' squads and
    transfers.
  - premierleague.com (https://www.premierleague.com): match pages (matchday squads and minutes), used to check and
    correct Sportmonks' matchday data.
  - Club, league and press sources cited in the verdict files and the ledger, by URL.
- Player names in the input files are the providers' labels and may be wrong or abbreviated. Verified names are in the
  player tables (`data/tables/`), with the column `name_verified` (yes / no).
- Published seasons: 2018/19-2025/26 (2020/21 as robustness only). The input files keep the earlier records the published
  seasons need: 2017/18 matchdays for the xU window, standings from 2013/14 for the seed pots, and transfer and contract
  records of earlier years for arrival dates and origins. They also keep squad values 2014/15–2017/18 and a few earlier
  rule and exclusion records (kept as published context; not used by the 2018/19–2025/26 run). One exception: the 60
  West Ham United exclusions in `retention_overrides.csv` are dated from 2014-07-01 but are open-ended, so the run does
  use them: each excludes one player at West Ham United for every fixture of every published season.
- Retained, as used throughout `data/`, means contracted or on loan at the club, not loaned out. A player retained for a
  fixture but not named in the matchday squad counts as absent (see `data/DATA_DICTIONARY.md`).
- The data in `data/` are licensed under CC BY-NC 4.0 (LICENSE-DATA). The code is licensed under MIT (LICENSE).
