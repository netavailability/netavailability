"""The analysis battery: every statistic reported on the club tables, for two season sets, from one run folder.

  python -m netavailability.analyses.battery --run-dir DIR --out DIR --set SET7|SET11|both [--only main with2021 exwin] [--jobs N]
  import: main(argv=None) -> exit code (0 = no unexpected failure); run_battery(run_dir, out, sets, only, jobs)
  -> dict with the output paths and the headline numbers per set.

Sets: SET7 = 2018/19, 2019/20, 2021/22, 2022/23-2025/26; SET11 = SET7 + 2014/15-2017/18. 2020/21 (played mostly
without crowds) is used only by the `with2021` robustness variant. With --set both the two sets run in parallel into
<out>/SET7/ and <out>/SET11/; inside a set the three variants, and inside a variant the independent steps, run
concurrently (at most --jobs processes).

Run folder (the pipeline's contract, common.py): <run-dir>/runs.csv gives, per season, the --out-suffix of its tables
and its inputs folder (--pulls, --suffix, --meta-suffix): tables <run-dir>/<tag>/<name>_<tag><SFX>.csv; fixtures
<pulls>/fixtures<suffix>.csv; Premier League season ids from <pulls>/teams<meta-suffix>.csv (fallback: the input
league_seasons.csv). Finish and points come from the input standings.csv, squad values (Transfermarkt,
1 July; 2014/15 dated 10 July 2014) from the input club_season_values.csv by (season, team_id).

Variants: main (the set), with2021 (+ 2020/21), exwin (the set with the Omicron window 1 Dec 2021-31 Jan 2022 and the
2019/20 restart 17 Jun-26 Jul 2020 removed from every within-season quantity: per-fixture NET from calibration_ and
NETabsence from absence_trace_ rebuilt into club-season NETavailability and the half-season file). Each variant folder
holds club_seasons.csv (finish, points, NETavailability, NETabsence, rank; `label` = FINAL for 2022/23-2025/26,
ROBUSTNESS for 2020/21, PAPER otherwise) and club_season_values.csv (the same with squad values), then one folder per
step. The steps run as child processes (python -m netavailability.analyses.<module>):
  F    regressions          points / finish ~ squad value, NETavailability; per season and pooled with season FE, HC3
  G    half_season_inputs,  first-half availability -> second-half points (half-season lag models)
       half_season_models
  H    persistence          op1-op5: ICC, split-half, permutation, lag-1 regression to the mean, the money question
  H2   carryover_null       op1-op3: the persistence statistics against a carry-over-only (AR(1)) null
  H3   asymmetry            op1-op4: shape, stickiness of deficits, two-season deficit runs
  H3b  two_season_runs      op1-op5: the sum rule for two-season runs, value quintiles, points context
  L    extremity            op1-op4: how unusual Tottenham's availability is, two scales, two chance models
  N    power                power and the 95% upper bound for a lasting club edge
Seasons are indexed by start year minus the set's first start year, so 2019/20 -> 2021/22 is a two-year gap. Several
steps carry self-checks whose targets are recomputed from the run's own inputs (selfcheck.py); a failing check exits 1
and is reported as an unexpected failure. The checks are counted under copy_known_value_checks (key name kept).
Own arithmetic here (on statistics the steps computed): the inputs, the ex-window rebuild, the points decomposition on
fixed_effects.ols_fe (expected = fitted with c = 0; availability part = beta_c*c; other = residual; squad-value
equivalent = exp(beta_c*c/beta_value) x the club's 1 July value; the same pool without Tottenham and Chelsea), the
headline extraction, the robustness-rows table and the two charts.

headline_<SET>.json, per variant (keys under variants.<variant>):
  F_pools / F        pooled regression (points ~ value + NETavailability + season FE, HC3) by pool: FINAL4
                     (2022/23-2025/26), paper_no2021, all; F = the all-seasons row next to the same model by
                     fixed_effects.ols_fe; F_noTC = without Tottenham Hotspur and Chelsea
  decomposition      the points decomposition per pool (paper = all seasons of the variant, FINAL4)
  G_pools / G        half-season models (b) second-half points ~ value + first-half absence per match, (c) + first-half
                     points; G_input_fails = the half-season input checks that failed
  H                  ICC (all clubs, clubs with six or more seasons), split-half r, permutation p, lag-1 slope
  H2                 share of carry-over-only panels at or above each observed persistence statistic; flags
  H3                 Tottenham- and Chelsea-depth two-season run shares; stickiness slope difference
  H3b                sum-rule Tottenham / Chelsea depth shares
  L                  extremity shares and verdicts T1-T4
  N                  the 95% upper bound and the minimum detectable edge
  copy_known_value_checks, unexpected_failures, extraction_errors

Outputs per set, <out>/<SET>/: battery_<SET>.md, headline_<SET>.json, robustness_rows_<SET>.csv,
decomposition_named_<SET>.csv, decomposition_all_club_seasons_<SET>.csv, decomposition_summary_<SET>.csv,
script_runs_<SET>.csv, chart_netav_by_rank_per_season_<SET>.png, chart_league_mean_trend_<SET>.png,
league_mean_by_season_<SET>.csv, <variant>/{inputs, <step folders>, logs/}. Nothing is written outside --out.
"""
import argparse, hashlib, json, os, shutil, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd

from .. import common, settings
from . import fixed_effects

SET7 = ["2018/2019", "2019/2020", "2021/2022", "2022/2023", "2023/2024", "2024/2025", "2025/2026"]
EARLY4 = ["2014/2015", "2015/2016", "2016/2017", "2017/2018"]
SETS = {"SET7": SET7, "SET11": EARLY4 + SET7}
ROBUST = "2020/2021"
FINAL4 = ["2022/2023", "2023/2024", "2024/2025", "2025/2026"]
WINDOWS = [("Omicron", "2021-12-01", "2022-01-31"), ("restart 2019/20", "2020-06-17", "2020-07-26")]
NAMED = [("Tottenham Hotspur", "2024/2025"), ("Tottenham Hotspur", "2025/2026"), ("Chelsea", "2022/2023"), ("Chelsea", "2023/2024"),
         ("Nottingham Forest", "2024/2025"), ("Wolverhampton Wanderers", "2018/2019")]
NAMED_EARLY = [("Leicester City", "2015/2016"), ("Sunderland", "2016/2017")]
DROP = ["Tottenham Hotspur", "Chelsea"]
VARIANTS = ["main", "with2021", "exwin"]
TABLES = ["club_table", "club_split_january", "calibration", "absence_trace"]
MARKER = ".analysis_variant"
MODULES = {"F": "regressions", "G1": "half_season_inputs", "G23": "half_season_models", "H": "persistence", "H2": "carryover_null",
           "H3": "asymmetry", "H3b": "two_season_runs", "L": "extremity", "N": "power"}
DIRS = {"F": "regressions", "G": "half_season", "H": "persistence", "H2": "carryover_null", "H3": "asymmetry",
        "H3b": "two_season_runs", "L": "extremity", "N": "power"}
OPS = {"H": ["op1", "op2", "op3", "op4", "op5"], "H2": ["op1", "op2", "op3"], "H3": ["op1", "op2", "op3", "op4"],
       "H3b": ["op1", "op2", "op3", "op4", "op5"], "L": ["op1", "op2", "op3", "op4"]}
_PRINT = threading.Lock()


def tag(s):
    return s.replace("/", "-")


def short(s):
    return f"{s[2:4]}/{s[7:9]}"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


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


def par(*fns):
    """Run callables concurrently (threads; the work is in subprocesses) and return their results; re-raises."""
    if len(fns) == 1:
        return [fns[0]()]
    with ThreadPoolExecutor(len(fns)) as ex:
        futs = [ex.submit(f) for f in fns]
        return [f.result() for f in futs]


