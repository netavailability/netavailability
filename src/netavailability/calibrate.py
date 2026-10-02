#!/usr/bin/env python3
"""Calibration re-measure: measures the method's constants on a run folder. It only measures: it changes no constant.

Usage:
  python calibrate.py --run-dir DIR --out DIR --set SET7|SET11|both [--fit S ...] [--test S ...] [--jobs N] [--skip-instrument]
  main(argv) can also be imported and called; it returns {set name: result dict (the JSON content)}.

The module is self-contained (standard library, numpy, pandas, scipy, statsmodels): its instrumented children are
started by file path.

Run-folder contract (common.py): <run-dir>/runs.csv (season, input_set, rc, seconds, command = JSON list) and
<run-dir>/<season-tag>/<name>_<season-tag><SFX>.csv. Each season's input files (teams / appearances / fixtures) are read
from the --pulls / --suffix / --meta-suffix of that season's own command, so a run that spans several input sets is
measured on the files each season was computed from.

SET7 = 2018/19, 2019/20, 2021/22, 2022/23-2025/26; SET11 = SET7 + 2014/15-2017/18; 2020/21 is never used.
Chronological blocks: test = 2022/23-2025/26, fit = the set's earlier seasons; --fit / --test override (restricted to
the set's seasons).

Method:
1. INSTRUMENTED PASS. Each season's command from runs.csv is replayed unchanged (same script, same flags; only --out
   is redirected to <out>/inst/<season-tag>/) under a read-only sys.setprofile hook that captures every xU_calc and
   call of the compute's eligibility function with its caller context (the call sites are found by their source text). The
   instrumented club table is hashed against the run's (the hook changes nothing). With --set both the pass runs once
   for the union of seasons.
2. POPULATIONS. The charged calls (named and absence fixtures), the mover population (player-seasons with a slot
   carried from another Premier League club in a charged call) and the fill population (imports with a fill slot).
3. MOVER ROWS. Per mover: carried = mean raw proportion over the carried slots at his first naming for the club in the
   season, pot delta = from_seed - to_seed (unclipped), realised = his first 12 squads for the club inside the season,
   gap = realised - carried.
4. MOVER STATISTICS. OLS of gap on pot delta through zero and with intercept, delta = -slope, on the fit / test / all
   blocks; chronological fit-to-test residuals; residual slopes with a fixed delta applied; the same-pot (sideways)
   cell (pot delta = 0).
5. TIER FILLS, keepers excluded: realised = mean proportion over the first 12 named squads for the club dated on or
   after the arrival in force, per origin group.
6. L COMPOSITE. Bin weights from the run's absence spells (the set's seasons); per-season mean absolute error of the
   last-L mean against the next H squads (H horizons 1-18, window from the start of the previous season); the
   weighted composite per L per season; the best L on fit / test / all; paired t and Wilcoxon tests of L12 against
   L13, L14, L11, L10 (and against a block's best L when that is another value).
Outputs per set in <out>/: calibration_<SET>.md, calibration_table_<SET>.csv, calibration_<SET>.json and the detail
CSVs in <out>/<SET>/populations, movers, tier_fills, L_window; captures in <out>/inst/.
"""
import argparse, hashlib, json, os, runpy, shutil, subprocess, sys, time, warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
K = ["season", "player_id", "team_id"]
L = 12
PL_NAME = "Premier League"
SET7 = ["2018/2019", "2019/2020", "2021/2022", "2022/2023", "2023/2024", "2024/2025", "2025/2026"]
SET11 = ["2014/2015", "2015/2016", "2016/2017", "2017/2018"] + SET7
SETS = {"SET7": SET7, "SET11": SET11}
TEST_DEFAULT = ["2022/2023", "2023/2024", "2024/2025", "2025/2026"]
# the spec values in force (used when the run's command does not carry the flag)
SPEC = {"mover": 0.10, "sideways": -0.15, "tier1": 0.5, "tier2": 0.35, "tier3": 0.25, "data_club": 0.45, "unknown": 0.35, "L": 12}
FLAG = {"mover": "--mover-delta", "sideways": "--sideways-adjust", "tier1": "--tier1-fill", "tier2": "--tier2-fill",
        "tier3": "--tier3-fill", "data_club": "--data-club-fill", "unknown": "--unknown-fill", "L": "--L"}
L_COMPARATORS = (13, 14, 11, 10)


def tag(s):
    return s.replace("/", "-")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def prev_season_name(name):
    a, b = name.split("/")
    return f"{int(a)-1}/{int(b)-1}"


def season_of(d):
    d = pd.Timestamp(d)
    y = d.year if d.month >= 7 else d.year - 1
    return f"{y}/{y + 1}"


def read_runs(run_dir):
    runs = pd.read_csv(Path(run_dir) / "runs.csv")
    return {r.season: json.loads(r.command) for r in runs.itertuples()}


def opt(cmd, flag, default=None):
    return cmd[cmd.index(flag) + 1] if flag in cmd else default


