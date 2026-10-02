#!/usr/bin/env python3
"""
NETavailability: the per-season compute.

For one Premier League season it works out, for every player-club, on which of the club's fixtures the player was
retained (under contract, not loaned out), whether he was named in the matchday squad, and how much playing time the
club could have expected from him (xU, expected usage). A retained player who is not named is an absence worth xU x 90
expected minutes.

  RET              expected minutes of the retained players: sum over retained fixtures of xU x 90
  NET              expected minutes of the named players: sum over named fixtures of xU x 90
  NETavailability  NET / RET, per player-club and per club; clubs are ranked by it, highest first
  NETabsence       RET - NET: the expected minutes of the retained players who were not named
  xU               the mean share of the match he played over his last 12 named squads (L = 12)

The rules, in plain words:
  Retention. A player has a basis at a club on a fixture date from (a) a dated contract covering the date, (b) a squad
      row when the club has no contract record for him, or (c) having been named for the club earlier in the season.
      An academy player (no arrival record at the club) has bases (a) and (b) only from his first naming for the club in
      any season. The transfer timeline then decides whether he is at the club on that date (not loaned out, not yet
      departed); a naming always makes him retained for that fixture.
  Transfer timeline. Arrivals (loan, transfer, free) take effect three days after the record date (a settling
      allowance, for genuine arrivals only); loan returns one day after; departures one day after (the old club keeps
      him on the record date). Effective dates never run backwards in record order. A promotion from the club's own
      youth, reserve or B side is not an arrival. A departure with no destination is cancelled by a later naming for the
      same club with no record elsewhere in between (a contract renewal). An arrival at a club while another club holds
      an open loan-out closes that loan-out on the same date. An open loan-in is closed when the parent club's loan is
      deemed to end (its return record, or the registration window close / nominal loan end inferred for it), or when
      the player is named or recorded at a third club. A loan-out followed by a naming for the parent club returns him
      on the latest registration window close or nominal loan end in between (--window-closes).
  xU. The mean share of the match he played over his last L named squads before the fixture (from the start of the
      previous season; the appearances file's proportion column). A share from another Premier League club is carried:
      the carried share is adjusted by --mover-delta (0.10) per seed-pot step of the move (down for a move to a stronger
      club, up for a move to a weaker one), and reduced by --sideways-adjust (0.15) for a move between clubs of the same
      pot (sideways-on tables); keepers carry nothing from other clubs. Slots at
      clubs outside the data dated before the player's effective arrival, and empty slots, take an import fill by the
      origin of the arrival (tier 1 / tier 2 / tier 3 countries, a club of the data, another club's youth side, unknown);
      the fill of empty slots expires as the player plays fixtures for his new club. A match he was sent off in counts at
      the mean of his other slots.
  Seeds. Each club's seed is the mean of its finishing pots over the five seasons before the target season (pot 1 =
      1st-4th, 2 = 5th-8th, 3 = 9th-14th, 4 = 15th-20th, 5 = not in the Premier League), rounded half up, from the
      cached Premier League standings.
  Sent-off minutes. A named player sent off loses max(0, xU x 90 - minutes played up to the dismissal); these minutes
      are reported per club and are not part of NETabsence.
  Rule files. --origin-overrides sets the fill of named player-clubs; --keeper-override treats player-clubs as keepers;
      --retention-overrides marks player-club-date ranges EXCLUDE (a disputed fixture is neither charged nor in RET),
      NOT_RETAIN (not retained unless named) or RETAIN (retained); the first row covering a date wins.
      --first-team-first makes the arrival sort stable and lets a first-team record beat a same-date youth duplicate.

Outputs in --out, for season tag <tag> and output suffix <sfx>:
  club_table_<tag><sfx>.csv            NETavailability rank, Club, Games, NETabsence, NETabsence per match,
                                       NETavailability, NET, RET, Top-3 share, Sent-off mins, absence_order_flag, team_id
  club_table_paper_<tag><sfx>.csv      the same, worst first
  player_table_<tag><sfx>.csv          one row per player-club: E, N, A, xU, NET, NETabsence, RET, NETavailability, ...
  presence_ledger_<tag><sfx>.csv       one row per player-club retention window
  absence_trace_<tag><sfx>.csv         every retained-unnamed player-fixture with its xU (--trace-all)
  calibration_<tag><sfx>.csv           per fixture: the sum of exclusive xU over each team's named players
  club_split_half_<tag><sfx>.csv, club_split_january_<tag><sfx>.csv, club_E_summary_<tag><sfx>.csv,
  allowance_<tag><sfx>.csv, allowance_detail_<tag><sfx>.csv, named_while_blocked_<tag><sfx>.csv,
  retention_overrides_applied_<tag><sfx>.csv, undated_contracts_material_<tag><sfx>.csv,
  movers_<tag><sfx>.csv, movers_summary_<tag><sfx>.csv, movers_summary_nogk_<tag><sfx>.csv, seeds_<tag>_<sfx>.csv
  season-independent files, written once per folder: null_out_cancellations, loan_returns, loan_anomalies,
  loan_to_loan_synth, transfers_219_null_to (each _<sfx>.csv)

Inputs (in --pulls): appearances, fixtures and events (with --suffix), teams, squads, transfers, contracts and
contracts_no_dated_record (with --meta-suffix), and standings.csv (Premier League standings, one row per club-season),
league_seasons.csv (Premier League season ids) and team_transfers.csv (one row per transfer event with the from- and
to-club and their countries, for the origin tiers).

The sizing and calibration stages read this file as source text (a probe copy of xU_calc; caller contexts of xU_calc
and local variable names of the functions main, xU_calc and eligibility). Change those parts together with sizing.py and
calibrate.py.

Usage:
  python compute.py --season 2019/2020 --pulls <inputs> --suffix "" --meta-suffix "" --out <dir> --out-suffix _on \
      --window-closes <window_table.csv> [the constants and rule files]
"""
import argparse
import bisect
import math
import re
from collections import namedtuple
from datetime import timedelta
from pathlib import Path
import numpy as np
import pandas as pd

PL_NAME, CH_NAME = "Premier League", "Championship"
GK_POSITION = 24
T_LOAN, T_TRANSFER, T_FREE, T_END_LOAN = 218, 219, 220, 9688
T_SYNTH = 0                       # synthesised departure / inferred return
ARRIVAL_TYPES = {T_LOAN, T_TRANSFER, T_FREE}
SENT_OFF_TYPES = {"Redcard", "Yellow/Red card"}
FAR_FUTURE = pd.Timestamp("2099-12-31")

# effective-date lags (days after the record date)
ARRIVAL_LAG, RETURN_LAG, OUT_LAG = 3, 1, 1
ALLOWANCE_REPORT_DAYS = 14        # allowance report: fixtures on days X..X+14 after an arrival record
N_SEED_SEASONS = 5
# origin tiers by from-team country_id (Sportmonks core ids, anchored on club names in the transfer payloads)
TIER1_COUNTRIES = {17, 32, 11, 251, 75285, 20, 38, 556}
TIER2_COUNTRIES = {462, 1161, 404, 455, 320, 47, 62, 1578, 143, 125, 245, 2, 491, 515, 227, 86, 296, 266, 674, 224, 155,
                   401, 116, 1638, 802, 1233, 1796, 3126, 2405, 919}
TIER3_COUNTRIES = {5, 3483, 44, 98, 479, 712, 1004, 353, 458, 459, 158, 886, 5618, 1190, 80, 2817, 275, 35376, 153732, 1739,
                   146, 2802, 23, 74505, 1176, 1424, 614, 1640, 338, 488, 21462}
TIER_FILL = {"tier1": 0.5, "tier2": 0.4, "tier3": 0.2, "unknown": 0.4}

# youth / reserve / B side detection ("<club> U21", "<club> Reserves", "<club> B", "<club> II", "<club> 2")
YOUTH_RE = re.compile(r"(\bU\s?1\d\b|\bU\s?2\d\b|\bYouth\b|\bReserves?\b|\bAcademy\b|\bB\b$|\bII\b$|\s2$)", re.I)
YOUTH_ALIASES = {"wolves": "wolverhampton wanderers", "spurs": "tottenham hotspur", "man utd": "manchester united",
                 "man united": "manchester united", "man city": "manchester city", "forest": "nottingham forest",
                 "newcastle utd": "newcastle united", "west brom": "west bromwich albion", "sheff utd": "sheffield united",
                 "sheff wed": "sheffield wednesday", "qpr": "queens park rangers", "villa": "aston villa",
                 "palace": "crystal palace", "boro": "middlesbrough"}

# timeline event: eff = effective date, rec = record date, order = same-day tie-break, kind in/out,
# type = type_id (T_SYNTH for synthesised/inferred), genuine = arrival not from a same-club youth side,
# other = the other team's name (or the inference rule), synth = synthesised
Ev = namedtuple("Ev", "eff rec order kind type genuine other synth")


def pot_of_finish(f):
    if f is None or (isinstance(f, float) and math.isnan(f)):
        return 5
    f = int(f)
    return 1 if f <= 4 else 2 if f <= 8 else 3 if f <= 14 else 4 if f <= 20 else 5


def round_half_up(x):
    return int(math.floor(x + 0.5))


def prev_season_name(name):
    a, b = name.split("/")
    return f"{int(a)-1}/{int(b)-1}"


def season_tag(name):
    return name.replace("/", "-")


def short_season(name):
    """'2018/2019' -> '2018-19'"""
    a, b = name.split("/")
    return f"{a}-{b[2:]}"


def norm_club(name):
    s = str(name).lower().replace("&", "and").replace(".", "")
    s = re.sub(r"\butd\b", "united", s)
    toks = [t for t in s.split() if t not in ("afc", "fc", "cf")]
    return " ".join(toks)


def youth_stem(name):
    """Strip the youth/reserve marker from a team name; None if the name carries no marker."""
    if not YOUTH_RE.search(str(name)):
        return None
    stem = YOUTH_RE.sub("", str(name)).strip(" -")
    return norm_club(stem)


def is_same_club_youth(from_name, parent_name):
    """True if from_name is a youth/reserve/B side of parent_name."""
    stem = youth_stem(from_name)
    if stem is None:
        return False
    stem = YOUTH_ALIASES.get(stem, stem)
    parent = norm_club(parent_name)
    return stem == parent or parent.startswith(stem + " ") or stem.startswith(parent + " ")