def clean(o):
    """JSON-safe: numpy scalars -> python, NaN -> None."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.bool_, bool)):
        return bool(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        return None if (np.isnan(o) or np.isinf(o)) else float(o)
    if isinstance(o, Path):
        return str(o)
    return o


# ---------------------------------------------------------------- run folder
class Run:
    """The run folder: per season the table suffix, the inputs folder and the PL season id."""

    def __init__(self, run_dir):
        self.dir = Path(run_dir).resolve()
        runs = pd.read_csv(self.dir / "runs.csv")
        self.info = {}
        for r in runs.itertuples():
            c = json.loads(r.command)
            arg = lambda k, d=None: c[c.index(k) + 1] if k in c else d
            self.info[r.season] = dict(input_set=str(getattr(r, "input_set", "")), rc=int(r.rc), pulls=Path(arg("--pulls")), sfx=arg("--suffix", ""),
                                       msfx=arg("--meta-suffix", ""), out_sfx=arg("--out-suffix"))
        self._teams, self._fx, self._league = {}, {}, None
        self.values = pd.read_csv(settings.inp("club_season_values"))

    def table_path(self, name, s):
        return self.dir / tag(s) / f"{name}_{tag(s)}{self.info[s]['out_sfx']}.csv"

    def table(self, name, s, **kw):
        return pd.read_csv(self.table_path(name, s), **kw)

    def fixtures_path(self, s):
        i = self.info[s]
        return i["pulls"] / f"fixtures{i['sfx']}.csv"

    def fixtures(self, s):
        p = self.fixtures_path(s)
        if p not in self._fx:
            d = pd.read_csv(p, parse_dates=["date"])
            self._fx[p] = d[d.league_id == 8].drop_duplicates("fixture_id")
        return self._fx[p]

    def season_id(self, s):
        i = self.info[s]
        p = i["pulls"] / f"teams{i['msfx']}.csv"
        if p.exists():
            if p not in self._teams:
                self._teams[p] = pd.read_csv(p)
            t = self._teams[p]
            t = t[(t.league == "Premier League") & (t.season == s)]
            if len(t) and t.season_id.nunique() == 1:
                return int(t.season_id.iloc[0]), f"teams{i['msfx']}.csv"
        if self._league is None:
            lp = settings.inp("league_seasons")
            self._league = {r.season: int(r.season_id) for r in pd.read_csv(lp).itertuples()} if lp.exists() else {}
        if s in self._league:
            return self._league[s], "league_seasons.csv"
        return None, None

    def standings(self, s):
        sid, _ = self.season_id(s)
        st = pd.read_csv(settings.inp("standings"))
        st = st[st.season_id == sid]
        return sid, {int(t): (int(p), int(q)) for t, p, q in zip(st.team_id, st.position, st.points)}

    def preflight(self, s):
        """Everything the battery needs for one season; returns the list of what is missing (empty = complete)."""
        miss = []
        if s not in self.info:
            return [f"{s}: no row in runs.csv"]
        if self.info[s]["rc"] != 0:
            miss.append(f"{s}: compute rc {self.info[s]['rc']} in runs.csv")
        for name in TABLES:
            if not self.table_path(name, s).exists():
                miss.append(f"{s}: table {self.table_path(name, s).relative_to(self.dir)} not in the run folder")
        if not self.fixtures_path(s).exists():
            miss.append(f"{s}: fixtures file {self.fixtures_path(s)} not found")
        sid, src = self.season_id(s)
        if sid is None:
            miss.append(f"{s}: no Premier League season id in the inputs teams file or league_seasons.csv")
        elif not (pd.read_csv(settings.inp("standings")).season_id == sid).any():
            miss.append(f"{s}: no standings rows for season id {sid} in standings.csv")
        if miss:
            return miss
        ct = self.table("club_table", s)
        _, fin = self.standings(s)
        if sorted(p for p, _ in fin.values()) != list(range(1, 21)):
            miss.append(f"{s}: standings.csv does not hold positions 1-20 for season id {sid}")
        no_st = sorted(set(ct.team_id) - set(fin))
        if no_st:
            miss.append(f"{s}: no standings row for team_id {no_st}")
        v = self.values[self.values.season == s]
        no_v = ct[~ct.team_id.isin(v.team_id[v.log_value_rel.notna()])]
        if len(no_v):
            miss.append(f"{s}: no squad value in club_season_values.csv for " + ", ".join(f"{c} ({t})" for c, t in zip(no_v.Club, no_v.team_id)))
        if len(ct) != 20:
            miss.append(f"{s}: club table has {len(ct)} rows, not 20")
        return miss


# ---------------------------------------------------------------- inputs
def in_window(d):
    return np.zeros(len(d), bool) | np.any([(d >= a) & (d <= b) for _, a, b in WINDOWS], axis=0)


def build_inputs(run, seasons, out, exwin=False):
    """club_seasons.csv and club_season_values.csv from the run; exwin: per-fixture rebuild with the windows removed."""
    rows, removed = [], {}
    for s in seasons:
        t = tag(s)
        ct = run.table("club_table", s)
        sid, fin = run.standings(s)
        if exwin:
            cal = run.table("calibration", s, parse_dates=["date"]); trc = run.table("absence_trace", s, parse_dates=["date"])
            removed[s] = int(in_window(cal.date).sum())
            cal = cal[~in_window(cal.date)]; trc = trc[~in_window(trc.date)]
            net = pd.concat([cal[["home_id", "home_sum_xU"]].rename(columns={"home_id": "team_id", "home_sum_xU": "x"}),
                             cal[["away_id", "away_sum_xU"]].rename(columns={"away_id": "team_id", "away_sum_xU": "x"})]).groupby("team_id").x.sum() * 90
            ab = trc.groupby("team_id").minutes.sum()
            games = pd.concat([cal.home_id, cal.away_id]).value_counts()
        for r in ct.itertuples():
            tid = int(r.team_id)
            if exwin:
                n_, a_ = float(net.get(tid, 0.0)), float(ab.get(tid, 0.0))
                netav, netabs, g = n_ / (n_ + a_), a_, int(games.get(tid, 0))
            else:
                netav, netabs, g = float(r.NETavailability), float(r.NETabsence), int(r.Games)
            rows.append(dict(season=s, club=r.Club, team_id=tid, finish=fin[tid][0], points=fin[tid][1], NETavailability=round(netav, 4), NETabsence=int(round(netabs)),
                             games=g, label="ROBUSTNESS" if s == ROBUST else ("FINAL" if s in FINAL4 else "PAPER"),
                             club_table_file=f"{t}/club_table_{t}{run.info[s]['out_sfx']}.csv", standings_season_id=sid))
    d = pd.DataFrame(rows)
    d["NETavailability_rank"] = d.groupby("season").NETavailability.rank(ascending=False, method="first").astype(int)
    d = d[["season", "club", "team_id", "finish", "points", "NETavailability", "NETabsence", "NETavailability_rank", "label", "club_table_file", "standings_season_id", "games"]]
    v = d.merge(run.values[["season", "team_id", "tm_id", "squad_value_eur", "squad_value_text", "value_date", "value_flag", "value_source", "log_value_rel"]], on=["season", "team_id"], how="left")
    assert v.log_value_rel.notna().all(), "squad value missing"
    if out is not None:
        d.to_csv(out / "club_seasons.csv", index=False)
        v.to_csv(out / "club_season_values.csv", index=False)
    return d, v, removed


def build_half_season_exwin(run, seasons, out, vals):
    """Half-season file in half_season_models' columns from per-fixture data with the windows removed."""
    rows = []
    for s in seasons:
        sid, _ = run.season_id(s)
        sp = run.table("club_split_january", s); wc = pd.Timestamp(sp.winter_close.iloc[0])
        cal = run.table("calibration", s, parse_dates=["date"]); trc = run.table("absence_trace", s, parse_dates=["date"])
        fx = run.fixtures(s)
        f = fx[fx.season_id == sid].copy(); f["date"] = f.date.dt.normalize(); f = f[~in_window(f.date)]
        trc = trc[~in_window(trc.date)]; cal = cal[~in_window(cal.date)]
        for r in vals[vals.season == s].itertuples():
            c = int(r.team_id)
            m = f[(f.home_id == c) | (f.away_id == c)].copy(); home = m.home_id == c
            gf = m.home_goals.where(home, m.away_goals); ga = m.away_goals.where(home, m.home_goals)
            m["pts"] = (gf > ga) * 3 + (gf == ga) * 1; pre = m.date < wc
            ta = trc[trc.team_id == c]; pre_a = ta.date < wc
            rows.append(dict(season=s, club=r.club, team_id=c, label=r.label, winter_close=wc.date().isoformat(), fixtures=len(m), g_H1=int(pre.sum()), g_H2=int((~pre).sum()),
                             pts_H1=int(m.pts[pre].sum()), pts_H2=int(m.pts[~pre].sum()), pts_rebuilt=int(m.pts.sum()), pts_official=int(r.points), deduction=0,
                             NETabs_H1=int(round(ta.minutes[pre_a].sum())), NETabs_H2=int(round(ta.minutes[~pre_a].sum())),
                             NETabs_pm_H1=ta.minutes[pre_a].sum() / max(int(pre.sum()), 1), NETabs_pm_H2=ta.minutes[~pre_a].sum() / max(int((~pre).sum()), 1),
                             finish=r.finish, NETavailability=r.NETavailability, NETabsence=r.NETabsence, log_value_rel=r.log_value_rel, squad_value_eur=r.squad_value_eur,
                             value_date=r.value_date, value_flag=r.value_flag))
    d = pd.DataFrame(rows)
    (out / DIRS["G"]).mkdir(exist_ok=True)
    d.to_csv(out / DIRS["G"] / "half_season.csv", index=False)
    return d


