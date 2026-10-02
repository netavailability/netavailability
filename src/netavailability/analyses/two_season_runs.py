"""Two-season deficit runs: the sum-rule sensitivity of the asymmetry step's run test, whether rich clubs are spared
deep deficits, and the points context.

  op1  self-checks against the run's own inputs (rows for the configured seasons, pairs, SD and the named clubs' c
       recomputed from club_seasons.csv, the asymmetry step's share; a failure exits 1), and the sha256 of the
       read-only inputs
  op2  every consecutive-season club pair ranked by its two-season sum of c; the share of carry-over-only panels with
       a pair as deep as the Tottenham and Chelsea runs under three depth rules (sum, most negative season, milder
       season), with the surplus mirror
  op3  are the clubs with the highest squad values spared deep deficits: value quintiles of the seasons at or below
       -1 / -1.5 SD (chi-square with Monte Carlo p, exact multinomial p, binomial and mean-rank tests)
  op4  points context for the named runs (points of 4th, 5th, 17th, 18th; points associated with c at the run's
       points-per-unit coefficient: points ~ log squad value + c + season FE over all seasons of the variant, HC3,
       as the battery's points decomposition, with its 95% interval)
  op5  verdict text; re-check of the inputs' sha256
The null is the carry-over step's `simulate` (imported), 5,000 panels, fixed seed.
Reads persistence/op1_panel.csv, asymmetry/op4_named_runs.csv, club_seasons.csv and club_season_values.csv in
NETAV_ANALYSIS_DIR; writes its CSVs and report.md in two_season_runs/.
Run as: python -m netavailability.analyses.two_season_runs op1|op2|op3|op4|op5
"""
import hashlib
import itertools
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

import os
from . import carryover_null as carry
from . import fixed_effects as fe
from . import selfcheck
BASE = Path(os.environ["NETAV_ANALYSIS_DIR"])
PANEL = BASE / "persistence" / "op1_panel.csv"
CARRY_SCRIPT = Path(carry.__file__)
NAMED_RUNS = BASE / "asymmetry" / "op4_named_runs.csv"
FINISH = BASE / "club_seasons.csv"
VALUES = BASE / "club_season_values.csv"
OUT = BASE / "two_season_runs"
REPORT = OUT / "report.md"
SEED = 20260930
NSIM = 5000
NDRAW = 10000
TOT, CHE = "Tottenham Hotspur", "Chelsea"
TOT_S, CHE_S = ("2024/2025", "2025/2026"), ("2022/2023", "2023/2024")
FINAL = ["2022/2023", "2023/2024", "2024/2025", "2025/2026"]
EPS = 1e-12
# read-only inputs whose sha256 op1 records and op5 re-checks (label, path); the points coefficient is estimated from
# club_season_values.csv
READ_ONLY = [("persistence/op1_panel.csv", PANEL), ("carryover_null.py", CARRY_SCRIPT), ("asymmetry/op4_named_runs.csv", NAMED_RUNS),
             ("club_seasons.csv", FINISH), ("club_season_values.csv", VALUES)]

LINES = []


def out(s=""):
    print(s)
    LINES.append(s)


md_table = carry.md_table


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load():
    m = pd.read_csv(PANEL)
    return m, sorted(m.season.unique())


def pairs_idx(m):
    """Row indices (cur, prev) for the same club in consecutive seasons (as the asymmetry step)."""
    pos = {(ti, s): k for k, (ti, s) in enumerate(zip(m.team_id, m.s_idx))}
    pr = [(k, pos[(ti, s - 1)]) for k, (ti, s) in enumerate(zip(m.team_id, m.s_idx)) if (ti, s - 1) in pos]
    return np.array([p[0] for p in pr]), np.array([p[1] for p in pr])


def rho_sd(m):
    cur, prv = pairs_idx(m)
    return stats.pearsonr(m.c.values[cur], m.c.values[prv])[0], m.c.std(ddof=1)


def club_val(m, club, season):
    return float(m.loc[(m.club == club) & (m.season == season), "c"].iloc[0])


def sims(m):
    rho, sd = rho_sd(m)
    return carry.simulate(m, rho, sd, nsim=NSIM, seed=SEED)


