"""Club persistence beyond one-season carry-over.

A club that does well one season tends to do well the next simply because the same squad carries over. This step
asks whether the persistence statistics of the persistence step exceed what that carry-over alone produces:
  op1  self-checks of the persistence panel against the run's own inputs (rows for the configured seasons, clubs,
       the centring, the lag-1 slope recomputed from sums, and this module's vectorised estimators against the
       persistence step's functions on the same panel; a failure exits 1), and the pooled lag-1 Pearson correlation
       rho used below
  op2  club intervals corrected for the lag-1 correlation (effective n = n (1 - rho) / (1 + rho))
  op3  the carry-over-only null: per club a stationary AR(1) series with the observed rho and SD, no club effect,
       run through every season (also those a club was absent), observed club-seasons kept, season-centred;
       5,000 panels, fixed seed; the share of panels at or above each observed statistic
The module also provides the shared pieces the asymmetry, two-season-run and power steps import: load, lag1, Design
(ICC, permutation statistic, split-half, flag intervals), nflag, simulate, md_table, NSIM, SEED.
Reads persistence/op1_panel.csv in NETAV_ANALYSIS_DIR; writes its CSVs and report.md in carryover_null/.
Run as: python -m netavailability.analyses.carryover_null op1|op2|op3
"""
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf

import os
from . import selfcheck
BASE = Path(os.environ["NETAV_ANALYSIS_DIR"])
PANEL = BASE / "persistence" / "op1_panel.csv"
OUT = BASE / "carryover_null"
REPORT = OUT / "report.md"
SEED = 20260930
NSIM = 5000

LINES = []


def out(s=""):
    print(s)
    LINES.append(s)


