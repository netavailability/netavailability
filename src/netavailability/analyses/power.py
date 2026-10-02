"""Power and a 95% upper bound for a lasting club edge in NETavailability.

Alternative model: c = u_club + e, with u_club ~ N(0, sigma_u^2) fixed per club and e the carry-over step's AR(1).
For each share s = sigma_u^2 / total variance (0.00-0.30 in steps of 0.01; total SD and lag-1 correlation held at the
observed values) 2,000 panels are simulated (fixed seeds, common random numbers across s). Power = share of panels
above the carry-over-only null's 95th percentile (ICC all clubs, ICC six or more seasons, permutation statistic,
split-half r, corrected flags; and any of three at Bonferroni 0.05/3). The 95% upper bound is the s at which fewer
than 5% of panels sit at or below the observed statistic. Self-checks against the run's own inputs (rows for the
configured seasons; lag-1 r and SD recomputed from club_seasons.csv; ICC and split-half against the persistence step's
functions; the re-simulated null against the saved draws) are written to checks.csv (the step continues).
Reads persistence/op1_panel.csv and carryover_null/op3_null_draws.csv in NETAV_ANALYSIS_DIR and imports the carry-over
step; writes checks.csv, null_thresholds.csv, power_by_share.csv, upper_bound_shares.csv, headline.csv, alt_draws.csv
and report.md in power/. Run as: python -m netavailability.analyses.power
"""
import hashlib
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

import os
from . import carryover_null
from . import persistence
from . import selfcheck
BASE = Path(os.environ["NETAV_ANALYSIS_DIR"])
PANEL = BASE / "persistence" / "op1_panel.csv"
CARRY_PY = Path(carryover_null.__file__)
NULLD = BASE / "carryover_null" / "op3_null_draws.csv"
OUT = BASE / "power"
REPORT = OUT / "report.md"
SEED = 20260930
NSIM = 2000
COARSE_GRID = [0, 0.02, 0.05, 0.08, 0.10, 0.15, 0.20, 0.25, 0.30]   # the grid the report tables show
FINE_GRID = [round(0.01 * k, 2) for k in range(31)]  # contains every coarse grid point
PTS, PTS_LO, PTS_HI, PTS_FINAL = 92.0, 63.0, 121.1, 82.5   # points per unit of c (all seasons, its 95% CI; final four seasons): earlier estimates

LINES = []


def out(s=""):
    print(s)
    LINES.append(s)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p):
    try:
        return str(Path(p).relative_to(BASE))
    except ValueError:
        return Path(p).name


def lag_pairs(m):
    """Same pairs as the carry-over step's op3 calibration: row k and the same team's row in the previous season."""
    prev_map = {(ti, s): k for k, (ti, s) in enumerate(zip(m.team_id, m.s_idx))}
    pairs = [(k, prev_map[(ti, s - 1)]) for k, (ti, s) in enumerate(zip(m.team_id, m.s_idx)) if (ti, s - 1) in prev_map]
    return np.array([p[0] for p in pairs]), np.array([p[1] for p in pairs])


def lag_r(Y, cur, prv):
    a = Y[:, cur] - Y[:, cur].mean(1, keepdims=True); b = Y[:, prv] - Y[:, prv].mean(1, keepdims=True)
    return (a * b).sum(1) / np.sqrt((a ** 2).sum(1) * (b ** 2).sum(1))


def all_stats(carry, D, Y, rho):
    f = D.flags(Y, rho)
    return dict(icc_all=D.icc(Y), icc_ge6=D.icc(Y, D.rows6), perm_stat=D.perm_stat(Y),
                split_half_r=D.split_half(Y), flags_raw=carry.nflag(f["lo_raw"], f["hi_raw"]).astype(float),
                flags_adj=carry.nflag(f["lo_adj"], f["hi_adj"]).astype(float))


def crossing_down(xs, ys, level):
    """Largest x before ys first drops below level, linearly interpolated to ys == level."""
    for i in range(1, len(xs)):
        if ys[i] < level <= ys[i - 1]:
            return xs[i - 1] + (ys[i - 1] - level) / (ys[i - 1] - ys[i]) * (xs[i] - xs[i - 1])
    return np.nan


