# Is club availability persistent?

## 1. Provenance and checks

Run 2026-10-02 05:33.

Inputs (read-only):

- `club_seasons.csv` — 160 rows
- `club_season_values.csv` — 160 rows

Join on season + team_id. Season-centred NETavailability `c` = club value − that season's 20-club mean. Rank 1 = highest NETavailability within season (method=min).

**(a)** rows 160 (configured: 8 seasons × 20 = 160); seasons 8 (2018/2019–2025/2026); per-season counts [np.int64(20)]; duplicate season+team_id 0; join to squad-value file 160/160; log_value_rel missing 0 → **PASS**

Note: squad values are dated 2018-07-01, 2019-07-01, 2020-07-01, 2021-07-01, 2022-07-01, 2023-07-01, 2024-07-01, 2025-07-01 (the Transfermarkt reference dates used).

**(b)** Tottenham Hotspur ranks 2018/2019→2025/2026: [15, 16, 11, 1, 9, 10, 20, 20]; club tables' rank column [15, 16, 11, 1, 9, 10, 20, 20] → **PASS** (recomputed ranks agree with file column NETavailability_rank for all 160: True)

**(c)** adjacent-season Spearman of NETavailability ranks (clubs in both seasons):

| pair | n | spearman |
|---|---|---|
| 2018/2019→2019/2020 | 17 | 0.4363 |
| 2019/2020→2020/2021 | 17 | 0.0025 |
| 2020/2021→2021/2022 | 17 | -0.0049 |
| 2021/2022→2022/2023 | 17 | 0.6961 |
| 2022/2023→2023/2024 | 17 | 0.5564 |
| 2023/2024→2024/2025 | 17 | 0.0319 |
| 2024/2025→2025/2026 | 17 | 0.4216 |

Mean over 7 pairs = **0.3057** (recomputed as the Pearson correlation of ranks: 0.3057, tolerance 1e-09) → **PASS**

**(d)** seasons present per club (30 clubs):

| club | seasons |
|---|---|
| Arsenal | 8 |
| Brighton & Hove Albion | 8 |
| Crystal Palace | 8 |
| Everton | 8 |
| Chelsea | 8 |
| Liverpool | 8 |
| Manchester United | 8 |
| Tottenham Hotspur | 8 |
| West Ham United | 8 |
| Wolverhampton Wanderers | 8 |
| Manchester City | 8 |
| Newcastle United | 8 |
| Aston Villa | 7 |
| AFC Bournemouth | 6 |
| Southampton | 6 |
| Fulham | 6 |
| Burnley | 6 |
| Leicester City | 6 |
| Brentford | 5 |
| Nottingham Forest | 4 |
| Leeds United | 4 |
| Watford | 3 |
| Sheffield United | 3 |
| Norwich City | 2 |
| Cardiff City | 1 |
| Huddersfield Town | 1 |
| Ipswich Town | 1 |
| Luton Town | 1 |
| Sunderland | 1 |
| West Bromwich Albion | 1 |

Clubs with ≥6 seasons: 18; ≥8: 12; all 8: 12.

Self-checks against the run's own inputs: ALL PASS


## 2. Signal versus noise (season-centred NETavailability)

Data: 8 seasons: INDICATIVE 0 (none), FINAL 4 (2022/2023–2025/2026); 160 club-seasons, 30 clubs.

### 2(a) Intraclass correlation (one-way random effects, ANOVA estimator for unbalanced groups, σ²_b truncated at 0; 95% interval = percentile bootstrap over clubs, 2,000 draws, seed 20260930)

**ICC, season-centred NETavailability**

| sample | clubs | obs | n0 | MSB | MSW | var_between | var_within | ICC | ci_lo | ci_hi |
|---|---|---|---|---|---|---|---|---|---|---|
| all clubs | 30 | 160 | 5.28405 | 0.00368082 | 0.00229618 | 0.000262041 | 0.00229618 | 0.102431 | 0 | 0.233825 |
| clubs ≥6 seasons | 18 | 133 | 7.38257 | 0.00533432 | 0.00219808 | 0.000424817 | 0.00219808 | 0.161965 | 0.0125659 | 0.282779 |