def md_table(df, floatfmt="{:.4f}"):
    cols = list(df.columns)
    rows = ["| " + " | ".join(str(c) for c in cols) + " |",
            "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, (float, np.floating)):
                cells.append("" if pd.isna(v) else floatfmt.format(v))
            else:
                cells.append(str(v))
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join(rows)


def load():
    m = pd.read_csv(PANEL)
    seasons = sorted(m.season.unique())
    return m, seasons


def lag1(m):
    prev = m[["team_id", "s_idx", "c"]].copy()
    prev["s_idx"] += 1
    j = m.merge(prev, on=["team_id", "s_idx"], suffixes=("", "_prev"))
    fit = smf.ols("c ~ c_prev", j).fit()
    r = stats.pearsonr(j.c, j.c_prev)[0]
    return j, fit, r


# ---------- vectorised statistics (rows = simulations, columns = panel rows) ----------
class Design:
    """Fixed panel structure: club/season membership of the panel rows."""

    def __init__(self, m):
        self.clubs = sorted(m.club.unique())
        self.ci = m.club.map({c: i for i, c in enumerate(self.clubs)}).values
        self.si = m.s_idx.values
        K, S = len(self.clubs), m.s_idx.max() + 1
        self.G = np.zeros((len(m), K)); self.G[np.arange(len(m)), self.ci] = 1
        self.Sm = np.zeros((len(m), S)); self.Sm[np.arange(len(m)), self.si] = 1
        self.n = self.G.sum(0)
        self.ge6 = self.n >= 6
        self.rows6 = self.ge6[self.ci]
        # odd/even split-half as in the persistence step: half A = s_idx even (the first season, the third, ...)
        A = (self.si % 2 == 0)
        self.GA = self.G * A[:, None]; self.GB = self.G * (~A)[:, None]
        nA, nB = self.GA.sum(0), self.GB.sum(0)
        self.sh = (nA >= 3) & (nB >= 3)
        self.nA, self.nB = nA, nB

    def icc(self, Y, rows=None):
        if rows is None:
            Yr, G = Y, self.G
        else:
            Yr = Y[:, rows]
            G = self.G[rows]
            G = G[:, G.sum(0) > 0]
        n = G.sum(0); k = len(n); N = n.sum()
        means = (Yr @ G) / n
        grand = Yr.mean(1, keepdims=True)
        ssb = (n * (means - grand) ** 2).sum(1)
        ssw = ((Yr - means @ G.T) ** 2).sum(1)
        msb, msw = ssb / (k - 1), ssw / (N - k)
        n0 = (N - (n ** 2).sum() / N) / (k - 1)
        sb2 = np.maximum((msb - msw) / n0, 0.0)
        return sb2 / (sb2 + msw)

    def perm_stat(self, Y):
        means = (Y @ self.G) / self.n
        w = self.n[self.ge6]; mm = means[:, self.ge6]
        mu = (mm * w).sum(1, keepdims=True) / w.sum()
        return ((mm - mu) ** 2 * w).sum(1) / w.sum()

    def split_half(self, Y):
        a = ((Y @ self.GA) / np.where(self.nA > 0, self.nA, 1))[:, self.sh]
        b = ((Y @ self.GB) / np.where(self.nB > 0, self.nB, 1))[:, self.sh]
        a = a - a.mean(1, keepdims=True); b = b - b.mean(1, keepdims=True)
        return (a * b).sum(1) / np.sqrt((a ** 2).sum(1) * (b ** 2).sum(1))

    def flags(self, Y, rho):
        """Club intervals for clubs >=6 seasons: raw (t(n-1), sd/sqrt n) and AR-adjusted.
        Returns (mean, sd, n, lo_raw, hi_raw, lo_adj, hi_adj) arrays shaped (sims, clubs>=6)."""
        n = self.n[self.ge6]
        means = ((Y @ self.G) / self.n)[:, self.ge6]
        ss = ((Y - ((Y @ self.G) / self.n) @ self.G.T) ** 2) @ self.G
        sd = np.sqrt(ss[:, self.ge6] / (n - 1))
        tr = stats.t.ppf(0.975, n - 1)
        se = sd / np.sqrt(n)
        neff = n * (1 - rho) / (1 + rho)
        ta = stats.t.ppf(0.975, np.maximum(neff - 1, 1))
        sea = sd / np.sqrt(neff)
        return dict(n=n, neff=neff, mean=means, sd=sd, se_raw=se, t_raw=tr, se_adj=sea, t_adj=ta,
                    lo_raw=means - tr * se, hi_raw=means + tr * se,
                    lo_adj=means - ta * sea, hi_adj=means + ta * sea)


def nflag(lo, hi):
    return ((lo > 0) | (hi < 0)).sum(1)


# ---------- ops ----------
def op1(m, seasons):
    out("## 1. Provenance and checks\n")
    out(f"Run {datetime.now():%Y-%m-%d %H:%M}.\n")
    out(f"Input (read-only): `persistence/{PANEL.name}` — {len(m)} rows. It is the panel the persistence step built; its "
        "`c` column is the season-centred NETavailability (club value − that season's 20-club mean).\n")
    fails = []
    R = selfcheck.reference()
    tol = selfcheck.TOL
    per = m.groupby("season").size()
    ok_a = len(m) == R["rows"] and (per == selfcheck.CLUBS_PER_SEASON).all() and seasons == R["seasons"] and m.club.nunique() == R["clubs"]
    out(f"**(a)** rows {len(m)} (configured: {len(R['seasons'])} seasons × {selfcheck.CLUBS_PER_SEASON} = {R['rows']}); seasons "
        f"{len(seasons)} ({seasons[0]}–{seasons[-1]}); per-season counts {sorted(set(per.values))}; clubs {m.club.nunique()} "
        f"(club_seasons.csv: {R['clubs']}) → **{'PASS' if ok_a else 'FAIL'}**\n")
    if not ok_a: fails.append("a")
    c2 = m.NETavailability - m.groupby("season").NETavailability.transform("mean")
    dmax = (c2 - m.c).abs().max()
    ok_b = dmax <= 1e-9
    out(f"**(b)** recomputed season-centred value vs panel column `c`: max |difference| = {dmax:.3g} "
        f"(tolerance 1e-9) → **{'PASS' if ok_b else 'FAIL'}**\n")
    if not ok_b: fails.append("b")
    j, fit, r = lag1(m)
    b = fit.params.c_prev
    ok_c = abs(b - R["lag1_slope_c"]) <= tol and len(j) == R["pairs"]
    out(f"**(c)** OLS of c(t) on c(t−1), clubs in consecutive seasons: n = {len(j)} pairs, slope = **{b:.6f}** "
        f"(SE {fit.bse.c_prev:.4f}); recomputed from club_seasons.csv: {R['pairs']} pairs, slope {R['lag1_slope_c']:.6f}, "
        f"tolerance {tol:g} → **{'PASS' if ok_c else 'FAIL'}**. "
        f"Pooled lag-1 Pearson correlation on the same pairs: **ρ = {r:.6f}**. This ρ is used in Ops 2 and 3 "
        f"(the pooled lag-1 correlation; it differs from the slope by {r-b:+.4f}).\n")
    if not ok_c: fails.append("c")
    D = Design(m)
    obs = D.perm_stat(m.c.values[None, :])[0]
    ok_d = abs(obs - R["perm_stat"]) <= tol
    out(f"**(d)** the persistence step's permutation statistic (season-count-weighted variance of club means, {D.ge6.sum()} clubs ≥6 "
        f"seasons): **{obs:.10f}**; recomputed from club_seasons.csv: {R['perm_stat']:.10f}, tolerance {tol:g} → "
        f"**{'PASS' if ok_d else 'FAIL'}**\n")
    if not ok_d: fails.append("d")
    # this module's vectorised estimators against the persistence step's own functions on the same panel
    from . import persistence as P
    Y = m.c.values[None, :]
    fr = D.flags(Y, r)
    sub6 = m[m.groupby("club").season.transform("size") >= 6]
    sh = P.split_half(m, "c", "parity", "odd v even")
    icc_all, icc6, shr, nfl = D.icc(Y)[0], D.icc(Y, D.rows6)[0], D.split_half(Y)[0], int(nflag(fr["lo_raw"], fr["hi_raw"])[0])
    ref_all, ref6 = P.icc_anova(m, "c")["icc"], P.icc_anova(sub6, "c")["icc"]
    ref_fl = 0
    for _, g in sub6.groupby("club"):
        se = g.c.std(ddof=1) / np.sqrt(len(g)); tq = stats.t.ppf(0.975, len(g) - 1)
        ref_fl += int(g.c.mean() - tq * se > 0 or g.c.mean() + tq * se < 0)
    ok_e = (abs(icc_all - ref_all) <= tol and abs(icc6 - ref6) <= tol and abs(shr - sh["pearson"]) <= tol
            and int(D.sh.sum()) == sh["n"] and nfl == ref_fl)
    out(f"**(e)** this module's vectorised estimators against the persistence step's functions on the same panel: "
        f"ICC all {icc_all:.6f} ({ref_all:.6f}), ICC ≥6 {icc6:.6f} ({ref6:.6f}), odd/even r {shr:.6f} on {D.sh.sum()} clubs "
        f"({sh['pearson']:.6f}, n {sh['n']}), uncorrected flags {nfl} ({ref_fl}); tolerance {tol:g} → **{'PASS' if ok_e else 'FAIL'}**\n")
    if not ok_e: fails.append("e")
    pd.DataFrame([dict(rows=len(m), seasons=len(seasons), clubs=m.club.nunique(), max_abs_diff_c=dmax,
                       lag1_pairs=len(j), lag1_slope=b, lag1_slope_se=fit.bse.c_prev, lag1_pearson_rho=r,
                       perm_stat=obs, sd_c=m.c.std(ddof=1), checks="PASS" if not fails else "FAIL " + ",".join(fails))]
                 ).to_csv(OUT / "op1_checks.csv", index=False)
    out(f"Self-checks against the run's own inputs: {'ALL PASS' if not fails else 'FAILED ' + ','.join(fails)}\n")
    return (("ALL PASS" if not fails else "FAIL " + ",".join(fails)) +
            f"; slope {b:.4f}; rho {r:.4f}; perm stat {obs:.9f}; maxdiff c {dmax:.2g}"), fails


def op2(m, seasons):
    out("## 2. Corrected club intervals\n")
    _, _, rho = lag1(m)
    D = Design(m)
    f = D.flags(m.c.values[None, :], rho)
    ge6 = [c for c, k in zip(D.clubs, D.ge6) if k]
    t = pd.DataFrame(dict(club=ge6, seasons=f["n"].astype(int), mean=f["mean"][0], sd=f["sd"][0],
                          se_raw=f["se_raw"][0], lo_raw=f["lo_raw"][0], hi_raw=f["hi_raw"][0],
                          n_eff=f["neff"], df_adj=np.maximum(f["neff"] - 1, 1), se_adj=f["se_adj"][0],
                          lo_adj=f["lo_adj"][0], hi_adj=f["hi_adj"][0]))
    t["flag_raw"] = np.where(t.lo_raw > 0, "ABOVE", np.where(t.hi_raw < 0, "BELOW", ""))
    t["flag_adj"] = np.where(t.lo_adj > 0, "ABOVE", np.where(t.hi_adj < 0, "BELOW", ""))
    t = t.sort_values("mean", ascending=False).reset_index(drop=True)
    t.to_csv(OUT / "op2_corrected_intervals.csv", index=False)
    fac = (1 - rho) / (1 + rho)
    out(f"ρ = {rho:.4f} (pooled lag-1 Pearson, step 1). Effective n = n × (1 − ρ)/(1 + ρ) = n × {fac:.4f}; "
        f"adjusted SE = sd/√n_eff; t on max(n_eff − 1, 1) df (fractional df). "
        f"Raw interval = the persistence step's: mean ± t(n−1)·sd/√n. The adjustment widens each interval by the factor "
        f"t_adj·√n / (t_raw·√n_eff), e.g. {(f['t_adj'][list(f['n']).index(int(max(f['n'])))] * np.sqrt(int(max(f['n'])))) / (stats.t.ppf(0.975, int(max(f['n'])) - 1) * np.sqrt(int(max(f['n'])) * fac)):.2f}× "
        f"for {int(max(f['n']))} seasons and {(f['t_adj'][list(f['n']).index(6)] * np.sqrt(6)) / (stats.t.ppf(0.975, 5) * np.sqrt(6 * fac)):.2f}× for 6.\n")   # example at the longest club
    out(md_table(t, "{:.4f}"))
    nr, na = (t.flag_raw != "").sum(), (t.flag_adj != "").sum()
    exp = 0.05 * len(t)
    out(f"\nFlags: raw {nr} of {len(t)} ({(t.flag_raw=='ABOVE').sum()} above, {(t.flag_raw=='BELOW').sum()} below); "
        f"adjusted **{na} of {len(t)}** ({(t.flag_adj=='ABOVE').sum()} above, {(t.flag_adj=='BELOW').sum()} below"
        f"{': ' + ', '.join(f'{c} {g}' for c, g in zip(t.club, t.flag_adj) if g) if na else ''}).\n")
    out(f"Expected by chance at a nominal 5% two-sided level: {exp:.2f} of {len(t)}. Binomial P(≥{na}) = "
        f"{stats.binom.sf(na-1, len(t), 0.05) if na > 0 else 1.0:.4g} (assumes the {len(t)} intervals are independent and exactly "
        f"5%; the adjusted intervals are approximate, and the clubs share season-centring, so step 3(d) gives the "
        f"simulation-based chance benchmark).\n")
    return (f"rho {rho:.4f}; flags raw {nr}/{len(t)}, adjusted {na}/{len(t)} "
            f"({'; '.join(f'{c} {g}' for c, g in zip(t.club, t.flag_adj) if g) or 'none'}); expected {exp:.2f}"), []


def simulate(m, rho, sd, nsim=NSIM, seed=SEED):
    """AR(1), no club effect, every club over every season; keep present cells; season-centre."""
    rng = np.random.default_rng(seed)
    K = m.club.nunique(); S = int(m.s_idx.max()) + 1   # seasons by start year incl. an empty column for a season left out (gap = two AR steps)
    clubs = sorted(m.club.unique())
    ci = m.club.map({c: i for i, c in enumerate(clubs)}).values
    si = m.s_idx.values
    X = np.empty((nsim, K, S))
    X[:, :, 0] = rng.normal(0, sd, (nsim, K))
    innov = rng.normal(0, sd * np.sqrt(1 - rho ** 2), (nsim, K, S - 1))
    for s in range(1, S):
        X[:, :, s] = rho * X[:, :, s - 1] + innov[:, :, s - 1]
    Y = X[:, ci, si]
    Sm = np.zeros((len(m), S)); Sm[np.arange(len(m)), si] = 1
    Y = Y - ((Y @ Sm) / np.maximum(Sm.sum(0), 1)) @ Sm.T   # an empty gap column divides by 1, not 0
    return Y


def op3(m, seasons):
    out("## 3. Carry-over-only null\n")
    _, _, rho = lag1(m)
    sd = m.c.std(ddof=1)
    D = Design(m)
    Y = simulate(m, rho, sd)
    out(f"{NSIM:,} simulated panels, seed {SEED}. No club effect. For each of the {m.club.nunique()} clubs a stationary AR(1) series "
        f"over the {int(m.s_idx.max()) + 1} start years {seasons[0][:4]}/{seasons[0][7:]}–{seasons[-1][:4]}/{seasons[-1][7:]} with lag-1 coefficient ρ = {rho:.4f} and marginal SD {sd:.5f} "
        f"(observed SD of c, ddof 1): x₁ ~ N(0, SD²), xₜ = ρ·xₜ₋₁ + N(0, SD²(1−ρ²)). The series runs through seasons "
        f"a club was absent, so a club's seasons either side of a gap correlate at ρ^gap. Only the {len(m)} observed "
        "club-seasons are kept, then each season is centred on its 20-club mean exactly as the real data are. "
        "The step 2 correction uses the fixed step 1 ρ in every simulated panel.\n")
    # calibration: lag-1 slope/corr and SD in the simulated centred panels
    prev_map = {(ti, s): k for k, (ti, s) in enumerate(zip(m.team_id, m.s_idx))}
    pairs = [(k, prev_map[(ti, s - 1)]) for k, (ti, s) in enumerate(zip(m.team_id, m.s_idx)) if (ti, s - 1) in prev_map]
    cur, prv = np.array([p[0] for p in pairs]), np.array([p[1] for p in pairs])
    a = Y[:, cur] - Y[:, cur].mean(1, keepdims=True); b = Y[:, prv] - Y[:, prv].mean(1, keepdims=True)
    sim_r = (a * b).sum(1) / np.sqrt((a ** 2).sum(1) * (b ** 2).sum(1))
    sim_sd = Y.std(1, ddof=1)
    out(f"Calibration: in the simulated centred panels the pooled lag-1 correlation on the same {len(pairs)} pairs "
        f"averages {sim_r.mean():.4f} (5th–95th pct {np.percentile(sim_r,5):.3f}–{np.percentile(sim_r,95):.3f}; "
        f"observed {rho:.4f}) and the SD of the centred value averages {sim_sd.mean():.5f} (observed {sd:.5f}). "
        "Season-centring removes a little of both, so the null reproduces slightly less carry-over than observed "
        "on average.\n")
    obs = m.c.values[None, :]
    fo, fs = D.flags(obs, rho), D.flags(Y, rho)
    stats_ = [
        ("(a) ICC, all 35 clubs", D.icc(obs)[0], D.icc(Y)),
        ("(a) ICC, 19 clubs ≥6 seasons", D.icc(obs, D.rows6)[0], D.icc(Y, D.rows6)),
        ("(b) permutation statistic (weighted var of club means, ≥6 seasons)", D.perm_stat(obs)[0], D.perm_stat(Y)),
        (f"(c) odd v even split-half Pearson r ({D.sh.sum()} clubs)", D.split_half(obs)[0], D.split_half(Y)),
        ("(d) clubs flagged, uncorrected intervals", float(nflag(fo["lo_raw"], fo["hi_raw"])[0]),
         nflag(fs["lo_raw"], fs["hi_raw"]).astype(float)),
        ("(d) clubs flagged, step 2 corrected intervals", float(nflag(fo["lo_adj"], fo["hi_adj"])[0]),
         nflag(fs["lo_adj"], fs["hi_adj"]).astype(float)),
    ]
    rows = []
    for name, o, s in stats_:
        k = (s >= o - 1e-15).sum()
        rows.append(dict(statistic=name, observed=o, sim_mean=s.mean(), sim_median=np.median(s),
                         sim_p95=np.percentile(s, 95), share_ge_obs=k / NSIM, p_plus1=(k + 1) / (NSIM + 1)))
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "op3_null_summary.csv", index=False)
    out(md_table(t, "{:.6g}"))
    out(f"\n`share_ge_obs` = share of the {NSIM:,} simulations at or above the observed value (the p-value against "
        "carry-over only); `p_plus1` = (k+1)/(N+1) for reference. ICCs are truncated at 0 as in "
        "the persistence step, so many simulated ICCs are exactly 0.\n")
    icc0 = (stats_[0][2] == 0).mean()
    out(f"Share of simulated panels with ICC (all clubs) truncated to 0: {icc0:.3f}.\n")
    for key, arr in (("raw", nflag(fs["lo_raw"], fs["hi_raw"])), ("adj", nflag(fs["lo_adj"], fs["hi_adj"]))):
        vc = pd.Series(arr).value_counts().sort_index()
        out(f"- Distribution of simulated flag counts ({'uncorrected' if key=='raw' else 'corrected'}): " +
            ", ".join(f"{int(i)}: {v/NSIM:.3f}" for i, v in vc.items()))
    out()
    sims = pd.DataFrame({"icc_all": stats_[0][2], "icc_ge6": stats_[1][2], "perm_stat": stats_[2][2],
                         "split_half_r": stats_[3][2], "flags_raw": stats_[4][2].astype(int),
                         "flags_adj": stats_[5][2].astype(int), "lag1_r": sim_r, "sd_c": sim_sd})
    sims.index.name = "sim"
    sims.to_csv(OUT / "op3_null_draws.csv")
    return "; ".join(f"{n.split(' ')[0]}{'' if i not in (0,1) else ('all' if i==0 else '>=6')} obs {o:.4g} p {k:.4f}"
                     for i, (n, o, k) in enumerate(zip(t.statistic, t.observed, t.share_ge_obs))) + \
        f"; sim lag1 r mean {sim_r.mean():.3f}", []


if __name__ == "__main__":
    op = sys.argv[1]
    m, seasons = load()
    note, fails = globals()[op](m, seasons)
    with open(REPORT, "a", encoding="utf-8") as f:
        if op == "op1":
            f.write("# Club persistence beyond one-season carry-over\n\n")
        f.write("\n".join(LINES) + "\n\n")
    sys.exit(1 if fails else 0)
