"""How unusual is Tottenham Hotspur's availability? Two scales, two chance models.

Scales per club-season: c = NETavailability - season mean (% scale) and m = season mean A_pm - A_pm with
A_pm = NETabsence / 38 (minutes scale; both "higher = better"). Chance models: (N) a normal AR(1) per club with the
scale's lag-1 correlation and SD, no club effect (the carry-over step's model, re-implemented with the same draw order),
and (Q) a shape-preserving AR(1) on normal scores mapped back through the empirical quantiles; each simulated league is
season-centred; 5,000 leagues, fixed seed.
  op1  self-checks against the run's own inputs (rows, seasons, clubs, pairs, the named clubs' values and the lag-1
       correlations recomputed from club_seasons.csv and the configured seasons; a failure exits 1); the shape of
       each scale; the extremes
  op2  calibration of the four configurations and a validation of (N) on the % scale: the Tottenham-depth shares
       from this module's re-implementation against the carry-over step's own `simulate` on the same inputs (exits 1
       when they differ)
  op3  tests T1 (single season), T2 (two-season sum), T3 (two seasons, milder season), T4 (gap to 19th), each with
       its surplus mirror
  op4  verdict: "rare by chance" only if the share is below 0.05 under both models on both scales; the headline
       quotes the largest of the four shares
Reads club_seasons.csv in NETAV_ANALYSIS_DIR; writes its CSVs and report.md in extremity/.
Run as: python -m netavailability.analyses.extremity op1|op2|op3|op4
"""
import hashlib
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

import os
from . import carryover_null as carry
from . import selfcheck
BASE = Path(os.environ["NETAV_ANALYSIS_DIR"])
INPUT = BASE / "club_seasons.csv"
OUT = BASE / "extremity"
REPORT = OUT / "report.md"
SEED = 20260930
NSIM = 5000
EPS = 1e-9
TOT, CHE = "Tottenham Hotspur", "Chelsea"
TOT_S, CHE_S = ("2024/2025", "2025/2026"), ("2022/2023", "2023/2024")
SCALES = {"pct": ("c", "% scale (c = NETavailability − season mean)"),
          "min": ("m", "minutes scale (m = season mean A_pm − A_pm, A_pm = NETabsence ÷ 38)")}
MODELS = {"N": "normal AR(1)", "Q": "shape-preserving (normal scores)"}
CONFIGS = [(s, k) for s in SCALES for k in MODELS]

LINES = []


def out(s=""):
    print(s)
    LINES.append(s)


def md_table(df, floatfmt="{:.4f}"):
    cols = list(df.columns)
    rows = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
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


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def short(s):
    return f"{s[:4]}/{s[-2:]}"


# ---------------------------------------------------------------- data
def load():
    m = pd.read_csv(INPUT)
    seasons = sorted(m.season.unique())
    m["s_idx"] = m.season.str[:4].astype(int) - int(seasons[0][:4])   # index by start year, so 2019/20 -> 2021/22 is a two-year gap when 2020/21 is excluded
    m["c"] = m.NETavailability - m.groupby("season").NETavailability.transform("mean")
    m["A_pm"] = m.NETabsence / 38
    m["m"] = m.groupby("season").A_pm.transform("mean") - m.A_pm
    return m, seasons


def pairs_idx(m):
    """Row indices (cur, prev): same team_id in consecutive seasons."""
    pos = {(ti, s): k for k, (ti, s) in enumerate(zip(m.team_id, m.s_idx))}
    pr = [(k, pos[(ti, s - 1)]) for k, (ti, s) in enumerate(zip(m.team_id, m.s_idx)) if (ti, s - 1) in pos]
    return np.array([p[0] for p in pr]), np.array([p[1] for p in pr])


def lag1(m, v):
    cur, prv = pairs_idx(m)
    return stats.pearsonr(v[cur], v[prv])[0]


def normal_scores(v):
    """Rank-based inverse normal (Blom plotting position (r − 3/8)/(n + 1/4)); ties get the average rank."""
    r = stats.rankdata(v, method="average")
    return stats.norm.ppf((r - 0.375) / (len(v) + 0.25))


def club_val(m, col, club, season):
    return float(m.loc[(m.club == club) & (m.season == season), col].iloc[0])