### 2(b) Split-half

**Split-half club means** (clubs with ≥3 seasons in each half)

| split | half_a | half_b | n | pearson | p_pearson | spearman | p_spearman |
|---|---|---|---|---|---|---|---|
| odd v even | odd seasons (2014/15, 2016/17, …) | even seasons (2015/16, 2017/18, …) | 14 | 0.6979 | 0.0055 | 0.7011 | 0.0052 |
| first v second half | 2018/2019–2021/2022 | 2022/2023–2025/2026 | 13 | 0.1983 | 0.5161 | 0.1484 | 0.6286 |

- odd v even clubs (n=14): AFC Bournemouth, Arsenal, Aston Villa, Brighton & Hove Albion, Chelsea, Crystal Palace, Everton, Liverpool, Manchester City, Manchester United, Newcastle United, Tottenham Hotspur, West Ham United, Wolverhampton Wanderers

- first v second half clubs (n=13): Arsenal, Aston Villa, Brighton & Hove Albion, Chelsea, Crystal Palace, Everton, Liverpool, Manchester City, Manchester United, Newcastle United, Tottenham Hotspur, West Ham United, Wolverhampton Wanderers

### 2(c) Permutation test

**Permutation** (shuffle club labels within season, 10,000 draws, seed 20260930; statistic = season-count-weighted variance of club means, clubs ≥6 seasons)

| clubs_ge6 | observed | perm_mean | perm_p95 | ratio_obs_to_mean | p |
|---|---|---|---|---|---|
| 18 | 0.00068183 | 0.000336969 | 0.000528156 | 2.02342 | 0.0039996 |

### 2(d) One-season regression to the mean

OLS of c(t) on c(t−1), clubs present in consecutive seasons: n = 119 pairs.

- slope = **0.3407** (OLS SE 0.0840, p = 8.99e-05; club-clustered SE 0.0711, p = 1.68e-06); intercept 0.00183; R² 0.1234
- Pearson r(c(t), c(t−1)) = 0.3512
- SD of season-centred NETavailability = 0.0505 (5.05 pp).
- In words: a club one SD (5.05 pp) above the season average is expected to be 1.72 pp (0.34 SD) above average the next season — about 66% of the gap regresses away in one season.


## 3. The clubs (≥6 seasons)

Data: 8 seasons: INDICATIVE 0 (none), FINAL 4 (2022/2023–2025/2026). EB shrinkage uses variance components from 2(a), all clubs.

**Club means of season-centred NETavailability** (sorted by EB shrunken estimate; B = σ²_b/(σ²_b+σ²_w/n), σ²_b=0.000262, σ²_w=0.0023; 95% interval = mean ± t(n−1)·SE)

