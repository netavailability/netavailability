# Is availability asymmetric? Deficit runs against carry-over

## 1. Provenance and checks

Run 2026-10-02 05:33. Read-only inputs:

- `persistence/op1_panel.csv` — sha256 `59861472db49774c…`, 140 rows
- `carryover_null.py` — sha256 `7c15f3e80a76642d…`; imported so that the null is the carry-over step's `simulate` function itself (AR(1) per club, stationary start, observed club-seasons kept, season-centred), not a re-implementation.
- `carryover_null/op3_null_draws.csv` — used only to confirm the imported null reproduces the carry-over step's draws.

**Expectation written before the first run:** Tottenham's two-season run is rare under carry-over alone — the share of simulated panels containing any run at least as deep is below 0.05. No expectation is set for asymmetry.

Targets are recomputed from this run's `club_seasons.csv` and configured seasons (`selfcheck`), tolerance 1e-09.

**(a)** rows = 140 (configured: 7 seasons × 20 = 140) → **PASS**
**(b)** pooled lag-1 Pearson correlation of c (same club, consecutive seasons, 85 pairs) = 0.418980 (recomputed: 0.418980 on 85 pairs) → **PASS**
**(c)** SD of c (ddof 1) = 0.051914 (recomputed: 0.051914) → **PASS**
**(d)** Tottenham c 2024/25 = -0.085240 (recomputed: -0.085240), 2025/26 = -0.122310 (recomputed: -0.122310) → **PASS**

**(e)** imported null vs the carry-over step's saved draws (5,000 panels, seed 20260930): max |Δ SD of c| = 1e-16, max |Δ lag-1 r| = 3.9e-16 → **PASS** (identical panels).

The two runs (SD units = c / 0.0519 observed SD):

| club | season | c | sd_units |
|---|---|---|---|
| Tottenham Hotspur | 2024/2025 | -0.0852 | -1.6420 |
| Tottenham Hotspur | 2025/2026 | -0.1223 | -2.3560 |
| Chelsea | 2022/2023 | -0.0978 | -1.8830 |
| Chelsea | 2023/2024 | -0.0933 | -1.7981 |

Less extreme season of each run: Tottenham -0.0852 = **-1.642 SD**; Chelsea -0.0933 = **-1.798 SD**. By the depth rule (both seasons at or below the less extreme value) Chelsea's run is deeper than Tottenham's (Chelsea's milder season -1.80 SD vs Tottenham's -1.64 SD), although Tottenham has the single deepest season (-2.36 SD). Both runs are in the FINAL seasons (2022/23–2025/26).

Self-checks against the run's own inputs: ALL PASS


## 2. Shape and ceiling

Adjusted Fisher–Pearson skewness and excess kurtosis (scipy, `bias=False`). Bootstrap 95% intervals: 2,000 resamples of club-seasons with replacement, seed 20260930, percentile method (resampling club-seasons ignores within-club carry-over, so these intervals are if anything too narrow). `null_skew_p_le_obs` = share of the 5,000 carry-over-only panels (normal shocks, symmetric) with skewness at or below the observed; `null_kurt_p_ge_obs` = share with excess kurtosis at or above.

| sample | n | skewness | skew_lo | skew_hi | excess_kurtosis | kurt_lo | kurt_hi | null_skew_p_le_obs | null_kurt_p_ge_obs |
|---|---|---|---|---|---|---|---|---|---|
| all 140 | 140 | 0.2432 | -0.1015 | 0.5743 | -0.1361 | -0.6758 | 0.5339 | 0.8788 | 0.5734 |
| FINAL 80 | 80 | 0.1315 | -0.2295 | 0.4688 | -0.5195 | -0.9931 | 0.1173 | 0.6906 | 0.8534 |

Null reference: simulated skewness mean +0.002 (2.5–97.5% -0.415 to +0.422) for 140; FINAL 80 -0.545 to +0.550.

Five most negative club-seasons:

