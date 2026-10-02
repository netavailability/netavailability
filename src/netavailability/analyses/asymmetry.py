"""Is season-centred NETavailability asymmetric, and how unusual are the Tottenham 2024/25-2025/26 and Chelsea
2022/23-2023/24 two-season deficit runs under carry-over alone?

  op1  self-checks against the run's own inputs (rows for the configured seasons; lag-1 correlation, SD and the named
       clubs' c recomputed from club_seasons.csv; a failure exits 1) and a check that the imported null reproduces
       the carry-over step's saved draws
  op2  shape (skewness, excess kurtosis, bootstrap intervals, the null's shape) and the ceiling at 1.0
  op3  is bad stickier than good: lag-1 slopes below and above the season mean, with an interaction test and the
       same difference under the null
  op4  two-season runs at k = 1, 1.5 SD and at the Tottenham depth against the carry-over-only null
The null is the carry-over step's `simulate` (imported), 5,000 panels, fixed seed.
Reads persistence/op1_panel.csv and carryover_null/op3_null_draws.csv in NETAV_ANALYSIS_DIR; writes its CSVs and
report.md in asymmetry/. Run as: python -m netavailability.analyses.asymmetry op1|op2|op3|op4
"""
import hashlib
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf

import os
from . import carryover_null as carry
from . import selfcheck
BASE = Path(os.environ["NETAV_ANALYSIS_DIR"])
PANEL = BASE / "persistence" / "op1_panel.csv"
CARRY_SCRIPT = Path(carry.__file__)
NULL_DRAWS = BASE / "carryover_null" / "op3_null_draws.csv"
OUT = BASE / "asymmetry"
REPORT = OUT / "report.md"
SEED = 20260930
NSIM = 5000
NBOOT = 2000
TOT, CHE = "Tottenham Hotspur", "Chelsea"
TOT_S, CHE_S = ("2024/2025", "2025/2026"), ("2022/2023", "2023/2024")

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
    """Row indices (cur, prev) for the same club in consecutive seasons."""
    pos = {(ti, s): k for k, (ti, s) in enumerate(zip(m.team_id, m.s_idx))}
    pr = [(k, pos[(ti, s - 1)]) for k, (ti, s) in enumerate(zip(m.team_id, m.s_idx)) if (ti, s - 1) in pos]
    return np.array([p[0] for p in pr]), np.array([p[1] for p in pr])


def rho_sd(m):
    cur, prv = pairs_idx(m)
    return stats.pearsonr(m.c.values[cur], m.c.values[prv])[0], m.c.std(ddof=1)


def club_val(m, club, season):
    return float(m.loc[(m.club == club) & (m.season == season), "c"].iloc[0])


def run_thresholds(m):
    sd = m.c.std(ddof=1)
    tot = [club_val(m, TOT, s) for s in TOT_S]
    che = [club_val(m, CHE, s) for s in CHE_S]
    return sd, tot, che, max(tot), max(che)   # less extreme = the larger (less negative) value


def sims(m):
    rho, sd = rho_sd(m)
    return carry.simulate(m, rho, sd, nsim=NSIM, seed=SEED)


def skew_kurt(x, axis=-1):
    return stats.skew(x, axis=axis, bias=False), stats.kurtosis(x, axis=axis, fisher=True, bias=False)