# ---------------------------------------------------------------- 1. instrumented child
def child(season, run_dir, out_root):
    cmd = list(read_runs(run_dir)[season])
    COMPUTE = Path(cmd[1])
    out = Path(out_root) / "inst" / tag(season)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    i = cmd.index("--out"); cmd[i + 1] = str(out)
    src = COMPUTE.read_text().splitlines()
    # caller contexts by source text
    pats = {"as_of": "xU_asof, info = xU_calc", "named": "xf, _ = xU_calc(pid, c, r.date, exclusive=True)\n                net +=",
            "absence": "xf, inf = xU_calc", "allowance_hyp": "xf, _ = xU_calc(pid, c, r.date, exclusive=True)\n                    charged, hyp",
            "sentoff": "xU_b, _ = xU_calc", "mover": "carried, cinfo = xU_calc", "mover_raw": "carried_raw = carried if not delta else xU_calc"}
    optional = {"retention_hyp": "_hyp = xU_calc(pid, c, D, exclusive=True)"}     # the retention-override call site
    CTX = {}
    for k, pat in {**pats, **optional}.items():
        first = pat.split("\n")[0]
        cands = [n + 1 for n, ln in enumerate(src) if first in ln]
        if "\n" in pat:
            nxt = pat.split("\n")[1].strip()
            cands = [n for n in cands if nxt in src[n]]
        if k in optional and not cands:
            continue
        assert len(cands) == 1, (k, cands)
        CTX[cands[0]] = k
    n_sites = sum(1 for ln in src if "xU_calc(" in ln and "def xU_calc" not in ln)
    assert n_sites == len(CTX), f"xU_calc call sites in {COMPUTE.name}: {n_sites}, contexts recognised: {len(CTX)}"
    calls, slots_rows, eligs, dump = [], [], [], {}
    fname = str(COMPUTE)

    def hook(frame, event, arg):
        if event != "return":
            return
        co = frame.f_code; nm = co.co_name
        if nm == "xU_calc":
            if co.co_filename != fname:
                return
            lc = frame.f_locals; back = frame.f_back
            ctx = CTX.get(back.f_lineno, f"line{back.f_lineno}")
            fixture_id = int(back.f_locals["r"].fixture_id) if ctx in ("named", "absence", "allowance_hyp", "sentoff") else None
            pid, club, slots, p, Lx, seed_lookup = lc["pid"], lc["club"], lc["slots"], lc["p"], lc["L"], lc["seed_lookup"]
            call_id = len(calls)
            n_adj, sum_raw, sum_adj, n_same_nonpl = 0, 0.0, 0.0, 0
            from_c, from_u, from_e, from_g = set(), set(), set(), set()
            if p is not None and slots:
                lo, hi = lc["lo"], lc["hi"]
                for i, (kind, v) in zip(range(max(lo, hi - Lx), hi), slots):
                    tid = int(p["team_id"][i]); raw = float(p["prop"][i])
                    if kind == "carried":
                        sum_raw += raw; sum_adj += v
                        if abs(v - raw) > 1e-12:
                            n_adj += 1
                        from_c.add(tid)
                    elif kind == "unseen":
                        from_u.add(tid)
                    elif kind == "expired":
                        from_e.add(tid)
                    elif kind == "gk_other":
                        from_g.add(tid)
                    elif kind == "actual" and not p["is_pl"][i]:
                        n_same_nonpl += 1
                    if ctx in ("absence", "mover", "as_of") or kind in ("carried", "unseen", "expired", "gk_other", "sentoff"):
                        slots_rows.append((call_id, i, str(p["dates"][i])[:10], int(p["fixture_id"][i]), tid, int(bool(p["is_pl"][i])), kind, raw,
                                           None if v is None else float(v), seed_lookup(tid) if kind == "carried" else None))
            kinds = [k for k, _ in slots]; arr = lc["arr"]
            calls.append(dict(call_id=call_id, ctx=ctx, player_id=int(pid), team_id=int(club), ref_date=str(lc["ref_date"])[:10],
                              fixture_id=fixture_id, exclusive=int(bool(lc["exclusive"])), delta=lc["dl"], xU=float(lc["xU"]),
                              is_gk=int(bool(lc["is_gk"])), is_import=int(bool(lc["imp"])), named_before=int(bool(lc["named_before"])),
                              fill_ok=int(bool(lc["fill_ok"])), tier=lc["tier"], fill=float(lc["fill"]),
                              arrival_eff=None if arr is None else str(arr)[:10],
                              n_actual=kinds.count("actual"), n_actual_nonpl=n_same_nonpl, n_carried=kinds.count("carried"),
                              n_carried_adjusted=n_adj, sum_carried_raw=sum_raw, sum_carried_adj=sum_adj,
                              n_unseen=kinds.count("unseen"), n_expired=kinds.count("expired"), n_gk_other=kinds.count("gk_other"),
                              n_sentoff=kinds.count("sentoff"), so_val=float(lc["so_val"]), shortfall=int(lc["shortfall"]),
                              n_empty_filled=int(lc["n_fill"]), fixtures_since_arrival=int(lc["n_fx"]), to_seed=seed_lookup(club),
                              carried_from="|".join(map(str, sorted(from_c))), unseen_from="|".join(map(str, sorted(from_u))),
                              expired_from="|".join(map(str, sorted(from_e))), gk_other_from="|".join(map(str, sorted(from_g)))))
        elif nm == "eligibility":
            if co.co_filename != fname:
                return
            lc = frame.f_locals
            c, pid = lc["c"], lc["pid"]
            ivs, has_rec, in_squad, gate, academy = lc["ivs"], lc["has_rec"], lc["in_squad"], lc["gate"], lc["academy"]
            fnh = lc["fnh"]
            eligs.append(dict(team_id=int(c), player_id=int(pid), academy=int(bool(academy)), gate=None if gate is None else str(gate)[:10],
                              first_named_here=None if fnh is None else str(fnh)[:10], has_contract_record=int(bool(has_rec)),
                              n_dated_contracts=len(ivs), in_squad=int(bool(in_squad)),
                              basis=lc["basis"] if isinstance(lc["basis"], str) else "".join(sorted(lc["basis"])),
                              n_blocked=int(lc["n_blocked"]), n_allow=int(lc["n_allow"]), n_forced=int(lc["n_forced"]),
                              elig="".join("1" if x else "0" for x in lc["elig"]), base="".join("1" if x else "0" for x in lc["base_l"])))
        elif nm == "main":
            if co.co_filename != fname:
                return
            dump.update(frame.f_locals)

    sys.argv = cmd[1:]
    os.chdir(COMPUTE.parent)
    sys.setprofile(hook)
    try:
        runpy.run_path(str(COMPUTE), run_name="__main__")
    finally:
        sys.setprofile(None)
    d = dump; t = tag(season)
    INST = out.parent
    pd.DataFrame(calls).to_csv(INST / f"xu_calls_{t}.csv", index=False)
    pd.DataFrame(slots_rows, columns=["call_id", "slot_index", "slot_date", "slot_fixture_id", "slot_team_id", "slot_is_pl", "kind", "raw_proportion",
                                      "value_used", "from_seed"]).to_csv(INST / f"xu_slots_{t}.csv", index=False)
    pd.DataFrame(eligs).to_csv(INST / f"eligibility_{t}.csv", index=False)
    pairs = d["pairs"]; pids = {p for _, p in pairs}
    tier_of_from, in_from_id, team_name_any = d["tier_of_from"], d["in_from_id"], d["team_name_any"]
    rows = []
    for (pid, club), evs in d["timeline"].items():
        if pid not in pids:
            continue
        for e in evs:
            frm = in_from_id.get((pid, club, e.rec)) if (e.kind == "in" and e.type in (218, 219, 220)) else None
            rows.append(dict(player_id=pid, team_id=club, club=team_name_any.get(club, club), in_target_pairs=int((club, pid) in pairs), kind=e.kind, type=e.type,
                             rec=str(e.rec)[:10], eff=str(e.eff)[:10], lag_days=(e.eff - e.rec).days, genuine=int(bool(e.genuine)), synth=int(bool(e.synth)),
                             other=e.other, from_team_id=frm, from_tier=tier_of_from(frm) if (e.kind == "in" and e.type in (218, 219, 220)) else None,
                             from_in_data=None if frm is None else int(frm in d["data_clubs"])))
    pd.DataFrame(rows).to_csv(INST / f"timeline_{t}.csv", index=False)
    pd.DataFrame([dict(player_id=k[0], team_id=k[1], origin_date=v[0], origin_from=v[1], origin_type=v[2]) for k, v in d["origin"].items()
                  if (k[1], k[0]) in pairs]).to_csv(INST / f"origin_{t}.csv", index=False)
    pd.DataFrame([dict(team_id=c, player_id=p, first_named_club_any=str(d["first_named_club_any"].get((c, p)))[:10],
                       first_named_any=str(d["first_named_any"].get(p))[:10], is_gk=int(d["position_of"](p) == 24), position_id=d["position_of"](p))
                  for (c, p) in sorted(pairs)]).to_csv(INST / f"pairs_{t}.csv", index=False)
    pd.DataFrame([dict(key="season_start", value=str(d["season_start"])[:10]), dict(key="season_end", value=str(d["season_end"])[:10]),
                  dict(key="window_start", value=str(d["window_start"])[:10]), dict(key="L", value=d["L"]), dict(key="delta", value=d["delta"]),
                  dict(key="baseline", value=d["B"]), dict(key="n_pairs", value=len(pairs)), dict(key="n_xU_calls", value=len(calls)),
                  dict(key="pot_seasons", value="|".join(d["pot_seasons"]))]).to_csv(INST / f"run_facts_{t}.csv", index=False)
    print(f"CALIB {season}: {len(calls)} xU_calc calls, {len(eligs)} eligibility calls; contexts {sorted(CTX.values())}", file=sys.stderr)


# ---------------------------------------------------------------- input-set context (teams / appearances / fixtures of one --pulls)
class Ctx:
    """The input files one group of seasons was computed from."""

    def __init__(self, pulls, sfx, msfx, seasons):
        self.key, self.seasons = (str(pulls), sfx, msfx), list(seasons)
        pulls = Path(pulls)
        teams = pd.read_csv(pulls / f"teams{msfx}.csv")
        self.teams = teams
        self.id2name = dict(zip(teams.team_id, teams.name))
        self.league_in = {(int(r.team_id), r.season): r.league for r in teams.itertuples()}
        self.data_clubs = set(teams.team_id)
        a = pd.read_csv(pulls / f"appearances{sfx}.csv", parse_dates=["date"])          # load_apps()
        a = a[a.player_id.notna()].copy()
        a["player_id"] = a.player_id.astype(int)
        a = a.sort_values(["date", "fixture_id"]).reset_index(drop=True)
        a["season"] = a.season_id.map(dict(zip(teams.season_id, teams.season)))            # every league (mover rows)
        self.pl_ids = {int(r_.season_id): r_.season for r_ in teams[teams.league == PL_NAME].drop_duplicates("season_id").itertuples()}
        a["pl_season"] = a.season_id.map(self.pl_ids)                                      # PL seasons only (L composite)
        self.apps = a
        fx = pd.read_csv(pulls / f"fixtures{sfx}.csv", parse_dates=["date"]); fx["date"] = fx.date.dt.normalize()
        self.fx = fx

    def from_league(self, tid, date):
        if pd.isna(tid):
            return "unknown"
        lg = self.league_in.get((int(tid), season_of(date)))
        if lg is not None:
            return lg
        return "data club, neither league that season" if int(tid) in self.data_clubs else "outside data"