# ---------------------------------------------------------------- decomposition (own arithmetic on fixed_effects.ols_fe)
def decomposition(v, fe, pool_name, seasons):
    d = v[v.season.isin(seasons)].reset_index(drop=True).copy()
    d["c"] = d.NETavailability - d.groupby("season").NETavailability.transform("mean")
    full = fe.ols_fe(d.points, d[["log_value_rel", "c"]], d.season)
    base = fe.ols_fe(d.points, d[["log_value_rel"]], d.season)
    bv, bc = float(full["beta"][0]), float(full["beta"][1])
    d["availability_part"] = bc * d.c
    d["expected_c0"] = full["fitted"] - d.availability_part
    d["other"] = full["resid"]
    d["equiv_dlog_value"] = d.availability_part / bv
    d["equiv_value_multiple"] = np.exp(d.equiv_dlog_value)
    d["equiv_value_eur"] = d.squad_value_eur * (d.equiv_value_multiple - 1)
    d["pool"] = pool_name
    nd = d[~d.club.isin(DROP)].reset_index(drop=True)
    nfull = fe.ols_fe(nd.points, nd[["log_value_rel", "c"]], nd.season); nbase = fe.ols_fe(nd.points, nd[["log_value_rel"]], nd.season)
    summ = dict(pool=pool_name, n=int(full["n"]), beta_value=bv, se_value=float(full["se"][0]), beta_c=bc, se_c=float(full["se"][1]), p_c=float(full["p"][1]),
                r2=float(full["r2"]), dR2=float(full["r2"] - base["r2"]), pts_per_pp=bc / 100, within_sd_c=float(d.c.std(ddof=1)), pts_per_sd=bc * float(d.c.std(ddof=1)),
                value_equiv_of_1sd=float(np.exp(bc * d.c.std(ddof=1) / bv)),
                n_noTC=int(nfull["n"]), beta_c_noTC=float(nfull["beta"][1]), se_c_noTC=float(nfull["se"][1]), p_c_noTC=float(nfull["p"][1]), dR2_noTC=float(nfull["r2"] - nbase["r2"]))
    return d, summ


# ---------------------------------------------------------------- charts (ramp stretched to the season count)
def charts(v, B, SET):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    INK, MUTED, GRID = "#1f1f1e", "#6b6a64", "#e4e3dc"
    rc = {"font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "axes.spines.top": False, "axes.spines.right": False}
    allS = sorted(v.season.unique())
    base = ["#a9c7ec", "#83aee2", "#5d93d6", "#3a78c8", "#2560b0", "#164a92", "#0b3570", "#041f4a"]   # one hue, light -> dark = earlier -> later
    cm = LinearSegmentedColormap.from_list("seasons", base)
    ramp = base if len(allS) <= 8 else [matplotlib.colors.to_hex(cm(i / (len(allS) - 1))) for i in range(len(allS))]
    sfx = ""
    with plt.rc_context(rc):
        fig, ax = plt.subplots(figsize=(9, 5.2))
        for i, s in enumerate(allS):
            d = v[v.season == s].sort_values("NETavailability_rank")
            rob = s == ROBUST
            ax.plot(d.NETavailability_rank, d.NETavailability, color=(MUTED if rob else ramp[min(i, len(ramp) - 1)]), lw=1.6 if rob else 2, ls="--" if rob else "-", marker="o", ms=3.5,
                    label=short(s) + (" (excluded, robustness only)" if rob else ""))
        ax.set_xlabel("Rank by NETavailability within season (1 = highest)", color=MUTED); ax.set_ylabel("NETavailability", color=MUTED)
        ax.set_xticks(range(1, 21)); ax.set_xlim(0.5, 20.5)   # no end labels (they collide at rank 20); the legend carries identity; ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
        ax.set_title(f"NETavailability by rank, each season ({SET}){sfx}", loc="left", color=INK)
        ax.legend(frameon=False, fontsize=8, loc="lower left", ncol=1 if len(allS) <= 8 else 2); fig.tight_layout()
        fig.savefig(B / f"chart_netav_by_rank_per_season_{SET}.png", dpi=160); plt.close(fig)
        g = v.groupby("season").agg(mean_netav=("NETavailability", "mean"), sd=("NETavailability", "std"), mean_abs_pm=("NETabsence", lambda x: x.mean() / 38)).reindex(allS)
        fig, ax = plt.subplots(figsize=(8 if len(allS) <= 8 else 10, 4.2))
        x = np.arange(len(allS)); y = g.mean_netav.values
        ax.plot(x, y, color=base[5], lw=2, marker="o", ms=6)
        for i, s in enumerate(allS):
            if s == ROBUST:
                ax.plot(x[i], y[i], marker="o", ms=9, mfc="white", mec=MUTED, mew=1.5); ax.annotate("2020/21 excluded\n(closed doors)", (x[i], y[i]), (0, -34), textcoords="offset points", ha="center", fontsize=8, color=MUTED)
            dip = 0 < i < len(y) - 1 and y[i] < y[i - 1] and y[i] < y[i + 1] and s != ROBUST   # a local minimum: label below, clear of the line
            ax.annotate(f"{y[i]:.3f}", (x[i], y[i]), (0, -15 if dip else 8), textcoords="offset points", ha="center", fontsize=8, color=INK)
        ax.set_xticks(x); ax.set_xticklabels([short(s) for s in allS]); ax.set_ylabel("League mean NETavailability", color=MUTED)
        pad = (y.max() - y.min()) * 0.35 or 0.01
        ax.set_ylim(y.min() - pad * 1.6, y.max() + pad)
        ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True); ax.set_title(f"League-mean NETavailability by season ({SET}){sfx}", loc="left", color=INK)
        fig.tight_layout(); fig.savefig(B / f"chart_league_mean_trend_{SET}.png", dpi=160); plt.close(fig)
    g.reset_index().to_csv(B / f"league_mean_by_season_{SET}.csv", index=False)
    return g