| season | club | label | NETavailability | c | sd_units |
|---|---|---|---|---|---|
| 2025/2026 | Tottenham Hotspur | FINAL | 0.6915 | -0.1223 | -2.3560 |
| 2019/2020 | AFC Bournemouth | PAPER | 0.6960 | -0.1023 | -1.9702 |
| 2022/2023 | Chelsea | FINAL | 0.7163 | -0.0978 | -1.8830 |
| 2023/2024 | Chelsea | FINAL | 0.6712 | -0.0933 | -1.7981 |
| 2019/2020 | Aston Villa | PAPER | 0.7090 | -0.0893 | -1.7198 |

Five most positive club-seasons:

| season | club | label | NETavailability | c | sd_units |
|---|---|---|---|---|---|
| 2018/2019 | Wolverhampton Wanderers | PAPER | 0.9358 | 0.1495 | 2.8799 |
| 2023/2024 | Manchester City | FINAL | 0.8903 | 0.1258 | 2.4224 |
| 2019/2020 | Wolverhampton Wanderers | PAPER | 0.9163 | 0.1180 | 2.2734 |
| 2023/2024 | Arsenal | FINAL | 0.8778 | 0.1133 | 2.1816 |
| 2023/2024 | West Ham United | FINAL | 0.8645 | 0.1000 | 1.9254 |

Tail counts (SD = 0.05191; thresholds inclusive). `normal_expect_each` = 140 × P(Z ≥ k); `null_mean_*` = mean count per carry-over-only panel:

| k_sd | below_minus_k | above_plus_k | below_FINAL | above_FINAL | null_mean_below | null_mean_above | normal_expect_each |
|---|---|---|---|---|---|---|---|
| 1.00 | 23.00 | 22.00 | 15.00 | 14.00 | 21.41 | 21.40 | 22.21 |
| 1.50 | 9.00 | 11.00 | 6.00 | 8.00 | 8.68 | 8.71 | 9.35 |
| 2.00 | 1.00 | 4.00 | 1.00 | 2.00 | 2.79 | 2.86 | 3.19 |

Ceiling check, per season (raw NETavailability; SD units use the pooled SD of c):

| season | max_raw | league_mean | min_raw | sd_raw | max_to_1 | mean_to_1_in_sd_c | max_c_sd_units | min_c_sd_units |
|---|---|---|---|---|---|---|---|---|
| 2018/2019 | 0.9358 | 0.7863 | 0.7150 | 0.0507 | 0.0642 | 4.1165 | 2.8799 | -1.3733 |
| 2019/2020 | 0.9163 | 0.7983 | 0.6960 | 0.0560 | 0.0837 | 3.8857 | 2.2734 | -1.9702 |
| 2021/2022 | 0.8654 | 0.8035 | 0.7345 | 0.0421 | 0.1346 | 3.7856 | 1.1928 | -1.3286 |
| 2022/2023 | 0.8888 | 0.8141 | 0.7163 | 0.0477 | 0.1112 | 3.5818 | 1.4398 | -1.8830 |
| 2023/2024 | 0.8903 | 0.7645 | 0.6712 | 0.0731 | 0.1097 | 4.5355 | 2.4224 | -1.7981 |
| 2024/2025 | 0.8850 | 0.8050 | 0.7198 | 0.0503 | 0.1150 | 3.7555 | 1.5403 | -1.6420 |
| 2025/2026 | 0.8895 | 0.8138 | 0.6915 | 0.0456 | 0.1105 | 3.5865 | 1.4580 | -2.3560 |

Highest raw NETavailability in any season: 0.9358 (2018/2019); smallest distance from a season's maximum to 1.0 = 0.0642 = 1.24 SD of c. The league mean sits 3.58–4.54 SD below 1.0, while the most extreme positive club-season is 2.88 SD above its season mean. Across all seasons 22/11/4 club-seasons are at or above +1/+1.5/+2 SD against 23/9/1 at or below −1/−1.5/−2 SD, the largest positive and negative values are +2.88 and -2.36 SD, and skewness is +0.243. **No club is close enough to 1.0 for the upper tail to be mechanically compressed**: the nearest approach (Wolverhampton Wanderers 2018/2019, 0.9358) still leaves 0.064 = 1.24 SD of headroom, and the upper tail is as long and as populated as the lower one. The bound can only bite in the rare season where one club is already more than 2.5 SD above the mean.


