# Deficit runs: sum-rule sensitivity, squad value, points at stake

## 1. Provenance and checks

Run 2026-10-02 05:34.

Inputs (read-only; SHA-256 recorded in `op1_checks.csv` and re-checked in step 5):

- `persistence/op1_panel.csv` — sha256 402e27fd77b2efb0…
- `carryover_null.py` — sha256 7c15f3e80a76642d…
- `asymmetry/op4_named_runs.csv` — sha256 6d6d5a9020e7d921…
- `club_seasons.csv` — sha256 d879dbc6a0e1026b…
- `club_season_values.csv` — sha256 902616b4a4ca2921…

The carry-over-only null is the carry-over step's `simulate`, imported, with the same ρ and SD the asymmetry step used, 5,000 panels, seed 20260930.

Pre-registered expectation (written before the first run): under the sum rule a run at least as deep as Tottenham's still appears in a large share of simulated leagues (of the order of 0.3–0.7). A share below 0.05 is a FINDING.

| check | value | target | tol | result |
|---|---|---|---|---|
| rows | 160.0000 | 160.0000 | 0.0000 | PASS |
| SD of c (ddof 1) | 0.0505 | 0.0505 | 0.0000 | PASS |
| Tottenham Hotspur c 2024/25 | -0.0852 | -0.0852 | 0.0000 | PASS |
| Tottenham Hotspur c 2025/26 | -0.1223 | -0.1223 | 0.0000 | PASS |
| Chelsea c 2022/23 | -0.0978 | -0.0978 | 0.0000 | PASS |
| Chelsea c 2023/24 | -0.0933 | -0.0933 | 0.0000 | PASS |
| consecutive club-season pairs | 119.0000 | 119.0000 | 0.0000 | PASS |
| Tottenham milder-season share (asymmetry step's op4_named_runs.csv) | 0.4900 | 0.4900 | 0.0000 | PASS |
| club_season_values rows matched to panel (season, team_id) | 160.0000 | 160.0000 | 0.0000 | PASS |
| max |log_value_rel values file − panel| | 0.0000 | 0.0000 | 0.0000 | PASS |
| club_seasons rows matched; points and finish equal panel | 160.0000 | 160.0000 | 0.0000 | PASS |

Imported null: ρ = 0.3512, SD = 0.05048; Tottenham milder-season share = 0.4900 (asymmetry step's file 0.4900) — identical.

**step 1: ALL CHECKS PASS.**


## 2. The sum rule

All 119 club-pairs of consecutive seasons, ranked by the two-season sum of c (most negative first). SD of c = 0.05048. Top ten:

| rank | club | seasons | c_first | c_second | sum_c | sum_in_sd | label_second |
|---|---|---|---|---|---|---|---|
| 1 | Tottenham Hotspur | 2024/25–2025/26 | -0.0852 | -0.1223 | -0.2075 | -4.1111 | FINAL |
| 2 | Chelsea | 2022/23–2023/24 | -0.0978 | -0.0933 | -0.1911 | -3.7853 | FINAL |
| 3 | Newcastle United | 2019/20–2020/21 | -0.0803 | -0.0748 | -0.1551 | -3.0725 | ROBUSTNESS |
| 4 | Brighton & Hove Albion | 2023/24–2024/25 | -0.0525 | -0.0781 | -0.1307 | -2.5886 | FINAL |
| 5 | Newcastle United | 2020/21–2021/22 | -0.0748 | -0.0552 | -0.1300 | -2.5752 | PAPER |
| 6 | AFC Bournemouth | 2018/19–2019/20 | -0.0162 | -0.1023 | -0.1185 | -2.3467 | PAPER |
| 7 | Manchester United | 2023/24–2024/25 | -0.0703 | -0.0435 | -0.1139 | -2.2558 | FINAL |
| 8 | Manchester United | 2022/23–2023/24 | -0.0412 | -0.0703 | -0.1115 | -2.2086 | FINAL |
| 9 | Newcastle United | 2018/19–2019/20 | -0.0296 | -0.0803 | -0.1099 | -2.1764 | PAPER |
| 10 | Chelsea | 2021/22–2022/23 | -0.0100 | -0.0978 | -0.1077 | -2.1339 | FINAL |

Tottenham Hotspur 2024/25–2025/26: rank **1** of 119 (sum -0.2075). Chelsea 2022/23–2023/24: rank **2** (sum -0.1911). Full ranking in `op2_pairs_ranked.csv`.

Null: the carry-over-only AR(1) (ρ = 0.3512, SD 0.05048), 5,000 panels, seed 20260930 — the panels the asymmetry step used. In each panel, the same 119 pairs are scored. Deficit side: a pair qualifies if its statistic is at or below the named run's value (sum rule: pair sum ≤ run sum; single-season rule: the pair's more negative season ≤ the run's more negative season; milder-season rule: both seasons ≤ the run's milder season). Surplus mirror: the same threshold with the sign reversed, pairs at or above it (sum ≥ −sum; more positive season ≥ −value; both ≥ −value). The observed surplus count is for the real data.

| run | rule | side | threshold | threshold_sd | observed_pairs | share_panels_any | mean_pairs_per_panel | share_panels_ge_observed |
|---|---|---|---|---|---|---|---|---|
| Tottenham Hotspur 2024/25–2025/26 | sum of the two seasons | deficit | -0.2075 | -4.1111 | 1 | 0.4046 | 0.5994 | 0.4046 |
| Tottenham Hotspur 2024/25–2025/26 | sum of the two seasons | surplus mirror | 0.2075 | 4.1111 | 1 | 0.4086 | 0.6140 | 0.4086 |
| Tottenham Hotspur 2024/25–2025/26 | most negative single season of the pair | deficit | -0.1223 | -2.4227 | 1 | 0.6022 | 1.4918 | 0.6022 |
| Tottenham Hotspur 2024/25–2025/26 | most negative single season of the pair | surplus mirror | 0.1223 | 2.4227 | 3 | 0.6040 | 1.5358 | 0.2234 |
| Tottenham Hotspur 2024/25–2025/26 | milder season (asymmetry-step rule) | deficit | -0.0852 | -1.6884 | 2 | 0.4900 | 0.7190 | 0.1690 |
| Tottenham Hotspur 2024/25–2025/26 | milder season (asymmetry-step rule) | surplus mirror | 0.0852 | 1.6884 | 1 | 0.4946 | 0.7476 | 0.4946 |
| Chelsea 2022/23–2023/24 | sum of the two seasons | deficit | -0.1911 | -3.7853 | 2 | 0.6068 | 1.0646 | 0.2936 |
| Chelsea 2022/23–2023/24 | sum of the two seasons | surplus mirror | 0.1911 | 3.7853 | 2 | 0.6068 | 1.0888 | 0.2936 |
| Chelsea 2022/23–2023/24 | most negative single season of the pair | deficit | -0.0978 | -1.9363 | 4 | 0.9710 | 5.3254 | 0.7224 |
| Chelsea 2022/23–2023/24 | most negative single season of the pair | surplus mirror | 0.0978 | 1.9363 | 8 | 0.9714 | 5.3354 | 0.2152 |
| Chelsea 2022/23–2023/24 | milder season (asymmetry-step rule) | deficit | -0.0933 | -1.8490 | 1 | 0.3178 | 0.4112 | 0.3178 |
| Chelsea 2022/23–2023/24 | milder season (asymmetry-step rule) | surplus mirror | 0.0933 | 1.8490 | 1 | 0.3250 | 0.4232 | 0.3250 |

`share_panels_any` = share of simulated 8-season leagues with at least one such pair; `mean_pairs_per_panel` = mean count; `share_panels_ge_observed` = share with at least the observed count (one-sided p against carry-over alone). Overlapping pairs (three bad seasons in a row) count twice, as in the asymmetry step.

**Sum rule, Tottenham depth: share of simulated leagues with a pair as deep = 0.4046 (Chelsea depth 0.6068).** Expectation (0.3–0.7): **MET**.


## 3. Are rich clubs spared?

Squad-value rank within season from `log_value_rel` in `club_season_values.csv` (1 = highest; 20 clubs per season; no ties). Value quintile Q1 = ranks 1–4 (richest) … Q5 = ranks 17–20. Thresholds on c in units of the observed SD 0.05048 (ddof 1), as the asymmetry step. Under a uniform draw each qualifying season is equally likely to fall in any quintile (probability 1/5, since each season has exactly four clubs per quintile).

Tests: (i) chi-square against uniform with Monte Carlo p (10,000 multinomial draws, seed 20260930); (ii) exact multinomial p (full enumeration); (iii) directional: exact binomial P(Q1 count ≤ observed) with p = 1/5 (small = rich clubs under-represented = spared), and the mean value rank against 10.5 with a Monte Carlo p from 10,000 uniform draws of ranks 1–20. Caveat: repeat seasons of the same club are not independent, so these p-values are if anything too small.

**deficit ≤ −1 SD** (28 club-seasons):

| club | season | c | c_in_sd | value_rank | value_quintile | finish | label |
|---|---|---|---|---|---|---|---|
| Tottenham Hotspur | 2025/2026 | -0.1223 | -2.4227 | 6 | 2 | 17 | FINAL |
| AFC Bournemouth | 2019/2020 | -0.1023 | -2.0260 | 10 | 3 | 18 | PAPER |
| Chelsea | 2022/2023 | -0.0978 | -1.9363 | 3 | 1 | 12 | FINAL |
| Chelsea | 2023/2024 | -0.0933 | -1.8490 | 3 | 1 | 6 | FINAL |
| Aston Villa | 2019/2020 | -0.0893 | -1.7684 | 18 | 5 | 17 | PAPER |
| Liverpool | 2020/2021 | -0.0871 | -1.7260 | 2 | 1 | 3 | ROBUSTNESS |
| Tottenham Hotspur | 2024/2025 | -0.0852 | -1.6884 | 5 | 2 | 17 | FINAL |
| Brentford | 2023/2024 | -0.0829 | -1.6430 | 13 | 4 | 16 | FINAL |
| Newcastle United | 2019/2020 | -0.0803 | -1.5902 | 15 | 4 | 13 | PAPER |
| Brighton & Hove Albion | 2024/2025 | -0.0781 | -1.5478 | 9 | 3 | 8 | FINAL |
| Newcastle United | 2020/2021 | -0.0748 | -1.4823 | 11 | 3 | 12 | ROBUSTNESS |
| Nottingham Forest | 2022/2023 | -0.0739 | -1.4629 | 20 | 5 | 16 | FINAL |
| Luton Town | 2023/2024 | -0.0734 | -1.4548 | 20 | 5 | 18 | FINAL |
| West Ham United | 2018/2019 | -0.0713 | -1.4122 | 10 | 3 | 10 | PAPER |
| Southampton | 2024/2025 | -0.0712 | -1.4111 | 19 | 5 | 20 | FINAL |
| Manchester United | 2023/2024 | -0.0703 | -1.3934 | 5 | 2 | 8 | FINAL |
| Everton | 2021/2022 | -0.0690 | -1.3663 | 7 | 2 | 16 | PAPER |
| Sheffield United | 2023/2024 | -0.0673 | -1.3340 | 19 | 5 | 20 | FINAL |
| Leicester City | 2021/2022 | -0.0663 | -1.3128 | 8 | 2 | 8 | PAPER |
| Arsenal | 2019/2020 | -0.0618 | -1.2237 | 6 | 2 | 8 | PAPER |
| Newcastle United | 2023/2024 | -0.0611 | -1.2112 | 7 | 2 | 7 | FINAL |
| Newcastle United | 2021/2022 | -0.0552 | -1.0929 | 14 | 4 | 11 | PAPER |
| Burnley | 2025/2026 | -0.0537 | -1.0639 | 19 | 5 | 19 | FINAL |
| Ipswich Town | 2024/2025 | -0.0535 | -1.0605 | 20 | 5 | 19 | FINAL |
| Sheffield United | 2020/2021 | -0.0533 | -1.0565 | 17 | 5 | 20 | ROBUSTNESS |
| Brighton & Hove Albion | 2023/2024 | -0.0525 | -1.0408 | 8 | 2 | 11 | FINAL |
| Liverpool | 2022/2023 | -0.0516 | -1.0212 | 2 | 1 | 5 | FINAL |
| Leicester City | 2018/2019 | -0.0505 | -1.0002 | 8 | 2 | 9 | PAPER |

**deficit ≤ −1.5 SD** (10 club-seasons):

| club | season | c | c_in_sd | value_rank | value_quintile | finish | label |
|---|---|---|---|---|---|---|---|
| Tottenham Hotspur | 2025/2026 | -0.1223 | -2.4227 | 6 | 2 | 17 | FINAL |
| AFC Bournemouth | 2019/2020 | -0.1023 | -2.0260 | 10 | 3 | 18 | PAPER |
| Chelsea | 2022/2023 | -0.0978 | -1.9363 | 3 | 1 | 12 | FINAL |
| Chelsea | 2023/2024 | -0.0933 | -1.8490 | 3 | 1 | 6 | FINAL |
| Aston Villa | 2019/2020 | -0.0893 | -1.7684 | 18 | 5 | 17 | PAPER |
| Liverpool | 2020/2021 | -0.0871 | -1.7260 | 2 | 1 | 3 | ROBUSTNESS |
| Tottenham Hotspur | 2024/2025 | -0.0852 | -1.6884 | 5 | 2 | 17 | FINAL |
| Brentford | 2023/2024 | -0.0829 | -1.6430 | 13 | 4 | 16 | FINAL |
| Newcastle United | 2019/2020 | -0.0803 | -1.5902 | 15 | 4 | 13 | PAPER |
| Brighton & Hove Albion | 2024/2025 | -0.0781 | -1.5478 | 9 | 3 | 8 | FINAL |

**surplus ≥ +1 SD** (24 club-seasons):

| club | season | c | c_in_sd | value_rank | value_quintile | finish | label |
|---|---|---|---|---|---|---|---|
| Wolverhampton Wanderers | 2018/2019 | 0.1495 | 2.9614 | 17 | 5 | 7 | PAPER |
| Manchester City | 2023/2024 | 0.1258 | 2.4909 | 1 | 1 | 1 | FINAL |
| Wolverhampton Wanderers | 2019/2020 | 0.1180 | 2.3377 | 12 | 3 | 7 | PAPER |
| Arsenal | 2023/2024 | 0.1133 | 2.2433 | 2 | 1 | 2 | FINAL |
| West Ham United | 2023/2024 | 0.1000 | 1.9799 | 10 | 3 | 9 | FINAL |
| Everton | 2023/2024 | 0.0944 | 1.8690 | 12 | 3 | 15 | FINAL |
| Fulham | 2023/2024 | 0.0836 | 1.6550 | 17 | 5 | 13 | FINAL |
| Wolverhampton Wanderers | 2023/2024 | 0.0817 | 1.6174 | 11 | 3 | 14 | FINAL |
| Sheffield United | 2019/2020 | 0.0806 | 1.5969 | 20 | 5 | 9 | PAPER |
| Nottingham Forest | 2024/2025 | 0.0800 | 1.5838 | 14 | 4 | 7 | FINAL |
| Liverpool | 2024/2025 | 0.0788 | 1.5601 | 4 | 1 | 1 | FINAL |
| Brentford | 2025/2026 | 0.0757 | 1.4993 | 12 | 3 | 9 | FINAL |
| Manchester City | 2022/2023 | 0.0747 | 1.4805 | 1 | 1 | 1 | FINAL |
| Southampton | 2019/2020 | 0.0742 | 1.4701 | 11 | 3 | 11 | PAPER |
| Chelsea | 2018/2019 | 0.0711 | 1.4084 | 2 | 1 | 3 | PAPER |
| Aston Villa | 2022/2023 | 0.0693 | 1.3736 | 7 | 2 | 7 | FINAL |
| Crystal Palace | 2024/2025 | 0.0635 | 1.2570 | 11 | 3 | 12 | FINAL |
| Crystal Palace | 2018/2019 | 0.0623 | 1.2341 | 13 | 4 | 12 | PAPER |
| Tottenham Hotspur | 2021/2022 | 0.0619 | 1.2266 | 5 | 2 | 4 | PAPER |
| Manchester City | 2020/2021 | 0.0610 | 1.2076 | 1 | 1 | 1 | ROBUSTNESS |
| West Ham United | 2022/2023 | 0.0581 | 1.1517 | 10 | 3 | 14 | FINAL |
| Leeds United | 2025/2026 | 0.0525 | 1.0397 | 18 | 5 | 14 | FINAL |
| Crystal Palace | 2021/2022 | 0.0519 | 1.0285 | 16 | 4 | 12 | PAPER |
| Aston Villa | 2021/2022 | 0.0509 | 1.0087 | 9 | 3 | 14 | PAPER |

**surplus ≥ +1.5 SD** (11 club-seasons):

| club | season | c | c_in_sd | value_rank | value_quintile | finish | label |
|---|---|---|---|---|---|---|---|
| Wolverhampton Wanderers | 2018/2019 | 0.1495 | 2.9614 | 17 | 5 | 7 | PAPER |
| Manchester City | 2023/2024 | 0.1258 | 2.4909 | 1 | 1 | 1 | FINAL |
| Wolverhampton Wanderers | 2019/2020 | 0.1180 | 2.3377 | 12 | 3 | 7 | PAPER |
| Arsenal | 2023/2024 | 0.1133 | 2.2433 | 2 | 1 | 2 | FINAL |
| West Ham United | 2023/2024 | 0.1000 | 1.9799 | 10 | 3 | 9 | FINAL |
| Everton | 2023/2024 | 0.0944 | 1.8690 | 12 | 3 | 15 | FINAL |
| Fulham | 2023/2024 | 0.0836 | 1.6550 | 17 | 5 | 13 | FINAL |
| Wolverhampton Wanderers | 2023/2024 | 0.0817 | 1.6174 | 11 | 3 | 14 | FINAL |
| Sheffield United | 2019/2020 | 0.0806 | 1.5969 | 20 | 5 | 9 | PAPER |
| Nottingham Forest | 2024/2025 | 0.0800 | 1.5838 | 14 | 4 | 7 | FINAL |
| Liverpool | 2024/2025 | 0.0788 | 1.5601 | 4 | 1 | 1 | FINAL |

Distribution by value quintile and tests:

| set | n | Q1 | Q2 | Q3 | Q4 | Q5 | expected_per_q | chi2 | p_chi2_mc | p_exact_multinomial | p_Q1_le_obs | mean_value_rank | p_mean_rank_two_sided |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| deficit ≤ −1 SD | 28 | 4 | 9 | 4 | 3 | 8 | 5.6000 | 5.2143 | 0.2854 | 0.2863 | 0.3149 | 10.8571 | 0.7572 |
| deficit ≤ −1.5 SD | 10 | 3 | 2 | 2 | 2 | 1 | 2.0000 | 1.0000 | 0.9878 | 0.9884 | 0.8791 | 8.4000 | 0.2624 |
| surplus ≥ +1 SD | 24 | 6 | 2 | 9 | 3 | 4 | 4.8000 | 6.4167 | 0.1802 | 0.2068 | 0.8111 | 9.8333 | 0.5790 |
| surplus ≥ +1.5 SD | 11 | 3 | 0 | 4 | 1 | 3 | 2.2000 | 4.9091 | 0.3666 | 0.2828 | 0.8389 | 10.9091 | 0.8414 |

**Deep-deficit seasons (≤ −1 SD): 4 of 28 in the richest quintile (expected 5.6); P(Q1 ≤ 4) = 0.315; spread across quintiles p = 0.285 (MC) / 0.286 (exact). At ≤ −1.5 SD: 3 of 10 in Q1, p = 0.988 / 0.988.**


## 4. Points context

Source `club_seasons.csv` (points after deductions: 2023/24 Everton −8, Nottingham Forest −4). No model estimation.

| season | pts_4th | pts_5th | pts_17th | pts_18th |
|---|---|---|---|---|
| 2022/23 | 71 | 67 | 36 | 34 |
| 2023/24 | 68 | 66 | 32 | 26 |
| 2024/25 | 69 | 66 | 38 | 25 |
| 2025/26 | 65 | 60 | 41 | 39 |

| season | THFC_finish | THFC_pts | THFC_minus_18th | THFC_minus_4th | CFC_finish | CFC_pts | CFC_minus_18th | CFC_minus_4th |
|---|---|---|---|---|---|---|---|---|
| 2022/23 | 8 | 60 | 26 | -11 | 12 | 44 | 10 | -27 |
| 2023/24 | 5 | 66 | 40 | -2 | 6 | 63 | 37 | -5 |
| 2024/25 | 17 | 38 | 13 | -31 | 4 | 69 | 44 | 0 |
| 2025/26 | 17 | 41 | 2 | -24 | 10 | 52 | 13 | -13 |

`_minus_18th` = club points − 18th-placed points (positive = margin above the drop zone); `_minus_4th` = club points − 4th-placed points (negative = short of the top four).

**Availability-associated points, association not causation.** c × 91.71 (points per unit of c from this run: points ~ log squad value + c + season FE over all 8 seasons of the variant, HC3, as the battery's points decomposition; the `_lo`/`_hi` columns use its 95% interval 54.9–128.5). c is centred on the season mean, so these are points relative to a league-average availability season.

| club | season | c | points_assoc | points_assoc_lo | points_assoc_hi | actual_points | finish |
|---|---|---|---|---|---|---|---|
| Tottenham Hotspur | 2024/25 | -0.0852 | -7.8 | -4.7 | -11.0 | 38 | 17 |
| Tottenham Hotspur | 2025/26 | -0.1223 | -11.2 | -6.7 | -15.7 | 41 | 17 |
| Chelsea | 2022/23 | -0.0978 | -9.0 | -5.4 | -12.6 | 44 | 12 |
| Chelsea | 2023/24 | -0.0933 | -8.6 | -5.1 | -12.0 | 63 | 6 |


## 5. Verdict

**(1) Does the sum rule change the asymmetry step's conclusion?** No. Ranked by the two-season sum, Tottenham 2024/25–2025/26 is 1 of 119 and Chelsea 2022/23–2023/24 is 2. Under carry-over alone, a pair at least as deep by sum appears in 40% of simulated leagues for Tottenham's depth and 61% for Chelsea's (milder-season rule: 49% and 32%; most-negative-season rule: 60% and 97%). The surplus mirrors are 41% and 61%, so the null is symmetric as built. Expectation (0.3–0.7 under the sum rule): MET.

**(2) Are rich clubs hit by deep deficits as often as others?** The data do not show that they are spared. Of 28 club-seasons at or below −1 SD, 4 belong to the four highest-value squads of their season (expected 5.6 under a uniform draw; quintiles Q1–Q5 4/9/4/3/8; chi-square MC p = 0.285, exact p = 0.286; P(Q1 ≤ observed) = 0.315). At −1.5 SD: 3 of 10 (p = 0.988). Surplus seasons ≥ +1 SD: 6 of 24 in Q1 (p = 0.207).

**(3) Points at stake.** At 91.71 points per unit (association, not causation; the run's all-seasons coefficient), the named deficits are associated with -7.8 and -11.2 points for Tottenham (2024/25, 2025/26) and -9.0 and -8.6 for Chelsea (2022/23, 2023/24); on the interval 54.9–128.5 the Tottenham 2025/26 figure runs -15.7 to -6.7. Tottenham finished 17 and 17, +13 and +2 points from 18th place, -31 and -24 from 4th. Chelsea finished 12 and 6, -27 and -5 from 4th.

The values of c used, as in `op4_named_points.csv`: Tottenham Hotspur 2024/25 c = -0.0852; Tottenham Hotspur 2025/26 c = -0.1223; Chelsea 2022/23 c = -0.0978; Chelsea 2023/24 c = -0.0933.

Tottenham 2025/26 finished 2 points above 18th place; the availability-associated figure for that season (-11.2, interval -15.7 to -6.7) is larger than that margin. That is an association, not a claim that better availability would have kept them further clear.

**Sentences a paper could use (conservative first):**

1. "Two-season runs of low availability as deep as Tottenham Hotspur's in 2024/25–2025/26 are common under one-season carry-over alone, whether depth is judged by the milder season (49% of simulated 8-season leagues) or by the two-season total (40%); we therefore do not treat such runs as evidence of a persistent club effect."
2. "Low-availability seasons (at least one SD below the season mean) fall across the squad-value distribution as a uniform draw would give (4 of 28 in the top value quintile against 5.6 expected; exact multinomial p = 0.29); the richest clubs are not measurably spared."
3. "On the all-seasons association of 91.7 points per unit of availability (95% interval 54.9–128.5), Tottenham's 2025/26 availability deficit corresponds to about 11 points (range 7–16) below a league-average availability season; this is an association, not an estimate of causal effect."

**Files written by this step:**

- `op1_checks.csv`
- `op2_null.csv`
- `op2_pairs_ranked.csv`
- `op3_listed_seasons.csv`
- `op3_quintile_tests.csv`
- `op4_named_points.csv`
- `op4_points_context.csv`
- `report.md`
- `report.md`

Read-only inputs unchanged since step 1 (SHA-256 re-check): **YES**.