# ---------------------------------------------------------------- one set
class SetRun:
    def __init__(self, run, SET, seasons, B, only, sem, log, missing):
        self.run, self.SET, self.seasons, self.B, self.only, self.sem, self.log = run, SET, seasons, B, only, sem, log
        self.missing = missing
        self.steps, self.var = [], {}
        self.fe = fixed_effects
        n = len(seasons)
        y0, y1 = seasons[0], seasons[-1]
        pre = [s for s in seasons if s < ROBUST]; post = [s for s in seasons if s > ROBUST]
        span = lambda ss: (f"{ss[0][:4]}/{ss[0][7:9]}" + (f"–{ss[-1][:4]}/{ss[-1][7:9]}" if len(ss) > 1 else "")) if ss else ""
        # SET7 keeps its original pool labels
        self.label_F = "paper 7 (2018/19, 2019/20, 2021/22–2025/26)" if seasons == SET7 else f"paper {n} ({', '.join(x for x in (span(pre), span(post)) if x)})"
        self.label_G = f"paper {n} (no 2020/21)"

    # ---- one step as a child process
    def step(self, var, name, script, args, env, out):
        with self.sem:
            t0 = time.time()
            r = subprocess.run(common.module_cmd(f"analyses.{script}", *args), capture_output=True, text=True, env=env, cwd=out)
            dt = time.time() - t0
        (out / "logs").mkdir(exist_ok=True)
        (out / "logs" / f"{name}.txt").write_text(r.stdout + ("\nSTDERR\n" + r.stderr if r.stderr else ""))
        tb = "Traceback (most recent call last)" in r.stderr
        last = [l for l in r.stderr.strip().splitlines() if l.strip()][-1][:300] if tb else ""
        self.steps.append(dict(set=self.SET, variant=var, step=name, script=script, rc=r.returncode, seconds=round(dt, 1), traceback=tb, error=last))
        self.log(f"  [{self.SET}/{var}] {name}: rc {r.returncode} in {dt:.0f} s" + (" — TRACEBACK" if tb else ""))
        return r.returncode

    def variant(self, var):
        run = self.run
        exwin = var == "exwin"
        seasons = sorted(self.seasons + [ROBUST]) if var == "with2021" else list(self.seasons)
        out = self.B / var
        if out.exists():
            if not (out / MARKER).exists():
                raise SystemExit(f"{out} exists and was not written by this battery; not overwritten")
            shutil.rmtree(out)
        out.mkdir(parents=True); (out / MARKER).write_text(datetime.now().isoformat())
        t0 = time.time()
        d, v, removed = build_inputs(run, seasons, out, exwin=exwin)
        (out / DIRS["F"]).mkdir(); shutil.copy(out / "club_season_values.csv", out / DIRS["F"] / "club_season_values.csv")
        sf = {s: dict(split=str(run.table_path("club_split_january", s)), fixtures=str(run.fixtures_path(s))) for s in seasons}
        (out / "season_files.json").write_text(json.dumps(sf, indent=1))
        env = common.child_env(NETAV_ANALYSIS_DIR=out, PYTHONDONTWRITEBYTECODE="1", NETAV_SEASON_FILES=out / "season_files.json",
                               NETAV_POOL_LABEL_REGRESSIONS=self.label_F, NETAV_POOL_LABEL_HALF_SEASON=self.label_G)
        for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "MKL_NUM_THREADS"):
            env.setdefault(k, "1")   # one BLAS thread per script process: the battery runs many at once (results unchanged)
        info = dict(seasons=seasons, exwin=exwin, n=len(d), value_dates=sorted(v.value_date.unique()), removed=removed)
        for x in ("G", "H", "H2", "H3", "H3b", "L", "N"):
            if not (exwin and x != "G"):
                (out / DIRS[x]).mkdir(exist_ok=True)

        def chain(key):
            for op in OPS[key]:
                self.step(var, f"{key}_{op}", MODULES[key], [op], env, out)

        def F():
            self.step(var, "F_regressions", MODULES["F"], [], dict(env, NETAV_ANALYSIS_DIR=str(out / DIRS["F"])), out)

        def G():
            if exwin:
                h = build_half_season_exwin(run, seasons, out, v)
                info["exwin_fixtures_kept"] = (int(h.fixtures.min()), int(h.fixtures.max()))
            else:
                self.step(var, "G_half_season_inputs", MODULES["G1"], [], env, out)
            self.step(var, "G_half_season_models", MODULES["G23"], [], env, out)

        def Hfam():
            self.step(var, "H_op1", MODULES["H"], ["op1"], env, out)   # writes the panel every later step reads
            def rest_H():
                for op in OPS["H"][1:]:
                    self.step(var, f"H_{op}", MODULES["H"], [op], env, out)
            def H2_then():
                chain("H2")
                par(lambda: (chain("H3"), chain("H3b")), lambda: self.step(var, "N_main", MODULES["N"], [], env, out))
            par(rest_H, H2_then)

        if exwin:
            par(F, G)
        else:
            par(F, G, Hfam, lambda: chain("L"))
        # ---- decomposition (own arithmetic)
        decos, summs = [], []
        for pool_name, ss in (("paper", seasons), ("FINAL4", [s for s in seasons if s in FINAL4])):
            dd, sm = decomposition(v, self.fe, f"{var}:{pool_name}", ss)
            dd.to_csv(out / f"decomposition_{pool_name}.csv", index=False); summs.append(sm); decos.append(dd)
        info.update(decos=decos, summs=summs, seconds=time.time() - t0)
        self.var[var] = info
        return info

    # ---- headline extraction (reads the steps' CSVs; never recomputes a statistic)
    def headline(self, var):
        out = self.B / var; info = self.var[var]; H = dict(seasons=info["seasons"], n_club_seasons=info["n"]); err = {}

        def grab(key, fn):
            try:
                H[key] = fn()
            except Exception as e:   # a missing or malformed output of a step: reported, never fatal
                H[key] = None; err[key] = f"{type(e).__name__}: {e}"

        def pool_rows(df):
            return {("FINAL4" if p.startswith("FINAL") else "all" if p.startswith("all") else "paper_no2021"): g for p, g in df.groupby("pool", sort=False)}

        def f_():
            po = pd.read_csv(out / DIRS["F"] / "pooled.csv"); po = po[po.y == "points"]
            res = {}
            for k, g in pool_rows(po).items():
                r = g.iloc[0]
                res[k] = dict(pool=r.pool, n=int(r.n), coef=r.c_netav_coef, se_hc3=r.c_netav_se_hc3, p_hc3=r.c_netav_p_hc3, dR2=r.dR2, dR2_F_p=r.dR2_F_p,
                              value_coef=r.c_lv_coef, value_se_hc3=r.c_lv_se_hc3, R2_value_only=r.a_R2, R2_with_netav=r.c_R2, std_beta=r.c_netav_beta)
            return res
        grab("F_pools", f_)
        sm = {s["pool"].split(":")[1]: s for s in info["summs"]}
        H["decomposition"] = {k: {x: s[x] for x in s if x != "pool"} for k, s in sm.items()}
        p = sm["paper"]
        H["F_noTC"] = dict(source="fixed_effects.ols_fe on the variant's seasons without Tottenham Hotspur and Chelsea", n=p["n_noTC"], coef=p["beta_c_noTC"], se_hc3=p["se_c_noTC"], p_t=p["p_c_noTC"], dR2=p["dR2_noTC"])
        if H.get("F_pools"):
            a = H["F_pools"]["all"]
            H["F"] = dict(source="regressions pooled, all seasons of the variant: points ~ squad value + NETavailability + season FE, HC3", n=a["n"], coef=a["coef"], se_hc3=a["se_hc3"], p_hc3=a["p_hc3"],
                          p_t_fe_lib=p["p_c"], dR2=a["dR2"], fe_lib_coef=p["beta_c"], fe_lib_se=p["se_c"],
                          agrees_with_fe_lib=bool(abs(a["coef"] - p["beta_c"]) < 1e-6 and abs(a["se_hc3"] - p["se_c"]) < 1e-6 and a["n"] == p["n"]))
        else:
            H["F"] = None

        def g_():
            g = pd.read_csv(out / DIRS["G"] / "tests.csv"); res = {}
            for k, gg in pool_rows(g).items():
                res[k] = {r.model: dict(pool=r.pool, n=int(r.n), coef=r.coef, se_hc3=r.se_hc3, p_hc3=r.p_hc3, dR2=r.dR2, F_p=r.F_p, boot_lo=r.boot_lo, boot_hi=r.boot_hi) for r in gg.itertuples()}
            return res
        grab("G_pools", g_)
        H["G"] = dict(H["G_pools"]["all"], source="half_season_models tests, all seasons of the variant: second-half points ~ value + first-half absence per match (b), + first-half points (c); HC3") if H.get("G_pools") else None
        chk = out / DIRS["G"] / "input_checks.json"
        if chk.exists():
            H["G_input_fails"] = json.load(open(chk)).get("fails", [])
        if not info["exwin"]:
            def h_():
                h = out / DIRS["H"]
                icc = pd.read_csv(h / "op2a_icc.csv"); sh = pd.read_csv(h / "op2b_split_half.csv")
                pm = pd.read_csv(h / "op2c_permutation.csv"); rm = pd.read_csv(h / "op2d_regression_to_mean.csv")
                return dict(icc_all=icc.ICC[0], icc_all_ci=[icc.ci_lo[0], icc.ci_hi[0]], icc_all_obs=int(icc.obs[0]), icc_all_clubs=int(icc.clubs[0]),
                            icc_ge6=icc.ICC[1], icc_ge6_ci=[icc.ci_lo[1], icc.ci_hi[1]], icc_ge6_clubs=int(icc.clubs[1]),
                            split_half_odd_even_r=sh.pearson[0], split_half_odd_even_n=int(sh.n[0]), split_half_halves_r=sh.pearson[1], split_half_halves_n=int(sh.n[1]),
                            permutation_p=pm.p[0], lag1_slope=rm.slope[0], lag1_se_ols=rm.se_ols[0], lag1_se_cluster=rm.se_cluster[0], lag1_n_pairs=int(rm.n[0]), sd_c=rm.sd_c[0])
            grab("H", h_)

            def h2_():
                t = pd.read_csv(out / DIRS["H2"] / "op3_null_summary.csv"); ci = pd.read_csv(out / DIRS["H2"] / "op2_corrected_intervals.csv")
                k = ["icc_all", "icc_ge6", "permutation", "split_half", "flags_uncorrected", "flags_corrected"]
                c1 = pd.read_csv(out / DIRS["H2"] / "op1_checks.csv")
                return dict(shares_ge_obs={a: t.share_ge_obs[i] for i, a in enumerate(k)}, observed={a: t.observed[i] for i, a in enumerate(k)},
                            corrected_flags=int(ci.flag_adj.notna().sum()), uncorrected_flags=int(ci.flag_raw.notna().sum()), clubs_ge6=len(ci), lag1_pearson_rho=c1.lag1_pearson_rho[0])
            grab("H2", h2_)

            def h3_():
                nm = pd.read_csv(out / DIRS["H3"] / "op4_named_runs.csv"); st = pd.read_csv(out / DIRS["H3"] / "op3_slope_diff_tests.csv")
                return dict(tottenham_depth_share=nm.share_panels_any[0], chelsea_depth_share=nm.share_panels_any[1],
                            stickiness_slope_diff=st.slope_diff_lower_minus_upper[0], stickiness_p_cluster=st.p_cluster[0], stickiness_null_share=st.null_share_ge_obs[0], stickiness_n=int(st.n[0]))
            grab("H3", h3_)

            def h3b_():
                t = pd.read_csv(out / DIRS["H3b"] / "op2_null.csv"); t = t[(t.rule == "sum of the two seasons") & (t.side == "deficit")].reset_index(drop=True)
                return dict(sum_rule_tottenham_share=t.share_panels_any[0], sum_rule_chelsea_share=t.share_panels_any[1], expectation_0_3_to_0_7_met=bool(0.3 <= t.share_panels_any[0] <= 0.7))
            grab("H3b", h3b_)

            def l_():
                lv = pd.read_csv(out / DIRS["L"] / "op4_verdict.csv")
                rows = [dict(test=r["test"], run=r["run"], cN=r["c·N"], cQ=r["c·Q"], mN=r["m·N"], mQ=r["m·Q"], headline_share=r["headline_share"], headline_config=r["headline_config"],
                             verdict=r["verdict"]) for r in lv.to_dict("records")]
                key = [("T1", "Tottenham 2025/26"), ("T2", "Tottenham 2024/25–2025/26"), ("T3", "Tottenham 2024/25–2025/26"), ("T4", "Tottenham 2025/26 gap to 19th")]
                hs = {t: next(r["headline_share"] for r in rows if r["test"] == t and r["run"] == rn) for t, rn in key}
                hv = {t: next(r["verdict"] for r in rows if r["test"] == t and r["run"] == rn) for t, rn in key}
                return dict(shares_T1_T4=hs, verdicts_T1_T4=hv, verdict="NOT SHOWN RARE" if all(x == "NOT SHOWN RARE" for x in hv.values()) else "; ".join(f"{t} {x}" for t, x in hv.items()), rows=rows)
            grab("L", l_)

            def n_():
                nh = pd.read_csv(out / DIRS["N"] / "headline.csv")
                row = lambda q, s: nh[(nh.quantity == q) & (nh.statistic == s)].iloc[0]
                ub, mde, anyb = row("95% upper bound", "ICC-all"), row("MDE at 80% power", "ICC-all"), row("MDE at 80% power", "any (Bonferroni)")
                pw = pd.read_csv(out / DIRS["N"] / "power_by_share.csv")
                return dict(upper_bound_95_icc_all_pp=ub.sigma_u_pp, upper_bound_95_icc_all_s=ub.s, upper_bound_pts_at_92=ub.pts_92, upper_bound_pts_at_82_5=ub.pts_82_5,
                            mde80_icc_all_pp=mde.sigma_u_pp, mde80_any_bonferroni_pp=anyb.sigma_u_pp, max_power_icc_all_s_le_0_30=float(pw.power_icc_all.max()),
                            max_power_any_bonferroni=float(pw.power_any_bonf.max()), headline_file=f"{var}/{DIRS['N']}/headline.csv", rows=nh.to_dict("records"))
            grab("N", n_)
        # the steps' self-checks (targets recomputed from the run's own inputs): counted; a failing step is an unexpected failure
        chk = {}
        for key in ("H", "H2", "H3", "H3b", "L", "N"):
            f_csv = out / DIRS[key] / ("checks.csv" if key == "N" else "op1_checks.csv")
            if not f_csv.exists():
                continue
            c = pd.read_csv(f_csv)
            col = "result" if "result" in c.columns else ("checks" if "checks" in c.columns else None)
            chk[key] = dict(fail=int(c[col].astype(str).str.contains("FAIL").sum()) if col else None, of=len(c))
        H["copy_known_value_checks"] = chk
        steps = [s for s in self.steps if s["variant"] == var]
        H["unexpected_failures"] = [dict(step=s["step"], rc=s["rc"], error=s["error"]) for s in steps if s["traceback"] or s["rc"] != 0]
        H["extraction_errors"] = err
        return H


