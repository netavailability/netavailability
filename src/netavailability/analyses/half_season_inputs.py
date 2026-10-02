"""Half-season inputs for the lag models, with their input checks.

Each club-season is split at the season's winter registration window close (the compute's own rule: a fixture dated
before the close is in the first half; fixtures on the close date fall in the second half). Points per half are rebuilt
from the fixtures; NETabsence per half comes from the compute's club_split_january table. The checks (38 fixtures per
club, halves that agree with the split file, rebuilt points = official points + deduction, Manchester City 2023/24
rebuilt to 91) are written to input_checks.json; the half-season file is written whatever the checks say, and the step
exits 1 when a check fails (the battery reports it).

Reads club_seasons.csv and club_season_values.csv in NETAV_ANALYSIS_DIR and the per-season split and fixtures files
named in NETAV_SEASON_FILES (season -> {"split": path, "fixtures": path}); writes half_season/half_season.csv and
half_season/input_checks.json. Run as: python -m netavailability.analyses.half_season_inputs
"""
import json
import os
import sys
from pathlib import Path

import pandas as pd

F = Path(os.environ["NETAV_ANALYSIS_DIR"])
G = F / "half_season"
SEASON_FILES = json.load(open(os.environ["NETAV_SEASON_FILES"]))
G.mkdir(parents=True, exist_ok=True)
OUT = G / "half_season.csv"
CHK = G / "input_checks.json"

SPLIT = {}
FIXT = {}
for s in sorted(SEASON_FILES):
    SPLIT[s] = SEASON_FILES[s]["split"]
    FIXT[s] = SEASON_FILES[s]["fixtures"]

DEDUCTIONS = {("2023/2024", "Everton"): 8, ("2023/2024", "Nottingham Forest"): 4}

vals = pd.read_csv(F / "club_season_values.csv")
fin = pd.read_csv(F / "club_seasons.csv")
fx_cache = {}
rows, fails, checks = [], [], {"split_files": {}, "split_columns": {}, "games_per_half": {}, "on_split_date": {}}
for s, sf in SPLIT.items():
    if s not in set(fin.season):   # only the seasons of this panel
        continue
    p = Path(sf)
    if not p.exists():
        checks["split_files"][s] = None
        continue
    sp = pd.read_csv(p)
    checks["split_files"][s] = sf
    checks["split_columns"][s] = list(sp.columns)
    wc = pd.Timestamp(sp.winter_close.iloc[0])
    assert sp.winter_close.nunique() == 1
    fn = FIXT[s]
    if fn not in fx_cache:
        d = pd.read_csv(Path(fn), parse_dates=["date"])
        fx_cache[fn] = d[d.league_id == 8].drop_duplicates("fixture_id")
    sid = int(fin.loc[fin.season == s, "standings_season_id"].iloc[0])
    fx = fx_cache[fn][fx_cache[fn].season_id == sid]
    checks["on_split_date"][s] = int((fx.date.dt.normalize() == wc).sum())
    for _, r in fin[fin.season == s].iterrows():
        c = int(r.team_id)
        m = fx[(fx.home_id == c) | (fx.away_id == c)].copy()
        home = m.home_id == c
        gf = m.home_goals.where(home, m.away_goals)
        ga = m.away_goals.where(home, m.home_goals)
        m["pts"] = (gf > ga) * 3 + (gf == ga) * 1
        pre = m.date < wc
        spr = sp[sp.team_id == c]
        if len(spr) != 1:
            fails.append(f"{s} {r.club}: split row count {len(spr)}")
            continue
        spr = spr.iloc[0]
        pts = int(m.pts.sum())
        ded = DEDUCTIONS.get((s, r.club), 0)
        row = dict(season=s, club=r.club, team_id=c, label=r.label, winter_close=wc.date().isoformat(),
                   fixtures=len(m), g_H1=int(pre.sum()), g_H2=int((~pre).sum()),
                   pts_H1=int(m.pts[pre].sum()), pts_H2=int(m.pts[~pre].sum()), pts_rebuilt=pts,
                   pts_official=int(r.points), deduction=ded,
                   split_pre_fixtures=int(spr.pre_fixtures), split_post_fixtures=int(spr.post_fixtures),
                   NETabs_H1=int(spr.pre_NETabsence), NETabs_H2=int(spr.post_NETabsence),
                   NETabs_pm_H1=spr.pre_NETabsence / spr.pre_fixtures, NETabs_pm_H2=spr.post_NETabsence / spr.post_fixtures,
                   NETabs_pm_H1_file=spr.pre_per_match, NETabs_pm_H2_file=spr.post_per_match,
                   split_file=sf, fixtures_file=fn)
        if len(m) != 38 or row["g_H1"] + row["g_H2"] != 38:
            fails.append(f"{s} {r.club}: fixtures {len(m)}, halves {row['g_H1']}+{row['g_H2']}")
        if pts != r.points + ded:
            fails.append(f"{s} {r.club}: rebuilt {pts} != official {r.points} + deduction {ded}")
        if (row["g_H1"], row["g_H2"]) != (row["split_pre_fixtures"], row["split_post_fixtures"]):
            fails.append(f"{s} {r.club}: halves {row['g_H1']}/{row['g_H2']} != split file {row['split_pre_fixtures']}/{row['split_post_fixtures']}")
        rows.append(row)
    g = pd.DataFrame([x for x in rows if x["season"] == s])
    checks["games_per_half"][s] = dict(H1_min=int(g.g_H1.min()), H1_max=int(g.g_H1.max()),
                                       H2_min=int(g.g_H2.min()), H2_max=int(g.g_H2.max()), n=len(g))

df = pd.DataFrame(rows).merge(vals[["season", "team_id", "finish", "NETavailability", "NETabsence", "log_value_rel",
                                     "squad_value_eur", "value_date", "value_flag"]], on=["season", "team_id"], how="left")
city = df[(df.season == "2023/2024") & (df.club == "Manchester City")].pts_rebuilt
checks["man_city_2023_24_rebuilt"] = int(city.iloc[0]) if len(city) else None
if checks["man_city_2023_24_rebuilt"] != 91:
    fails.append(f"Man City 2023/24 rebuilt {checks['man_city_2023_24_rebuilt']} != 91")
for (s, club), ded in DEDUCTIONS.items():
    r = df[(df.season == s) & (df.club == club)].iloc[0]
    checks[f"deduction {s} {club}"] = f"rebuilt {r.pts_rebuilt} = official {r.pts_official} + {ded}"
checks["max_abs_per_match_vs_file"] = float(max((df.NETabs_pm_H1 - df.NETabs_pm_H1_file).abs().max(),
                                                (df.NETabs_pm_H2 - df.NETabs_pm_H2_file).abs().max()))
checks["missing_values"] = int(df.log_value_rel.isna().sum())
checks["n_rows"] = len(df)
checks["fails"] = fails
print(json.dumps(checks, indent=1, default=str))
df.to_csv(OUT, index=False)   # written before the exit, so a failed check is reported by the battery instead of stopping it
CHK.write_text(json.dumps(checks, indent=1, default=str))
print("wrote", OUT, len(df))
if fails:
    print("CHECKS FAILED (file written; exit 1)")
    sys.exit(1)
