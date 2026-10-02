# Is club availability persistent?

## 1. Provenance and checks

Run 2026-10-02 05:33.

Inputs (read-only):

- `club_seasons.csv` — 140 rows
- `club_season_values.csv` — 140 rows

Join on season + team_id. Season-centred NETavailability `c` = club value − that season's 20-club mean. Rank 1 = highest NETavailability within season (method=min).

**(a)** rows 140 (configured: 7 seasons × 20 = 140); seasons 7 (2018/2019–2025/2026); per-season counts [np.int64(20)]; duplicate season+team_id 0; join to squad-value file 140/140; log_value_rel missing 0 → **PASS**

Note: squad values are dated 2018-07-01, 2019-07-01, 2021-07-01, 2022-07-01, 2023-07-01, 2024-07-01, 2025-07-01 (the Transfermarkt reference dates used).

**(b)** Tottenham Hotspur ranks 2018/2019→2025/2026: [15, 16, 1, 9, 10, 20, 20]; club tables' rank column [15, 16, 1, 9, 10, 20, 20] → **PASS** (recomputed ranks agree with file column NETavailability_rank for all 140: True)

**(c)** adjacent-season Spearman of NETavailability ranks (clubs in both seasons):

| pair | n | spearman |
|---|---|---|
| 2018/2019→2019/2020 | 17 | 0.4363 |
| 2019/2020→2021/2022 | 18 | -0.0774 |
| 2021/2022→2022/2023 | 17 | 0.6961 |
| 2022/2023→2023/2024 | 17 | 0.5564 |
| 2023/2024→2024/2025 | 17 | 0.0319 |
| 2024/2025→2025/2026 | 17 | 0.4216 |

Mean over 6 pairs = **0.3441** (recomputed as the Pearson correlation of ranks: 0.3441, tolerance 1e-09) → **PASS**

**(d)** seasons present per club (29 clubs):

| club | seasons |
|---|---|
| Arsenal | 7 |
| Brighton & Hove Albion | 7 |
| Everton | 7 |
| Chelsea | 7 |
| Crystal Palace | 7 |
| Manchester City | 7 |
| West Ham United | 7 |
| Tottenham Hotspur | 7 |
| Wolverhampton Wanderers | 7 |
| Newcastle United | 7 |
| Manchester United | 7 |
| Liverpool | 7 |
| AFC Bournemouth | 6 |
| Aston Villa | 6 |
| Brentford | 5 |
| Southampton | 5 |
| Fulham | 5 |
| Burnley | 5 |
| Leicester City | 5 |
| Nottingham Forest | 4 |
| Leeds United | 3 |
| Watford | 3 |
| Sheffield United | 2 |
| Norwich City | 2 |
| Cardiff City | 1 |
| Ipswich Town | 1 |
| Huddersfield Town | 1 |
| Luton Town | 1 |
| Sunderland | 1 |

Clubs with ≥6 seasons: 14; ≥8: 0; all 7: 12.

Self-checks against the run's own inputs: ALL PASS


## 2. Signal versus noise (season-centred NETavailability)

Data: 7 seasons: INDICATIVE 0 (none), FINAL 4 (2022/2023–2025/2026); 140 club-seasons, 29 clubs.

### 2(a) Intraclass correlation (one-way random effects, ANOVA estimator for unbalanced groups, σ²_b truncated at 0; 95% interval = percentile bootstrap over clubs, 2,000 draws, seed 20260930)

**ICC, season-centred NETavailability**

| sample | clubs | obs | n0 | MSB | MSW | var_between | var_within | ICC | ci_lo | ci_hi |
|---|---|---|---|---|---|---|---|---|---|---|
| all clubs | 29 | 140 | 4.78776 | 0.00394414 | 0.00237993 | 0.000326709 | 0.00237993 | 0.120707 | 0 | 0.270903 |
| clubs ≥6 seasons | 14 | 96 | 6.85577 | 0.0064492 | 0.00237832 | 0.000593789 | 0.00237832 | 0.199787 | 0.00134836 | 0.365784 |