def short(s):
    return f"{s[:4]}/{s[-2:]}"


def points_coef():
    """Points per unit of c from this run: points ~ log_value_rel + c + season FE, HC3, over all seasons of the variant
    (fixed_effects.ols_fe, the battery's points decomposition, pool `paper`); returns (coef, lo, hi, seasons) with the
    95% interval coef ± t(0.975, residual df) · SE."""
    v = pd.read_csv(VALUES)
    v["c"] = v.NETavailability - v.groupby("season").NETavailability.transform("mean")
    f = fe.ols_fe(v.points, v[["log_value_rel", "c"]], v.season)
    b, se = float(f["beta"][1]), float(f["se"][1])
    q = stats.t.ppf(0.975, f["df_resid"])
    return b, b - q * se, b + q * se, v.season.nunique()


# ---------------------------------------------------------------- ops
def op1(m, seasons):
    out("## 1. Provenance and checks\n")
    out(f"Run {datetime.now():%Y-%m-%d %H:%M}.\n")
    out("Inputs (read-only; SHA-256 recorded in `op1_checks.csv` and re-checked in step 5):\n")
    for lab, p in READ_ONLY:
        out(f"- `{lab}` — sha256 {sha(p)[:16] + '…' if p is not None else 'not recorded'}")
    out("\nThe carry-over-only null is the carry-over step's `simulate`, imported, with the same "
        f"ρ and SD the asymmetry step used, {NSIM:,} panels, seed {SEED}.\n")
    out("Pre-registered expectation (written before the first run): under the sum rule a run at least as deep as "
        "Tottenham's still appears in a large share of simulated leagues (of the order of 0.3–0.7). A share below "
        "0.05 is a FINDING.\n")
    rows = []

    def chk(name, value, target, tol, ok=None):
        ok = (abs(value - target) <= tol) if ok is None else ok
        rows.append(dict(check=name, value=value, target=target, tol=tol, result="PASS" if ok else "FAIL"))

    # targets recomputed from this run's club_seasons.csv and configured seasons (selfcheck)
    R = selfcheck.reference()
    tol = selfcheck.TOL
    rho, sd = rho_sd(m)
    chk("rows", len(m), R["rows"], 0)
    chk("SD of c (ddof 1)", sd, R["sd_c"], tol)
    for club, ss in ((TOT, TOT_S), (CHE, CHE_S)):
        for s in ss:
            chk(f"{club} c {short(s)}", club_val(m, club, s), float(R["c"][(club, s)]), tol)
    cur, prv = pairs_idx(m)
    chk("consecutive club-season pairs", len(cur), R["pairs"], 0)
    # reproduce the asymmetry step's op4: Tottenham milder-season rule share
    Y = sims(m)
    tthr = max(club_val(m, TOT, s) for s in TOT_S)
    share = (((Y[:, cur] <= tthr + EPS) & (Y[:, prv] <= tthr + EPS)).sum(1) >= 1).mean()
    h3 = float(pd.read_csv(NAMED_RUNS).share_panels_any.iloc[0])
    chk("Tottenham milder-season share (asymmetry step's op4_named_runs.csv)", share, h3, 0.0, ok=(share == h3))
    # value file consistency with panel
    v = pd.read_csv(VALUES)
    j = m.merge(v[["season", "team_id", "log_value_rel"]], on=["season", "team_id"], suffixes=("", "_v"))
    dv = float(np.abs(j.log_value_rel - j.log_value_rel_v).max())
    chk("club_season_values rows matched to panel (season, team_id)", len(j), R["rows"], 0)
    chk("max |log_value_rel values file − panel|", dv, 0.0, 1e-9)
    f = pd.read_csv(FINISH)
    jf = m.merge(f[["season", "team_id", "points", "finish"]], on=["season", "team_id"], suffixes=("", "_f"))
    chk("club_seasons rows matched; points and finish equal panel", len(jf), R["rows"], 0,
        ok=len(jf) == R["rows"] and (jf.points == jf.points_f).all() and (jf.finish == jf.finish_f).all())
    t = pd.DataFrame(rows)
    t["sha256"] = ""
    t = pd.concat([t, pd.DataFrame([dict(check=f"sha256 {lab}", value=np.nan, target=np.nan,
                                         tol=np.nan, result="RECORDED", sha256=sha(p) if p is not None else "") for lab, p in READ_ONLY])],
                  ignore_index=True)
    t.to_csv(OUT / "op1_checks.csv", index=False)
    out(md_table(t[t.result != "RECORDED"].drop(columns="sha256"), "{:.4f}"))
    out(f"\nImported null: ρ = {rho:.4f}, SD = {sd:.5f}; Tottenham milder-season share = {share:.4f} "
        f"(asymmetry step's file {h3:.4f}) — identical.\n")
    fails = t[t.result == "FAIL"].check.tolist()
    out(f"**step 1: {'ALL CHECKS PASS' if not fails else 'FAIL: ' + '; '.join(fails)}.**\n")
    return f"{len(rows)} checks, {len(fails)} fail; SD {sd:.5f}; THFC milder share {share:.4f}", fails


