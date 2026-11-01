Block-permutation null on temporally ordered windows (n=400, d=20, alpha=0.05, B=199, 300 trials per cell)

| pool | condition | block=1 | block=10 | block=25 | block=50 |
| --- | --- | --- | --- | --- | --- |
| gaussian | null | 3.3% | 3.3% | 3.7% | 3.3% |
| gaussian | mean_0.5 | 98.7% | 99.3% | 99.0% | 98.3% |
| multivariate_t3 | null | 3.3% | 1.7% | 4.0% | 2.7% |
| multivariate_t3 | mean_0.5 | 93.7% | 92.3% | 94.0% | 93.7% |
| real_tuesday | null | 88.7% | 69.3% | 50.0% | 41.3% |
| real_tuesday | mean_0.5 | 100.0% | 100.0% | 100.0% | 100.0% |
| nsl_kdd | null | 1.7% | 2.3% | 4.3% | 2.7% |
| nsl_kdd | mean_0.5 | 100.0% | 100.0% | 100.0% | 100.0% |

Mean |lag-k| autocorrelation of the pooled windows:

| pool | lag 1 | lag 2 | lag 3 | lag 4 | lag 5 | lag 6 | lag 7 | lag 8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gaussian | 0.021 | 0.026 | 0.028 | 0.024 | 0.028 | 0.028 | 0.022 | 0.037 |
| multivariate_t3 | 0.019 | 0.025 | 0.034 | 0.025 | 0.040 | 0.021 | 0.036 | 0.031 |
| real_tuesday | 0.172 | 0.111 | 0.133 | 0.112 | 0.064 | 0.078 | 0.053 | 0.063 |
| nsl_kdd | 0.015 | 0.020 | 0.045 | 0.017 | 0.025 | 0.038 | 0.026 | 0.026 |

Synthetic pools are i.i.d. by construction and act as the negative control: the block size must not move their rate. The real pools keep the row order of the recorded traffic, so block sizes above one are the only honest nulls there.
