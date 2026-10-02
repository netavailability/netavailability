# How big a lasting club edge could hide? Power and upper bound for the persistence statistics

## 1. Provenance

Run 2026-10-02 05:33 (numpy 2.4.6, pandas 3.0.5).

Module: `power.py` (sha256 `6df0f1a03fd7cb5742267cbc80cf44532bee49117babbd4978ec85424ff83683`).

Inputs (read-only):

| file | sha256 | use |
|---|---|---|
| `persistence/op1_panel.csv` | `402e27fd77b2efb0157323762399e9b915c70f7caf41684ddb27ccf8c9b8bf45` | panel, 160 club-seasons, `c` = NETavailability − season mean |
| `carryover_null.py` | `7c15f3e80a76642d1aa0db7a20d3056c15fb65d44e5d43201ec898e073d4cd61` | imported: `load`, `lag1`, `Design` (ICC, permutation statistic, split-half, flag intervals), `nflag`, `simulate` |
| `carryover_null/op3_null_draws.csv` | `3e641e1949b54ab98f1bf99894d90634ec61c194f9bf0823029064e386227b33` | the carry-over step's 5,000 carry-over-only null draws (thresholds) |

Outputs: CSVs in `power/`, this report.

## 2. Self-checks (targets recomputed from this run's inputs)

| check | quantity | value | target | tolerance | result |
|---|---|---|---|---|---|
| a | rows | 160 | 160 | 0 | PASS |
| b | pooled lag-1 Pearson of c | 0.351218 | 0.351218 | 1e-09 | PASS |
| c | SD of c (ddof 1) | 0.0504849 | 0.0504849 | 1e-09 | PASS |
| d | ICC all clubs | 0.102431 | 0.102431 | 1e-09 | PASS |
| d | ICC clubs ≥6 seasons | 0.161965 | 0.161965 | 1e-09 | PASS |
| d | odd/even split-half r | 0.69788 | 0.69788 | 1e-09 | PASS |
| e | max abs Δ re-simulated vs saved null draws (all 8 columns, 5000 draws, seed 20260930) | 5.55112e-16 | 0 | 1e-12 | PASS |

(e) per column: icc_all 2.36e-16, icc_ge6 2.22e-16, perm_stat 1e-16, split_half_r 5.55e-16, flags_raw 0, flags_adj 0, lag1_r 4.44e-16, sd_c 1.11e-16. The carry-over step's `simulate` was called with its own constants (NSIM 5000, SEED 20260930), the observed ρ 0.351218 and SD 0.050485; statistics came from its `Design`/`nflag`.

Also (not stopping checks): permutation statistic 0.000681830 (recomputed from club_seasons.csv: 0.000681830); corrected-interval flags 0; uncorrected 3.

**All checks PASS.**

## 3. Method as run

Alternative model: c = u_club + e. u_club ~ N(0, σ_u²), one value per club for the whole window; e is the carry-over step's AR(1) (its `simulate`, which runs each club's series through all 8 start years, keeps the 160 observed club-seasons and season-centres). For share s = σ_u²/total variance: total SD fixed at the observed 0.050485, so σ_u = 0.050485·√s and SD(e) = 0.050485·√(1−s); total lag-1 r fixed at the observed 0.351218, so ρ_e = (0.351218 − s)/(1 − s). u_club is season-centred with the same season means as e (centring is linear, so centre(e + u) = centre(e) + centre(u)).

2,000 panels per s, seed 20260930: e from `simulate(seed=20260930)` at every s, and z_club ~ N(0,1) drawn once from seed 20260931 and scaled by σ_u at every s (common random numbers across s, so the curves are smooth in s). The coarse grid [0, 0.02, 0.05, 0.08, 0.1, 0.15, 0.2, 0.25, 0.3] was run inside a 0.01-step grid 0.00–0.30 (31 values), which covers every crossing; tables (i)–(ii) show the coarse grid, the CSVs hold all 31.

