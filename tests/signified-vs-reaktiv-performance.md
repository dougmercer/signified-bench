(signified-bench) ➜  signified-bench git:(main) ✗ uv run  signified-bench --table --suite compare
................                                                                                                                  [100%]
=========================================================== warnings summary ============================================================
tests/test_compare_benchmarks.py: 192 warnings
  /Users/dougmercer/Documents/dev/signified-bench/.venv/lib/python3.14/site-packages/reaktiv/effect.py:155: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    self._is_async = asyncio.iscoroutinefunction(func)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html

------------------------------------------------------------------------------------------------------------------- benchmark: 16 tests --------------------------------------------------------------------------------------------------------------------
Name (time in ms)                                                                    Min                   Max                  Mean             StdDev                Median                IQR            Outliers       OPS            Rounds  Iterations
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_compare_steady_state_scenarios[signal_read_write-reaktiv]                    6.5814 (1.0)          7.1079 (1.0)          6.7428 (1.0)       0.1188 (1.0)          6.7017 (1.0)       0.1580 (1.96)         45;3  148.3070 (1.0)         147           1
test_compare_steady_state_scenarios[signal_read_write-signified]                  6.8934 (1.05)        16.3691 (2.30)         7.1310 (1.06)      0.8564 (7.21)         7.0062 (1.05)      0.0805 (1.0)          4;14  140.2322 (0.95)        145           1
test_compare_steady_state_scenarios[shared_dependency_branches-reaktiv]          27.0750 (4.11)        28.5240 (4.01)        27.5203 (4.08)      0.3913 (3.29)        27.3506 (4.08)      0.6149 (7.64)         11;0   36.3368 (0.25)         36           1
test_compare_steady_state_scenarios[multi_input_computed-reaktiv]                36.2188 (5.50)        38.3742 (5.40)        36.6869 (5.44)      0.5768 (4.85)        36.4374 (5.44)      0.5047 (6.27)          4;2   27.2577 (0.18)         28           1
test_compare_steady_state_scenarios[multi_input_computed-signified]              45.8678 (6.97)        47.8711 (6.73)        46.3863 (6.88)      0.6375 (5.37)        46.1680 (6.89)      0.5044 (6.27)          5;5   21.5581 (0.15)         22           1
test_compare_steady_state_scenarios[shared_clock_reads-reaktiv]                  48.3668 (7.35)        49.5768 (6.97)        48.6222 (7.21)      0.2604 (2.19)        48.5577 (7.25)      0.2081 (2.59)          2;1   20.5667 (0.14)         21           1
test_compare_steady_state_scenarios[shared_dependency_branches-signified]        48.6730 (7.40)        50.5417 (7.11)        49.3981 (7.33)      0.6300 (5.30)        49.0494 (7.32)      0.9939 (12.35)         6;0   20.2437 (0.14)         21           1
test_compare_steady_state_scenarios[shared_clock_reads-signified]                96.5425 (14.67)      100.2048 (14.10)       97.6262 (14.48)     1.1061 (9.31)        97.3048 (14.52)     0.6589 (8.19)          2;2   10.2432 (0.07)         12           1
test_compare_steady_state_scenarios[deep_chain_updates-reaktiv]                 130.6958 (19.86)      135.6547 (19.09)      132.0643 (19.59)     1.4445 (12.16)      131.7363 (19.66)     1.0675 (13.26)         2;2    7.5721 (0.05)         12           1
test_compare_steady_state_scenarios[fanout_updates-reaktiv]                     232.6199 (35.35)      238.0495 (33.49)      234.7949 (34.82)     1.6691 (14.05)      234.3317 (34.97)     1.7491 (21.73)         3;1    4.2590 (0.03)         12           1
test_compare_steady_state_scenarios[diamond_updates-reaktiv]                    254.0111 (38.60)      263.1013 (37.02)      256.1803 (37.99)     2.4161 (20.33)      255.7182 (38.16)     1.6862 (20.95)         1;1    3.9035 (0.03)         12           1
test_compare_steady_state_scenarios[deep_chain_updates-signified]               308.8589 (46.93)      317.6789 (44.69)      313.2297 (46.45)     3.2023 (26.95)      312.8695 (46.69)     5.6901 (70.68)         5;0    3.1925 (0.02)         12           1
test_compare_steady_state_scenarios[fanout_updates-signified]                   483.2297 (73.42)      502.0097 (70.63)      490.0295 (72.67)     5.8342 (49.10)      489.5755 (73.05)     8.2034 (101.91)        4;0    2.0407 (0.01)         12           1
test_compare_steady_state_scenarios[diamond_updates-signified]                  520.9583 (79.16)      533.4911 (75.06)      526.0824 (78.02)     3.6290 (30.54)      525.3992 (78.40)     3.8502 (47.83)         4;0    1.9008 (0.01)         12           1
test_compare_steady_state_scenarios[effect_fanout_updates-signified]          1,188.6085 (180.60)   1,217.9482 (171.35)   1,205.2471 (178.75)    9.0367 (76.06)    1,208.2946 (180.30)   14.3211 (177.90)        3;0    0.8297 (0.01)         12           1
test_compare_steady_state_scenarios[effect_fanout_updates-reaktiv]            1,490.0850 (226.41)   1,549.2433 (217.96)   1,518.3243 (225.18)   20.3914 (171.62)   1,515.3242 (226.11)   34.3018 (426.11)        5;0    0.6586 (0.00)         12           1
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Legend:
  Outliers: 1 Standard Deviation from Mean; 1.5 IQR (InterQuartile Range) from 1st Quartile and 3rd Quartile.
  OPS: Operations Per Second, computed as 1 / Mean
16 passed, 6 deselected, 192 warnings in 85.57s (0:01:25)