def centre(m, Y):
    si = m.s_idx.values
    S = si.max() + 1
    Sm = np.zeros((len(m), S)); Sm[np.arange(len(m)), si] = 1
    return Y - ((Y @ Sm) / np.maximum(Sm.sum(0), 1)) @ Sm.T   # an empty gap column divides by 1, not 0


def ar1_panels(m, rho, sd, nsim=NSIM, seed=SEED):
    """Stationary AR(1) per club (clubs sorted by name) over every start year of the set, no club effect; returns the observed
    club-season cells, uncentred. Same draw order as the carry-over step's `simulate` (fresh generator)."""
    rng = np.random.default_rng(seed)
    K = m.club.nunique(); S = int(m.s_idx.max()) + 1   # seasons by start year incl. an empty column for a season left out
    clubs = sorted(m.club.unique())
    ci = m.club.map({c: i for i, c in enumerate(clubs)}).values
    si = m.s_idx.values
    X = np.empty((nsim, K, S))
    X[:, :, 0] = rng.normal(0, sd, (nsim, K))
    innov = rng.normal(0, sd * np.sqrt(1 - rho ** 2), (nsim, K, S - 1))
    for s in range(1, S):
        X[:, :, s] = rho * X[:, :, s - 1] + innov[:, :, s - 1]
    return X[:, ci, si]


def params(m, scale):
    col = SCALES[scale][0]
    v = m[col].values
    z = normal_scores(v)
    return dict(rho=lag1(m, v), sd=float(np.std(v, ddof=1)), rho_q=lag1(m, z), z=z, v=v)


def simulate(m, scale, model):
    p = params(m, scale)
    if model == "N":
        return centre(m, ar1_panels(m, p["rho"], p["sd"]))
    Z = ar1_panels(m, p["rho_q"], 1.0)
    o = np.argsort(p["z"], kind="stable")
    return centre(m, np.interp(Z, p["z"][o], p["v"][o]))  # np.interp clamps beyond the ends to observed min/max


def pooled_r(m, Y):
    cur, prv = pairs_idx(m)
    a = Y[:, cur] - Y[:, cur].mean(1, keepdims=True); b = Y[:, prv] - Y[:, prv].mean(1, keepdims=True)
    return (a * b).sum(1) / np.sqrt((a ** 2).sum(1) * (b ** 2).sum(1))


def season_gaps(m, V):
    """V: (nsim, club-seasons). Returns (bottom gaps, top gaps), each (nsim, seasons): 19th − 20th and 1st − 2nd on the measure."""
    bot, top = [], []
    for s in sorted(m.s_idx.unique()):   # observed seasons only
        cols = np.where(m.s_idx.values == s)[0]
        srt = np.sort(V[:, cols], axis=1)
        bot.append(srt[:, 1] - srt[:, 0]); top.append(srt[:, -1] - srt[:, -2])
    return np.stack(bot, 1), np.stack(top, 1)


