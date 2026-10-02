# Analysis battery — SET7

Battery run 2026-10-02 05:35. Run folder `<run>/run_on` (table suffix _on). Seasons 18/19, 19/20, 21/22, 22/23, 23/24, 24/25, 25/26 (input sets: late 7); robustness season 20/21. Squad values: `club_season_values.csv` by (season, team_id); points and finish: standings.csv. Outputs in `<run>/analyses/SET7/`.

Steps run: `regressions`, `half_season_inputs`, `half_season_models`, `persistence`, `carryover_null`, `asymmetry`, `two_season_runs`, `extremity`, `power`; `fixed_effects`.


## Variant `main` — seasons 18/19, 19/20, 21/22, 22/23, 23/24, 24/25, 25/26

Inputs: 140 club-seasons, 7 seasons; squad values dated 2018-07-01, 2019-07-01, 2021-07-01, 2022-07-01, 2023-07-01, 2024-07-01, 2025-07-01.

Steps: F_regressions rc 0 50 s; G_half_season_inputs rc 0 1 s; G_half_season_models rc 0 89 s; H2_op1 rc 0 3 s; H2_op2 rc 0 3 s; H2_op3 rc 0 3 s; H3_op1 rc 0 3 s; H3_op2 rc 0 3 s; H3_op3 rc 0 3 s; H3_op4 rc 0 2 s; H3b_op1 rc 0 3 s; H3b_op2 rc 0 3 s; H3b_op3 rc 0 7 s; H3b_op4 rc 0 2 s; H3b_op5 rc 0 3 s; H_op1 rc 0 2 s; H_op2 rc 0 30 s; H_op3 rc 0 2 s; H_op4 rc 0 8 s; H_op5 rc 0 41 s; L_op1 rc 0 2 s; L_op2 rc 0 4 s; L_op3 rc 0 3 s; L_op4 rc 0 3 s; N_main rc 0 6 s.

**F** (`regressions`): pooled models with season FE, HC3 — (a) points ~ value, (c) points ~ value + NETavailability:

| pool | n | a_R2 | c_R2 | dR2 | dR2_F_p | c_lv_coef | c_lv_se_hc3 | c_netav_coef | c_netav_se_hc3 | c_netav_p_hc3 | c_netav_beta |
|---|---|---|---|---|---|---|---|---|---|---|---|
| FINAL 2022/23–2025/26 | 80 | 0.481 | 0.541 | 0.0600 | 0.0027 | 16.505 | 2.460 | 82.059 | 27.328 | 0.0027 | 0.264 |
| paper 7 (2018/19, 2019/20, 2021/22–2025/26) | 140 | 0.549 | 0.617 | 0.0682 | 0.0000 | 17.638 | 1.865 | 92.782 | 20.061 | 0.0000 | 0.274 |
| all seasons in the file | 140 | 0.549 | 0.617 | 0.0682 | 0.0000 | 17.638 | 1.865 | 92.782 | 20.061 | 0.0000 | 0.274 |

Same model by `fixed_effects.ols_fe` (decomposition): 92.782 ± 20.061 — agrees with the 'all seasons in the file' row. Without Tottenham and Chelsea: 80.898 ± 23.065 (n 126, p 0.0006, ΔR² 0.0464).

**G** (`half_season_models`): second-half points ~ value + first-half absence per match (b), + first-half points (c); HC3:

| pool | model | n | coef | se_hc3 | p_hc3 | dR2 | F_p | boot_lo | boot_hi |
|---|---|---|---|---|---|---|---|---|---|
| FINAL 2022/23-2025/26 | b | 80 | -0.022 | 0.012 | 0.064 | 0.0367 | 0.023 | -0.043 | -0.002 |
| FINAL 2022/23-2025/26 | c | 80 | -0.011 | 0.011 | 0.298 | 0.0086 | 0.209 | -0.033 | 0.008 |
| paper 7 (no 2020/21) | b | 140 | -0.024 | 0.008 | 0.002 | 0.0462 | 0.001 | -0.038 | -0.009 |
| paper 7 (no 2020/21) | c | 140 | -0.015 | 0.007 | 0.045 | 0.0153 | 0.034 | -0.028 | -0.001 |
| all seasons in the file | b | 140 | -0.024 | 0.008 | 0.002 | 0.0462 | 0.001 | -0.037 | -0.010 |
| all seasons in the file | c | 140 | -0.015 | 0.007 | 0.045 | 0.0153 | 0.034 | -0.028 | -0.001 |