| club | seasons | mean | se | ci_lo | ci_hi | shrink_B | shrunk | mean_rank | sd_rank | best_rank | worst_rank | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Wolverhampton Wanderers | 8 | 0.0578 | 0.0191 | 0.0126 | 0.1030 | 0.4773 | 0.0276 | 5.5000 | 3.8173 | 1 | 12 | ABOVE |
| Manchester City | 8 | 0.0359 | 0.0177 | -0.0060 | 0.0779 | 0.4773 | 0.0171 | 6.3750 | 5.3168 | 1 | 14 |  |
| Fulham | 6 | 0.0406 | 0.0103 | 0.0141 | 0.0670 | 0.4064 | 0.0165 | 5.5000 | 2.0736 | 2 | 8 | ABOVE |
| Crystal Palace | 8 | 0.0276 | 0.0125 | -0.0019 | 0.0571 | 0.4773 | 0.0132 | 6.8750 | 5.2491 | 2 | 17 |  |
| West Ham United | 8 | 0.0275 | 0.0179 | -0.0149 | 0.0699 | 0.4773 | 0.0131 | 7.6250 | 5.9507 | 3 | 20 |  |
| Everton | 8 | 0.0066 | 0.0160 | -0.0312 | 0.0444 | 0.4773 | 0.0031 | 10.3750 | 5.0973 | 4 | 20 |  |
| Aston Villa | 7 | 0.0042 | 0.0212 | -0.0478 | 0.0561 | 0.4441 | 0.0019 | 9.4286 | 6.5027 | 2 | 19 |  |
| Arsenal | 8 | 0.0037 | 0.0197 | -0.0428 | 0.0502 | 0.4773 | 0.0018 | 11.1250 | 5.7430 | 2 | 17 |  |
| Southampton | 6 | 0.0012 | 0.0201 | -0.0505 | 0.0528 | 0.4064 | 0.0005 | 10.0000 | 5.3292 | 3 | 18 |  |
| Liverpool | 8 | 0.0002 | 0.0190 | -0.0446 | 0.0450 | 0.4773 | 0.0001 | 10.0000 | 6.4807 | 2 | 20 |  |
| Burnley | 6 | -0.0056 | 0.0147 | -0.0434 | 0.0321 | 0.4064 | -0.0023 | 10.5000 | 5.2058 | 4 | 19 |  |
| Brighton & Hove Albion | 8 | -0.0096 | 0.0140 | -0.0428 | 0.0235 | 0.4773 | -0.0046 | 11.1250 | 4.4541 | 5 | 19 |  |
| AFC Bournemouth | 6 | -0.0119 | 0.0200 | -0.0633 | 0.0394 | 0.4064 | -0.0049 | 10.8333 | 5.4191 | 5 | 20 |  |
| **Chelsea** | 8 | -0.0185 | 0.0204 | -0.0666 | 0.0297 | 0.4773 | -0.0088 | 12.2500 | 6.7559 | 2 | 20 |  |
| Leicester City | 6 | -0.0252 | 0.0140 | -0.0613 | 0.0109 | 0.4064 | -0.0102 | 14.5000 | 5.2058 | 5 | 19 |  |
| **Tottenham Hotspur** | 8 | -0.0248 | 0.0203 | -0.0727 | 0.0231 | 0.4773 | -0.0118 | 12.7500 | 6.3640 | 1 | 20 |  |
| Manchester United | 8 | -0.0281 | 0.0122 | -0.0571 | 0.0009 | 0.4773 | -0.0134 | 14.3750 | 4.7790 | 3 | 18 |  |
| Newcastle United | 8 | -0.0392 | 0.0118 | -0.0671 | -0.0114 | 0.4773 | -0.0187 | 14.6250 | 3.5431 | 10 | 19 | BELOW |

Flags (95% interval excludes zero): 3 of 18 clubs (2 above, 1 below). Expected by chance at 5% two-sided: 0.90 (binomial P(≥3) = 0.05813).

Tottenham Hotspur excluding 2024/25–2025/26: n = 6, mean 0.0016, SE 0.0137, 95% interval [-0.0337, 0.0368], mean rank 10.33 (all 8 seasons: mean -0.0248, mean rank 12.75; 2024/25 and 2025/26 values [-0.0852, -0.1223]).

- Tottenham Hotspur: position 16 of 18 by shrunken estimate; raw mean -0.0248, shrunk -0.0118, interval [-0.0727, 0.0231] not flagged.
- Chelsea: position 14 of 18 by shrunken estimate; raw mean -0.0185, shrunk -0.0088, interval [-0.0666, 0.0297] not flagged.


## 4. Is persistence just money?

Data: 8 seasons: INDICATIVE 0 (none), FINAL 4 (2022/2023–2025/2026).