## 3. Is bad stickier than good?

85 club pairs in consecutive seasons (as step 1). OLS of c(t) on c(t−1) in each subset; SE shown both conventional and clustered by club. Slope difference tested by the interaction model c(t) = a + b·c(t−1) + d·G + e·G·c(t−1) (G = 1 for the lower group), club-clustered SE; e = lower-group slope − upper-group slope, so e > 0 means deficits are stickier.

| subset | n | clubs | slope | se_ols | se_cluster | intercept | mean_c_prev | mean_c_t |
|---|---|---|---|---|---|---|---|---|
| c(t−1) < 0 | 41 | 18 | 0.3908 | 0.2812 | 0.2059 | -0.0019 | -0.0403 | -0.0177 |
| c(t−1) ≥ 0 | 44 | 17 | 0.1847 | 0.2166 | 0.1959 | 0.0169 | 0.0478 | 0.0258 |
| c(t−1) ≤ −1 SD | 13 | 10 | 0.7420 | 0.9160 | 0.9707 | 0.0241 | -0.0736 | -0.0305 |
| c(t−1) ≥ +1 SD | 17 | 12 | 0.1703 | 0.4983 | 0.6613 | 0.0106 | 0.0835 | 0.0248 |
| all pairs | 85 | 22 | 0.4152 | 0.0988 | 0.0816 | 0.0026 | 0.0053 | 0.0048 |

Slope-difference tests (lower − upper). `p_cluster` two-sided from the interaction model; `null_share_ge_obs` = one-sided share of the 5,000 carry-over-only panels (same subsets, same thresholds in c units) with a difference at least as large.

| test | n | slope_diff_lower_minus_upper | se_cluster | z | p_cluster | null_mean_diff | null_sd_diff | null_share_ge_obs | null_valid_panels |
|---|---|---|---|---|---|---|---|---|---|
| split at 0 | 85 | 0.2061 | 0.3226 | 0.6389 | 0.5229 | -0.0028 | 0.3341 | 0.2700 | 5000 |
| tails ±1 SD | 30 | 0.5717 | 1.1599 | 0.4929 | 0.6221 | 0.0067 | 0.9988 | 0.2690 | 5000 |

Mean c(t) in the season after an extreme season (`retained_share` = mean c(t) / mean c(t−1)):

| after | n | mean_c_prev | mean_c_t | mean_c_t_sd | retained_share | null_mean_c_t |
|---|---|---|---|---|---|---|
| c(t−1) ≤ −1 SD | 13 | -0.0736 | -0.0305 | -0.5872 | 0.4140 | -0.0323 |
| c(t−1) ≥ +1 SD | 17 | 0.0835 | 0.0248 | 0.4783 | 0.2973 | 0.0323 |

Magnitude asymmetry |mean after deficit| − |mean after surplus| = +0.0056 (+0.11 SD); Welch t on −c(t) after deficits vs c(t) after surpluses: t = 0.33, p = 0.743 (pairs treated as independent). Under the null the same difference has mean -0.0001 and share ≥ observed = 0.367.


## 4. Two-season runs against carry-over alone

A run is one club-pair of consecutive seasons (step 1's 85 pairs); a club with three consecutive qualifying seasons contributes two overlapping runs. Deficit run: both seasons ≤ −k·SD; surplus run: both ≥ +k·SD; SD = observed 0.05191, thresholds held fixed in c units in every simulated panel (the null's marginal SD is calibrated to it). k = 1, 1.5 and the Tottenham threshold 1.6420 (its 2024/25 value, the less extreme of its two seasons). Null: the carry-over-only AR(1), 5,000 panels, seed 20260930 (identical panels to the carry-over step).