**H** (`persistence`): ICC all clubs 0.121 [0.000, 0.271] (n obs 140, 29 clubs), clubs ≥6 seasons 0.200 [0.001, 0.366]; split-half odd/even r 0.742 (n 13), halves r 0.344 (n 14); permutation p 0.0022; lag-1 slope 0.415 (SE 0.099, n 85 consecutive-season pairs).

**H2** (`carryover_null`): carry-over-only null (ρ 0.4190) — icc_all obs 0.1207 share≥obs 0.697; icc_ge6 obs 0.1998 share≥obs 0.341; permutation obs 0.0008733 share≥obs 0.229; split_half obs 0.7418 share≥obs 0.172; flags_uncorrected obs 4 share≥obs 0.166; flags_corrected obs 0 share≥obs 1.000; corrected flags 0 of 14.

**H3** (`asymmetry`): Tottenham-depth two-season run share of null panels 0.4930, Chelsea-depth 0.3270; stickiness slope difference (lower − upper) +0.206 (p 0.523, null share 0.270).

**H3b** (`two_season_runs`): sum rule, Tottenham depth: share of simulated leagues with a pair as deep = 0.4250 (Chelsea depth 0.6044); expectation 0.3–0.7: MET.

**L** (`extremity`):

| test | run | c·N | c·Q | m·N | m·Q | headline_share | headline_config | verdict |
|---|---|---|---|---|---|---|---|---|
| T1 | Tottenham 2025/26 | 0.6672 | 0.2452 | 0.3762 | 0.2278 | 0.6672 | c·N | NOT SHOWN RARE |
| T1 | Tottenham 2024/25 | 0.9996 | 0.9960 | 0.9926 | 0.9920 | 0.9996 | c·N | NOT SHOWN RARE |
| T2 | Tottenham 2024/25–2025/26 | 0.4250 | 0.1998 | 0.2330 | 0.1826 | 0.4250 | c·N | NOT SHOWN RARE |
| T2 | Chelsea 2022/23–2023/24 | 0.6044 | 0.3980 | 0.5258 | 0.5100 | 0.6044 | c·N | NOT SHOWN RARE |
| T3 | Tottenham 2024/25–2025/26 | 0.4930 | 0.3966 | 0.3416 | 0.3414 | 0.4930 | c·N | NOT SHOWN RARE |
| T3 | Chelsea 2022/23–2023/24 | 0.3270 | 0.2220 | 0.3096 | 0.3062 | 0.3270 | c·N | NOT SHOWN RARE |
| T4 | Tottenham 2025/26 gap to 19th | 0.2762 | 0.0498 | 0.1084 | 0.0406 | 0.2762 | c·N | NOT SHOWN RARE |

**N** (`power`; `main/power/headline.csv`): 95% upper bound on a lasting club edge from ICC-all σ_u = 2.30 pp (≈ 2.12 points a season at 92 per unit, 1.90 at 82.5); MDE at 80% power: ICC-all not reached on s ≤ 0.30, any-of-three not reached on s ≤ 0.30 (max power on s ≤ 0.30: ICC-all 0.600, any-of-three 0.461).

| quantity | statistic | grid_min_s | s | sigma_u_pp | pts_92 | pts_63 | pts_121 | pts_82_5 |
|---|---|---|---|---|---|---|---|---|
| MDE at 80% power | ICC-all |  |  |  |  |  |  |  |
| MDE at 80% power | ICC ≥6 |  |  |  |  |  |  |  |
| MDE at 80% power | permutation |  |  |  |  |  |  |  |
| MDE at 80% power | split-half |  |  |  |  |  |  |  |
| MDE at 80% power | corrected flags | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| MDE at 80% power | any (Bonferroni) |  |  |  |  |  |  |  |
| 95% upper bound | ICC-all |  | 0.197 | 2.303 | 2.119 | 1.451 | 2.789 | 1.900 |
| 95% upper bound | permutation |  |  |  |  |  |  |  |
| 95% upper bound | split-half |  |  |  |  |  |  |  |
| 95% upper bound | ICC ≥6 |  |  |  |  |  |  |  |

