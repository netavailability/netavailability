### Calibration re-measure, SET7, on `run_on`

Script `calibrate.py` (sha256 `6411d46972d09b70…`); compute `compute.py` as recorded in `runs.csv`; run folder `<run>/run_on` (suffix _on). Seasons 2018/2019, 2019/2020, 2021/2022, 2022/2023, 2023/2024, 2024/2025, 2025/2026; chronological fit 2018/2019, 2019/2020, 2021/2022 → test 2022/2023, 2023/2024, 2024/2025, 2025/2026. Input sets: late = 18/19/21/22/23/24/25. Detail files in `<run>/calibration/SET7`. This stage measures only: no constant is changed.

**1. Instrumented pass**: club tables identical to the run's in 7/7 seasons (the hook changed nothing); every file of the season folders compared: 161/161 identical.

**2. Populations** (movers = player-seasons with a carried slot in a charged call; fills = imports with a fill slot):

| season | charged_calls | mover_population | fill_non_keepers | fill_keepers |
|---|---|---|---|---|
| 2018/2019 | 19858 | 29 | 84 | 8 |
| 2019/2020 | 20535 | 34 | 96 | 8 |
| 2021/2022 | 22627 | 33 | 89 | 13 |
| 2022/2023 | 23158 | 57 | 137 | 11 |
| 2023/2024 | 24352 | 54 | 113 | 16 |
| 2024/2025 | 22832 | 60 | 107 | 6 |
| 2025/2026 | 23057 | 59 | 109 | 15 |

**3. Mover rows**: 326 population rows, 312 measured (18/19 27, 19/20 32, 21/22 33, 22/23 55, 23/24 51, 24/25 57, 25/26 57); not measured: 4 with no carried slot at the first naming, 10 not named for the club in the season.

**4. Mover constant** (adjusted = carried − delta × (from_seed − to_seed); b = OLS slope of gap on pot delta, delta = −b):

| block | seasons | model | n | delta | SE | p | grid | intercept | intercept_SE |
|---|---|---|---|---|---|---|---|---|---|
| fit | 18/19/21 | through zero | 92 | 0.0912 | 0.0175 | <0.0001 | 0.10 |  |  |
| fit | 18/19/21 | with intercept | 92 | 0.0911 | 0.0177 | <0.0001 | 0.10 | 0.0009 | 0.0367 |
| test | 22/23/24/25 | through zero | 220 | 0.0983 | 0.0118 | <0.0001 | 0.10 |  |  |
| test | 22/23/24/25 | with intercept | 220 | 0.1012 | 0.0116 | <0.0001 | 0.10 | -0.0677 | 0.0205 |
| all | 18/19/21/22/23/24/25 | through zero | 312 | 0.0958 | 0.0097 | <0.0001 | 0.10 |  |  |
| all | 18/19/21/22/23/24/25 | with intercept | 312 | 0.0978 | 0.0097 | <0.0001 | 0.10 | -0.0475 | 0.0181 |

Per season (through zero): 18/19 0.073 ± 0.039 (n 27); 19/20 0.107 ± 0.026 (n 32); 21/22 0.090 ± 0.029 (n 33); 22/23 0.109 ± 0.020 (n 55); 23/24 0.081 ± 0.026 (n 51); 24/25 0.110 ± 0.025 (n 57); 25/26 0.093 ± 0.025 (n 57)