# ---------------------------------------------------------------- ops
def op1(m, seasons):
    out("## 1. Provenance and checks\n")
    out(f"Run {datetime.now():%Y-%m-%d %H:%M}.\n")
    out(f"Input (read-only): `{INPUT.name}` — sha256 {sha(INPUT)}. Re-checked in step 4.\n")
    out("Definitions per club-season: c = NETavailability − season mean NETavailability (% scale); A_pm = "
        "NETabsence ÷ 38; m = season mean A_pm − A_pm (minutes scale, minutes lost per match relative to the season "
        "average; positive = fewer minutes lost). Both are \"higher = better\". Pairs = same `team_id` in "
        "consecutive seasons.\n")
    out("Expected result (written before the first run): on the % scale the tests reproduce the earlier "
        "shares. On the minutes scale Tottenham 2025/26 is the most extreme club-season of the 240, m is negatively "
        "skewed, and shares are lower than on the % scale under the normal model but closer to the % shares under "
        "the shape-preserving model. No expectation is set for whether anything falls below 0.05.\n")
    out("Claim rule (fixed before the first run): \"rare by chance\" for a test only if the share of "
        "simulated leagues is below 0.05 under BOTH chance models on BOTH scales; the headline quotes the LARGEST "
        "of the four shares.\n")
    rows = []

    def chk(name, value, target, tol, ok=None):
        ok = (abs(value - target) <= tol) if ok is None else ok
        rows.append(dict(check=name, value=float(value), target=float(target), tol=float(tol), result="PASS" if ok else "FAIL"))

    # targets recomputed from this run's club_seasons.csv and configured seasons (selfcheck)
    R = selfcheck.reference()
    tol = selfcheck.TOL
    per = m.season.value_counts()
    chk("rows", len(m), R["rows"], 0)
    chk("seasons", len(seasons), len(R["seasons"]), 0, ok=seasons == R["seasons"])
    chk("rows per season = 20 (all seasons)", per.min(), selfcheck.CLUBS_PER_SEASON, 0, ok=bool((per == selfcheck.CLUBS_PER_SEASON).all()))
    chk("clubs (one team_id each)", m.club.nunique(), R["clubs"], 0, ok=m.club.nunique() == R["clubs"] and m.team_id.nunique() == R["clubs"]
        and m.groupby("club").team_id.nunique().max() == 1)
    npairs = len(pairs_idx(m)[0])
    chk("consecutive same-club pairs", npairs, R["pairs"], 0)
    for col, club, s in (("m", TOT, "2025/2026"), ("m", TOT, "2024/2025"), ("m", CHE, "2023/2024"), ("c", TOT, "2024/2025"), ("c", TOT, "2025/2026")):
        chk(f"{'Tottenham' if club == TOT else 'Chelsea'} {col} {short(s)}", club_val(m, col, club, s), float(R[col][(club, s)]), tol)
    chk(f"lag-1 Pearson r of c ({npairs} pairs)", lag1(m, m.c.values), R["lag1_r_c"], tol)
    chk(f"lag-1 Pearson r of m ({npairs} pairs)", lag1(m, m.m.values), R["lag1_r_m"], tol)
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "op1_checks.csv", index=False)
    out(md_table(t, "{:.4f}"))
    out("")

    dist, ext = [], []
    for scale, (col, lab) in SCALES.items():
        v = m[col].values
        sw = stats.shapiro(v)
        sk = stats.skewtest(v)
        order = np.argsort(v, kind="stable")
        pos_t = int(np.where(order == m.index[(m.club == TOT) & (m.season == "2025/2026")][0])[0][0]) + 1
        dist.append(dict(scale=col, n=len(v), mean=v.mean(), SD=np.std(v, ddof=1), skew_G1=stats.skew(v, bias=False),
                         skew_g1=stats.skew(v), skewtest_p=sk.pvalue, excess_kurtosis_G2=stats.kurtosis(v, bias=False),
                         shapiro_W=sw.statistic, shapiro_p=sw.pvalue, min=v.min(), max=v.max(),
                         THFC_2025_26_position=pos_t))
        for side, idx in (("lowest", order[:5]), ("highest", order[::-1][:5])):
            for k, i in enumerate(idx, 1):
                r = m.iloc[i]
                ext.append(dict(scale=col, side=side, k=k, club=r.club, season=short(r.season), value=r[col],
                                value_in_sd=r[col] / np.std(v, ddof=1), other_scale=r["m" if col == "c" else "c"],
                                label=r.label))
    D, E = pd.DataFrame(dist), pd.DataFrame(ext)
    D.to_csv(OUT / "op1_distribution.csv", index=False)
    E.to_csv(OUT / "op1_extremes.csv", index=False)
    out(f"Shape of each scale ({len(m)} club-seasons). SD with ddof 1; skew_G1 and excess_kurtosis_G2 are the "
        "bias-adjusted sample statistics (skew_g1 = unadjusted); skewtest_p = D'Agostino test of zero skew; "
        f"THFC_2025_26_position = rank of Tottenham 2025/26 among the {len(m)} (1 = most negative):\n")
    out(md_table(D.T.reset_index().rename(columns={"index": "statistic", 0: "c", 1: "m"}).assign(
        c=lambda d: d.c.map(lambda x: f"{x:.4g}" if isinstance(x, (float, np.floating)) else str(x)),
        m=lambda d: d.m.map(lambda x: f"{x:.4g}" if isinstance(x, (float, np.floating)) else str(x)))))
    out("")
    for col in ("c", "m"):
        out(f"Five lowest and five highest on {col} (`other_scale` = the same club-season on the other scale):\n")
        out(md_table(E[E.scale == col].drop(columns="scale").reset_index(drop=True), "{:.4f}"))
        out("")
    fails = t[t.result == "FAIL"].check.tolist()
    out(f"**step 1: {'ALL CHECKS PASS' if not fails else 'FAIL: ' + '; '.join(fails)}.**\n")
    note = (f"{len(t)} checks, {len(fails)} fail; " + "; ".join(
        f"{r.scale} SD {r.SD:.4g} skew {r.skew_G1:.3f} exkurt {r.excess_kurtosis_G2:.3f} SW p {r.shapiro_p:.2g} THFC pos {r.THFC_2025_26_position}"
        for r in D.itertuples()))
    return note, fails


