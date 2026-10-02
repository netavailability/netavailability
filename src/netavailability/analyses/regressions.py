"""Points and finish against squad value and NETavailability.

Per season (OLS, n = 20) and pooled with season fixed effects (HC3): (a) y ~ log squad value, (b) y ~ NETavailability,
(c) y ~ both, for y = points and finish; the gain in R-squared from adding NETavailability to value (dR2) with its F
test; standardised betas; the value -> NETavailability path. A bootstrap of dR2 on the final four seasons (1,000 draws,
club-seasons resampled within season, fixed seed). Pools: the final four seasons 2022/23-2025/26, every season but
2020/21 ("paper" pool; label from NETAV_POOL_LABEL_REGRESSIONS) and all seasons in the file.

Reads club_season_values.csv in NETAV_ANALYSIS_DIR; writes per_season.csv, residuals_per_season.csv, pooled.csv and
bootstrap.json there. Run as: python -m netavailability.analyses.regressions
"""
import os, json
import numpy as np, pandas as pd, statsmodels.formula.api as smf
from scipy import stats
OUT = os.environ["NETAV_ANALYSIS_DIR"]
df = pd.read_csv(os.path.join(OUT, "club_season_values.csv"))
df = df.rename(columns={"NETavailability": "netav"}); df["lv"] = df["log_value_rel"]
seasons = sorted(df.season.unique())
POOLS = {"FINAL 2022/23–2025/26": [s for s in seasons if s >= "2022/2023"], os.environ.get("NETAV_POOL_LABEL_REGRESSIONS", "paper 7 (2018/19, 2019/20, 2021/22–2025/26)"): [s for s in seasons if s != "2020/2021"], "all seasons in the file": seasons}
F = {"a": "{y} ~ lv", "b": "{y} ~ netav", "c": "{y} ~ lv + netav"}
def zb(d, y, x):  # standardised betas: z-score y and x within d, same design
    z = d.copy()
    for v in [y] + x: z[v] = (z[v] - z[v].mean()) / z[v].std(ddof=1)
    return z

# ---- per season
per = []
for y in ["points", "finish"]:
    for s in seasons:
        d = df[df.season == s]
        r = {"y": y, "season": s, "label": d.label.iloc[0], "n": len(d)}
        for k, f in F.items():
            m = smf.ols(f.format(y=y), d).fit()
            xs = [v for v in ["lv", "netav"] if v in f]
            mz = smf.ols(f.format(y=y), zb(d, y, xs)).fit()
            r[f"{k}_R2"], r[f"{k}_adjR2"] = m.rsquared, m.rsquared_adj
            for v in xs:
                r[f"{k}_{v}_coef"], r[f"{k}_{v}_se"], r[f"{k}_{v}_p"], r[f"{k}_{v}_beta"] = m.params[v], m.bse[v], m.pvalues[v], mz.params[v]
            if k == "a": r["resid_a"] = m.resid
        r["dR2"] = r["c_R2"] - r["a_R2"]
        r["pearson_lv_netav"], r["pearson_lv_netav_p"] = stats.pearsonr(d.lv, d.netav)
        r["spearman_lv_netav"], r["spearman_lv_netav_p"] = stats.spearmanr(d.lv, d.netav)
        r["resid_netav_r"], r["resid_netav_p"] = stats.pearsonr(r.pop("resid_a"), d.netav)
        if y == "finish":
            r["spearman_netavrank_finish"], r["spearman_netavrank_finish_p"] = stats.spearmanr(d.NETavailability_rank, d.finish)
        per.append(r)
per = pd.DataFrame(per); per.to_csv(os.path.join(OUT, "per_season.csv"), index=False)

# ---- residual per club-season (per-season model a, points)
res = []
for s in seasons:
    d = df[df.season == s].copy(); m = smf.ols("points ~ lv", d).fit()
    d["cost_expectation"] = m.fittedvalues; d["residual"] = m.resid; res.append(d)
res = pd.concat(res); res.to_csv(os.path.join(OUT, "residuals_per_season.csv"), index=False)