Chronological fit/test (residual = test gap − fitted line; residual slope 0 = the fit's delta holds in the test):

| model | fit_n | fit_slope_b | fit_SE | fit_delta | fit_intercept | fit_intercept_SE | test_n | test_own_delta | test_own_SE | resid_mean | resid_mean_SE | resid_slope | resid_slope_SE | resid_slope_p |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| through zero | 92 | -0.0912 | 0.0175 | 0.0912 |  |  | 220 | 0.0983 | 0.0118 | -0.0664 | 0.0205 | -0.0072 | 0.0118 | 0.5446 |
| with intercept | 92 | -0.0911 | 0.0177 | 0.0911 | 0.0009 | 0.0367 | 220 | 0.1012 | 0.0116 | -0.0673 | 0.0205 | -0.0100 | 0.0116 | 0.3870 |

Residual slope with a fixed delta applied (through zero; 0 = nothing left):

| delta_applied | seasons | n | resid_mean | resid_mean_SE | resid_slope | SE | p |
|---|---|---|---|---|---|---|---|
| 0.05 | all | 312 | -0.0403 | 0.0187 | -0.0458 | 0.0097 | <0.0001 |
| 0.05 | fit | 92 | 0.0091 | 0.0374 | -0.0412 | 0.0175 | 0.0209 |
| 0.05 | test | 220 | -0.0609 | 0.0213 | -0.0483 | 0.0118 | <0.0001 |
| 0.10 | all | 312 | -0.0479 | 0.0180 | 0.0042 | 0.0097 | 0.6633 |
| 0.10 | fit | 92 | -0.0008 | 0.0363 | 0.0088 | 0.0175 | 0.6165 |
| 0.10 | test | 220 | -0.0675 | 0.0204 | 0.0017 | 0.0118 | 0.8884 |
| 0.15 | all | 312 | -0.0554 | 0.0188 | 0.0542 | 0.0097 | <0.0001 |
| 0.15 | fit | 92 | -0.0107 | 0.0385 | 0.0588 | 0.0175 | 0.0012 |
| 0.15 | test | 220 | -0.0741 | 0.0213 | 0.0517 | 0.0118 | <0.0001 |

**Sideways (same-pot, pot delta = 0) cell** — mean gap = realised − carried; the rule in force adds -0.15 to carried:

| block | n | mean_carried | mean_realised | mean_gap | SE | t | p | grid |
|---|---|---|---|---|---|---|---|---|
| fit | 11 | 0.8092 | 0.5457 | -0.2634 | 0.0847 | -3.11 | 0.0111 | -0.25 |
| test | 50 | 0.5556 | 0.4064 | -0.1492 | 0.0394 | -3.79 | 0.0004 | -0.15 |
| all | 61 | 0.6014 | 0.4315 | -0.1698 | 0.0358 | -4.74 | <0.0001 | -0.15 |

Chronological: fit-block mean gap -0.2634 ± 0.0847 (n 11, grid -0.25) applied to the test block: test mean gap -0.1492 ± 0.0394 (n 50); difference test − fit +0.1142, Welch p = 0.2408. With -0.15 applied the test-block residual is +0.0008 ± 0.0394 (one-sample t p = 0.9845).

**5. Tier fills, keepers excluded** (fill population; realised = first 12 squads for the club from the arrival in force; 720 measured non-keeper player-seasons, 15 never named after the arrival, keepers 77):

| tier | spec_fill | n | mean | SE | median | grid | fit_n | fit_mean | fit_SE | fit_grid | test_n | test_mean | test_SE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tier1 | 0.50 | 416 | 0.518 | 0.014 | 0.528 | 0.50 | 141 | 0.534 | 0.024 | 0.55 | 275 | 0.510 | 0.018 |
| tier2 | 0.35 | 86 | 0.334 | 0.030 | 0.286 | 0.35 | 41 | 0.350 | 0.041 | 0.35 | 45 | 0.320 | 0.044 |
| tier3 | 0.25 | 48 | 0.255 | 0.040 | 0.142 | 0.25 | 10 | 0.377 | 0.117 | 0.40 | 38 | 0.223 | 0.040 |
| Championship origin | 0.45 | 92 | 0.460 | 0.031 | 0.451 | 0.45 | 40 | 0.464 | 0.046 | 0.45 | 52 | 0.458 | 0.042 |
| PL origin | 0.45 | 50 | 0.450 | 0.042 | 0.411 | 0.45 | 19 | 0.416 | 0.068 | 0.40 | 31 | 0.471 | 0.054 |
| data club in neither league that season | 0.45 | 5 | 0.295 | 0.125 | 0.376 | 0.30 | 1 | 0.652 |  | 0.65 | 4 | 0.206 | 0.112 |
| every data-club origin together | 0.45 | 147 | 0.451 | 0.024 | 0.429 | 0.45 | 60 | 0.452 | 0.037 | 0.45 | 87 | 0.451 | 0.032 |

**6. L composite** (bin weights from the run's absence spells in the set's seasons: 10627 spells, 1353572 minutes; weights H1 0.132, H4 0.248, H6 0.124, H8 0.081, H10 0.068, H12 0.056, H14 0.037, H16 0.046, H18 0.208). Composite MAE by L (pooled): best L fit = **15**, test = **13**, all = **13**; at L = 12: fit 0.1873, test 0.1831, all 0.1850; at the best L: 0.1870 / 0.1831 / 0.1849.

| L | fit | test | all |
|---|---|---|---|
| 8 | 0.18996 | 0.18476 | 0.18706 |
| 9 | 0.18903 | 0.18410 | 0.18629 |
| 10 | 0.18832 | 0.18360 | 0.18570 |
| 11 | 0.18768 | 0.18333 | 0.18527 |
| 12 | 0.18726 | 0.18313 | 0.18498 |
| 13 | 0.18712 | 0.18311 | 0.18491 |
| 14 | 0.18706 | 0.18319 | 0.18492 |
| 15 | 0.18704 | 0.18333 | 0.18500 |
| 16 | 0.18706 | 0.18351 | 0.18511 |
| 17 | 0.18707 | 0.18374 | 0.18524 |
| 18 | 0.18712 | 0.18412 | 0.18547 |

Paired season tests of the composite (d = composite(L_a) − composite(L_b); positive = L_b better; scipy ttest_rel and wilcoxon, two-sided):

| pair | seasons | n | mean_d | SD_d | t | p_t | p_wilcoxon |
|---|---|---|---|---|---|---|---|
| L12 − L13 | all | 7 | 0.00007 | 0.00027 | 0.697 | 0.512 | 0.578 |
| L12 − L13 | fit | 3 | 0.00014 | 0.00018 | 1.302 | 0.323 | 0.500 |
| L12 − L13 | test | 4 | 0.00002 | 0.00035 | 0.133 | 0.903 | 1.000 |
| L12 − L14 | all | 7 | 0.00005 | 0.00052 | 0.276 | 0.792 | 0.688 |
| L12 − L14 | fit | 3 | 0.00019 | 0.00036 | 0.935 | 0.448 | 0.500 |
| L12 − L14 | test | 4 | -0.00005 | 0.00065 | -0.153 | 0.888 | 1.000 |
| L13 − L14 | all | 7 | -0.00002 | 0.00025 | -0.186 | 0.858 | 0.812 |
| L13 − L14 | fit | 3 | 0.00006 | 0.00018 | 0.550 | 0.638 | 0.750 |
| L13 − L14 | test | 4 | -0.00007 | 0.00031 | -0.469 | 0.671 | 0.625 |
| L12 − L11 | all | 7 | -0.00030 | 0.00026 | -3.071 | 0.022 | 0.031 |
| L12 − L11 | fit | 3 | -0.00042 | 0.00026 | -2.874 | 0.103 | 0.250 |
| L12 − L11 | test | 4 | -0.00021 | 0.00026 | -1.641 | 0.199 | 0.250 |
| L12 − L10 | all | 7 | -0.00074 | 0.00054 | -3.633 | 0.011 | 0.031 |
| L12 − L10 | fit | 3 | -0.00106 | 0.00043 | -4.277 | 0.051 | 0.250 |
| L12 − L10 | test | 4 | -0.00049 | 0.00052 | -1.899 | 0.154 | 0.250 |
| L12 − L15 | all | 7 | -0.00002 | 0.00073 | -0.057 | 0.956 | 1.000 |
| L12 − L15 | fit | 3 | 0.00021 | 0.00052 | 0.697 | 0.558 | 0.500 |
| L12 − L15 | test | 4 | -0.00019 | 0.00090 | -0.415 | 0.706 | 0.625 |

**L = 12 within the tie**: no L tested against 12 (13, 14, 11, 10, 15) is better than it at paired-t p < 0.05 in any block. By the two-sided rule (no L12-vs-L13/L14 paired t-test below 0.05 in either direction): within the tie.

**Calibration table** — one row per constant × block; current = the value in force in the run's commands; se analytic (OLS slope SE, or SD/√n of a mean); nearest_005 = measured rounded to the nearest 0.05; for L: measured = best L, n = seasons, p = paired t of L12 against the other L:

| constant | block | current | measured | se | n | nearest_005 | abs_diff_in_se | p_L12_vs_L13 | p_L12_vs_L14 | p_L12_vs_L11 | p_L12_vs_L10 | p_L12_vs_best | L12_within_tie |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| mover | fit | 0.10 | 0.0912 | 0.0175 | 92 | 0.10 | 0.50 |  |  |  |  |  |  |
| mover | test | 0.10 | 0.0983 | 0.0118 | 220 | 0.10 | 0.14 |  |  |  |  |  |  |
| mover | all | 0.10 | 0.0958 | 0.0097 | 312 | 0.10 | 0.44 |  |  |  |  |  |  |
| mover_with_intercept | fit | 0.10 | 0.0911 | 0.0177 | 92 | 0.10 | 0.50 |  |  |  |  |  |  |
| mover_with_intercept | test | 0.10 | 0.1012 | 0.0116 | 220 | 0.10 | 0.10 |  |  |  |  |  |  |
| mover_with_intercept | all | 0.10 | 0.0978 | 0.0097 | 312 | 0.10 | 0.23 |  |  |  |  |  |  |
| sideways | fit | -0.15 | -0.2634 | 0.0847 | 11 | -0.25 | 1.34 |  |  |  |  |  |  |
| sideways | test | -0.15 | -0.1492 | 0.0394 | 50 | -0.15 | 0.02 |  |  |  |  |  |  |
| sideways | all | -0.15 | -0.1698 | 0.0358 | 61 | -0.15 | 0.55 |  |  |  |  |  |  |
| tier1 | fit | 0.50 | 0.5339 | 0.0244 | 141 | 0.55 | 1.39 |  |  |  |  |  |  |
| tier1 | test | 0.50 | 0.5095 | 0.0178 | 275 | 0.50 | 0.54 |  |  |  |  |  |  |
| tier1 | all | 0.50 | 0.5178 | 0.0144 | 416 | 0.50 | 1.24 |  |  |  |  |  |  |
| tier2 | fit | 0.35 | 0.3498 | 0.0413 | 41 | 0.35 | 0.00 |  |  |  |  |  |  |
| tier2 | test | 0.35 | 0.3201 | 0.0445 | 45 | 0.30 | 0.67 |  |  |  |  |  |  |
| tier2 | all | 0.35 | 0.3343 | 0.0303 | 86 | 0.35 | 0.52 |  |  |  |  |  |  |
| tier3 | fit | 0.25 | 0.3772 | 0.1174 | 10 | 0.40 | 1.08 |  |  |  |  |  |  |
| tier3 | test | 0.25 | 0.2233 | 0.0400 | 38 | 0.20 | 0.67 |  |  |  |  |  |  |
| tier3 | all | 0.25 | 0.2553 | 0.0404 | 48 | 0.25 | 0.13 |  |  |  |  |  |  |
| data_club | fit | 0.45 | 0.4516 | 0.0372 | 60 | 0.45 | 0.04 |  |  |  |  |  |  |
| data_club | test | 0.45 | 0.4510 | 0.0325 | 87 | 0.45 | 0.03 |  |  |  |  |  |  |
| data_club | all | 0.45 | 0.4512 | 0.0244 | 147 | 0.45 | 0.05 |  |  |  |  |  |  |
| data_club_PL_origin | fit | 0.45 | 0.4159 | 0.0681 | 19 | 0.40 | 0.50 |  |  |  |  |  |  |
| data_club_PL_origin | test | 0.45 | 0.4713 | 0.0544 | 31 | 0.45 | 0.39 |  |  |  |  |  |  |
| data_club_PL_origin | all | 0.45 | 0.4503 | 0.0423 | 50 | 0.45 | 0.01 |  |  |  |  |  |  |
| data_club_Championship_origin | fit | 0.45 | 0.4635 | 0.0455 | 40 | 0.45 | 0.30 |  |  |  |  |  |  |
| data_club_Championship_origin | test | 0.45 | 0.4577 | 0.0422 | 52 | 0.45 | 0.18 |  |  |  |  |  |  |
| data_club_Championship_origin | all | 0.45 | 0.4603 | 0.0308 | 92 | 0.45 | 0.33 |  |  |  |  |  |  |
| data_club_neither_league_origin | fit | 0.45 | 0.6518 |  | 1 | 0.65 |  |  |  |  |  |  |  |
| data_club_neither_league_origin | test | 0.45 | 0.2061 | 0.1124 | 4 | 0.20 | 2.17 |  |  |  |  |  |  |
| data_club_neither_league_origin | all | 0.45 | 0.2952 | 0.1246 | 5 | 0.30 | 1.24 |  |  |  |  |  |  |
| unknown | fit | 0.35 |  |  | 0 |  |  |  |  |  |  |  |  |
| unknown | test | 0.35 |  |  | 0 |  |  |  |  |  |  |  |  |
| unknown | all | 0.35 |  |  | 0 |  |  |  |  |  |  |  |  |
| L | fit | 12 | 15 |  | 3 |  |  | 0.323 | 0.448 | 0.103 | 0.051 | 0.558 | yes |
| L | test | 12 | 13 |  | 4 |  |  | 0.903 | 0.888 | 0.199 | 0.154 | 0.903 | yes |
| L | all | 12 | 13 |  | 7 |  |  | 0.512 | 0.792 | 0.022 | 0.011 | 0.512 | yes |

