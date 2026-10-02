# How unusual is Tottenham Hotspur's availability? Two scales, two chance models

## 1. Provenance and checks

Run 2026-10-02 05:33.

Input (read-only): `club_seasons.csv` — sha256 d879dbc6a0e1026bcfaa0ad78b5e33eef08b58fb0085899e289a148a3cb54ead. Re-checked in step 4.

Definitions per club-season: c = NETavailability − season mean NETavailability (% scale); A_pm = NETabsence ÷ 38; m = season mean A_pm − A_pm (minutes scale, minutes lost per match relative to the season average; positive = fewer minutes lost). Both are "higher = better". Pairs = same `team_id` in consecutive seasons.

Expected result (written before the first run): on the % scale the tests reproduce the earlier shares. On the minutes scale Tottenham 2025/26 is the most extreme club-season of the 240, m is negatively skewed, and shares are lower than on the % scale under the normal model but closer to the % shares under the shape-preserving model. No expectation is set for whether anything falls below 0.05.

Claim rule (fixed before the first run): "rare by chance" for a test only if the share of simulated leagues is below 0.05 under BOTH chance models on BOTH scales; the headline quotes the LARGEST of the four shares.

| check | value | target | tol | result |
|---|---|---|---|---|
| rows | 160.0000 | 160.0000 | 0.0000 | PASS |
| seasons | 8.0000 | 8.0000 | 0.0000 | PASS |
| rows per season = 20 (all seasons) | 20.0000 | 20.0000 | 0.0000 | PASS |
| clubs (one team_id each) | 30.0000 | 30.0000 | 0.0000 | PASS |
| consecutive same-club pairs | 119.0000 | 119.0000 | 0.0000 | PASS |
| Tottenham m 2025/26 | -209.6237 | -209.6237 | 0.0000 | PASS |
| Tottenham m 2024/25 | -142.0724 | -142.0724 | 0.0000 | PASS |
| Chelsea m 2023/24 | -144.8961 | -144.8961 | 0.0000 | PASS |
| Tottenham c 2024/25 | -0.0852 | -0.0852 | 0.0000 | PASS |
| Tottenham c 2025/26 | -0.1223 | -0.1223 | 0.0000 | PASS |
| lag-1 Pearson r of c (119 pairs) | 0.3512 | 0.3512 | 0.0000 | PASS |
| lag-1 Pearson r of m (119 pairs) | 0.3727 | 0.3727 | 0.0000 | PASS |

Shape of each scale (160 club-seasons). SD with ddof 1; skew_G1 and excess_kurtosis_G2 are the bias-adjusted sample statistics (skew_g1 = unadjusted); skewtest_p = D'Agostino test of zero skew; THFC_2025_26_position = rank of Tottenham 2025/26 among the 160 (1 = most negative):

| statistic | c | m |
|---|---|---|
| scale | c | m |
| n | 160 | 160 |
| mean | 4.857e-18 | 5.329e-16 |
| SD | 0.05048 | 77.45 |
| skew_G1 | 0.1957 | -0.06009 |
| skew_g1 | 0.1938 | -0.05952 |
| skewtest_p | 0.3007 | 0.7489 |
| excess_kurtosis_G2 | -0.08139 | -0.1017 |
| shapiro_W | 0.9949 | 0.9967 |
| shapiro_p | 0.8595 | 0.9806 |
| min | -0.1223 | -209.6 |
| max | 0.1495 | 203.3 |
| THFC_2025_26_position | 1 | 1 |

Five lowest and five highest on c (`other_scale` = the same club-season on the other scale):

