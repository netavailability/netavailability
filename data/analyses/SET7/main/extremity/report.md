# How unusual is Tottenham Hotspur's availability? Two scales, two chance models

## 1. Provenance and checks

Run 2026-10-02 05:33.

Input (read-only): `club_seasons.csv` — sha256 62cfe635ec135c387aa7157047a37c57464bc72c806ef4819306d1a38105dfd2. Re-checked in step 4.

Definitions per club-season: c = NETavailability − season mean NETavailability (% scale); A_pm = NETabsence ÷ 38; m = season mean A_pm − A_pm (minutes scale, minutes lost per match relative to the season average; positive = fewer minutes lost). Both are "higher = better". Pairs = same `team_id` in consecutive seasons.

Expected result (written before the first run): on the % scale the tests reproduce the earlier shares. On the minutes scale Tottenham 2025/26 is the most extreme club-season of the 240, m is negatively skewed, and shares are lower than on the % scale under the normal model but closer to the % shares under the shape-preserving model. No expectation is set for whether anything falls below 0.05.

Claim rule (fixed before the first run): "rare by chance" for a test only if the share of simulated leagues is below 0.05 under BOTH chance models on BOTH scales; the headline quotes the LARGEST of the four shares.

| check | value | target | tol | result |
|---|---|---|---|---|
| rows | 140.0000 | 140.0000 | 0.0000 | PASS |
| seasons | 7.0000 | 7.0000 | 0.0000 | PASS |
| rows per season = 20 (all seasons) | 20.0000 | 20.0000 | 0.0000 | PASS |
| clubs (one team_id each) | 29.0000 | 29.0000 | 0.0000 | PASS |
| consecutive same-club pairs | 85.0000 | 85.0000 | 0.0000 | PASS |
| Tottenham m 2025/26 | -209.6237 | -209.6237 | 0.0000 | PASS |
| Tottenham m 2024/25 | -142.0724 | -142.0724 | 0.0000 | PASS |
| Chelsea m 2023/24 | -144.8961 | -144.8961 | 0.0000 | PASS |
| Tottenham c 2024/25 | -0.0852 | -0.0852 | 0.0000 | PASS |
| Tottenham c 2025/26 | -0.1223 | -0.1223 | 0.0000 | PASS |
| lag-1 Pearson r of c (85 pairs) | 0.4190 | 0.4190 | 0.0000 | PASS |
| lag-1 Pearson r of m (85 pairs) | 0.4237 | 0.4237 | 0.0000 | PASS |

Shape of each scale (140 club-seasons). SD with ddof 1; skew_G1 and excess_kurtosis_G2 are the bias-adjusted sample statistics (skew_g1 = unadjusted); skewtest_p = D'Agostino test of zero skew; THFC_2025_26_position = rank of Tottenham 2025/26 among the 140 (1 = most negative):

| statistic | c | m |
|---|---|---|
| scale | c | m |
| n | 140 | 140 |
| mean | 9.516e-18 | -5.684e-15 |
| SD | 0.05191 | 79.44 |
| skew_G1 | 0.2432 | -0.01162 |
| skew_g1 | 0.2406 | -0.0115 |
| skewtest_p | 0.229 | 0.9536 |
| excess_kurtosis_G2 | -0.1361 | -0.1555 |
| shapiro_W | 0.9937 | 0.9973 |
| shapiro_p | 0.7986 | 0.9971 |
| min | -0.1223 | -209.6 |
| max | 0.1495 | 203.3 |
| THFC_2025_26_position | 1 | 1 |

Five lowest and five highest on c (`other_scale` = the same club-season on the other scale):

| side | k | club | season | value | value_in_sd | other_scale | label |
|---|---|---|---|---|---|---|---|
| lowest | 1 | Tottenham Hotspur | 2025/26 | -0.1223 | -2.3560 | -209.6237 | FINAL |
| lowest | 2 | AFC Bournemouth | 2019/20 | -0.1023 | -1.9702 | -182.9618 | PAPER |
| lowest | 3 | Chelsea | 2022/23 | -0.0978 | -1.8830 | -158.6421 | FINAL |
| lowest | 4 | Chelsea | 2023/24 | -0.0933 | -1.7981 | -144.8961 | FINAL |
| lowest | 5 | Aston Villa | 2019/20 | -0.0893 | -1.7198 | -148.2250 | PAPER |
| highest | 1 | Wolverhampton Wanderers | 2018/19 | 0.1495 | 2.8799 | 203.2803 | PAPER |
| highest | 2 | Manchester City | 2023/24 | 0.1258 | 2.4224 | 184.9987 | FINAL |
| highest | 3 | Wolverhampton Wanderers | 2019/20 | 0.1180 | 2.2734 | 162.6697 | PAPER |
| highest | 4 | Arsenal | 2023/24 | 0.1133 | 2.1816 | 166.4724 | FINAL |
| highest | 5 | West Ham United | 2023/24 | 0.1000 | 1.9254 | 154.0776 | FINAL |

