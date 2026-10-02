# NETavailability

NETavailability measures how much of its expected playing strength a Premier League club had available, season by season.
Availability is read from matchday squad sheets: a player who was retained (contracted or on loan at the club, not loaned out) for a fixture but not named in the squad counts as absent.
Each absence is weighted by that player's expected usage (xU: the mean share of the match he played over his last 12 named squads), so a missing regular costs more than a missing fringe player.

For each club-season: RET = expected minutes of the retained players, NET = expected minutes of the named players, NETavailability = NET ÷ RET, and NETabsence = RET − NET.

The pipeline covers 2014/15–2025/26; this release and the abstract use 2018/19–2025/26 (2020/21 as robustness only). Earlier seasons were computed as an out-of-sample check and will be reported in the full paper.

Data: Sportmonks (https://www.sportmonks.com): fixtures, matchday squads, minutes, events, teams, squads, transfers, contracts, standings. Transfermarkt (https://www.transfermarkt.co.uk) for squad values and verification; premierleague.com (https://www.premierleague.com) for verification. All data in `data/` are in our own derived CSV format; no raw provider files are included (DATA_NOTICE.md).

Reconciliation against Transfermarkt and premierleague.com was run on the providers' pages; every correction is listed in the ledger with its source URL; the published inputs are the reconciled ones. (The ledger is `data/inputs/reconciled/ledger.csv`, column `source_url`. Twelve corrections rest on Sportmonks' own matchday namings rather than an outside page; for them the ledger's `basis` and `verdict` columns give the evidence.)

## Repository

```
run.py                      one command from the input files to the tables, checks and analyses
config/settings.toml        every setting: constants, rule switches, seasons, data root
config/*.csv                the rule files (manual overrides, identity merges, verdict corrections, window closes, keeper overrides)
src/netavailability/        the pipeline
  pipeline.py               the stages and the run folder
  compute.py                the per-season compute (retention, xU, RET, NET, NETabsence, the tables)
  prepare.py                match length
  sizing.py                 disputed records sized in expected minutes
  reconcile.py              verdicts applied to the inputs; the dispute ledger
  transfermarkt.py          Transfermarkt squad pages, histories, club ids (local files only)
  checks.py, presence.py    checks C2-C7
  calibrate.py              the constants re-measured on a run
  analyses/                 the analysis battery (points regressions, persistence, extremity, power)
  export.py                 the publishable club and player tables
  settings.py, common.py    settings, input paths, shared helpers
data/                       results and inputs, 2018/19-2025/26 (DATA_DICTIONARY.md, DATA_NOTICE.md)
  tables/                   club and player tables, sideways adjustment on (main) and off
  calibration/, analyses/   the calibration and the analysis battery on the 7-season set (and the 2020/21 variant)
  inputs/                   the input files the pipeline reads, in our derived CSV format
    reconciled/             the reconciled inputs the published run starts from, and the ledger (one outcome per disputed record)
```

## Reproduce

1. Python 3.11 or later: `python -m venv .venv && .venv/bin/pip install -r requirements.txt`.
2. `python run.py --name final` runs the published pipeline for 2018/19-2025/26 from `data/inputs/` into `<output_root>/final/`: it starts from the reconciled inputs (`data/inputs/reconciled/`) and runs the per-season compute, the checks, the calibration, the analyses and the export. `--stages ...` re-runs chosen stages on the same folder; `--seasons ...` chooses seasons.
3. The sizing and reconcile code is included. `python run.py --full-chain` runs it from the provider data (stages prepare, base, size, reconcile); it needs the Transfermarkt squad pages and transfer histories it was run on, which are not distributed, so it cannot be run from this repository alone. `--with-switches` (the switch-effect runs) needs the full chain too.
4. `data_root` in `config/settings.toml` lists the data folders in search order (or pass `--data-root DIR`). The repository holds no data-collection code.

The tables in `data/` are written by the `export` stage; `data/` is licensed under CC BY-NC 4.0 (LICENSE-DATA).

## The stages

1. **integrity**: every input file and rule file is present; their sha256 are recorded.

The published run then takes the reconciled inputs (stage **reconciled**) and continues at stage 6. The full chain (`--full-chain`) runs stages 2-5:

2. **prepare**: match length. A fixture lasts as long as its duration or its latest substitution or dismissal, whichever is later; every appearance's minutes and share of the match are recomputed on that length.
3. **base**: the method on the unreconciled inputs, for every configured season. This run prices the disputes.
4. **size**: every record on which Sportmonks and Transfermarkt disagree is sized in expected minutes (xU x 90 over the fixtures it affects). A dispute worth 180 expected minutes or more needs an independent verdict before it may change the inputs.
5. **reconcile**: where an independent verdict settles a dispute, the squads and transfers are corrected; where none does, the disputed player-club-fixtures are left out of the charge (not counted as absent and not in the total). Contradicted squad rows are dropped, duplicate ids of one person merged, and arrivals from clubs Sportmonks lacks priced by their origin club. Every dispute gets exactly one outcome in `ledger.csv` (check C1 stops the run otherwise).
6. **run**: the method on the reconciled inputs, with the same-pot ("sideways") adjustment on and off. A player found at two clubs on one date is closed at the new club's arrival record and the seasons are run again.
7. **checks**: C2 no player at two clubs on one date; C3 every premierleague.com named player-match is named in the input; C4 the named players' expected usage sums to about 11 per team per fixture; C5 no arrival from a club outside the data is left at the unknown tier; C6 mechanism tests on small test inputs; C7 named cases follow their verdicts. C3 and the C6 tests a, b and b2 need extracts that are not distributed; the public run reports them as "skipped in the public run".
8. **calibration**: the constants (mover delta, sideways adjustment, import fills, the window L) re-measured on the run; this stage only measures.
9. **analyses**: the analysis battery on the 7-season set (2018/19, 2019/20, 2021/22-2025/26, and a variant with 2020/21): points against squad value and NETavailability, half-season models, persistence, extremity of named club-seasons, power. (With 2014/15-2017/18 configured it also runs the 11-season set.)
10. **export**: the club and player tables for the export seasons (`data/DATA_DICTIONARY.md`).
11. **switches** (optional): each rule switch of `[rules]` flipped alone; Spearman correlation per season against the main run and the expected minutes moved.

## The method in short

- **Retained (contracted or on loan at the club, not loaned out)**: a player is retained for a club's fixture when he has a basis there (a dated contract, a squad row when the club has no contract record for him, or a naming earlier in the season) and the transfer timeline has him at the club. Arrivals take effect three days after the record date; departures the day after. Being named always makes him retained for that fixture.
- **xU**: the mean share of the match he played over his last 12 named squads before the fixture. A share from another Premier League club is carried: the carried share is adjusted by 0.10 per seed-pot step of the move (down for a move to a stronger club, up for a move to a weaker one), and reduced by 0.15 for a move between clubs of the same pot (sideways-on tables). Slots outside the data and empty slots take an import fill by origin (0.5 tier-1 countries, 0.35 tier 2, 0.25 tier 3, 0.45 a club of the data, 0 another club's youth side, 0.35 unknown) that expires as he plays for his new club. Keepers carry nothing from other clubs.
- **Tables**: RET, NET, NETabsence and NETavailability per player-club and per club; clubs are ranked by NETavailability.

`compute.py`'s docstring states every rule; `config/settings.toml` holds every constant and switch.

## Input data

The published run reads `data/inputs/`. These are all the files shipped there, in our own derived CSV format; each file's columns are the ones the code reads. Player names in these files are the providers' labels; the verified names are in the player tables (`name_verified`).

| path | content | source |
|---|---|---|
| `reconciled/late/{squads,transfers,appearances,events,contracts}.csv` | the reconciled inputs of 2018/19-2025/26 (with 2017/18 for the xU look-back): squads, transfer and loan events, one row per player per fixture (minutes, on / off times, cards), match events, contracts | Sportmonks, corrected by the review |
| `reconciled/{retention_overrides,origin_overrides,placeholder_origin_arrivals,ledger}.csv` | the exclusions and per player-club fills the compute reads; arrivals from clubs Sportmonks lacks; the ledger of every disputed record with its outcome and source URL | our review |
| `sportmonks/late/{appearances,events,fixtures,squads,transfers,contracts,contracts_no_dated_record,teams}.csv` | the Sportmonks tables before reconciliation (the published run reads teams, contracts_no_dated_record) | Sportmonks |
| `matchday/late/{appearances,events,fixtures}.csv` | the matchday files corrected against premierleague.com match pages (the published run reads fixtures) | Sportmonks, checked against premierleague.com |
| `sportmonks/standings.csv` | Premier League final position and points, one row per club-season from 2013/14 (the seed pots use the five seasons before a season) | Sportmonks |
| `sportmonks/league_seasons.csv` | Premier League season ids | Sportmonks |
| `sportmonks/team_transfers.csv` | one row per transfer or loan event with the from- and to-club and their countries (origin tiers of imports) | Sportmonks |
| `transfermarkt/club_season_values.csv` | squad market value per club-season on 1 July (source pages in `data/DATA_DICTIONARY.md`) | Transfermarkt |
| `transfermarkt/club_ids_primary.csv`, `club_ids_secondary.csv` | Sportmonks team id -> Transfermarkt club id | Transfermarkt |
| `review/verdicts/{round1,round2,gapfill,gapfill_cases}.csv` | independent verdicts on disputed records, with their sources (URLs) | club, league and press sources |
| `review/player_names_verified.csv` | player names checked against premierleague.com and Transfermarkt (used by the export) | our review |
| `tests/transfers_testC_5rows.csv` | a five-row test input for check C6 c (synthetic rows) | test data |

Not distributed: the raw provider responses, the Transfermarkt squad pages and transfer histories, the premierleague.com match-page extracts, and the review's working tables (dispute lists, Sportmonks-Transfermarkt differences, identity tables). The full chain (`--full-chain`) and checks C3 and C6 a, b, b2 need them.

## Licenses

Code: MIT (LICENSE). Data in `data/`: CC BY-NC 4.0 (LICENSE-DATA). No raw provider files are included (DATA_NOTICE.md). Citation: CITATION.cff.