# ---------------------------------------------------------------- ops
def op1(m, seasons):
    out("## 1. Provenance and checks\n")
    out(f"Run {datetime.now():%Y-%m-%d %H:%M}. Read-only inputs:\n")
    out(f"- `persistence/{PANEL.name}` — sha256 `{sha(PANEL)[:16]}…`, {len(m)} rows")
    out(f"- `{CARRY_SCRIPT.name}` — sha256 `{sha(CARRY_SCRIPT)[:16]}…`; imported so that the "
        "null is the carry-over step's `simulate` function itself (AR(1) per club, stationary start, "
        "observed club-seasons kept, season-centred), not a re-implementation.")
    out(f"- `carryover_null/{NULL_DRAWS.name}` — used only to confirm the imported null reproduces the carry-over step's draws.\n")
    out("**Expectation written before the first run:** Tottenham's two-season run is rare under "
        "carry-over alone — the share of simulated panels containing any run at least as deep is below 0.05. "
        "No expectation is set for asymmetry.\n")
    fails = []
    R = selfcheck.reference()
    tol = selfcheck.TOL
    rho, sd = rho_sd(m)
    ok = len(m) == R["rows"]
    out(f"Targets are recomputed from this run's `club_seasons.csv` and configured seasons (`selfcheck`), tolerance {tol:g}.\n")
    out(f"**(a)** rows = {len(m)} (configured: {len(R['seasons'])} seasons × {selfcheck.CLUBS_PER_SEASON} = {R['rows']}) → **{'PASS' if ok else 'FAIL'}**")
    if not ok: fails.append("a")
    npairs = len(pairs_idx(m)[0])
    ok = abs(rho - R["lag1_r_c"]) <= tol and npairs == R["pairs"]
    out(f"**(b)** pooled lag-1 Pearson correlation of c (same club, consecutive seasons, {npairs} "
        f"pairs) = {rho:.6f} (recomputed: {R['lag1_r_c']:.6f} on {R['pairs']} pairs) → **{'PASS' if ok else 'FAIL'}**")
    if not ok: fails.append("b")
    ok = abs(sd - R["sd_c"]) <= tol
    out(f"**(c)** SD of c (ddof 1) = {sd:.6f} (recomputed: {R['sd_c']:.6f}) → **{'PASS' if ok else 'FAIL'}**")
    if not ok: fails.append("c")
    _, tot, che, tthr, cthr = run_thresholds(m)
    ref_t = [float(R["c"][(TOT, s)]) for s in TOT_S]
    ok = all(abs(a - b) <= tol for a, b in zip(tot, ref_t))
    out(f"**(d)** Tottenham c 2024/25 = {tot[0]:.6f} (recomputed: {ref_t[0]:.6f}), 2025/26 = {tot[1]:.6f} "
        f"(recomputed: {ref_t[1]:.6f}) → **{'PASS' if ok else 'FAIL'}**\n")
    if not ok: fails.append("d")
    # consistency: the imported null reproduces the carry-over step's saved draws (sd_c and lag1_r columns)
    Y = sims(m)
    d = pd.read_csv(NULL_DRAWS)
    cur, prv = pairs_idx(m)
    a = Y[:, cur] - Y[:, cur].mean(1, keepdims=True); b = Y[:, prv] - Y[:, prv].mean(1, keepdims=True)
    r_sim = (a * b).sum(1) / np.sqrt((a ** 2).sum(1) * (b ** 2).sum(1))
    dsd = np.abs(Y.std(1, ddof=1) - d.sd_c.values).max(); dr = np.abs(r_sim - d.lag1_r.values).max()
    ok = dsd < 1e-12 and dr < 1e-12
    out(f"**(e)** imported null vs the carry-over step's saved draws (5,000 panels, seed {SEED}): max |Δ SD of c| = {dsd:.2g}, "
        f"max |Δ lag-1 r| = {dr:.2g} → **{'PASS' if ok else 'FAIL'}** (identical panels).\n")
    if not ok: fails.append("e")
    rows = [dict(club=TOT, season=s, c=v, sd_units=v / sd) for s, v in zip(TOT_S, tot)] + \
           [dict(club=CHE, season=s, c=v, sd_units=v / sd) for s, v in zip(CHE_S, che)]
    t = pd.DataFrame(rows)
    out(f"The two runs (SD units = c / {sd:.4f} observed SD):\n")
    out(md_table(t, "{:.4f}"))
    out(f"\nLess extreme season of each run: Tottenham {tthr:.4f} = **{tthr/sd:.3f} SD**; Chelsea {cthr:.4f} = "
        f"**{cthr/sd:.3f} SD**. By the depth rule (both seasons at or below the less extreme value) "
        f"Chelsea's run is {'deeper' if cthr < tthr else 'shallower'} than Tottenham's "
        f"(Chelsea's milder season {cthr/sd:.2f} SD vs Tottenham's {tthr/sd:.2f} SD), although Tottenham has the "
        f"single deepest season ({min(tot)/sd:.2f} SD). Both runs are in the FINAL seasons (2022/23–2025/26).\n")
    t.to_csv(OUT / "op1_runs.csv", index=False)
    pd.DataFrame([dict(rows=len(m), lag1_rho=rho, sd_c=sd, tot_2425=tot[0], tot_2526=tot[1], che_2223=che[0],
                       che_2324=che[1], null_max_dsd=dsd, null_max_dr=dr,
                       checks="PASS" if not fails else "FAIL " + ",".join(fails))]
                 ).to_csv(OUT / "op1_checks.csv", index=False)
    out(f"Self-checks against the run's own inputs: {'ALL PASS' if not fails else 'FAILED ' + ','.join(fails)}\n")
    return (("ALL PASS" if not fails else "FAIL " + ",".join(fails)) +
            f"; rho {rho:.4f}; sd {sd:.5f}; THFC {tot[0]/sd:.2f},{tot[1]/sd:.2f} SD; CFC {che[0]/sd:.2f},{che[1]/sd:.2f} SD; "
            f"null matches the saved draws"), fails