# ---------------------------------------------------------------- report text
def pm(x, se, d=3):
    return f"{x:.{d}f} ± {se:.{d}f}".replace("-", "−")


def robustness_rows(heads):
    """The robustness rows in one place: one row per analysis, a column per variant."""
    def cell(var, fn):
        h = heads.get(var)
        if h is None:
            return "not run"
        try:
            return fn(h)
        except Exception:
            return "n/a (season totals)" if var == "exwin" else "not available"
    rows = [
        ("F: NETavailability coefficient, points ~ value + NETav, season FE, HC3 (pooled)", lambda h: f"{pm(h['F']['coef'], h['F']['se_hc3'], 1)} (n {h['F']['n']}, ΔR² {h['F']['dR2']:.3f})"),
        ("F without Spurs and Chelsea", lambda h: f"{pm(h['F_noTC']['coef'], h['F_noTC']['se_hc3'], 1)} (p {h['F_noTC']['p_t']:.4f}, n {h['F_noTC']['n']})"),
        ("G model (b): H2 points ~ value + H1 absence per match (pooled)", lambda h: f"{pm(h['G']['b']['coef'], h['G']['b']['se_hc3'])} (p {h['G']['b']['p_hc3']:.3f}, ΔR² {h['G']['b']['dR2']:.3f})"),
        ("G model (c) (+ H1 points)", lambda h: f"{pm(h['G']['c']['coef'], h['G']['c']['se_hc3'])} (p {h['G']['c']['p_hc3']:.3f})"),
        ("H: ICC all clubs [bootstrap 95%]", lambda h: f"{h['H']['icc_all']:.3f} [{h['H']['icc_all_ci'][0]:.3f}, {h['H']['icc_all_ci'][1]:.3f}]"),
        ("H: lag-1 slope (pairs)", lambda h: f"{pm(h['H']['lag1_slope'], h['H']['lag1_se_ols'])} (n {h['H']['lag1_n_pairs']})"),
        ("H2: share of null panels ≥ observed ICC-all / permutation / split-half", lambda h: " / ".join(f"{h['H2']['shares_ge_obs'][k]:.3f}" for k in ("icc_all", "permutation", "split_half"))),
        ("H3: Tottenham-depth run share; stickiness diff (p)", lambda h: f"{h['H3']['tottenham_depth_share']:.3f}; {h['H3']['stickiness_slope_diff']:+.2f} ({h['H3']['stickiness_p_cluster']:.2f})"),
        ("H3b: sum-rule Tottenham-depth share", lambda h: f"{h['H3b']['sum_rule_tottenham_share']:.3f}"),
        ("L: headline shares T1–T4 (largest of c·N, c·Q, m·N, m·Q)", lambda h: " / ".join(f"{h['L']['shares_T1_T4'][t]:.2f}" for t in ("T1", "T2", "T3", "T4")) + f" — {h['L']['verdict']}"),
        ("N: 95% upper bound on a lasting edge (ICC-all)", lambda h: f"{h['N']['upper_bound_95_icc_all_pp']:.2f} pp" if h['N']['upper_bound_95_icc_all_pp'] is not None and not pd.isna(h['N']['upper_bound_95_icc_all_pp']) else "not reached on s ≤ 0.30"),
        ("Decomposition β_c (pts per unit c), FINAL 4 / all seasons of the variant", lambda h: f"{pm(h['decomposition']['FINAL4']['beta_c'], h['decomposition']['FINAL4']['se_c'], 1)} / {pm(h['decomposition']['paper']['beta_c'], h['decomposition']['paper']['se_c'], 1)}"),
    ]
    return pd.DataFrame([dict(analysis=name, **{v: cell(v, fn) for v in VARIANTS}) for name, fn in rows])


