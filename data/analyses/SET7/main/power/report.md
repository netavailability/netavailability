# How big a lasting club edge could hide? Power and upper bound for the persistence statistics

## 1. Provenance

Run 2026-10-02 05:33 (numpy 2.4.6, pandas 3.0.5).

Module: `power.py` (sha256 `6df0f1a03fd7cb5742267cbc80cf44532bee49117babbd4978ec85424ff83683`).

Inputs (read-only):

| file | sha256 | use |
|---|---|---|
| `persistence/op1_panel.csv` | `59861472db49774c33a4fad12ef35eb498c5b14f5824be7df42048461a098e5c` | panel, 140 club-seasons, `c` = NETavailability − season mean |
| `carryover_null.py` | `7c15f3e80a76642d1aa0db7a20d3056c15fb65d44e5d43201ec898e073d4cd61` | imported: `load`, `lag1`, `Design` (ICC, permutation statistic, split-half, flag intervals), `nflag`, `simulate` |
| `carryover_null/op3_null_draws.csv` | `c50c324d85ebfd28b238a5d83b9bc107da65c8df6f41b17cde469d72ea7ea891` | the carry-over step's 5,000 carry-over-only null draws (thresholds) |

Outputs: CSVs in `power/`, this report.

## 2. Self-checks (targets recomputed from this run's inputs)

| check | quantity | value | target | tolerance | result |
|---|---|---|---|---|---|
| a | rows | 140 | 140 | 0 | PASS |
| b | pooled lag-1 Pearson of c | 0.41898 | 0.41898 | 1e-09 | PASS |
| c | SD of c (ddof 1) | 0.0519136 | 0.0519136 | 1e-09 | PASS |
| d | ICC all clubs | 0.120707 | 0.120707 | 1e-09 | PASS |
| d | ICC clubs ≥6 seasons | 0.199787 | 0.199787 | 1e-09 | PASS |
| d | odd/even split-half r | 0.741808 | 0.741808 | 1e-09 | PASS |
| e | max abs Δ re-simulated vs saved null draws (all 8 columns, 5000 draws, seed 20260930) | 1.11022e-16 | 0 | 1e-12 | PASS |

(e) per column: icc_all 9.89e-17, icc_ge6 9.89e-17, perm_stat 1e-16, split_half_r 1.11e-16, flags_raw 0, flags_adj 0, lag1_r 8.33e-17, sd_c 9.71e-17. The carry-over step's `simulate` was called with its own constants (NSIM 5000, SEED 20260930), the observed ρ 0.418980 and SD 0.051914; statistics came from its `Design`/`nflag`.

Also (not stopping checks): permutation statistic 0.000873330 (recomputed from club_seasons.csv: 0.000873330); corrected-interval flags 0; uncorrected 4.

**All checks PASS.**

## 3. Method as run

Alternative model: c = u_club + e. u_club ~ N(0, σ_u²), one value per club for the whole window; e is the carry-over step's AR(1) (its `simulate`, which runs each club's series through all 8 start years, keeps the 140 observed club-seasons and season-centres). For share s = σ_u²/total variance: total SD fixed at the observed 0.051914, so σ_u = 0.051914·√s and SD(e) = 0.051914·√(1−s); total lag-1 r fixed at the observed 0.418980, so ρ_e = (0.418980 − s)/(1 − s). u_club is season-centred with the same season means as e (centring is linear, so centre(e + u) = centre(e) + centre(u)).

2,000 panels per s, seed 20260930: e from `simulate(seed=20260930)` at every s, and z_club ~ N(0,1) drawn once from seed 20260931 and scaled by σ_u at every s (common random numbers across s, so the curves are smooth in s). The coarse grid [0, 0.02, 0.05, 0.08, 0.1, 0.15, 0.2, 0.25, 0.3] was run inside a 0.01-step grid 0.00–0.30 (31 values), which covers every crossing; tables (i)–(ii) show the coarse grid, the CSVs hold all 31.