def op2(m, seasons):
    out("## 2. The two chance models\n")
    npairs = len(pairs_idx(m)[0])
    out(f"Four configurations = 2 scales × 2 models; each uses a fresh generator with seed {SEED} and {NSIM:,} "
        f"simulated {len(seasons)}-season leagues. Common skeleton: {m.club.nunique()} clubs (sorted by name), a stationary AR(1) per club over "
        f"{short(seasons[0])}–{short(seasons[-1])} with no club effect, running through seasons a club was absent; only the {len(m)} observed "
        "club-seasons are kept; each simulated value is then centred on its season's 20-club mean.\n")
    out("- **(N) normal:** x₁ ~ N(0, SD²), xₜ = ρ·xₜ₋₁ + N(0, SD²(1−ρ²)), with ρ = the scale's pooled lag-1 "
        f"Pearson r ({npairs} pairs) and SD = its SD (ddof 1). This is the carry-over step's model, re-implemented in this "
        "module with the same draw order.")
    out(f"- **(Q) shape-preserving:** the scale's {len(m)} observed values → normal scores (Blom plotting position "
        f"(r − 3/8)/(n + 1/4), ties averaged); ρ_q = pooled lag-1 r of the normal scores on the same {npairs} pairs; the "
        "AR(1) is run on the standard-normal scale (SD 1) with ρ_q; each simulated value is mapped back through the "
        "empirical quantile function (linear interpolation between the (normal score, observed value) points; "
        "beyond the lowest/highest normal score the observed min/max). Then season-centred.\n")
    out("A consequence of (Q) worth stating before the tests: before centring, no simulated value can lie beyond the "
        "observed min or max, so the observed extreme club-season can only be matched or exceeded through the "
        "season-centring step. For the single most extreme club-season on a scale, the Q-model share is therefore "
        "set largely by the plotting position (how much probability sits beyond the lowest normal score, here "
        f"{0.625 / (len(m) + 0.25):.4f} per cell) — see caveats.\n")
    cur, prv = pairs_idx(m)
    rows, fails = [], []
    val = []
    for scale, model in CONFIGS:
        col = SCALES[scale][0]
        p = params(m, scale)
        Y = simulate(m, scale, model)
        r = pooled_r(m, Y)
        sdv = Y.std(1, ddof=1)
        skv = stats.skew(Y, axis=1, bias=False)
        kv = stats.kurtosis(Y, axis=1, bias=False)
        v = p["v"]
        rows.append(dict(scale=col, model=model, rho_used=p["rho"] if model == "N" else p["rho_q"],
                         sd_used=p["sd"] if model == "N" else 1.0,
                         obs_lag1_r=p["rho"], sim_lag1_r_mean=r.mean(), sim_lag1_r_p05=np.percentile(r, 5),
                         sim_lag1_r_p95=np.percentile(r, 95), obs_SD=p["sd"], sim_SD_mean=sdv.mean(),
                         obs_skew=stats.skew(v, bias=False), sim_skew_mean=skv.mean(),
                         obs_exkurt=stats.kurtosis(v, bias=False), sim_exkurt_mean=kv.mean(),
                         obs_min=v.min(), sim_min_mean=Y.min(1).mean(), obs_max=v.max(), sim_max_mean=Y.max(1).mean()))
        if (scale, model) == ("pct", "N"):
            thr_m = max(club_val(m, "c", TOT, s) for s in TOT_S)
            thr_s = sum(club_val(m, "c", TOT, s) for s in TOT_S)
            milder = (((Y[:, cur] <= thr_m + EPS) & (Y[:, prv] <= thr_m + EPS)).sum(1) >= 1).mean()
            summ = ((Y[:, cur] + Y[:, prv] <= thr_s + EPS).sum(1) >= 1).mean()
            # the same shares from the carry-over step's own `simulate` (the model this module re-implements)
            Yc = carry.simulate(m, p["rho"], p["sd"], nsim=NSIM, seed=SEED)
            ref_milder = (((Yc[:, cur] <= thr_m + EPS) & (Yc[:, prv] <= thr_m + EPS)).sum(1) >= 1).mean()
            ref_sum = ((Yc[:, cur] + Yc[:, prv] <= thr_s + EPS).sum(1) >= 1).mean()
            for name, got, tgt in (("Tottenham milder-season share (carry-over step's simulate)", milder, ref_milder),
                                   ("Tottenham sum-rule share (carry-over step's simulate)", summ, ref_sum)):
                ok = abs(got - tgt) <= selfcheck.TOL
                val.append(dict(check=name, value=got, target=tgt, tol=selfcheck.TOL, exact_match_4dp=round(got, 4) == round(tgt, 4),
                                result="PASS" if ok else "FAIL"))
                if not ok:
                    fails.append(name)
    V = pd.DataFrame(val)
    C = pd.DataFrame(rows)
    V.to_csv(OUT / "op2_validation.csv", index=False)
    C.to_csv(OUT / "op2_calibration.csv", index=False)
    ns = m[["season", "club", "c", "m"]].copy()
    ns["z_c"] = normal_scores(m.c.values); ns["z_m"] = normal_scores(m.m.values)
    ns.to_csv(OUT / "op2_normal_scores.csv", index=False)
    out("**Validation — (N) on the % scale against the carry-over step's `simulate` on the same inputs (same seed, fresh generator):**\n")
    out(md_table(V, "{:.4f}"))
    out("")
    out("**Calibration of each configuration** (simulated values are the season-centred panels; `rho_used` = the "
        "AR(1) coefficient fed in, ρ for N and ρ_q for Q; `sim_*_mean` = average over the 5,000 leagues of the "
        "per-league statistic; p05/p95 = 5th/95th percentiles):\n")
    out(md_table(C, "{:.4f}"))
    out("")
    out(f"ρ_q (normal scores): c {params(m, 'pct')['rho_q']:.4f}, m {params(m, 'min')['rho_q']:.4f}.\n")
    out(f"**step 2: {'VALIDATION PASSES' if not fails else 'VALIDATION FAILS: ' + '; '.join(fails)}.**\n")
    note = (f"val milder {V.value.iloc[0]:.4f} sum {V.value.iloc[1]:.4f}; " + "; ".join(
        f"{r.scale}{r.model} rho {r.rho_used:.3f} simr {r.sim_lag1_r_mean:.3f} simSD {r.sim_SD_mean:.4g}/{r.obs_SD:.4g} "
        f"skew {r.sim_skew_mean:.2f}/{r.obs_skew:.2f}" for r in C.itertuples()))
    return note, fails