Five lowest and five highest on m (`other_scale` = the same club-season on the other scale):

| side | k | club | season | value | value_in_sd | other_scale | label |
|---|---|---|---|---|---|---|---|
| lowest | 1 | Tottenham Hotspur | 2025/26 | -209.6237 | -2.6387 | -0.1223 | FINAL |
| lowest | 2 | AFC Bournemouth | 2019/20 | -182.9618 | -2.3031 | -0.1023 | PAPER |
| lowest | 3 | Chelsea | 2022/23 | -158.6421 | -1.9969 | -0.0978 | FINAL |
| lowest | 4 | Aston Villa | 2019/20 | -148.2250 | -1.8658 | -0.0893 | PAPER |
| lowest | 5 | Chelsea | 2023/24 | -144.8961 | -1.8239 | -0.0933 | FINAL |
| highest | 1 | Wolverhampton Wanderers | 2018/19 | 203.2803 | 2.5588 | 0.1495 | PAPER |
| highest | 2 | Manchester City | 2023/24 | 184.9987 | 2.3287 | 0.1258 | FINAL |
| highest | 3 | Arsenal | 2023/24 | 166.4724 | 2.0955 | 0.1133 | FINAL |
| highest | 4 | Wolverhampton Wanderers | 2019/20 | 162.6697 | 2.0476 | 0.1180 | PAPER |
| highest | 5 | West Ham United | 2023/24 | 154.0776 | 1.9395 | 0.1000 | FINAL |

**step 1: ALL CHECKS PASS.**


## 2. The two chance models

Four configurations = 2 scales × 2 models; each uses a fresh generator with seed 20260930 and 5,000 simulated 7-season leagues. Common skeleton: 29 clubs (sorted by name), a stationary AR(1) per club over 2018/19–2025/26 with no club effect, running through seasons a club was absent; only the 140 observed club-seasons are kept; each simulated value is then centred on its season's 20-club mean.

- **(N) normal:** x₁ ~ N(0, SD²), xₜ = ρ·xₜ₋₁ + N(0, SD²(1−ρ²)), with ρ = the scale's pooled lag-1 Pearson r (85 pairs) and SD = its SD (ddof 1). This is the carry-over step's model, re-implemented in this module with the same draw order.
- **(Q) shape-preserving:** the scale's 140 observed values → normal scores (Blom plotting position (r − 3/8)/(n + 1/4), ties averaged); ρ_q = pooled lag-1 r of the normal scores on the same 85 pairs; the AR(1) is run on the standard-normal scale (SD 1) with ρ_q; each simulated value is mapped back through the empirical quantile function (linear interpolation between the (normal score, observed value) points; beyond the lowest/highest normal score the observed min/max). Then season-centred.

A consequence of (Q) worth stating before the tests: before centring, no simulated value can lie beyond the observed min or max, so the observed extreme club-season can only be matched or exceeded through the season-centring step. For the single most extreme club-season on a scale, the Q-model share is therefore set largely by the plotting position (how much probability sits beyond the lowest normal score, here 0.0045 per cell) — see caveats.

**Validation — (N) on the % scale against the carry-over step's `simulate` on the same inputs (same seed, fresh generator):**

