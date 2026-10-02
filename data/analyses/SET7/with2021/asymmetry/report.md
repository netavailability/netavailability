# Is availability asymmetric? Deficit runs against carry-over

## 1. Provenance and checks

Run 2026-10-02 05:33. Read-only inputs:

- `persistence/op1_panel.csv` — sha256 `402e27fd77b2efb0…`, 160 rows
- `carryover_null.py` — sha256 `7c15f3e80a76642d…`; imported so that the null is the carry-over step's `simulate` function itself (AR(1) per club, stationary start, observed club-seasons kept, season-centred), not a re-implementation.
- `carryover_null/op3_null_draws.csv` — used only to confirm the imported null reproduces the carry-over step's draws.

**Expectation written before the first run:** Tottenham's two-season run is rare under carry-over alone — the share of simulated panels containing any run at least as deep is below 0.05. No expectation is set for asymmetry.

Targets are recomputed from this run's `club_seasons.csv` and configured seasons (`selfcheck`), tolerance 1e-09.

**(a)** rows = 160 (configured: 8 seasons × 20 = 160) → **PASS**
**(b)** pooled lag-1 Pearson correlation of c (same club, consecutive seasons, 119 pairs) = 0.351218 (recomputed: 0.351218 on 119 pairs) → **PASS**
**(c)** SD of c (ddof 1) = 0.050485 (recomputed: 0.050485) → **PASS**
**(d)** Tottenham c 2024/25 = -0.085240 (recomputed: -0.085240), 2025/26 = -0.122310 (recomputed: -0.122310) → **PASS**

**(e)** imported null vs the carry-over step's saved draws (5,000 panels, seed 20260930): max |Δ SD of c| = 1.1e-16, max |Δ lag-1 r| = 4.4e-16 → **PASS** (identical panels).

The two runs (SD units = c / 0.0505 observed SD):

| club | season | c | sd_units |
|---|---|---|---|
| Tottenham Hotspur | 2024/2025 | -0.0852 | -1.6884 |
| Tottenham Hotspur | 2025/2026 | -0.1223 | -2.4227 |
| Chelsea | 2022/2023 | -0.0978 | -1.9363 |
| Chelsea | 2023/2024 | -0.0933 | -1.8490 |

Less extreme season of each run: Tottenham -0.0852 = **-1.688 SD**; Chelsea -0.0933 = **-1.849 SD**. By the depth rule (both seasons at or below the less extreme value) Chelsea's run is deeper than Tottenham's (Chelsea's milder season -1.85 SD vs Tottenham's -1.69 SD), although Tottenham has the single deepest season (-2.42 SD). Both runs are in the FINAL seasons (2022/23–2025/26).

Self-checks against the run's own inputs: ALL PASS


## 2. Shape and ceiling

Adjusted Fisher–Pearson skewness and excess kurtosis (scipy, `bias=False`). Bootstrap 95% intervals: 2,000 resamples of club-seasons with replacement, seed 20260930, percentile method (resampling club-seasons ignores within-club carry-over, so these intervals are if anything too narrow). `null_skew_p_le_obs` = share of the 5,000 carry-over-only panels (normal shocks, symmetric) with skewness at or below the observed; `null_kurt_p_ge_obs` = share with excess kurtosis at or above.

| sample | n | skewness | skew_lo | skew_hi | excess_kurtosis | kurt_lo | kurt_hi | null_skew_p_le_obs | null_kurt_p_ge_obs |
|---|---|---|---|---|---|---|---|---|---|
| all 160 | 160 | 0.1957 | -0.1322 | 0.5314 | -0.0814 | -0.6474 | 0.5310 | 0.8408 | 0.5242 |
| FINAL 80 | 80 | 0.1315 | -0.2290 | 0.4916 | -0.5195 | -0.9939 | 0.1173 | 0.6908 | 0.8654 |

Null reference: simulated skewness mean +0.001 (2.5–97.5% -0.382 to +0.390) for 160; FINAL 80 -0.540 to +0.549.

Five most negative club-seasons:

| season | club | label | NETavailability | c | sd_units |
|---|---|---|---|---|---|
| 2025/2026 | Tottenham Hotspur | FINAL | 0.6915 | -0.1223 | -2.4227 |
| 2019/2020 | AFC Bournemouth | PAPER | 0.6960 | -0.1023 | -2.0260 |
| 2022/2023 | Chelsea | FINAL | 0.7163 | -0.0978 | -1.9363 |
| 2023/2024 | Chelsea | FINAL | 0.6712 | -0.0933 | -1.8490 |
| 2019/2020 | Aston Villa | PAPER | 0.7090 | -0.0893 | -1.7684 |

Five most positive club-seasons:

| season | club | label | NETavailability | c | sd_units |
|---|---|---|---|---|---|
| 2018/2019 | Wolverhampton Wanderers | PAPER | 0.9358 | 0.1495 | 2.9614 |
| 2023/2024 | Manchester City | FINAL | 0.8903 | 0.1258 | 2.4909 |
| 2019/2020 | Wolverhampton Wanderers | PAPER | 0.9163 | 0.1180 | 2.3377 |
| 2023/2024 | Arsenal | FINAL | 0.8778 | 0.1133 | 2.2433 |
| 2023/2024 | West Ham United | FINAL | 0.8645 | 0.1000 | 1.9799 |

Tail counts (SD = 0.05048; thresholds inclusive). `normal_expect_each` = 160 × P(Z ≥ k); `null_mean_*` = mean count per carry-over-only panel:

| k_sd | below_minus_k | above_plus_k | below_FINAL | above_FINAL | null_mean_below | null_mean_above | normal_expect_each |
|---|---|---|---|---|---|---|---|
| 1.00 | 28.00 | 24.00 | 16.00 | 14.00 | 24.42 | 24.48 | 25.38 |
| 1.50 | 10.00 | 11.00 | 6.00 | 8.00 | 9.91 | 9.96 | 10.69 |
| 2.00 | 2.00 | 4.00 | 1.00 | 2.00 | 3.23 | 3.23 | 3.64 |

Ceiling check, per season (raw NETavailability; SD units use the pooled SD of c):

| season | max_raw | league_mean | min_raw | sd_raw | max_to_1 | mean_to_1_in_sd_c | max_c_sd_units | min_c_sd_units |
|---|---|---|---|---|---|---|---|---|
| 2018/2019 | 0.9358 | 0.7863 | 0.7150 | 0.0507 | 0.0642 | 4.2330 | 2.9614 | -1.4122 |
| 2019/2020 | 0.9163 | 0.7983 | 0.6960 | 0.0560 | 0.0837 | 3.9957 | 2.3377 | -2.0260 |
| 2020/2021 | 0.8532 | 0.7922 | 0.7051 | 0.0402 | 0.1468 | 4.1154 | 1.2076 | -1.7260 |
| 2021/2022 | 0.8654 | 0.8035 | 0.7345 | 0.0421 | 0.1346 | 3.8927 | 1.2266 | -1.3663 |
| 2022/2023 | 0.8888 | 0.8141 | 0.7163 | 0.0477 | 0.1112 | 3.6832 | 1.4805 | -1.9363 |
| 2023/2024 | 0.8903 | 0.7645 | 0.6712 | 0.0731 | 0.1097 | 4.6639 | 2.4909 | -1.8490 |
| 2024/2025 | 0.8850 | 0.8050 | 0.7198 | 0.0503 | 0.1150 | 3.8617 | 1.5838 | -1.6884 |
| 2025/2026 | 0.8895 | 0.8138 | 0.6915 | 0.0456 | 0.1105 | 3.6880 | 1.4993 | -2.4227 |

Highest raw NETavailability in any season: 0.9358 (2018/2019); smallest distance from a season's maximum to 1.0 = 0.0642 = 1.27 SD of c. The league mean sits 3.68–4.66 SD below 1.0, while the most extreme positive club-season is 2.96 SD above its season mean. Across all seasons 24/11/4 club-seasons are at or above +1/+1.5/+2 SD against 28/10/2 at or below −1/−1.5/−2 SD, the largest positive and negative values are +2.96 and -2.42 SD, and skewness is +0.196. **No club is close enough to 1.0 for the upper tail to be mechanically compressed**: the nearest approach (Wolverhampton Wanderers 2018/2019, 0.9358) still leaves 0.064 = 1.27 SD of headroom, and the upper tail is as long and as populated as the lower one. The bound can only bite in the rare season where one club is already more than 2.5 SD above the mean.