# ---- pooled with season FE, HC3
pool = []; boot = {}
for pname, ss in POOLS.items():
    d = df[df.season.isin(ss)].copy()
    d["netav_w"] = d.netav - d.groupby("season").netav.transform("mean")
    for y in ["points", "finish"]:
        r = {"pool": pname, "y": y, "n": len(d)}
        fits = {}
        for k, f in F.items():
            fe = f.format(y=y) + " + C(season)"
            m = smf.ols(fe, d).fit(cov_type="HC3"); m0 = smf.ols(fe, d).fit()
            xs = [v for v in ["lv", "netav"] if v in f]
            mz = smf.ols(fe, zb(d, y, xs)).fit(cov_type="HC3")
            fits[k] = m0
            # within-season R-squared (season means removed)
            yw = d[y] - d.groupby("season")[y].transform("mean")
            r[f"{k}_R2"], r[f"{k}_adjR2"], r[f"{k}_R2_within"] = m0.rsquared, m0.rsquared_adj, 1 - (m0.resid ** 2).sum() / (yw ** 2).sum()
            for v in xs:
                r[f"{k}_{v}_coef"], r[f"{k}_{v}_se_hc3"], r[f"{k}_{v}_p_hc3"], r[f"{k}_{v}_p_ols"], r[f"{k}_{v}_beta"] = m.params[v], m.bse[v], m.pvalues[v], m0.pvalues[v], mz.params[v]
        r["dR2"] = r["c_R2"] - r["a_R2"]
        ft = fits["c"].compare_f_test(fits["a"]); r["dR2_F"], r["dR2_F_p"] = ft[0], ft[1]
        # mediation path, pooled
        r["pearson_lv_netav_within"], r["pearson_lv_netav_within_p"] = stats.pearsonr(d.lv, d.netav_w)
        r["spearman_lv_netav_within"], r["spearman_lv_netav_within_p"] = stats.spearmanr(d.lv, d.netav_w)
        mm = smf.ols("netav ~ lv + C(season)", d).fit(cov_type="HC3")
        r["path_netav_on_lv_coef"], r["path_netav_on_lv_se_hc3"], r["path_netav_on_lv_p_hc3"] = mm.params["lv"], mm.bse["lv"], mm.pvalues["lv"]
        ra = fits["a"].resid
        r["resid_netav_within_r"], r["resid_netav_within_p"] = stats.pearsonr(ra, d.netav_w)
        pool.append(r)
    if pname.startswith("FINAL"):
        rng = np.random.default_rng(20260928)
        for y in ["points", "finish"]:
            dr, bc = [], []
            for _ in range(1000):
                idx = np.concatenate([rng.choice(np.where(d.season.values == s)[0], 20, replace=True) for s in ss])
                b = d.iloc[idx]
                ma = smf.ols(f"{y} ~ lv + C(season)", b).fit(); mc = smf.ols(f"{y} ~ lv + netav + C(season)", b).fit()
                dr.append(mc.rsquared - ma.rsquared); bc.append(mc.params["netav"])
            dr, bc = np.array(dr), np.array(bc)
            boot[y] = dict(draws=1000, seed=20260928, dR2_mean=dr.mean(), dR2_median=float(np.median(dr)), dR2_p2_5=np.percentile(dr, 2.5), dR2_p97_5=np.percentile(dr, 97.5),
                           netav_coef_p2_5=np.percentile(bc, 2.5), netav_coef_p97_5=np.percentile(bc, 97.5), netav_coef_share_le0=float((bc <= 0).mean()) if y == "points" else float((bc >= 0).mean()))
pool = pd.DataFrame(pool); pool.to_csv(os.path.join(OUT, "pooled.csv"), index=False)
json.dump(boot, open(os.path.join(OUT, "bootstrap.json"), "w"), indent=1, default=float)
print(per[per.y == "points"][["season", "a_R2", "a_lv_coef", "b_R2", "c_R2", "dR2", "c_netav_p", "pearson_lv_netav", "resid_netav_r", "resid_netav_p"]].round(3).to_string())
print(per[per.y == "finish"][["season", "a_R2", "a_lv_coef", "c_R2", "dR2", "c_netav_p", "spearman_netavrank_finish"]].round(3).to_string())
pd.set_option("display.width", 250)
print(pool.T.to_string())
print(json.dumps(boot, indent=1, default=float))