| check | value | target | tol | exact_match_4dp | result |
|---|---|---|---|---|---|
| Tottenham milder-season share (carry-over step's simulate) | 0.4930 | 0.4930 | 0.0000 | True | PASS |
| Tottenham sum-rule share (carry-over step's simulate) | 0.4250 | 0.4250 | 0.0000 | True | PASS |

**Calibration of each configuration** (simulated values are the season-centred panels; `rho_used` = the AR(1) coefficient fed in, ρ for N and ρ_q for Q; `sim_*_mean` = average over the 5,000 leagues of the per-league statistic; p05/p95 = 5th/95th percentiles):

| scale | model | rho_used | sd_used | obs_lag1_r | sim_lag1_r_mean | sim_lag1_r_p05 | sim_lag1_r_p95 | obs_SD | sim_SD_mean | obs_skew | sim_skew_mean | obs_exkurt | sim_exkurt_mean | obs_min | sim_min_mean | obs_max | sim_max_mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c | N | 0.4190 | 0.0519 | 0.4190 | 0.4091 | 0.2496 | 0.5616 | 0.0519 | 0.0507 | 0.2432 | 0.0016 | -0.1361 | -0.0163 | -0.1223 | -0.1329 | 0.1495 | 0.1326 |
| c | Q | 0.4312 | 1.0000 | 0.4190 | 0.4194 | 0.2588 | 0.5706 | 0.0519 | 0.0507 | 0.2432 | 0.2222 | -0.1361 | -0.1607 | -0.1223 | -0.1136 | 0.1495 | 0.1365 |
| m | N | 0.4237 | 79.4429 | 0.4237 | 0.4138 | 0.2542 | 0.5659 | 79.4429 | 77.6187 | -0.0116 | 0.0016 | -0.1555 | -0.0166 | -209.6237 | -203.4066 | 203.2803 | 202.9616 |
| m | Q | 0.4283 | 1.0000 | 0.4237 | 0.4173 | 0.2585 | 0.5673 | 79.4429 | 77.6383 | -0.0116 | -0.0082 | -0.1555 | -0.1710 | -209.6237 | -193.1574 | 203.2803 | 192.1478 |

ρ_q (normal scores): c 0.4312, m 0.4283.

**step 2: VALIDATION PASSES.**


## 3. Tests

Thresholds are the observed values in each measure's own units (not SD units), as the asymmetry step did; a simulated league counts if it contains at least one qualifying event. Comparisons use a tolerance of 1e-09. Mirror = the same threshold with the sign reversed, on the surplus side (T1: any club-season ≥ −value; T2: any pair sum ≥ −sum; T3: any pair with both seasons ≥ −milder value; T4: any season whose top gap, 1st − 2nd, is ≥ the same gap). `obs_count` = number of such events in the real data; `share_any` = share of simulated leagues with ≥ 1; `mean_count` = mean events per simulated league; `share_ge_obs` = share with at least the observed count. Overlapping pairs (three bad seasons in a row) count twice, as in the asymmetry step.

**T4 observed, % scale (c = NETavailability − season mean)** — per season, the 20th- and 19th-placed clubs and the gap between them (bottom_gap = 19th − 20th), and the top gap (1st − 2nd); ranks among the 7 seasons, 1 = largest:

| season | club_20th | value_20th | club_19th | value_19th | bottom_gap | club_1st | club_2nd | top_gap | bottom_gap_rank | top_gap_rank |
|---|---|---|---|---|---|---|---|---|---|---|
| 2018/19 | West Ham United | -0.0713 | Leicester City | -0.0505 | 0.0208 | Wolverhampton Wanderers | Chelsea | 0.0784 | 3 | 1 |
| 2019/20 | AFC Bournemouth | -0.1023 | Aston Villa | -0.0893 | 0.0130 | Wolverhampton Wanderers | Sheffield United | 0.0374 | 4 | 2 |
| 2021/22 | Everton | -0.0690 | Leicester City | -0.0663 | 0.0027 | Tottenham Hotspur | Crystal Palace | 0.0100 | 7 | 5 |
| 2022/23 | Chelsea | -0.0978 | Nottingham Forest | -0.0739 | 0.0239 | Manchester City | Aston Villa | 0.0054 | 2 | 6 |
| 2023/24 | Chelsea | -0.0933 | Brentford | -0.0829 | 0.0104 | Manchester City | Arsenal | 0.0125 | 5 | 4 |
| 2024/25 | Tottenham Hotspur | -0.0852 | Brighton & Hove Albion | -0.0781 | 0.0071 | Nottingham Forest | Liverpool | 0.0012 | 6 | 7 |
| 2025/26 | Tottenham Hotspur | -0.1223 | Burnley | -0.0537 | 0.0686 | Brentford | Leeds United | 0.0232 | 1 | 3 |

2025/26: 20th = Tottenham Hotspur, bottom gap 0.0686, rank **1** of 7 bottom gaps; top gaps ≥ it in the real data: 1.

**T4 observed, minutes scale (m = season mean A_pm − A_pm, A_pm = NETabsence ÷ 38)** — per season, the 20th- and 19th-placed clubs and the gap between them (bottom_gap = 19th − 20th), and the top gap (1st − 2nd); ranks among the 7 seasons, 1 = largest:

| season | club_20th | value_20th | club_19th | value_19th | bottom_gap | club_1st | club_2nd | top_gap | bottom_gap_rank | top_gap_rank |
|---|---|---|---|---|---|---|---|---|---|---|
| 2018/19 | West Ham United | -113.2724 | Leicester City | -84.8513 | 28.4211 | Wolverhampton Wanderers | Chelsea | 95.5000 | 4 | 1 |
| 2019/20 | AFC Bournemouth | -182.9618 | Aston Villa | -148.2250 | 34.7368 | Wolverhampton Wanderers | Sheffield United | 48.2105 | 3 | 2 |
| 2021/22 | Leicester City | -125.2987 | Newcastle United | -101.9303 | 23.3684 | Tottenham Hotspur | Manchester City | 20.3947 | 5 | 4 |
| 2022/23 | Chelsea | -158.6421 | Nottingham Forest | -113.4579 | 45.1842 | Manchester City | Aston Villa | 11.8421 | 2 | 6 |
| 2023/24 | Chelsea | -144.8961 | Brentford | -135.4487 | 9.4474 | Manchester City | Arsenal | 18.5263 | 7 | 5 |
| 2024/25 | Tottenham Hotspur | -142.0724 | Brighton & Hove Albion | -127.0461 | 15.0263 | Liverpool | Nottingham Forest | 3.7895 | 6 | 7 |
| 2025/26 | Tottenham Hotspur | -209.6237 | Burnley | -78.4132 | 131.2105 | Brentford | Wolverhampton Wanderers | 32.7632 | 1 | 3 |

2025/26: 20th = Tottenham Hotspur, bottom gap 131.2105, rank **1** of 7 bottom gaps; top gaps ≥ it in the real data: 0.

**T1 single season:**

| run | side | scale | model | threshold | obs_count | share_any | mean_count | share_ge_obs |
|---|---|---|---|---|---|---|---|---|
| Tottenham 2025/26 | deficit | c | N | -0.1223 | 1 | 0.6672 | 1.1022 | 0.6672 |
| Tottenham 2025/26 | surplus mirror | c | N | 0.1223 | 2 | 0.6602 | 1.0942 | 0.3010 |
| Tottenham 2024/25 | deficit | c | N | -0.0852 | 6 | 0.9996 | 6.4228 | 0.6414 |
| Tottenham 2024/25 | surplus mirror | c | N | 0.0852 | 6 | 0.9994 | 6.4768 | 0.6510 |
| Tottenham 2025/26 | deficit | c | Q | -0.1223 | 1 | 0.2452 | 0.2878 | 0.2452 |
| Tottenham 2025/26 | surplus mirror | c | Q | 0.1223 | 2 | 0.8304 | 1.7738 | 0.5376 |
| Tottenham 2024/25 | deficit | c | Q | -0.0852 | 6 | 0.9960 | 5.3078 | 0.4382 |
| Tottenham 2024/25 | surplus mirror | c | Q | 0.0852 | 6 | 0.9996 | 7.1700 | 0.7436 |
| Tottenham 2025/26 | deficit | m | N | -209.6237 | 1 | 0.3762 | 0.4762 | 0.3762 |
| Tottenham 2025/26 | surplus mirror | m | N | 209.6237 | 0 | 0.3712 | 0.4654 | 0.3712 |
| Tottenham 2024/25 | deficit | m | N | -142.0724 | 6 | 0.9926 | 4.6618 | 0.3166 |
| Tottenham 2024/25 | surplus mirror | m | N | 142.0724 | 6 | 0.9930 | 4.6958 | 0.3250 |
| Tottenham 2025/26 | deficit | m | Q | -209.6237 | 1 | 0.2278 | 0.2642 | 0.2278 |
| Tottenham 2025/26 | surplus mirror | m | Q | 209.6237 | 0 | 0.1638 | 0.1866 | 0.1638 |
| Tottenham 2024/25 | deficit | m | Q | -142.0724 | 6 | 0.9920 | 4.6148 | 0.3134 |
| Tottenham 2024/25 | surplus mirror | m | Q | 142.0724 | 6 | 0.9956 | 5.1218 | 0.4096 |

**T2 two-season run, sum rule:**

| run | side | scale | model | threshold | obs_count | share_any | mean_count | share_ge_obs |
|---|---|---|---|---|---|---|---|---|
| Tottenham 2024/25–2025/26 | deficit | c | N | -0.2075 | 1 | 0.4250 | 0.6252 | 0.4250 |
| Tottenham 2024/25–2025/26 | surplus mirror | c | N | 0.2075 | 1 | 0.4296 | 0.6110 | 0.4296 |
| Chelsea 2022/23–2023/24 | deficit | c | N | -0.1911 | 2 | 0.6044 | 1.0318 | 0.2804 |
| Chelsea 2022/23–2023/24 | surplus mirror | c | N | 0.1911 | 2 | 0.6114 | 1.0474 | 0.2862 |
| Tottenham 2024/25–2025/26 | deficit | c | Q | -0.2075 | 1 | 0.1998 | 0.2462 | 0.1998 |
| Tottenham 2024/25–2025/26 | surplus mirror | c | Q | 0.2075 | 1 | 0.5480 | 0.8630 | 0.5480 |
| Chelsea 2022/23–2023/24 | deficit | c | Q | -0.1911 | 2 | 0.3980 | 0.5684 | 0.1326 |
| Chelsea 2022/23–2023/24 | surplus mirror | c | Q | 0.1911 | 2 | 0.7294 | 1.4272 | 0.4110 |
| Tottenham 2024/25–2025/26 | deficit | m | N | -351.6961 | 1 | 0.2330 | 0.2960 | 0.2330 |
| Tottenham 2024/25–2025/26 | surplus mirror | m | N | 351.6961 | 1 | 0.2258 | 0.2820 | 0.2258 |
| Chelsea 2022/23–2023/24 | deficit | m | N | -303.5382 | 2 | 0.5258 | 0.8396 | 0.2218 |
| Chelsea 2022/23–2023/24 | surplus mirror | m | N | 303.5382 | 1 | 0.5340 | 0.8402 | 0.5340 |
| Tottenham 2024/25–2025/26 | deficit | m | Q | -351.6961 | 1 | 0.1826 | 0.2214 | 0.1826 |
| Tottenham 2024/25–2025/26 | surplus mirror | m | Q | 351.6961 | 1 | 0.1912 | 0.2292 | 0.1912 |
| Chelsea 2022/23–2023/24 | deficit | m | Q | -303.5382 | 2 | 0.5100 | 0.7894 | 0.2028 |
| Chelsea 2022/23–2023/24 | surplus mirror | m | Q | 303.5382 | 1 | 0.5200 | 0.7994 | 0.5200 |

**T3 two-season run, milder-season rule:**

| run | side | scale | model | threshold | obs_count | share_any | mean_count | share_ge_obs |
|---|---|---|---|---|---|---|---|---|
| Tottenham 2024/25–2025/26 | deficit | c | N | -0.0852 | 2 | 0.4930 | 0.7212 | 0.1734 |
| Tottenham 2024/25–2025/26 | surplus mirror | c | N | 0.0852 | 1 | 0.4902 | 0.7224 | 0.4902 |
| Chelsea 2022/23–2023/24 | deficit | c | N | -0.0933 | 1 | 0.3270 | 0.4266 | 0.3270 |
| Chelsea 2022/23–2023/24 | surplus mirror | c | N | 0.0933 | 1 | 0.3338 | 0.4358 | 0.3338 |
| Tottenham 2024/25–2025/26 | deficit | c | Q | -0.0852 | 2 | 0.3966 | 0.5514 | 0.1196 |
| Tottenham 2024/25–2025/26 | surplus mirror | c | Q | 0.0852 | 1 | 0.5482 | 0.8646 | 0.5482 |
| Chelsea 2022/23–2023/24 | deficit | c | Q | -0.0933 | 1 | 0.2220 | 0.2670 | 0.2220 |
| Chelsea 2022/23–2023/24 | surplus mirror | c | Q | 0.0933 | 1 | 0.4116 | 0.5698 | 0.4116 |
| Tottenham 2024/25–2025/26 | deficit | m | N | -142.0724 | 2 | 0.3416 | 0.4476 | 0.0858 |
| Tottenham 2024/25–2025/26 | surplus mirror | m | N | 142.0724 | 1 | 0.3464 | 0.4578 | 0.3464 |
| Chelsea 2022/23–2023/24 | deficit | m | N | -144.8961 | 1 | 0.3096 | 0.3960 | 0.3096 |
| Chelsea 2022/23–2023/24 | surplus mirror | m | N | 144.8961 | 1 | 0.3150 | 0.4062 | 0.3150 |
| Tottenham 2024/25–2025/26 | deficit | m | Q | -142.0724 | 2 | 0.3414 | 0.4498 | 0.0870 |
| Tottenham 2024/25–2025/26 | surplus mirror | m | Q | 142.0724 | 1 | 0.3848 | 0.5230 | 0.3848 |
| Chelsea 2022/23–2023/24 | deficit | m | Q | -144.8961 | 1 | 0.3062 | 0.3928 | 0.3062 |
| Chelsea 2022/23–2023/24 | surplus mirror | m | Q | 144.8961 | 1 | 0.3574 | 0.4756 | 0.3574 |

**T4 gap to 19th:**

| run | side | scale | model | threshold | obs_count | share_any | mean_count | share_ge_obs |
|---|---|---|---|---|---|---|---|---|
| Tottenham 2025/26 gap to 19th | deficit | c | N | 0.0686 | 1 | 0.2762 | 0.3200 | 0.2762 |
| Tottenham 2025/26 gap to 19th | surplus mirror | c | N | 0.0686 | 1 | 0.2680 | 0.3048 | 0.2680 |
| Tottenham 2025/26 gap to 19th | deficit | c | Q | 0.0686 | 1 | 0.0498 | 0.0510 | 0.0498 |
| Tottenham 2025/26 gap to 19th | surplus mirror | c | Q | 0.0686 | 1 | 0.3248 | 0.3844 | 0.3248 |
| Tottenham 2025/26 gap to 19th | deficit | m | N | 131.2105 | 1 | 0.1084 | 0.1150 | 0.1084 |
| Tottenham 2025/26 gap to 19th | surplus mirror | m | N | 131.2105 | 0 | 0.1030 | 0.1080 | 0.1030 |
| Tottenham 2025/26 gap to 19th | deficit | m | Q | 131.2105 | 1 | 0.0406 | 0.0418 | 0.0406 |
| Tottenham 2025/26 gap to 19th | surplus mirror | m | Q | 131.2105 | 0 | 0.0280 | 0.0280 | 0.0280 |

**Deficit-side shares at a glance (share of simulated leagues with ≥ 1 event):**

| test | run | c·N | c·Q | m·N | m·Q |
|---|---|---|---|---|---|
| T1 | Tottenham 2025/26 | 0.6672 | 0.2452 | 0.3762 | 0.2278 |
| T1 | Tottenham 2024/25 | 0.9996 | 0.9960 | 0.9926 | 0.9920 |
| T2 | Tottenham 2024/25–2025/26 | 0.4250 | 0.1998 | 0.2330 | 0.1826 |
| T2 | Chelsea 2022/23–2023/24 | 0.6044 | 0.3980 | 0.5258 | 0.5100 |
| T3 | Tottenham 2024/25–2025/26 | 0.4930 | 0.3966 | 0.3416 | 0.3414 |
| T3 | Chelsea 2022/23–2023/24 | 0.3270 | 0.2220 | 0.3096 | 0.3062 |
| T4 | Tottenham 2025/26 gap to 19th | 0.2762 | 0.0498 | 0.1084 | 0.0406 |

**Symmetry check (surplus mirror − deficit share):** N-model differences range -0.0082 to +0.0082 (symmetric as built, differences are Monte Carlo noise); Q-model differences range -0.0640 to +0.5852 (the Q model carries the observed asymmetry of each scale). Full table in `op3_symmetry.csv`.


## 4. Verdict

Test × scale × model → share of simulated leagues with at least one event as extreme (deficit side). Columns: c = % scale, m = minutes scale; N = normal AR(1), Q = shape-preserving. Claim rule applied literally: RARE BY CHANCE only if all four shares < 0.05; headline = the largest of the four.

| test | run | c·N | c·Q | m·N | m·Q | headline_share | headline_config | verdict |
|---|---|---|---|---|---|---|---|---|
| T1 | Tottenham 2025/26 | 0.6672 | 0.2452 | 0.3762 | 0.2278 | 0.6672 | c·N | NOT SHOWN RARE |
| T1 | Tottenham 2024/25 | 0.9996 | 0.9960 | 0.9926 | 0.9920 | 0.9996 | c·N | NOT SHOWN RARE |
| T2 | Tottenham 2024/25–2025/26 | 0.4250 | 0.1998 | 0.2330 | 0.1826 | 0.4250 | c·N | NOT SHOWN RARE |
| T2 | Chelsea 2022/23–2023/24 | 0.6044 | 0.3980 | 0.5258 | 0.5100 | 0.6044 | c·N | NOT SHOWN RARE |
| T3 | Tottenham 2024/25–2025/26 | 0.4930 | 0.3966 | 0.3416 | 0.3414 | 0.4930 | c·N | NOT SHOWN RARE |
| T3 | Chelsea 2022/23–2023/24 | 0.3270 | 0.2220 | 0.3096 | 0.3062 | 0.3270 | c·N | NOT SHOWN RARE |
| T4 | Tottenham 2025/26 gap to 19th | 0.2762 | 0.0498 | 0.1084 | 0.0406 | 0.2762 | c·N | NOT SHOWN RARE |

Claim rule, per test:

- T1 Tottenham 2025/26: **NOT SHOWN RARE** — headline share 0.6672 (c·N); others c·Q 0.2452, m·N 0.3762, m·Q 0.2278.
- T1 Tottenham 2024/25: **NOT SHOWN RARE** — headline share 0.9996 (c·N); others c·Q 0.9960, m·N 0.9926, m·Q 0.9920.
- T2 Tottenham 2024/25–2025/26: **NOT SHOWN RARE** — headline share 0.4250 (c·N); others c·Q 0.1998, m·N 0.2330, m·Q 0.1826.
- T2 Chelsea 2022/23–2023/24: **NOT SHOWN RARE** — headline share 0.6044 (c·N); others c·Q 0.3980, m·N 0.5258, m·Q 0.5100.
- T3 Tottenham 2024/25–2025/26: **NOT SHOWN RARE** — headline share 0.4930 (c·N); others c·Q 0.3966, m·N 0.3416, m·Q 0.3414.
- T3 Chelsea 2022/23–2023/24: **NOT SHOWN RARE** — headline share 0.3270 (c·N); others c·Q 0.2220, m·N 0.3096, m·Q 0.3062.
- T4 Tottenham 2025/26 gap to 19th: **NOT SHOWN RARE** — headline share 0.2762 (c·N); others c·Q 0.0498, m·N 0.1084, m·Q 0.0406.

Expectation written before the run, checked mechanically:

| expectation | result | status |
|---|---|---|
| % scale (N) reproduces the carry-over step's shares | milder 0.4930, sum 0.4250 | MET |
| Tottenham 2025/26 most extreme of 140 on m | position 1 | MET |
| m negatively skewed | G1 -0.012, skewtest p 0.95 | MET |
| minutes shares lower than % shares under N | 7 of 7 tests | MET |
| minutes shares closer to % shares under Q than under N | 5 of 7 tests | PARTLY MET |

Minutes-lower-under-N tests: T1 Tottenham 2025/26; T1 Tottenham 2024/25; T2 Tottenham 2024/25–2025/26; T2 Chelsea 2022/23–2023/24; T3 Tottenham 2024/25–2025/26; T3 Chelsea 2022/23–2023/24; T4 Tottenham 2025/26 gap to 19th. Closer-under-Q tests: T1 Tottenham 2025/26; T1 Tottenham 2024/25; T2 Tottenham 2024/25–2025/26; T3 Tottenham 2024/25–2025/26; T4 Tottenham 2025/26 gap to 19th.

**Files written by this step:**

- `op1_checks.csv`
- `op1_distribution.csv`
- `op1_extremes.csv`
- `op2_calibration.csv`
- `op2_normal_scores.csv`
- `op2_validation.csv`
- `op3_observed_gaps_c.csv`
- `op3_observed_gaps_m.csv`
- `op3_symmetry.csv`
- `op3_tests.csv`
- `op4_expectation.csv`
- `op4_narrative_values.csv`
- `op4_verdict.csv`
- `report.md`
- `report.md`

Input unchanged since step 1 (SHA-256 re-check against the value printed in §1): **YES**.