### 2(b) Split-half

**Split-half club means** (clubs with ≥3 seasons in each half)

| split | half_a | half_b | n | pearson | p_pearson | spearman | p_spearman |
|---|---|---|---|---|---|---|---|
| odd v even | odd seasons (2014/15, 2016/17, …) | even seasons (2015/16, 2017/18, …) | 13 | 0.7418 | 0.0037 | 0.7582 | 0.0027 |
| first v second half | 2018/2019–2022/2023 | 2023/2024–2025/2026 | 14 | 0.3437 | 0.2289 | 0.2967 | 0.3030 |

- odd v even clubs (n=13): AFC Bournemouth, Arsenal, Brighton & Hove Albion, Chelsea, Crystal Palace, Everton, Liverpool, Manchester City, Manchester United, Newcastle United, Tottenham Hotspur, West Ham United, Wolverhampton Wanderers

- first v second half clubs (n=14): AFC Bournemouth, Arsenal, Aston Villa, Brighton & Hove Albion, Chelsea, Crystal Palace, Everton, Liverpool, Manchester City, Manchester United, Newcastle United, Tottenham Hotspur, West Ham United, Wolverhampton Wanderers

### 2(c) Permutation test

**Permutation** (shuffle club labels within season, 10,000 draws, seed 20260930; statistic = season-count-weighted variance of club means, clubs ≥6 seasons)

| clubs_ge6 | observed | perm_mean | perm_p95 | ratio_obs_to_mean | p |
|---|---|---|---|---|---|
| 14 | 0.00087333 | 0.000381478 | 0.000638338 | 2.28933 | 0.00219978 |

### 2(d) One-season regression to the mean

OLS of c(t) on c(t−1), clubs present in consecutive seasons: n = 85 pairs.

- slope = **0.4152** (OLS SE 0.0988, p = 6.58e-05; club-clustered SE 0.0816, p = 3.61e-07); intercept 0.00260; R² 0.1755
- Pearson r(c(t), c(t−1)) = 0.4190
- SD of season-centred NETavailability = 0.0519 (5.19 pp).
- In words: a club one SD (5.19 pp) above the season average is expected to be 2.16 pp (0.42 SD) above average the next season — about 58% of the gap regresses away in one season.


## 3. The clubs (≥6 seasons)

Data: 7 seasons: INDICATIVE 0 (none), FINAL 4 (2022/2023–2025/2026). EB shrinkage uses variance components from 2(a), all clubs.

**Club means of season-centred NETavailability** (sorted by EB shrunken estimate; B = σ²_b/(σ²_b+σ²_w/n), σ²_b=0.000327, σ²_w=0.00238; 95% interval = mean ± t(n−1)·SE)