def op2(m, seasons):
    out("## 2. Shape and ceiling\n")
    sd = m.c.std(ddof=1)
    rng = np.random.default_rng(SEED)
    rows = []
    Y = sims(m)
    sk_null, ku_null = skew_kurt(Y, axis=1)
    fin = (m.label == "FINAL").values
    sk_null_f, ku_null_f = skew_kurt(Y[:, fin], axis=1)
    for name, x, skn, kun in ((f"all {len(m)}", m.c.values, sk_null, ku_null),
                              (f"FINAL {int(fin.sum())}", m.c.values[fin], sk_null_f, ku_null_f)):
        sk, ku = skew_kurt(x)
        B = x[rng.integers(0, len(x), (NBOOT, len(x)))]
        bs, bk = skew_kurt(B, axis=1)
        rows.append(dict(sample=name, n=len(x), skewness=sk, skew_lo=np.percentile(bs, 2.5), skew_hi=np.percentile(bs, 97.5),
                         excess_kurtosis=ku, kurt_lo=np.percentile(bk, 2.5), kurt_hi=np.percentile(bk, 97.5),
                         null_skew_p_le_obs=(skn <= sk).mean(), null_kurt_p_ge_obs=(kun >= ku).mean()))
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "op2_shape.csv", index=False)
    out(f"Adjusted Fisher–Pearson skewness and excess kurtosis (scipy, `bias=False`). Bootstrap 95% intervals: "
        f"{NBOOT:,} resamples of club-seasons with replacement, seed {SEED}, percentile method (resampling "
        f"club-seasons ignores within-club carry-over, so these intervals are if anything too narrow). "
        f"`null_skew_p_le_obs` = share of the {NSIM:,} carry-over-only panels (normal shocks, symmetric) with "
        f"skewness at or below the observed; `null_kurt_p_ge_obs` = share with excess kurtosis at or above.\n")
    out(md_table(t, "{:.4f}"))
    out(f"\nNull reference: simulated skewness mean {sk_null.mean():+.3f} (2.5–97.5% {np.percentile(sk_null,2.5):+.3f} to "
        f"{np.percentile(sk_null,97.5):+.3f}) for {len(m)}; FINAL {int(fin.sum())} {np.percentile(sk_null_f,2.5):+.3f} to "
        f"{np.percentile(sk_null_f,97.5):+.3f}.\n")
    cols = ["season", "club", "label", "NETavailability", "c"]
    e = m[cols].copy(); e["sd_units"] = e.c / sd
    lo, hi = e.nsmallest(5, "c"), e.nlargest(5, "c")
    out("Five most negative club-seasons:\n"); out(md_table(lo, "{:.4f}"))
    out("\nFive most positive club-seasons:\n"); out(md_table(hi, "{:.4f}"))
    pd.concat([lo.assign(tail="negative"), hi.assign(tail="positive")]).to_csv(OUT / "op2_extremes.csv", index=False)
    cnt = []
    for k in (1, 1.5, 2):
        cnt.append(dict(k_sd=k, below_minus_k=int((m.c <= -k * sd).sum()), above_plus_k=int((m.c >= k * sd).sum()),
                        below_FINAL=int((m.c[fin] <= -k * sd).sum()), above_FINAL=int((m.c[fin] >= k * sd).sum()),
                        null_mean_below=(Y <= -k * sd).sum(1).mean(), null_mean_above=(Y >= k * sd).sum(1).mean(),
                        normal_expect_each=len(m) * stats.norm.sf(k)))
    ct = pd.DataFrame(cnt)
    ct.to_csv(OUT / "op2_tail_counts.csv", index=False)
    out(f"\nTail counts (SD = {sd:.5f}; thresholds inclusive). `normal_expect_each` = {len(m)} × P(Z ≥ k); "
        "`null_mean_*` = mean count per carry-over-only panel:\n")
    out(md_table(ct, "{:.2f}"))
    # ceiling
    g = m.groupby("season").NETavailability
    ce = pd.DataFrame(dict(max_raw=g.max(), league_mean=g.mean(), min_raw=g.min(), sd_raw=g.std(ddof=1)))
    ce["max_to_1"] = 1 - ce.max_raw
    ce["mean_to_1_in_sd_c"] = (1 - ce.league_mean) / sd
    ce["max_c_sd_units"] = (ce.max_raw - ce.league_mean) / sd
    ce["min_c_sd_units"] = (ce.min_raw - ce.league_mean) / sd
    ce = ce.reset_index()
    ce.to_csv(OUT / "op2_ceiling.csv", index=False)
    out("\nCeiling check, per season (raw NETavailability; SD units use the pooled SD of c):\n")
    out(md_table(ce, "{:.4f}"))
    gap = ce.max_to_1.min(); mean_gap = ce.mean_to_1_in_sd_c.min()
    out(f"\nHighest raw NETavailability in any season: {ce.max_raw.max():.4f} ({ce.loc[ce.max_raw.idxmax(),'season']}); "
        f"smallest distance from a season's maximum to 1.0 = {gap:.4f} = {gap/sd:.2f} SD of c. The league mean sits "
        f"{mean_gap:.2f}–{ce.mean_to_1_in_sd_c.max():.2f} SD below 1.0, while the most extreme positive club-season is "
        f"{ce.max_c_sd_units.max():.2f} SD above its season mean. "
        f"Across all seasons {int((m.c >= sd).sum())}/{int((m.c >= 1.5*sd).sum())}/{int((m.c >= 2*sd).sum())} club-seasons "
        f"are at or above +1/+1.5/+2 SD against {int((m.c <= -sd).sum())}/{int((m.c <= -1.5*sd).sum())}/{int((m.c <= -2*sd).sum())} "
        f"at or below −1/−1.5/−2 SD, the largest positive and negative values are {m.c.max()/sd:+.2f} and {m.c.min()/sd:+.2f} SD, and "
        f"skewness is {t.skewness[0]:+.3f}. "
        + ("**No club is close enough to 1.0 for the upper tail to be mechanically compressed**: the nearest approach "
           f"({m.loc[m.NETavailability.idxmax(), 'club']} {m.loc[m.NETavailability.idxmax(), 'season']}, {ce.max_raw.max():.4f}) still leaves {gap:.3f} = {gap/sd:.2f} SD of headroom, and the "
           "upper tail is as long and as populated as the lower one. The bound can only bite in the rare season where one "
           "club is already more than 2.5 SD above the mean."
           if (m.c >= 2 * sd).sum() >= (m.c <= -2 * sd).sum() - 1 and m.c.max() >= -m.c.min() - 0.01 else
           "**The upper tail is shorter than the lower one, so mechanical compression cannot be ruled out.**") + "\n")
    s0 = t.iloc[0]
    return (f"skew all {s0.skewness:.3f} [{s0.skew_lo:.3f},{s0.skew_hi:.3f}] null p {s0.null_skew_p_le_obs:.3f}; "
            f"kurt {s0.excess_kurtosis:.3f}; FINAL skew {t.iloc[1].skewness:.3f}; tails -1/-1.5/-2 "
            f"{'/'.join(str(x) for x in ct.below_minus_k)} vs +1/+1.5/+2 {'/'.join(str(x) for x in ct.above_plus_k)}; "
            f"max raw {ce.max_raw.max():.4f}, min gap to 1 {gap:.4f}"), []