| side | k | club | season | value | value_in_sd | other_scale | label |
|---|---|---|---|---|---|---|---|
| lowest | 1 | Tottenham Hotspur | 2025/26 | -0.1223 | -2.4227 | -209.6237 | FINAL |
| lowest | 2 | AFC Bournemouth | 2019/20 | -0.1023 | -2.0260 | -182.9618 | PAPER |
| lowest | 3 | Chelsea | 2022/23 | -0.0978 | -1.9363 | -158.6421 | FINAL |
| lowest | 4 | Chelsea | 2023/24 | -0.0933 | -1.8490 | -144.8961 | FINAL |
| lowest | 5 | Aston Villa | 2019/20 | -0.0893 | -1.7684 | -148.2250 | PAPER |
| highest | 1 | Wolverhampton Wanderers | 2018/19 | 0.1495 | 2.9614 | 203.2803 | PAPER |
| highest | 2 | Manchester City | 2023/24 | 0.1258 | 2.4909 | 184.9987 | FINAL |
| highest | 3 | Wolverhampton Wanderers | 2019/20 | 0.1180 | 2.3377 | 162.6697 | PAPER |
| highest | 4 | Arsenal | 2023/24 | 0.1133 | 2.2433 | 166.4724 | FINAL |
| highest | 5 | West Ham United | 2023/24 | 0.1000 | 1.9799 | 154.0776 | FINAL |

Five lowest and five highest on m (`other_scale` = the same club-season on the other scale):

| side | k | club | season | value | value_in_sd | other_scale | label |
|---|---|---|---|---|---|---|---|
| lowest | 1 | Tottenham Hotspur | 2025/26 | -209.6237 | -2.7064 | -0.1223 | FINAL |
| lowest | 2 | AFC Bournemouth | 2019/20 | -182.9618 | -2.3622 | -0.1023 | PAPER |
| lowest | 3 | Chelsea | 2022/23 | -158.6421 | -2.0482 | -0.0978 | FINAL |
| lowest | 4 | Aston Villa | 2019/20 | -148.2250 | -1.9137 | -0.0893 | PAPER |
| lowest | 5 | Chelsea | 2023/24 | -144.8961 | -1.8707 | -0.0933 | FINAL |
| highest | 1 | Wolverhampton Wanderers | 2018/19 | 203.2803 | 2.6245 | 0.1495 | PAPER |
| highest | 2 | Manchester City | 2023/24 | 184.9987 | 2.3885 | 0.1258 | FINAL |
| highest | 3 | Arsenal | 2023/24 | 166.4724 | 2.1493 | 0.1133 | FINAL |
| highest | 4 | Wolverhampton Wanderers | 2019/20 | 162.6697 | 2.1002 | 0.1180 | PAPER |
| highest | 5 | West Ham United | 2023/24 | 154.0776 | 1.9893 | 0.1000 | FINAL |

**step 1: ALL CHECKS PASS.**


## 2. The two chance models

Four configurations = 2 scales × 2 models; each uses a fresh generator with seed 20260930 and 5,000 simulated 8-season leagues. Common skeleton: 30 clubs (sorted by name), a stationary AR(1) per club over 2018/19–2025/26 with no club effect, running through seasons a club was absent; only the 160 observed club-seasons are kept; each simulated value is then centred on its season's 20-club mean.

- **(N) normal:** x₁ ~ N(0, SD²), xₜ = ρ·xₜ₋₁ + N(0, SD²(1−ρ²)), with ρ = the scale's pooled lag-1 Pearson r (119 pairs) and SD = its SD (ddof 1). This is the carry-over step's model, re-implemented in this module with the same draw order.
- **(Q) shape-preserving:** the scale's 160 observed values → normal scores (Blom plotting position (r − 3/8)/(n + 1/4), ties averaged); ρ_q = pooled lag-1 r of the normal scores on the same 119 pairs; the AR(1) is run on the standard-normal scale (SD 1) with ρ_q; each simulated value is mapped back through the empirical quantile function (linear interpolation between the (normal score, observed value) points; beyond the lowest/highest normal score the observed min/max). Then season-centred.

A consequence of (Q) worth stating before the tests: before centring, no simulated value can lie beyond the observed min or max, so the observed extreme club-season can only be matched or exceeded through the season-centring step. For the single most extreme club-season on a scale, the Q-model share is therefore set largely by the plotting position (how much probability sits beyond the lowest normal score, here 0.0039 per cell) — see caveats.

**Validation — (N) on the % scale against the carry-over step's `simulate` on the same inputs (same seed, fresh generator):**