def op2(m, seasons):
    out("## 2. The sum rule\n")
    rho, sd = rho_sd(m)
    cur, prv = pairs_idx(m)
    obs = m.c.values
    S_obs = obs[cur] + obs[prv]
    P = pd.DataFrame(dict(club=m.club.values[cur], seasons=[f"{short(m.season[b])}–{short(m.season[a])}" for a, b in zip(cur, prv)],
                          c_first=obs[prv], c_second=obs[cur], sum_c=S_obs, sum_in_sd=S_obs / sd,
                          label_second=m.label.values[cur]))
    P = P.sort_values("sum_c").reset_index(drop=True)
    P.insert(0, "rank", np.arange(1, len(P) + 1))
    P.to_csv(OUT / "op2_pairs_ranked.csv", index=False)
    tkey, ckey = (TOT, "2024/25–2025/26"), (CHE, "2022/23–2023/24")
    pos = {k: int(P.loc[(P.club == k[0]) & (P.seasons == k[1]), "rank"].iloc[0]) for k in (tkey, ckey)}
    out(f"All {len(P)} club-pairs of consecutive seasons, ranked by the two-season sum of c (most negative first). "
        f"SD of c = {sd:.5f}. Top ten:\n")
    out(md_table(P.head(10), "{:.4f}"))
    out(f"\nTottenham Hotspur 2024/25–2025/26: rank **{pos[tkey]}** of {len(P)} (sum "
        f"{P.loc[P['rank'] == pos[tkey], 'sum_c'].iloc[0]:.4f}). Chelsea 2022/23–2023/24: rank **{pos[ckey]}** "
        f"(sum {P.loc[P['rank'] == pos[ckey], 'sum_c'].iloc[0]:.4f}). Full ranking in `op2_pairs_ranked.csv`.\n")
    Y = sims(m)
    Ys = Y[:, cur] + Y[:, prv]
    Ymin = np.minimum(Y[:, cur], Y[:, prv]); Ymax = np.maximum(Y[:, cur], Y[:, prv])
    Ymild = np.maximum(Y[:, cur], Y[:, prv]); Ymild_s = np.minimum(Y[:, cur], Y[:, prv])
    omin = np.minimum(obs[cur], obs[prv]); omax = np.maximum(obs[cur], obs[prv])
    rows = []
    for club, ss in ((TOT, TOT_S), (CHE, CHE_S)):
        v = [club_val(m, club, s) for s in ss]
        run = f"{club} {short(ss[0])}–{short(ss[1])}"
        rules = (("sum of the two seasons", sum(v), S_obs, Ys, -S_obs, -Ys),
                 ("most negative single season of the pair", min(v), omin, Ymin, -omax, -Ymax),
                 ("milder season (asymmetry-step rule)", max(v), omax, Ymild, -omin, -Ymild_s))
        for rule, thr, o_stat, y_stat, o_mir, y_mir in rules:
            for side, ov, yv in (("deficit", o_stat, y_stat), ("surplus mirror", o_mir, y_mir)):
                o = int((ov <= thr + EPS).sum())
                cnt = (yv <= thr + EPS).sum(1)
                rows.append(dict(run=run, rule=rule, side=side,
                                 threshold=thr if side == "deficit" else -thr, threshold_sd=(thr if side == "deficit" else -thr) / sd,
                                 observed_pairs=o, share_panels_any=(cnt >= 1).mean(), mean_pairs_per_panel=cnt.mean(),
                                 share_panels_ge_observed=(cnt >= o).mean()))
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "op2_null.csv", index=False)
    out(f"Null: the carry-over-only AR(1) (ρ = {rho:.4f}, SD {sd:.5f}), {NSIM:,} panels, seed {SEED} — the panels the "
        f"asymmetry step used. In each panel, the same {len(cur)} pairs are scored. Deficit side: a pair qualifies if its statistic is at or "
        "below the named run's value (sum rule: pair sum ≤ run sum; single-season rule: the pair's more negative "
        "season ≤ the run's more negative season; milder-season rule: both seasons ≤ the run's milder season). Surplus mirror: "
        "the same threshold with the sign reversed, pairs at or above it (sum ≥ −sum; more positive season ≥ −value; "
        "both ≥ −value). The observed surplus count is for the real data.\n")
    out(md_table(t, "{:.4f}"))
    out(f"\n`share_panels_any` = share of simulated {len(seasons)}-season leagues with at least one such pair; "
        "`mean_pairs_per_panel` = mean count; `share_panels_ge_observed` = share with at least the observed count "
        "(one-sided p against carry-over alone). Overlapping pairs (three bad seasons in a row) count twice, as in the asymmetry step.\n")
    ts = t[(t.rule == "sum of the two seasons") & (t.side == "deficit")].reset_index(drop=True)
    finding = ts.share_panels_any.iloc[0] < 0.05
    inrange = 0.3 <= ts.share_panels_any.iloc[0] <= 0.7
    out(f"**Sum rule, Tottenham depth: share of simulated leagues with a pair as deep = {ts.share_panels_any.iloc[0]:.4f} "
        f"(Chelsea depth {ts.share_panels_any.iloc[1]:.4f}).** Expectation (0.3–0.7): "
        f"**{'MET' if inrange else 'NOT MET'}**"
        f"{'; share below 0.05 — FINDING' if finding else ''}.\n")
    return ("; ".join(f"{r.run.split()[0]} {r.rule.split()[0]} {r.side.split()[0]} obs {r.observed_pairs} any {r.share_panels_any:.4f} "
                      f"E {r.mean_pairs_per_panel:.3f} ge {r.share_panels_ge_observed:.4f}" for r in t.itertuples())
            + f"; ranks THFC {pos[tkey]} CFC {pos[ckey]}"), []


