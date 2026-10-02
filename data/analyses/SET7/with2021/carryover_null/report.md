# Club persistence beyond one-season carry-over

## 1. Provenance and checks

Run 2026-10-02 05:33.

Input (read-only): `persistence/op1_panel.csv` — 160 rows. It is the panel the persistence step built; its `c` column is the season-centred NETavailability (club value − that season's 20-club mean).

**(a)** rows 160 (configured: 8 seasons × 20 = 160); seasons 8 (2018/2019–2025/2026); per-season counts [np.int64(20)]; clubs 30 (club_seasons.csv: 30) → **PASS**

**(b)** recomputed season-centred value vs panel column `c`: max |difference| = 9.89e-17 (tolerance 1e-9) → **PASS**

**(c)** OLS of c(t) on c(t−1), clubs in consecutive seasons: n = 119 pairs, slope = **0.340675** (SE 0.0840); recomputed from club_seasons.csv: 119 pairs, slope 0.340675, tolerance 1e-09 → **PASS**. Pooled lag-1 Pearson correlation on the same pairs: **ρ = 0.351218**. This ρ is used in Ops 2 and 3 (the pooled lag-1 correlation; it differs from the slope by +0.0105).

**(d)** the persistence step's permutation statistic (season-count-weighted variance of club means, 18 clubs ≥6 seasons): **0.0006818301**; recomputed from club_seasons.csv: 0.0006818301, tolerance 1e-09 → **PASS**

**(e)** this module's vectorised estimators against the persistence step's functions on the same panel: ICC all 0.102431 (0.102431), ICC ≥6 0.161965 (0.161965), odd/even r 0.697880 on 14 clubs (0.697880, n 14), uncorrected flags 3 (3); tolerance 1e-09 → **PASS**

Self-checks against the run's own inputs: ALL PASS


## 2. Corrected club intervals

ρ = 0.3512 (pooled lag-1 Pearson, step 1). Effective n = n × (1 − ρ)/(1 + ρ) = n × 0.4801; adjusted SE = sd/√n_eff; t on max(n_eff − 1, 1) df (fractional df). Raw interval = the persistence step's: mean ± t(n−1)·sd/√n. The adjustment widens each interval by the factor t_adj·√n / (t_raw·√n_eff), e.g. 2.01× for 8 seasons and 2.57× for 6.

| club | seasons | mean | sd | se_raw | lo_raw | hi_raw | n_eff | df_adj | se_adj | lo_adj | hi_adj | flag_raw | flag_adj |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Wolverhampton Wanderers | 8 | 0.0578 | 0.0540 | 0.0191 | 0.0126 | 0.1030 | 3.8412 | 2.8412 | 0.0276 | -0.0328 | 0.1484 | ABOVE |  |
| Fulham | 6 | 0.0406 | 0.0252 | 0.0103 | 0.0141 | 0.0670 | 2.8809 | 1.8809 | 0.0148 | -0.0273 | 0.1085 | ABOVE |  |
| Manchester City | 8 | 0.0359 | 0.0502 | 0.0177 | -0.0060 | 0.0779 | 3.8412 | 2.8412 | 0.0256 | -0.0481 | 0.1200 |  |  |
| Crystal Palace | 8 | 0.0276 | 0.0353 | 0.0125 | -0.0019 | 0.0571 | 3.8412 | 2.8412 | 0.0180 | -0.0315 | 0.0867 |  |  |
| West Ham United | 8 | 0.0275 | 0.0507 | 0.0179 | -0.0149 | 0.0699 | 3.8412 | 2.8412 | 0.0259 | -0.0575 | 0.1125 |  |  |
| Everton | 8 | 0.0066 | 0.0453 | 0.0160 | -0.0312 | 0.0444 | 3.8412 | 2.8412 | 0.0231 | -0.0693 | 0.0825 |  |  |
| Aston Villa | 7 | 0.0042 | 0.0562 | 0.0212 | -0.0478 | 0.0561 | 3.3610 | 2.3610 | 0.0306 | -0.1101 | 0.1185 |  |  |
| Arsenal | 8 | 0.0037 | 0.0556 | 0.0197 | -0.0428 | 0.0502 | 3.8412 | 2.8412 | 0.0284 | -0.0895 | 0.0969 |  |  |
| Southampton | 6 | 0.0012 | 0.0493 | 0.0201 | -0.0505 | 0.0528 | 2.8809 | 1.8809 | 0.0290 | -0.1316 | 0.1339 |  |  |
| Liverpool | 8 | 0.0002 | 0.0536 | 0.0190 | -0.0446 | 0.0450 | 3.8412 | 2.8412 | 0.0273 | -0.0896 | 0.0901 |  |  |
| Burnley | 6 | -0.0056 | 0.0360 | 0.0147 | -0.0434 | 0.0321 | 2.8809 | 1.8809 | 0.0212 | -0.1026 | 0.0913 |  |  |
| Brighton & Hove Albion | 8 | -0.0096 | 0.0396 | 0.0140 | -0.0428 | 0.0235 | 3.8412 | 2.8412 | 0.0202 | -0.0761 | 0.0568 |  |  |
| AFC Bournemouth | 6 | -0.0119 | 0.0489 | 0.0200 | -0.0633 | 0.0394 | 2.8809 | 1.8809 | 0.0288 | -0.1438 | 0.1199 |  |  |
| Chelsea | 8 | -0.0185 | 0.0576 | 0.0204 | -0.0666 | 0.0297 | 3.8412 | 2.8412 | 0.0294 | -0.1150 | 0.0781 |  |  |
| Tottenham Hotspur | 8 | -0.0248 | 0.0573 | 0.0203 | -0.0727 | 0.0231 | 3.8412 | 2.8412 | 0.0292 | -0.1208 | 0.0713 |  |  |
| Leicester City | 6 | -0.0252 | 0.0344 | 0.0140 | -0.0613 | 0.0109 | 2.8809 | 1.8809 | 0.0202 | -0.1178 | 0.0674 |  |  |
| Manchester United | 8 | -0.0281 | 0.0346 | 0.0122 | -0.0571 | 0.0009 | 3.8412 | 2.8412 | 0.0177 | -0.0862 | 0.0300 |  |  |
| Newcastle United | 8 | -0.0392 | 0.0333 | 0.0118 | -0.0671 | -0.0114 | 3.8412 | 2.8412 | 0.0170 | -0.0951 | 0.0166 | BELOW |  |

Flags: raw 3 of 18 (2 above, 1 below); adjusted **0 of 18** (0 above, 0 below).

Expected by chance at a nominal 5% two-sided level: 0.90 of 18. Binomial P(≥0) = 1 (assumes the 18 intervals are independent and exactly 5%; the adjusted intervals are approximate, and the clubs share season-centring, so step 3(d) gives the simulation-based chance benchmark).


## 3. Carry-over-only null

5,000 simulated panels, seed 20260930. No club effect. For each of the 30 clubs a stationary AR(1) series over the 8 start years 2018/19–2025/26 with lag-1 coefficient ρ = 0.3512 and marginal SD 0.05048 (observed SD of c, ddof 1): x₁ ~ N(0, SD²), xₜ = ρ·xₜ₋₁ + N(0, SD²(1−ρ²)). The series runs through seasons a club was absent, so a club's seasons either side of a gap correlate at ρ^gap. Only the 160 observed club-seasons are kept, then each season is centred on its 20-club mean exactly as the real data are. The step 2 correction uses the fixed step 1 ρ in every simulated panel.

Calibration: in the simulated centred panels the pooled lag-1 correlation on the same 119 pairs averages 0.3438 (5th–95th pct 0.199–0.484; observed 0.3512) and the SD of the centred value averages 0.04932 (observed 0.05048). Season-centring removes a little of both, so the null reproduces slightly less carry-over than observed on average.

| statistic | observed | sim_mean | sim_median | sim_p95 | share_ge_obs | p_plus1 |
|---|---|---|---|---|---|---|
| (a) ICC, all 35 clubs | 0.102431 | 0.137675 | 0.133667 | 0.270596 | 0.6534 | 0.653469 |
| (a) ICC, 19 clubs ≥6 seasons | 0.161965 | 0.133728 | 0.127236 | 0.274508 | 0.3398 | 0.339932 |
| (b) permutation statistic (weighted var of club means, ≥6 seasons) | 0.00068183 | 0.000588254 | 0.000562643 | 0.00096822 | 0.2848 | 0.284943 |
| (c) odd v even split-half Pearson r (14 clubs) | 0.69788 | 0.532542 | 0.562056 | 0.808609 | 0.2248 | 0.224955 |
| (d) clubs flagged, uncorrected intervals | 3 | 2.5914 | 2 | 5 | 0.4876 | 0.487702 |
| (d) clubs flagged, step 2 corrected intervals | 0 | 0.2334 | 0 | 1 | 1 | 1 |

`share_ge_obs` = share of the 5,000 simulations at or above the observed value (the p-value against carry-over only); `p_plus1` = (k+1)/(N+1) for reference. ICCs are truncated at 0 as in the persistence step, so many simulated ICCs are exactly 0.

Share of simulated panels with ICC (all clubs) truncated to 0: 0.029.

- Distribution of simulated flag counts (uncorrected): 0: 0.064, 1: 0.187, 2: 0.261, 3: 0.232, 4: 0.146, 5: 0.070, 6: 0.029, 7: 0.007, 8: 0.003, 9: 0.000, 10: 0.000
- Distribution of simulated flag counts (corrected): 0: 0.790, 1: 0.189, 2: 0.019, 3: 0.002