| k | tail | observed | null_mean | null_p95 | share_ge_obs | share_any |
|---|---|---|---|---|---|---|
| 1 | deficit | 3 | 4.4044 | 8.0000 | 0.8128 | 0.9908 |
| 1 | surplus | 3 | 4.4148 | 8.0000 | 0.8184 | 0.9868 |
| 1 | deficit − surplus | 0 | -0.0104 | 4.0000 | 0.5866 |  |
| 1.5 | deficit | 2 | 1.1332 | 3.0000 | 0.3166 | 0.6558 |
| 1.5 | surplus | 1 | 1.1308 | 3.0000 | 0.6514 | 0.6514 |
| 1.5 | deficit − surplus | 1 | 0.0024 | 2.0000 | 0.3486 |  |
| Tottenham 1.642 | deficit | 2 | 0.7212 | 2.0000 | 0.1734 | 0.4930 |
| Tottenham 1.642 | surplus | 1 | 0.7224 | 2.0000 | 0.4902 | 0.4902 |
| Tottenham 1.642 | deficit − surplus | 1 | -0.0012 | 2.0000 | 0.3024 |  |

`share_ge_obs` = share of simulated panels with at least the observed count (one-sided p against carry-over alone); `share_any` = share with at least one such run.

Observed runs at k = 1 (every qualifying pair):

| club | seasons | c_first | c_second | less_extreme_sd | tail | label |
|---|---|---|---|---|---|---|
| Chelsea | 2022/2023–2023/2024 | -0.0978 | -0.0933 | -1.7981 | deficit | FINAL |
| Tottenham Hotspur | 2024/2025–2025/2026 | -0.0852 | -0.1223 | -1.6420 | deficit | FINAL |
| Brighton & Hove Albion | 2023/2024–2024/2025 | -0.0525 | -0.0781 | -1.0122 | deficit | FINAL |
| West Ham United | 2022/2023–2023/2024 | 0.0581 | 0.1000 | 1.1200 | surplus | FINAL |
| Manchester City | 2022/2023–2023/2024 | 0.0747 | 0.1258 | 1.4398 | surplus | FINAL |
| Wolverhampton Wanderers | 2018/2019–2019/2020 | 0.1495 | 0.1180 | 2.2734 | surplus | PAPER |

Runs at least as deep as the named runs (depth rule: both seasons at or below the run's less extreme value). A simulated panel is itself a 7-season, 20-club league (140 club-seasons with the observed membership), so `expected_runs_per_12x20_league` (column name kept) is the mean count per panel. `mirror_surplus_share_any` = same threshold mirrored to the surplus side (symmetric by construction; a Monte Carlo check). `share_any_per_panel_sd` = sensitivity with the threshold set in each panel's own SD.

| run | observed_runs_this_deep | share_panels_any | expected_runs_per_12x20_league | share_panels_ge_observed | mirror_surplus_share_any | share_any_per_panel_sd |
|---|---|---|---|---|---|---|
| Tottenham 2024/25–2025/26 (both ≤ -0.0852 = -1.642 SD) | 2 | 0.4930 | 0.7212 | 0.1734 | 0.4902 | 0.5424 |
| Chelsea 2022/23–2023/24 (both ≤ -0.0933 = -1.798 SD) | 1 | 0.3270 | 0.4266 | 0.3270 | 0.3338 | 0.3580 |

Deficit tail vs null (share_ge_obs < 0.05): k=1 within (0.813), k=1.5 within (0.317), k=Tottenham 1.642 within (0.173). Surplus tail: k=1 within (0.818), k=1.5 within (0.651), k=Tottenham 1.642 within (0.490).

**Deficit tail exceeds the null while the surplus tail does not: NO.** Pre-registered expectation (Tottenham-depth share < 0.05): share = 0.4930 → **NOT MET**.