# ---------------------------------------------------------------- 2. populations (input-set context passed in)
def charged_calls(calls, tl, ctx):
    charged = calls[calls.ctx.isin(["named", "absence"])].copy()
    charged["uses_fill"] = (charged.n_unseen > 0) | (charged.n_empty_filled > 0) | ((charged.n_sentoff > 0) & (charged.n_actual + charged.n_carried == 0))
    charged["fill_slots"] = charged.n_unseen + charged.n_empty_filled
    ORDER = {9688: 0, 219: 1, 220: 1, 218: 2, 0: 1}
    arr_ev = tl[(tl.kind == "in") & tl.type.isin([218, 219, 220]) & (tl.genuine == 1)].copy()
    arr_ev["order"] = arr_ev.type.map(ORDER)
    m = charged.loc[charged.arrival_eff.notna(), K + ["call_id", "ref_date", "arrival_eff"]].merge(
        arr_ev[K + ["rec", "eff", "order", "type", "other", "from_team_id", "from_tier"]], on=K)
    m = m[m.rec <= m.ref_date].sort_values(["rec", "order"]).groupby(["season", "call_id"]).tail(1)
    assert (m.eff == m.arrival_eff).all() and len(m) == charged.arrival_eff.notna().sum()
    charged = charged.merge(m[["season", "call_id", "rec", "type", "other", "from_team_id", "from_tier"]].rename(
        columns={"rec": "arr_rec", "type": "arr_type", "other": "arr_from", "from_team_id": "arr_from_id", "from_tier": "arr_from_tier"}),
        on=["season", "call_id"], how="left")
    charged["arr_from_league"] = [ctx.from_league(t, d) if isinstance(d, str) else None for t, d in zip(charged.arr_from_id, charged.arr_rec)]
    return charged


def mover_population(charged, slots, ctx):
    g = charged.groupby(K).agg(is_gk=("is_gk", "max"), charged_calls=("xU", "size"),
                               calls_with_carried=("n_carried", lambda x: int((x > 0).sum())),
                               calls_adjusted=("n_carried_adjusted", lambda x: int((x > 0).sum()))).reset_index()
    cs = slots[slots.kind == "carried"].merge(charged[["season", "call_id", "player_id", "team_id", "ctx"]], on=["season", "call_id"])
    frm = cs.groupby(K).slot_team_id.agg(lambda x: ", ".join(ctx.id2name.get(t, str(t)) for t in sorted(set(x)))).rename("carried_from").reset_index()
    return g[g.calls_with_carried > 0].merge(frm, on=K, how="left")


def fill_population(charged):
    imp_fill = charged[(charged.is_import == 1) & charged.uses_fill].copy()
    imp_fill["origin_group"] = np.where(imp_fill.tier == "data_club",
                                        "data club: " + imp_fill.arr_from_league.fillna("no arrival on or before the date"), imp_fill.tier)
    imp_fill.loc[imp_fill.is_gk == 1, "origin_group"] = "keeper: " + imp_fill.arr_from_tier.fillna("none").where(
        imp_fill.arr_from_tier != "data_club", "data club: " + imp_fill.arr_from_league.fillna(""))
    r2 = imp_fill.groupby(K + ["is_gk", "tier", "fill", "origin_group"], dropna=False).agg(
        calls_named=("ctx", lambda x: int((x == "named").sum())), calls_absence=("ctx", lambda x: int((x == "absence").sum())),
        fill_slots=("fill_slots", "sum"), arr_from=("arr_from", "last"), arr_rec=("arr_rec", "last"),
        first_fill_ref=("ref_date", "min")).reset_index()
    return r2


# ---------------------------------------------------------------- 3. mover rows
def mover_rows(pop, calls, slots, elig, facts, ctx):
    apps = ctx.apps
    rows = pop.merge(elig[K + ["first_named_here"]], on=K, how="left")
    assert len(rows) == len(pop)
    first_any = apps.groupby(["team_id", "player_id"]).date.min().rename("first_named_club_ever").reset_index()
    rows = rows.merge(first_any, on=["team_id", "player_id"], how="left")
    named = calls[calls.ctx == "named"]
    first_call = rows[rows.first_named_here.notna()].merge(named, left_on=K + ["first_named_here"], right_on=K + ["ref_date"], suffixes=("", "_call"))
    assert (first_call.empty or first_call.groupby(K).size().max() == 1) and len(first_call) == rows.first_named_here.notna().sum()
    cs = slots[slots.kind == "carried"].merge(first_call[["season", "call_id"] + ["player_id", "team_id", "to_seed"]], on=["season", "call_id"])
    cs["slot_delta"] = cs.from_seed - cs.to_seed
    agg = cs.groupby(K).agg(n_carried_slots=("raw_proportion", "size"), carried=("raw_proportion", "mean"), carried_adjusted_005=("value_used", "mean"),
                            pot_delta=("slot_delta", "mean"), n_from_clubs=("slot_team_id", "nunique"), n_slot_deltas=("slot_delta", "nunique"),
                            from_seed=("from_seed", "mean"), first_carried_slot=("slot_date", "min"), last_carried_slot=("slot_date", "max"),
                            from_clubs=("slot_team_id", lambda x: ", ".join(ctx.id2name.get(t, str(t)) for t in sorted(set(x))))).reset_index()
    rows = rows.merge(first_call[K + ["call_id", "to_seed", "n_actual", "n_carried", "n_unseen", "n_expired", "n_sentoff", "shortfall", "n_empty_filled", "xU"]]
                      .rename(columns={"xU": "xU_at_first_naming", "call_id": "first_naming_call_id"}), on=K, how="left").merge(agg, on=K, how="left")
    real, real_x = {}, {}
    g_by = {k: g for k, g in apps[apps.player_id.isin(rows.player_id)].groupby(["player_id", "team_id"])}
    for r in rows[rows.first_named_here.notna()].itertuples():
        g = g_by[(r.player_id, r.team_id)]
        fn = pd.Timestamp(r.first_named_here)
        end = pd.Timestamp(facts[r.season]["season_end"])
        h = g[(g.date >= fn) & (g.date <= end)].head(L)
        assert (h.season == r.season).all() and (h.league_id == 8).all(), (r.season, r.player_id, r.team_id)
        real[(r.season, r.player_id, r.team_id)] = (float(h.proportion.mean()), len(h), int(h.sent_off.sum()))
        hx = g[g.date >= fn].head(L)
        real_x[(r.season, r.player_id, r.team_id)] = (float(hx.proportion.mean()), len(hx))
    key = list(map(tuple, rows[K].values))
    rows["realised"] = [real.get(k, (np.nan,))[0] for k in key]
    rows["n_squads"] = [real.get(k, (np.nan, 0))[1] for k in key]
    rows["n_sent_off_in_realised"] = [real.get(k, (np.nan, 0, 0))[2] for k in key]
    rows["realised_across_season_end"] = [real_x.get(k, (np.nan,))[0] for k in key]
    rows["n_squads_across_season_end"] = [real_x.get(k, (np.nan, 0))[1] for k in key]
    rows["gap"] = rows.realised - rows.carried
    rows["first_naming_for_club_is_this_season"] = (rows.first_named_club_ever.dt.strftime("%Y-%m-%d") == rows.first_named_here).astype(int)
    rows["status"] = np.select(
        [rows.first_named_here.isna(), rows.n_carried_slots.isna()],
        ["not measured: not named for the club this season (absences only), so no first naming and no realised",
         "not measured: no carried slot in the window at his first naming this season (the other-club PL squads come later in the season)"],
        "measured")
    return rows.drop(columns=["first_named_club_ever"]).assign(first_named_club_ever=rows.first_named_club_ever.dt.strftime("%Y-%m-%d"))