def observed_gaps(m, col):
    rows = []
    for s in sorted(m.season.unique()):
        g = m[m.season == s].sort_values(col)
        rows.append(dict(season=short(s), club_20th=g.club.iloc[0], value_20th=g[col].iloc[0], club_19th=g.club.iloc[1],
                         value_19th=g[col].iloc[1], bottom_gap=g[col].iloc[1] - g[col].iloc[0],
                         club_1st=g.club.iloc[-1], club_2nd=g.club.iloc[-2], top_gap=g[col].iloc[-1] - g[col].iloc[-2]))
    G = pd.DataFrame(rows)
    G["bottom_gap_rank"] = G.bottom_gap.rank(ascending=False, method="min").astype(int)
    G["top_gap_rank"] = G.top_gap.rank(ascending=False, method="min").astype(int)
    return G


def op3(m, seasons):
    out("## 3. Tests\n")
    out(f"Thresholds are the observed values in each measure's own units (not SD units), as the asymmetry step did; a simulated "
        f"league counts if it contains at least one qualifying event. Comparisons use a tolerance of {EPS:g}. "
        "Mirror = the same threshold with the sign reversed, on the surplus side (T1: any club-season ≥ −value; "
        "T2: any pair sum ≥ −sum; T3: any pair with both seasons ≥ −milder value; T4: any season whose top gap, "
        "1st − 2nd, is ≥ the same gap). `obs_count` = number of such events in the real data; `share_any` = share "
        "of simulated leagues with ≥ 1; `mean_count` = mean events per simulated league; `share_ge_obs` = share "
        "with at least the observed count. Overlapping pairs (three bad seasons in a row) count twice, as in the asymmetry step.\n")
    cur, prv = pairs_idx(m)
    # observed T4 tables
    gaps = {}
    for scale, (col, lab) in SCALES.items():
        G = observed_gaps(m, col)
        gaps[col] = G
        G.to_csv(OUT / f"op3_observed_gaps_{col}.csv", index=False)
        tg = G[G.season == "2025/26"].iloc[0]
        out(f"**T4 observed, {lab}** — per season, the 20th- and 19th-placed clubs and the gap between them "
            f"(bottom_gap = 19th − 20th), and the top gap (1st − 2nd); ranks among the {len(seasons)} seasons, 1 = largest:\n")
        out(md_table(G, "{:.4f}"))
        out(f"\n2025/26: 20th = {tg.club_20th}, bottom gap {tg.bottom_gap:.4f}, rank **{tg.bottom_gap_rank}** of {len(seasons)} "
            f"bottom gaps; top gaps ≥ it in the real data: {int((G.top_gap >= tg.bottom_gap - EPS).sum())}.\n")
    rows = []
    for scale, model in CONFIGS:
        col = SCALES[scale][0]
        v = m[col].values
        Y = simulate(m, scale, model)
        tv = {s: club_val(m, col, TOT, s) for s in TOT_S}
        cv = {s: club_val(m, col, CHE, s) for s in CHE_S}
        Sy = Y[:, cur] + Y[:, prv]; So = v[cur] + v[prv]
        Ylo = np.maximum(Y[:, cur], Y[:, prv]); Olo = np.maximum(v[cur], v[prv])   # both ≤ thr  ⇔ max ≤ thr
        Yhi = np.minimum(Y[:, cur], Y[:, prv]); Ohi = np.minimum(v[cur], v[prv])   # both ≥ thr  ⇔ min ≥ thr
        bY, tY = season_gaps(m, Y)
        G = gaps[col]
        gthr = float(G[G.season == "2025/26"].bottom_gap.iloc[0])
        specs = [
            ("T1", "Tottenham 2025/26", tv["2025/2026"], (v, Y), (v, Y)),
            ("T1", "Tottenham 2024/25", tv["2024/2025"], (v, Y), (v, Y)),
            ("T2", "Tottenham 2024/25–2025/26", sum(tv.values()), (So, Sy), (So, Sy)),
            ("T2", "Chelsea 2022/23–2023/24", sum(cv.values()), (So, Sy), (So, Sy)),
            ("T3", "Tottenham 2024/25–2025/26", max(tv.values()), (Olo, Ylo), (Ohi, Yhi)),
            ("T3", "Chelsea 2022/23–2023/24", max(cv.values()), (Olo, Ylo), (Ohi, Yhi)),
        ]
        for test, run, thr, (od, yd), (om, ym) in specs:
            for side, o, y, qual in (("deficit", od, yd, lambda a: a <= thr + EPS),
                                     ("surplus mirror", om, ym, lambda a: a >= -thr - EPS)):
                oc = int(qual(o).sum()); cnt = qual(y).sum(1)
                rows.append(dict(test=test, run=run, side=side, scale=col, model=model,
                                 threshold=thr if side == "deficit" else -thr, obs_count=oc, share_any=(cnt >= 1).mean(),
                                 mean_count=cnt.mean(), share_ge_obs=(cnt >= max(oc, 1)).mean()))
        for side, o, y in (("deficit", G.bottom_gap.values, bY), ("surplus mirror", G.top_gap.values, tY)):
            oc = int((o >= gthr - EPS).sum()); cnt = (y >= gthr - EPS).sum(1)
            rows.append(dict(test="T4", run="Tottenham 2025/26 gap to 19th", side=side, scale=col, model=model,
                             threshold=gthr, obs_count=oc, share_any=(cnt >= 1).mean(), mean_count=cnt.mean(),
                             share_ge_obs=(cnt >= max(oc, 1)).mean()))
    T = pd.DataFrame(rows)
    T.to_csv(OUT / "op3_tests.csv", index=False)
    for test, head in (("T1", "T1 single season"), ("T2", "T2 two-season run, sum rule"),
                       ("T3", "T3 two-season run, milder-season rule"), ("T4", "T4 gap to 19th")):
        out(f"**{head}:**\n")
        out(md_table(T[T.test == test].drop(columns="test").reset_index(drop=True), "{:.4f}"))
        out("")
    W = T[T.side == "deficit"].pivot_table(index=["test", "run"], columns=["scale", "model"], values="share_any", sort=False)
    W.columns = [f"{a}·{b}" for a, b in W.columns]
    out("**Deficit-side shares at a glance (share of simulated leagues with ≥ 1 event):**\n")
    out(md_table(W.reset_index(), "{:.4f}"))
    out("")
    Mw = T.pivot_table(index=["test", "run", "scale", "model"], columns="side", values="share_any", sort=False).reset_index()
    Mw["mirror_minus_deficit"] = Mw["surplus mirror"] - Mw["deficit"]
    Mw.to_csv(OUT / "op3_symmetry.csv", index=False)
    out("**Symmetry check (surplus mirror − deficit share):** N-model differences range "
        f"{Mw[Mw.model == 'N'].mirror_minus_deficit.min():+.4f} to {Mw[Mw.model == 'N'].mirror_minus_deficit.max():+.4f} "
        "(symmetric as built, differences are Monte Carlo noise); Q-model differences range "
        f"{Mw[Mw.model == 'Q'].mirror_minus_deficit.min():+.4f} to {Mw[Mw.model == 'Q'].mirror_minus_deficit.max():+.4f} "
        "(the Q model carries the observed asymmetry of each scale). Full table in `op3_symmetry.csv`.\n")
    note = "; ".join(f"{r.test} {r.run.split()[0][:3]} {r.run.split()[-1]} {r.scale}{r.model} {r.side[:3]} {r.share_any:.4f}"
                     for r in T.itertuples() if r.side == "deficit")
    return note, []


