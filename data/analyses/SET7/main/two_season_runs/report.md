# Deficit runs: sum-rule sensitivity, squad value, points at stake

## 1. Provenance and checks

Run 2026-10-02 05:34.

Inputs (read-only; SHA-256 recorded in `op1_checks.csv` and re-checked in step 5):

- `persistence/op1_panel.csv` — sha256 59861472db49774c…
- `carryover_null.py` — sha256 7c15f3e80a76642d…
- `asymmetry/op4_named_runs.csv` — sha256 f8c537d4cac8dd72…
- `club_seasons.csv` — sha256 62cfe635ec135c38…
- `club_season_values.csv` — sha256 02535125fed13de5…

The carry-over-only null is the carry-over step's `simulate`, imported, with the same ρ and SD the asymmetry step used, 5,000 panels, seed 20260930.

Pre-registered expectation (written before the first run): under the sum rule a run at least as deep as Tottenham's still appears in a large share of simulated leagues (of the order of 0.3–0.7). A share below 0.05 is a FINDING.

| check | value | target | tol | result |
|---|---|---|---|---|
| rows | 140.0000 | 140.0000 | 0.0000 | PASS |
| SD of c (ddof 1) | 0.0519 | 0.0519 | 0.0000 | PASS |
| Tottenham Hotspur c 2024/25 | -0.0852 | -0.0852 | 0.0000 | PASS |
| Tottenham Hotspur c 2025/26 | -0.1223 | -0.1223 | 0.0000 | PASS |
| Chelsea c 2022/23 | -0.0978 | -0.0978 | 0.0000 | PASS |
| Chelsea c 2023/24 | -0.0933 | -0.0933 | 0.0000 | PASS |
| consecutive club-season pairs | 85.0000 | 85.0000 | 0.0000 | PASS |
| Tottenham milder-season share (asymmetry step's op4_named_runs.csv) | 0.4930 | 0.4930 | 0.0000 | PASS |
| club_season_values rows matched to panel (season, team_id) | 140.0000 | 140.0000 | 0.0000 | PASS |
| max |log_value_rel values file − panel| | 0.0000 | 0.0000 | 0.0000 | PASS |
| club_seasons rows matched; points and finish equal panel | 140.0000 | 140.0000 | 0.0000 | PASS |

Imported null: ρ = 0.4190, SD = 0.05191; Tottenham milder-season share = 0.4930 (asymmetry step's file 0.4930) — identical.

**step 1: ALL CHECKS PASS.**


## 2. The sum rule

All 85 club-pairs of consecutive seasons, ranked by the two-season sum of c (most negative first). SD of c = 0.05191. Top ten:

| rank | club | seasons | c_first | c_second | sum_c | sum_in_sd | label_second |
|---|---|---|---|---|---|---|---|
| 1 | Tottenham Hotspur | 2024/25–2025/26 | -0.0852 | -0.1223 | -0.2075 | -3.9980 | FINAL |
| 2 | Chelsea | 2022/23–2023/24 | -0.0978 | -0.0933 | -0.1911 | -3.6811 | FINAL |
| 3 | Brighton & Hove Albion | 2023/24–2024/25 | -0.0525 | -0.0781 | -0.1307 | -2.5174 | FINAL |
| 4 | AFC Bournemouth | 2018/19–2019/20 | -0.0162 | -0.1023 | -0.1185 | -2.2822 | PAPER |
| 5 | Manchester United | 2023/24–2024/25 | -0.0703 | -0.0435 | -0.1139 | -2.1937 | FINAL |
| 6 | Manchester United | 2022/23–2023/24 | -0.0412 | -0.0703 | -0.1115 | -2.1478 | FINAL |
| 7 | Newcastle United | 2018/19–2019/20 | -0.0296 | -0.0803 | -0.1099 | -2.1165 | PAPER |
| 8 | Chelsea | 2021/22–2022/23 | -0.0100 | -0.0978 | -0.1077 | -2.0752 | FINAL |
| 9 | Arsenal | 2018/19–2019/20 | -0.0408 | -0.0618 | -0.1026 | -1.9759 | PAPER |
| 10 | Chelsea | 2023/24–2024/25 | -0.0933 | -0.0084 | -0.1018 | -1.9607 | FINAL |

Tottenham Hotspur 2024/25–2025/26: rank **1** of 85 (sum -0.2075). Chelsea 2022/23–2023/24: rank **2** (sum -0.1911). Full ranking in `op2_pairs_ranked.csv`.

Null: the carry-over-only AR(1) (ρ = 0.4190, SD 0.05191), 5,000 panels, seed 20260930 — the panels the asymmetry step used. In each panel, the same 85 pairs are scored. Deficit side: a pair qualifies if its statistic is at or below the named run's value (sum rule: pair sum ≤ run sum; single-season rule: the pair's more negative season ≤ the run's more negative season; milder-season rule: both seasons ≤ the run's milder season). Surplus mirror: the same threshold with the sign reversed, pairs at or above it (sum ≥ −sum; more positive season ≥ −value; both ≥ −value). The observed surplus count is for the real data.

| run | rule | side | threshold | threshold_sd | observed_pairs | share_panels_any | mean_pairs_per_panel | share_panels_ge_observed |
|---|---|---|---|---|---|---|---|---|
| Tottenham Hotspur 2024/25–2025/26 | sum of the two seasons | deficit | -0.2075 | -3.9980 | 1 | 0.4250 | 0.6252 | 0.4250 |
| Tottenham Hotspur 2024/25–2025/26 | sum of the two seasons | surplus mirror | 0.2075 | 3.9980 | 1 | 0.4296 | 0.6110 | 0.4296 |
| Tottenham Hotspur 2024/25–2025/26 | most negative single season of the pair | deficit | -0.1223 | -2.3560 | 1 | 0.6074 | 1.2836 | 0.6074 |
| Tottenham Hotspur 2024/25–2025/26 | most negative single season of the pair | surplus mirror | 0.1223 | 2.3560 | 3 | 0.6082 | 1.2718 | 0.1720 |
| Tottenham Hotspur 2024/25–2025/26 | milder season (asymmetry-step rule) | deficit | -0.0852 | -1.6420 | 2 | 0.4930 | 0.7212 | 0.1734 |
| Tottenham Hotspur 2024/25–2025/26 | milder season (asymmetry-step rule) | surplus mirror | 0.0852 | 1.6420 | 1 | 0.4902 | 0.7224 | 0.4902 |
| Chelsea 2022/23–2023/24 | sum of the two seasons | deficit | -0.1911 | -3.6811 | 2 | 0.6044 | 1.0318 | 0.2804 |
| Chelsea 2022/23–2023/24 | sum of the two seasons | surplus mirror | 0.1911 | 3.6811 | 2 | 0.6114 | 1.0474 | 0.2862 |
| Chelsea 2022/23–2023/24 | most negative single season of the pair | deficit | -0.0978 | -1.8830 | 4 | 0.9614 | 4.1920 | 0.5826 |
| Chelsea 2022/23–2023/24 | most negative single season of the pair | surplus mirror | 0.0978 | 1.8830 | 7 | 0.9652 | 4.2754 | 0.1714 |
| Chelsea 2022/23–2023/24 | milder season (asymmetry-step rule) | deficit | -0.0933 | -1.7981 | 1 | 0.3270 | 0.4266 | 0.3270 |
| Chelsea 2022/23–2023/24 | milder season (asymmetry-step rule) | surplus mirror | 0.0933 | 1.7981 | 1 | 0.3338 | 0.4358 | 0.3338 |

`share_panels_any` = share of simulated 7-season leagues with at least one such pair; `mean_pairs_per_panel` = mean count; `share_panels_ge_observed` = share with at least the observed count (one-sided p against carry-over alone). Overlapping pairs (three bad seasons in a row) count twice, as in the asymmetry step.

**Sum rule, Tottenham depth: share of simulated leagues with a pair as deep = 0.4250 (Chelsea depth 0.6044).** Expectation (0.3–0.7): **MET**.


## 3. Are rich clubs spared?

Squad-value rank within season from `log_value_rel` in `club_season_values.csv` (1 = highest; 20 clubs per season; no ties). Value quintile Q1 = ranks 1–4 (richest) … Q5 = ranks 17–20. Thresholds on c in units of the observed SD 0.05191 (ddof 1), as the asymmetry step. Under a uniform draw each qualifying season is equally likely to fall in any quintile (probability 1/5, since each season has exactly four clubs per quintile).

Tests: (i) chi-square against uniform with Monte Carlo p (10,000 multinomial draws, seed 20260930); (ii) exact multinomial p (full enumeration); (iii) directional: exact binomial P(Q1 count ≤ observed) with p = 1/5 (small = rich clubs under-represented = spared), and the mean value rank against 10.5 with a Monte Carlo p from 10,000 uniform draws of ranks 1–20. Caveat: repeat seasons of the same club are not independent, so these p-values are if anything too small.

**deficit ≤ −1 SD** (23 club-seasons):

| club | season | c | c_in_sd | value_rank | value_quintile | finish | label |
|---|---|---|---|---|---|---|---|
| Tottenham Hotspur | 2025/2026 | -0.1223 | -2.3560 | 6 | 2 | 17 | FINAL |
| AFC Bournemouth | 2019/2020 | -0.1023 | -1.9702 | 10 | 3 | 18 | PAPER |
| Chelsea | 2022/2023 | -0.0978 | -1.8830 | 3 | 1 | 12 | FINAL |
| Chelsea | 2023/2024 | -0.0933 | -1.7981 | 3 | 1 | 6 | FINAL |
| Aston Villa | 2019/2020 | -0.0893 | -1.7198 | 18 | 5 | 17 | PAPER |
| Tottenham Hotspur | 2024/2025 | -0.0852 | -1.6420 | 5 | 2 | 17 | FINAL |
| Brentford | 2023/2024 | -0.0829 | -1.5978 | 13 | 4 | 16 | FINAL |
| Newcastle United | 2019/2020 | -0.0803 | -1.5464 | 15 | 4 | 13 | PAPER |
| Brighton & Hove Albion | 2024/2025 | -0.0781 | -1.5052 | 9 | 3 | 8 | FINAL |
| Nottingham Forest | 2022/2023 | -0.0739 | -1.4227 | 20 | 5 | 16 | FINAL |
| Luton Town | 2023/2024 | -0.0734 | -1.4148 | 20 | 5 | 18 | FINAL |
| West Ham United | 2018/2019 | -0.0713 | -1.3733 | 10 | 3 | 10 | PAPER |
| Southampton | 2024/2025 | -0.0712 | -1.3723 | 19 | 5 | 20 | FINAL |
| Manchester United | 2023/2024 | -0.0703 | -1.3550 | 5 | 2 | 8 | FINAL |
| Everton | 2021/2022 | -0.0690 | -1.3286 | 7 | 2 | 16 | PAPER |
| Sheffield United | 2023/2024 | -0.0673 | -1.2973 | 19 | 5 | 20 | FINAL |
| Leicester City | 2021/2022 | -0.0663 | -1.2766 | 8 | 2 | 8 | PAPER |
| Arsenal | 2019/2020 | -0.0618 | -1.1901 | 6 | 2 | 8 | PAPER |
| Newcastle United | 2023/2024 | -0.0611 | -1.1778 | 7 | 2 | 7 | FINAL |
| Newcastle United | 2021/2022 | -0.0552 | -1.0628 | 14 | 4 | 11 | PAPER |
| Burnley | 2025/2026 | -0.0537 | -1.0346 | 19 | 5 | 19 | FINAL |
| Ipswich Town | 2024/2025 | -0.0535 | -1.0313 | 20 | 5 | 19 | FINAL |
| Brighton & Hove Albion | 2023/2024 | -0.0525 | -1.0122 | 8 | 2 | 11 | FINAL |

**deficit ≤ −1.5 SD** (9 club-seasons):

| club | season | c | c_in_sd | value_rank | value_quintile | finish | label |
|---|---|---|---|---|---|---|---|
| Tottenham Hotspur | 2025/2026 | -0.1223 | -2.3560 | 6 | 2 | 17 | FINAL |
| AFC Bournemouth | 2019/2020 | -0.1023 | -1.9702 | 10 | 3 | 18 | PAPER |
| Chelsea | 2022/2023 | -0.0978 | -1.8830 | 3 | 1 | 12 | FINAL |
| Chelsea | 2023/2024 | -0.0933 | -1.7981 | 3 | 1 | 6 | FINAL |
| Aston Villa | 2019/2020 | -0.0893 | -1.7198 | 18 | 5 | 17 | PAPER |
| Tottenham Hotspur | 2024/2025 | -0.0852 | -1.6420 | 5 | 2 | 17 | FINAL |
| Brentford | 2023/2024 | -0.0829 | -1.5978 | 13 | 4 | 16 | FINAL |
| Newcastle United | 2019/2020 | -0.0803 | -1.5464 | 15 | 4 | 13 | PAPER |
| Brighton & Hove Albion | 2024/2025 | -0.0781 | -1.5052 | 9 | 3 | 8 | FINAL |

**surplus ≥ +1 SD** (22 club-seasons):

| club | season | c | c_in_sd | value_rank | value_quintile | finish | label |
|---|---|---|---|---|---|---|---|
| Wolverhampton Wanderers | 2018/2019 | 0.1495 | 2.8799 | 17 | 5 | 7 | PAPER |
| Manchester City | 2023/2024 | 0.1258 | 2.4224 | 1 | 1 | 1 | FINAL |
| Wolverhampton Wanderers | 2019/2020 | 0.1180 | 2.2734 | 12 | 3 | 7 | PAPER |
| Arsenal | 2023/2024 | 0.1133 | 2.1816 | 2 | 1 | 2 | FINAL |
| West Ham United | 2023/2024 | 0.1000 | 1.9254 | 10 | 3 | 9 | FINAL |
| Everton | 2023/2024 | 0.0944 | 1.8175 | 12 | 3 | 15 | FINAL |
| Fulham | 2023/2024 | 0.0836 | 1.6095 | 17 | 5 | 13 | FINAL |
| Wolverhampton Wanderers | 2023/2024 | 0.0817 | 1.5729 | 11 | 3 | 14 | FINAL |
| Sheffield United | 2019/2020 | 0.0806 | 1.5530 | 20 | 5 | 9 | PAPER |
| Nottingham Forest | 2024/2025 | 0.0800 | 1.5403 | 14 | 4 | 7 | FINAL |
| Liverpool | 2024/2025 | 0.0788 | 1.5171 | 4 | 1 | 1 | FINAL |
| Brentford | 2025/2026 | 0.0757 | 1.4580 | 12 | 3 | 9 | FINAL |
| Manchester City | 2022/2023 | 0.0747 | 1.4398 | 1 | 1 | 1 | FINAL |
| Southampton | 2019/2020 | 0.0742 | 1.4297 | 11 | 3 | 11 | PAPER |
| Chelsea | 2018/2019 | 0.0711 | 1.3697 | 2 | 1 | 3 | PAPER |
| Aston Villa | 2022/2023 | 0.0693 | 1.3358 | 7 | 2 | 7 | FINAL |
| Crystal Palace | 2024/2025 | 0.0635 | 1.2224 | 11 | 3 | 12 | FINAL |
| Crystal Palace | 2018/2019 | 0.0623 | 1.2002 | 13 | 4 | 12 | PAPER |
| Tottenham Hotspur | 2021/2022 | 0.0619 | 1.1928 | 5 | 2 | 4 | PAPER |
| West Ham United | 2022/2023 | 0.0581 | 1.1200 | 10 | 3 | 14 | FINAL |
| Leeds United | 2025/2026 | 0.0525 | 1.0111 | 18 | 5 | 14 | FINAL |
| Crystal Palace | 2021/2022 | 0.0519 | 1.0002 | 16 | 4 | 12 | PAPER |

**surplus ≥ +1.5 SD** (11 club-seasons):

| club | season | c | c_in_sd | value_rank | value_quintile | finish | label |
|---|---|---|---|---|---|---|---|
| Wolverhampton Wanderers | 2018/2019 | 0.1495 | 2.8799 | 17 | 5 | 7 | PAPER |
| Manchester City | 2023/2024 | 0.1258 | 2.4224 | 1 | 1 | 1 | FINAL |
| Wolverhampton Wanderers | 2019/2020 | 0.1180 | 2.2734 | 12 | 3 | 7 | PAPER |
| Arsenal | 2023/2024 | 0.1133 | 2.1816 | 2 | 1 | 2 | FINAL |
| West Ham United | 2023/2024 | 0.1000 | 1.9254 | 10 | 3 | 9 | FINAL |
| Everton | 2023/2024 | 0.0944 | 1.8175 | 12 | 3 | 15 | FINAL |
| Fulham | 2023/2024 | 0.0836 | 1.6095 | 17 | 5 | 13 | FINAL |
| Wolverhampton Wanderers | 2023/2024 | 0.0817 | 1.5729 | 11 | 3 | 14 | FINAL |
| Sheffield United | 2019/2020 | 0.0806 | 1.5530 | 20 | 5 | 9 | PAPER |
| Nottingham Forest | 2024/2025 | 0.0800 | 1.5403 | 14 | 4 | 7 | FINAL |
| Liverpool | 2024/2025 | 0.0788 | 1.5171 | 4 | 1 | 1 | FINAL |

Distribution by value quintile and tests:

| set | n | Q1 | Q2 | Q3 | Q4 | Q5 | expected_per_q | chi2 | p_chi2_mc | p_exact_multinomial | p_Q1_le_obs | mean_value_rank | p_mean_rank_two_sided |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| deficit ≤ −1 SD | 23 | 2 | 8 | 3 | 3 | 7 | 4.6000 | 6.3478 | 0.1858 | 0.1987 | 0.1332 | 11.4783 | 0.4257 |
| deficit ≤ −1.5 SD | 9 | 2 | 2 | 2 | 2 | 1 | 1.8000 | 0.4444 | 1.0000 | 1.0000 | 0.7382 | 9.1111 | 0.4972 |
| surplus ≥ +1 SD | 22 | 5 | 2 | 8 | 3 | 4 | 4.4000 | 4.8182 | 0.3486 | 0.3824 | 0.7326 | 10.2727 | 0.8669 |
| surplus ≥ +1.5 SD | 11 | 3 | 0 | 4 | 1 | 3 | 2.2000 | 4.9091 | 0.3756 | 0.2828 | 0.8389 | 10.9091 | 0.8321 |

**Deep-deficit seasons (≤ −1 SD): 2 of 23 in the richest quintile (expected 4.6); P(Q1 ≤ 2) = 0.133; spread across quintiles p = 0.186 (MC) / 0.199 (exact). At ≤ −1.5 SD: 2 of 9 in Q1, p = 1.000 / 1.000.**


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

**Availability-associated points, association not causation.** c × 92.78 (points per unit of c from this run: points ~ log squad value + c + season FE over all 7 seasons of the variant, HC3, as the battery's points decomposition; the `_lo`/`_hi` columns use its 95% interval 53.1–132.5). c is centred on the season mean, so these are points relative to a league-average availability season.

| club | season | c | points_assoc | points_assoc_lo | points_assoc_hi | actual_points | finish |
|---|---|---|---|---|---|---|---|
| Tottenham Hotspur | 2024/25 | -0.0852 | -7.9 | -4.5 | -11.3 | 38 | 17 |
| Tottenham Hotspur | 2025/26 | -0.1223 | -11.3 | -6.5 | -16.2 | 41 | 17 |
| Chelsea | 2022/23 | -0.0978 | -9.1 | -5.2 | -12.9 | 44 | 12 |
| Chelsea | 2023/24 | -0.0933 | -8.7 | -5.0 | -12.4 | 63 | 6 |


## 5. Verdict

**(1) Does the sum rule change the asymmetry step's conclusion?** No. Ranked by the two-season sum, Tottenham 2024/25–2025/26 is 1 of 85 and Chelsea 2022/23–2023/24 is 2. Under carry-over alone, a pair at least as deep by sum appears in 42% of simulated leagues for Tottenham's depth and 60% for Chelsea's (milder-season rule: 49% and 33%; most-negative-season rule: 61% and 96%). The surplus mirrors are 43% and 61%, so the null is symmetric as built. Expectation (0.3–0.7 under the sum rule): MET.

**(2) Are rich clubs hit by deep deficits as often as others?** The data do not show that they are spared. Of 23 club-seasons at or below −1 SD, 2 belong to the four highest-value squads of their season (expected 4.6 under a uniform draw; quintiles Q1–Q5 2/8/3/3/7; chi-square MC p = 0.186, exact p = 0.199; P(Q1 ≤ observed) = 0.133). At −1.5 SD: 2 of 9 (p = 1.000). Surplus seasons ≥ +1 SD: 5 of 22 in Q1 (p = 0.382).

**(3) Points at stake.** At 92.78 points per unit (association, not causation; the run's all-seasons coefficient), the named deficits are associated with -7.9 and -11.3 points for Tottenham (2024/25, 2025/26) and -9.1 and -8.7 for Chelsea (2022/23, 2023/24); on the interval 53.1–132.5 the Tottenham 2025/26 figure runs -16.2 to -6.5. Tottenham finished 17 and 17, +13 and +2 points from 18th place, -31 and -24 from 4th. Chelsea finished 12 and 6, -27 and -5 from 4th.

The values of c used, as in `op4_named_points.csv`: Tottenham Hotspur 2024/25 c = -0.0852; Tottenham Hotspur 2025/26 c = -0.1223; Chelsea 2022/23 c = -0.0978; Chelsea 2023/24 c = -0.0933.

Tottenham 2025/26 finished 2 points above 18th place; the availability-associated figure for that season (-11.3, interval -16.2 to -6.5) is larger than that margin. That is an association, not a claim that better availability would have kept them further clear.

**Sentences a paper could use (conservative first):**

1. "Two-season runs of low availability as deep as Tottenham Hotspur's in 2024/25–2025/26 are common under one-season carry-over alone, whether depth is judged by the milder season (49% of simulated 7-season leagues) or by the two-season total (42%); we therefore do not treat such runs as evidence of a persistent club effect."
2. "Low-availability seasons (at least one SD below the season mean) fall across the squad-value distribution as a uniform draw would give (2 of 23 in the top value quintile against 4.6 expected; exact multinomial p = 0.20); the richest clubs are not measurably spared."
3. "On the all-seasons association of 92.8 points per unit of availability (95% interval 53.1–132.5), Tottenham's 2025/26 availability deficit corresponds to about 11 points (range 6–16) below a league-average availability season; this is an association, not an estimate of causal effect."

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