def value_ranks(m):
    v = pd.read_csv(VALUES)[["season", "team_id", "log_value_rel"]].rename(columns={"log_value_rel": "lv"})
    j = m.merge(v, on=["season", "team_id"])
    j["value_rank"] = j.groupby("season").lv.rank(ascending=False, method="min").astype(int)
    j["value_quintile"] = (j.value_rank - 1) // 4 + 1
    return j


def exact_multinomial_p(counts, k=5):
    """Exact multinomial goodness-of-fit p (uniform cells): sum of P(x) over tables with P(x) <= P(observed)."""
    n = int(sum(counts))
    lp = lambda x: stats.multinomial.logpmf(x, n, [1 / k] * k)
    lobs = lp(counts)
    tot = 0.0
    for cut in itertools.combinations(range(n + k - 1), k - 1):
        x = np.diff((-1,) + cut + (n + k - 1,)) - 1
        l = lp(x)
        if l <= lobs + 1e-9:
            tot += np.exp(l)
    return min(tot, 1.0)


def op3(m, seasons):
    out("## 3. Are rich clubs spared?\n")
    rho, sd = rho_sd(m)
    j = value_ranks(m)
    out(f"Squad-value rank within season from `log_value_rel` in `{VALUES.name}` (1 = highest; 20 clubs "
        "per season; no ties). Value quintile Q1 = ranks 1–4 (richest) … Q5 = ranks 17–20. Thresholds on c in units "
        f"of the observed SD {sd:.5f} (ddof 1), as the asymmetry step. Under a uniform draw each qualifying season is equally likely "
        "to fall in any quintile (probability 1/5, since each season has exactly four clubs per quintile).\n")
    out(f"Tests: (i) chi-square against uniform with Monte Carlo p ({NDRAW:,} multinomial draws, seed {SEED}); "
        "(ii) exact multinomial p (full enumeration); (iii) directional: exact binomial P(Q1 count ≤ observed) with "
        "p = 1/5 (small = rich clubs under-represented = spared), and the mean value rank against 10.5 with a Monte "
        f"Carlo p from {NDRAW:,} uniform draws of ranks 1–20. Caveat: repeat seasons of the same club are not "
        "independent, so these p-values are if anything too small.\n")
    rng = np.random.default_rng(SEED)
    lists, summ = [], []
    for lab, mask in (("deficit ≤ −1 SD", j.c <= -sd + EPS), ("deficit ≤ −1.5 SD", j.c <= -1.5 * sd + EPS),
                      ("surplus ≥ +1 SD", j.c >= sd - EPS), ("surplus ≥ +1.5 SD", j.c >= 1.5 * sd - EPS)):
        d = j[mask].sort_values("c", ascending=lab.startswith("deficit"))
        n = len(d)
        counts = np.array([(d.value_quintile == q).sum() for q in range(1, 6)])
        e = n / 5
        chi = ((counts - e) ** 2 / e).sum()
        sim = rng.multinomial(n, [0.2] * 5, size=NDRAW)
        chi_sim = ((sim - e) ** 2 / e).sum(1)
        p_mc = ((chi_sim >= chi - 1e-9).sum() + 1) / (NDRAW + 1)
        p_ex = exact_multinomial_p(counts)
        p_q1 = stats.binom.cdf(counts[0], n, 0.2)
        mr = d.value_rank.mean()
        rs = rng.integers(1, 21, size=(NDRAW, n)).mean(1)
        p_mr = ((np.abs(rs - 10.5) >= abs(mr - 10.5) - 1e-9).sum() + 1) / (NDRAW + 1)
        summ.append(dict(set=lab, n=n, Q1=counts[0], Q2=counts[1], Q3=counts[2], Q4=counts[3], Q5=counts[4],
                         expected_per_q=e, chi2=chi, p_chi2_mc=p_mc, p_exact_multinomial=p_ex,
                         p_Q1_le_obs=p_q1, mean_value_rank=mr, p_mean_rank_two_sided=p_mr))
        for r in d.itertuples():
            lists.append(dict(set=lab, club=r.club, season=r.season, c=r.c, c_in_sd=r.c / sd,
                              value_rank=r.value_rank, value_quintile=r.value_quintile, finish=r.finish, label=r.label))
    L = pd.DataFrame(lists); T = pd.DataFrame(summ)
    L.to_csv(OUT / "op3_listed_seasons.csv", index=False)
    T.to_csv(OUT / "op3_quintile_tests.csv", index=False)
    for lab in L.set.unique():
        out(f"**{lab}** ({(L.set == lab).sum()} club-seasons):\n")
        out(md_table(L[L.set == lab].drop(columns="set").reset_index(drop=True), "{:.4f}"))
        out("")
    out("Distribution by value quintile and tests:\n")
    out(md_table(T, "{:.4f}"))
    d1 = T.iloc[0]; d15 = T.iloc[1]
    out(f"\n**Deep-deficit seasons (≤ −1 SD): {int(d1.Q1)} of {int(d1.n)} in the richest quintile (expected {d1.expected_per_q:.1f}); "
        f"P(Q1 ≤ {int(d1.Q1)}) = {d1.p_Q1_le_obs:.3f}; spread across quintiles p = {d1.p_chi2_mc:.3f} (MC) / "
        f"{d1.p_exact_multinomial:.3f} (exact). At ≤ −1.5 SD: {int(d15.Q1)} of {int(d15.n)} in Q1, "
        f"p = {d15.p_chi2_mc:.3f} / {d15.p_exact_multinomial:.3f}.**\n")
    return ("; ".join(f"{r.set} n {r.n} Q {r.Q1}/{r.Q2}/{r.Q3}/{r.Q4}/{r.Q5} p_mc {r.p_chi2_mc:.3f} p_ex {r.p_exact_multinomial:.3f} "
                      f"pQ1 {r.p_Q1_le_obs:.3f} meanrank {r.mean_value_rank:.2f}" for r in T.itertuples())), []