Corrected-interval flags use the carry-over step's fixed ρ = 0.351218 in every panel, as in its null. Power = share of panels > the null's 95th percentile (flags: ≥). "Any" = ICC-all or permutation or split-half above its null 98.333rd percentile (Bonferroni 0.05/3). Null thresholds from the carry-over step's 5,000 saved draws (numpy linear percentile):

| statistic | observed | null_p95 | null_p98_333 |
|---|---|---|---|
| icc_all | 0.102431 | 0.270596 | 0.30887 |
| icc_ge6 | 0.161965 | 0.274508 |  |
| perm_stat | 0.00068183 | 0.00096822 | 0.001113 |
| split_half_r | 0.69788 | 0.808609 | 0.85191 |
| flags_adj | 0 | 1 |  |

The flag count is discrete: under the null P(flags ≥ 1) = 0.2104, so that test's size is 0.210, not 0.05. Monte-Carlo SE of a share from 2,000 panels: ±0.0112 at 0.5, ±0.0089 at 0.8, ±0.0049 at 0.05.

Calibration: at s = 0 the simulated panels average lag-1 r 0.3455 and SD 0.04931; at s = 0.30, 0.3383 and 0.04920 (observed 0.3512, 0.05048; season-centring removes a little of both, as in the carry-over step).

## 4. Results

### (i) Power by s × statistic

| s | sigma_u_pp | rho_e | power_icc_all | power_icc_ge6 | power_perm | power_split_half | power_flags_adj | power_any_bonf |
|---|---|---|---|---|---|---|---|---|
| 0.000 | 0.000 | 0.351 | 0.038 | 0.036 | 0.044 | 0.051 | 0.207 | 0.035 |
| 0.020 | 0.714 | 0.338 | 0.058 | 0.053 | 0.053 | 0.054 | 0.215 | 0.044 |
| 0.050 | 1.129 | 0.317 | 0.091 | 0.092 | 0.085 | 0.061 | 0.238 | 0.064 |
| 0.080 | 1.428 | 0.295 | 0.139 | 0.132 | 0.118 | 0.070 | 0.271 | 0.090 |
| 0.100 | 1.596 | 0.279 | 0.177 | 0.166 | 0.140 | 0.082 | 0.300 | 0.116 |
| 0.150 | 1.955 | 0.237 | 0.273 | 0.265 | 0.203 | 0.106 | 0.356 | 0.199 |
| 0.200 | 2.258 | 0.189 | 0.398 | 0.379 | 0.283 | 0.124 | 0.434 | 0.294 |
| 0.250 | 2.524 | 0.135 | 0.545 | 0.513 | 0.362 | 0.144 | 0.507 | 0.401 |
| 0.300 | 2.765 | 0.073 | 0.688 | 0.643 | 0.452 | 0.161 | 0.584 | 0.541 |

### (ii) Upper-bound shares: share of panels at or below the observed statistic

| s | sigma_u_pp | share_icc_all_le_obs | share_perm_le_obs | share_split_half_le_obs | share_icc_ge6_le_obs |
|---|---|---|---|---|---|
| 0.000 | 0.000 | 0.321 | 0.699 | 0.769 | 0.652 |
| 0.020 | 0.714 | 0.279 | 0.680 | 0.756 | 0.605 |
| 0.050 | 1.129 | 0.220 | 0.618 | 0.730 | 0.529 |
| 0.080 | 1.428 | 0.173 | 0.564 | 0.700 | 0.454 |
| 0.100 | 1.596 | 0.143 | 0.529 | 0.678 | 0.406 |
| 0.150 | 1.955 | 0.086 | 0.432 | 0.640 | 0.290 |
| 0.200 | 2.258 | 0.048 | 0.337 | 0.597 | 0.194 |
| 0.250 | 2.524 | 0.024 | 0.261 | 0.557 | 0.119 |
| 0.300 | 2.765 | 0.014 | 0.199 | 0.531 | 0.070 |