GAP_ROWS = [
    ("F (regressions)", "season totals; season FE", "no lag structure; unaffected",
     "each earlier season enters with its own season dummy and its own per-season regression; pools: FINAL (2022/23 on), paper (every season but 2020/21), all seasons in the file"),
    ("G (half_season_inputs / half_season_models)", "within-season halves", "no cross-season lag; unaffected",
     "split file from the run folder and fixtures from the season's own inputs folder (input set early for 2014/15–2016/17, mid for 2017/18); winter close per season from the split file; its points check has deductions for 2023/24 only (none apply 2014/15–2017/18)"),
    ("H (persistence)", "lag-1 pairs via s_idx, parity split via s_idx % 2", "s_idx by start year: 2019/20 and 2021/22 are NOT a pair; odd/even split = odd/even start year. Its op1 check (c) alone lists 2019/20→2021/22 as an adjacent pair (a self-check table, not used by any statistic)",
     "s_idx = start year − 2014, so pairs run 2014/15→…→2019/20 and 2021/22→…; parity is unchanged (2014 and 2018 are both even); the chronological split halves the 11 listed seasons (6 + 5); op5 (ii) '2018/19–2025/26 only' selects by start year ≥ 2018"),
    ("H2 (carryover_null)", "lag-1 ρ from pairs; AR(1) null over S seasons", "pairs exclude the gap; the simulated AR(1) keeps an empty 2020/21 column, so 2019/20 → 2021/22 correlates at ρ²",
     "S = last start year − first + 1 = 12 columns from 2014/15 (8 from 2018/19 in SET7), all clubs of the set"),
    ("H3 / H3b (asymmetry / two_season_runs)", "H2's pairs and null", "as H2; a two-season run cannot span 2019/20–2021/22",
     "thresholds are the named runs' observed c values (Tottenham 2024/25–2025/26, Chelsea 2022/23–2023/24); the null's ρ and SD are the set's own, so the earlier seasons change them and add pairs and simulated columns; FINAL-80 sub-sample = label FINAL (2022/23 on)"),
    ("L (extremity)", "own pairs and AR(1) panels", "s_idx by start year; empty 2020/21 column in the panels; season gaps computed over observed seasons only",
     "as H2; T4's gap ranks are over the set's observed seasons; A_pm = NETabsence ÷ 38 in every season"),
    ("N (power)", "H2's pairs/null", "as H2", "as H2"),
    ("decomposition", "season totals", "unaffected", "pooled with season FE over the set; Leicester 2015/16 and Sunderland 2016/17 added to the named club-seasons (SET11 only)"),
]