def op4(m, seasons):
    out("## 4. Points context\n")
    f = pd.read_csv(FINISH)
    f = f[f.season.isin(FINAL)]
    out(f"Source `{FINISH.name}` (points after deductions: 2023/24 Everton −8, Nottingham Forest −4). "
        "No model estimation.\n")
    rows = []
    for s in FINAL:
        g = f[f.season == s].set_index("finish")
        r = dict(season=short(s), pts_4th=int(g.loc[4, "points"]), pts_5th=int(g.loc[5, "points"]),
                 pts_17th=int(g.loc[17, "points"]), pts_18th=int(g.loc[18, "points"]))
        for club, tag in ((TOT, "THFC"), (CHE, "CFC")):
            x = f[(f.season == s) & (f.club == club)].iloc[0]
            r[f"{tag}_finish"] = int(x.finish); r[f"{tag}_pts"] = int(x.points)
            r[f"{tag}_minus_18th"] = int(x.points) - r["pts_18th"]
            r[f"{tag}_minus_4th"] = int(x.points) - r["pts_4th"]
        rows.append(r)
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "op4_points_context.csv", index=False)
    out(md_table(t[["season", "pts_4th", "pts_5th", "pts_17th", "pts_18th"]]))
    out("")
    out(md_table(t[["season"] + [c for c in t.columns if c.startswith(("THFC", "CFC"))]]))
    out("\n`_minus_18th` = club points − 18th-placed points (positive = margin above the drop zone); `_minus_4th` = "
        "club points − 4th-placed points (negative = short of the top four).\n")
    COEF, COEF_LO, COEF_HI, ns = points_coef()
    named = []
    for club, ss in ((TOT, TOT_S), (CHE, CHE_S)):
        for s in ss:
            c = club_val(m, club, s)
            x = f[(f.season == s) & (f.club == club)].iloc[0]
            named.append(dict(club=club, season=short(s), c=c, points_assoc=c * COEF, points_assoc_lo=c * COEF_LO,
                              points_assoc_hi=c * COEF_HI, actual_points=int(x.points), finish=int(x.finish)))
    N = pd.DataFrame(named)
    N.to_csv(OUT / "op4_named_points.csv", index=False)
    out(f"**Availability-associated points, association not causation.** "
        f"c × {COEF:.2f} (points per unit of c from this run: points ~ log squad value + c + season FE over all {ns} "
        f"seasons of the variant, HC3, as the battery's points decomposition; the `_lo`/`_hi` columns use its 95% "
        f"interval {COEF_LO:.1f}–{COEF_HI:.1f}). c is centred on the season mean, so "
        "these are points relative to a league-average availability season.\n")
    out(md_table(N.assign(c=N.c.map("{:.4f}".format)), "{:.1f}"))
    out("")
    return "; ".join(f"{r.club.split()[0]} {r.season} c {r.c:.4f} pts {r.points_assoc:.1f} ({r.points_assoc_lo:.1f} to {r.points_assoc_hi:.1f})"
                     for r in N.itertuples()), []


