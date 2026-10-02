# Data dictionary

Published seasons: 2018/19-2025/26 (2020/21 as robustness only). The export step (`python -m netavailability.export`, the `export` stage of `run.py`) writes three tables per season, in two variants, into `tables/`:

- `sideways_on/`: the main tables (the same-pot "sideways" adjustment of carried xU on, -0.15).
- `sideways_off/`: the same method without the sideways adjustment (a robustness variant).

Each variant folder holds, for season `<yyyy-yyyy>`:

- `club_table_<yyyy-yyyy>.csv`: one row per club, best NETavailability first.
- `club_table_paper_<yyyy-yyyy>.csv`: the same rows, worst NETavailability first.
- `player_table_<yyyy-yyyy>.csv`: one row per player-club in the season.

`export_manifest.csv` lists every file with its row count and sha256. The club tables are byte-for-byte the compute's tables (`src/netavailability/compute.py`). The player table is the compute's table with verified player names and one added column, `name_verified`.

The column meanings below come from the compute's docstring and code. The column headers are identical in all published seasons.

Player names: the input files (`inputs/`) carry the providers' labels, which can be wrong or abbreviated. The player tables carry the verified name where it is strongly verified, with `name_verified` = yes.

## Terms used below

- **Fixture**: one of the club's Premier League matches in the season.
- **Named**: listed in the club's matchday squad (starting XI or bench) for a fixture.
- **Retained (contracted or on loan at the club, not loaned out)**: the player counts as available to the club for a fixture. Three things must hold:
  - he has a basis at the club on that date (see `elig_basis`);
  - the transfer timeline puts him at the club on that date (not loaned out, not yet departed);
  - no retention override removes him.

  Being named always makes him retained for that fixture. Column names that say "elig" (`elig_basis`, `elig_first`, `elig_last`) mean retained in this sense.
- **RET, NET, NETavailability, NETabsence**: RET = the expected minutes of the retained players; NET = the expected minutes of the named players; NETavailability = NET ÷ RET; NETabsence = RET − NET.
- **xU (expected usage)**: the mean share of the match he played over his last 12 named squads before the fixture. The window starts at the beginning of the previous season. The share is the appearances file's `proportion` column after the prepare stage: minutes played / match length, where match length = the larger of the fixture's duration and the latest substitution or dismissal time in the match, and minutes = (sub-off or dismissal time, else match length) - (time on, 0 for a starter). A named substitute who did not play has proportion 0.
  - A share from another Premier League club is "carried": the carried share is adjusted by 0.10 per seed-pot step of the move (down for a move to a stronger club, up for a move to a weaker one), and reduced by 0.15 for a move between clubs of the same pot (sideways-on tables).
  - Slots outside our data, and empty slots, take an import "fill" by origin tier. That fill expires after the player arrives.
  - Goalkeepers carry nothing from other clubs.
  - xU for a fixture is "exclusive": only squads strictly before the fixture date count.
- **Minutes**: xU x 90.

## club_table_<yyyy-yyyy>.csv (12 columns)

| column | meaning |
|---|---|
| NETavailability rank | Rank of the club by NETavailability, highest first (1 = best). Ranked at full precision, with ties broken by club name. |
| Club | Club name. |
| Games | Number of the club's fixtures in the season. |
| NETabsence | Sum of the players' NETabsence for the club, in expected minutes, rounded to an integer. |
| NETabsence per match | NETabsence divided by Games, rounded to 1 dp. |
| NETavailability | NET ÷ RET for the club, rounded to 4 dp. This is the share of the club's expected minutes that was available. |
| NET | Sum of the players' NET for the club, in expected minutes, rounded to an integer. |
| RET | Expected minutes of the club's retained players (= NET + NETabsence), rounded to an integer. |
| Top-3 share | Share of the club's NETabsence carried by its three largest player NETabsence values, rounded to 3 dp. Blank when NETabsence is 0. |
| Sent-off mins | Sum of the players' `sent_off_mins` for the club, rounded to an integer. This is not part of NETabsence. |
| absence_order_flag | 1 if the club's position when ordered by NETabsence (lowest first) differs from its NETavailability rank, else 0. |
| team_id | Sportmonks team id of the club. |

## club_table_paper_<yyyy-yyyy>.csv (13 columns)

Same rows and columns as `club_table`, sorted worst first, with one column added in front:

| column | meaning |
|---|---|
| Paper rank (worst first) | Rank by NETavailability, lowest first (1 = worst). Ties are broken by club name in reverse order. |
| NETavailability rank … team_id | As in `club_table` above. |

## player_table_<yyyy-yyyy>.csv (45 columns)

Rows are sorted by club and then by NETabsence, highest first. The "as of season end" columns describe the xU window at the club's last fixture of the season. That window includes squads on the end date itself.