def slopes_null(Y, cur, prv, mask_fn):
    """Vectorised OLS slope of Y[cur] on Y[prv] within a per-panel mask."""
    x, y = Y[:, prv], Y[:, cur]
    M = mask_fn(x)
    n = M.sum(1)
    xm = (x * M).sum(1) / np.maximum(n, 1); ym = (y * M).sum(1) / np.maximum(n, 1)
    sxy = ((x - xm[:, None]) * (y - ym[:, None]) * M).sum(1)
    sxx = (((x - xm[:, None]) ** 2) * M).sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(n >= 3, sxy / sxx, np.nan), ym, n


def op3(m, seasons):
    out("## 3. Is bad stickier than good?\n")
    sd = m.c.std(ddof=1)
    cur, prv = pairs_idx(m)
    j = pd.DataFrame(dict(c=m.c.values[cur], c_prev=m.c.values[prv], club=m.club.values[cur],
                          team_id=m.team_id.values[cur], season=m.season.values[cur]))
    out(f"{len(j)} club pairs in consecutive seasons (as step 1). OLS of c(t) on c(t−1) in each subset; SE shown both "
        "conventional and clustered by club. Slope difference tested by the interaction model "
        "c(t) = a + b·c(t−1) + d·G + e·G·c(t−1) (G = 1 for the lower group), club-clustered SE; e = lower-group "
        "slope − upper-group slope, so e > 0 means deficits are stickier.\n")
    rows = []
    specs = [("c(t−1) < 0", j.c_prev < 0), ("c(t−1) ≥ 0", j.c_prev >= 0),
             ("c(t−1) ≤ −1 SD", j.c_prev <= -sd), ("c(t−1) ≥ +1 SD", j.c_prev >= sd), ("all pairs", j.c_prev == j.c_prev)]
    for name, mask in specs:
        d = j[mask]
        f0 = smf.ols("c ~ c_prev", d).fit()
        fc = smf.ols("c ~ c_prev", d).fit(cov_type="cluster", cov_kwds={"groups": d.team_id})
        rows.append(dict(subset=name, n=len(d), clubs=d.team_id.nunique(), slope=f0.params.c_prev, se_ols=f0.bse.c_prev,
                         se_cluster=fc.bse.c_prev, intercept=f0.params.Intercept, mean_c_prev=d.c_prev.mean(),
                         mean_c_t=d.c.mean()))
    t = pd.DataFrame(rows)
    out(md_table(t, "{:.4f}"))
    Y = sims(m)
    tests = []
    for name, gmask, keep, mf in (
            ("split at 0", j.c_prev < 0, j.c_prev == j.c_prev, None),
            ("tails ±1 SD", j.c_prev <= -sd, (j.c_prev <= -sd) | (j.c_prev >= sd), None)):
        d = j[keep].copy(); d["G"] = gmask[keep].astype(int)
        fi = smf.ols("c ~ c_prev * G", d).fit(cov_type="cluster", cov_kwds={"groups": d.team_id})
        e, se = fi.params["c_prev:G"], fi.bse["c_prev:G"]
        # null distribution of the same slope difference
        if name == "split at 0":
            sl, _, _ = slopes_null(Y, cur, prv, lambda x: x < 0); su, _, _ = slopes_null(Y, cur, prv, lambda x: x >= 0)
        else:
            sl, _, _ = slopes_null(Y, cur, prv, lambda x: x <= -sd); su, _, _ = slopes_null(Y, cur, prv, lambda x: x >= sd)
        diff = sl - su; ok = ~np.isnan(diff)
        tests.append(dict(test=name, n=len(d), slope_diff_lower_minus_upper=e, se_cluster=se, z=e / se,
                          p_cluster=fi.pvalues["c_prev:G"], null_mean_diff=np.nanmean(diff),
                          null_sd_diff=np.nanstd(diff), null_share_ge_obs=(diff[ok] >= e).mean(), null_valid_panels=int(ok.sum())))
    tt = pd.DataFrame(tests)
    out("\nSlope-difference tests (lower − upper). `p_cluster` two-sided from the interaction model; "
        f"`null_share_ge_obs` = one-sided share of the {NSIM:,} carry-over-only panels (same subsets, same "
        "thresholds in c units) with a difference at least as large.\n")
    out(md_table(tt, "{:.4f}"))
    # mean following extreme seasons
    lo, hi = j[j.c_prev <= -sd], j[j.c_prev >= sd]
    wt = stats.ttest_ind(-lo.c, hi.c, equal_var=False)
    _, ym_lo, _ = slopes_null(Y, cur, prv, lambda x: x <= -sd)
    _, ym_hi, _ = slopes_null(Y, cur, prv, lambda x: x >= sd)
    obs_asym = (-lo.c.mean()) - hi.c.mean()
    null_asym = (-ym_lo) - ym_hi
    fol = pd.DataFrame([
        dict(after="c(t−1) ≤ −1 SD", n=len(lo), mean_c_prev=lo.c_prev.mean(), mean_c_t=lo.c.mean(),
             mean_c_t_sd=lo.c.mean() / sd, retained_share=lo.c.mean() / lo.c_prev.mean(),
             null_mean_c_t=np.nanmean(ym_lo)),
        dict(after="c(t−1) ≥ +1 SD", n=len(hi), mean_c_prev=hi.c_prev.mean(), mean_c_t=hi.c.mean(),
             mean_c_t_sd=hi.c.mean() / sd, retained_share=hi.c.mean() / hi.c_prev.mean(),
             null_mean_c_t=np.nanmean(ym_hi))])
    fol.to_csv(OUT / "op3_following.csv", index=False)
    out("\nMean c(t) in the season after an extreme season (`retained_share` = mean c(t) / mean c(t−1)):\n")
    out(md_table(fol, "{:.4f}"))
    out(f"\nMagnitude asymmetry |mean after deficit| − |mean after surplus| = {obs_asym:+.4f} "
        f"({obs_asym/sd:+.2f} SD); Welch t on −c(t) after deficits vs c(t) after surpluses: t = {wt.statistic:.2f}, "
        f"p = {wt.pvalue:.3f} (pairs treated as independent). Under the null the same difference has mean "
        f"{np.nanmean(null_asym):+.4f} and share ≥ observed = {(null_asym[~np.isnan(null_asym)] >= obs_asym).mean():.3f}.\n")
    t.to_csv(OUT / "op3_split_slopes.csv", index=False)
    tt.to_csv(OUT / "op3_slope_diff_tests.csv", index=False)
    return (f"slopes <0 {t.slope[0]:.3f} (n {t.n[0]}), >=0 {t.slope[1]:.3f} (n {t.n[1]}), diff {tt.slope_diff_lower_minus_upper[0]:+.3f} "
            f"p {tt.p_cluster[0]:.3f} null {tt.null_share_ge_obs[0]:.3f}; <=-1SD {t.slope[2]:.3f} (n {t.n[2]}), >=+1SD {t.slope[3]:.3f} "
            f"(n {t.n[3]}), diff {tt.slope_diff_lower_minus_upper[1]:+.3f} p {tt.p_cluster[1]:.3f} null {tt.null_share_ge_obs[1]:.3f}; "
            f"mean after -1SD {lo.c.mean():+.4f}, after +1SD {hi.c.mean():+.4f}"), []


