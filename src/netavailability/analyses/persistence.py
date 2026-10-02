"""Is club NETavailability persistent, or noise?

On the season-centred value c (club NETavailability minus that season's mean):
  op1  the panel (club seasons joined to squad values; c; rank; s_idx = start year minus the first start year, so a
       season left out leaves a gap) and its self-checks against the run's own inputs (row counts for the configured
       seasons, Tottenham's recomputed ranks against the club tables' rank column, the mean adjacent-season Spearman
       recomputed as the Pearson correlation of ranks): a failure exits 1; the panel and the adjacent-season
       Spearman table are written either way
  op2  signal versus noise: intraclass correlation (one-way random effects, ANOVA estimator, between-club variance
       truncated at 0, club bootstrap interval), split-half club means (odd v even start year; first v second half),
       a permutation test (club labels shuffled within season), one-season regression to the mean
  op3  the clubs with six or more seasons: mean, interval, empirical-Bayes shrunken estimate, flags
  op4  is persistence just money: the same on the residual of c on log squad value (season FE)
  op5  sensitivity: without 2019/20-2021/22, and 2018/19 onwards only
Seeds are fixed (SEED). Reads club_seasons.csv and club_season_values.csv in NETAV_ANALYSIS_DIR; writes its CSVs and
report.md in persistence/. Run as: python -m netavailability.analyses.persistence op1|op2|op3|op4|op5
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
F_NETAV = BASE / "club_seasons.csv"
F_VAL = BASE / "club_season_values.csv"
OUT = BASE / "persistence"
REPORT = OUT / "report.md"
SEED = 20260930
COVID = ["2019/2020", "2020/2021", "2021/2022"]

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
    a = pd.read_csv(F_NETAV)
    v = pd.read_csv(F_VAL)
    m = a.merge(v[["season", "team_id", "log_value_rel", "squad_value_eur", "value_date"]],
                on=["season", "team_id"], how="left", validate="one_to_one", indicator=True)
    seasons = sorted(a.season.unique())
    m["s_idx"] = m.season.str[:4].astype(int) - int(seasons[0][:4])   # index by start year, so 2019/20 -> 2021/22 is a two-year gap when 2020/21 is excluded
    m["c"] = m.NETavailability - m.groupby("season").NETavailability.transform("mean")
    m["rank"] = m.groupby("season").NETavailability.rank(ascending=False, method="min").astype(int)
    return a, v, m, seasons


def labels_of(df):
    lab = df.groupby("season").label.first()
    fin = [s for s in lab.index if lab[s] == "FINAL"]
    ind = [s for s in lab.index if lab[s] == "INDICATIVE"]
    def span(x):
        return f"{x[0]}–{x[-1]}" if len(x) > 1 else (x[0] if x else "none")
    return f"{df.season.nunique()} seasons: INDICATIVE {len(ind)} ({span(ind)}), FINAL {len(fin)} ({span(fin)})"


# ---------- statistics ----------
def icc_anova(df, y="c"):
    g = df.groupby("club")[y]
    n_i = g.size().values.astype(float)
    k = len(n_i)
    N = n_i.sum()
    means = g.mean().values
    grand = df[y].mean()
    ssb = (n_i * (means - grand) ** 2).sum()
    ssw = ((df[y] - g.transform("mean")) ** 2).sum()
    msb = ssb / (k - 1)
    msw = ssw / (N - k)
    n0 = (N - (n_i ** 2).sum() / N) / (k - 1)
    sb2 = max((msb - msw) / n0, 0.0)
    return dict(k=k, N=int(N), n0=n0, MSB=msb, MSW=msw, sb2=sb2, sw2=msw,
                icc=sb2 / (sb2 + msw), sb2_raw=(msb - msw) / n0)


def icc_boot(df, y="c", draws=2000, seed=SEED):
    rng = np.random.default_rng(seed)
    groups = [grp[y].values for _, grp in df.groupby("club")]
    k = len(groups)
    vals = []
    for _ in range(draws):
        pick = rng.integers(0, k, k)
        rows = [(j, x) for j, gi in enumerate(pick) for x in groups[gi]]
        b = pd.DataFrame(rows, columns=["club", y])
        vals.append(icc_anova(b, y)["icc"])
    vals = np.array(vals)
    return np.percentile(vals, 2.5), np.percentile(vals, 97.5), vals


def icc_block(df, y, title):
    rows = []
    for name, sub in [("all clubs", df),
                      ("clubs ≥6 seasons", df[df.groupby("club").season.transform("size") >= 6])]:
        r = icc_anova(sub, y)
        lo, hi, _ = icc_boot(sub, y)
        rows.append(dict(sample=name, clubs=r["k"], obs=r["N"], n0=r["n0"], MSB=r["MSB"], MSW=r["MSW"],
                         var_between=r["sb2"], var_within=r["sw2"], ICC=r["icc"], ci_lo=lo, ci_hi=hi))
    t = pd.DataFrame(rows)
    out(f"**{title}**\n")
    out(md_table(t, "{:.6g}"))
    out()
    return t


def split_half(df, y, split, desc):
    if split == "parity":
        first = df.s_idx % 2 == 0  # 2014/15 (idx 0), 2016/17, ...
        la, lb = "odd seasons (2014/15, 2016/17, …)", "even seasons (2015/16, 2017/18, …)"
    else:
        ss = sorted(df.season.unique())
        h = (len(ss) + 1) // 2
        first = df.season.isin(ss[:h])
        la, lb = f"{ss[0]}–{ss[h-1]}", f"{ss[h]}–{ss[-1]}"
    A = df[first].groupby("club")[y].agg(["mean", "size"])
    B = df[~first].groupby("club")[y].agg(["mean", "size"])
    j = A.join(B, lsuffix="_a", rsuffix="_b", how="inner")
    j = j[(j.size_a >= 3) & (j.size_b >= 3)]
    n = len(j)
    if n >= 3:
        pr, pp = stats.pearsonr(j.mean_a, j.mean_b)
        sr, sp = stats.spearmanr(j.mean_a, j.mean_b)
    else:
        pr = pp = sr = sp = np.nan
    return dict(split=desc, half_a=la, half_b=lb, n=n, pearson=pr, p_pearson=pp, spearman=sr, p_spearman=sp,
                clubs=", ".join(j.index))


def split_block(df, y, title):
    rows = [split_half(df, y, "parity", "odd v even"), split_half(df, y, "chrono", "first v second half")]
    t = pd.DataFrame(rows)
    out(f"**{title}** (clubs with ≥3 seasons in each half)\n")
    out(md_table(t.drop(columns="clubs"), "{:.4f}"))
    for r in rows:
        out(f"\n- {r['split']} clubs (n={r['n']}): {r['clubs']}")
    out()
    return t


def wvar_stat(clubs, y, keep):
    s = pd.DataFrame({"club": clubs, "y": y})
    g = s.groupby("club").y.agg(["mean", "size"]).loc[keep]
    w = g["size"].values
    mu = (w * g["mean"].values).sum() / w.sum()
    return (w * (g["mean"].values - mu) ** 2).sum() / w.sum()


def perm_block(df, y, title, draws=10000, seed=SEED):
    counts = df.groupby("club").season.size()
    keep = counts[counts >= 6].index
    obs = wvar_stat(df.club.values, df[y].values, keep)
    rng = np.random.default_rng(seed)
    clubs = df.club.values.copy()
    idx_by_season = [np.where(df.season.values == s)[0] for s in sorted(df.season.unique())]
    sims = np.empty(draws)
    yv = df[y].values
    for d in range(draws):
        pc = clubs.copy()
        for ix in idx_by_season:
            pc[ix] = clubs[rng.permutation(ix)]
        sims[d] = wvar_stat(pc, yv, keep)
    p = (1 + (sims >= obs).sum()) / (draws + 1)
    t = pd.DataFrame([dict(clubs_ge6=len(keep), observed=obs, perm_mean=sims.mean(),
                           perm_p95=np.percentile(sims, 95), ratio_obs_to_mean=obs / sims.mean(), p=p)])
    out(f"**{title}** (shuffle club labels within season, {draws:,} draws, seed {seed}; "
        f"statistic = season-count-weighted variance of club means, clubs ≥6 seasons)\n")
    out(md_table(t, "{:.6g}"))
    out()
    return t


def club_table(df, y, icc_row, title):
    sb2, sw2 = icc_row["sb2"], icc_row["sw2"]
    grand = df[y].mean()
    rows = []
    for club, g in df.groupby("club"):
        n = len(g)
        if n < 6:
            continue
        m = g[y].mean()
        se = g[y].std(ddof=1) / np.sqrt(n)
        tq = stats.t.ppf(0.975, n - 1)
        B = sb2 / (sb2 + sw2 / n) if sb2 > 0 else 0.0
        rows.append(dict(club=club, seasons=n, mean=m, se=se, ci_lo=m - tq * se, ci_hi=m + tq * se,
                         shrink_B=B, shrunk=grand + B * (m - grand),
                         mean_rank=g["rank"].mean(), sd_rank=g["rank"].std(ddof=1),
                         best_rank=g["rank"].min(), worst_rank=g["rank"].max()))
    t = pd.DataFrame(rows).sort_values("shrunk", ascending=False).reset_index(drop=True)
    t["flag"] = np.where(t.ci_lo > 0, "ABOVE", np.where(t.ci_hi < 0, "BELOW", ""))
    show = t.copy()
    show["club"] = [f"**{c}**" if c in ("Tottenham Hotspur", "Chelsea") else c for c in show.club]
    out(f"**{title}** (sorted by EB shrunken estimate; B = σ²_b/(σ²_b+σ²_w/n), σ²_b={sb2:.3g}, σ²_w={sw2:.3g}; "
        f"95% interval = mean ± t(n−1)·SE)\n")
    out(md_table(show, "{:.4f}"))
    nf = (t.flag != "").sum()
    out(f"\nFlags (95% interval excludes zero): {nf} of {len(t)} clubs "
        f"({(t.flag=='ABOVE').sum()} above, {(t.flag=='BELOW').sum()} below). "
        f"Expected by chance at 5% two-sided: {0.05*len(t):.2f} (binomial P(≥{nf}) = "
        f"{stats.binom.sf(nf-1, len(t), 0.05):.4g}).")
    out()
    return t


# ---------- ops ----------
def op1(a, v, m, seasons):
    out("## 1. Provenance and checks\n")
    out(f"Run {datetime.now():%Y-%m-%d %H:%M}.\n")
    out("Inputs (read-only):\n")
    for f in (F_NETAV, F_VAL):
        out(f"- `{f.name}` — {len(pd.read_csv(f))} rows")
    out("\nJoin on season + team_id. Season-centred NETavailability `c` = club value − that season's 20-club mean. "
        "Rank 1 = highest NETavailability within season (method=min).\n")
    fails = []
    # (a) against the configured season list: 20 rows per season
    conf = selfcheck.configured_seasons()
    want_rows = selfcheck.CLUBS_PER_SEASON * len(conf)
    per = a.groupby("season").size()
    dup = a.duplicated(["season", "team_id"]).sum()
    matched = (m["_merge"] == "both").sum()
    ok_a = len(a) == want_rows and (per == selfcheck.CLUBS_PER_SEASON).all() and seasons == conf and dup == 0 and matched == want_rows
    out(f"**(a)** rows {len(a)} (configured: {len(conf)} seasons × {selfcheck.CLUBS_PER_SEASON} = {want_rows}); seasons {len(seasons)} "
        f"({seasons[0]}–{seasons[-1]}); per-season counts {sorted(set(per.values))}; duplicate season+team_id {dup}; join to "
        f"squad-value file {matched}/{want_rows}; log_value_rel missing {m.log_value_rel.isna().sum()} → **{'PASS' if ok_a else 'FAIL'}**")
    vd = m.groupby("season").value_date.first()
    out(f"\nNote: squad values are dated {', '.join(sorted(set(vd)))} (the Transfermarkt reference dates used).\n")
    if not ok_a:
        fails.append("a")
    # (b) ranks recomputed here against the club tables' own rank column
    tot = m[m.club == "Tottenham Hotspur"].sort_values("season")
    got = tot["rank"].tolist()
    want = tot["NETavailability_rank"].astype(int).tolist()
    ok_b = got == want and tot.season.tolist() == seasons
    agree = (m["rank"] == m["NETavailability_rank"]).all()
    out(f"**(b)** Tottenham Hotspur ranks {seasons[0]}→{seasons[-1]}: {got}; club tables' rank column {want} → "
        f"**{'PASS' if ok_b else 'FAIL'}** (recomputed ranks agree with file column NETavailability_rank for all {len(m)}: {agree})\n")
    if not ok_b:
        fails.append("b")
    # (c)
    rhos = []
    for s0, s1 in zip(seasons[:-1], seasons[1:]):
        x = m[m.season == s0].set_index("team_id").NETavailability
        y = m[m.season == s1].set_index("team_id").NETavailability
        common = x.index.intersection(y.index)
        r = stats.spearmanr(x[common], y[common])[0]
        rhos.append(dict(pair=f"{s0}→{s1}", n=len(common), spearman=r))
    rt = pd.DataFrame(rhos)
    mr = rt.spearman.mean()
    # the same mean recomputed as the Pearson correlation of within-pair average ranks
    ref = []
    for s0, s1 in zip(seasons[:-1], seasons[1:]):
        x = m[m.season == s0].set_index("team_id").NETavailability
        y = m[m.season == s1].set_index("team_id").NETavailability
        common = x.index.intersection(y.index)
        ref.append(np.corrcoef(x[common].rank(), y[common].rank())[0, 1])
    mr_ref = float(np.mean(ref))
    ok_c = abs(mr - mr_ref) <= selfcheck.TOL
    out(f"**(c)** adjacent-season Spearman of NETavailability ranks (clubs in both seasons):\n")
    out(md_table(rt, "{:.4f}"))
    out(f"\nMean over {len(rt)} pairs = **{mr:.4f}** (recomputed as the Pearson correlation of ranks: {mr_ref:.4f}, "
        f"tolerance {selfcheck.TOL:g}) → **{'PASS' if ok_c else 'FAIL'}**\n")
    rt.to_csv(OUT / "op1_adjacent_spearman.csv", index=False)
    if not ok_c:
        fails.append("c")
    # (d)
    cnt = m.groupby("club").season.size().sort_values(ascending=False)
    out(f"**(d)** seasons present per club ({len(cnt)} clubs):\n")
    out(md_table(cnt.rename("seasons").reset_index()))
    out(f"\nClubs with ≥6 seasons: {(cnt>=6).sum()}; ≥8: {(cnt>=8).sum()}; all {len(seasons)}: {(cnt==len(seasons)).sum()}.\n")
    cnt.rename("seasons").to_csv(OUT / "op1_club_season_counts.csv")
    m.drop(columns="_merge").to_csv(OUT / "op1_panel.csv", index=False)
    out(f"Self-checks against the run's own inputs: {'ALL PASS' if not fails else 'FAILED ' + ','.join(fails)}\n")
    return ("ALL PASS" if not fails else "FAIL " + ",".join(fails)) + f"; mean adj Spearman {mr:.4f}; THFC ranks {'match' if ok_b else 'differ'}", fails


def op2(a, v, m, seasons):
    out("## 2. Signal versus noise (season-centred NETavailability)\n")
    out(f"Data: {labels_of(m)}; {len(m)} club-seasons, {m.club.nunique()} clubs.\n")
    out("### 2(a) Intraclass correlation (one-way random effects, ANOVA estimator for unbalanced groups, "
        "σ²_b truncated at 0; 95% interval = percentile bootstrap over clubs, 2,000 draws, seed 20260930)\n")
    t = icc_block(m, "c", "ICC, season-centred NETavailability")
    t.to_csv(OUT / "op2a_icc.csv", index=False)
    out("### 2(b) Split-half\n")
    s = split_block(m, "c", "Split-half club means")
    s.to_csv(OUT / "op2b_split_half.csv", index=False)
    out("### 2(c) Permutation test\n")
    p = perm_block(m, "c", "Permutation")
    p.to_csv(OUT / "op2c_permutation.csv", index=False)
    out("### 2(d) One-season regression to the mean\n")
    prev = m[["team_id", "s_idx", "c"]].copy()
    prev["s_idx"] += 1
    j = m.merge(prev, on=["team_id", "s_idx"], suffixes=("", "_prev"))
    fit = smf.ols("c ~ c_prev", j).fit()
    fitc = smf.ols("c ~ c_prev", j).fit(cov_type="cluster", cov_kwds={"groups": j.team_id})
    sd = m.c.std(ddof=1)
    b = fit.params.c_prev
    out(f"OLS of c(t) on c(t−1), clubs present in consecutive seasons: n = {len(j)} pairs.\n")
    out(f"- slope = **{b:.4f}** (OLS SE {fit.bse.c_prev:.4f}, p = {fit.pvalues.c_prev:.3g}; "
        f"club-clustered SE {fitc.bse.c_prev:.4f}, p = {fitc.pvalues.c_prev:.3g}); intercept {fit.params.Intercept:.5f}; R² {fit.rsquared:.4f}")
    out(f"- Pearson r(c(t), c(t−1)) = {stats.pearsonr(j.c, j.c_prev)[0]:.4f}")
    out(f"- SD of season-centred NETavailability = {sd:.4f} ({sd*100:.2f} pp).")
    out(f"- In words: a club one SD ({sd*100:.2f} pp) above the season average is expected to be "
        f"{b*sd*100:.2f} pp ({b:.2f} SD) above average the next season — about {100*(1-b):.0f}% of the gap "
        f"regresses away in one season.\n")
    pd.DataFrame([dict(n=len(j), slope=b, se_ols=fit.bse.c_prev, p_ols=fit.pvalues.c_prev,
                       se_cluster=fitc.bse.c_prev, p_cluster=fitc.pvalues.c_prev, sd_c=sd)]
                 ).to_csv(OUT / "op2d_regression_to_mean.csv", index=False)
    r = t.iloc[0]
    r6 = t.iloc[1]
    sh = s.iloc[0]
    return (f"ICC all {r.ICC:.3f} [{r.ci_lo:.3f},{r.ci_hi:.3f}], >=6 {r6.ICC:.3f} [{r6.ci_lo:.3f},{r6.ci_hi:.3f}]; "
            f"odd/even r {sh.pearson:.3f} rho {sh.spearman:.3f} n={sh.n}; halves r {s.iloc[1].pearson:.3f}; "
            f"perm p {p.p.iloc[0]:.4f}; slope {b:.3f}"), []


def op3(a, v, m, seasons):
    out("## 3. The clubs (≥6 seasons)\n")
    out(f"Data: {labels_of(m)}. EB shrinkage uses variance components from 2(a), all clubs.\n")
    r = icc_anova(m, "c")
    t = club_table(m, "c", r, "Club means of season-centred NETavailability")
    t.to_csv(OUT / "op3_clubs.csv", index=False)
    tot = m[m.club == "Tottenham Hotspur"]
    ex = tot[~tot.season.isin(["2024/2025", "2025/2026"])]
    se = ex.c.std(ddof=1) / np.sqrt(len(ex))
    tq = stats.t.ppf(0.975, len(ex) - 1)
    out(f"Tottenham Hotspur excluding 2024/25–2025/26: n = {len(ex)}, mean {ex.c.mean():.4f}, SE {se:.4f}, "
        f"95% interval [{ex.c.mean()-tq*se:.4f}, {ex.c.mean()+tq*se:.4f}], mean rank {ex['rank'].mean():.2f} "
        f"(all {len(tot)} seasons: mean {tot.c.mean():.4f}, mean rank {tot['rank'].mean():.2f}; "
        f"2024/25 and 2025/26 values {tot[tot.season.isin(['2024/2025','2025/2026'])].c.round(4).tolist()}).\n")
    for c in ("Tottenham Hotspur", "Chelsea"):
        row = t[t.club == c].iloc[0]
        out(f"- {c}: position {t.index[t.club==c][0]+1} of {len(t)} by shrunken estimate; raw mean {row['mean']:.4f}, "
            f"shrunk {row.shrunk:.4f}, interval [{row.ci_lo:.4f}, {row.ci_hi:.4f}] {row.flag or 'not flagged'}.")
    out()
    fl = t[t.flag != ""]
    return (f"{len(t)} clubs; flags {len(fl)} ({'; '.join(f'{c} {f}' for c, f in zip(fl.club, fl.flag))}); "
            f"expected by chance {0.05*len(t):.2f}; THFC excl 24/25-25/26 mean {ex.c.mean():.4f}"), []


def op4(a, v, m, seasons):
    out("## 4. Is persistence just money?\n")
    out(f"Data: {labels_of(m)}.\n")
    fit = smf.ols("c ~ log_value_rel + C(season)", m).fit()
    fitc = smf.ols("c ~ log_value_rel + C(season)", m).fit(cov_type="cluster", cov_kwds={"groups": m.team_id})
    m = m.copy()
    m["resid"] = fit.resid
    out(f"OLS c ~ log_value_rel + season FE (n = {int(fit.nobs)}): coefficient {fit.params.log_value_rel:.5f} "
        f"(SE {fit.bse.log_value_rel:.5f}, p = {fit.pvalues.log_value_rel:.3g}; club-clustered SE "
        f"{fitc.bse.log_value_rel:.5f}, p = {fitc.pvalues.log_value_rel:.3g}); R² {fit.rsquared:.4f}. "
        f"Residual SD {m.resid.std(ddof=1):.4f} vs c SD {m.c.std(ddof=1):.4f}.\n")
    out("### 4(a) ICC on residual\n")
    t = icc_block(m, "resid", "ICC, value-adjusted residual")
    out("### 4(b) Split-half on residual\n")
    s = split_block(m, "resid", "Split-half, value-adjusted residual")
    out("### 4(c) Clubs on residual\n")
    ct = club_table(m, "resid", icc_anova(m, "resid"), "Club means of value-adjusted residual")
    out("### 4(d) Club-level money correlation\n")
    cnt = m.groupby("club").season.transform("size")
    g = m[cnt >= 6].groupby("club")[["log_value_rel", "c"]].mean()
    pr, pp = stats.pearsonr(g.log_value_rel, g.c)
    sr, sp = stats.spearmanr(g.log_value_rel, g.c)
    out(f"Across {len(g)} clubs with ≥6 seasons, mean log_value_rel vs mean season-centred NETavailability: "
        f"Pearson r = {pr:.4f} (p = {pp:.3g}), Spearman ρ = {sr:.4f} (p = {sp:.3g}).\n")
    m[["season", "club", "team_id", "c", "log_value_rel", "resid"]].to_csv(OUT / "op4_residual_panel.csv", index=False)
    t.to_csv(OUT / "op4_icc_resid.csv", index=False)
    s.to_csv(OUT / "op4_split_half_resid.csv", index=False)
    ct.to_csv(OUT / "op4_clubs_resid.csv", index=False)
    g.to_csv(OUT / "op4_club_value_means.csv")
    fl = ct[ct.flag != ""]
    return (f"coef {fit.params.log_value_rel:.4f} p {fit.pvalues.log_value_rel:.3g}; resid ICC all {t.iloc[0].ICC:.3f} "
            f"[{t.iloc[0].ci_lo:.3f},{t.iloc[0].ci_hi:.3f}]; odd/even r {s.iloc[0].pearson:.3f}; flags {len(fl)}; "
            f"club-level r(value,avail) {pr:.3f} p {pp:.3g}"), []


def op5(a, v, m, seasons):
    out("## 5. Sensitivity\n")
    out("Season-centring is within season, so subsetting seasons does not change any club's centred value. "
        "Split-half: parity split keeps the original odd/even assignment; the chronological split halves the "
        "retained seasons (first half gets the extra season when the count is odd).\n")
    notes = []
    rows = []
    for key, desc, sub in [("i", "(i) excluding Covid-flagged 2019/20, 2020/21, 2021/22", m[~m.season.isin(COVID)]),
                           ("ii", "(ii) 2018/19–2025/26 only", m[m.season.str[:4].astype(int) >= 2018])]:   # by start year
        lab = labels_of(sub)
        out(f"### 5{key}. {desc} — {lab}\n")
        out(f"{len(sub)} club-seasons, {sub.club.nunique()} clubs.\n")
        t = icc_block(sub, "c", f"ICC — {lab}")
        s = split_block(sub, "c", f"Split-half — {lab}")
        p = perm_block(sub, "c", f"Permutation — {lab}")
        for df_, kind in ((t, "icc"), (s.drop(columns="clubs"), "split"), (p, "perm")):
            d = df_.copy(); d.insert(0, "table", kind); d.insert(0, "sensitivity", key); rows.append(d)
        notes.append(f"({key}) ICC all {t.iloc[0].ICC:.3f} [{t.iloc[0].ci_lo:.3f},{t.iloc[0].ci_hi:.3f}], "
                     f"odd/even r {s.iloc[0].pearson:.3f} n={s.iloc[0].n}, perm p {p.p.iloc[0]:.4f}")
    pd.concat(rows, ignore_index=True).to_csv(OUT / "op5_sensitivity.csv", index=False)
    out("### 5(iii). FINAL seasons only (2022/23–2025/26) — not run\n")
    out("Four seasons are too few: no club can reach the ≥6-season threshold used by the permutation statistic and the "
        "club table, and a split-half needs ≥3 seasons in each half (≥6 in total). An ICC on 4 seasons would rest "
        "on ≤4 observations per club; it is not reported.\n")
    return "; ".join(notes) + "; FINAL-only not run (too few seasons)", []


if __name__ == "__main__":
    op = sys.argv[1]
    a, v, m, seasons = load()
    note, fails = globals()[op](a, v, m, seasons)
    with open(REPORT, "a", encoding="utf-8") as f:
        if op == "op1":
            f.write("# Is club availability persistent?\n\n")
        f.write("\n".join(LINES) + "\n\n")
    sys.exit(1 if fails else 0)