| column | meaning |
|---|---|
| team_id | Sportmonks team id of the club. |
| club | Club name. |
| player_id | Player id: the Sportmonks player id, or 900000000 + the Transfermarkt id for a player known only from Transfermarkt (no Sportmonks id). |
| player | Player name: the verified name where it is strongly verified (see `name_verified`), otherwise Sportmonks' name. |
| name_verified | `yes` if the name was strongly verified against premierleague.com / Transfermarkt (a match on name and date of birth, not on name alone, date of birth alone or a name label), else `no` (the name is Sportmonks'). |
| position_id | Sportmonks position id: the player's most common lineup position, falling back to the contracts file. 24 = goalkeeper, which is also forced by the keeper override. |
| E | Number of the club's fixtures for which the player was retained. |
| N | Number of the club's fixtures for which the player was named. |
| A | max(0, E − N): the number of retained fixtures for which he was not named. |
| xU | Mean exclusive xU over the retained-unnamed fixtures, rounded to 4 dp. Equal to `xU_asof` when there are none. |
| NET | Sum over named fixtures of exclusive xU x 90, in expected minutes, rounded to 1 dp. |
| NETabsence | Sum over retained-unnamed fixtures of exclusive xU x 90 (RET − NET), in expected minutes, rounded to 1 dp. Sent-off minutes are excluded. |
| RET | Expected minutes of the player while retained, over his retained fixtures (= NET + NETabsence), rounded to 1 dp. |
| NETavailability | NET ÷ RET, rounded to 4 dp. Blank when RET = 0. |
| xU_asof | xU at the club's last fixture of the season (inclusive window), rounded to 4 dp. |
| sent_off_mins | Sum over named fixtures in which he was sent off (red or second yellow, not rescinded) of max(0, xU x 90 − minutes played up to the dismissal), rounded to 1 dp. |
| sent_off_n | Number of named fixtures in which he was sent off. |
| slots_actual | As of season end: the number of window slots with an observed value, from this club or carried from another Premier League club. |
| slots_carried | As of season end: the number of window slots from another Premier League club (seed-adjusted). |
| slots_unseen | As of season end: the number of window slots from a non-Premier-League club dated before his effective arrival, priced at `fill`. |
| slots_expired | As of season end: the number of window slots from a non-Premier-League club after his effective arrival, plus a goalkeeper's other-club slots. These are priced at 0. |
| slots_sentoff | As of season end: the number of window slots in which he was sent off. These are priced at the mean of his observed slots, or at `fill` if there are none. |
| slots_empty | As of season end: L (12) minus the number of named squads in the window, i.e. the shortfall. |
| slots_empty_filled | As of season end: the number of empty slots priced at `fill`. This is min(`slots_empty`, max(0, L − the club's fixtures since his effective arrival)). The rest are priced at 0. |
| arrival_eff | Effective date of the latest genuine arrival record at this club on or before season end. An arrival takes effect 3 days after the record date. Blank if there is none. |
| fill | Import fill used for unseen and empty slots, as of season end: the tier fill, or the override fill where one is set. 0 for goalkeepers and non-imports. |
| origin_tier | Origin tier of the arrival in force: `tier1` / `tier2` / `tier3` (by the from-club's country), `unknown`, `data_club` (from a Premier League or Championship club of our data) or `none` (not an import, or a goalkeeper). A suffix `+override` means a per-player origin override set the fill. |
| named_anywhere | 1 if the player was named in any squad in the appearances file on or before season end, else 0. |
| is_gk | 1 if goalkeeper (position 24, or by the keeper override), else 0. |
| is_import | 1 if the player has a genuine arrival record at this club, else 0. A promotion from the club's own youth, reserve or B side does not count. |
| academy | 1 if he has no genuine arrival record at this club (the complement of `is_import`), else 0. Academy players are retained on their contract or squad basis only from their first naming for the club in any season. |
| origin_from | From-club of the earliest genuine arrival record at this club. Blank for academy players. |
| origin_date | Record date of that arrival. |
| origin_type | Sportmonks transfer type of that arrival: 218 = loan, 219 = transfer, 220 = free transfer. |
| youth_promo_from | The club's own youth, reserve or B side named in his earliest same-club promotion record, if any. |
| elig_basis | The bases of retention ("elig" = retained) met on at least one fixture: `a` = a dated contract at the club covering the date; `b` = in the season squad list, with no contract record at the club; `c` = named for the club earlier in the season or on that date. Blank if no basis is met. |
| fixtures_blocked_by_transfers | Number of fixtures where a basis held but the transfer timeline put him away from the club (not yet arrived, or departed). |
| named_in_allowance | Number of fixtures for which he was named while blocked, within an arrival allowance (between an arrival record's date and its effective date). These count as retained. |
| named_while_blocked | Number of fixtures for which he was named while blocked, outside any allowance. These are forced retained and listed in the season's named_while_blocked file. |
| elig_first | Date of his first retained fixture ("elig" = retained). Blank if none. |
| elig_last | Date of his last retained fixture. Blank if none. |
| data_flag | `data mismatch: excluded` if an EXCLUDE retention override (a disputed player-club case with no settling verdict) met at least one fixture, else blank. |
| fixtures_excluded | Number of fixtures made not retained by a retention override (EXCLUDE or NOT_RETAIN) that he would otherwise have been charged for. |
| minutes_excluded | Expected minutes (exclusive xU x 90) removed by those overrides, rounded to 1 dp. |
| fixtures_force_retained | Number of fixtures made retained by a RETAIN override that would otherwise not have been retained. |

## Notes

- The last four player columns come from the retention overrides (the exclusions of disputed records), which the pipeline always passes to the compute.
- Player ids of 900000000 and above are players known only from Transfermarkt (900000000 + the Transfermarkt id).

## Inputs in our derived format (`inputs/sportmonks/`)

| file | columns |
|---|---|
| `standings.csv` | season_id, season, position (final league position), team_id, team, points; one row per Premier League club-season from 2013/14 |
| `league_seasons.csv` | season_id, season: the Premier League season ids |
| `team_transfers.csv` | transfer_id, date, type_id (218 loan, 219 transfer, 220 free, 9688 end of loan), from_team_id, from_country_id, to_team_id, to_country_id; one row per transfer or loan event (an event listed by both clubs appears once) |

The other input files are described in README.md ("Input data").

## Squad values (`inputs/transfermarkt/club_season_values.csv`)

One row per club-season (240 rows, 2014/15-2025/26): the club's total squad market value on 1 July of the season (10 July in 2014/15), read from Transfermarkt's dated competition page of the league the club plays in now (Premier League GB1, Championship GB2, League One GB3; column `value_source`). The pages, per season (date = `value_date`):

| season | Premier League page (Championship / League One: replace `premier-league/…/GB1` by `championship/…/GB2` / `league-one/…/GB3`) |
|---|---|
| 2014/2015 | https://www.transfermarkt.co.uk/premier-league/marktwerteverein/wettbewerb/GB1/plus/?stichtag=2014-07-10 |
| 2015/2016 | https://www.transfermarkt.co.uk/premier-league/marktwerteverein/wettbewerb/GB1/plus/?stichtag=2015-07-01 |
| 2016/2017 | https://www.transfermarkt.co.uk/premier-league/marktwerteverein/wettbewerb/GB1/plus/?stichtag=2016-07-01 |
| 2017/2018 | https://www.transfermarkt.co.uk/premier-league/marktwerteverein/wettbewerb/GB1/plus/?stichtag=2017-07-01 |
| 2018/2019 | https://www.transfermarkt.co.uk/premier-league/marktwerteverein/wettbewerb/GB1/plus/?stichtag=2018-07-01 |
| 2019/2020 | https://www.transfermarkt.co.uk/premier-league/marktwerteverein/wettbewerb/GB1/plus/?stichtag=2019-07-01 |
| 2020/2021 | https://www.transfermarkt.co.uk/premier-league/marktwerteverein/wettbewerb/GB1/plus/?stichtag=2020-07-01 |
| 2021/2022 | https://www.transfermarkt.co.uk/premier-league/marktwerteverein/wettbewerb/GB1/plus/?stichtag=2021-07-01 |
| 2022/2023 | https://www.transfermarkt.co.uk/premier-league/marktwerteverein/wettbewerb/GB1/plus/?stichtag=2022-07-01 |
| 2023/2024 | https://www.transfermarkt.co.uk/premier-league/marktwerteverein/wettbewerb/GB1/plus/?stichtag=2023-07-01 |
| 2024/2025 | https://www.transfermarkt.co.uk/premier-league/marktwerteverein/wettbewerb/GB1/plus/?stichtag=2024-07-01 |
| 2025/2026 | https://www.transfermarkt.co.uk/premier-league/marktwerteverein/wettbewerb/GB1/plus/?stichtag=2025-07-01 |

## Other outputs

- `inputs/reconciled/ledger.csv`: one row per disputed record of the published seasons, with its size in expected minutes, the verdict (if any), the outcome (APPLIED, EXCLUDED, ADDED_NO_VERDICT), `basis` (why) and `source_url` (the verdict's source pages; blank when there is no verdict or it rests on Sportmonks' own namings).
- `inputs/reconciled/`: the reconciled inputs the published run starts from (late set: squads, transfers, appearances, events, contracts; `retention_overrides.csv` = the exclusions, `origin_overrides.csv` = per player-club fills, `placeholder_origin_arrivals.csv`).
- `calibration/`: the constants re-measured on the 7-season set (`calibration_table_SET7.csv`, `calibration_SET7.json`).
- `analyses/SET7/`: the analysis battery on the 7-season set (`headline_SET7.json`; variants `main`, `with2021`, `exwin`).
- `abstract_numbers.csv`: one row per number in the submitted abstract (text, Figure 1 and Table 1). Columns: `id`, `section`, `abstract_context` (where the number appears), `number_as_printed`, `source_file` and `source_line` (the file in this repository and the line the value is on), `source_field` (column, key or row; "×0.01" or "×100" when the printed number is the source value rescaled), `source_value` (full precision) and `check` (the build check or audit item that confirmed it).