Corrected-interval flags use the carry-over step's fixed ρ = 0.418980 in every panel, as in its null. Power = share of panels > the null's 95th percentile (flags: ≥). "Any" = ICC-all or permutation or split-half above its null 98.333rd percentile (Bonferroni 0.05/3). Null thresholds from the carry-over step's 5,000 saved draws (numpy linear percentile):

| statistic | observed | null_p95 | null_p98_333 |
|---|---|---|---|
| icc_all | 0.120707 | 0.310765 | 0.355381 |
| icc_ge6 | 0.199787 | 0.327048 |  |
| perm_stat | 0.00087333 | 0.00118817 | 0.00138904 |
| split_half_r | 0.741808 | 0.828975 | 0.869404 |
| flags_adj | 0 | 0 |  |

The flag count is discrete: under the null P(flags ≥ 0) = 1.0000, so that test's size is 1.000, not 0.05. Monte-Carlo SE of a share from 2,000 panels: ±0.0112 at 0.5, ±0.0089 at 0.8, ±0.0049 at 0.05.

Calibration: at s = 0 the simulated panels average lag-1 r 0.4076 and SD 0.05063; at s = 0.30, 0.4072 and 0.05063 (observed 0.4190, 0.05191; season-centring removes a little of both, as in the carry-over step).

## 4. Results

### (i) Power by s × statistic

| s | sigma_u_pp | rho_e | power_icc_all | power_icc_ge6 | power_perm | power_split_half | power_flags_adj | power_any_bonf |
|---|---|---|---|---|---|---|---|---|
| 0.000 | 0.000 | 0.419 | 0.051 | 0.054 | 0.047 | 0.051 | 1.000 | 0.043 |
| 0.020 | 0.734 | 0.407 | 0.064 | 0.074 | 0.059 | 0.054 | 1.000 | 0.052 |
| 0.050 | 1.161 | 0.388 | 0.092 | 0.100 | 0.085 | 0.061 | 1.000 | 0.072 |
| 0.080 | 1.468 | 0.368 | 0.128 | 0.131 | 0.105 | 0.072 | 1.000 | 0.098 |
| 0.100 | 1.642 | 0.354 | 0.166 | 0.153 | 0.124 | 0.079 | 1.000 | 0.117 |
| 0.150 | 2.011 | 0.316 | 0.241 | 0.230 | 0.169 | 0.097 | 1.000 | 0.172 |
| 0.200 | 2.322 | 0.274 | 0.352 | 0.314 | 0.229 | 0.115 | 1.000 | 0.246 |
| 0.250 | 2.596 | 0.225 | 0.472 | 0.421 | 0.287 | 0.133 | 1.000 | 0.347 |
| 0.300 | 2.843 | 0.170 | 0.600 | 0.525 | 0.353 | 0.152 | 1.000 | 0.461 |

### (ii) Upper-bound shares: share of panels at or below the observed statistic

| s | sigma_u_pp | share_icc_all_le_obs | share_perm_le_obs | share_split_half_le_obs | share_icc_ge6_le_obs |
|---|---|---|---|---|---|
| 0.000 | 0.000 | 0.308 | 0.758 | 0.803 | 0.651 |
| 0.020 | 0.734 | 0.269 | 0.738 | 0.794 | 0.615 |
| 0.050 | 1.161 | 0.224 | 0.695 | 0.777 | 0.564 |
| 0.080 | 1.468 | 0.178 | 0.652 | 0.758 | 0.497 |
| 0.100 | 1.642 | 0.139 | 0.626 | 0.746 | 0.454 |
| 0.150 | 2.011 | 0.086 | 0.555 | 0.712 | 0.362 |
| 0.200 | 2.322 | 0.048 | 0.487 | 0.671 | 0.270 |
| 0.250 | 2.596 | 0.025 | 0.414 | 0.635 | 0.196 |
| 0.300 | 2.843 | 0.013 | 0.350 | 0.601 | 0.133 |