OLS c ~ log_value_rel + season FE (n = 160): coefficient 0.00281 (SE 0.00535, p = 0.601; club-clustered SE 0.00606, p = 0.643); R² 0.0018. Residual SD 0.0504 vs c SD 0.0505.

### 4(a) ICC on residual

**ICC, value-adjusted residual**

| sample | clubs | obs | n0 | MSB | MSW | var_between | var_within | ICC | ci_lo | ci_hi |
|---|---|---|---|---|---|---|---|---|---|---|
| all clubs | 30 | 160 | 5.28405 | 0.00368221 | 0.00229019 | 0.000263438 | 0.00229019 | 0.103162 | 0 | 0.233971 |
| clubs ≥6 seasons | 18 | 133 | 7.38257 | 0.00549523 | 0.00218929 | 0.000447804 | 0.00218929 | 0.16981 | 0.0178174 | 0.292545 |

### 4(b) Split-half on residual

**Split-half, value-adjusted residual** (clubs with ≥3 seasons in each half)

| split | half_a | half_b | n | pearson | p_pearson | spearman | p_spearman |
|---|---|---|---|---|---|---|---|
| odd v even | odd seasons (2014/15, 2016/17, …) | even seasons (2015/16, 2017/18, …) | 14 | 0.7042 | 0.0049 | 0.6747 | 0.0081 |
| first v second half | 2018/2019–2021/2022 | 2022/2023–2025/2026 | 13 | 0.2191 | 0.4721 | 0.2637 | 0.3839 |

- odd v even clubs (n=14): AFC Bournemouth, Arsenal, Aston Villa, Brighton & Hove Albion, Chelsea, Crystal Palace, Everton, Liverpool, Manchester City, Manchester United, Newcastle United, Tottenham Hotspur, West Ham United, Wolverhampton Wanderers

- first v second half clubs (n=13): Arsenal, Aston Villa, Brighton & Hove Albion, Chelsea, Crystal Palace, Everton, Liverpool, Manchester City, Manchester United, Newcastle United, Tottenham Hotspur, West Ham United, Wolverhampton Wanderers

### 4(c) Clubs on residual

**Club means of value-adjusted residual** (sorted by EB shrunken estimate; B = σ²_b/(σ²_b+σ²_w/n), σ²_b=0.000263, σ²_w=0.00229; 95% interval = mean ± t(n−1)·SE)

