# Why the asymptotic relational null fails (calibrated diagnostics)

alpha = 0.05, seeds = 20

| dataset | median unique frac | analytic FWER reject | permutation FWER reject |
| --- | ---: | ---: | ---: |
| real_tuesday | 0.406 | 75.0% | 5.0% |
| real_heldout | 0.455 | 70.0% | 5.0% |
| multivariate_t3 | 1.000 | 50.0% | 5.0% |
| zero_inflated_tied | 0.147 | 15.0% | 5.0% |

| dataset | min unique > | edges | analytic | permutation |
| --- | --- | ---: | ---: | ---: |
| real_tuesday | <25% | 1394 | 0.6% | 0.0% |
| real_tuesday | 25-50% | 1862 | 0.3% | 0.0% |
| real_tuesday | 50-75% | 265 | 0.0% | 0.0% |
| real_tuesday | >75% | 279 | 4.3% | 0.4% |
| real_heldout | <25% | 1159 | 1.3% | 0.1% |
| real_heldout | 25-50% | 1978 | 0.2% | 0.0% |
| real_heldout | 50-75% | 373 | 0.3% | 0.0% |
| real_heldout | >75% | 290 | 0.0% | 0.0% |
| multivariate_t3 | <25% | 0 | - | - |
| multivariate_t3 | 25-50% | 0 | - | - |
| multivariate_t3 | 50-75% | 0 | - | - |
| multivariate_t3 | >75% | 3800 | 0.4% | 0.0% |
| zero_inflated_tied | <25% | 3800 | 0.1% | 0.0% |
| zero_inflated_tied | 25-50% | 0 | - | - |
| zero_inflated_tied | 50-75% | 0 | - | - |
| zero_inflated_tied | >75% | 0 | - | - |
