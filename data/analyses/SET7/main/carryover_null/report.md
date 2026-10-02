# Club persistence beyond one-season carry-over

## 1. Provenance and checks

Run 2026-10-02 05:33.

Input (read-only): `persistence/op1_panel.csv` — 140 rows. It is the panel the persistence step built; its `c` column is the season-centred NETavailability (club value − that season's 20-club mean).

**(a)** rows 140 (configured: 7 seasons × 20 = 140); seasons 7 (2018/2019–2025/2026); per-season counts [np.int64(20)]; clubs 29 (club_seasons.csv: 29) → **PASS**

**(b)** recomputed season-centred value vs panel column `c`: max |difference| = 9.71e-17 (tolerance 1e-9) → **PASS**

**(c)** OLS of c(t) on c(t−1), clubs in consecutive seasons: n = 85 pairs, slope = **0.415243** (SE 0.0988); recomputed from club_seasons.csv: 85 pairs, slope 0.415243, tolerance 1e-09 → **PASS**. Pooled lag-1 Pearson correlation on the same pairs: **ρ = 0.418980**. This ρ is used in Ops 2 and 3 (the pooled lag-1 correlation; it differs from the slope by +0.0037).

**(d)** the persistence step's permutation statistic (season-count-weighted variance of club means, 14 clubs ≥6 seasons): **0.0008733296**; recomputed from club_seasons.csv: 0.0008733296, tolerance 1e-09 → **PASS**

**(e)** this module's vectorised estimators against the persistence step's functions on the same panel: ICC all 0.120707 (0.120707), ICC ≥6 0.199787 (0.199787), odd/even r 0.741808 on 13 clubs (0.741808, n 13), uncorrected flags 4 (4); tolerance 1e-09 → **PASS**

Self-checks against the run's own inputs: ALL PASS


## 2. Corrected club intervals

ρ = 0.4190 (pooled lag-1 Pearson, step 1). Effective n = n × (1 − ρ)/(1 + ρ) = n × 0.4095; adjusted SE = sd/√n_eff; t on max(n_eff − 1, 1) df (fractional df). Raw interval = the persistence step's: mean ± t(n−1)·sd/√n. The adjustment widens each interval by the factor t_adj·√n / (t_raw·√n_eff), e.g. 2.95× for 7 seasons and 3.81× for 6.

| club | seasons | mean | sd | se_raw | lo_raw | hi_raw | n_eff | df_adj | se_adj | lo_adj | hi_adj | flag_raw | flag_adj |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Wolverhampton Wanderers | 7 | 0.0663 | 0.0522 | 0.0197 | 0.0180 | 0.1146 | 2.8662 | 1.8662 | 0.0309 | -0.0760 | 0.2086 | ABOVE |  |
| Crystal Palace | 7 | 0.0360 | 0.0281 | 0.0106 | 0.0101 | 0.0620 | 2.8662 | 1.8662 | 0.0166 | -0.0405 | 0.1125 | ABOVE |  |
| Manchester City | 7 | 0.0324 | 0.0531 | 0.0201 | -0.0167 | 0.0814 | 2.8662 | 1.8662 | 0.0313 | -0.1122 | 0.1769 |  |  |
| West Ham United | 7 | 0.0272 | 0.0548 | 0.0207 | -0.0235 | 0.0778 | 2.8662 | 1.8662 | 0.0323 | -0.1220 | 0.1763 |  |  |
| Liverpool | 7 | 0.0127 | 0.0436 | 0.0165 | -0.0276 | 0.0530 | 2.8662 | 1.8662 | 0.0257 | -0.1060 | 0.1314 |  |  |
| Aston Villa | 6 | 0.0071 | 0.0609 | 0.0249 | -0.0568 | 0.0711 | 2.4568 | 1.4568 | 0.0389 | -0.2367 | 0.2510 |  |  |
| Arsenal | 7 | 0.0064 | 0.0595 | 0.0225 | -0.0486 | 0.0614 | 2.8662 | 1.8662 | 0.0351 | -0.1556 | 0.1685 |  |  |
| Everton | 7 | 0.0059 | 0.0488 | 0.0185 | -0.0393 | 0.0510 | 2.8662 | 1.8662 | 0.0288 | -0.1272 | 0.1389 |  |  |
| Brighton & Hove Albion | 7 | -0.0094 | 0.0428 | 0.0162 | -0.0490 | 0.0302 | 2.8662 | 1.8662 | 0.0253 | -0.1260 | 0.1072 |  |  |
| AFC Bournemouth | 6 | -0.0119 | 0.0489 | 0.0200 | -0.0633 | 0.0394 | 2.4568 | 1.4568 | 0.0312 | -0.2077 | 0.1838 |  |  |
| Chelsea | 7 | -0.0258 | 0.0581 | 0.0220 | -0.0795 | 0.0280 | 2.8662 | 1.8662 | 0.0343 | -0.1840 | 0.1325 |  |  |
| Tottenham Hotspur | 7 | -0.0286 | 0.0608 | 0.0230 | -0.0848 | 0.0276 | 2.8662 | 1.8662 | 0.0359 | -0.1942 | 0.1370 |  |  |
| Newcastle United | 7 | -0.0341 | 0.0325 | 0.0123 | -0.0642 | -0.0041 | 2.8662 | 1.8662 | 0.0192 | -0.1225 | 0.0543 | BELOW |  |
| Manchester United | 7 | -0.0389 | 0.0176 | 0.0067 | -0.0552 | -0.0226 | 2.8662 | 1.8662 | 0.0104 | -0.0868 | 0.0090 | BELOW |  |

Flags: raw 4 of 14 (2 above, 2 below); adjusted **0 of 14** (0 above, 0 below).

Expected by chance at a nominal 5% two-sided level: 0.70 of 14. Binomial P(≥0) = 1 (assumes the 14 intervals are independent and exactly 5%; the adjusted intervals are approximate, and the clubs share season-centring, so step 3(d) gives the simulation-based chance benchmark).


## 3. Carry-over-only null

5,000 simulated panels, seed 20260930. No club effect. For each of the 29 clubs a stationary AR(1) series over the 8 start years 2018/19–2025/26 with lag-1 coefficient ρ = 0.4190 and marginal SD 0.05191 (observed SD of c, ddof 1): x₁ ~ N(0, SD²), xₜ = ρ·xₜ₋₁ + N(0, SD²(1−ρ²)). The series runs through seasons a club was absent, so a club's seasons either side of a gap correlate at ρ^gap. Only the 140 observed club-seasons are kept, then each season is centred on its 20-club mean exactly as the real data are. The step 2 correction uses the fixed step 1 ρ in every simulated panel.

Calibration: in the simulated centred panels the pooled lag-1 correlation on the same 85 pairs averages 0.4091 (5th–95th pct 0.250–0.562; observed 0.4190) and the SD of the centred value averages 0.05072 (observed 0.05191). Season-centring removes a little of both, so the null reproduces slightly less carry-over than observed on average.

| statistic | observed | sim_mean | sim_median | sim_p95 | share_ge_obs | p_plus1 |
|---|---|---|---|---|---|---|
| (a) ICC, all 35 clubs | 0.120707 | 0.16775 | 0.165818 | 0.310765 | 0.6968 | 0.696861 |
| (a) ICC, 19 clubs ≥6 seasons | 0.199787 | 0.161575 | 0.155353 | 0.327048 | 0.3406 | 0.340732 |
| (b) permutation statistic (weighted var of club means, ≥6 seasons) | 0.00087333 | 0.000693982 | 0.000658797 | 0.00118817 | 0.229 | 0.229154 |
| (c) odd v even split-half Pearson r (13 clubs) | 0.741808 | 0.553981 | 0.585438 | 0.828975 | 0.1724 | 0.172565 |
| (d) clubs flagged, uncorrected intervals | 4 | 2.192 | 2 | 5 | 0.1656 | 0.165767 |
| (d) clubs flagged, step 2 corrected intervals | 0 | 0.0484 | 0 | 0 | 1 | 1 |

`share_ge_obs` = share of the 5,000 simulations at or above the observed value (the p-value against carry-over only); `p_plus1` = (k+1)/(N+1) for reference. ICCs are truncated at 0 as in the persistence step, so many simulated ICCs are exactly 0.

Share of simulated panels with ICC (all clubs) truncated to 0: 0.022.

- Distribution of simulated flag counts (uncorrected): 0: 0.087, 1: 0.245, 2: 0.291, 3: 0.211, 4: 0.112, 5: 0.041, 6: 0.010, 7: 0.002, 8: 0.000, 9: 0.000
- Distribution of simulated flag counts (corrected): 0: 0.953, 1: 0.046, 2: 0.001, 3: 0.000