| club | seasons | mean | se | ci_lo | ci_hi | shrink_B | shrunk | mean_rank | sd_rank | best_rank | worst_rank | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Wolverhampton Wanderers | 8 | 0.0582 | 0.0193 | 0.0127 | 0.1038 | 0.4792 | 0.0279 | 5.5000 | 3.8173 | 1 | 12 | ABOVE |
| Fulham | 6 | 0.0427 | 0.0101 | 0.0168 | 0.0685 | 0.4083 | 0.0174 | 5.5000 | 2.0736 | 2 | 8 | ABOVE |
| Manchester City | 8 | 0.0326 | 0.0177 | -0.0093 | 0.0746 | 0.4792 | 0.0156 | 6.3750 | 5.3168 | 1 | 14 |  |
| Crystal Palace | 8 | 0.0286 | 0.0124 | -0.0008 | 0.0580 | 0.4792 | 0.0137 | 6.8750 | 5.2491 | 2 | 17 |  |
| West Ham United | 8 | 0.0277 | 0.0179 | -0.0146 | 0.0699 | 0.4792 | 0.0133 | 7.6250 | 5.9507 | 3 | 20 |  |
| Everton | 8 | 0.0064 | 0.0161 | -0.0316 | 0.0444 | 0.4792 | 0.0031 | 10.3750 | 5.0973 | 4 | 20 |  |
| Aston Villa | 7 | 0.0042 | 0.0208 | -0.0468 | 0.0552 | 0.4460 | 0.0019 | 9.4286 | 6.5027 | 2 | 19 |  |
| Southampton | 6 | 0.0020 | 0.0198 | -0.0489 | 0.0530 | 0.4083 | 0.0008 | 10.0000 | 5.3292 | 3 | 18 |  |
| Arsenal | 8 | 0.0017 | 0.0196 | -0.0446 | 0.0480 | 0.4792 | 0.0008 | 11.1250 | 5.7430 | 2 | 17 |  |
| Liverpool | 8 | -0.0025 | 0.0190 | -0.0475 | 0.0425 | 0.4792 | -0.0012 | 10.0000 | 6.4807 | 2 | 20 |  |
| Burnley | 6 | -0.0036 | 0.0146 | -0.0411 | 0.0340 | 0.4083 | -0.0015 | 10.5000 | 5.2058 | 4 | 19 |  |
| AFC Bournemouth | 6 | -0.0107 | 0.0200 | -0.0622 | 0.0407 | 0.4083 | -0.0044 | 10.8333 | 5.4191 | 5 | 20 |  |
| Brighton & Hove Albion | 8 | -0.0093 | 0.0142 | -0.0428 | 0.0243 | 0.4792 | -0.0044 | 11.1250 | 4.4541 | 5 | 19 |  |
| **Chelsea** | 8 | -0.0211 | 0.0203 | -0.0690 | 0.0268 | 0.4792 | -0.0101 | 12.2500 | 6.7559 | 2 | 20 |  |
| Leicester City | 6 | -0.0256 | 0.0142 | -0.0621 | 0.0110 | 0.4083 | -0.0104 | 14.5000 | 5.2058 | 5 | 19 |  |
| **Tottenham Hotspur** | 8 | -0.0268 | 0.0202 | -0.0746 | 0.0209 | 0.4792 | -0.0129 | 12.7500 | 6.3640 | 1 | 20 |  |
| Manchester United | 8 | -0.0302 | 0.0122 | -0.0591 | -0.0013 | 0.4792 | -0.0145 | 14.3750 | 4.7790 | 3 | 18 | BELOW |
| Newcastle United | 8 | -0.0391 | 0.0117 | -0.0666 | -0.0115 | 0.4792 | -0.0187 | 14.6250 | 3.5431 | 10 | 19 | BELOW |

Flags (95% interval excludes zero): 4 of 18 clubs (2 above, 2 below). Expected by chance at 5% two-sided: 0.90 (binomial P(≥4) = 0.01087).

### 4(d) Club-level money correlation

Across 18 clubs with ≥6 seasons, mean log_value_rel vs mean season-centred NETavailability: Pearson r = -0.2108 (p = 0.401), Spearman ρ = -0.2363 (p = 0.345).


## 5. Sensitivity

Season-centring is within season, so subsetting seasons does not change any club's centred value. Split-half: parity split keeps the original odd/even assignment; the chronological split halves the retained seasons (first half gets the extra season when the count is odd).

### 5i. (i) excluding Covid-flagged 2019/20, 2020/21, 2021/22 — 5 seasons: INDICATIVE 0 (none), FINAL 4 (2022/2023–2025/2026)

100 club-seasons, 28 clubs.

**ICC — 5 seasons: INDICATIVE 0 (none), FINAL 4 (2022/2023–2025/2026)**

| sample | clubs | obs | n0 | MSB | MSW | var_between | var_within | ICC | ci_lo | ci_hi |
|---|---|---|---|---|---|---|---|---|---|---|
| all clubs | 28 | 100 | 3.54222 | 0.00415676 | 0.00235093 | 0.000509802 | 0.00235093 | 0.178207 | 0 | 0.332385 |
| clubs ≥6 seasons | 0 | 0 |  | -0 |  |  |  |  |  |  |

**Split-half — 5 seasons: INDICATIVE 0 (none), FINAL 4 (2022/2023–2025/2026)** (clubs with ≥3 seasons in each half)