def op4(m, seasons):
    out("## 4. Two-season runs against carry-over alone\n")
    sd, tot, che, tthr, cthr = run_thresholds(m)
    cur, prv = pairs_idx(m)
    Y = sims(m)
    obs = m.c.values
    kT = tthr / sd  # negative
    out(f"A run is one club-pair of consecutive seasons (step 1's {len(cur)} pairs); a club with three consecutive "
        "qualifying seasons contributes two overlapping runs. Deficit run: both seasons ≤ −k·SD; surplus run: both "
        f"≥ +k·SD; SD = observed {sd:.5f}, thresholds held fixed in c units in every simulated panel (the null's "
        f"marginal SD is calibrated to it). k = 1, 1.5 and the Tottenham threshold {abs(kT):.4f} (its 2024/25 value, the less extreme of its two seasons). "
        f"Null: the carry-over-only AR(1), {NSIM:,} panels, seed {SEED} (identical panels to the carry-over step).\n")
    eps = 1e-12
    rows = []
    for klab, k in (("1", 1.0), ("1.5", 1.5), (f"Tottenham {abs(kT):.3f}", abs(kT))):
        thr = k * sd
        od = int(((obs[cur] <= -thr + eps) & (obs[prv] <= -thr + eps)).sum())
        ou = int(((obs[cur] >= thr - eps) & (obs[prv] >= thr - eps)).sum())
        sdn = ((Y[:, cur] <= -thr + eps) & (Y[:, prv] <= -thr + eps)).sum(1)
        sup = ((Y[:, cur] >= thr - eps) & (Y[:, prv] >= thr - eps)).sum(1)
        for tail, o, s in (("deficit", od, sdn), ("surplus", ou, sup)):
            rows.append(dict(k=klab, tail=tail, observed=o, null_mean=s.mean(), null_p95=np.percentile(s, 95),
                             share_ge_obs=(s >= o).mean(), share_any=(s >= 1).mean()))
        # asymmetry statistic: deficit − surplus runs
        rows.append(dict(k=klab, tail="deficit − surplus", observed=od - ou, null_mean=(sdn - sup).mean(),
                         null_p95=np.percentile(sdn - sup, 95), share_ge_obs=((sdn - sup) >= od - ou).mean(),
                         share_any=np.nan))
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "op4_run_counts.csv", index=False)
    out(md_table(t, "{:.4f}"))
    out("\n`share_ge_obs` = share of simulated panels with at least the observed count (one-sided p against "
        "carry-over alone); `share_any` = share with at least one such run.\n")
    # which observed runs
    lst = []
    for kk, (a, b) in enumerate(zip(cur, prv)):
        lo_ = max(obs[a], obs[b]); hi_ = min(obs[a], obs[b])
        if lo_ <= -sd + eps or hi_ >= sd - eps:
            lst.append(dict(club=m.club[a], seasons=f"{m.season[b]}–{m.season[a]}", c_first=obs[b], c_second=obs[a],
                            less_extreme_sd=(lo_ if lo_ <= -sd + eps else hi_) / sd,
                            tail="deficit" if lo_ <= -sd + eps else "surplus", label=m.label[a]))
    ol = pd.DataFrame(lst).sort_values(["tail", "less_extreme_sd"]).reset_index(drop=True)
    ol.to_csv(OUT / "op4_observed_runs.csv", index=False)
    out("Observed runs at k = 1 (every qualifying pair):\n")
    out(md_table(ol, "{:.4f}"))
    # Tottenham / Chelsea depth
    spec = []
    for who, thr in ((f"Tottenham 2024/25–2025/26 (both ≤ {tthr:.4f} = {tthr/sd:.3f} SD)", tthr),
                     (f"Chelsea 2022/23–2023/24 (both ≤ {cthr:.4f} = {cthr/sd:.3f} SD)", cthr)):
        o = int(((obs[cur] <= thr + eps) & (obs[prv] <= thr + eps)).sum())
        s = ((Y[:, cur] <= thr + eps) & (Y[:, prv] <= thr + eps)).sum(1)
        sm = ((Y[:, cur] >= -thr - eps) & (Y[:, prv] >= -thr - eps)).sum(1)
        # per-panel-SD sensitivity: threshold in each panel's own SD units
        psd = Y.std(1, ddof=1)[:, None]
        sp = ((Y[:, cur] <= thr / sd * psd + eps) & (Y[:, prv] <= thr / sd * psd + eps)).sum(1)
        spec.append(dict(run=who, observed_runs_this_deep=o, share_panels_any=(s >= 1).mean(),
                         expected_runs_per_12x20_league=s.mean(), share_panels_ge_observed=(s >= o).mean(),
                         mirror_surplus_share_any=(sm >= 1).mean(), share_any_per_panel_sd=(sp >= 1).mean()))
    st = pd.DataFrame(spec)
    st.to_csv(OUT / "op4_named_runs.csv", index=False)
    out("\nRuns at least as deep as the named runs (depth rule: both seasons at or below the run's less extreme "
        f"value). A simulated panel is itself a {len(seasons)}-season, 20-club league ({len(m)} club-seasons with the observed "
        "membership), so `expected_runs_per_12x20_league` (column name kept) is the mean count per panel. "
        "`mirror_surplus_share_any` = same threshold mirrored to the surplus side (symmetric by construction; a "
        "Monte Carlo check). `share_any_per_panel_sd` = sensitivity with the threshold set in each panel's own SD.\n")
    out(md_table(st, "{:.4f}"))
    # verdict line on tails
    dq = t[t["tail"] == "deficit"].reset_index(drop=True); sq = t[t["tail"] == "surplus"].reset_index(drop=True)
    exceed_d = [r.share_ge_obs < 0.05 for r in dq.itertuples()]
    exceed_s = [r.share_ge_obs < 0.05 for r in sq.itertuples()]
    out("\nDeficit tail vs null (share_ge_obs < 0.05): " + ", ".join(f"k={a} {'EXCEEDS' if e else 'within'} "
        f"({p:.3f})" for a, e, p in zip(dq.k, exceed_d, dq.share_ge_obs)) + ". Surplus tail: " +
        ", ".join(f"k={a} {'EXCEEDS' if e else 'within'} ({p:.3f})" for a, e, p in zip(sq.k, exceed_s, sq.share_ge_obs)) + ".\n")
    both = all(exceed_d) and not any(exceed_s)
    some = any(exceed_d) and not any(exceed_s)
    out(f"**Deficit tail exceeds the null while the surplus tail does not: "
        f"{'YES at every k' if both else ('at some k only' if some else 'NO')}.** "
        f"Pre-registered expectation (Tottenham-depth share < 0.05): share = {st.share_panels_any[0]:.4f} → "
        f"**{'MET' if st.share_panels_any[0] < 0.05 else 'NOT MET'}**.\n")
    return ("; ".join(f"{r.k} {r.side} obs {r.observed} null {r.null_mean:.2f} p {r.share_ge_obs:.3f}" for r in t.rename(columns={"tail": "side"}).itertuples()) +
            f"; THFC-depth any {st.share_panels_any[0]:.4f} E {st.expected_runs_per_12x20_league[0]:.3f}; "
            f"CFC-depth any {st.share_panels_any[1]:.4f} E {st.expected_runs_per_12x20_league[1]:.3f}"), []


if __name__ == "__main__":
    op = sys.argv[1]
    m, seasons = load()
    note, fails = globals()[op](m, seasons)
    with open(REPORT, "a", encoding="utf-8") as f:
        if op == "op1":
            f.write("# Is availability asymmetric? Deficit runs against carry-over\n\n")
        f.write("\n".join(LINES) + "\n\n")
    sys.exit(1 if fails else 0)