# ---------------------------------------------------------------- 5. tier-fill rows
LAB = {"tier1": "tier1", "tier2": "tier2", "tier3": "tier3", "unknown": "unknown", "data club: Championship": "Championship origin",
       "data club: Premier League": "PL origin", "data club: data club, neither league that season": "data club in neither league that season",
       "data club: no arrival on or before the date": "data club, arrival record dated after the fixture"}
DC_GROUPS = ["Championship origin", "PL origin", "data club in neither league that season"]


def tier_rows(r2, origin, ctx):
    apps = ctx.apps
    pop = r2.copy()
    pop["group"] = pop.origin_group.str.replace("^keeper: ", "", regex=True).map(LAB).fillna(pop.origin_group)
    pop = pop.merge(origin[K + ["origin_date", "origin_from"]], on=K, how="left")
    pop["arrival_used"] = pop.arr_rec.fillna(pop.origin_date)
    pop = pop[pop.arrival_used.notna()]
    g_by = {k: g for k, g in apps[apps.player_id.isin(pop.player_id)].groupby(["player_id", "team_id"])}
    real = []
    for r_ in pop.itertuples():
        g = g_by.get((r_.player_id, r_.team_id))
        h = g[g.date >= pd.Timestamp(r_.arrival_used)].head(L) if g is not None else None
        real.append((np.nan, 0) if h is None or h.empty else (float(h.proportion.mean()), len(h)))
    pop["realised"], pop["n_squads"] = zip(*real) if real else ((), ())
    pop["status"] = np.where(pop.n_squads > 0, "measured", "not measured: never named for the club on or after the arrival")
    return pop


# ---------------------------------------------------------------- 6. L composite pieces (horizon errors, per input set)
LS = list(range(6, 25)); HS = [1, 4, 6, 8, 10, 12, 14, 16, 18]
BINS = [(1, 1, 1), (2, 4, 4), (5, 6, 6), (7, 8, 8), (9, 10, 10), (11, 12, 12), (13, 14, 14), (15, 16, 16), (17, 10**9, 18)]


def bin_of(n):
    for lo, hi, H in BINS:
        if lo <= n <= hi:
            return H


def spells_of(ctx, traces):
    """Absence spells from the run's absence traces (club fixture order); traces = {season: DataFrame}."""
    fx = ctx.fx; sid_of_name = {v: k for k, v in ctx.pl_ids.items()}
    spell_rows = []
    for s, trc in traces.items():
        trc = trc.copy()
        fx_s = fx[fx.season_id == sid_of_name[s]]
        order = {}
        for c in set(fx_s.home_id).union(fx_s.away_id):
            dd = fx_s[(fx_s.home_id == c) | (fx_s.away_id == c)].sort_values("date")
            order[int(c)] = {int(f): i for i, f in enumerate(dd.fixture_id)}
        trc["idx"] = [order[int(c)][int(f)] for c, f in zip(trc.team_id, trc.fixture_id)]
        for (c, pid), g in trc.groupby(["team_id", "player_id"]):
            g = g.sort_values("idx"); run, prev = [], None
            for r_ in g.itertuples():
                if prev is not None and r_.idx == prev + 1:
                    run.append(r_.minutes)
                else:
                    if run:
                        spell_rows.append(dict(season=s, length=len(run), mins=sum(run)))
                    run = [r_.minutes]
                prev = r_.idx
            if run:
                spell_rows.append(dict(season=s, length=len(run), mins=sum(run)))
    return pd.DataFrame(spell_rows, columns=["season", "length", "mins"])


def horizon_mae(ctx):
    """Per-season MAE(L, H) for the ctx's seasons: (season, H, L, n, MAE)."""
    teams, fx, seasons = ctx.teams, ctx.fx, ctx.seasons
    sid_of_name = {v: k for k, v in ctx.pl_ids.items()}
    wstart = {}
    for S_ in sid_of_name:
        prev_ids = set(teams[teams.season == prev_season_name(S_)].season_id)
        wstart[S_] = fx[fx.season_id.isin(prev_ids)].date.min() if prev_ids else fx[fx.season_id == sid_of_name[S_]].date.min()
    ap_ = ctx.apps
    # only player-club groups with a squad in a target season contribute
    keys = ap_.loc[ap_.pl_season.isin(seasons), ["player_id", "team_id"]].drop_duplicates()
    ap_ = ap_.merge(keys.assign(_k=1), on=["player_id", "team_id"], how="left")
    ap_ = ap_[ap_._k == 1]
    acc = {}
    for (pid, club), g in ap_.groupby(["player_id", "team_id"], sort=False):
        pr = g.proportion.to_numpy(dtype=float); sn = g.pl_season.to_numpy(dtype=object); n = len(pr)
        if n < 2:
            continue
        idx = np.nonzero(g.pl_season.isin(seasons).to_numpy())[0]
        if len(idx) == 0:
            continue
        cs = np.concatenate([[0.0], np.cumsum(pr)]); dts = g.date.to_numpy()
        lo = np.empty(n, dtype=int); lo[idx] = [np.searchsorted(dts, np.datetime64(wstart[sn[t_]])) for t_ in idx]
        for H in HS:
            ok_h = idx[idx + H <= n - 1]
            if len(ok_h) == 0:
                continue
            truth = (cs[ok_h + H + 1] - cs[ok_h + 1]) / H
            for Lx in LS:
                ok = ok_h - Lx >= lo[ok_h]
                if not ok.any():
                    continue
                t_ = ok_h[ok]; ae = np.abs((cs[t_] - cs[t_ - Lx]) / Lx - truth[ok]); ss = sn[t_]
                for S_ in np.unique(ss):
                    mm = ss == S_; a = acc.setdefault((S_, H, Lx), [0, 0.0]); a[0] += int(mm.sum()); a[1] += float(ae[mm].sum())
    return pd.DataFrame([dict(season=k[0], H=k[1], L=k[2], n=v[0], MAE=v[1] / v[0]) for k, v in acc.items()], columns=["season", "H", "L", "n", "MAE"])


# ---------------------------------------------------------------- statistics
def P(p):
    return "<0.0001" if p < 0.0001 else f"{p:.4f}"


def grid(x):
    return round(round(x / 0.05) * 0.05, 2) + 0.0


def ols(d, intercept, y="gap", x="pot_delta", w=None, cluster=None):
    import statsmodels.api as sm
    X = sm.add_constant(d[[x]].astype(float)) if intercept else d[[x]].astype(float)
    mod = sm.WLS(d[y].astype(float), X, weights=d[w]) if w else sm.OLS(d[y].astype(float), X)
    f = mod.fit() if cluster is None else mod.fit(cov_type="cluster", cov_kwds={"groups": d[cluster]})
    out = dict(n=int(f.nobs), slope=f.params[x], slope_se=f.bse[x], slope_p=f.pvalues[x])
    if intercept:
        out.update(intercept=f.params["const"], intercept_se=f.bse["const"], intercept_p=f.pvalues["const"])
    return out


def fit_test(m, name, fit_s, test_s):
    f, t_ = m[m.season.isin(fit_s)], m[m.season.isin(test_s)]
    out = []
    for ic in (False, True):
        o = ols(f, ic)
        t2 = t_.copy()
        t2["resid"] = t2.gap - (o.get("intercept", 0.0) + o["slope"] * t2.pot_delta)
        r = ols(t2, ic, y="resid")
        ot = ols(t_, ic)
        out.append(dict(split=name, model="with intercept" if ic else "through zero", fit_n=o["n"], fit_slope_b=o["slope"], fit_SE=o["slope_se"], fit_delta=-o["slope"],
                        fit_intercept=o.get("intercept"), fit_intercept_SE=o.get("intercept_se"), test_n=len(t_), test_own_delta=-ot["slope"], test_own_SE=ot["slope_se"],
                        resid_mean=t2.resid.mean(), resid_mean_SE=t2.resid.std(ddof=1) / np.sqrt(len(t2)), resid_slope=r["slope"], resid_slope_SE=r["slope_se"], resid_slope_p=P(r["slope_p"])))
    return out


def se(x):
    return x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else np.nan