| split | half_a | half_b | n | pearson | p_pearson | spearman | p_spearman |
|---|---|---|---|---|---|---|---|
| odd v even | odd seasons (2014/15, 2016/17, …) | even seasons (2015/16, 2017/18, …) | 0 |  |  |  |  |
| first v second half | 2018/2019–2023/2024 | 2024/2025–2025/2026 | 0 |  |  |  |  |

- odd v even clubs (n=0): 

- first v second half clubs (n=0): 

**Permutation — 5 seasons: INDICATIVE 0 (none), FINAL 4 (2022/2023–2025/2026)** (shuffle club labels within season, 10,000 draws, seed 20260930; statistic = season-count-weighted variance of club means, clubs ≥6 seasons)

| clubs_ge6 | observed | perm_mean | perm_p95 | ratio_obs_to_mean | p |
|---|---|---|---|---|---|
| 0 |  |  |  |  | 9.999e-05 |

### 5ii. (ii) 2018/19–2025/26 only — 8 seasons: INDICATIVE 0 (none), FINAL 4 (2022/2023–2025/2026)

160 club-seasons, 30 clubs.

**ICC — 8 seasons: INDICATIVE 0 (none), FINAL 4 (2022/2023–2025/2026)**

| sample | clubs | obs | n0 | MSB | MSW | var_between | var_within | ICC | ci_lo | ci_hi |
|---|---|---|---|---|---|---|---|---|---|---|
| all clubs | 30 | 160 | 5.28405 | 0.00368082 | 0.00229618 | 0.000262041 | 0.00229618 | 0.102431 | 0 | 0.233825 |
| clubs ≥6 seasons | 18 | 133 | 7.38257 | 0.00533432 | 0.00219808 | 0.000424817 | 0.00219808 | 0.161965 | 0.0125659 | 0.282779 |

**Split-half — 8 seasons: INDICATIVE 0 (none), FINAL 4 (2022/2023–2025/2026)** (clubs with ≥3 seasons in each half)

| split | half_a | half_b | n | pearson | p_pearson | spearman | p_spearman |
|---|---|---|---|---|---|---|---|
| odd v even | odd seasons (2014/15, 2016/17, …) | even seasons (2015/16, 2017/18, …) | 14 | 0.6979 | 0.0055 | 0.7011 | 0.0052 |
| first v second half | 2018/2019–2021/2022 | 2022/2023–2025/2026 | 13 | 0.1983 | 0.5161 | 0.1484 | 0.6286 |

- odd v even clubs (n=14): AFC Bournemouth, Arsenal, Aston Villa, Brighton & Hove Albion, Chelsea, Crystal Palace, Everton, Liverpool, Manchester City, Manchester United, Newcastle United, Tottenham Hotspur, West Ham United, Wolverhampton Wanderers

- first v second half clubs (n=13): Arsenal, Aston Villa, Brighton & Hove Albion, Chelsea, Crystal Palace, Everton, Liverpool, Manchester City, Manchester United, Newcastle United, Tottenham Hotspur, West Ham United, Wolverhampton Wanderers

**Permutation — 8 seasons: INDICATIVE 0 (none), FINAL 4 (2022/2023–2025/2026)** (shuffle club labels within season, 10,000 draws, seed 20260930; statistic = season-count-weighted variance of club means, clubs ≥6 seasons)

| clubs_ge6 | observed | perm_mean | perm_p95 | ratio_obs_to_mean | p |
|---|---|---|---|---|---|
| 18 | 0.00068183 | 0.000336969 | 0.000528156 | 2.02342 | 0.0039996 |

### 5(iii). FINAL seasons only (2022/23–2025/26) — not run

Four seasons are too few: no club can reach the ≥6-season threshold used by the permutation statistic and the club table, and a split-half needs ≥3 seasons in each half (≥6 in total). An ICC on 4 seasons would rest on ≤4 observations per club; it is not reported.


