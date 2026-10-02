"""Self-check targets of the analysis steps, recomputed from the run's own inputs.

The steps' op1 checks compare what each step computed from its panel with the same quantities recomputed here by
separate code from the variant's club_seasons.csv and its configured season list (season_files.json, written by the
battery), so a check fails only when a step's panel, centring or pairing disagrees with the run it was given.
Pairs are matched by team_id and start year (merge), not by the steps' row-index pairing; the lag-1 correlation and
slope are computed from sums, not by scipy or statsmodels.
"""
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(os.environ["NETAV_ANALYSIS_DIR"])
CLUBS_PER_SEASON = 20
TOL = 1e-9   # recomputed values agree to rounding; anything larger is a real disagreement


def configured_seasons():
    """The variant's season list as the battery configured it."""
    p = Path(os.environ.get("NETAV_SEASON_FILES") or BASE / "season_files.json")
    return sorted(json.loads(p.read_text()))


def _corr(x, y):
    x = x - x.mean(); y = y - y.mean()
    return float((x * y).sum() / np.sqrt((x * x).sum() * (y * y).sum()))


def reference():
    """Expected rows (20 per configured season), clubs, consecutive same-club pairs, and per scale (c = NETavailability
    − season mean; m = season mean of NETabsence/38 − NETabsence/38) the values, SD (ddof 1) and pooled lag-1 Pearson r;
    the lag-1 OLS slope of c and the permutation statistic (season-count-weighted variance of club means, clubs with six
    or more seasons)."""
    cs = pd.read_csv(BASE / "club_seasons.csv")
    seasons = configured_seasons()
    d = cs.assign(year=cs.season.str[:4].astype(int))
    d["c"] = d.NETavailability - d.groupby("season").NETavailability.transform("mean")
    a = d.NETabsence / 38
    d["m"] = a.groupby(d.season).transform("mean") - a
    prev = d[["team_id", "year", "c", "m"]].assign(year=d.year + 1)
    j = d.merge(prev, on=["team_id", "year"], suffixes=("", "_prev"))
    cp, cc = j.c_prev - j.c_prev.mean(), j.c - j.c.mean()
    n = d.groupby("club").season.size()
    g = d[d.club.isin(n[n >= 6].index)].groupby("club").c.agg(["mean", "size"])
    mu = (g["size"] * g["mean"]).sum() / g["size"].sum()
    key = d.set_index(["club", "season"])
    return dict(seasons=seasons, rows=CLUBS_PER_SEASON * len(seasons), clubs=int(d.club.nunique()), pairs=len(j),
                c=key.c, m=key.m, sd_c=float(d.c.std(ddof=1)), sd_m=float(d.m.std(ddof=1)),
                lag1_r_c=_corr(j.c, j.c_prev), lag1_r_m=_corr(j.m, j.m_prev),
                lag1_slope_c=float((cp * cc).sum() / (cp * cp).sum()),
                perm_stat=float((g["size"] * (g["mean"] - mu) ** 2).sum() / g["size"].sum()))