## 3. Is bad stickier than good?

119 club pairs in consecutive seasons (as step 1). OLS of c(t) on c(t−1) in each subset; SE shown both conventional and clustered by club. Slope difference tested by the interaction model c(t) = a + b·c(t−1) + d·G + e·G·c(t−1) (G = 1 for the lower group), club-clustered SE; e = lower-group slope − upper-group slope, so e > 0 means deficits are stickier.

| subset | n | clubs | slope | se_ols | se_cluster | intercept | mean_c_prev | mean_c_t |
|---|---|---|---|---|---|---|---|---|
| c(t−1) < 0 | 57 | 20 | 0.5310 | 0.2147 | 0.1349 | 0.0087 | -0.0387 | -0.0119 |
| c(t−1) ≥ 0 | 62 | 22 | 0.1809 | 0.1850 | 0.1449 | 0.0094 | 0.0442 | 0.0174 |
| c(t−1) ≤ −1 SD | 20 | 13 | 0.7353 | 0.6326 | 0.7148 | 0.0258 | -0.0726 | -0.0276 |
| c(t−1) ≥ +1 SD | 22 | 14 | -0.0577 | 0.4274 | 0.5313 | 0.0275 | 0.0820 | 0.0228 |
| all pairs | 119 | 23 | 0.3407 | 0.0840 | 0.0711 | 0.0018 | 0.0045 | 0.0034 |

Slope-difference tests (lower − upper). `p_cluster` two-sided from the interaction model; `null_share_ge_obs` = one-sided share of the 5,000 carry-over-only panels (same subsets, same thresholds in c units) with a difference at least as large.

| test | n | slope_diff_lower_minus_upper | se_cluster | z | p_cluster | null_mean_diff | null_sd_diff | null_share_ge_obs | null_valid_panels |
|---|---|---|---|---|---|---|---|---|---|
| split at 0 | 119 | 0.3501 | 0.2125 | 1.6471 | 0.0995 | -0.0014 | 0.2939 | 0.1166 | 5000 |
| tails ±1 SD | 42 | 0.7930 | 0.8764 | 0.9048 | 0.3656 | 0.0086 | 0.7871 | 0.1536 | 5000 |

Mean c(t) in the season after an extreme season (`retained_share` = mean c(t) / mean c(t−1)):

| after | n | mean_c_prev | mean_c_t | mean_c_t_sd | retained_share | null_mean_c_t |
|---|---|---|---|---|---|---|
| c(t−1) ≤ −1 SD | 20 | -0.0726 | -0.0276 | -0.5457 | 0.3794 | -0.0263 |
| c(t−1) ≥ +1 SD | 22 | 0.0820 | 0.0228 | 0.4507 | 0.2774 | 0.0264 |

Magnitude asymmetry |mean after deficit| − |mean after surplus| = +0.0048 (+0.10 SD); Welch t on −c(t) after deficits vs c(t) after surpluses: t = 0.35, p = 0.727 (pairs treated as independent). Under the null the same difference has mean -0.0001 and share ≥ observed = 0.369.


## 4. Two-season runs against carry-over alone

A run is one club-pair of consecutive seasons (step 1's 119 pairs); a club with three consecutive qualifying seasons contributes two overlapping runs. Deficit run: both seasons ≤ −k·SD; surplus run: both ≥ +k·SD; SD = observed 0.05048, thresholds held fixed in c units in every simulated panel (the null's marginal SD is calibrated to it). k = 1, 1.5 and the Tottenham threshold 1.6884 (its 2024/25 value, the less extreme of its two seasons). Null: the carry-over-only AR(1), 5,000 panels, seed 20260930 (identical panels to the carry-over step).