def op5(m, seasons):
    out("## 5. Verdict\n")
    t2 = pd.read_csv(OUT / "op2_null.csv")
    P = pd.read_csv(OUT / "op2_pairs_ranked.csv")
    T3 = pd.read_csv(OUT / "op3_quintile_tests.csv").set_index("set")
    C = pd.read_csv(OUT / "op4_points_context.csv")
    N = pd.read_csv(OUT / "op4_named_points.csv")
    g = lambda run, rule, side="deficit": t2[t2.run.str.startswith(run) & t2.rule.str.startswith(rule) & (t2.side == side)].iloc[0]
    ts, cs = g(TOT, "sum"), g(CHE, "sum")
    tm, cm = g(TOT, "most"), g(CHE, "most")
    th, ch = g(TOT, "milder"), g(CHE, "milder")
    rt = int(P[(P.club == TOT) & (P.seasons == "2024/25–2025/26")]["rank"].iloc[0])
    rc = int(P[(P.club == CHE) & (P.seasons == "2022/23–2023/24")]["rank"].iloc[0])
    changes = (ts.share_panels_any < 0.05) or (cs.share_panels_any < 0.05)
    COEF, COEF_LO, COEF_HI, ns = points_coef()
    out("**(1) Does the sum rule change the asymmetry step's conclusion?** "
        f"{'Yes' if changes else 'No'}. Ranked by the two-season sum, Tottenham 2024/25–2025/26 is {rt} of {len(P)} and "
        f"Chelsea 2022/23–2023/24 is {rc}. Under carry-over alone, a pair at least as deep by sum appears in "
        f"{ts.share_panels_any:.0%} of simulated leagues for Tottenham's depth and {cs.share_panels_any:.0%} for Chelsea's "
        f"(milder-season rule: {th.share_panels_any:.0%} and {ch.share_panels_any:.0%}; most-negative-season rule: "
        f"{tm.share_panels_any:.0%} and {cm.share_panels_any:.0%}). The surplus mirrors are "
        f"{g(TOT, 'sum', 'surplus mirror').share_panels_any:.0%} and {g(CHE, 'sum', 'surplus mirror').share_panels_any:.0%}, "
        "so the null is symmetric as built. Expectation (0.3–0.7 under the sum rule): "
        f"{'MET' if 0.3 <= ts.share_panels_any <= 0.7 else 'NOT MET'}.\n")
    d1, d15 = T3.loc["deficit ≤ −1 SD"], T3.loc["deficit ≤ −1.5 SD"]
    s1 = T3.loc["surplus ≥ +1 SD"]
    spared = d1.p_Q1_le_obs < 0.05
    out("**(2) Are rich clubs hit by deep deficits as often as others?** "
        f"{'No — the richest quintile is under-represented' if spared else 'The data do not show that they are spared'}. "
        f"Of {int(d1.n)} club-seasons at or below −1 SD, {int(d1.Q1)} belong to the four highest-value squads of their "
        f"season (expected {d1.expected_per_q:.1f} under a uniform draw; quintiles Q1–Q5 "
        f"{int(d1.Q1)}/{int(d1.Q2)}/{int(d1.Q3)}/{int(d1.Q4)}/{int(d1.Q5)}; chi-square MC p = {d1.p_chi2_mc:.3f}, exact "
        f"p = {d1.p_exact_multinomial:.3f}; P(Q1 ≤ observed) = {d1.p_Q1_le_obs:.3f}). At −1.5 SD: {int(d15.Q1)} of "
        f"{int(d15.n)} (p = {d15.p_exact_multinomial:.3f}). Surplus seasons ≥ +1 SD: {int(s1.Q1)} of {int(s1.n)} in Q1 "
        f"(p = {s1.p_exact_multinomial:.3f}).\n")
    Cf = C.set_index("season")
    nm = N.set_index(["club", "season"])
    tp = nm.loc[(TOT, "2025/26")]; tp0 = nm.loc[(TOT, "2024/25")]
    cp0 = nm.loc[(CHE, "2022/23")]; cp1 = nm.loc[(CHE, "2023/24")]
    out("**(3) Points at stake.** "
        f"At {COEF:.2f} points per unit (association, not causation; the run's all-seasons coefficient), the named "
        f"deficits are associated with {tp0.points_assoc:.1f} and {tp.points_assoc:.1f} points for Tottenham "
        f"(2024/25, 2025/26) and {cp0.points_assoc:.1f} and {cp1.points_assoc:.1f} for Chelsea (2022/23, 2023/24); on "
        f"the interval {COEF_LO:.1f}–{COEF_HI:.1f} the Tottenham 2025/26 figure runs {tp.points_assoc_hi:.1f} to {tp.points_assoc_lo:.1f}. "
        f"Tottenham finished {int(Cf.loc['2024/25', 'THFC_finish'])} and {int(Cf.loc['2025/26', 'THFC_finish'])}, "
        f"{int(Cf.loc['2024/25', 'THFC_minus_18th']):+d} and {int(Cf.loc['2025/26', 'THFC_minus_18th']):+d} points from 18th place, "
        f"{int(Cf.loc['2024/25', 'THFC_minus_4th']):+d} and {int(Cf.loc['2025/26', 'THFC_minus_4th']):+d} from 4th. "
        f"Chelsea finished {int(Cf.loc['2022/23', 'CFC_finish'])} and {int(Cf.loc['2023/24', 'CFC_finish'])}, "
        f"{int(Cf.loc['2022/23', 'CFC_minus_4th']):+d} and {int(Cf.loc['2023/24', 'CFC_minus_4th']):+d} from 4th.\n")
    out("The values of c used, as in `op4_named_points.csv`: "
        + "; ".join(f"{r.club} {r.season} c = {r.c:.4f}" for r in N.itertuples()) + ".\n")
    out(f"Tottenham 2025/26 finished {int(Cf.loc['2025/26', 'THFC_minus_18th'])} points above 18th place; the "
        f"availability-associated figure for that season ({tp.points_assoc:.1f}, interval {tp.points_assoc_hi:.1f} to "
        f"{tp.points_assoc_lo:.1f}) is larger than that margin. That is an association, not a claim that better "
        "availability would have kept them further clear.\n")
    out("**Sentences a paper could use (conservative first):**\n")
    out(f"1. \"Two-season runs of low availability as deep as Tottenham Hotspur's in 2024/25–2025/26 are "
        f"{'common' if ts.share_panels_any >= 0.3 else ('not rare' if ts.share_panels_any >= 0.05 else 'rare')} under one-season carry-over alone, "
        f"whether depth is judged by the milder season ({th.share_panels_any:.0%} of simulated {len(seasons)}-season leagues) or by the "
        f"two-season total ({ts.share_panels_any:.0%}); we therefore do not treat such runs as evidence of a persistent club effect.\"")
    out(f"2. \"Low-availability seasons (at least one SD below the season mean) fall across the squad-value distribution "
        f"{'as a uniform draw would give' if d1.p_exact_multinomial >= 0.05 else 'unevenly'} ({int(d1.Q1)} of {int(d1.n)} in the "
        f"top value quintile against {d1.expected_per_q:.1f} expected; exact multinomial p = {d1.p_exact_multinomial:.2f})"
        f"{'; the richest clubs are not measurably spared' if not spared else '; the richest clubs are under-represented'}.\"")
    out(f"3. \"On the all-seasons association of {COEF:.1f} points per unit of availability (95% interval {COEF_LO:.1f}–{COEF_HI:.1f}), "
        f"Tottenham's 2025/26 availability deficit corresponds to about {abs(tp.points_assoc):.0f} points "
        f"(range {abs(tp.points_assoc_lo):.0f}–{abs(tp.points_assoc_hi):.0f}) below a league-average availability season; "
        f"this is an association, not an estimate of causal effect.\"\n")
    # inventory and integrity
    new = sorted(p for p in OUT.iterdir() if p.is_file())
    out("**Files written by this step:**\n")
    for p in new + [REPORT]:
        out(f"- `{p.name}`")
    out("")
    chk = pd.read_csv(OUT / "op1_checks.csv", keep_default_na=False)
    rec = chk[chk.result == "RECORDED"]
    paths = dict(READ_ONLY)
    same = all((sha(paths[r.check.replace("sha256 ", "")]) if paths[r.check.replace("sha256 ", "")] is not None else "") == r.sha256
               for r in rec.itertuples())
    out(f"Read-only inputs unchanged since step 1 (SHA-256 re-check): **{'YES' if same else 'NO'}**.\n")
    return (f"sum-rule THFC any {ts.share_panels_any:.4f} CFC {cs.share_panels_any:.4f}; conclusion {'changed' if changes else 'unchanged'}; "
            f"<=-1SD Q1 {int(d1.Q1)}/{int(d1.n)} p_ex {d1.p_exact_multinomial:.3f}; THFC 25/26 pts {tp.points_assoc:.1f}; inputs unchanged {same}"), []


if __name__ == "__main__":
    op = sys.argv[1]
    m, seasons = load()
    note, fails = globals()[op](m, seasons)
    with open(REPORT, "a", encoding="utf-8") as f:
        if op == "op1":
            f.write("# Deficit runs: sum-rule sensitivity, squad value, points at stake\n\n")
        f.write("\n".join(LINES) + "\n\n")
    if fails:
        sys.exit(1)