def write_set(sr, heads, t_set):
    """Report, CSVs and headline JSON of one set (serial; after every subprocess has finished)."""
    B, SET, run = sr.B, sr.SET, sr.run
    md = []
    say = md.append
    say(f"# Analysis battery — {SET}\n")
    if sr.missing:
        say(f"**INCOMPLETE {SET}: " + "; ".join(sr.missing) + f". The set was built on the remaining seasons ({', '.join(short(s) for s in sr.seasons)}).**\n")
    say(f"Battery run {datetime.now():%Y-%m-%d %H:%M}. Run folder `{run.dir}` "
        f"(table suffix {', '.join(sorted({run.info[s]['out_sfx'] for s in sr.seasons}))}). Seasons {', '.join(short(s) for s in sr.seasons)} "
        f"(input sets: {', '.join(f'{k} {v}' for k, v in pd.Series([run.info[s]['input_set'] for s in sr.seasons]).value_counts(sort=False).items())}); robustness season {short(ROBUST)}. "
        f"Squad values: `club_season_values.csv` by (season, team_id); points and finish: standings.csv. Outputs in `{B}/`.\n")
    say("Steps run: " + ", ".join(f"`{v}`" for v in MODULES.values()) + "; `fixed_effects`.\n")
    steps = pd.DataFrame(sr.steps)
    for var in [v for v in VARIANTS if v in heads]:
        info, h, out = sr.var[var], heads[var], B / var
        say(f"\n## Variant `{var}` — seasons {', '.join(short(s) for s in info['seasons'])}{' — Omicron and restart windows removed from within-season data' if info['exwin'] else ''}\n")
        say(f"Inputs: {info['n']} club-seasons, {len(info['seasons'])} seasons; squad values dated {', '.join(info['value_dates'])}." +
            (f" Fixtures removed by the windows: {', '.join(f'{short(s)} {n}' for s, n in info['removed'].items() if n)}; fixtures kept per club-season {info['exwin_fixtures_kept'][0]}–{info['exwin_fixtures_kept'][1]}." if info["exwin"] and "exwin_fixtures_kept" in info else "") + "\n")
        st = steps[steps.variant == var]
        say("Steps: " + "; ".join(f"{r.step} rc {r.rc} {r.seconds:.0f} s" for r in st.sort_values("step").itertuples()) + ".\n")
        if h["unexpected_failures"]:
            say("**UNEXPECTED FAILURES: " + "; ".join(f"{x['step']} rc {x['rc']} {x['error']}" for x in h["unexpected_failures"]) + "**\n")
        if h["extraction_errors"]:
            say("**Headline not extracted: " + "; ".join(f"{k} ({v})" for k, v in h["extraction_errors"].items()) + "**\n")
        if h.get("G_input_fails"):
            say(f"**G input checks FAILED ({len(h['G_input_fails'])}): " + "; ".join(h["G_input_fails"][:12]) + (" …" if len(h["G_input_fails"]) > 12 else "") + " — the G rows of this variant are not valid until resolved.**\n")
        p = out / DIRS["F"] / "pooled.csv"
        if p.exists():
            po = pd.read_csv(p)
            cols = [c for c in ("pool", "n", "a_R2", "c_R2", "dR2", "dR2_F_p", "c_lv_coef", "c_lv_se_hc3", "c_netav_coef", "c_netav_se_hc3", "c_netav_p_hc3", "c_netav_beta") if c in po.columns]
            say("**F** (`regressions`): pooled models with season FE, HC3 — (a) points ~ value, (c) points ~ value + NETavailability:\n")
            say(md_table(po[po.y == "points"][cols], floatfmt={c: ".3f" for c in cols if c not in ("pool", "n")} | {"dR2": ".4f", "dR2_F_p": ".4f", "c_netav_p_hc3": ".4f"}) + "\n")
            if h.get("F"):
                say(f"Same model by `fixed_effects.ols_fe` (decomposition): {h['F']['fe_lib_coef']:.3f} ± {h['F']['fe_lib_se']:.3f} — {'agrees' if h['F']['agrees_with_fe_lib'] else '**DISAGREES**'} with the 'all seasons in the file' row. "
                    f"Without Tottenham and Chelsea: {h['F_noTC']['coef']:.3f} ± {h['F_noTC']['se_hc3']:.3f} (n {h['F_noTC']['n']}, p {h['F_noTC']['p_t']:.4f}, ΔR² {h['F_noTC']['dR2']:.4f}).\n")
        p = out / DIRS["G"] / "tests.csv"
        if p.exists():
            g = pd.read_csv(p)
            say("**G** (`half_season_models`): second-half points ~ value + first-half absence per match (b), + first-half points (c); HC3:\n")
            say(md_table(g[["pool", "model", "n", "coef", "se_hc3", "p_hc3", "dR2", "F_p", "boot_lo", "boot_hi"]], floatfmt={"coef": ".3f", "se_hc3": ".3f", "p_hc3": ".3f", "dR2": ".4f", "F_p": ".3f", "boot_lo": ".3f", "boot_hi": ".3f"}) + "\n")
        if not info["exwin"]:
            x = h.get("H")
            if x:
                say(f"**H** (`persistence`): ICC all clubs {x['icc_all']:.3f} [{x['icc_all_ci'][0]:.3f}, {x['icc_all_ci'][1]:.3f}] (n obs {x['icc_all_obs']}, {x['icc_all_clubs']} clubs), clubs ≥6 seasons {x['icc_ge6']:.3f} [{x['icc_ge6_ci'][0]:.3f}, {x['icc_ge6_ci'][1]:.3f}]; "
                    f"split-half odd/even r {x['split_half_odd_even_r']:.3f} (n {x['split_half_odd_even_n']}), halves r {x['split_half_halves_r']:.3f} (n {x['split_half_halves_n']}); permutation p {x['permutation_p']:.4f}; "
                    f"lag-1 slope {x['lag1_slope']:.3f} (SE {x['lag1_se_ols']:.3f}, n {x['lag1_n_pairs']} consecutive-season pairs).\n")
            x = h.get("H2")
            if x:
                say("**H2** (`carryover_null`): carry-over-only null (ρ " + f"{x['lag1_pearson_rho']:.4f}) — " + "; ".join(f"{k} obs {x['observed'][k]:.4g} share≥obs {x['shares_ge_obs'][k]:.3f}" for k in x["observed"]) +
                    f"; corrected flags {x['corrected_flags']} of {x['clubs_ge6']}.\n")
            x = h.get("H3")
            if x:
                say(f"**H3** (`asymmetry`): Tottenham-depth two-season run share of null panels {x['tottenham_depth_share']:.4f}, Chelsea-depth {x['chelsea_depth_share']:.4f}; "
                    f"stickiness slope difference (lower − upper) {x['stickiness_slope_diff']:+.3f} (p {x['stickiness_p_cluster']:.3f}, null share {x['stickiness_null_share']:.3f}).\n")
            x = h.get("H3b")
            if x:
                say(f"**H3b** (`two_season_runs`): sum rule, Tottenham depth: share of simulated leagues with a pair as deep = {x['sum_rule_tottenham_share']:.4f} (Chelsea depth {x['sum_rule_chelsea_share']:.4f}); "
                    f"expectation 0.3–0.7: {'MET' if x['expectation_0_3_to_0_7_met'] else 'NOT MET'}.\n")
            if h.get("L"):
                say("**L** (`extremity`):\n\n" + md_table(pd.read_csv(out / DIRS["L"] / "op4_verdict.csv")) + "\n")
            x = h.get("N")
            if x:
                fmt = lambda v, u="": "not reached on s ≤ 0.30" if v is None or pd.isna(v) else f"{v:.2f}{u}"
                say(f"**N** (`power`; `{x['headline_file']}`): 95% upper bound on a lasting club edge from ICC-all σ_u = {fmt(x['upper_bound_95_icc_all_pp'], ' pp')} "
                    f"(≈ {fmt(x['upper_bound_pts_at_92'])} points a season at 92 per unit, {fmt(x['upper_bound_pts_at_82_5'])} at 82.5); MDE at 80% power: ICC-all {fmt(x['mde80_icc_all_pp'], ' pp')}, "
                    f"any-of-three {fmt(x['mde80_any_bonferroni_pp'], ' pp')} (max power on s ≤ 0.30: ICC-all {x['max_power_icc_all_s_le_0_30']:.3f}, any-of-three {x['max_power_any_bonferroni']:.3f}).\n\n" +
                    md_table(pd.DataFrame(x["rows"]), default=".3f") + "\n")
            ck = h["copy_known_value_checks"]
            if ck:
                say("Self-checks of the steps (targets recomputed from this run's inputs): " + "; ".join(f"{k}: {v['fail']} FAIL of {v['of']}" for k, v in ck.items()) + ".\n")
    # ---- decomposition tables
    S = pd.DataFrame([s for v in VARIANTS if v in sr.var for s in sr.var[v]["summs"]]); S.to_csv(B / f"decomposition_summary_{SET}.csv", index=False)
    say("\n## Points decomposition — points ~ log_value_rel + c + C(season), HC3 (fixed_effects.ols_fe); c = NETavailability − season mean\n")
    say(md_table(S, floatfmt={c: ".3f" for c in S.columns if c not in ("pool", "n", "n_noTC")} | {"p_c": ".4f", "p_c_noTC": ".4f", "dR2": ".4f", "dR2_noTC": ".4f", "pts_per_pp": ".3f"}) + "\n")
    say("`<variant>:paper` = all seasons of the variant, `<variant>:FINAL4` = 2022/23–2025/26. `beta_c` = points per unit of c (÷100 = points per percentage point of NETavailability); `pts_per_sd` = β_c × within-season SD of c; "
        "`value_equiv_of_1sd` = the squad-value multiple that buys the same points (exp(β_c·SD/β_value)); `_noTC` = the same pool without Tottenham Hotspur and Chelsea.\n")
    D = pd.concat([d for v in VARIANTS if v in sr.var for d in sr.var[v]["decos"]], ignore_index=True); D.to_csv(B / f"decomposition_all_club_seasons_{SET}.csv", index=False)
    named_keys = NAMED + (NAMED_EARLY if SET == "SET11" else [])
    named = D[[(c, s) in named_keys for c, s in zip(D.club, D.season)]].sort_values(["pool", "club", "season"])
    cols = ["pool", "season", "club", "points", "expected_c0", "availability_part", "other", "c", "NETavailability", "NETavailability_rank", "squad_value_eur", "squad_value_text", "equiv_dlog_value", "equiv_value_multiple", "equiv_value_eur"]
    nm = named[cols].copy(); nm["equiv_value_EURm"] = (nm.equiv_value_eur / 1e6).round(1)
    nm.to_csv(B / f"decomposition_named_{SET}.csv", index=False)
    absent = [f"{c} {short(s)}" for c, s in named_keys if s in sr.seasons and not ((D.club == c) & (D.season == s)).any()]
    say("Named club-seasons (expected = fitted with c = 0; availability part = β_c·c; other = residual; squad-value equivalent = multiple of the club's 1 July value with the same points effect, and its € amount):\n")
    show = nm[["pool", "season", "club", "points", "expected_c0", "availability_part", "other", "c", "NETavailability_rank", "squad_value_text", "equiv_value_multiple", "equiv_value_EURm"]]
    say(md_table(show, floatfmt={"expected_c0": ".1f", "availability_part": ".1f", "other": ".1f", "c": ".4f", "equiv_value_multiple": ".3f", "equiv_value_EURm": ".1f"}) + "\n")
    if absent:
        say("**Named club-seasons not found in the club tables: " + ", ".join(absent) + ".**\n")
    # ---- robustness rows
    R = robustness_rows(heads); R.to_csv(B / f"robustness_rows_{SET}.csv", index=False)
    say("\n## Robustness rows in one place\n")
    say(md_table(R.rename(columns={"main": f"main ({SET})", "with2021": "+ 2020/21", "exwin": "ex-window (Omicron, restart)"})) + "\n")
    # ---- gap / earlier seasons
    say("## How each step treats the two-year gap 2019/20 → 2021/22" + (" and the seasons before 2018/19" if SET == "SET11" else "") + "\n")
    gt = pd.DataFrame([dict(script=a, uses=b, gap=c, **({"seasons before 2018/19": d} if SET == "SET11" else {})) for a, b, c, d in GAP_ROWS])
    say(md_table(gt) + "\n")
    if (B / f"league_mean_by_season_{SET}.csv").exists():
        g = pd.read_csv(B / f"league_mean_by_season_{SET}.csv")
        say(f"Charts: `chart_netav_by_rank_per_season_{SET}.png`, `chart_league_mean_trend_{SET}.png`. League-mean NETavailability by season: " + ", ".join(f"{short(s)} {x:.4f}" for s, x in zip(g.season, g.mean_netav)) + ".\n")
    steps.sort_values(["variant", "step"]).to_csv(B / f"script_runs_{SET}.csv", index=False)
    unexpected = [dict(variant=v, **x) for v, h in heads.items() for x in h["unexpected_failures"]] + [dict(variant=v, step=f"extract {k}", rc=None, error=e) for v, h in heads.items() for k, e in h["extraction_errors"].items()]
    say(f"\n{SET} done in {t_set:.0f} s wall ({steps.seconds.sum():.0f} s of script time). Unexpected failures: {len(unexpected)}.")
    (B / f"battery_{SET}.md").write_text("\n".join(md) + "\n")
    head = dict(set=SET, label="FINAL", generated=datetime.now().isoformat(timespec="seconds"), script="netavailability.analyses.battery", script_sha256=sha(__file__),
                run_dir=run.dir, seasons=sr.seasons, robust_season=ROBUST, complete=not sr.missing, missing=sr.missing, windows_excluded_in_exwin=WINDOWS,
                named_club_seasons=[f"{c} {s}" for c, s in named_keys], seconds_wall=round(t_set, 1), unexpected_failures=unexpected, variants=heads,
                named_decomposition=nm.to_dict("records"))
    (B / f"headline_{SET}.json").write_text(json.dumps(clean(head), indent=1, ensure_ascii=False) + "\n")
    return head, unexpected