# ---------------------------------------------------------------- seeds from cached PL standings
def build_seeds(season_name, teams, club_ids, club_name, indir):
    pot_seasons, s = [], season_name
    for _ in range(N_SEED_SEASONS):
        s = prev_season_name(s)
        pot_seasons.insert(0, s)
    sid_of = {r.season: int(r.season_id) for r in teams[teams.league == PL_NAME].drop_duplicates("season_id").itertuples()}
    lp = indir / "league_seasons.csv"
    n_fallback = 0
    if lp.exists():
        for e in pd.read_csv(lp).itertuples():
            if e.season not in sid_of:
                sid_of[e.season] = int(e.season_id); n_fallback += 1
    st_all = pd.read_csv(indir / "standings.csv")
    finish, names, participants, uncached = {}, {}, set(), []
    for s in pot_seasons:
        sid = sid_of.get(s)
        if sid is None:
            raise SystemExit(f"seeds: no season_id for PL {s} in teams.csv or {lp.name}")
        data = st_all[st_all.season_id == sid]
        if data.empty:
            print(f"seeds: WARNING no cached standings for PL {s} (season_id {sid}): pot 5 for every club in that season")
            uncached.append(s)
            continue
        if len(data) != 20:
            print(f"seeds: WARNING PL {s} (season_id {sid}) standings has {len(data)} rows")
        for d in data.itertuples():
            tid = int(d.team_id)
            finish[(tid, s)] = int(d.position)
            names[tid] = None if pd.isna(d.team) else d.team
            participants.add(tid)
        print(f"seeds: PL {s} season_id {sid}: {len(data)} standing rows from standings.csv")
    universe = set(club_ids) | participants | {int(t) for t in teams.team_id}
    rows = []
    for tid in sorted(universe):
        fins = [finish.get((tid, s)) for s in pot_seasons]
        pots = [pot_of_finish(f) for f in fins]
        mean = float(np.mean(pots))
        rows.append(dict(club=club_name.get(tid, names.get(tid)), team_id=tid,
                         **{f"pot_{short_season(s)}": p for s, p in zip(pot_seasons, pots)},
                         **{f"finish_{short_season(s)}": f for s, f in zip(pot_seasons, fins)},
                         mean=round(mean, 2), seed=round_half_up(mean)))
    seeds = pd.DataFrame(rows).sort_values(["seed", "mean", "club"]).reset_index(drop=True)
    if uncached:
        cached_cols = [f"pot_{short_season(x)}" for x in pot_seasons if x not in uncached]
        tgt = seeds[seeds.team_id.isin(club_ids)]
        n_any = int((tgt[cached_cols] < 5).any(axis=1).sum()) if cached_cols else 0
        print(f"seeds: {len(uncached)} of {len(pot_seasons)} pot seasons uncached ({uncached}); every one of the {len(seeds)} clubs in the file "
              f"takes pot 5 for them; {len(tgt)} target clubs affected, of which {n_any} have a cached PL finish in the remaining seasons "
              f"and {len(tgt) - n_any} rest on pot 5 alone")
    return seeds, pot_seasons, n_fallback


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="NETavailability compute for one Premier League season")
    ap.add_argument("--season", required=True, help="target season, e.g. 2019/2020")
    ap.add_argument("--league", default=PL_NAME)
    ap.add_argument("--pulls", required=True, help="folder of the input files")
    ap.add_argument("--suffix", default="", help="suffix of the appearances / fixtures / events files")
    ap.add_argument("--meta-suffix", default="", help="suffix of the teams / squads / transfers / contracts files")
    ap.add_argument("--L", type=int, default=12, help="xU window: the last L named squads")
    ap.add_argument("--baseline", type=float, default=0.5, help="fill of an import whose origin has no tier fill")
    ap.add_argument("--out", default=None, help="output folder (default = --pulls)")
    ap.add_argument("--fill-unnamed-imports", action=argparse.BooleanOptionalAction, default=True,
                    help="an import with a genuine arrival record gets his fill even if never named")
    ap.add_argument("--mover-delta", type=float, default=0.05,
                    help="carried slots adjusted to carried - delta x (from_seed - to_seed), clipped to 0..1")
    ap.add_argument("--academy-gate", choices=["any", "season"], default="any",
                    help="academy eligibility starts at the first naming for the club in any season (any) or in the target season")
    ap.add_argument("--out-suffix", default="", help="suffix of the output files")
    ap.add_argument("--youth-fill", type=float, default=None,
                    help="fill of an import whose arrival is from another club's youth / reserve / B side (default: its tier fill)")
    ap.add_argument("--allowance-genuine-only", action="store_true",
                    help="the three-day arrival allowance applies only to genuine arrivals (others take effect on the record date)")
    ap.add_argument("--unknown-fill", type=float, default=TIER_FILL["unknown"], help="fill of the unknown origin tier")
    ap.add_argument("--keeper-override", default=None, help="CSV with columns player_id, team_id: player-clubs treated as keepers")
    ap.add_argument("--tier1-fill", type=float, default=TIER_FILL["tier1"], help="fill of a tier-1 country origin")
    ap.add_argument("--tier2-fill", type=float, default=TIER_FILL["tier2"], help="fill of a tier-2 country origin")
    ap.add_argument("--tier3-fill", type=float, default=TIER_FILL["tier3"], help="fill of a tier-3 country origin")
    ap.add_argument("--data-club-fill", type=float, default=None, help="fill of an origin club of the data (default: --baseline)")
    ap.add_argument("--origin-overrides", default=None, help="CSV with columns player_id, fill[, team_id]: per player(-club) fill")
    ap.add_argument("--sideways-adjust", type=float, default=None,
                    help="carried slots from a club of the same seed take clip(v - A, 0, 1) (default: off)")
    ap.add_argument("--trace-all", action="store_true", help="write every absence to absence_trace_<tag><sfx>.csv")
    ap.add_argument("--window-closes", required=True,
                    help="CSV with columns date, kind (window_close | nominal_loan_end)")
    ap.add_argument("--retention-overrides", default=None,
                    help="CSV with columns player_id, team_id, from, to, action (EXCLUDE | NOT_RETAIN | RETAIN), case_id")
    ap.add_argument("--first-team-first", action="store_true",
                    help="stable arrival sort; a first-team record beats a same-date youth duplicate")
    args = ap.parse_args()
    _wc = pd.read_csv(args.window_closes, parse_dates=["date"])
    WINDOW_CLOSES = sorted(pd.Timestamp(d) for d in _wc[_wc.kind == "window_close"].date)
    NOMINAL_LOAN_ENDS = sorted(pd.Timestamp(d) for d in _wc[_wc.kind == "nominal_loan_end"].date)
    ret_ov, ret_applied, ret_by_pair = {}, [], {}                             # retention overrides
    if args.retention_overrides:
        _ro = pd.read_csv(args.retention_overrides)
        for _p, _t, _f, _to, _a, _c in zip(_ro.player_id, _ro.team_id, pd.to_datetime(_ro["from"]), pd.to_datetime(_ro["to"]),
                                           _ro.action, _ro.case_id if "case_id" in _ro.columns else [""] * len(_ro)):
            ret_ov.setdefault((int(_p), int(_t)), []).append((_f, _to, str(_a).strip().upper(), _c))
    OUT_SUFFIX = args.out_suffix
    DATE_TAG = OUT_SUFFIX.lstrip("_")
    tier_fill_of = dict(TIER_FILL, tier1=args.tier1_fill, tier2=args.tier2_fill, tier3=args.tier3_fill, unknown=args.unknown_fill)
    data_club_fill = args.data_club_fill
    sideways = args.sideways_adjust
    origin_override = {}
    if args.origin_overrides:
        oo = pd.read_csv(args.origin_overrides)
        for r in oo.itertuples():
            key = (int(r.player_id), int(r.team_id)) if ("team_id" in oo.columns and not pd.isna(r.team_id)) else int(r.player_id)
            origin_override[key] = float(r.fill)
    keeper_override = set()
    if args.keeper_override:
        ko = pd.read_csv(args.keeper_override)
        keeper_override = set(zip(ko.player_id.astype(int), ko.team_id.astype(int)))
    L, B, delta = args.L, args.baseline, args.mover_delta
    pulls = Path(args.pulls)
    out = Path(args.out) if args.out else pulls
    sfx = args.suffix
    msfx = args.meta_suffix
    tag = season_tag(args.season)

    apps = pd.read_csv(pulls / f"appearances{sfx}.csv", parse_dates=["date"])
    fx = pd.read_csv(pulls / f"fixtures{sfx}.csv", parse_dates=["date"])
    ev = pd.read_csv(pulls / f"events{sfx}.csv")
    teams = pd.read_csv(pulls / f"teams{msfx}.csv")
    squads = pd.read_csv(pulls / f"squads{msfx}.csv")
    transfers = pd.read_csv(pulls / f"transfers{msfx}.csv", parse_dates=["date"])
    contracts = pd.read_csv(pulls / f"contracts{msfx}.csv")

    apps = apps[apps.player_id.notna()].copy()
    apps["player_id"] = apps.player_id.astype(int)
    apps = apps.sort_values(["date", "fixture_id"]).reset_index(drop=True)
    fx["date"] = fx.date.dt.normalize()
    transfers = transfers.drop_duplicates("transfer_id")           # each transfer is pulled from both clubs
    contracts["start"] = pd.to_datetime(contracts["start"], errors="coerce")
    contracts["end"] = pd.to_datetime(contracts["end"], errors="coerce")

    # ---- season / league lookups
    t_target = teams[(teams.league == args.league) & (teams.season == args.season)]
    if t_target.empty:
        raise SystemExit(f"No teams for {args.league} {args.season} in teams.csv")
    season_id = int(t_target.season_id.iloc[0])
    club_ids = sorted(set(t_target.team_id))
    club_name = dict(zip(teams.team_id, teams.name))
    # any club named in transfers.csv (for reports on clubs outside teams.csv); teams.csv names win
    team_name_any = {}
    for a, b in (("from_team_id", "from_team"), ("to_team_id", "to_team")):
        t = transfers[transfers[a].notna() & transfers[b].notna()]
        team_name_any.update(dict(zip(t[a].astype(int), t[b])))
    team_name_any.update(club_name)
    data_clubs = {int(t) for t in teams.team_id}
    country_of = {}
    _tt = pd.read_csv(pulls / "team_transfers.csv")
    for _f, _fc, _t, _tc in zip(_tt.from_team_id, _tt.from_country_id, _tt.to_team_id, _tt.to_country_id):
        for _id, _c in ((_f, _fc), (_t, _tc)):
            if not pd.isna(_id) and not pd.isna(_c):
                country_of[int(_id)] = int(_c)

    def tier_of_from(from_id):
        if from_id is None:
            return "unknown"
        if from_id in data_clubs:
            return "data_club"
        c = country_of.get(from_id)
        if c is None:
            return "unknown"
        return "tier1" if c in TIER1_COUNTRIES else "tier2" if c in TIER2_COUNTRIES else "tier3" if c in TIER3_COUNTRIES else "unknown"
    league_of_season = dict(zip(teams.season_id, teams.league))
    name_of_season = dict(zip(teams.season_id, teams.season))
    pl_season_ids = {s for s, l in league_of_season.items() if l == PL_NAME}

    fx_s = fx[fx.season_id == season_id]
    season_start, season_end = fx_s.date.min(), fx_s.date.max()
    as_of = season_end
    prev = prev_season_name(args.season)
    prev_ids = set(teams[teams.season == prev].season_id)
    window_start = fx[fx.season_id.isin(prev_ids)].date.min() if prev_ids else season_start
    print(f"{args.league} {args.season}: season_id {season_id}, {len(club_ids)} clubs, "
          f"{len(fx_s)} fixtures, {season_start.date()} -> {season_end.date()}; window from {window_start.date()}")
    print(f"options: L={L} baseline={B} fill_unnamed_imports={args.fill_unnamed_imports} mover_delta={delta} "
          f"academy_gate={args.academy_gate}")
    print(f"fill options: youth_fill={args.youth_fill} allowance_genuine_only={args.allowance_genuine_only} "
          f"unknown_fill={args.unknown_fill} keeper_override={sorted(keeper_override)} tier_fills={tier_fill_of} "
          f"data_club_fill={data_club_fill} sideways_adjust={sideways} origin_overrides={len(origin_override)}")
    print(f"rule files: window_closes={args.window_closes} ({len(WINDOW_CLOSES)} closes, {len(NOMINAL_LOAN_ENDS)} nominal loan ends) "
          f"retention_overrides={sum(len(v) for v in ret_ov.values())} rows on {len(ret_ov)} player-clubs "
          f"first_team_first={args.first_team_first}")

    # ---- club fixture lists (for E and T) and every club's fixture dates across the file (fill expiry)
    club_fx = {}
    for c in club_ids:
        d = fx_s[(fx_s.home_id == c) | (fx_s.away_id == c)].sort_values("date")
        club_fx[c] = d[["fixture_id", "date"]].reset_index(drop=True)
    club_fx_all = {}
    for col in ("home_id", "away_id"):
        for tid, g in fx.groupby(col):
            club_fx_all.setdefault(int(tid), []).extend(list(g.date))
    club_fx_all = {k: sorted(v) for k, v in club_fx_all.items()}

    # ---- named squads per player as sorted arrays (fast rolling windows)
    apps["is_pl"] = apps.season_id.isin(pl_season_ids)
    by_player = {}
    for pid, g in apps.groupby("player_id"):
        by_player[pid] = dict(dates=list(g.date), fixture_id=list(g.fixture_id), team_id=list(g.team_id),
                              is_pl=list(g.is_pl), prop=list(g.proportion.astype(float)), player=g.player.iloc[-1], g=g)
    first_named_any = apps.groupby("player_id").date.min().to_dict()
    first_named_club_any = apps.groupby(["team_id", "player_id"]).date.min().to_dict()   # academy gate (any season)

    # ---- sent-off matches: events rows, type Redcard / Yellow/Red card, not rescinded, player_id present
    resc = ev.rescinded.astype(str).str.lower().eq("true")
    so = ev[ev.type.isin(SENT_OFF_TYPES) & ~resc & ev.player_id.notna()].copy()
    so["player_id"] = so.player_id.astype(int)
    sent_off_set = set(zip(so.fixture_id, so.player_id))
    sent_off_elapsed = so.groupby(["fixture_id", "player_id"]).elapsed.min().to_dict()
    print(f"sent-off matches in events{sfx}.csv: {len(sent_off_set)} (player, fixture) pairs")

    # ---- position per player: modal lineup position_id, else contracts.csv position_id
    pos = apps[apps.position_id.notna()].groupby("player_id").position_id.agg(lambda s: s.mode().iloc[0]).to_dict()
    cpos = contracts[contracts.position_id.notna()].groupby("player_id").position_id.agg(lambda s: s.mode().iloc[0]).to_dict()

    def position_of(pid):
        p = pos.get(pid, cpos.get(pid))
        return int(p) if p is not None and not pd.isna(p) else None

    # ---- import classification per (player, club): earliest genuine arrival record
    arrivals = transfers[transfers.type_id.isin(ARRIVAL_TYPES) & transfers.to_team_id.notna() & transfers.date.notna()]
    if args.first_team_first:                                                 # first-team record first
        arrivals = arrivals.assign(_y=arrivals.from_team.map(lambda n: bool(YOUTH_RE.search(str(n))))).sort_values(
            ["date", "_y"], kind="stable")
    else:
        arrivals = arrivals.sort_values("date")
    origin, youth_promos = {}, {}
    for r in arrivals.itertuples():
        key = (int(r.player_id), int(r.to_team_id))
        parent = club_name.get(int(r.to_team_id), r.to_team)
        if is_same_club_youth(r.from_team, parent):
            youth_promos.setdefault(key, []).append((r.date.date(), r.from_team, int(r.type_id)))
        elif key not in origin:
            origin[key] = (r.date.date(), r.from_team, int(r.type_id))

    def is_import(pid, club):
        return (pid, club) in origin

    # ---- seeds (built before the player loop: the mover adjustment needs them)
    seeds_path = out / f"seeds_{tag}_{DATE_TAG}.csv"
    seeds, pot_seasons, n_fb = build_seeds(args.season, teams, club_ids, club_name, pulls)
    seeds.to_csv(seeds_path, index=False)
    print(f"seeds: {seeds_path.name}: {len(seeds)} clubs, pots {pot_seasons[0]}..{pot_seasons[-1]}; "
          f"{n_fb} season ids taken from league_seasons.csv")
    missing = set(club_ids) - set(seeds.team_id)
    if missing:
        print(f"seeds: WARNING target clubs without a seed: {sorted(club_name.get(m, m) for m in missing)}")
    seed_of = {int(r.team_id): int(r.seed) for r in seeds.itertuples() if not pd.isna(r.team_id)} if seeds is not None else {}

    def seed_lookup(tid):
        return seed_of.get(int(tid), 5)      # a club never in the cached PL seasons has five pots of 5

    # ---- transfer timeline per (player, club): raw events on record dates
    tr = transfers[transfers.type_id.isin([T_LOAN, T_TRANSFER, T_FREE, T_END_LOAN]) & transfers.date.notna()]
    order = {T_END_LOAN: 0, T_TRANSFER: 1, T_FREE: 1, T_LOAN: 2, T_SYNTH: 1}   # same-day: returns, permanents, loans
    raw, out_detail = {}, {}
    loan_from = {}          # (pid, to_club, rec) -> from_team_id of a 218 record (mirror loan rule)
    null_out = {}           # (pid, from_club, rec) -> type of a departure record with null to_team_id (renewal rule)
    in_from_id = {}         # (pid, to_club, rec) -> from_team_id of an arrival record (origin tier)
    in_from_youth = {}      # (pid, to_club, rec) -> the record held in in_from_id is from a youth side

    def write_once(df, path):
        if path.exists():
            print(f"  {path.name} exists; not rewritten")
        else:
            df.to_csv(path, index=False)

    def add_ev(pid, club, rec, kind, t, genuine, other, synth=False):
        raw.setdefault((pid, club), []).append(Ev(None, rec, order[t], kind, t, genuine, other, synth))

    for r in tr.itertuples():
        pid = int(r.player_id)
        if not pd.isna(r.to_team_id):
            to = int(r.to_team_id)
            genuine = not (r.type_id in ARRIVAL_TYPES and is_same_club_youth(r.from_team, club_name.get(to, r.to_team)))
            add_ev(pid, to, r.date, "in", int(r.type_id), genuine, r.from_team)
            if r.type_id in ARRIVAL_TYPES:
                _k, _yth = (pid, to, r.date), bool(YOUTH_RE.search(str(r.from_team)))
                if not (args.first_team_first and _k in in_from_id and _yth and not in_from_youth[_k]):   # first-team record first
                    in_from_id[_k] = None if pd.isna(r.from_team_id) else int(r.from_team_id)
                    in_from_youth[_k] = _yth
            if r.type_id == T_LOAN:
                loan_from[(pid, to, r.date)] = None if pd.isna(r.from_team_id) else int(r.from_team_id)
        if not pd.isna(r.from_team_id):
            add_ev(pid, int(r.from_team_id), r.date, "out", int(r.type_id), True, r.to_team)
            out_detail[(pid, int(r.from_team_id), r.date)] = (r.to_team, r.player)
            if pd.isna(r.to_team_id):
                null_out[(pid, int(r.from_team_id), r.date)] = int(r.type_id)

    all_clubs = set(teams.team_id)                      # every club held, so the loan files do not depend on --season
    namings = {k: sorted(set(g.date)) for k, g in apps[apps.team_id.isin(all_clubs)].groupby(["player_id", "team_id"])}

    # ---- renewal: a departure with null to_team_id followed by a naming for the same club, with no intervening record
    #          at another club, is a contract renewal: the departure is cancelled
    rec_by_pid = {}
    for (pid, club), evs in raw.items():
        for e in evs:
            rec_by_pid.setdefault(pid, []).append((e.rec, club))
    cancel_rows = []
    for (pid, club, X), t in sorted(null_out.items()):
        nm = [d for d in namings.get((pid, club), []) if d > X]
        if not nm:
            continue
        d = nm[0]
        if any(c != club and X < r <= d for r, c in rec_by_pid.get(pid, [])):
            continue
        raw[(pid, club)] = [e for e in raw[(pid, club)] if not (e.kind == "out" and e.rec == X and e.type == t)]
        y = d.year if d.month >= 7 else d.year - 1
        cancel_rows.append(dict(season=f"{y}/{y+1}", player_id=pid, player=by_player.get(pid, {}).get("player"),
                                club=club_name.get(club, club), team_id=club, out_type=t, out_date=X.date(),
                                first_named_after=d.date()))
    cancels = pd.DataFrame(cancel_rows, columns=["season", "player_id", "player", "club", "team_id", "out_type", "out_date", "first_named_after"])
    write_once(cancels.sort_values(["season", "club", "player"]), out / f"null_out_cancellations_{DATE_TAG}.csv")
    print(f"renewals: {len(cancels)} null-destination departures cancelled by a later naming for the same club "
          f"({len(null_out)} null-destination departure records in total)")
    for sn, g in cancels.groupby("season"):
        print(f"  {sn}: {len(g)}" + ("" if sn != args.season else "  <- target season: "
              + "; ".join(f"{r.player} ({r.club}, out {r.out_date}, named {r.first_named_after})" for r in g.itertuples())))

    # ---- loan-to-loan: an arrival at B while another club A holds an open loan-out -> synthesised out at A
    clubs_of = {}
    for (pid, club) in raw:
        clubs_of.setdefault(pid, set()).add(club)
    synth_rows = []
    arr_recs = tr[tr.type_id.isin(ARRIVAL_TYPES) & tr.to_team_id.notna()].sort_values(["date", "transfer_id"])
    for r in arr_recs.itertuples():
        pid, Bc, Y = int(r.player_id), int(r.to_team_id), r.date
        frm = None if pd.isna(r.from_team_id) else int(r.from_team_id)
        for A in sorted(clubs_of.get(pid, ())):
            if A == Bc or A == frm:
                continue
            prior = sorted([e for e in raw[(pid, A)] if e.rec < Y], key=lambda e: (e.rec, e.order))
            if not prior:
                continue
            last = prior[-1]
            if last.kind == "out" and last.type == T_LOAN and not last.synth:
                add_ev(pid, A, Y, "out", T_SYNTH, True, r.to_team, synth=True)
                out_detail[(pid, A, Y)] = (r.to_team, r.player)
                synth_rows.append(dict(player_id=pid, player=r.player, parent_club=team_name_any.get(A, A), parent_team_id=A,
                                       loan_out_date=last.rec.date(), loan_out_to=last.other,
                                       in_club=team_name_any.get(Bc, r.to_team), in_team_id=Bc, in_date=Y.date(),
                                       in_type=int(r.type_id), in_from=r.from_team, transfer_id=int(r.transfer_id),
                                       synth_out_effective=(Y + timedelta(days=OUT_LAG)).date()))
    for sr in synth_rows:
        sr["rule"], sr["closure_reason"] = "loan_to_loan", ""
    synth_cols = ["rule", "player_id", "player", "parent_club", "parent_team_id", "loan_out_date", "loan_out_to", "in_club",
                  "in_team_id", "in_date", "in_type", "in_from", "transfer_id", "synth_out_effective", "closure_reason"]
    null219 = transfers[(transfers.type_id == T_TRANSFER) & transfers.to_team_id.isna()].sort_values(["date", "player"])
    write_once(null219, out / f"transfers_219_null_to_{DATE_TAG}.csv")
    in_target = null219[null219.from_team_id.isin(club_ids)]
    print(f"loan-to-loan: {len(synth_rows)} synthesised out events (loan_to_loan_synth_{DATE_TAG}.csv); "
          f"{len(null219)} Transfer (219) records with null to_team_id ({len(in_target)} from target-season clubs; "
          f"transfers_219_null_to_{DATE_TAG}.csv)")

    # ---- window-rule returns (on record dates) on the raw events + namings
    boundaries = sorted(WINDOW_CLOSES + NOMINAL_LOAN_ENDS)
    return_rows, anomaly_rows, inferred_ret = [], [], {}
    for key, evs in raw.items():
        nm = namings.get(key)
        if not nm:
            continue
        merged = sorted([(e.rec, e.order, e) for e in evs] + [(d, 9, None) for d in nm], key=lambda x: (x[0], x[1]))
        state, out_at, out_type, extra, flagged = None, None, None, [], None
        for d, o, e in merged:
            if e is not None:
                state, flagged = e.kind, None
                if e.kind == "out":
                    out_at, out_type = d, e.type
                continue
            if state != "out":
                continue
            cands = [w for w in boundaries if out_at < w <= d]
            to_team, pname = out_detail.get((key[0], key[1], out_at), (None, None))
            if cands:
                W = max(cands)
                rule = "window_close" if W in WINDOW_CLOSES else "nominal_loan_end"
                literal = [w for w in WINDOW_CLOSES if out_at < w <= d]
                extra.append(Ev(None, W, -1, "in", T_SYNTH, False, rule, False))
                inferred_ret[(key[0], key[1], out_at)] = W
                state = "in"
                return_rows.append(dict(player_id=key[0], player=pname or by_player.get(key[0], {}).get("player"),
                                        club=club_name.get(key[1]), out_type=out_type, out_date=out_at.date(),
                                        out_to=to_team, first_named_after=d.date(), return_date=W.date(), rule=rule,
                                        literal_window_close=max(literal).date() if literal else None,
                                        anomaly_before=flagged.date() if flagged is not None else None))
            elif flagged is None:
                flagged = d
                nxt = [w for w in WINDOW_CLOSES if w > out_at]
                anomaly_rows.append(dict(player_id=key[0], player=pname or by_player.get(key[0], {}).get("player"),
                                         club=club_name.get(key[1]), out_type=out_type, out_date=out_at.date(),
                                         out_to=to_team, first_named_parent=d.date(),
                                         next_window_close=nxt[0].date() if nxt else None,
                                         note="named before any window close / nominal loan end since the out-event; left blocked"))
        evs.extend(extra)

    # ---- effective dates
    def eff_of(e):
        if e.kind == "in":
            lag = ARRIVAL_LAG if e.type in ARRIVAL_TYPES else (RETURN_LAG if e.type == T_END_LOAN else 0)
            if args.allowance_genuine_only and e.type in ARRIVAL_TYPES and not e.genuine:
                lag = 0                                                   # not a genuine arrival -> no settling allowance
        else:
            lag = OUT_LAG
        return e.rec + timedelta(days=lag)

    timeline = {}
    for k, evs in raw.items():
        seq, run = [], None
        for e in sorted(evs, key=lambda e: (e.rec, e.order)):
            eff = eff_of(e)
            if run is not None and eff < run:
                eff = run                      # effective dates never run backwards in record order
            run = eff
            seq.append(e._replace(eff=eff))
        timeline[k] = sorted(seq, key=lambda e: (e.eff, e.rec, e.order))

    # ---- mirror loan rule: close open loan-ins at the borrowing club
    by_pid_clubs = {}
    for (pid, club) in timeline:
        by_pid_clubs.setdefault(pid, set()).add(club)
    namings_by_pid = {}
    for (pid, club), dts in namings.items():
        namings_by_pid.setdefault(pid, []).extend((d, club) for d in dts)
    for pid in namings_by_pid:
        namings_by_pid[pid].sort()
    mirror_rows = []
    for (pid, Bc) in list(timeline):
        evs = timeline[(pid, Bc)]
        for e in [x for x in evs if x.kind == "in" and x.type == T_LOAN and not x.synth]:
            X = e.rec
            later = sorted([x for x in evs if (x.rec, x.order) > (X, e.order) and not x.synth], key=lambda x: (x.rec, x.order))
            if later and later[0].kind == "out":
                continue                                          # closed by a record at B
            next_in_eff = later[0].eff if later else None
            A = loan_from.get((pid, Bc, X))
            cands = []
            if A is not None:
                W = inferred_ret.get((pid, A, X))
                if W is not None:
                    cands.append((W, W, "parent_inferred_return"))
                for x in timeline.get((pid, A), ()):
                    if x.kind == "in" and x.type == T_END_LOAN and x.rec > X:
                        cands.append((x.eff, x.rec, "parent_return_record")); break
            for d, C in namings_by_pid.get(pid, ()):
                if d > X and C not in (A, Bc):
                    cands.append((d, d, f"third_club_named:{club_name.get(C, C)}")); break
            third = [(x.rec, C) for C in by_pid_clubs.get(pid, ()) if C not in (A, Bc)
                     for x in timeline[(pid, C)] if x.rec > X and x.type != T_SYNTH]
            if third:
                rec, C = min(third)
                cands.append((rec + timedelta(days=OUT_LAG), rec, f"third_club_record:{team_name_any.get(C, C)}"))
            if not cands:
                continue
            eff, rec, why = min(cands)
            if next_in_eff is not None and eff >= next_in_eff:
                continue                                          # a later record at B already re-opens him there
            eff = max(eff, e.eff)
            ne = Ev(eff, rec, 1, "out", T_SYNTH, True, f"mirror:{why}", True)
            timeline[(pid, Bc)] = sorted(evs + [ne], key=lambda x: (x.eff, x.rec, x.order))
            evs = timeline[(pid, Bc)]
            mirror_rows.append(dict(rule="mirror_loan_in", player_id=pid, player=by_player.get(pid, {}).get("player"),
                                    parent_club=team_name_any.get(A, A), parent_team_id=A, loan_out_date=X.date(),
                                    loan_out_to=team_name_any.get(Bc, Bc), in_club=team_name_any.get(Bc, Bc), in_team_id=Bc,
                                    in_date=X.date(), in_type=T_LOAN, in_from=e.other, transfer_id=None,
                                    synth_out_effective=eff.date(), closure_reason=why))
    synth_all = pd.DataFrame(synth_rows + mirror_rows, columns=synth_cols).sort_values(["rule", "in_date", "player"])
    write_once(synth_all, out / f"loan_to_loan_synth_{DATE_TAG}.csv")
    in_target_mirror = [m for m in mirror_rows if m["in_team_id"] in club_ids]
    print(f"mirror loans: {len(mirror_rows)} mirror closures of open loan-ins ({len(in_target_mirror)} at target-season clubs); "
          f"reasons: {dict(pd.Series([m['closure_reason'].split(':')[0] for m in mirror_rows]).value_counts()) if mirror_rows else {}}")

    def transfer_state(pid, club, D):
        evs = timeline.get((pid, club))
        if not evs:
            return True
        before = [e for e in evs if e.eff <= D]
        if before:
            return before[-1].kind != "out"
        nxt = [e for e in evs if not (e.kind == "in" and e.type in ARRIVAL_TYPES and not e.genuine)]   # youth promotions never block
        return not nxt or nxt[0].kind != "in"          # next real event is an arrival -> he had not arrived yet

    def in_allowance(pid, club, D):
        """D lies between an 'in' record date and its effective date."""
        return any(e.kind == "in" and e.rec <= D < e.eff for e in timeline.get((pid, club), ()))

    def event_desc(e):
        if e is None:
            return None
        return f"{e.kind} type {e.type}{' synth' if e.synth else ''} rec {e.rec.date()} eff {e.eff.date()} ({e.other})"

    def latest_arrival(pid, club, ref):
        cands = [e for e in timeline.get((pid, club), ()) if e.kind == "in" and e.type in ARRIVAL_TYPES
                 and e.genuine and e.rec <= ref]
        if args.first_team_first:                                             # same-date duplicates -> the first-team record
            return max(cands, key=lambda e: (e.rec, e.order, 0 if YOUTH_RE.search(str(e.other)) else 1)) if cands else None
        return max(cands, key=lambda e: (e.rec, e.order)) if cands else None

    def arrival_eff(pid, club, ref):
        """Effective date of the latest genuine arrival record at this club on or before ref; None if none."""
        e = latest_arrival(pid, club, ref)
        return e.eff if e is not None else None

    def origin_tier(pid, club, ref):
        """Tier of the latest genuine arrival on or before ref; falls back to the origin record; 'none' if neither."""
        e = latest_arrival(pid, club, ref)
        if e is not None:
            return tier_of_from(in_from_id.get((pid, club, e.rec)))
        og = origin.get((pid, club))
        if og is None:
            return "none"
        cands = transfers[(transfers.player_id == pid) & (transfers.to_team_id == club) & transfers.type_id.isin(ARRIVAL_TYPES)]
        return tier_of_from(None if cands.empty or pd.isna(cands.iloc[0].from_team_id) else int(cands.iloc[0].from_team_id))

    def origin_other_club_youth(pid, club, ref):
        """The record whose tier origin_tier uses is from a youth/reserve/B side (YOUTH_RE) of another club."""
        e = latest_arrival(pid, club, ref)
        if e is not None:
            name = e.other
        else:
            if origin.get((pid, club)) is None:
                return False
            cands = transfers[(transfers.player_id == pid) & (transfers.to_team_id == club) & transfers.type_id.isin(ARRIVAL_TYPES)]
            name = None if cands.empty else cands.iloc[0].from_team
        if name is None or pd.isna(name) or not YOUTH_RE.search(str(name)):
            return False
        return not is_same_club_youth(name, club_name.get(club, club))

    if return_rows:
        write_once(pd.DataFrame(return_rows).sort_values(["club", "player"]), out / f"loan_returns_{DATE_TAG}.csv")
    write_once(pd.DataFrame(anomaly_rows, columns=["player_id", "player", "club", "out_type", "out_date", "out_to", "first_named_parent",
                                                   "next_window_close", "note"]), out / f"loan_anomalies_{DATE_TAG}.csv")
    print(f"window returns: {len(return_rows)} out-events closed by the window/nominal-end rule; {len(anomaly_rows)} anomalies left blocked")

    # ---- xU (window of last L named squads strictly before / on the reference date; fills; import rule)
    def xU_calc(pid, club, ref_date, exclusive=True, delta_override=None):
        dl = delta if delta_override is None else delta_override
        sw = sideways if delta_override is None else None                 # raw carried (delta_override=0) is unadjusted
        p = by_player.get(pid)
        is_gk = position_of(pid) == GK_POSITION or (pid, club) in keeper_override
        imp = is_import(pid, club)
        fn = first_named_any.get(pid)
        named_before = fn is not None and ((fn < ref_date) if exclusive else (fn <= ref_date))
        fill_ok = named_before or (args.fill_unnamed_imports and (pid, club) in origin)
        tier = origin_tier(pid, club, ref_date) if (imp and not is_gk) else "none"
        tier_fill = B if tier in ("data_club", "none") else tier_fill_of[tier]
        if data_club_fill is not None and tier == "data_club":
            tier_fill = data_club_fill
        if args.youth_fill is not None and imp and not is_gk and origin_other_club_youth(pid, club, ref_date):
            tier_fill = args.youth_fill
        if origin_override and imp and not is_gk:
            ov = origin_override.get((pid, club), origin_override.get(pid))
            if ov is not None:
                tier_fill = ov
                tier = f"{tier}+override"
        fill = 0.0 if is_gk else (tier_fill if (imp and fill_ok) else 0.0)
        arr = arrival_eff(pid, club, ref_date)
        slots = []
        if p is not None:
            dates = p["dates"]
            lo = bisect.bisect_left(dates, window_start)
            hi = bisect.bisect_left(dates, ref_date) if exclusive else bisect.bisect_right(dates, ref_date)
            for i in range(max(lo, hi - L), hi):
                tid = p["team_id"][i]
                if (p["fixture_id"][i], pid) in sent_off_set:
                    slots.append(("sentoff", None))
                elif tid == club:
                    slots.append(("actual", p["prop"][i]))
                elif is_gk:
                    slots.append(("gk_other", 0.0))                       # keepers carry nothing
                elif p["is_pl"][i]:
                    v = p["prop"][i]
                    if dl:                                                # stronger destination -> lower carried
                        v = min(1.0, max(0.0, v - dl * (seed_lookup(tid) - seed_lookup(club))))
                    if sw is not None and seed_lookup(tid) == seed_lookup(club):
                        v = min(1.0, max(0.0, v - sw))                    # sideways (same-pot) mover
                    slots.append(("carried", v))
                elif arr is None or dates[i] < arr:
                    slots.append(("unseen", fill))                        # before arrival -> fill
                else:
                    slots.append(("expired", 0.0))                        # non-PL after arrival -> 0
        actual = [v for k, v in slots if k in ("actual", "carried")]
        so_val = float(np.mean(actual)) if actual else fill
        vals = [so_val if k == "sentoff" else v for k, v in slots]
        shortfall = L - len(slots)
        if arr is None:
            n_fx = 0
        else:
            cd = club_fx_all.get(club, [])
            hi_fx = bisect.bisect_left(cd, ref_date) if exclusive else bisect.bisect_right(cd, ref_date)
            n_fx = max(0, hi_fx - bisect.bisect_left(cd, arr))
        n_fill = min(shortfall, max(0, L - n_fx))                        # fill expiry
        xU = (sum(vals) + n_fill * fill) / L
        info = dict(slots_actual=len(actual), slots_carried=sum(1 for k, _ in slots if k == "carried"),
                    slots_unseen=sum(1 for k, _ in slots if k == "unseen"),
                    slots_expired=sum(1 for k, _ in slots if k in ("expired", "gk_other")),
                    slots_sentoff=sum(1 for k, _ in slots if k == "sentoff"), slots_empty=shortfall,
                    slots_empty_filled=n_fill, fixtures_since_arrival=n_fx, fill=fill,
                    arrival_eff=arr.date() if arr is not None else None, origin_tier=tier,
                    named_anywhere=int(bool(named_before)), is_gk=int(is_gk), is_import=int(imp))
        return xU, info

    # ---- eligibility bases
    sq = squads[squads.season_id == season_id]
    squad_pairs = set(zip(sq.team_id.astype(int), sq.player_id.dropna().astype(int)))
    con = contracts[contracts.team_id.isin(club_ids) & contracts.start.notna()].copy()
    con["end_eff"] = con.end.fillna(FAR_FUTURE)
    con_all = {}
    for r in con.itertuples():
        con_all.setdefault((int(r.player_id), int(r.team_id)), []).append((r.start, r.end_eff))
    con_has_record = {(int(r.player_id), int(r.team_id)) for r in contracts[contracts.team_id.isin(club_ids)].itertuples()}
    named = apps[(apps.season_id == season_id) & (apps.team_id.isin(club_ids))]
    named_fx = {k: set(g.fixture_id) for k, g in named.groupby(["team_id", "player_id"])}
    first_named_here = named.groupby(["team_id", "player_id"]).date.min().to_dict()
    con_overlap = {k for k, ivs in con_all.items() if any(s <= season_end and e >= season_start for s, e in ivs)}
    pairs = set(named_fx) | {k for k in squad_pairs if k[0] in club_ids} | {(c, p) for (p, c) in con_overlap}
    pairs |= {(c, p) for (p, c), v in ret_ov.items() if c in club_ids                                        # RETAIN rows
              and any(a == "RETAIN" and f <= season_end and t >= season_start for f, t, a, _ in v)}
    n_named_allow, n_named_blocked, blocked_rows = 0, 0, []
    academy_gate_affected = []

    def eligibility(c, pid):
        cf = club_fx[c]
        ivs = con_all.get((pid, c), [])
        has_rec = (pid, c) in con_has_record
        in_squad = (c, pid) in squad_pairs
        fnh = first_named_here.get((c, pid))
        nfx = named_fx.get((c, pid), set())
        academy = (pid, c) not in origin
        gate = first_named_club_any.get((c, pid)) if args.academy_gate == "any" else fnh
        elig, base_l, basis, n_blocked, n_allow, n_forced, forced_rows = [], [], set(), 0, 0, 0, []
        for r in cf.itertuples():
            D = r.date
            gate_ok = (not academy) or (gate is not None and gate <= D)
            a = any(s <= D <= e for s, e in ivs) and gate_ok
            b = (not has_rec) and in_squad and gate_ok
            cc = fnh is not None and fnh <= D
            base = a or b or cc
            if base:
                basis.update([x for x, ok in (("a", a), ("b", b), ("c", cc)) if ok])
            ok = base and transfer_state(pid, c, D)
            if base and not ok:
                n_blocked += 1
            if r.fixture_id in nfx and not ok:
                ok = True
                if in_allowance(pid, c, D):
                    n_allow += 1
                else:
                    n_forced += 1
                    evs = timeline.get((pid, c), [])
                    before = [e for e in evs if e.eff <= D]
                    after = [e for e in evs if e.eff > D]
                    forced_rows.append(dict(player_id=pid, club=club_name.get(c, c), fixture_id=r.fixture_id, date=D.date(),
                                            base=("" if base else "no_base ") + "".join(sorted(basis)),
                                            last_event=event_desc(before[-1] if before else None),
                                            next_event=event_desc(after[0] if after else None)))
            if ret_ov:                                                        # retention overrides
                _act = next((x for x in ret_ov.get((pid, c), ()) if x[0] <= D <= x[1]), None)
                if _act is not None:
                    _hyp = 0.0
                    if _act[2] == "RETAIN":
                        _did = "already_retained" if ok else "forced_retained"
                        ok = True
                    elif r.fixture_id in nfx:
                        _did = "named_kept"
                    elif ok:
                        _did = "excluded" if _act[2] == "EXCLUDE" else "not_retained"
                        _hyp = xU_calc(pid, c, D, exclusive=True)[0] * 90
                        ok = False
                    else:
                        _did = "not_charged_anyway"
                    _row = dict(season=args.season, player_id=pid, team_id=c, club=club_name.get(c, c), fixture_id=r.fixture_id,
                                date=D.date(), action=_act[2], case_id=_act[3], effect=_did, minutes_removed=round(_hyp, 4))
                    ret_applied.append(_row)
                    ret_by_pair.setdefault((pid, c), []).append(_row)
            elig.append(ok)
            base_l.append(base)
        return elig, base_l, "".join(sorted(basis)), n_blocked, n_allow, n_forced, forced_rows, academy

    # ---- player rows (per-fixture rolling xU; NET / NETabsence; calibration; allowance report)
    rows, fixture_loss = [], {c: np.zeros(len(club_fx[c])) for c in club_ids}
    ledger_rows = []
    trace_all_rows = []
    calib_sum, calib_n = {}, {}
    allowance_rows = []
    for (c, pid) in sorted(pairs):
        elig, base_l, basis, n_blocked, n_allow, n_forced, forced_rows, academy = eligibility(c, pid)
        n_named_allow += n_allow
        n_named_blocked += n_forced
        cf = club_fx[c]
        nfx = named_fx.get((c, pid), set())
        for fr in forced_rows:
            fr["player"] = by_player.get(pid, {}).get("player")
            blocked_rows.append(fr)
        E = int(sum(elig))
        N = len(nfx)
        A = max(0, E - N)
        xU_asof, info = xU_calc(pid, c, as_of, exclusive=False)
        per_fx, loss_by_fx, net = [], {}, 0.0
        for i, r in enumerate(cf.itertuples()):
            if r.fixture_id in nfx:                                       # NET / calibration
                xf, _ = xU_calc(pid, c, r.date, exclusive=True)
                net += xf * 90
                calib_sum[(r.fixture_id, c)] = calib_sum.get((r.fixture_id, c), 0.0) + xf
                calib_n[(r.fixture_id, c)] = calib_n.get((r.fixture_id, c), 0) + 1
            elif elig[i]:
                xf, inf = xU_calc(pid, c, r.date, exclusive=True)
                per_fx.append(xf)
                loss_by_fx[r.fixture_id] = xf * 90
                fixture_loss[c][i] += xf * 90
                if args.trace_all:
                    trace_all_rows.append(dict(player_id=pid, player=by_player.get(pid, {}).get("player"), team_id=c, club=club_name.get(c),
                                               fixture_id=r.fixture_id, date=r.date.date(), xU=round(xf, 4), minutes=round(xf * 90, 4),
                                               slots_actual=inf["slots_actual"], slots_carried=inf["slots_carried"],
                                               slots_unseen=inf["slots_unseen"], slots_expired=inf["slots_expired"],
                                               slots_sentoff=inf["slots_sentoff"], slots_empty=inf["slots_empty"],
                                               slots_empty_filled=inf["slots_empty_filled"], fill=inf["fill"], origin_tier=inf["origin_tier"],
                                               arrival_eff=inf["arrival_eff"], fixtures_since_arrival=inf["fixtures_since_arrival"]))
        net_absence = sum(per_fx) * 90
        ret = net + net_absence
        # presence ledger: maximal runs of retained fixtures
        fx_dates = list(cf.date); fx_ids = list(cf.fixture_id)
        i = 0; win_list = []
        while i < len(elig):
            if not elig[i]:
                i += 1; continue
            j = i
            while j + 1 < len(elig) and elig[j + 1]:
                j += 1
            win_list.append((i, j)); i = j + 1
        evs_pc = timeline.get((pid, c), [])
        for w, (i0, i1) in enumerate(win_list, 1):
            d0, d1 = fx_dates[i0], fx_dates[i1]
            ev0 = [e for e in evs_pc if fx_dates[i0 - 1] < e.eff <= d0] if i0 > 0 else []
            ev1 = [e for e in evs_pc if d1 < e.eff <= fx_dates[i1 + 1]] if i1 + 1 < len(elig) else []
            fnh_ = first_named_here.get((c, pid))
            start_src = "season_start" if i0 == 0 else (f"{ev0[-1].kind}_{ev0[-1].type}" + ("_synth" if ev0[-1].synth else "") if ev0
                                                       else ("first_named" if fnh_ is not None and fnh_ == d0 else "basis"))
            end_src = "season_end" if i1 == len(elig) - 1 else (f"{ev1[0].kind}_{ev1[0].type}" + ("_synth" if ev1[0].synth else "") if ev1 else "basis")
            named_idx = [k for k in range(i0, i1 + 1) if fx_ids[k] in nfx]
            lead = (named_idx[0] - i0) if named_idx else (i1 - i0 + 1)
            tail = (i1 - named_idx[-1]) if named_idx else 0
            w_abs = sum(loss_by_fx.get(fx_ids[k], 0.0) for k in range(i0, i1 + 1))
            ledger_rows.append(dict(season=args.season, player_id=pid, player=by_player.get(pid, {}).get("player"), team_id=c,
                                    club=club_name.get(c, c), window_no=w, n_windows=len(win_list), start=d0.date(), end=d1.date(),
                                    start_fixture_id=fx_ids[i0], end_fixture_id=fx_ids[i1], start_source=start_src, end_source=end_src,
                                    E=i1 - i0 + 1, N=len(named_idx), A=i1 - i0 + 1 - len(named_idx), NETabsence=round(w_abs, 1),
                                    lead_unnamed=lead, tail_unnamed=tail, forced_named=n_allow + n_forced, elig_basis=basis,
                                    is_import=int(is_import(pid, c)), academy=int(academy)))
        xU = float(np.mean(per_fx)) if per_fx else xU_asof
        # allowance report: fixtures on days X..X+14 after each arrival record at this club
        for e in timeline.get((pid, c), ()):
            if e.kind != "in" or e.type not in ARRIVAL_TYPES:
                continue
            X = e.rec
            if X < season_start - timedelta(days=ALLOWANCE_REPORT_DAYS) or X > season_end:
                continue
            for i, r in enumerate(cf.itertuples()):
                k = (r.date - X).days
                if k < 0 or k > ALLOWANCE_REPORT_DAYS or r.fixture_id in nfx or not base_l[i]:
                    continue
                if elig[i]:
                    charged, hyp = loss_by_fx.get(r.fixture_id, 0.0), 0.0
                else:
                    xf, _ = xU_calc(pid, c, r.date, exclusive=True)
                    charged, hyp = 0.0, xf * 90
                allowance_rows.append(dict(team_id=c, club=club_name.get(c, c), player_id=pid,
                                           player=by_player.get(pid, {}).get("player"), arrival_date=X.date(),
                                           arrival_type=e.type, arrival_from=e.other, effective=e.eff.date(),
                                           fixture_id=r.fixture_id, date=r.date.date(), day=k,
                                           eligible_v3=int(elig[i]), charged_v3=round(charged, 1),
                                           removed_by_allowance=round(hyp, 1)))
        # sent-off minutes
        so_mins, so_n = 0.0, 0
        for r in cf.itertuples():
            if (r.fixture_id, pid) in sent_off_set and r.fixture_id in nfx:
                arow = named[(named.fixture_id == r.fixture_id) & (named.player_id == pid) & (named.team_id == c)].iloc[0]
                played = float(arow.minutes)
                if arow.played == 1 and pd.notna(arow.on_at):
                    played = min(played, max(0.0, float(sent_off_elapsed[(r.fixture_id, pid)]) - float(arow.on_at)))
                xU_b, _ = xU_calc(pid, c, r.date, exclusive=True)
                so_mins += max(0.0, xU_b * 90 - played)
                so_n += 1
        p = by_player.get(pid)
        gn = named[(named.team_id == c) & (named.player_id == pid)]
        pname = gn.player.iloc[0] if len(gn) else (p["player"] if p is not None else
                                                    sq[sq.player_id == pid].player.iloc[0] if (sq.player_id == pid).any() else "")
        el_dates = [d for d, ok in zip(cf.date, elig) if ok]
        og = origin.get((pid, c))
        yp = youth_promos.get((pid, c), [])
        gate_any = first_named_club_any.get((c, pid))
        if academy and N == 0 and gate_any is not None and gate_any < season_start:
            academy_gate_affected.append((club_name.get(c, c), pname, E, round(net_absence, 1)))
        rows.append(dict(team_id=c, club=club_name.get(c, c), player_id=pid, player=pname,
                         position_id=GK_POSITION if (pid, c) in keeper_override else position_of(pid),
                         E=E, N=N, A=A, xU=round(xU, 4), NET=round(net, 1), NETabsence=round(net_absence, 1),
                         RET=round(ret, 1), NETavailability=round(net / ret, 4) if ret > 0 else None,
                         xU_asof=round(xU_asof, 4), sent_off_mins=round(so_mins, 1), sent_off_n=so_n,
                         slots_actual=info["slots_actual"], slots_carried=info["slots_carried"],
                         slots_unseen=info["slots_unseen"], slots_expired=info["slots_expired"],
                         slots_sentoff=info["slots_sentoff"], slots_empty=info["slots_empty"],
                         slots_empty_filled=info["slots_empty_filled"], arrival_eff=info["arrival_eff"],
                         fill=info["fill"], origin_tier=info["origin_tier"], named_anywhere=info["named_anywhere"], is_gk=info["is_gk"],
                         is_import=info["is_import"], academy=int(academy),
                         origin_from=og[1] if og else None, origin_date=og[0] if og else None,
                         origin_type=og[2] if og else None, youth_promo_from=yp[0][1] if yp else None,
                         elig_basis=basis, fixtures_blocked_by_transfers=n_blocked,
                         named_in_allowance=n_allow, named_while_blocked=n_forced,
                         elig_first=el_dates[0].date() if el_dates else None,
                         elig_last=el_dates[-1].date() if el_dates else None))
        if ret_ov:                                                            # retention overrides
            _ra = ret_by_pair.get((pid, c), [])
            rows[-1].update(data_flag="data mismatch: excluded" if any(x["action"] == "EXCLUDE" for x in _ra) else "",
                            fixtures_excluded=sum(1 for x in _ra if x["effect"] in ("excluded", "not_retained")),
                            minutes_excluded=round(sum(x["minutes_removed"] for x in _ra), 1),
                            fixtures_force_retained=sum(1 for x in _ra if x["effect"] == "forced_retained"))

    players = pd.DataFrame(rows).sort_values(["club", "NETabsence"], ascending=[True, False])
    players.to_csv(out / f"player_table_{tag}{OUT_SUFFIX}.csv", index=False)
    if ret_ov:                                                                # retention overrides
        _ra = pd.DataFrame(ret_applied, columns=["season", "player_id", "team_id", "club", "fixture_id", "date", "action", "case_id",
                                                 "effect", "minutes_removed"])
        _ra.to_csv(out / f"retention_overrides_applied_{tag}{OUT_SUFFIX}.csv", index=False)
        print(f"retention overrides met {len(_ra)} player-club-fixtures: {dict(_ra.effect.value_counts())}; "
              f"minutes removed {_ra.minutes_removed.sum():.1f}")
    ledger = pd.DataFrame(ledger_rows).sort_values(["club", "player", "window_no"])
    ledger.to_csv(out / f"presence_ledger_{tag}{OUT_SUFFIX}.csv", index=False)
    print(f"presence ledger: {len(ledger)} windows for {ledger.groupby(['team_id', 'player_id']).ngroups} player-clubs; "
          f"start sources {dict(ledger.start_source.value_counts())}")
    print(f"player rows: {len(players)}; imports {int(players.is_import.sum())} of {len(players)}; "
          f"academy {int(players.academy.sum())}")
    imp_rows = players[(players.is_import == 1) & (players.is_gk == 0)]
    new_this = imp_rows[pd.to_datetime(imp_rows.origin_date, errors="coerce") >= season_start - timedelta(days=75)]
    print("import player-clubs by origin tier (non-keepers): "
          + ", ".join(f"{t}={int((imp_rows.origin_tier == t).sum())}" for t in ("tier1", "tier2", "tier3", "unknown", "data_club", "none"))
          + "; of which arrived since 1 June before the season: "
          + ", ".join(f"{t}={int((new_this.origin_tier == t).sum())}" for t in ("tier1", "tier2", "tier3", "unknown", "data_club")))
    print(f"named fixtures forced eligible: {n_named_allow} within an arrival/return allowance (expected), "
          f"{n_named_blocked} while blocked (named_while_blocked_{tag}{OUT_SUFFIX}.csv)")
    bcols = ["player_id", "player", "club", "fixture_id", "date", "base", "last_event", "next_event"]
    blocked = pd.DataFrame(blocked_rows, columns=bcols).sort_values(["club", "player", "date"])
    blocked.to_csv(out / f"named_while_blocked_{tag}{OUT_SUFFIX}.csv", index=False)
    if len(blocked):
        pd.set_option("display.width", 250)
        print(blocked.to_string(index=False))
    LOAN_OUT_CHECKS = [("Destiny Udogie", 32777506, 6, "2022/2023", "2022-08-16"), ("Stefanos Tzimas", 37601748, 78, "2024/2025", "2025-02-03"),
                ("Josh Bowler", 518750, 63, "2022/2023", "2022-09-01")]
    for nm, pid, club, sn, d in LOAN_OUT_CHECKS:
        if sn != args.season:
            continue
        pr = players[(players.player_id == pid) & (players.team_id == club)]
        E_ = int(pr.E.iloc[0]) if len(pr) else 0
        print(f"sign-and-loan-out check {nm} at {club_name.get(club)} ({sn}, sign-and-loan-out {d}): "
              f"{'in player table' if len(pr) else 'not in player table'}; E={E_} N={int(pr.N.iloc[0]) if len(pr) else 0} "
              f"NETabsence={float(pr.NETabsence.iloc[0]) if len(pr) else 0.0} -> {'PASS' if E_ == 0 else 'FAIL'}")
        for x in timeline.get((pid, club), []):
            print(f"    timeline: {event_desc(x)}")
    if args.academy_gate == "any":
        print(f"academy gate 'any': {len(academy_gate_affected)} academy player-clubs not named this season but named for the "
              f"club in an earlier season (they would have E=0 under --academy-gate season): "
              f"NETabsence {sum(x[3] for x in academy_gate_affected):.0f}")
        for x in sorted(academy_gate_affected, key=lambda x: -x[3])[:15]:
            print(f"    {x[0]}: {x[1]} E={x[2]} NETabsence={x[3]}")

    pd.set_option("display.width", 220)
    if args.trace_all:
        tcols = ["player_id", "player", "team_id", "club", "fixture_id", "date", "xU", "minutes", "slots_actual", "slots_carried", "slots_unseen",
                 "slots_expired", "slots_sentoff", "slots_empty", "slots_empty_filled", "fill", "origin_tier", "arrival_eff", "fixtures_since_arrival"]
        tall = pd.DataFrame(trace_all_rows, columns=tcols)
        tall.to_csv(out / f"absence_trace_{tag}{OUT_SUFFIX}.csv", index=False)
        print(f"\nabsence trace: {len(tall)} eligible-unnamed player-fixtures, {tall.minutes.sum():.1f} minutes -> absence_trace_{tag}{OUT_SUFFIX}.csv")

    # ---- club table; half-season and January splits
    winter = [w for w in WINDOW_CLOSES if w.month in (1, 2) and w.year == int(args.season.split("/")[1])]
    winter_close = winter[0] if winter else None
    club_rows, split_rows, jan_rows = [], [], []
    for c in club_ids:
        p = players[players.team_id == c]
        T = len(club_fx[c])
        absence = float(p.NETabsence.sum())
        net = float(p.NET.sum())
        ret = net + absence
        top3 = float(p.NETabsence.nlargest(3).sum()) / absence if absence > 0 else None
        club_rows.append({"Club": club_name.get(c, c), "team_id": c, "Games": T, "NETabsence": absence,
                          "NETabsence per match": absence / T if T else None,
                          "NETavailability": net / ret if ret > 0 else None, "NET": net, "RET": ret,
                          "Top-3 share": top3, "Sent-off mins": int(round(p.sent_off_mins.sum()))})
        fl = fixture_loss[c]
        split_rows.append(dict(club=club_name.get(c, c), team_id=c,
                               first19_fixtures=int(min(19, T)), first19_NETabsence=int(round(fl[:19].sum())),
                               last19_fixtures=int(max(0, T - 19)), last19_NETabsence=int(round(fl[19:].sum())) if T > 19 else None))
        if winter_close is not None:
            pre = np.array([d < winter_close for d in club_fx[c].date])
            n_pre, n_post = int(pre.sum()), int((~pre).sum())
            jan_rows.append(dict(club=club_name.get(c, c), team_id=c, winter_close=winter_close.date(),
                                 pre_fixtures=n_pre, pre_NETabsence=int(round(fl[pre].sum())),
                                 pre_per_match=round(fl[pre].sum() / n_pre, 1) if n_pre else None,
                                 post_fixtures=n_post, post_NETabsence=int(round(fl[~pre].sum())),
                                 post_per_match=round(fl[~pre].sum() / n_post, 1) if n_post else None))
    club = pd.DataFrame(club_rows).sort_values(["NETavailability", "Club"], ascending=[False, True]).reset_index(drop=True)
    club.insert(0, "NETavailability rank", club.index + 1)
    abs_order = club.NETabsence.rank(method="first").astype(int)              # ascending-NETabsence position
    club["absence_order_flag"] = (abs_order != club["NETavailability rank"]).astype(int)
    club = club[["NETavailability rank", "Club", "Games", "NETabsence", "NETabsence per match", "NETavailability", "NET", "RET",
                 "Top-3 share", "Sent-off mins", "absence_order_flag", "team_id"]]
    club_out = club.copy()
    club_out["NETabsence"] = club_out.NETabsence.round(0).astype(int)
    club_out["NETabsence per match"] = club_out["NETabsence per match"].round(1)
    club_out["NETavailability"] = club_out.NETavailability.round(4)
    club_out["NET"] = club_out.NET.round(0).astype(int)
    club_out["RET"] = club_out.RET.round(0).astype(int)
    club_out["Top-3 share"] = club_out["Top-3 share"].round(3)
    club_out.to_csv(out / f"club_table_{tag}{OUT_SUFFIX}.csv", index=False)
    paper = club_out.sort_values(["NETavailability", "Club"], ascending=[True, False]).reset_index(drop=True)
    paper.insert(0, "Paper rank (worst first)", paper.index + 1)
    paper.to_csv(out / f"club_table_paper_{tag}{OUT_SUFFIX}.csv", index=False)
    split = pd.DataFrame(split_rows)
    split.to_csv(out / f"club_split_half_{tag}{OUT_SUFFIX}.csv", index=False)
    if jan_rows:
        pd.DataFrame(jan_rows).to_csv(out / f"club_split_january_{tag}{OUT_SUFFIX}.csv", index=False)
    else:
        print(f"WARNING no winter window close found for {args.season}; club_split_january not written")

    esum = players.groupby("club").agg(players=("player_id", "size"), E_gt0=("E", lambda s: int((s > 0).sum())),
                                       E_full=("E", lambda s: int((s == s.max()).sum())), E_mean=("E", "mean"),
                                       E_sum=("E", "sum"), N_sum=("N", "sum"), A_sum=("A", "sum")).round(1)
    esum.to_csv(out / f"club_E_summary_{tag}{OUT_SUFFIX}.csv")

    print("\nPaper order (worst first):\n" + paper.drop(columns="team_id").to_string(index=False))
    print(f"\nL={L}, baseline={B} (tiered for foreign imports), rolling xU; NETabsence excludes sent-off mins; ranked by NETavailability\n")
    print(club_out.drop(columns="team_id").to_string(index=False))
    print("\nE summary per club:\n" + esum.to_string())
    if jan_rows:
        print(f"\nJanuary split (winter close {winter_close.date()}):\n" + pd.DataFrame(jan_rows).drop(columns="team_id").to_string(index=False))

    # ---- split-half Spearman (first 19 vs last 19 NETabsence across the clubs)
    if split.last19_NETabsence.notna().all() and len(split) > 2:
        rho = split.first19_NETabsence.rank().corr(split.last19_NETabsence.rank())
        pear = split.first19_NETabsence.corr(split.last19_NETabsence)
        print(f"\nSplit-half Spearman rho (first 19 vs last 19 NETabsence, n={len(split)}): {rho:.3f}  (Pearson {pear:.3f})")

    # ---- calibration per fixture
    cal_rows = []
    for r in fx_s.sort_values("date").itertuples():
        h, a = int(r.home_id), int(r.away_id)
        hs, as_ = calib_sum.get((r.fixture_id, h), 0.0), calib_sum.get((r.fixture_id, a), 0.0)
        cal_rows.append(dict(fixture_id=r.fixture_id, date=r.date.date(), home_id=h, home=club_name.get(h, h),
                             away_id=a, away=club_name.get(a, a), home_named=calib_n.get((r.fixture_id, h), 0),
                             home_sum_xU=round(hs, 3), away_named=calib_n.get((r.fixture_id, a), 0),
                             away_sum_xU=round(as_, 3), total_sum_xU=round(hs + as_, 3)))
    cal = pd.DataFrame(cal_rows)
    cal.to_csv(out / f"calibration_{tag}{OUT_SUFFIX}.csv", index=False)
    team_sums = pd.concat([cal[["home_id", "home_sum_xU"]].rename(columns={"home_id": "team_id", "home_sum_xU": "sum_xU"}),
                           cal[["away_id", "away_sum_xU"]].rename(columns={"away_id": "team_id", "away_sum_xU": "sum_xU"})])
    per_club = team_sums.groupby("team_id").sum_xU.agg(["mean", "min", "max"]).round(3)
    per_club.insert(0, "club", [club_name.get(t, t) for t in per_club.index])
    print(f"\ncalibration: sum of exclusive xU over named players, per team per fixture (target ~ 11)\n"
          + per_club.sort_values("mean").to_string())
    print(f"calibration league mean per team per fixture: {team_sums.sum_xU.mean():.3f} over {len(team_sums)} team-fixtures "
          f"(mean named per team {np.mean(list(calib_n.values())):.1f})")

    # ---- allowance report
    acols = ["team_id", "club", "player_id", "player", "arrival_date", "arrival_type", "arrival_from", "effective", "fixture_id",
             "date", "day", "eligible_v3", "charged_v3", "removed_by_allowance"]
    adf = pd.DataFrame(allowance_rows, columns=acols).sort_values(["club", "arrival_date", "player", "date"])
    adf.to_csv(out / f"allowance_detail_{tag}{OUT_SUFFIX}.csv", index=False)
    arr_n = {}
    for (c, pid) in pairs:
        for e in timeline.get((pid, c), ()):
            if e.kind == "in" and e.type in ARRIVAL_TYPES and season_start - timedelta(days=ALLOWANCE_REPORT_DAYS) <= e.rec <= season_end:
                arr_n[c] = arr_n.get(c, 0) + 1
    al_rows = []
    for c in club_ids:
        g = adf[adf.team_id == c]
        d0_2 = g[g.day.between(0, 2)].removed_by_allowance.sum()
        d1_3 = g[g.day.between(1, 2)].removed_by_allowance.sum() + g[g.day == 3].charged_v3.sum()
        d3 = g[g.day == 3].charged_v3.sum()
        d4_14 = g[g.day.between(4, 14)].charged_v3.sum()
        al_rows.append(dict(club=club_name.get(c, c), team_id=c, arrivals=arr_n.get(c, 0),
                            removed_d0_d2=round(d0_2, 1), band_d1_d3=round(d1_3, 1), charged_d3=round(d3, 1),
                            charged_d4_d14=round(d4_14, 1)))
    al = pd.DataFrame(al_rows)
    al.to_csv(out / f"allowance_{tag}{OUT_SUFFIX}.csv", index=False)
    print(f"\nallowance report (minutes): removed_d0_d2 = would-be NETabsence on days X..X+2 after an arrival record "
          f"(blocked by the +3 rule); band_d1_d3 = the X+1..X+3 band (X+1, X+2 hypothetical + X+3 charged); "
          f"charged_d4_d14 = NETabsence charged on X+4..X+14\n" + al.drop(columns="team_id").to_string(index=False))
    print(f"allowance totals: removed_d0_d2 {al.removed_d0_d2.sum():.0f}; band_d1_d3 {al.band_d1_d3.sum():.0f}; "
          f"charged_d4_d14 {al.charged_d4_d14.sum():.0f}")
    # allowance diagnostic — absence rate (minutes per retained unnamed player-fixture) on days 4-14 vs the club average
    diag = []
    for c in club_ids:
        g = adf[(adf.team_id == c) & adf.day.between(4, 14) & (adf.eligible_v3 == 1)]
        p = players[players.team_id == c]
        club_rate = p.NETabsence.sum() / p.A.sum() if p.A.sum() else None
        band_rate = g.charged_v3.sum() / len(g) if len(g) else None
        diag.append(dict(club=club_name.get(c, c), band_player_fixtures=len(g), band_minutes=round(g.charged_v3.sum(), 1),
                         band_rate=round(band_rate, 2) if band_rate is not None else None,
                         club_rate=round(club_rate, 2) if club_rate else None,
                         ratio=round(band_rate / club_rate, 3) if (band_rate is not None and club_rate) else None))
    dg = pd.DataFrame(diag)
    pooled_band = adf[adf.day.between(4, 14) & (adf.eligible_v3 == 1)]
    pooled_rate = pooled_band.charged_v3.sum() / len(pooled_band) if len(pooled_band) else float("nan")
    pooled_club = players.NETabsence.sum() / players.A.sum()
    r = dg.ratio.dropna()
    print("\nallowance diagnostic (minutes per eligible unnamed player-fixture; band = days 4-14 after an arrival record):\n"
          + dg.to_string(index=False))
    print(f"allowance pooled: band rate {pooled_rate:.2f} over {len(pooled_band)} player-fixtures vs club-average rate {pooled_club:.2f} "
          f"(ratio {pooled_rate / pooled_club:.3f}); mean club ratio {r.mean():.3f} +- SE {r.std(ddof=1) / np.sqrt(len(r)):.3f} (n={len(r)} clubs)")

    # ---- undated contracts with material NETabsence (any season)
    nd = pulls / f"contracts_no_dated_record{msfx}.csv"
    if not nd.exists():
        nd = pulls / "contracts_no_dated_record.csv"
    if nd.exists():
        undated = set(pd.read_csv(nd).player_id.astype(int))
        m = players[players.player_id.isin(undated) & (players.NETabsence > 0)]
        m = m[["player", "club", "E", "N", "NETabsence"]].sort_values("NETabsence", ascending=False)
        m.to_csv(out / f"undated_contracts_material_{tag}{OUT_SUFFIX}.csv", index=False)
        print(f"\nE: {len(m)} of {len(undated)} undated-contract players have NETabsence > 0 in {args.season}")

    # ---- seeds print (target clubs)
    if seeds is not None:
        st = seeds[seeds.team_id.isin(club_ids)]
        print(f"\n{seeds_path.name}: {len(seeds)} clubs in file; target-season clubs:")
        print(st.to_string(index=False))

    # ---- movers: players whose target-season club differs from the club they were last named for
    if seeds is not None:
        mv = []
        n_seed_default = 0
        for (c, pid), fn in first_named_here.items():
            g = by_player[pid]["g"]
            prior = g[g.date < fn]
            if prior.empty:
                continue
            last = prior.iloc[-1]
            if int(last.team_id) == c:
                continue
            if int(last.team_id) not in seed_of:
                n_seed_default += 1
            from_seed, to_seed = seed_lookup(int(last.team_id)), seed_lookup(c)
            direction = "up" if to_seed < from_seed else ("down" if to_seed > from_seed else "same")
            carried, cinfo = xU_calc(pid, c, fn, exclusive=True)
            carried_raw = carried if not delta else xU_calc(pid, c, fn, exclusive=True, delta_override=0.0)[0]
            here = g[(g.team_id == c) & (g.date >= fn)].head(L)
            realised = float(here.proportion.mean())
            mv.append(dict(player_id=pid, player=last.player, from_club=club_name.get(int(last.team_id), last.team_id),
                           to_club=club_name.get(c, c), from_seed=from_seed, to_seed=to_seed, direction=direction,
                           is_gk=cinfo["is_gk"], last_named_from=last.date.date(), first_named_to=fn.date(),
                           carried_xU=round(carried, 4), carried_xU_raw=round(carried_raw, 4),
                           realised_xU=round(realised, 4), n_squads=len(here), difference=round(realised - carried, 4)))
        movers = pd.DataFrame(mv).sort_values(["to_club", "player"])
        mpath = out / f"movers_{tag}{OUT_SUFFIX}.csv"
        movers.to_csv(mpath, index=False)

        def summarise(df):
            s = df.groupby("direction").agg(n=("player_id", "size"), mean_carried=("carried_xU", "mean"),
                                            mean_realised=("realised_xU", "mean"), mean_difference=("difference", "mean")).round(4)
            return s.reindex([d for d in ("up", "same", "down") if d in s.index])

        summ = summarise(movers)
        summ.to_csv(out / f"movers_summary_{tag}{OUT_SUFFIX}.csv")
        summ_nogk = summarise(movers[movers.is_gk == 0])
        summ_nogk.to_csv(out / f"movers_summary_nogk_{tag}{OUT_SUFFIX}.csv")
        print(f"\n{mpath.name}: {len(movers)} rows (mover_delta={delta}; {n_seed_default} from-clubs outside the seed file -> seed 5)\n"
              + summ.to_string())
        ng = movers[movers.is_gk == 0].copy()
        ng["pot_delta"] = (ng.to_seed - ng.from_seed).clip(-2, 2)
        for lab, col in (("raw carried", "carried_xU_raw"), ("delta-adjusted carried", "carried_xU")):
            y = ng.realised_xU - ng[col]; x = ng.pot_delta.astype(float)
            if len(ng) > 2 and x.nunique() > 1:
                X = np.column_stack([np.ones(len(x)), x]); beta, res, *_ = np.linalg.lstsq(X, y, rcond=None)
                resid = y - X @ beta; s2 = (resid ** 2).sum() / (len(x) - 2)
                se = np.sqrt(s2 * np.linalg.inv(X.T @ X).diagonal())
                print(f"mover slope ({lab}, keepers excluded, n={len(ng)}): gap = {beta[0]:.4f} (SE {se[0]:.4f}) + "
                      f"{beta[1]:.4f} (SE {se[1]:.4f}) x pot_delta   [pot_delta = to_seed - from_seed, clipped -2..2]")
        print(f"\nkeeper-excluded ({int((movers.is_gk == 0).sum())} rows):\n" + summ_nogk.to_string())


if __name__ == "__main__":
    main()