| club | seasons | mean | se | ci_lo | ci_hi | shrink_B | shrunk | mean_rank | sd_rank | best_rank | worst_rank | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Wolverhampton Wanderers | 7 | 0.0663 | 0.0197 | 0.0180 | 0.1146 | 0.4900 | 0.0325 | 4.5714 | 2.9921 | 1 | 9 | ABOVE |
| Crystal Palace | 7 | 0.0360 | 0.0106 | 0.0101 | 0.0620 | 0.4900 | 0.0177 | 5.4286 | 3.5523 | 2 | 12 | ABOVE |
| Manchester City | 7 | 0.0324 | 0.0201 | -0.0167 | 0.0814 | 0.4900 | 0.0159 | 7.1429 | 5.2418 | 1 | 14 |  |
| West Ham United | 7 | 0.0272 | 0.0207 | -0.0235 | 0.0778 | 0.4900 | 0.0133 | 8.0000 | 6.3246 | 3 | 20 |  |
| Liverpool | 7 | 0.0127 | 0.0165 | -0.0276 | 0.0530 | 0.4900 | 0.0062 | 8.5714 | 5.4729 | 2 | 18 |  |
| Aston Villa | 6 | 0.0071 | 0.0249 | -0.0568 | 0.0711 | 0.4517 | 0.0032 | 8.6667 | 6.7725 | 2 | 19 |  |
| Arsenal | 7 | 0.0064 | 0.0225 | -0.0486 | 0.0614 | 0.4900 | 0.0032 | 10.5714 | 5.9682 | 2 | 17 |  |
| Everton | 7 | 0.0059 | 0.0185 | -0.0393 | 0.0510 | 0.4900 | 0.0029 | 10.5714 | 5.4729 | 4 | 20 |  |
| Brighton & Hove Albion | 7 | -0.0094 | 0.0162 | -0.0490 | 0.0302 | 0.4900 | -0.0046 | 10.8571 | 4.7409 | 5 | 19 |  |
| AFC Bournemouth | 6 | -0.0119 | 0.0200 | -0.0633 | 0.0394 | 0.4517 | -0.0054 | 10.8333 | 5.4191 | 5 | 20 |  |
| **Chelsea** | 7 | -0.0258 | 0.0220 | -0.0795 | 0.0280 | 0.4900 | -0.0126 | 13.4286 | 6.3471 | 2 | 20 |  |
| **Tottenham Hotspur** | 7 | -0.0286 | 0.0230 | -0.0848 | 0.0276 | 0.4900 | -0.0140 | 13.0000 | 6.8313 | 1 | 20 |  |
| Newcastle United | 7 | -0.0341 | 0.0123 | -0.0642 | -0.0041 | 0.4900 | -0.0167 | 14.0000 | 3.3166 | 10 | 18 | BELOW |
| Manchester United | 7 | -0.0389 | 0.0067 | -0.0552 | -0.0226 | 0.4900 | -0.0191 | 16.0000 | 1.4142 | 14 | 18 | BELOW |

Flags (95% interval excludes zero): 4 of 14 clubs (2 above, 2 below). Expected by chance at 5% two-sided: 0.70 (binomial P(≥4) = 0.004173).

Tottenham Hotspur excluding 2024/25–2025/26: n = 5, mean 0.0015, SE 0.0168, 95% interval [-0.0451, 0.0482], mean rank 10.20 (all 7 seasons: mean -0.0286, mean rank 13.00; 2024/25 and 2025/26 values [-0.0852, -0.1223]).

- Tottenham Hotspur: position 12 of 14 by shrunken estimate; raw mean -0.0286, shrunk -0.0140, interval [-0.0848, 0.0276] not flagged.
- Chelsea: position 11 of 14 by shrunken estimate; raw mean -0.0258, shrunk -0.0126, interval [-0.0795, 0.0280] not flagged.


## 4. Is persistence just money?

Data: 7 seasons: INDICATIVE 0 (none), FINAL 4 (2022/2023–2025/2026).

OLS c ~ log_value_rel + season FE (n = 140): coefficient 0.00345 (SE 0.00594, p = 0.563; club-clustered SE 0.00675, p = 0.61); R² 0.0025. Residual SD 0.0518 vs c SD 0.0519.

### 4(a) ICC on residual

**ICC, value-adjusted residual**

| sample | clubs | obs | n0 | MSB | MSW | var_between | var_within | ICC | ci_lo | ci_hi |
|---|---|---|---|---|---|---|---|---|---|---|
| all clubs | 29 | 140 | 4.78776 | 0.00395502 | 0.0023686 | 0.000331349 | 0.0023686 | 0.122724 | 0 | 0.27833 |
| clubs ≥6 seasons | 14 | 96 | 6.85577 | 0.00666435 | 0.00236902 | 0.000626527 | 0.00236902 | 0.209153 | 0.00210262 | 0.378037 |

### 4(b) Split-half on residual

**Split-half, value-adjusted residual** (clubs with ≥3 seasons in each half)