def md_table(df, floatfmt=None, default=".4f"):
    floatfmt = floatfmt or {}
    lines = ["| " + " | ".join(str(c) for c in df.columns) + " |", "|" + "---|" * len(df.columns)]
    for r in df.itertuples(index=False):
        cells = []
        for c, v in zip(df.columns, r):
            if v is None or (isinstance(v, (float, np.floating)) and np.isnan(v)):
                cells.append("")
            elif isinstance(v, (float, np.floating)):
                cells.append(format(v, floatfmt[c]) if c in floatfmt else (str(int(v)) if float(v).is_integer() and abs(v) < 1e6 else format(v, default)))
            else:
                cells.append(str(v).replace("|", "/").strip())
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def jsonable(o):
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


def short(ss):
    return "/".join(s[2:4] for s in ss)


# ---------------------------------------------------------------- the union pass: instrument + row-level measurements
def instrument(run_dir, out, seasons, cmds, jobs, log):
    INST = out / "inst"; INST.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    def one(s):
        t1 = time.time()
        r = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--run-dir", str(run_dir), "--out", str(out), "--child", s],
                           capture_output=True, text=True, cwd=HERE)
        (INST / f"stdout_{tag(s)}.txt").write_text(r.stdout); (INST / f"stderr_{tag(s)}.txt").write_text(r.stderr)
        return s, r.returncode, round(time.time() - t1, 1)
    with ThreadPoolExecutor(max(1, jobs)) as ex:
        res = list(ex.map(one, seasons))
    bad = [r for r in res if r[1] != 0]
    if bad:
        raise SystemExit(f"STOP: instrumented run failed: {bad}; see stderr files in {INST}")
    hrows = []
    for s in seasons:
        t = tag(s); sfx = opt(cmds[s], "--out-suffix")
        a_dir, b_dir = INST / t, Path(run_dir) / t
        a, b = a_dir / f"club_table_{t}{sfx}.csv", b_dir / f"club_table_{t}{sfx}.csv"
        files = sorted(p.name for p in b_dir.iterdir() if p.is_file())
        same = [f for f in files if (a_dir / f).exists() and sha(a_dir / f) == sha(b_dir / f)]
        hrows.append(dict(season=s, seconds=[r[2] for r in res if r[0] == s][0], club_table_identical=sha(a) == sha(b),
                          run_files=len(files), files_identical=len(same), files_differing="|".join(f for f in files if f not in same)))
    h = pd.DataFrame(hrows); h.to_csv(out / "inst_hashes.csv", index=False)
    log(f"  instrumented pass: {len(seasons)} seasons in {time.time() - t0:.0f} s ({jobs} parallel); club tables identical {int(h.club_table_identical.sum())}/{len(h)}")
    return h, time.time() - t0


def measure_rows(run_dir, out, seasons, cmds, log):
    """Row-level measurements for the union of seasons, one input set at a time."""
    INST = out / "inst"
    groups = {}
    for s in seasons:
        c = cmds[s]
        groups.setdefault((opt(c, "--pulls"), opt(c, "--suffix"), opt(c, "--meta-suffix", "")), []).append(s)
    parts = {k: [] for k in ("charged_n", "r1", "r2", "mrows", "trows", "ps")}
    ctxs = []
    for (pulls, sfx, msfx), ss in groups.items():
        t0 = time.time()
        ctx = Ctx(pulls, sfx, msfx, ss); ctxs.append(ctx)

        def per_season(pattern, **kw):
            return pd.concat([pd.read_csv(INST / pattern.format(tag=tag(s)), low_memory=False, **kw).assign(season=s) for s in ss], ignore_index=True)
        calls = per_season("xu_calls_{tag}.csv"); slots = per_season("xu_slots_{tag}.csv"); tl = per_season("timeline_{tag}.csv")
        elig = per_season("eligibility_{tag}.csv", dtype={"elig": str, "base": str, "basis": str})
        origin = per_season("origin_{tag}.csv")
        facts = {s: dict(pd.read_csv(INST / f"run_facts_{tag(s)}.csv").values) for s in ss}
        charged = charged_calls(calls, tl, ctx)
        r1 = mover_population(charged, slots, ctx)
        r2 = fill_population(charged)
        pt = pd.concat([pd.read_csv(Path(run_dir) / tag(s) / f"player_table_{tag(s)}{opt(cmds[s], '--out-suffix')}.csv").assign(season=s) for s in ss], ignore_index=True)
        names = pt[K + ["player", "club"]].drop_duplicates(K)
        r1 = r1.merge(names, on=K, how="left"); r2 = r2.merge(names, on=K, how="left")
        parts["charged_n"].append(charged.groupby("season").size().rename("charged_calls").reset_index())
        parts["r1"].append(r1); parts["r2"].append(r2)
        parts["mrows"].append(mover_rows(r1, calls, slots, elig, facts, ctx))
        parts["trows"].append(tier_rows(r2, origin, ctx))
        parts["ps"].append(horizon_mae(ctx))
        log(f"  rows for input set {Path(pulls).name} ({short(ss)}): {time.time() - t0:.0f} s")
    D = {k: pd.concat(v, ignore_index=True) for k, v in parts.items()}
    D["ctx_of"] = {s: c for c in ctxs for s in c.seasons}
    D["groups"] = {" ".join(k): v for k, v in groups.items()}
    return D


# ---------------------------------------------------------------- one set: statistics, table, report
def current_values(cmds, seasons):
    cur, src = {}, {}
    for k, flag in FLAG.items():
        vals = {opt(cmds[s], flag) for s in seasons}
        if len(vals) != 1:
            raise SystemExit(f"STOP: {flag} differs between the seasons of the run: {vals}")
        v = vals.pop()
        if v is None:
            cur[k], src[k] = (0.0, "flag absent: sideways adjustment off in this run") if k == "sideways" else (SPEC[k], "flag absent: spec value")
        else:
            cur[k], src[k] = (-float(v) if k == "sideways" else float(v)), f"{flag} {v}"
    cur["L"] = int(cur["L"])
    return cur, src