# ---------------------------------------------------------------- driver
def run_battery(run_dir, out, sets=("SET7", "SET11"), only=tuple(VARIANTS), jobs=None, log=None):
    """Runs the battery; returns dict(rc, seconds, sets={SET: dict(dir, headline, unexpected, missing)})."""
    T0 = time.time()
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    def _log(s=""):
        with _PRINT:
            print(s, flush=True)
    log = log or _log
    run = Run(run_dir)
    sem = threading.BoundedSemaphore(max(1, int(jobs or os.cpu_count() or 4)))
    only = [v for v in VARIANTS if v in only]
    result = dict(rc=0, sets={})
    miss7 = [m for s in SET7 for m in run.preflight(s)]
    if miss7:
        raise SystemExit("STOP: the run folder is incomplete for the seven paper seasons: " + "; ".join(miss7))
    miss_rob = run.preflight(ROBUST)
    plans = []
    for SET in sets:
        seasons, missing = [], []
        for s in SETS[SET]:
            m = run.preflight(s)
            (missing.extend(m) if m else seasons.append(s))
        B = out / SET; B.mkdir(exist_ok=True)
        variants = list(only)
        if miss_rob and "with2021" in variants:
            variants.remove("with2021"); missing.append("with2021 not run — " + "; ".join(miss_rob))
        if SET == "SET11" and seasons == SET7:
            (B / f"battery_{SET}.md").write_text(f"# Analysis battery — {SET}" + "\n\n**NOT BUILT: none of 2014/15–2017/18 is complete — " + "; ".join(missing) + ".**\n")
            (B / f"headline_{SET}.json").write_text(json.dumps(clean(dict(set=SET, complete=False, built=False, missing=missing)), indent=1) + "\n")
            log(f"{SET}: NOT BUILT — " + "; ".join(missing)); result["rc"] = 1
            result["sets"][SET] = dict(dir=B, headline=None, unexpected=[], missing=missing)
            continue
        if missing:
            log(f"{SET}: INCOMPLETE — " + "; ".join(missing)); result["rc"] = 1
        plans.append((SET, SetRun(run, SET, seasons, B, variants, sem, log, missing), variants))

    def do_set(plan):
        SET, sr, variants = plan
        t0 = time.time()
        log(f"{SET}: {len(sr.seasons)} seasons, variants {', '.join(variants)}")
        par(*[(lambda v=v: sr.variant(v)) for v in variants])
        return time.time() - t0

    times = par(*[(lambda p=p: do_set(p)) for p in plans]) if plans else []
    for (SET, sr, variants), t_set in zip(plans, times):
        heads = {v: sr.headline(v) for v in variants}
        try:   # charts: all seasons of the set plus the robustness season, from the run's club tables (serial; matplotlib)
            _, v_all, _ = build_inputs(run, sorted(sr.seasons + ([] if miss_rob else [ROBUST])), None)
            charts(v_all, sr.B, SET)
        except Exception as e:
            log(f"{SET}: charts failed ({type(e).__name__}: {e})"); result["rc"] = 1
        head, unexpected = write_set(sr, heads, t_set)
        if unexpected:
            result["rc"] = 1
            log(f"{SET}: UNEXPECTED FAILURES: " + "; ".join(f"{u['variant']}/{u['step']} {u['error']}" for u in unexpected))
        result["sets"][SET] = dict(dir=sr.B, headline=head, unexpected=unexpected, missing=sr.missing)
        log(f"{SET}: written {sr.B / f'battery_{SET}.md'} ({t_set:.0f} s)")
    result["seconds"] = time.time() - T0
    log(f"Battery done in {result['seconds']:.0f} s; rc {result['rc']}.")
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--run-dir", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--set", default="both", choices=["SET7", "SET11", "both"])
    ap.add_argument("--only", nargs="*", default=VARIANTS, choices=VARIANTS)
    ap.add_argument("--jobs", type=int, default=None, help="most concurrent script processes (default: CPU count)")
    args = ap.parse_args(argv)
    sets = ["SET7", "SET11"] if args.set == "both" else [args.set]
    return run_battery(args.run_dir, args.out, sets=sets, only=args.only, jobs=args.jobs)["rc"]


if __name__ == "__main__":
    sys.exit(main())