def crossing_up(xs, ys, level):
    """Smallest x at which ys first reaches level, linearly interpolated."""
    if ys[0] >= level:
        return xs[0]
    for i in range(1, len(xs)):
        if ys[i] >= level > ys[i - 1]:
            return xs[i - 1] + (level - ys[i - 1]) / (ys[i] - ys[i - 1]) * (xs[i] - xs[i - 1])
    return np.nan


def main():
    t0 = datetime.now()
    shas0 = {p: sha(p) for p in (PANEL, CARRY_PY, NULLD)}
    carry = carryover_null
    m, seasons = carry.load()
    _, _, rho = carry.lag1(m)
    sd = m.c.std(ddof=1)
    D = carry.Design(m)
    obs = m.c.values[None, :]
    ob = {k: v[0] for k, v in all_stats(carry, D, obs, rho).items()}
    nulld = pd.read_csv(NULLD)

    out("# How big a lasting club edge could hide? Power and upper bound for the persistence statistics\n")
    out("## 1. Provenance\n")
    out(f"Run {t0:%Y-%m-%d %H:%M} (numpy {np.__version__}, pandas {pd.__version__}).\n")
    out(f"Module: `{rel(__file__)}` (sha256 `{sha(__file__)}`).\n")
    out("Inputs (read-only):\n")
    out("| file | sha256 | use |\n|---|---|---|")
    out(f"| `{rel(PANEL)}` | `{shas0[PANEL]}` | panel, {len(m)} club-seasons, `c` = NETavailability − season mean |")
    out(f"| `{rel(CARRY_PY)}` | `{shas0[CARRY_PY]}` | imported: `load`, `lag1`, `Design` (ICC, "
        f"permutation statistic, split-half, flag intervals), `nflag`, `simulate` |")
    out(f"| `{rel(NULLD)}` | `{shas0[NULLD]}` | the carry-over step's {len(nulld):,} carry-over-only null draws (thresholds) |")
    out(f"\nOutputs: CSVs in `{rel(OUT)}/`, this report.\n")

    # ---------- checks ----------
    out("## 2. Self-checks (targets recomputed from this run's inputs)\n")
    fails = []
    rows = []

    def chk(key, label, val, target, tol):
        ok = abs(val - target) <= tol
        rows.append(dict(check=key, quantity=label, value=val, target=target, tolerance=tol,
                         result="PASS" if ok else "FAIL"))
        if not ok:
            fails.append(key)

    R = selfcheck.reference()
    tol = selfcheck.TOL
    sub6 = m[m.groupby("club").season.transform("size") >= 6]
    chk("a", "rows", len(m), R["rows"], 0)
    chk("b", "pooled lag-1 Pearson of c", rho, R["lag1_r_c"], tol)
    chk("c", "SD of c (ddof 1)", sd, R["sd_c"], tol)
    chk("d", "ICC all clubs", ob["icc_all"], persistence.icc_anova(m, "c")["icc"], tol)
    chk("d", "ICC clubs ≥6 seasons", ob["icc_ge6"], persistence.icc_anova(sub6, "c")["icc"], tol)
    chk("d", "odd/even split-half r", ob["split_half_r"], persistence.split_half(m, "c", "parity", "odd v even")["pearson"], tol)
    Yn = carry.simulate(m, rho, sd, nsim=carry.NSIM, seed=carry.SEED)
    rn = all_stats(carry, D, Yn, rho)
    cur, prv = lag_pairs(m)
    rn["lag1_r"] = lag_r(Yn, cur, prv); rn["sd_c"] = Yn.std(1, ddof=1)
    dmax = {k: float(np.max(np.abs(rn[k] - nulld[k].values))) for k in rn}
    chk("e", f"max abs Δ re-simulated vs saved null draws (all {len(rn)} columns, {carry.NSIM} draws, seed {carry.SEED})",
        max(dmax.values()), 0.0, 1e-12)
    ct = pd.DataFrame(rows)
    ct.to_csv(OUT / "checks.csv", index=False)
    out(carry.md_table(ct, "{:.6g}"))
    out("\n(e) per column: " + ", ".join(f"{k} {v:.3g}" for k, v in dmax.items()) +
        f". The carry-over step's `simulate` was called with its own constants (NSIM {carry.NSIM}, SEED {carry.SEED}), the observed ρ "
        f"{rho:.6f} and SD {sd:.6f}; statistics came from its `Design`/`nflag`.\n")
    out(f"Also (not stopping checks): permutation statistic {ob['perm_stat']:.9f} (recomputed from club_seasons.csv: "
        f"{R['perm_stat']:.9f}); corrected-interval flags {ob['flags_adj']:.0f}; uncorrected {ob['flags_raw']:.0f}.\n")
    if fails:
        out(f"**Checks FAILED: {', '.join(fails)} — the targets are recomputed from this run's inputs, so this is a real disagreement; "
            "the run continues and the step exits 1.**\n")
    else:
        out("**All checks PASS.**\n")

    # ---------- simulation under the alternative ----------
    thr95 = {k: np.percentile(nulld[k], 95) for k in ("icc_all", "icc_ge6", "perm_stat", "split_half_r", "flags_adj")}
    thrB = {k: np.percentile(nulld[k], 100 - 5 / 3) for k in ("icc_all", "perm_stat", "split_half_r")}
    size_flags = (nulld.flags_adj >= thr95["flags_adj"]).mean()
    zu = np.random.default_rng(SEED + 1).normal(0, 1, (NSIM, len(D.clubs)))  # one draw of club effects, reused
    Sm, ci = D.Sm, D.ci
    prow, urow, allsims = [], [], []
    for s in FINE_GRID:
        rho_e = (rho - s) / (1 - s)
        sd_e, sd_u = sd * np.sqrt(1 - s), sd * np.sqrt(s)
        E = carry.simulate(m, rho_e, sd_e, nsim=NSIM, seed=SEED)  # AR(1) part, season-centred by the carry-over step
        U = sd_u * zu[:, ci]
        U = U - ((U @ Sm) / np.maximum(Sm.sum(0), 1)) @ Sm.T  # season-centre the club part the same way (centring is linear; an empty gap column divides by 1)
        Y = E + U
        st = all_stats(carry, D, Y, rho)
        lr, sdc = lag_r(Y, cur, prv), Y.std(1, ddof=1)
        anyB = (st["icc_all"] > thrB["icc_all"]) | (st["perm_stat"] > thrB["perm_stat"]) | \
               (st["split_half_r"] > thrB["split_half_r"])
        prow.append(dict(s=s, sigma_u=sd_u, sigma_u_pp=100 * sd_u, rho_e=rho_e,
                         power_icc_all=(st["icc_all"] > thr95["icc_all"]).mean(),
                         power_icc_ge6=(st["icc_ge6"] > thr95["icc_ge6"]).mean(),
                         power_perm=(st["perm_stat"] > thr95["perm_stat"]).mean(),
                         power_split_half=(st["split_half_r"] > thr95["split_half_r"]).mean(),
                         power_flags_adj=(st["flags_adj"] >= thr95["flags_adj"]).mean(),
                         power_any_bonf=anyB.mean(),
                         sim_lag1_r_mean=lr.mean(), sim_sd_c_mean=sdc.mean()))
        urow.append(dict(s=s, sigma_u=sd_u, sigma_u_pp=100 * sd_u,
                         share_icc_all_le_obs=(st["icc_all"] <= ob["icc_all"]).mean(),
                         share_perm_le_obs=(st["perm_stat"] <= ob["perm_stat"]).mean(),
                         share_split_half_le_obs=(st["split_half_r"] <= ob["split_half_r"]).mean(),
                         share_icc_ge6_le_obs=(st["icc_ge6"] <= ob["icc_ge6"]).mean()))
        allsims.append(pd.DataFrame(dict(s=s, sim=np.arange(NSIM), **{k: v for k, v in st.items()},
                                         lag1_r=lr, sd_c=sdc)))
    P, U_ = pd.DataFrame(prow), pd.DataFrame(urow)
    P.to_csv(OUT / "power_by_share.csv", index=False)
    U_.to_csv(OUT / "upper_bound_shares.csv", index=False)
    pd.concat(allsims).to_csv(OUT / "alt_draws.csv", index=False)
    pd.DataFrame([dict(statistic=k, null_p95=thr95[k], null_p98_333=thrB.get(k, np.nan)) for k in thr95]
                 ).to_csv(OUT / "null_thresholds.csv", index=False)

    out("## 3. Method as run\n")
    out(f"Alternative model: c = u_club + e. u_club ~ N(0, σ_u²), one value per club for the whole window; e is the carry-over step's "
        f"AR(1) (its `simulate`, which runs each club's series through all {int(m.s_idx.max()) + 1} start years, keeps the {len(m)} observed "
        f"club-seasons and season-centres). For share s = σ_u²/total variance: total SD fixed at the observed "
        f"{sd:.6f}, so σ_u = {sd:.6f}·√s and SD(e) = {sd:.6f}·√(1−s); total lag-1 r fixed at the observed "
        f"{rho:.6f}, so ρ_e = ({rho:.6f} − s)/(1 − s). u_club is season-centred with the same season means as e "
        "(centring is linear, so centre(e + u) = centre(e) + centre(u)).\n")
    out(f"{NSIM:,} panels per s, seed {SEED}: e from `simulate(seed={SEED})` at every s, and z_club ~ N(0,1) drawn "
        f"once from seed {SEED + 1} and scaled by σ_u at every s (common random numbers across s, so the curves are "
        f"smooth in s). The coarse grid {COARSE_GRID} was run inside a 0.01-step grid 0.00–0.30 ({len(FINE_GRID)} "
        "values), which covers every crossing; tables (i)–(ii) show the coarse grid, the CSVs hold all 31.\n")
    out(f"Corrected-interval flags use the carry-over step's fixed ρ = {rho:.6f} in every panel, as in its null. Power = share of "
        f"panels > the null's 95th percentile (flags: ≥). \"Any\" = ICC-all or permutation or split-half above its "
        f"null 98.333rd percentile (Bonferroni 0.05/3). Null thresholds from the carry-over step's {len(nulld):,} saved draws "
        "(numpy linear percentile):\n")
    tt = pd.DataFrame([dict(statistic=k, observed=ob[k], null_p95=thr95[k], null_p98_333=thrB.get(k, np.nan)) for k in thr95])
    out(carry.md_table(tt, "{:.6g}"))
    out(f"\nThe flag count is discrete: under the null P(flags ≥ {thr95['flags_adj']:.0f}) = {size_flags:.4f}, so that "
        f"test's size is {size_flags:.3f}, not 0.05. Monte-Carlo SE of a share from {NSIM:,} panels: ±{np.sqrt(.25/NSIM):.4f} "
        f"at 0.5, ±{np.sqrt(.8*.2/NSIM):.4f} at 0.8, ±{np.sqrt(.05*.95/NSIM):.4f} at 0.05.\n")
    c0 = P.iloc[0]
    out(f"Calibration: at s = 0 the simulated panels average lag-1 r {c0.sim_lag1_r_mean:.4f} and SD {c0.sim_sd_c_mean:.5f}; "
        f"at s = 0.30, {P.iloc[-1].sim_lag1_r_mean:.4f} and {P.iloc[-1].sim_sd_c_mean:.5f} (observed {rho:.4f}, {sd:.5f}; "
        "season-centring removes a little of both, as in the carry-over step).\n")

    # ---------- results ----------
    out("## 4. Results\n")
    out("### (i) Power by s × statistic\n")
    Pb = P[P.s.isin(COARSE_GRID)].copy()
    out(carry.md_table(Pb[["s", "sigma_u_pp", "rho_e", "power_icc_all", "power_icc_ge6", "power_perm",
                        "power_split_half", "power_flags_adj", "power_any_bonf"]], "{:.3f}"))
    out("\n### (ii) Upper-bound shares: share of panels at or below the observed statistic\n")
    Ub = U_[U_.s.isin(COARSE_GRID)]
    out(carry.md_table(Ub[["s", "sigma_u_pp", "share_icc_all_le_obs", "share_perm_le_obs", "share_split_half_le_obs",
                        "share_icc_ge6_le_obs"]], "{:.3f}"))
    out(f"\n(ICC ≥6 is shown for completeness; the bound uses ICC-all, permutation and split-half. Observed: "
        f"ICC-all {ob['icc_all']:.4f}, permutation {ob['perm_stat']:.6g}, split-half {ob['split_half_r']:.4f}, ICC ≥6 {ob['icc_ge6']:.4f}.)\n")

    xs = P.s.values
    grid_min = lambda col: next((x for x, y in zip(xs, P[col]) if y >= 0.8), np.nan)
    mde = {k: (crossing_up(xs, P[col].values, 0.8), grid_min(col)) for k, col in
           [("ICC-all", "power_icc_all"), ("ICC ≥6", "power_icc_ge6"), ("permutation", "power_perm"),
            ("split-half", "power_split_half"), ("corrected flags", "power_flags_adj"), ("any (Bonferroni)", "power_any_bonf")]}
    ub = {k: crossing_down(xs, U_[col].values, 0.05) for k, col in
          [("ICC-all", "share_icc_all_le_obs"), ("permutation", "share_perm_le_obs"),
           ("split-half", "share_split_half_le_obs"), ("ICC ≥6", "share_icc_ge6_le_obs")]}
    nonmono = {k: bool(((U_[col].values[1:] >= 0.05) & (U_[col].values[:-1] < 0.05)).any()) for k, col in
               [("ICC-all", "share_icc_all_le_obs"), ("permutation", "share_perm_le_obs"),
                ("split-half", "share_split_half_le_obs"), ("ICC ≥6", "share_icc_ge6_le_obs")]}

    def conv(s):
        if np.isnan(s):
            return dict(s=np.nan, sigma_u_pp=np.nan, pts_92=np.nan, pts_63=np.nan, pts_121=np.nan, pts_82_5=np.nan)
        su = sd * np.sqrt(s)
        return dict(s=s, sigma_u_pp=100 * su, pts_92=PTS * su, pts_63=PTS_LO * su, pts_121=PTS_HI * su,
                    pts_82_5=PTS_FINAL * su)

    hrows = []
    for k, (si, sg) in mde.items():
        hrows.append(dict(quantity="MDE at 80% power", statistic=k, grid_min_s=sg, **conv(si)))
    for k, si in ub.items():
        hrows.append(dict(quantity="95% upper bound", statistic=k, grid_min_s=np.nan, **conv(si)))
    H = pd.DataFrame(hrows)
    H.to_csv(OUT / "headline.csv", index=False)
    out("### (iii) Headline: MDE at 80% power and 95% upper bound\n")
    out("s interpolated linearly on the 0.01 grid; `grid_min_s` = smallest grid s with power ≥ 0.80. σ_u in pp = 100·σ_u. "
        f"Points a season = σ_u × {PTS} (12-season coefficient; range {PTS_LO}–{PTS_HI} from its 95% CI) and × {PTS_FINAL} "
        "(FINAL). A club one σ_u above average has an edge of exactly σ_u: the pp and points columns are that club's edge. "
        "Headline statistic: ICC-all (the persistence statistics' primary one).\n")
    out(carry.md_table(H[["quantity", "statistic", "s", "grid_min_s", "sigma_u_pp", "pts_92", "pts_63", "pts_121", "pts_82_5"]],
                    "{:.3f}"))
    out(f"\nBlank = not reached on s ≤ 0.30, the top of the admissible range (ρ_e = (ρ − s)/(1 − s) ≥ 0 needs s ≤ {rho:.3f}); for those statistics the MDE or bound is > 0.30, i.e. σ_u > {conv(0.30)['sigma_u_pp']:.2f} pp (> {conv(0.30)['pts_92']:.1f} points)." +
        ("" if not any(nonmono.values()) else " Upper-bound share re-crosses 0.05 upward for: " +
         ", ".join(k for k, v in nonmono.items() if v) + " (first downward crossing used).") + "\n")

    # ---------- verdict ----------
    hm, hu = conv(mde["ICC-all"][0]), conv(ub["ICC-all"])
    am = conv(mde["any (Bonferroni)"][0])
    exp_mde = 2 <= hm["sigma_u_pp"] <= 3
    exp_ub = 1.5 <= hu["sigma_u_pp"] <= 2.5
    out("## 5. Verdict\n")
    out(f"On ICC-all, a lasting club edge with SD σ_u = {hm['sigma_u_pp']:.2f} pp (s = {hm['s']:.3f} of the variance of c; "
        f"≈ {hm['pts_92']:.1f} points a season at {PTS}, {hm['pts_63']:.1f}–{hm['pts_121']:.1f} over the coefficient's CI, "
        f"{hm['pts_82_5']:.1f} at {PTS_FINAL}) is detected with 80% probability; the Bonferroni any-of-three test reaches 80% "
        f"at σ_u = {am['sigma_u_pp']:.2f} pp (s = {am['s']:.3f}). The observed ICC-all {ob['icc_all']:.4f} is below "
        f"95% of simulated panels (fewer than 5% at or below it) once σ_u exceeds {hu['sigma_u_pp']:.2f} pp (s = {hu['s']:.3f}; ≈ {hu['pts_92']:.1f} points a season, "
        f"{hu['pts_63']:.1f}–{hu['pts_121']:.1f}; {hu['pts_82_5']:.1f} at {PTS_FINAL}): that is the 95% upper bound. "
        f"The permutation and split-half statistics are weaker: at s = 0.30 (σ_u {conv(0.30)['sigma_u_pp']:.2f} pp) their power is "
        f"{P.power_perm.iloc[-1]:.3f} and {P.power_split_half.iloc[-1]:.3f}, and {U_.share_perm_le_obs.iloc[-1]:.3f} and "
        f"{U_.share_split_half_le_obs.iloc[-1]:.3f} of panels still sit at or below the observed values, so neither rules out "
        f"any s ≤ 0.30; ICC ≥6 gives a bound of {conv(ub['ICC ≥6'])['sigma_u_pp']:.2f} pp. At s = 0 the ICC-all test's "
        f"simulated size is {P.power_icc_all.iloc[0]:.3f} (nominal 0.05). Expected result: MDE 2–3 pp → "
        f"{'HELD' if exp_mde else 'DID NOT HOLD'} ({hm['sigma_u_pp']:.2f} pp); upper bound ≈ 2 pp (taken as 1.5–2.5) → "
        f"{'HELD' if exp_ub else 'DID NOT HOLD'} ({hu['sigma_u_pp']:.2f} pp, {hu['pts_92']:.1f} points vs ≈ 2 expected).\n")
    nw = {7: "seven", 8: "eight", 11: "eleven", 12: "twelve"}.get(len(seasons), str(len(seasons)))
    out(f"Paper sentence: \"Over {nw} seasons we would have detected a lasting club edge of {hm['sigma_u_pp']:.1f} pp "
        f"(≈ {hm['pts_92']:.1f} points a season) with 80% probability; we found none, and the data rule out a lasting edge "
        f"larger than {hu['sigma_u_pp']:.1f} pp (≈ {hu['pts_92']:.1f} points a season) at 95%.\"\n")

    t2 = datetime.now()
    shas1 = {p: sha(p) for p in (PANEL, CARRY_PY, NULLD)}
    same = shas0 == shas1
    out(f"Inputs unchanged after the run (sha256 re-read): {same}. Elapsed {int((t2 - t0).total_seconds())} s.\n")
    out("Files written: `" + "`, `".join(rel(OUT / f) for f in (
        "checks.csv", "null_thresholds.csv", "power_by_share.csv", "upper_bound_shares.csv", "headline.csv",
        "alt_draws.csv")) + f"`, `{rel(REPORT)}`.\n")
    REPORT.write_text("\n".join(LINES) + "\n", encoding="utf-8")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