def analyse(name, ALL, FIT, TEST, D, run_dir, out, cmds, inst_h, script_sha):
    from scipy import stats
    C = out / name
    for sub in ("populations", "movers", "tier_fills", "L_window"):
        (C / sub).mkdir(parents=True, exist_ok=True)
    BLOCKS = (("fit", FIT), ("test", TEST), ("all", ALL))
    cur, cur_src = current_values(cmds, ALL)
    sfxs = sorted({opt(cmds[s], "--out-suffix") for s in ALL}); computes = sorted({Path(cmds[s][1]).name for s in ALL})
    md = [f"### Calibration re-measure, {name}, on `{Path(run_dir).name}`\n",
          f"Script `{Path(__file__).name}` (sha256 `{script_sha[:16]}…`); compute {', '.join('`' + c + '`' for c in computes)} as recorded in `runs.csv`; "
          f"run folder `{run_dir}` (suffix {', '.join(sfxs)}). Seasons {', '.join(ALL)}; chronological fit {', '.join(FIT)} → test {', '.join(TEST)}. "
          f"Input sets: " + "; ".join(f"{Path(k.split(' ')[0]).name if ' ' in k else k} = {short([s for s in v if s in ALL])}" for k, v in D["groups"].items() if set(v) & set(ALL)) +
          f". Detail files in `{C}`. This stage measures only: no constant is changed.\n"]
    say = lambda s="": md.append(s)
    res = dict(set=name, seasons=ALL, fit=FIT, test=TEST, run_dir=str(run_dir), current=cur, current_source=cur_src)
    # ---- 1
    if inst_h is not None:
        h = inst_h[inst_h.season.isin(ALL)]
        n_same, n_all = int(h.club_table_identical.sum()), len(h)
        say(f"**1. Instrumented pass**: club tables identical to the run's in {n_same}/{n_all} seasons (the hook changed nothing); "
            f"every file of the season folders compared: {int(h.files_identical.sum())}/{int(h.run_files.sum())} identical"
            + ("" if (h.files_identical == h.run_files).all() else f" (differing: {dict(zip(h.season, h.files_differing))})") + ".\n")
        res["instrumented"] = dict(club_tables_identical=n_same, seasons=n_all, files_identical=int(h.files_identical.sum()), files=int(h.run_files.sum()))
    else:
        say("**1. Instrumented pass**: skipped (--skip-instrument): the captures already in `inst/` were reused; identity not re-checked.\n")
        res["instrumented"] = None
    # ---- 2
    r1 = D["r1"][D["r1"].season.isin(ALL)]; r2 = D["r2"][D["r2"].season.isin(ALL)]
    r1.to_csv(C / "populations" / "mover_population.csv", index=False); r2.to_csv(C / "populations" / "fill_population.csv", index=False)
    cn = dict(zip(D["charged_n"].season, D["charged_n"].charged_calls))
    pop_t = pd.DataFrame([dict(season=s, charged_calls=int(cn.get(s, 0)), mover_population=int((r1.season == s).sum()),
                               fill_non_keepers=r2[(r2.season == s) & (r2.is_gk == 0)][K].drop_duplicates().shape[0],
                               fill_keepers=r2[(r2.season == s) & (r2.is_gk == 1)][K].drop_duplicates().shape[0]) for s in ALL])
    pop_t.to_csv(C / "populations" / "populations.csv", index=False)
    say("**2. Populations** (movers = player-seasons with a carried slot in a charged call; fills = imports with a fill slot):\n")
    say(md_table(pop_t) + "\n")
    res["populations"] = pop_t.to_dict("records")
    # ---- 3
    rows = D["mrows"][D["mrows"].season.isin(ALL)].copy()
    rows["block"] = np.where(rows.season.isin(TEST), "test", np.where(rows.season.isin(FIT), "fit", "neither"))
    rows.to_csv(C / "movers" / "mover_rows.csv", index=False)
    m = rows[rows.status == "measured"].copy()
    say(f"**3. Mover rows**: {len(rows)} population rows, {len(m)} measured ({', '.join(f'{s[2:4]}/{s[7:9]} {int((m.season == s).sum())}' for s in ALL)}); "
        f"not measured: {int((rows.status.str.startswith('not measured: no carried')).sum())} with no carried slot at the first naming, "
        f"{int((rows.status.str.startswith('not measured: not named')).sum())} not named for the club in the season.\n")
    res["mover_rows"] = dict(population=len(rows), measured=len(m), by_season={s: int((m.season == s).sum()) for s in ALL})
    # ---- 4
    say("**4. Mover constant** (adjusted = carried − delta × (from_seed − to_seed); b = OLS slope of gap on pot delta, delta = −b):\n")
    st, mover = [], {}
    for lab, ss in BLOCKS:
        d = m[m.season.isin(ss)]
        for ic in (False, True):
            o = ols(d, ic)
            st.append(dict(block=lab, seasons=short(ss), model="with intercept" if ic else "through zero", n=o["n"], delta=-o["slope"], SE=o["slope_se"], p=P(o["slope_p"]),
                           grid=grid(-o["slope"]), intercept=o.get("intercept"), intercept_SE=o.get("intercept_se")))
            mover[(lab, ic)] = o
    per = []
    for s in ALL:
        d = m[m.season == s]
        if len(d) > 2:
            o = ols(d, False); per.append(dict(season=s, n=o["n"], delta=-o["slope"], SE=o["slope_se"]))
    st_df = pd.DataFrame(st); st_df.to_csv(C / "movers" / "mover_stats.csv", index=False)
    pd.DataFrame(per).to_csv(C / "movers" / "mover_per_season.csv", index=False)
    say(md_table(st_df, floatfmt={"delta": ".4f", "SE": ".4f", "grid": ".2f", "intercept": ".4f", "intercept_SE": ".4f"}) + "\n")
    say("Per season (through zero): " + "; ".join(f"{r['season'][2:4]}/{r['season'][7:9]} {r['delta']:.3f} ± {r['SE']:.3f} (n {r['n']})" for r in per) + "\n")
    ft = pd.DataFrame(fit_test(m, f"chronological: fit {short(FIT)}, test {short(TEST)}", FIT, TEST)); ft.to_csv(C / "movers" / "mover_fit_test.csv", index=False)
    say("Chronological fit/test (residual = test gap − fitted line; residual slope 0 = the fit's delta holds in the test):\n")
    say(md_table(ft.drop(columns=["split"]), floatfmt={c: ".4f" for c in ft.columns if c not in ("split", "model", "fit_n", "test_n", "resid_slope_p")}) + "\n")
    rr = []
    for k in (0.05, 0.10, 0.15):
        for lab, ss in (("all", ALL), ("fit", FIT), ("test", TEST)):
            d2 = m[m.season.isin(ss)].copy(); d2["resid"] = d2.gap + k * d2.pot_delta; r0 = ols(d2, False, y="resid")
            rr.append(dict(delta_applied=k, seasons=lab, n=len(d2), resid_mean=d2.resid.mean(), resid_mean_SE=se(d2.resid), resid_slope=r0["slope"], SE=r0["slope_se"], p=P(r0["slope_p"])))
    rrd = pd.DataFrame(rr); rrd.to_csv(C / "movers" / "mover_residual_slopes.csv", index=False)
    say("Residual slope with a fixed delta applied (through zero; 0 = nothing left):\n")
    say(md_table(rrd, floatfmt={"delta_applied": ".2f", "resid_mean": ".4f", "resid_mean_SE": ".4f", "resid_slope": ".4f", "SE": ".4f"}) + "\n")
    res["mover"] = dict(stats=st_df.to_dict("records"), per_season=per, fit_test=ft.to_dict("records"), residual_slopes=rrd.to_dict("records"))
    # sideways cell
    z = m[(m.pot_delta == 0)]
    sw, zb = [], {}
    for lab, ss in BLOCKS:
        d = z[z.season.isin(ss)]; zb[lab] = d
        tt = stats.ttest_1samp(d.gap, 0) if len(d) > 1 else None
        sw.append(dict(block=lab, n=len(d), mean_carried=d.carried.mean(), mean_realised=d.realised.mean(), mean_gap=d.gap.mean(), SE=se(d.gap),
                       t=tt.statistic if tt else np.nan, p=P(tt.pvalue) if tt else "", grid=grid(d.gap.mean()) if len(d) else np.nan))
    swd = pd.DataFrame(sw); swd.to_csv(C / "movers" / "sideways_cell.csv", index=False)
    zf, zt = zb["fit"], zb["test"]
    welch = stats.ttest_ind(zf.gap, zt.gap, equal_var=False) if len(zf) > 1 and len(zt) > 1 else None
    resid_c = zt.gap - cur["sideways"]
    say(f"**Sideways (same-pot, pot delta = 0) cell** — mean gap = realised − carried; the rule in force adds {cur['sideways']:+.2f} to carried:\n")
    say(md_table(swd, floatfmt={"mean_carried": ".4f", "mean_realised": ".4f", "mean_gap": ".4f", "SE": ".4f", "t": ".2f", "grid": ".2f"}) + "\n")
    say(f"Chronological: fit-block mean gap {zf.gap.mean():+.4f} ± {se(zf.gap):.4f} (n {len(zf)}, grid {grid(zf.gap.mean()) if len(zf) else float('nan'):.2f}) applied to the test block: "
        f"test mean gap {zt.gap.mean():+.4f} ± {se(zt.gap):.4f} (n {len(zt)}); difference test − fit {zt.gap.mean() - zf.gap.mean():+.4f}, Welch p = {P(welch.pvalue) if welch else 'n/a'}. "
        f"With {cur['sideways']:+.2f} applied the test-block residual is {resid_c.mean():+.4f} ± {se(resid_c):.4f} (one-sample t p = {P(stats.ttest_1samp(resid_c, 0).pvalue) if len(resid_c) > 1 else 'n/a'}).\n")
    res["sideways"] = dict(cell=swd.to_dict("records"), welch_p=welch.pvalue if welch else None, test_residual_mean=resid_c.mean(), test_residual_SE=se(resid_c))
    # ---- 5
    pop = D["trows"][D["trows"].season.isin(ALL)]
    pop.to_csv(C / "tier_fills" / "tier_fill_rows.csv", index=False)
    nk = pop[(pop.is_gk == 0) & (pop.status == "measured")]
    CURF = {"tier1": cur["tier1"], "tier2": cur["tier2"], "tier3": cur["tier3"], "unknown": cur["unknown"], **{g: cur["data_club"] for g in DC_GROUPS}}
    ALLDC = "every data-club origin together"
    tr, fills = [], {}
    for gname in ["tier1", "tier2", "tier3", "unknown"] + DC_GROUPS + [ALLDC]:
        x = nk[nk.group.isin(DC_GROUPS)] if gname == ALLDC else nk[nk.group == gname]
        fills[gname] = x
        if x.empty:
            continue
        xf, xt = x[x.season.isin(FIT)], x[x.season.isin(TEST)]
        tr.append(dict(tier=gname, spec_fill=CURF.get(gname, cur["data_club"]), n=len(x), mean=x.realised.mean(), SE=se(x.realised), median=x.realised.median(), grid=grid(x.realised.mean()),
                       fit_n=len(xf), fit_mean=xf.realised.mean(), fit_SE=se(xf.realised), fit_grid=grid(xf.realised.mean()) if len(xf) else np.nan,
                       test_n=len(xt), test_mean=xt.realised.mean(), test_SE=se(xt.realised)))
    trd = pd.DataFrame(tr); trd.to_csv(C / "tier_fills" / "tier_fills.csv", index=False)
    late = nk[nk.group == "data club, arrival record dated after the fixture"]
    say(f"**5. Tier fills, keepers excluded** (fill population; realised = first 12 squads for the club from the arrival in force; {len(nk)} measured non-keeper player-seasons, "
        f"{int(((pop.is_gk == 0) & (pop.status != 'measured')).sum())} never named after the arrival, keepers {pop[pop.is_gk == 1][K].drop_duplicates().shape[0]}"
        + (f"; {len(late)} data-club rows whose arrival record is dated after the fixture are in no group" if len(late) else "") + "):\n")
    say(md_table(trd, floatfmt={c: ".3f" for c in trd.columns if c not in ("tier", "n", "fit_n", "test_n")} | {"spec_fill": ".2f", "grid": ".2f", "fit_grid": ".2f"}) + "\n")
    # origin league not readable: the arrival is dated in a season for which the input set's teams file has no Championship clubs
    nl = nk[nk.group == "data club in neither league that season"]
    no_ch = [s_ for s_, a_ in zip(nl.season, nl.arrival_used)
             if not any(lg == "Championship" and sn_ == season_of(a_) for (_, sn_), lg in D["ctx_of"][s_].league_in.items())]
    if no_ch:
        say(f"Coverage note: {len(no_ch)} of the {len(nl)} rows in \"data club in neither league that season\" ({', '.join(f'{s_[2:4]}/{s_[7:9]} {no_ch.count(s_)}' for s_ in ALL if s_ in no_ch)}) "
            f"have an arrival dated in a season for which the input set's teams file holds no Championship clubs, so the origin league cannot be read; "
            f"they count in the data-club fill but in neither the PL-origin nor the Championship-origin split.\n")
    res["tier_fills"] = trd.to_dict("records"); res["tier_fills_origin_league_unreadable"] = dict(rows=len(no_ch), of=len(nl), by_season={s_: no_ch.count(s_) for s_ in ALL if s_ in no_ch})
    # ---- 6
    traces = {s: pd.read_csv(Path(run_dir) / tag(s) / f"absence_trace_{tag(s)}{opt(cmds[s], '--out-suffix')}.csv") for s in ALL}
    ctxs = []
    for s in ALL:
        if D["ctx_of"][s] not in ctxs:
            ctxs.append(D["ctx_of"][s])
    spells = pd.concat([spells_of(c, {s: traces[s] for s in ALL if D["ctx_of"][s] is c}) for c in ctxs], ignore_index=True)
    spells["H"] = spells.length.map(bin_of)
    wt = spells.groupby("H").mins.sum().reindex(HS).fillna(0); W = wt / wt.sum()
    ps = D["ps"][D["ps"].season.isin(ALL)]
    ps.to_csv(C / "L_window" / "L_horizon_per_season.csv", index=False)

    def composite(seasons):
        d = ps[ps.season.isin(seasons)].assign(sa=lambda x: x.n * x.MAE).groupby(["H", "L"])[["n", "sa"]].sum()
        t_ = pd.DataFrame(dict(MAE=d.sa / d.n)).reset_index().pivot(index="L", columns="H", values="MAE")
        return sum(t_[H] * W[H] for H in HS)
    comp = pd.DataFrame({s: composite([s]) for s in ALL}); comp.to_csv(C / "L_window" / "L_composite_by_season.csv")
    pooled = {lab: composite(ss) for lab, ss in BLOCKS}
    best = {lab: int(v.idxmin()) for lab, v in pooled.items()}
    pair_list = [(12, 13), (12, 14), (13, 14), (12, 11), (12, 10)] + [(12, b) for b in sorted(set(best.values())) if b not in (10, 11, 12, 13, 14)]
    tests = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for a, b in pair_list:
            for lab, ss in (("all", ALL), ("fit", FIT), ("test", TEST)):
                d = (comp.loc[a, ss] - comp.loc[b, ss]).to_numpy()
                tt = stats.ttest_rel(comp.loc[a, ss].to_numpy(), comp.loc[b, ss].to_numpy()) if len(d) > 1 else None
                try:
                    wp = stats.wilcoxon(d, zero_method="wilcox", alternative="two-sided").pvalue
                except ValueError:
                    wp = np.nan
                tests.append(dict(pair=f"L{a} − L{b}", seasons=lab, n=len(d), mean_d=d.mean(), SD_d=d.std(ddof=1) if len(d) > 1 else np.nan,
                                  t=tt.statistic if tt else np.nan, p_t=tt.pvalue if tt else np.nan, p_wilcoxon=wp))
    td = pd.DataFrame(tests); td.to_csv(C / "L_window" / "L_paired_tests.csv", index=False)
    ct = pd.DataFrame({"L": LS, "fit": [pooled["fit"][x] for x in LS], "test": [pooled["test"][x] for x in LS], "all": [pooled["all"][x] for x in LS]})
    ct.to_csv(C / "L_window" / "L_composite_pooled.csv", index=False)
    t12 = td[td.pair.str.startswith("L12 − ")]
    # headline rule: no other L tested against 12 is significantly better than it (paired t p < 0.05 with mean d > 0)
    beaten = t12[(t12.p_t < 0.05) & (t12.mean_d > 0)]
    tie_block = {lab: beaten[beaten.seasons == lab].empty for lab, _ in BLOCKS}
    tie = beaten.empty
    # the earlier two-sided rule, kept for comparison: no paired t-test of L12 against L13 or L14 reaches p < 0.05 (either direction)
    tie_s = bool((td[td.pair.isin(["L12 − L13", "L12 − L14"])].p_t.dropna() >= 0.05).all())
    say(f"**6. L composite** (bin weights from the run's absence spells in the set's seasons: {len(spells)} spells, {spells.mins.sum():.0f} minutes; weights " +
        ", ".join(f"H{H} {W[H]:.3f}" for H in HS) + f"). Composite MAE by L (pooled): best L fit = **{best['fit']}**, test = **{best['test']}**, all = **{best['all']}**; "
        f"at L = 12: fit {pooled['fit'][12]:.4f}, test {pooled['test'][12]:.4f}, all {pooled['all'][12]:.4f}; at the best L: {pooled['fit'][best['fit']]:.4f} / {pooled['test'][best['test']]:.4f} / {pooled['all'][best['all']]:.4f}.\n")
    say(md_table(ct[ct.L.between(8, 18)], floatfmt={"fit": ".5f", "test": ".5f", "all": ".5f"}) + "\n")
    say("Paired season tests of the composite (d = composite(L_a) − composite(L_b); positive = L_b better; scipy ttest_rel and wilcoxon, two-sided):\n")
    say(md_table(td, floatfmt={"mean_d": ".5f", "SD_d": ".5f", "t": ".3f", "p_t": ".3f", "p_wilcoxon": ".3f"}) + "\n")
    say(f"**L = 12 {'within the tie' if tie else 'NOT within the tie'}**: " +
        ("no L tested against 12 (" + ", ".join(p.replace("L12 − L", "") for p in dict.fromkeys(t12.pair)) + ") is better than it at paired-t p < 0.05 in any block"
         if tie else "better than L12 at paired-t p < 0.05: " + "; ".join(f"{r_.pair.replace('L12 − ', '')} ({r_.seasons}, p {r_.p_t:.3f})" for r_ in beaten.itertuples())) +
        f". By the two-sided rule (no L12-vs-L13/L14 paired t-test below 0.05 in either direction): {'within the tie' if tie_s else 'NOT within the tie'}.\n")
    res["L"] = dict(best=best, composite_at_12={lab: pooled[lab][12] for lab in pooled}, composite_at_best={lab: pooled[lab][best[lab]] for lab in pooled},
                    weights={f"H{H}": W[H] for H in HS}, spells=len(spells), spell_minutes=float(spells.mins.sum()), pooled=ct.to_dict("records"),
                    paired_tests=td.to_dict("records"), L12_within_tie=bool(tie), L12_within_tie_by_block=tie_block, L12_within_tie_0930_rule=tie_s)
    # ---- calibration table: one row per constant x block
    T = []

    def row(constant, block, current, measured, se_, n, note=""):
        ok = se_ is not None and not np.isnan(se_) and se_ > 0 and n > 0
        T.append(dict(constant=constant, block=block, current=current, measured=measured if n > 0 else np.nan, se=se_ if n > 1 else np.nan, n=int(n),
                      nearest_005=grid(measured) if n > 0 and not np.isnan(measured) else np.nan,
                      abs_diff_in_se=abs(measured - current) / se_ if ok else np.nan, note=note))
    for lab, ss in BLOCKS:
        o = mover[(lab, False)]; row("mover", lab, cur["mover"], -o["slope"], o["slope_se"], o["n"], "delta = −slope of gap on pot delta, OLS through zero")
    for lab, ss in BLOCKS:
        o = mover[(lab, True)]; row("mover_with_intercept", lab, cur["mover"], -o["slope"], o["slope_se"], o["n"], f"OLS with intercept {o['intercept']:+.4f} ± {o['intercept_se']:.4f}")
    for lab, ss in BLOCKS:
        d = zb[lab]; row("sideways", lab, cur["sideways"], d.gap.mean(), se(d.gap), len(d), "mean gap in the same-pot cell (pot delta = 0)")
    for cname, gname in (("tier1", "tier1"), ("tier2", "tier2"), ("tier3", "tier3"), ("data_club", ALLDC), ("data_club_PL_origin", "PL origin"),
                         ("data_club_Championship_origin", "Championship origin"), ("data_club_neither_league_origin", "data club in neither league that season"),
                         ("unknown", "unknown")):
        for lab, ss in BLOCKS:
            x = fills[gname]; x = x[x.season.isin(ss)].realised
            row(cname, lab, CURF.get(gname, cur["data_club"]), x.mean() if len(x) else np.nan, se(x), len(x), "mean realised proportion, first 12 squads from the arrival, keepers excluded")
    for r_ in T:
        r_.update({f"p_L12_vs_L{b}": np.nan for b in L_COMPARATORS}, p_L12_vs_best=np.nan, L12_within_tie="")
    for lab, ss in BLOCKS:
        pv = {b: td[(td.pair == f"L12 − L{b}") & (td.seasons == lab)].p_t.iloc[0] for b in L_COMPARATORS}
        pb = np.nan if best[lab] == 12 else td[(td.pair == f"L12 − L{best[lab]}") & (td.seasons == lab)].p_t.iloc[0]
        T.append(dict(constant="L", block=lab, current=cur["L"], measured=best[lab], se=np.nan, n=len(ss), nearest_005=np.nan, abs_diff_in_se=np.nan,
                      note=f"best L of the composite (MAE {pooled[lab][best[lab]]:.5f}; at L = {cur['L']} {pooled[lab][cur['L']]:.5f}); n = seasons; p = paired t of L12 against the other L over seasons",
                      **{f"p_L12_vs_L{b}": pv[b] for b in L_COMPARATORS}, p_L12_vs_best=pb, L12_within_tie="yes" if tie_block[lab] else "no"))
    cols = ["constant", "block", "current", "measured", "se", "n", "nearest_005", "abs_diff_in_se"] + [f"p_L12_vs_L{b}" for b in L_COMPARATORS] + ["p_L12_vs_best", "L12_within_tie", "note"]
    tab = pd.DataFrame(T)[cols]
    tab.to_csv(out / f"calibration_table_{name}.csv", index=False)
    say(f"**Calibration table** — one row per constant × block; current = the value in force in the run's commands; se analytic "
        f"(OLS slope SE, or SD/√n of a mean); nearest_005 = measured rounded to the nearest 0.05; for L: measured = best L, n = seasons, p = paired t of L12 against the other L:\n")
    disp = tab.drop(columns=["note"]).astype(object)
    isL = (tab.constant == "L").to_numpy()
    disp["current"] = [f"{v:.0f}" if l_ else f"{v:.2f}" for v, l_ in zip(tab.current, isL)]
    disp["measured"] = ["" if pd.isna(v) else (f"{v:.0f}" if l_ else f"{v:.4f}") for v, l_ in zip(tab.measured, isL)]
    say(md_table(disp, floatfmt={"se": ".4f", "nearest_005": ".2f", "abs_diff_in_se": ".2f", **{c: ".3f" for c in cols if c.startswith("p_L12")}}) + "\n")
    res["table"] = tab.to_dict("records")
    res["constants"] = {c: {r_["block"]: {k: v for k, v in r_.items() if k not in ("constant", "block")} for r_ in T if r_["constant"] == c} for c in dict.fromkeys(r_["constant"] for r_ in T)}
    (out / f"calibration_{name}.md").write_text("\n".join(md) + "\n")
    res = jsonable(res)
    (out / f"calibration_{name}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    return res


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run-dir", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--set", default="both", choices=["SET7", "SET11", "both"])
    ap.add_argument("--fit", nargs="*", default=None); ap.add_argument("--test", nargs="*", default=None)
    ap.add_argument("--jobs", type=int, default=None)
    ap.add_argument("--skip-instrument", action="store_true", help="reuse the captures already in <out>/inst")
    ap.add_argument("--child", default=None, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    run_dir, out = Path(args.run_dir).resolve(), Path(args.out).resolve()
    if args.child:
        child(args.child, run_dir, out); return None
    log = lambda *a: print(*a, flush=True)
    warnings.filterwarnings("ignore")
    T0 = time.time()
    out.mkdir(parents=True, exist_ok=True)
    cmds = read_runs(run_dir)
    names = ["SET7", "SET11"] if args.set == "both" else [args.set]
    union = [s for s in SET11 if any(s in SETS[n] for n in names)]
    missing = [s for s in union if s not in cmds]
    if missing:
        raise SystemExit(f"STOP: seasons not in {run_dir / 'runs.csv'}: {missing}")
    log(f"calibration re-measure on {run_dir} -> {out}; sets {names}")
    jobs = args.jobs or min(os.cpu_count() or 4, len(union))
    inst_h, inst_s = (None, 0.0) if args.skip_instrument else instrument(run_dir, out, union, cmds, jobs, log)
    D = measure_rows(run_dir, out, union, cmds, log)
    script_sha = sha(__file__)
    results = {}
    for n in names:
        ALL = SETS[n]
        TEST = [s for s in (args.test if args.test is not None else TEST_DEFAULT) if s in ALL]
        FIT = [s for s in (args.fit if args.fit is not None else [s for s in ALL if s not in TEST]) if s in ALL]
        t1 = time.time()
        results[n] = analyse(n, ALL, FIT, TEST, D, run_dir, out, cmds, inst_h, script_sha)
        log(f"  {n}: statistics and report in {time.time() - t1:.0f} s -> {out / f'calibration_{n}.md'}")
    log(f"calibration re-measure done in {time.time() - T0:.0f} s (instrumented pass {inst_s:.0f} s)")
    return results


if __name__ == "__main__":
    main()