| k | tail | observed | null_mean | null_p95 | share_ge_obs | share_any |
|---|---|---|---|---|---|---|
| 1 | deficit | 5 | 5.5544 | 10.0000 | 0.6456 | 0.9950 |
| 1 | surplus | 4 | 5.5568 | 10.0000 | 0.7960 | 0.9956 |
| 1 | deficit − surplus | 1 | -0.0024 | 5.0000 | 0.4302 |  |
| 1.5 | deficit | 2 | 1.3622 | 4.0000 | 0.3928 | 0.7176 |
| 1.5 | surplus | 1 | 1.3750 | 4.0000 | 0.7148 | 0.7148 |
| 1.5 | deficit − surplus | 1 | -0.0128 | 3.0000 | 0.3694 |  |
| Tottenham 1.688 | deficit | 2 | 0.7190 | 2.0000 | 0.1690 | 0.4900 |
| Tottenham 1.688 | surplus | 1 | 0.7476 | 3.0000 | 0.4946 | 0.4946 |
| Tottenham 1.688 | deficit − surplus | 1 | -0.0286 | 2.0000 | 0.2906 |  |

`share_ge_obs` = share of simulated panels with at least the observed count (one-sided p against carry-over alone); `share_any` = share with at least one such run.

Observed runs at k = 1 (every qualifying pair):

| club | seasons | c_first | c_second | less_extreme_sd | tail | label |
|---|---|---|---|---|---|---|
| Chelsea | 2022/2023–2023/2024 | -0.0978 | -0.0933 | -1.8490 | deficit | FINAL |
| Tottenham Hotspur | 2024/2025–2025/2026 | -0.0852 | -0.1223 | -1.6884 | deficit | FINAL |
| Newcastle United | 2019/2020–2020/2021 | -0.0803 | -0.0748 | -1.4823 | deficit | ROBUSTNESS |
| Newcastle United | 2020/2021–2021/2022 | -0.0748 | -0.0552 | -1.0929 | deficit | PAPER |
| Brighton & Hove Albion | 2023/2024–2024/2025 | -0.0525 | -0.0781 | -1.0408 | deficit | FINAL |
| Aston Villa | 2021/2022–2022/2023 | 0.0509 | 0.0693 | 1.0087 | surplus | FINAL |
| West Ham United | 2022/2023–2023/2024 | 0.0581 | 0.1000 | 1.1517 | surplus | FINAL |
| Manchester City | 2022/2023–2023/2024 | 0.0747 | 0.1258 | 1.4805 | surplus | FINAL |
| Wolverhampton Wanderers | 2018/2019–2019/2020 | 0.1495 | 0.1180 | 2.3377 | surplus | PAPER |

Runs at least as deep as the named runs (depth rule: both seasons at or below the run's less extreme value). A simulated panel is itself a 8-season, 20-club league (160 club-seasons with the observed membership), so `expected_runs_per_12x20_league` (column name kept) is the mean count per panel. `mirror_surplus_share_any` = same threshold mirrored to the surplus side (symmetric by construction; a Monte Carlo check). `share_any_per_panel_sd` = sensitivity with the threshold set in each panel's own SD.

| run | observed_runs_this_deep | share_panels_any | expected_runs_per_12x20_league | share_panels_ge_observed | mirror_surplus_share_any | share_any_per_panel_sd |
|---|---|---|---|---|---|---|
| Tottenham 2024/25–2025/26 (both ≤ -0.0852 = -1.688 SD) | 2 | 0.4900 | 0.7190 | 0.1690 | 0.4946 | 0.5398 |
| Chelsea 2022/23–2023/24 (both ≤ -0.0933 = -1.849 SD) | 1 | 0.3178 | 0.4112 | 0.3178 | 0.3250 | 0.3480 |

Deficit tail vs null (share_ge_obs < 0.05): k=1 within (0.646), k=1.5 within (0.393), k=Tottenham 1.688 within (0.169). Surplus tail: k=1 within (0.796), k=1.5 within (0.715), k=Tottenham 1.688 within (0.495).

**Deficit tail exceeds the null while the surplus tail does not: NO.** Pre-registered expectation (Tottenham-depth share < 0.05): share = 0.4900 → **NOT MET**.


