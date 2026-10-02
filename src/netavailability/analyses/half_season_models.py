"""Half-season lag models: does first-half availability predict second-half points?

Availability per half = NETabsence per match (AVAIL_H1, AVAIL_H2; more absence = less availability). First the
full-season result is reproduced on the final four seasons (points ~ log squad value + NETavailability, season FE,
HC3; with the reference values 82.5 and dR2 0.062 of an earlier input build, so pass_coef / pass_dR2 are informative
only), with the per-match form of the season measure to calibrate units. Then, per pool, second-half points on value
plus (b) first-half absence per match, (c) also first-half points, and the other models (a, d, e, f, c_ppg); nested F
tests and a within-season bootstrap (1,000 draws, fixed seed) of the first-half absence coefficient for (b) and (c);
the residual form; per-season fits. Pools: the final four seasons, every season but 2020/21 (label from
NETAV_POOL_LABEL_HALF_SEASON) and all seasons in the file.

Reads half_season/half_season.csv in NETAV_ANALYSIS_DIR; writes half_season/reproduce.json, pooled.csv, tests.csv,
per_season.csv, residual_r.csv and bootstrap.csv. Run as: python -m netavailability.analyses.half_season_models
"""
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

G = Path(os.environ["NETAV_ANALYSIS_DIR"]) / "half_season"
OUTS = {k: G / f"{k}.{e}" for k, e in [("reproduce", "json"), ("pooled", "csv"), ("tests", "csv"),
                                        ("per_season", "csv"), ("residual_r", "csv"), ("bootstrap", "csv")]}

d = pd.read_csv(G / "half_season.csv")
d = d.rename(columns={"NETabs_pm_H1": "AVAIL_H1", "NETabs_pm_H2": "AVAIL_H2", "pts_H1": "H1_points", "pts_H2": "H2_points"})
d["points"] = d.pts_official  # official season points after deductions, as in the regressions
d["NETabs_pm_season"] =d.NETabsence / d.fixtures
d["H2_ppg"] = d.H2_points / d.g_H2
d["syear"] = d.season.str[:4].astype(int)
POOLS = [("FINAL 2022/23-2025/26", d[d.syear >= 2022]), (os.environ.get("NETAV_POOL_LABEL_HALF_SEASON", "paper 7 (no 2020/21)"), d[d.syear != 2020]), ("all seasons in the file", d)]
FE = " + C(season)"


def fit(f, data, hc3=True):
    m = smf.ols(f, data=data)
    return m.fit(cov_type="HC3") if hc3 else m.fit()


def wsd(data, x):
    return float((data[x] - data.groupby("season")[x].transform("mean")).std(ddof=1))


# ---- reproduce the full-season result
fin = POOLS[0][1]
r0 = fit("points ~ log_value_rel" + FE, fin)
r1 = fit("points ~ log_value_rel + NETavailability" + FE, fin)
r0n, r1n = fit("points ~ log_value_rel" + FE, fin, False), fit("points ~ log_value_rel + NETavailability" + FE, fin, False)
Fv, Fp, _ = r1n.compare_f_test(r0n)
c, se, p = r1.params["NETavailability"], r1.bse["NETavailability"], r1.pvalues["NETavailability"]
dr2 = r1.rsquared - r0.rsquared
rep = dict(n=int(r1.nobs), coef=c, se_hc3=se, p=p, r2_a=r0.rsquared, r2_b=r1.rsquared, dR2=dr2, F=Fv, F_p=Fp,
           pass_coef=bool(abs(c - 82.5) <= 0.5), pass_dR2=bool(abs(dr2 - 0.062) <= 0.002))
# same full-season model with the half-season measure's form (NETabsence per match), to calibrate units
ra = fit("points ~ log_value_rel + NETabs_pm_season" + FE, fin)
rep["season_NETabs_pm_coef"] = ra.params["NETabs_pm_season"]
rep["season_NETabs_pm_se"] = ra.bse["NETabs_pm_season"]
rep["season_NETabs_pm_p"] = ra.pvalues["NETabs_pm_season"]
rep["season_NETabs_pm_dR2"] = ra.rsquared - r0.rsquared
# translation: NETavailability change per 1 NETabsence per match (within season, FINAL)
cal = fit("NETavailability ~ NETabs_pm_season" + FE, fin, False)
rep["dNETav_per_abs_pm"] = cal.params["NETabs_pm_season"]
rep["cal_r2"] = cal.rsquared
rep["wsd_NETav"] = wsd(fin, "NETavailability")
rep["wsd_NETabs_pm_season"] = wsd(fin, "NETabs_pm_season")
print(json.dumps(rep, indent=1, default=float))
OUTS["reproduce"].write_text(json.dumps(rep, indent=1, default=float))
if not (rep["pass_coef"] and rep["pass_dR2"]):
    print("NOTE: the reference values (82.5, dR2 0.062) belong to an earlier input build; on other inputs they are not expected to be reproduced; continuing")