(ICC ≥6 is shown for completeness; the bound uses ICC-all, permutation and split-half. Observed: ICC-all 0.1207, permutation 0.00087333, split-half 0.7418, ICC ≥6 0.1998.)

### (iii) Headline: MDE at 80% power and 95% upper bound

s interpolated linearly on the 0.01 grid; `grid_min_s` = smallest grid s with power ≥ 0.80. σ_u in pp = 100·σ_u. Points a season = σ_u × 92.0 (12-season coefficient; range 63.0–121.1 from its 95% CI) and × 82.5 (FINAL). A club one σ_u above average has an edge of exactly σ_u: the pp and points columns are that club's edge. Headline statistic: ICC-all (the persistence statistics' primary one).

| quantity | statistic | s | grid_min_s | sigma_u_pp | pts_92 | pts_63 | pts_121 | pts_82_5 |
|---|---|---|---|---|---|---|---|---|
| MDE at 80% power | ICC-all |  |  |  |  |  |  |  |
| MDE at 80% power | ICC ≥6 |  |  |  |  |  |  |  |
| MDE at 80% power | permutation |  |  |  |  |  |  |  |
| MDE at 80% power | split-half |  |  |  |  |  |  |  |
| MDE at 80% power | corrected flags | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| MDE at 80% power | any (Bonferroni) |  |  |  |  |  |  |  |
| 95% upper bound | ICC-all | 0.197 |  | 2.303 | 2.119 | 1.451 | 2.789 | 1.900 |
| 95% upper bound | permutation |  |  |  |  |  |  |  |
| 95% upper bound | split-half |  |  |  |  |  |  |  |
| 95% upper bound | ICC ≥6 |  |  |  |  |  |  |  |

Blank = not reached on s ≤ 0.30, the top of the admissible range (ρ_e = (ρ − s)/(1 − s) ≥ 0 needs s ≤ 0.419); for those statistics the MDE or bound is > 0.30, i.e. σ_u > 2.84 pp (> 2.6 points).

## 5. Verdict

On ICC-all, a lasting club edge with SD σ_u = nan pp (s = nan of the variance of c; ≈ nan points a season at 92.0, nan–nan over the coefficient's CI, nan at 82.5) is detected with 80% probability; the Bonferroni any-of-three test reaches 80% at σ_u = nan pp (s = nan). The observed ICC-all 0.1207 is below 95% of simulated panels (fewer than 5% at or below it) once σ_u exceeds 2.30 pp (s = 0.197; ≈ 2.1 points a season, 1.5–2.8; 1.9 at 82.5): that is the 95% upper bound. The permutation and split-half statistics are weaker: at s = 0.30 (σ_u 2.84 pp) their power is 0.353 and 0.152, and 0.350 and 0.601 of panels still sit at or below the observed values, so neither rules out any s ≤ 0.30; ICC ≥6 gives a bound of nan pp. At s = 0 the ICC-all test's simulated size is 0.051 (nominal 0.05). Expected result: MDE 2–3 pp → DID NOT HOLD (nan pp); upper bound ≈ 2 pp (taken as 1.5–2.5) → HELD (2.30 pp, 2.1 points vs ≈ 2 expected).

Paper sentence: "Over seven seasons we would have detected a lasting club edge of nan pp (≈ nan points a season) with 80% probability; we found none, and the data rule out a lasting edge larger than 2.3 pp (≈ 2.1 points a season) at 95%."

Inputs unchanged after the run (sha256 re-read): True. Elapsed 3 s.

Files written: `power/checks.csv`, `power/null_thresholds.csv`, `power/power_by_share.csv`, `power/upper_bound_shares.csv`, `power/headline.csv`, `power/alt_draws.csv`, `power/report.md`.