| check | value | target | tol | exact_match_4dp | result |
|---|---|---|---|---|---|
| Tottenham milder-season share (carry-over step's simulate) | 0.4900 | 0.4900 | 0.0000 | True | PASS |
| Tottenham sum-rule share (carry-over step's simulate) | 0.4046 | 0.4046 | 0.0000 | True | PASS |

**Calibration of each configuration** (simulated values are the season-centred panels; `rho_used` = the AR(1) coefficient fed in, ρ for N and ρ_q for Q; `sim_*_mean` = average over the 5,000 leagues of the per-league statistic; p05/p95 = 5th/95th percentiles):

| scale | model | rho_used | sd_used | obs_lag1_r | sim_lag1_r_mean | sim_lag1_r_p05 | sim_lag1_r_p95 | obs_SD | sim_SD_mean | obs_skew | sim_skew_mean | obs_exkurt | sim_exkurt_mean | obs_min | sim_min_mean | obs_max | sim_max_mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c | N | 0.3512 | 0.0505 | 0.3512 | 0.3438 | 0.1988 | 0.4837 | 0.0505 | 0.0493 | 0.1957 | 0.0010 | -0.0814 | -0.0140 | -0.1223 | -0.1315 | 0.1495 | 0.1314 |
| c | Q | 0.3567 | 1.0000 | 0.3512 | 0.3479 | 0.2006 | 0.4874 | 0.0505 | 0.0493 | 0.1957 | 0.1778 | -0.0814 | -0.1073 | -0.1223 | -0.1138 | 0.1495 | 0.1366 |
| m | N | 0.3727 | 77.4548 | 0.3727 | 0.3649 | 0.2210 | 0.5026 | 77.4548 | 75.6608 | -0.0601 | 0.0008 | -0.1017 | -0.0154 | -209.6237 | -201.6958 | 203.2803 | 201.4314 |
| m | Q | 0.3676 | 1.0000 | 0.3727 | 0.3590 | 0.2146 | 0.4979 | 77.4548 | 75.6916 | -0.0601 | -0.0543 | -0.1017 | -0.1176 | -209.6237 | -193.2721 | 203.2803 | 192.1913 |

ρ_q (normal scores): c 0.3567, m 0.3676.

**step 2: VALIDATION PASSES.**


## 3. Tests

Thresholds are the observed values in each measure's own units (not SD units), as the asymmetry step did; a simulated league counts if it contains at least one qualifying event. Comparisons use a tolerance of 1e-09. Mirror = the same threshold with the sign reversed, on the surplus side (T1: any club-season ≥ −value; T2: any pair sum ≥ −sum; T3: any pair with both seasons ≥ −milder value; T4: any season whose top gap, 1st − 2nd, is ≥ the same gap). `obs_count` = number of such events in the real data; `share_any` = share of simulated leagues with ≥ 1; `mean_count` = mean events per simulated league; `share_ge_obs` = share with at least the observed count. Overlapping pairs (three bad seasons in a row) count twice, as in the asymmetry step.

**T4 observed, % scale (c = NETavailability − season mean)** — per season, the 20th- and 19th-placed clubs and the gap between them (bottom_gap = 19th − 20th), and the top gap (1st − 2nd); ranks among the 8 seasons, 1 = largest:

| season | club_20th | value_20th | club_19th | value_19th | bottom_gap | club_1st | club_2nd | top_gap | bottom_gap_rank | top_gap_rank |
|---|---|---|---|---|---|---|---|---|---|---|
| 2018/19 | West Ham United | -0.0713 | Leicester City | -0.0505 | 0.0208 | Wolverhampton Wanderers | Chelsea | 0.0784 | 3 | 1 |
| 2019/20 | AFC Bournemouth | -0.1023 | Aston Villa | -0.0893 | 0.0130 | Wolverhampton Wanderers | Sheffield United | 0.0374 | 4 | 2 |
| 2020/21 | Liverpool | -0.0871 | Newcastle United | -0.0748 | 0.0123 | Manchester City | Fulham | 0.0105 | 5 | 5 |
| 2021/22 | Everton | -0.0690 | Leicester City | -0.0663 | 0.0027 | Tottenham Hotspur | Crystal Palace | 0.0100 | 8 | 6 |
| 2022/23 | Chelsea | -0.0978 | Nottingham Forest | -0.0739 | 0.0239 | Manchester City | Aston Villa | 0.0054 | 2 | 7 |
| 2023/24 | Chelsea | -0.0933 | Brentford | -0.0829 | 0.0104 | Manchester City | Arsenal | 0.0125 | 6 | 4 |
| 2024/25 | Tottenham Hotspur | -0.0852 | Brighton & Hove Albion | -0.0781 | 0.0071 | Nottingham Forest | Liverpool | 0.0012 | 7 | 8 |
| 2025/26 | Tottenham Hotspur | -0.1223 | Burnley | -0.0537 | 0.0686 | Brentford | Leeds United | 0.0232 | 1 | 3 |

2025/26: 20th = Tottenham Hotspur, bottom gap 0.0686, rank **1** of 8 bottom gaps; top gaps ≥ it in the real data: 1.

**T4 observed, minutes scale (m = season mean A_pm − A_pm, A_pm = NETabsence ÷ 38)** — per season, the 20th- and 19th-placed clubs and the gap between them (bottom_gap = 19th − 20th), and the top gap (1st − 2nd); ranks among the 8 seasons, 1 = largest:

| season | club_20th | value_20th | club_19th | value_19th | bottom_gap | club_1st | club_2nd | top_gap | bottom_gap_rank | top_gap_rank |
|---|---|---|---|---|---|---|---|---|---|---|
| 2018/19 | West Ham United | -113.2724 | Leicester City | -84.8513 | 28.4211 | Wolverhampton Wanderers | Chelsea | 95.5000 | 4 | 1 |
| 2019/20 | AFC Bournemouth | -182.9618 | Aston Villa | -148.2250 | 34.7368 | Wolverhampton Wanderers | Sheffield United | 48.2105 | 3 | 2 |
| 2020/21 | Liverpool | -138.0947 | Newcastle United | -131.9895 | 6.1053 | Manchester City | Manchester United | 14.3947 | 8 | 6 |
| 2021/22 | Leicester City | -125.2987 | Newcastle United | -101.9303 | 23.3684 | Tottenham Hotspur | Manchester City | 20.3947 | 5 | 4 |
| 2022/23 | Chelsea | -158.6421 | Nottingham Forest | -113.4579 | 45.1842 | Manchester City | Aston Villa | 11.8421 | 2 | 7 |
| 2023/24 | Chelsea | -144.8961 | Brentford | -135.4487 | 9.4474 | Manchester City | Arsenal | 18.5263 | 7 | 5 |
| 2024/25 | Tottenham Hotspur | -142.0724 | Brighton & Hove Albion | -127.0461 | 15.0263 | Liverpool | Nottingham Forest | 3.7895 | 6 | 8 |
| 2025/26 | Tottenham Hotspur | -209.6237 | Burnley | -78.4132 | 131.2105 | Brentford | Wolverhampton Wanderers | 32.7632 | 1 | 3 |

2025/26: 20th = Tottenham Hotspur, bottom gap 131.2105, rank **1** of 8 bottom gaps; top gaps ≥ it in the real data: 0.

**T1 single season:**

| run | side | scale | model | threshold | obs_count | share_any | mean_count | share_ge_obs |
|---|---|---|---|---|---|---|---|---|
| Tottenham 2025/26 | deficit | c | N | -0.1223 | 1 | 0.6414 | 1.0386 | 0.6414 |
| Tottenham 2025/26 | surplus mirror | c | N | 0.1223 | 2 | 0.6448 | 1.0462 | 0.2854 |
| Tottenham 2024/25 | deficit | c | N | -0.0852 | 7 | 0.9994 | 6.6696 | 0.5058 |
| Tottenham 2024/25 | surplus mirror | c | N | 0.0852 | 6 | 0.9998 | 6.6914 | 0.6804 |
| Tottenham 2025/26 | deficit | c | Q | -0.1223 | 1 | 0.2378 | 0.2822 | 0.2378 |
| Tottenham 2025/26 | surplus mirror | c | Q | 0.1223 | 2 | 0.8326 | 1.7500 | 0.5220 |
| Tottenham 2024/25 | deficit | c | Q | -0.0852 | 7 | 0.9982 | 5.7766 | 0.3658 |
| Tottenham 2024/25 | surplus mirror | c | Q | 0.0852 | 6 | 0.9998 | 7.1486 | 0.7418 |
| Tottenham 2025/26 | deficit | m | N | -209.6237 | 1 | 0.3518 | 0.4412 | 0.3518 |
| Tottenham 2025/26 | surplus mirror | m | N | 209.6237 | 0 | 0.3530 | 0.4328 | 0.3530 |
| Tottenham 2024/25 | deficit | m | N | -142.0724 | 6 | 0.9946 | 4.7850 | 0.3446 |
| Tottenham 2024/25 | surplus mirror | m | N | 142.0724 | 6 | 0.9932 | 4.8240 | 0.3504 |
| Tottenham 2025/26 | deficit | m | Q | -209.6237 | 1 | 0.2296 | 0.2644 | 0.2296 |
| Tottenham 2025/26 | surplus mirror | m | Q | 209.6237 | 0 | 0.1682 | 0.1850 | 0.1682 |
| Tottenham 2024/25 | deficit | m | Q | -142.0724 | 6 | 0.9954 | 5.0082 | 0.3902 |
| Tottenham 2024/25 | surplus mirror | m | Q | 142.0724 | 6 | 0.9956 | 5.0882 | 0.3946 |

**T2 two-season run, sum rule:**

| run | side | scale | model | threshold | obs_count | share_any | mean_count | share_ge_obs |
|---|---|---|---|---|---|---|---|---|
| Tottenham 2024/25–2025/26 | deficit | c | N | -0.2075 | 1 | 0.4046 | 0.5994 | 0.4046 |
| Tottenham 2024/25–2025/26 | surplus mirror | c | N | 0.2075 | 1 | 0.4086 | 0.6140 | 0.4086 |
| Chelsea 2022/23–2023/24 | deficit | c | N | -0.1911 | 2 | 0.6068 | 1.0646 | 0.2936 |
| Chelsea 2022/23–2023/24 | surplus mirror | c | N | 0.1911 | 2 | 0.6068 | 1.0888 | 0.2936 |
| Tottenham 2024/25–2025/26 | deficit | c | Q | -0.2075 | 1 | 0.1854 | 0.2272 | 0.1854 |
| Tottenham 2024/25–2025/26 | surplus mirror | c | Q | 0.2075 | 1 | 0.5290 | 0.8562 | 0.5290 |
| Chelsea 2022/23–2023/24 | deficit | c | Q | -0.1911 | 2 | 0.4016 | 0.5860 | 0.1372 |
| Chelsea 2022/23–2023/24 | surplus mirror | c | Q | 0.1911 | 2 | 0.7142 | 1.4548 | 0.4152 |
| Tottenham 2024/25–2025/26 | deficit | m | N | -351.6961 | 1 | 0.2224 | 0.2882 | 0.2224 |
| Tottenham 2024/25–2025/26 | surplus mirror | m | N | 351.6961 | 1 | 0.2196 | 0.2834 | 0.2196 |
| Chelsea 2022/23–2023/24 | deficit | m | N | -303.5382 | 2 | 0.5386 | 0.8924 | 0.2384 |
| Chelsea 2022/23–2023/24 | surplus mirror | m | N | 303.5382 | 1 | 0.5448 | 0.9184 | 0.5448 |
| Tottenham 2024/25–2025/26 | deficit | m | Q | -351.6961 | 1 | 0.1730 | 0.2084 | 0.1730 |
| Tottenham 2024/25–2025/26 | surplus mirror | m | Q | 351.6961 | 1 | 0.1800 | 0.2154 | 0.1800 |
| Chelsea 2022/23–2023/24 | deficit | m | Q | -303.5382 | 2 | 0.5364 | 0.8666 | 0.2272 |
| Chelsea 2022/23–2023/24 | surplus mirror | m | Q | 303.5382 | 1 | 0.5170 | 0.8178 | 0.5170 |

**T3 two-season run, milder-season rule:**

| run | side | scale | model | threshold | obs_count | share_any | mean_count | share_ge_obs |
|---|---|---|---|---|---|---|---|---|
| Tottenham 2024/25–2025/26 | deficit | c | N | -0.0852 | 2 | 0.4900 | 0.7190 | 0.1690 |
| Tottenham 2024/25–2025/26 | surplus mirror | c | N | 0.0852 | 1 | 0.4946 | 0.7476 | 0.4946 |
| Chelsea 2022/23–2023/24 | deficit | c | N | -0.0933 | 1 | 0.3178 | 0.4112 | 0.3178 |
| Chelsea 2022/23–2023/24 | surplus mirror | c | N | 0.0933 | 1 | 0.3250 | 0.4232 | 0.3250 |
| Tottenham 2024/25–2025/26 | deficit | c | Q | -0.0852 | 2 | 0.4160 | 0.5810 | 0.1240 |
| Tottenham 2024/25–2025/26 | surplus mirror | c | Q | 0.0852 | 1 | 0.5314 | 0.8322 | 0.5314 |
| Chelsea 2022/23–2023/24 | deficit | c | Q | -0.0933 | 1 | 0.2104 | 0.2540 | 0.2104 |
| Chelsea 2022/23–2023/24 | surplus mirror | c | Q | 0.0933 | 1 | 0.3858 | 0.5296 | 0.3858 |
| Tottenham 2024/25–2025/26 | deficit | m | N | -142.0724 | 2 | 0.3466 | 0.4624 | 0.0912 |
| Tottenham 2024/25–2025/26 | surplus mirror | m | N | 142.0724 | 1 | 0.3562 | 0.4814 | 0.3562 |
| Chelsea 2022/23–2023/24 | deficit | m | N | -144.8961 | 1 | 0.3144 | 0.4046 | 0.3144 |
| Chelsea 2022/23–2023/24 | surplus mirror | m | N | 144.8961 | 1 | 0.3220 | 0.4212 | 0.3220 |
| Tottenham 2024/25–2025/26 | deficit | m | Q | -142.0724 | 2 | 0.3630 | 0.4830 | 0.0932 |
| Tottenham 2024/25–2025/26 | surplus mirror | m | Q | 142.0724 | 1 | 0.3750 | 0.5154 | 0.3750 |
| Chelsea 2022/23–2023/24 | deficit | m | Q | -144.8961 | 1 | 0.3184 | 0.4100 | 0.3184 |
| Chelsea 2022/23–2023/24 | surplus mirror | m | Q | 144.8961 | 1 | 0.3420 | 0.4588 | 0.3420 |

**T4 gap to 19th:**

| run | side | scale | model | threshold | obs_count | share_any | mean_count | share_ge_obs |
|---|---|---|---|---|---|---|---|---|
| Tottenham 2025/26 gap to 19th | deficit | c | N | 0.0686 | 1 | 0.2736 | 0.3154 | 0.2736 |
| Tottenham 2025/26 gap to 19th | surplus mirror | c | N | 0.0686 | 1 | 0.2714 | 0.3084 | 0.2714 |
| Tottenham 2025/26 gap to 19th | deficit | c | Q | 0.0686 | 1 | 0.0556 | 0.0570 | 0.0556 |
| Tottenham 2025/26 gap to 19th | surplus mirror | c | Q | 0.0686 | 1 | 0.3816 | 0.4674 | 0.3816 |
| Tottenham 2025/26 gap to 19th | deficit | m | N | 131.2105 | 1 | 0.1056 | 0.1118 | 0.1056 |
| Tottenham 2025/26 gap to 19th | surplus mirror | m | N | 131.2105 | 0 | 0.1060 | 0.1096 | 0.1060 |
| Tottenham 2025/26 gap to 19th | deficit | m | Q | 131.2105 | 1 | 0.0458 | 0.0472 | 0.0458 |
| Tottenham 2025/26 gap to 19th | surplus mirror | m | Q | 131.2105 | 0 | 0.0324 | 0.0324 | 0.0324 |

**Deficit-side shares at a glance (share of simulated leagues with ≥ 1 event):**

| test | run | c·N | c·Q | m·N | m·Q |
|---|---|---|---|---|---|
| T1 | Tottenham 2025/26 | 0.6414 | 0.2378 | 0.3518 | 0.2296 |
| T1 | Tottenham 2024/25 | 0.9994 | 0.9982 | 0.9946 | 0.9954 |
| T2 | Tottenham 2024/25–2025/26 | 0.4046 | 0.1854 | 0.2224 | 0.1730 |
| T2 | Chelsea 2022/23–2023/24 | 0.6068 | 0.4016 | 0.5386 | 0.5364 |
| T3 | Tottenham 2024/25–2025/26 | 0.4900 | 0.4160 | 0.3466 | 0.3630 |
| T3 | Chelsea 2022/23–2023/24 | 0.3178 | 0.2104 | 0.3144 | 0.3184 |
| T4 | Tottenham 2025/26 gap to 19th | 0.2736 | 0.0556 | 0.1056 | 0.0458 |

**Symmetry check (surplus mirror − deficit share):** N-model differences range -0.0028 to +0.0096 (symmetric as built, differences are Monte Carlo noise); Q-model differences range -0.0614 to +0.5948 (the Q model carries the observed asymmetry of each scale). Full table in `op3_symmetry.csv`.


## 4. Verdict

Test × scale × model → share of simulated leagues with at least one event as extreme (deficit side). Columns: c = % scale, m = minutes scale; N = normal AR(1), Q = shape-preserving. Claim rule applied literally: RARE BY CHANCE only if all four shares < 0.05; headline = the largest of the four.

| test | run | c·N | c·Q | m·N | m·Q | headline_share | headline_config | verdict |
|---|---|---|---|---|---|---|---|---|
| T1 | Tottenham 2025/26 | 0.6414 | 0.2378 | 0.3518 | 0.2296 | 0.6414 | c·N | NOT SHOWN RARE |
| T1 | Tottenham 2024/25 | 0.9994 | 0.9982 | 0.9946 | 0.9954 | 0.9994 | c·N | NOT SHOWN RARE |
| T2 | Tottenham 2024/25–2025/26 | 0.4046 | 0.1854 | 0.2224 | 0.1730 | 0.4046 | c·N | NOT SHOWN RARE |
| T2 | Chelsea 2022/23–2023/24 | 0.6068 | 0.4016 | 0.5386 | 0.5364 | 0.6068 | c·N | NOT SHOWN RARE |
| T3 | Tottenham 2024/25–2025/26 | 0.4900 | 0.4160 | 0.3466 | 0.3630 | 0.4900 | c·N | NOT SHOWN RARE |
| T3 | Chelsea 2022/23–2023/24 | 0.3178 | 0.2104 | 0.3144 | 0.3184 | 0.3184 | m·Q | NOT SHOWN RARE |
| T4 | Tottenham 2025/26 gap to 19th | 0.2736 | 0.0556 | 0.1056 | 0.0458 | 0.2736 | c·N | NOT SHOWN RARE |

Claim rule, per test:

- T1 Tottenham 2025/26: **NOT SHOWN RARE** — headline share 0.6414 (c·N); others c·Q 0.2378, m·N 0.3518, m·Q 0.2296.
- T1 Tottenham 2024/25: **NOT SHOWN RARE** — headline share 0.9994 (c·N); others c·Q 0.9982, m·N 0.9946, m·Q 0.9954.
- T2 Tottenham 2024/25–2025/26: **NOT SHOWN RARE** — headline share 0.4046 (c·N); others c·Q 0.1854, m·N 0.2224, m·Q 0.1730.
- T2 Chelsea 2022/23–2023/24: **NOT SHOWN RARE** — headline share 0.6068 (c·N); others c·Q 0.4016, m·N 0.5386, m·Q 0.5364.
- T3 Tottenham 2024/25–2025/26: **NOT SHOWN RARE** — headline share 0.4900 (c·N); others c·Q 0.4160, m·N 0.3466, m·Q 0.3630.
- T3 Chelsea 2022/23–2023/24: **NOT SHOWN RARE** — headline share 0.3184 (m·Q); others c·N 0.3178, c·Q 0.2104, m·N 0.3144.
- T4 Tottenham 2025/26 gap to 19th: **NOT SHOWN RARE** — headline share 0.2736 (c·N); others c·Q 0.0556, m·N 0.1056, m·Q 0.0458.

Expectation written before the run, checked mechanically:

| expectation | result | status |
|---|---|---|
| % scale (N) reproduces the carry-over step's shares | milder 0.4900, sum 0.4046 | MET |
| Tottenham 2025/26 most extreme of 160 on m | position 1 | MET |
| m negatively skewed | G1 -0.060, skewtest p 0.75 | MET |
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