def op4(m, seasons):
    out("## 4. Verdict\n")
    T = pd.read_csv(OUT / "op3_tests.csv")
    D = pd.read_csv(OUT / "op1_distribution.csv").set_index("scale")
    V = pd.read_csv(OUT / "op2_validation.csv")
    Cb = pd.read_csv(OUT / "op2_calibration.csv")
    d = T[T.side == "deficit"]
    rows = []
    for (test, run), g in d.groupby(["test", "run"], sort=False):
        s = {f"{r.scale}·{r.model}": r.share_any for r in g.itertuples()}
        big = max(s, key=s.get)
        rows.append(dict(test=test, run=run, **{k: s[k] for k in ("c·N", "c·Q", "m·N", "m·Q")},
                         headline_share=s[big], headline_config=big,
                         verdict="RARE BY CHANCE" if all(x < 0.05 for x in s.values()) else "NOT SHOWN RARE"))
    R = pd.DataFrame(rows)
    R.to_csv(OUT / "op4_verdict.csv", index=False)
    out("Test × scale × model → share of simulated leagues with at least one event as extreme (deficit side). "
        "Columns: c = % scale, m = minutes scale; N = normal AR(1), Q = shape-preserving. Claim rule applied "
        "literally: RARE BY CHANCE only if all four shares < 0.05; headline = the largest of the four.\n")
    out(md_table(R, "{:.4f}"))
    out("")
    out("Claim rule, per test:\n")
    for r in R.itertuples():
        others = ", ".join(f"{k} {R.loc[r.Index, k]:.4f}" for k in ("c·N", "c·Q", "m·N", "m·Q") if k != r.headline_config)
        out(f"- {r.test} {r.run}: **{r.verdict}** — headline share {r.headline_share:.4f} ({r.headline_config}); "
            f"others {others}.")
    out("")
    # expectation check, mechanical
    g = lambda test, run, sc, mo: float(d[(d.test == test) & (d.run == run) & (d.scale == sc) & (d.model == mo)].share_any.iloc[0])
    keys = [(r.test, r.run) for r in R.itertuples()]
    lowerN = [k for k in keys if g(*k, "m", "N") < g(*k, "c", "N")]
    closerQ = [k for k in keys if abs(g(*k, "m", "Q") - g(*k, "c", "Q")) < abs(g(*k, "m", "N") - g(*k, "c", "N"))]
    exp = [
        ("% scale (N) reproduces the carry-over step's shares", f"milder {V.value.iloc[0]:.4f}, sum {V.value.iloc[1]:.4f}",
         "MET" if (V.result == "PASS").all() else "NOT MET"),
        (f"Tottenham 2025/26 most extreme of {len(m)} on m", f"position {int(D.loc['m', 'THFC_2025_26_position'])}",
         "MET" if int(D.loc["m", "THFC_2025_26_position"]) == 1 else "NOT MET"),
        ("m negatively skewed", f"G1 {D.loc['m', 'skew_G1']:.3f}, skewtest p {D.loc['m', 'skewtest_p']:.2g}",
         "MET" if D.loc["m", "skew_G1"] < 0 else "NOT MET"),
        ("minutes shares lower than % shares under N", f"{len(lowerN)} of {len(keys)} tests",
         "MET" if len(lowerN) == len(keys) else ("PARTLY MET" if lowerN else "NOT MET")),
        ("minutes shares closer to % shares under Q than under N", f"{len(closerQ)} of {len(keys)} tests",
         "MET" if len(closerQ) == len(keys) else ("PARTLY MET" if closerQ else "NOT MET")),
    ]
    E = pd.DataFrame(exp, columns=["expectation", "result", "status"])
    E.to_csv(OUT / "op4_expectation.csv", index=False)
    out("Expectation written before the run, checked mechanically:\n")
    out(md_table(E))
    out("")
    out("Minutes-lower-under-N tests: " + ("; ".join(f"{a} {b}" for a, b in lowerN) or "none") + ". "
        "Closer-under-Q tests: " + ("; ".join(f"{a} {b}" for a, b in closerQ) or "none") + ".\n")
    # the values a narrative quotes, one per key
    vals = {f"{r.test}_{r.run.split()[0][:3]}_{r.run.split()[-1].replace('/', '').replace('–', '_')}_{k.replace('·', '')}":
            R.loc[r.Index, k] for r in R.itertuples() for k in ("c·N", "c·Q", "m·N", "m·Q")}
    vals.update({f"{r.test}_{r.run.split()[0][:3]}_{r.run.split()[-1].replace('/', '').replace('–', '_')}_head": r.headline_share
                 for r in R.itertuples()})
    for sc in ("c", "m"):
        for k in D.columns:
            vals[f"{sc}_{k}"] = D.loc[sc, k]
    for r in Cb.itertuples():
        for k in ("rho_used", "sim_skew_mean", "obs_skew", "sim_min_mean", "obs_min", "sim_lag1_r_mean", "sim_SD_mean"):
            vals[f"{r.scale}{r.model}_{k}"] = getattr(r, k)
    pd.Series(vals).to_csv(OUT / "op4_narrative_values.csv", header=["value"])
    # inventory and integrity
    new = sorted(p for p in OUT.iterdir() if p.is_file())
    out("**Files written by this step:**\n")
    for p in new + [REPORT]:
        out(f"- `{p.name}`")
    out("")
    same = sha(INPUT) == input_sha_at_op1()
    out(f"Input unchanged since step 1 (SHA-256 re-check against the value printed in §1): **{'YES' if same else 'NO'}**.\n")
    return ("; ".join(f"{r.test} {r.run.split()[0][:3]} {r.run.split()[-1]} head {r.headline_share:.4f} {r.verdict}"
                      for r in R.itertuples()) + f"; input unchanged {same}"), []


def input_sha_at_op1():
    txt = REPORT.read_text(encoding="utf-8")
    key = f"`{INPUT.name}` — sha256 "
    return txt.split(key, 1)[1][:64]


if __name__ == "__main__":
    op = sys.argv[1]
    m, seasons = load()
    note, fails = globals()[op](m, seasons)
    with open(REPORT, "a", encoding="utf-8") as f:
        if op == "op1":
            f.write("# How unusual is Tottenham Hotspur's availability? Two scales, two chance models\n\n")
        f.write("\n".join(LINES) + "\n\n")
    if fails:
        sys.exit(1)