Self-checks of the steps (targets recomputed from this run's inputs): H2: 0 FAIL of 1; H3: 0 FAIL of 1; H3b: 0 FAIL of 16; L: 0 FAIL of 12; N: 0 FAIL of 7.


## Variant `with2021` — seasons 18/19, 19/20, 20/21, 21/22, 22/23, 23/24, 24/25, 25/26

Inputs: 160 club-seasons, 8 seasons; squad values dated 2018-07-01, 2019-07-01, 2020-07-01, 2021-07-01, 2022-07-01, 2023-07-01, 2024-07-01, 2025-07-01.

Steps: F_regressions rc 0 49 s; G_half_season_inputs rc 0 2 s; G_half_season_models rc 0 89 s; H2_op1 rc 0 3 s; H2_op2 rc 0 3 s; H2_op3 rc 0 3 s; H3_op1 rc 0 3 s; H3_op2 rc 0 3 s; H3_op3 rc 0 3 s; H3_op4 rc 0 2 s; H3b_op1 rc 0 2 s; H3b_op2 rc 0 3 s; H3b_op3 rc 0 9 s; H3b_op4 rc 0 2 s; H3b_op5 rc 0 2 s; H_op1 rc 0 2 s; H_op2 rc 0 32 s; H_op3 rc 0 2 s; H_op4 rc 0 8 s; H_op5 rc 0 42 s; L_op1 rc 0 2 s; L_op2 rc 0 4 s; L_op3 rc 0 4 s; L_op4 rc 0 3 s; N_main rc 0 7 s.

**F** (`regressions`): pooled models with season FE, HC3 — (a) points ~ value, (c) points ~ value + NETavailability:

| pool | n | a_R2 | c_R2 | dR2 | dR2_F_p | c_lv_coef | c_lv_se_hc3 | c_netav_coef | c_netav_se_hc3 | c_netav_p_hc3 | c_netav_beta |
|---|---|---|---|---|---|---|---|---|---|---|---|
| FINAL 2022/23–2025/26 | 80 | 0.481 | 0.541 | 0.0600 | 0.0027 | 16.505 | 2.460 | 82.059 | 27.328 | 0.0027 | 0.264 |
| paper 7 (2018/19, 2019/20, 2021/22–2025/26) | 140 | 0.549 | 0.617 | 0.0682 | 0.0000 | 17.638 | 1.865 | 92.782 | 20.061 | 0.0000 | 0.274 |
| all seasons in the file | 160 | 0.560 | 0.625 | 0.0647 | 0.0000 | 17.474 | 1.662 | 91.709 | 18.620 | 0.0000 | 0.266 |

Same model by `fixed_effects.ols_fe` (decomposition): 91.709 ± 18.620 — agrees with the 'all seasons in the file' row. Without Tottenham and Chelsea: 81.506 ± 21.049 (n 144, p 0.0002, ΔR² 0.0464).

**G** (`half_season_models`): second-half points ~ value + first-half absence per match (b), + first-half points (c); HC3:

| pool | model | n | coef | se_hc3 | p_hc3 | dR2 | F_p | boot_lo | boot_hi |
|---|---|---|---|---|---|---|---|---|---|
| FINAL 2022/23-2025/26 | b | 80 | -0.022 | 0.012 | 0.064 | 0.0367 | 0.023 | -0.043 | -0.002 |
| FINAL 2022/23-2025/26 | c | 80 | -0.011 | 0.011 | 0.298 | 0.0086 | 0.209 | -0.033 | 0.008 |
| paper 7 (no 2020/21) | b | 140 | -0.024 | 0.008 | 0.002 | 0.0462 | 0.001 | -0.038 | -0.009 |
| paper 7 (no 2020/21) | c | 140 | -0.015 | 0.007 | 0.045 | 0.0153 | 0.034 | -0.028 | -0.001 |
| all seasons in the file | b | 160 | -0.023 | 0.007 | 0.001 | 0.0403 | 0.001 | -0.036 | -0.009 |
| all seasons in the file | c | 160 | -0.013 | 0.007 | 0.050 | 0.0122 | 0.038 | -0.026 | -0.000 |

**H** (`persistence`): ICC all clubs 0.102 [0.000, 0.234] (n obs 160, 30 clubs), clubs ≥6 seasons 0.162 [0.013, 0.283]; split-half odd/even r 0.698 (n 14), halves r 0.198 (n 13); permutation p 0.0040; lag-1 slope 0.341 (SE 0.084, n 119 consecutive-season pairs).

**H2** (`carryover_null`): carry-over-only null (ρ 0.3512) — icc_all obs 0.1024 share≥obs 0.653; icc_ge6 obs 0.162 share≥obs 0.340; permutation obs 0.0006818 share≥obs 0.285; split_half obs 0.6979 share≥obs 0.225; flags_uncorrected obs 3 share≥obs 0.488; flags_corrected obs 0 share≥obs 1.000; corrected flags 0 of 18.

**H3** (`asymmetry`): Tottenham-depth two-season run share of null panels 0.4900, Chelsea-depth 0.3178; stickiness slope difference (lower − upper) +0.350 (p 0.100, null share 0.117).

**H3b** (`two_season_runs`): sum rule, Tottenham depth: share of simulated leagues with a pair as deep = 0.4046 (Chelsea depth 0.6068); expectation 0.3–0.7: MET.

**L** (`extremity`):

| test | run | c·N | c·Q | m·N | m·Q | headline_share | headline_config | verdict |
|---|---|---|---|---|---|---|---|---|
| T1 | Tottenham 2025/26 | 0.6414 | 0.2378 | 0.3518 | 0.2296 | 0.6414 | c·N | NOT SHOWN RARE |
| T1 | Tottenham 2024/25 | 0.9994 | 0.9982 | 0.9946 | 0.9954 | 0.9994 | c·N | NOT SHOWN RARE |
| T2 | Tottenham 2024/25–2025/26 | 0.4046 | 0.1854 | 0.2224 | 0.1730 | 0.4046 | c·N | NOT SHOWN RARE |
| T2 | Chelsea 2022/23–2023/24 | 0.6068 | 0.4016 | 0.5386 | 0.5364 | 0.6068 | c·N | NOT SHOWN RARE |
| T3 | Tottenham 2024/25–2025/26 | 0.4900 | 0.4160 | 0.3466 | 0.3630 | 0.4900 | c·N | NOT SHOWN RARE |
| T3 | Chelsea 2022/23–2023/24 | 0.3178 | 0.2104 | 0.3144 | 0.3184 | 0.3184 | m·Q | NOT SHOWN RARE |
| T4 | Tottenham 2025/26 gap to 19th | 0.2736 | 0.0556 | 0.1056 | 0.0458 | 0.2736 | c·N | NOT SHOWN RARE |

**N** (`power`; `with2021/power/headline.csv`): 95% upper bound on a lasting club edge from ICC-all σ_u = 2.23 pp (≈ 2.05 points a season at 92 per unit, 1.84 at 82.5); MDE at 80% power: ICC-all not reached on s ≤ 0.30, any-of-three not reached on s ≤ 0.30 (max power on s ≤ 0.30: ICC-all 0.688, any-of-three 0.541).

| quantity | statistic | grid_min_s | s | sigma_u_pp | pts_92 | pts_63 | pts_121 | pts_82_5 |
|---|---|---|---|---|---|---|---|---|
| MDE at 80% power | ICC-all |  |  |  |  |  |  |  |
| MDE at 80% power | ICC ≥6 |  |  |  |  |  |  |  |
| MDE at 80% power | permutation |  |  |  |  |  |  |  |
| MDE at 80% power | split-half |  |  |  |  |  |  |  |
| MDE at 80% power | corrected flags |  |  |  |  |  |  |  |
| MDE at 80% power | any (Bonferroni) |  |  |  |  |  |  |  |
| 95% upper bound | ICC-all |  | 0.195 | 2.229 | 2.051 | 1.404 | 2.700 | 1.839 |
| 95% upper bound | permutation |  |  |  |  |  |  |  |
| 95% upper bound | split-half |  |  |  |  |  |  |  |
| 95% upper bound | ICC ≥6 |  |  |  |  |  |  |  |

Self-checks of the steps (targets recomputed from this run's inputs): H2: 0 FAIL of 1; H3: 0 FAIL of 1; H3b: 0 FAIL of 16; L: 0 FAIL of 12; N: 0 FAIL of 7.


## Variant `exwin` — seasons 18/19, 19/20, 21/22, 22/23, 23/24, 24/25, 25/26 — Omicron and restart windows removed from within-season data

Inputs: 140 club-seasons, 7 seasons; squad values dated 2018-07-01, 2019-07-01, 2021-07-01, 2022-07-01, 2023-07-01, 2024-07-01, 2025-07-01. Fixtures removed by the windows: 19/20 92, 21/22 83; fixtures kept per club-season 27–38.

Steps: F_regressions rc 0 49 s; G_half_season_models rc 0 86 s.

**F** (`regressions`): pooled models with season FE, HC3 — (a) points ~ value, (c) points ~ value + NETavailability:

| pool | n | a_R2 | c_R2 | dR2 | dR2_F_p | c_lv_coef | c_lv_se_hc3 | c_netav_coef | c_netav_se_hc3 | c_netav_p_hc3 | c_netav_beta |
|---|---|---|---|---|---|---|---|---|---|---|---|
| FINAL 2022/23–2025/26 | 80 | 0.481 | 0.541 | 0.0601 | 0.0027 | 16.504 | 2.460 | 82.063 | 27.324 | 0.0027 | 0.264 |
| paper 7 (2018/19, 2019/20, 2021/22–2025/26) | 140 | 0.549 | 0.619 | 0.0701 | 0.0000 | 17.882 | 1.875 | 91.802 | 19.563 | 0.0000 | 0.279 |
| all seasons in the file | 140 | 0.549 | 0.619 | 0.0701 | 0.0000 | 17.882 | 1.875 | 91.802 | 19.563 | 0.0000 | 0.279 |

Same model by `fixed_effects.ols_fe` (decomposition): 91.802 ± 19.563 — agrees with the 'all seasons in the file' row. Without Tottenham and Chelsea: 79.979 ± 22.266 (n 126, p 0.0005, ΔR² 0.0481).

**G** (`half_season_models`): second-half points ~ value + first-half absence per match (b), + first-half points (c); HC3:

| pool | model | n | coef | se_hc3 | p_hc3 | dR2 | F_p | boot_lo | boot_hi |
|---|---|---|---|---|---|---|---|---|---|
| FINAL 2022/23-2025/26 | b | 80 | -0.022 | 0.012 | 0.064 | 0.0367 | 0.023 | -0.043 | -0.002 |
| FINAL 2022/23-2025/26 | c | 80 | -0.011 | 0.011 | 0.298 | 0.0086 | 0.209 | -0.033 | 0.008 |
| paper 7 (no 2020/21) | b | 140 | -0.020 | 0.008 | 0.010 | 0.0256 | 0.004 | -0.034 | -0.005 |
| paper 7 (no 2020/21) | c | 140 | -0.011 | 0.007 | 0.135 | 0.0069 | 0.113 | -0.024 | 0.003 |
| all seasons in the file | b | 140 | -0.020 | 0.008 | 0.010 | 0.0256 | 0.004 | -0.034 | -0.007 |
| all seasons in the file | c | 140 | -0.011 | 0.007 | 0.135 | 0.0069 | 0.113 | -0.025 | 0.003 |


## Points decomposition — points ~ log_value_rel + c + C(season), HC3 (fixed_effects.ols_fe); c = NETavailability − season mean

| pool | n | beta_value | se_value | beta_c | se_c | p_c | r2 | dR2 | pts_per_pp | within_sd_c | pts_per_sd | value_equiv_of_1sd | n_noTC | beta_c_noTC | se_c_noTC | p_c_noTC | dR2_noTC |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| main:paper | 140 | 17.638 | 1.865 | 92.782 | 20.061 | 0.0000 | 0.617 | 0.0682 | 0.928 | 0.052 | 4.817 | 1.314 | 126 | 80.898 | 23.065 | 0.0006 | 0.0464 |
| main:FINAL4 | 80 | 16.505 | 2.460 | 82.059 | 27.328 | 0.0036 | 0.541 | 0.0600 | 0.821 | 0.054 | 4.453 | 1.310 | 72 | 56.462 | 31.198 | 0.0749 | 0.0224 |
| with2021:paper | 160 | 17.474 | 1.662 | 91.709 | 18.620 | 0.0000 | 0.625 | 0.0647 | 0.917 | 0.050 | 4.630 | 1.303 | 144 | 81.506 | 21.049 | 0.0002 | 0.0464 |
| with2021:FINAL4 | 80 | 16.505 | 2.460 | 82.059 | 27.328 | 0.0036 | 0.541 | 0.0600 | 0.821 | 0.054 | 4.453 | 1.310 | 72 | 56.462 | 31.198 | 0.0749 | 0.0224 |
| exwin:paper | 140 | 17.882 | 1.875 | 91.802 | 19.563 | 0.0000 | 0.619 | 0.0701 | 0.918 | 0.053 | 4.880 | 1.314 | 126 | 79.979 | 22.266 | 0.0005 | 0.0481 |
| exwin:FINAL4 | 80 | 16.504 | 2.460 | 82.063 | 27.324 | 0.0036 | 0.541 | 0.0601 | 0.821 | 0.054 | 4.453 | 1.310 | 72 | 56.473 | 31.195 | 0.0748 | 0.0225 |

`<variant>:paper` = all seasons of the variant, `<variant>:FINAL4` = 2022/23–2025/26. `beta_c` = points per unit of c (÷100 = points per percentage point of NETavailability); `pts_per_sd` = β_c × within-season SD of c; `value_equiv_of_1sd` = the squad-value multiple that buys the same points (exp(β_c·SD/β_value)); `_noTC` = the same pool without Tottenham Hotspur and Chelsea.

Named club-seasons (expected = fitted with c = 0; availability part = β_c·c; other = residual; squad-value equivalent = multiple of the club's 1 July value with the same points effect, and its € amount):

| pool | season | club | points | expected_c0 | availability_part | other | c | NETavailability_rank | squad_value_text | equiv_value_multiple | equiv_value_EURm |
|---|---|---|---|---|---|---|---|---|---|---|---|
| exwin:FINAL4 | 2022/2023 | Chelsea | 44 | 64.0 | -8.0 | -12.0 | -0.0978 | 20 | €729.70m | 0.615 | -280.9 |
| exwin:FINAL4 | 2023/2024 | Chelsea | 63 | 67.8 | -7.7 | 2.9 | -0.0934 | 20 | €972.20m | 0.629 | -361.0 |
| exwin:FINAL4 | 2024/2025 | Nottingham Forest | 65 | 49.2 | 6.6 | 9.2 | 0.0800 | 1 | €390.35m | 1.488 | 190.6 |
| exwin:FINAL4 | 2024/2025 | Tottenham Hotspur | 38 | 61.7 | -7.0 | -16.7 | -0.0852 | 20 | €832.30m | 0.655 | -287.5 |
| exwin:FINAL4 | 2025/2026 | Tottenham Hotspur | 41 | 59.4 | -10.0 | -8.4 | -0.1223 | 20 | €804.90m | 0.544 | -366.7 |
| exwin:paper | 2022/2023 | Chelsea | 44 | 65.0 | -9.0 | -12.0 | -0.0978 | 20 | €729.70m | 0.605 | -288.0 |
| exwin:paper | 2023/2024 | Chelsea | 63 | 69.1 | -8.6 | 2.5 | -0.0934 | 20 | €972.20m | 0.619 | -370.2 |
| exwin:paper | 2024/2025 | Nottingham Forest | 65 | 49.0 | 7.3 | 8.7 | 0.0800 | 1 | €390.35m | 1.508 | 198.1 |
| exwin:paper | 2024/2025 | Tottenham Hotspur | 38 | 62.5 | -7.8 | -16.7 | -0.0852 | 20 | €832.30m | 0.646 | -295.0 |
| exwin:paper | 2025/2026 | Tottenham Hotspur | 41 | 60.1 | -11.2 | -7.8 | -0.1223 | 20 | €804.90m | 0.534 | -375.3 |
| exwin:paper | 2018/2019 | Wolverhampton Wanderers | 57 | 40.7 | 13.7 | 2.6 | 0.1495 | 1 | €127.80m | 2.155 | 147.5 |
| main:FINAL4 | 2022/2023 | Chelsea | 44 | 64.0 | -8.0 | -12.0 | -0.0978 | 20 | €729.70m | 0.615 | -280.9 |
| main:FINAL4 | 2023/2024 | Chelsea | 63 | 67.8 | -7.7 | 2.9 | -0.0933 | 20 | €972.20m | 0.629 | -361.0 |
| main:FINAL4 | 2024/2025 | Nottingham Forest | 65 | 49.2 | 6.6 | 9.2 | 0.0800 | 1 | €390.35m | 1.488 | 190.6 |
| main:FINAL4 | 2024/2025 | Tottenham Hotspur | 38 | 61.7 | -7.0 | -16.7 | -0.0852 | 20 | €832.30m | 0.655 | -287.5 |
| main:FINAL4 | 2025/2026 | Tottenham Hotspur | 41 | 59.4 | -10.0 | -8.4 | -0.1223 | 20 | €804.90m | 0.544 | -366.7 |
| main:paper | 2022/2023 | Chelsea | 44 | 64.8 | -9.1 | -11.7 | -0.0978 | 20 | €729.70m | 0.598 | -293.4 |
| main:paper | 2023/2024 | Chelsea | 63 | 68.8 | -8.7 | 2.8 | -0.0933 | 20 | €972.20m | 0.612 | -377.2 |
| main:paper | 2024/2025 | Nottingham Forest | 65 | 49.0 | 7.4 | 8.6 | 0.0800 | 1 | €390.35m | 1.523 | 204.1 |
| main:paper | 2024/2025 | Tottenham Hotspur | 38 | 62.4 | -7.9 | -16.5 | -0.0852 | 20 | €832.30m | 0.639 | -300.7 |
| main:paper | 2025/2026 | Tottenham Hotspur | 41 | 59.9 | -11.3 | -7.6 | -0.1223 | 20 | €804.90m | 0.526 | -381.9 |
| main:paper | 2018/2019 | Wolverhampton Wanderers | 57 | 40.8 | 13.9 | 2.3 | 0.1495 | 1 | €127.80m | 2.196 | 152.8 |
| with2021:FINAL4 | 2022/2023 | Chelsea | 44 | 64.0 | -8.0 | -12.0 | -0.0978 | 20 | €729.70m | 0.615 | -280.9 |
| with2021:FINAL4 | 2023/2024 | Chelsea | 63 | 67.8 | -7.7 | 2.9 | -0.0933 | 20 | €972.20m | 0.629 | -361.0 |
| with2021:FINAL4 | 2024/2025 | Nottingham Forest | 65 | 49.2 | 6.6 | 9.2 | 0.0800 | 1 | €390.35m | 1.488 | 190.6 |
| with2021:FINAL4 | 2024/2025 | Tottenham Hotspur | 38 | 61.7 | -7.0 | -16.7 | -0.0852 | 20 | €832.30m | 0.655 | -287.5 |
| with2021:FINAL4 | 2025/2026 | Tottenham Hotspur | 41 | 59.4 | -10.0 | -8.4 | -0.1223 | 20 | €804.90m | 0.544 | -366.7 |
| with2021:paper | 2022/2023 | Chelsea | 44 | 64.7 | -9.0 | -11.7 | -0.0978 | 20 | €729.70m | 0.599 | -292.8 |
| with2021:paper | 2023/2024 | Chelsea | 63 | 68.7 | -8.6 | 2.9 | -0.0933 | 20 | €972.20m | 0.613 | -376.5 |
| with2021:paper | 2024/2025 | Nottingham Forest | 65 | 49.1 | 7.3 | 8.6 | 0.0800 | 1 | €390.35m | 1.521 | 203.5 |
| with2021:paper | 2024/2025 | Tottenham Hotspur | 38 | 62.3 | -7.8 | -16.5 | -0.0852 | 20 | €832.30m | 0.639 | -300.2 |
| with2021:paper | 2025/2026 | Tottenham Hotspur | 41 | 59.9 | -11.2 | -7.7 | -0.1223 | 20 | €804.90m | 0.526 | -381.3 |
| with2021:paper | 2018/2019 | Wolverhampton Wanderers | 57 | 41.0 | 13.7 | 2.3 | 0.1495 | 1 | €127.80m | 2.192 | 152.3 |


## Robustness rows in one place

| analysis | main (SET7) | + 2020/21 | ex-window (Omicron, restart) |
|---|---|---|---|
| F: NETavailability coefficient, points ~ value + NETav, season FE, HC3 (pooled) | 92.8 ± 20.1 (n 140, ΔR² 0.068) | 91.7 ± 18.6 (n 160, ΔR² 0.065) | 91.8 ± 19.6 (n 140, ΔR² 0.070) |
| F without Spurs and Chelsea | 80.9 ± 23.1 (p 0.0006, n 126) | 81.5 ± 21.0 (p 0.0002, n 144) | 80.0 ± 22.3 (p 0.0005, n 126) |
| G model (b): H2 points ~ value + H1 absence per match (pooled) | −0.024 ± 0.008 (p 0.002, ΔR² 0.046) | −0.023 ± 0.007 (p 0.001, ΔR² 0.040) | −0.020 ± 0.008 (p 0.010, ΔR² 0.026) |
| G model (c) (+ H1 points) | −0.015 ± 0.007 (p 0.045) | −0.013 ± 0.007 (p 0.050) | −0.011 ± 0.007 (p 0.135) |
| H: ICC all clubs [bootstrap 95%] | 0.121 [0.000, 0.271] | 0.102 [0.000, 0.234] | n/a (season totals) |
| H: lag-1 slope (pairs) | 0.415 ± 0.099 (n 85) | 0.341 ± 0.084 (n 119) | n/a (season totals) |
| H2: share of null panels ≥ observed ICC-all / permutation / split-half | 0.697 / 0.229 / 0.172 | 0.653 / 0.285 / 0.225 | n/a (season totals) |
| H3: Tottenham-depth run share; stickiness diff (p) | 0.493; +0.21 (0.52) | 0.490; +0.35 (0.10) | n/a (season totals) |
| H3b: sum-rule Tottenham-depth share | 0.425 | 0.405 | n/a (season totals) |
| L: headline shares T1–T4 (largest of c·N, c·Q, m·N, m·Q) | 0.67 / 0.42 / 0.49 / 0.28 — NOT SHOWN RARE | 0.64 / 0.40 / 0.49 / 0.27 — NOT SHOWN RARE | n/a (season totals) |
| N: 95% upper bound on a lasting edge (ICC-all) | 2.30 pp | 2.23 pp | n/a (season totals) |
| Decomposition β_c (pts per unit c), FINAL 4 / all seasons of the variant | 82.1 ± 27.3 / 92.8 ± 20.1 | 82.1 ± 27.3 / 91.7 ± 18.6 | 82.1 ± 27.3 / 91.8 ± 19.6 |

## How each step treats the two-year gap 2019/20 → 2021/22

| script | uses | gap |
|---|---|---|
| F (regressions) | season totals; season FE | no lag structure; unaffected |
| G (half_season_inputs / half_season_models) | within-season halves | no cross-season lag; unaffected |
| H (persistence) | lag-1 pairs via s_idx, parity split via s_idx % 2 | s_idx by start year: 2019/20 and 2021/22 are NOT a pair; odd/even split = odd/even start year. Its op1 check (c) alone lists 2019/20→2021/22 as an adjacent pair (a self-check table, not used by any statistic) |
| H2 (carryover_null) | lag-1 ρ from pairs; AR(1) null over S seasons | pairs exclude the gap; the simulated AR(1) keeps an empty 2020/21 column, so 2019/20 → 2021/22 correlates at ρ² |
| H3 / H3b (asymmetry / two_season_runs) | H2's pairs and null | as H2; a two-season run cannot span 2019/20–2021/22 |
| L (extremity) | own pairs and AR(1) panels | s_idx by start year; empty 2020/21 column in the panels; season gaps computed over observed seasons only |
| N (power) | H2's pairs/null | as H2 |
| decomposition | season totals | unaffected |

Charts: `chart_netav_by_rank_per_season_SET7.png`, `chart_league_mean_trend_SET7.png`. League-mean NETavailability by season: 18/19 0.7863, 19/20 0.7983, 20/21 0.7922, 21/22 0.8035, 22/23 0.8141, 23/24 0.7645, 24/25 0.8050, 25/26 0.8138.


SET7 done in 91 s wall (700 s of script time). Unexpected failures: 0.