| split | half_a | half_b | n | pearson | p_pearson | spearman | p_spearman |
|---|---|---|---|---|---|---|---|
| odd v even | odd seasons (2014/15, 2016/17, …) | even seasons (2015/16, 2017/18, …) | 13 | 0.7479 | 0.0033 | 0.7363 | 0.0041 |
| first v second half | 2018/2019–2022/2023 | 2023/2024–2025/2026 | 14 | 0.3575 | 0.2095 | 0.3802 | 0.1799 |

- odd v even clubs (n=13): AFC Bournemouth, Arsenal, Brighton & Hove Albion, Chelsea, Crystal Palace, Everton, Liverpool, Manchester City, Manchester United, Newcastle United, Tottenham Hotspur, West Ham United, Wolverhampton Wanderers

- first v second half clubs (n=14): AFC Bournemouth, Arsenal, Aston Villa, Brighton & Hove Albion, Chelsea, Crystal Palace, Everton, Liverpool, Manchester City, Manchester United, Newcastle United, Tottenham Hotspur, West Ham United, Wolverhampton Wanderers

### 4(c) Clubs on residual

**Club means of value-adjusted residual** (sorted by EB shrunken estimate; B = σ²_b/(σ²_b+σ²_w/n), σ²_b=0.000331, σ²_w=0.00237; 95% interval = mean ± t(n−1)·SE)

| club | seasons | mean | se | ci_lo | ci_hi | shrink_B | shrunk | mean_rank | sd_rank | best_rank | worst_rank | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Wolverhampton Wanderers | 7 | 0.0669 | 0.0199 | 0.0182 | 0.1157 | 0.4948 | 0.0331 | 4.5714 | 2.9921 | 1 | 9 | ABOVE |
| Crystal Palace | 7 | 0.0371 | 0.0106 | 0.0111 | 0.0631 | 0.4948 | 0.0184 | 5.4286 | 3.5523 | 2 | 12 | ABOVE |
| Manchester City | 7 | 0.0284 | 0.0201 | -0.0207 | 0.0775 | 0.4948 | 0.0140 | 7.1429 | 5.2418 | 1 | 14 |  |
| West Ham United | 7 | 0.0274 | 0.0206 | -0.0231 | 0.0779 | 0.4948 | 0.0136 | 8.0000 | 6.3246 | 3 | 20 |  |
| Liverpool | 7 | 0.0095 | 0.0164 | -0.0307 | 0.0498 | 0.4948 | 0.0047 | 8.5714 | 5.4729 | 2 | 18 |  |
| Aston Villa | 6 | 0.0070 | 0.0243 | -0.0555 | 0.0695 | 0.4563 | 0.0032 | 8.6667 | 6.7725 | 2 | 19 |  |
| Everton | 7 | 0.0058 | 0.0186 | -0.0396 | 0.0512 | 0.4948 | 0.0028 | 10.5714 | 5.4729 | 4 | 20 |  |
| Arsenal | 7 | 0.0039 | 0.0224 | -0.0508 | 0.0587 | 0.4948 | 0.0020 | 10.5714 | 5.9682 | 2 | 17 |  |
| Brighton & Hove Albion | 7 | -0.0091 | 0.0164 | -0.0493 | 0.0311 | 0.4948 | -0.0045 | 10.8571 | 4.7409 | 5 | 19 |  |
| AFC Bournemouth | 6 | -0.0105 | 0.0200 | -0.0620 | 0.0411 | 0.4563 | -0.0048 | 10.8333 | 5.4191 | 5 | 20 |  |
| **Chelsea** | 7 | -0.0290 | 0.0218 | -0.0823 | 0.0243 | 0.4948 | -0.0143 | 13.4286 | 6.3471 | 2 | 20 |  |
| **Tottenham Hotspur** | 7 | -0.0310 | 0.0229 | -0.0871 | 0.0250 | 0.4948 | -0.0153 | 13.0000 | 6.8313 | 1 | 20 |  |
| Newcastle United | 7 | -0.0340 | 0.0121 | -0.0636 | -0.0044 | 0.4948 | -0.0168 | 14.0000 | 3.3166 | 10 | 18 | BELOW |
| Manchester United | 7 | -0.0415 | 0.0067 | -0.0578 | -0.0252 | 0.4948 | -0.0205 | 16.0000 | 1.4142 | 14 | 18 | BELOW |