(ICC ≥6 is shown for completeness; the bound uses ICC-all, permutation and split-half. Observed: ICC-all 0.1024, permutation 0.00068183, split-half 0.6979, ICC ≥6 0.1620.)

### (iii) Headline: MDE at 80% power and 95% upper bound

s interpolated linearly on the 0.01 grid; `grid_min_s` = smallest grid s with power ≥ 0.80. σ_u in pp = 100·σ_u. Points a season = σ_u × 92.0 (12-season coefficient; range 63.0–121.1 from its 95% CI) and × 82.5 (FINAL). A club one σ_u above average has an edge of exactly σ_u: the pp and points columns are that club's edge. Headline statistic: ICC-all (the persistence statistics' primary one).

| quantity | statistic | s | grid_min_s | sigma_u_pp | pts_92 | pts_63 | pts_121 | pts_82_5 |
|---|---|---|---|---|---|---|---|---|
| MDE at 80% power | ICC-all |  |  |  |  |  |  |  |
| MDE at 80% power | ICC ≥6 |  |  |  |  |  |  |  |
| MDE at 80% power | permutation |  |  |  |  |  |  |  |
| MDE at 80% power | split-half |  |  |  |  |  |  |  |
| MDE at 80% power | corrected flags |  |  |  |  |  |  |  |
| MDE at 80% power | any (Bonferroni) |  |  |  |  |  |  |  |
| 95% upper bound | ICC-all | 0.195 |  | 2.229 | 2.051 | 1.404 | 2.700 | 1.839 |
| 95% upper bound | permutation |  |  |  |  |  |  |  |
| 95% upper bound | split-half |  |  |  |  |  |  |  |
| 95% upper bound | ICC ≥6 |  |  |  |  |  |  |  |

Blank = not reached on s ≤ 0.30, the top of the admissible range (ρ_e = (ρ − s)/(1 − s) ≥ 0 needs s ≤ 0.351); for those statistics the MDE or bound is > 0.30, i.e. σ_u > 2.77 pp (> 2.5 points).

## 5. Verdict

On ICC-all, a lasting club edge with SD σ_u = nan pp (s = nan of the variance of c; ≈ nan points a season at 92.0, nan–nan over the coefficient's CI, nan at 82.5) is detected with 80% probability; the Bonferroni any-of-three test reaches 80% at σ_u = nan pp (s = nan). The observed ICC-all 0.1024 is below 95% of simulated panels (fewer than 5% at or below it) once σ_u exceeds 2.23 pp (s = 0.195; ≈ 2.1 points a season, 1.4–2.7; 1.8 at 82.5): that is the 95% upper bound. The permutation and split-half statistics are weaker: at s = 0.30 (σ_u 2.77 pp) their power is 0.452 and 0.161, and 0.199 and 0.531 of panels still sit at or below the observed values, so neither rules out any s ≤ 0.30; ICC ≥6 gives a bound of nan pp. At s = 0 the ICC-all test's simulated size is 0.038 (nominal 0.05). Expected result: MDE 2–3 pp → DID NOT HOLD (nan pp); upper bound ≈ 2 pp (taken as 1.5–2.5) → HELD (2.23 pp, 2.1 points vs ≈ 2 expected).

Paper sentence: "Over eight seasons we would have detected a lasting club edge of nan pp (≈ nan points a season) with 80% probability; we found none, and the data rule out a lasting edge larger than 2.2 pp (≈ 2.1 points a season) at 95%."

Inputs unchanged after the run (sha256 re-read): True. Elapsed 3 s.

Files written: `power/checks.csv`, `power/null_thresholds.csv`, `power/power_by_share.csv`, `power/upper_bound_shares.csv`, `power/headline.csv`, `power/alt_draws.csv`, `power/report.md`.