# ---- half-season models
MODELS = {
    "a": ("H2_points", ["log_value_rel"]),
    "b": ("H2_points", ["log_value_rel", "AVAIL_H1"]),
    "c": ("H2_points", ["log_value_rel", "AVAIL_H1", "H1_points"]),
    "d": ("H2_points", ["log_value_rel", "AVAIL_H2"]),
    "e": ("H2_points", ["log_value_rel", "AVAIL_H1", "AVAIL_H2"]),
    "f": ("AVAIL_H2", ["log_value_rel", "H1_points", "AVAIL_H1"]),
    "c_ppg": ("H2_ppg", ["log_value_rel", "AVAIL_H1", "H1_points"]),  # sensitivity: outcome per game
}
pooled, tests, per_season, resid_r, boots = [], [], [], [], []
rng = np.random.default_rng(20260928)
for pool, data in POOLS:
    data = data.reset_index(drop=True)
    for k, (y, xs) in MODELS.items():
        r = fit(f"{y} ~ {' + '.join(xs)}" + FE, data)
        for x in xs:
            pooled.append(dict(pool=pool, model=k, outcome=y, term=x, n=int(r.nobs), coef=r.params[x], se_hc3=r.bse[x],
                               p=r.pvalues[x], beta=r.params[x] * data[x].std() / data[y].std(),
                               r2=r.rsquared, adj_r2=r.rsquared_adj))
    # nested tests for (b) and (c)
    for k, base in [("b", ["log_value_rel"]), ("c", ["log_value_rel", "H1_points"])]:
        xs = MODELS[k][1]
        full = fit("H2_points ~ " + " + ".join(xs) + FE, data)
        fulln = fit("H2_points ~ " + " + ".join(xs) + FE, data, False)
        red = fit("H2_points ~ " + " + ".join(base) + FE, data, False)
        Fv, Fp, _ = fulln.compare_f_test(red)
        s = wsd(data, "AVAIL_H1")
        cc = full.params["AVAIL_H1"]
        bs = []
        for _ in range(1000):
            idx = np.concatenate([rng.choice(g.index.values, size=len(g), replace=True) for _, g in data.groupby("season")])
            bs.append(smf.ols("H2_points ~ " + " + ".join(xs) + FE, data=data.loc[idx]).fit().params["AVAIL_H1"])
        bs = np.array(bs)
        boots += [dict(pool=pool, model=k, draw=i, coef=v) for i, v in enumerate(bs)]
        tests.append(dict(pool=pool, model=k, n=len(data), coef=cc, se_hc3=full.bse["AVAIL_H1"], p_hc3=full.pvalues["AVAIL_H1"],
                          wsd_AVAIL_H1=s, coef_per_wsd=cc * s, se_per_wsd=full.bse["AVAIL_H1"] * s,
                          r2_without=red.rsquared, r2_with=fulln.rsquared, dR2=fulln.rsquared - red.rsquared, F=Fv, F_p=Fp,
                          boot_lo=np.percentile(bs, 2.5), boot_hi=np.percentile(bs, 97.5), boot_share_le0=float((bs <= 0).mean()),
                          boot_share_ge0=float((bs >= 0).mean()),
                          approx_pts_per_pp_NETav=cc / (rep["dNETav_per_abs_pm"] * 100)))
    # (g) residual form
    ra_ = fit("H2_points ~ log_value_rel" + FE, data, False)
    rr, pp = stats.pearsonr(ra_.resid, data.AVAIL_H1)
    resid_r.append(dict(pool=pool, n=len(data), r=rr, p=pp))

for s, g in d.groupby("season"):
    for k in ("b", "c"):
        y, xs = MODELS[k]
        r = fit(f"{y} ~ {' + '.join(xs)}", g)
        per_season.append(dict(season=s, label=g.label.iloc[0], model=k, n=int(r.nobs), coef=r.params["AVAIL_H1"],
                               se_hc3=r.bse["AVAIL_H1"], p=r.pvalues["AVAIL_H1"], r2=r.rsquared))

pd.DataFrame(pooled).to_csv(OUTS["pooled"], index=False)
pd.DataFrame(tests).to_csv(OUTS["tests"], index=False)
pd.DataFrame(per_season).to_csv(OUTS["per_season"], index=False)
pd.DataFrame(resid_r).to_csv(OUTS["residual_r"], index=False)
pd.DataFrame(boots).to_csv(OUTS["bootstrap"], index=False)
pd.set_option("display.width", 250)
print(pd.DataFrame(pooled).to_string())
print(pd.DataFrame(tests).T.to_string())
print(pd.DataFrame(per_season).to_string())
print(pd.DataFrame(resid_r).to_string())