Flags (95% interval excludes zero): 4 of 14 clubs (2 above, 2 below). Expected by chance at 5% two-sided: 0.70 (binomial P(≥4) = 0.004173).

### 4(d) Club-level money correlation

Across 14 clubs with ≥6 seasons, mean log_value_rel vs mean season-centred NETavailability: Pearson r = -0.2352 (p = 0.418), Spearman ρ = -0.1956 (p = 0.503).


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

### 5ii. (ii) 2018/19–2025/26 only — 7 seasons: INDICATIVE 0 (none), FINAL 4 (2022/2023–2025/2026)

140 club-seasons, 29 clubs.

**ICC — 7 seasons: INDICATIVE 0 (none), FINAL 4 (2022/2023–2025/2026)**

| sample | clubs | obs | n0 | MSB | MSW | var_between | var_within | ICC | ci_lo | ci_hi |
|---|---|---|---|---|---|---|---|---|---|---|
| all clubs | 29 | 140 | 4.78776 | 0.00394414 | 0.00237993 | 0.000326709 | 0.00237993 | 0.120707 | 0 | 0.270903 |
| clubs ≥6 seasons | 14 | 96 | 6.85577 | 0.0064492 | 0.00237832 | 0.000593789 | 0.00237832 | 0.199787 | 0.00134836 | 0.365784 |

**Split-half — 7 seasons: INDICATIVE 0 (none), FINAL 4 (2022/2023–2025/2026)** (clubs with ≥3 seasons in each half)

| split | half_a | half_b | n | pearson | p_pearson | spearman | p_spearman |
|---|---|---|---|---|---|---|---|
| odd v even | odd seasons (2014/15, 2016/17, …) | even seasons (2015/16, 2017/18, …) | 13 | 0.7418 | 0.0037 | 0.7582 | 0.0027 |
| first v second half | 2018/2019–2022/2023 | 2023/2024–2025/2026 | 14 | 0.3437 | 0.2289 | 0.2967 | 0.3030 |

- odd v even clubs (n=13): AFC Bournemouth, Arsenal, Brighton & Hove Albion, Chelsea, Crystal Palace, Everton, Liverpool, Manchester City, Manchester United, Newcastle United, Tottenham Hotspur, West Ham United, Wolverhampton Wanderers

- first v second half clubs (n=14): AFC Bournemouth, Arsenal, Aston Villa, Brighton & Hove Albion, Chelsea, Crystal Palace, Everton, Liverpool, Manchester City, Manchester United, Newcastle United, Tottenham Hotspur, West Ham United, Wolverhampton Wanderers

**Permutation — 7 seasons: INDICATIVE 0 (none), FINAL 4 (2022/2023–2025/2026)** (shuffle club labels within season, 10,000 draws, seed 20260930; statistic = season-count-weighted variance of club means, clubs ≥6 seasons)

| clubs_ge6 | observed | perm_mean | perm_p95 | ratio_obs_to_mean | p |
|---|---|---|---|---|---|
| 14 | 0.00087333 | 0.000381478 | 0.000638338 | 2.28933 | 0.00219978 |

### 5(iii). FINAL seasons only (2022/23–2025/26) — not run

Four seasons are too few: no club can reach the ≥6-season threshold used by the permutation statistic and the club table, and a split-half needs ≥3 seasons in each half (≥6 in total). An ICC on 4 seasons would rest on ≤4 observations per club; it is not reported.


