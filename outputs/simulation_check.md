# Simulation check: are the error bars honest for this panel?

*Simulated bank outcomes on the real panel.* The countries, years, gaps and IMF macro data are real; the bank
outcomes are made up, with no true effects, and noise built to behave like the real outcomes' noise. Run before
any estimate, as the plan requires (`docs/plan.md`, section 6). 1000 simulated panels per
setting; the wild bootstrap uses the first 200 with 199 draws each.

## The noise

For each outcome, the real values are stripped of country and year effects (no macro variable is used), and the
simulated noise is tuned until it matches what is left: each country keeps its own noise level, and three
settings are chosen to match the statistics below. "Persistence" is the year-to-year correlation of a country's
shocks; "shared share" is the part of the noise that comes from a shock some countries share in a year, with
country-specific exposure that the year effects cannot remove; "tails" sets how often extreme years occur.

| outcome | year-to-year corr. (real / sim.) | cross-country |corr.| (real / sim.) | tail weight (real / sim.) | persistence | shared share | tails (t df) |
|---|---|---|---|---|---|---|
| ROA | 0.17 / 0.20 | 0.39 / 0.40 | 4.2 / 3.5 | 0.30 | 0.55 | 3 |
| Non-interest income share | 0.47 / 0.47 | 0.36 / 0.37 | 2.9 / 3.0 | 0.60 | 0.40 | 3 |
| Capital ratio | 0.51 / 0.51 | 0.38 / 0.40 | 2.8 / 2.8 | 0.65 | 0.45 | 3 |
| Real asset growth | 0.25 / 0.24 | 0.27 / 0.28 | 3.6 / 3.4 | 0.35 | 0.10 | 3 |

## Coverage with this noise

Share of simulated panels whose 95% interval contains the true value (honest = 0.95; with 1000 panels, about
+/- 0.014 is simulation noise; +/- 0.031 for the wild
bootstrap).

**Main regressions (question 1) and dollar lending (question 2, the last line of each outcome):**

| outcome | coefficient | unadjusted | country cluster | wild bootstrap | two-way cluster | Driscoll-Kraay |
|---|---|---|---|---|---|---|
| ROA | GDP growth | 0.921 | 0.964 | 0.940 | 0.957 | 0.923 |
| ROA | Inflation | 0.879 | 0.948 | 0.945 | 0.946 | 0.929 |
| ROA | Policy rate | 0.884 | 0.952 | 0.945 | 0.967 | 0.896 |
| ROA | Dollar exchange rate | 0.831 | 0.937 | 0.960 | 0.941 | 0.914 |
| ROA | FX change x FX-loan share | 0.827 | 0.925 | 0.920 | 0.923 | 0.922 |
| Non-interest income share | GDP growth | 0.900 | 0.940 | 0.925 | 0.937 | 0.875 |
| Non-interest income share | Inflation | 0.853 | 0.956 | 0.975 | 0.954 | 0.877 |
| Non-interest income share | Policy rate | 0.811 | 0.952 | 0.970 | 0.952 | 0.848 |
| Non-interest income share | Dollar exchange rate | 0.900 | 0.949 | 0.950 | 0.948 | 0.906 |
| Non-interest income share | FX change x FX-loan share | 0.922 | 0.953 | 0.960 | 0.933 | 0.898 |
| Capital ratio | GDP growth | 0.853 | 0.945 | 0.935 | 0.944 | 0.893 |
| Capital ratio | Inflation | 0.768 | 0.954 | 0.955 | 0.958 | 0.843 |
| Capital ratio | Policy rate | 0.797 | 0.957 | 0.925 | 0.961 | 0.856 |
| Capital ratio | Dollar exchange rate | 0.866 | 0.946 | 0.940 | 0.946 | 0.918 |
| Capital ratio | FX change x FX-loan share | 0.894 | 0.928 | 0.925 | 0.929 | 0.896 |
| Real asset growth | GDP growth | 0.924 | 0.957 | 0.945 | 0.951 | 0.906 |
| Real asset growth | Inflation | 0.862 | 0.939 | 0.950 | 0.938 | 0.878 |
| Real asset growth | Policy rate | 0.857 | 0.957 | 0.955 | 0.951 | 0.858 |
| Real asset growth | Dollar exchange rate | 0.878 | 0.942 | 0.945 | 0.930 | 0.907 |
| Real asset growth | FX change x FX-loan share | 0.902 | 0.932 | 0.915 | 0.921 | 0.900 |

**Effects over time** (local projections; worst and mean over the 16 outcome-variable pairs at each horizon):

| horizon | unadjusted (worst / mean) | country cluster (worst / mean) | two-way cluster (worst / mean) | Driscoll-Kraay (worst / mean) |
|---|---|---|---|---|
| LP h=0 | 0.829 / 0.905 | 0.940 / 0.949 | 0.924 / 0.941 | 0.924 / 0.930 |
| LP h=1 | 0.812 / 0.888 | 0.927 / 0.945 | 0.920 / 0.941 | 0.908 / 0.924 |
| LP h=2 | 0.843 / 0.895 | 0.935 / 0.947 | 0.929 / 0.942 | 0.904 / 0.927 |

**With one feature of the noise pushed harder** (worst coverage over the 20 coefficients of questions 1 and 2):

| noise | unadjusted | country cluster | wild bootstrap | two-way cluster | Driscoll-Kraay |
|---|---|---|---|---|---|
| calibrated | 0.768 | 0.925 | 0.915 | 0.921 | 0.843 |
| more persistent | 0.718 | 0.911 | 0.915 | 0.910 | 0.782 |
| more shared shocks | 0.794 | 0.923 | 0.915 | 0.904 | 0.830 |
| fatter tails | 0.795 | 0.916 | 0.915 | 0.917 | 0.846 |

## Decision (fixed in the plan before this check)

- **main and dollar-lending:** worst coverage of country clustering 0.925; it stays primary.
- **local projections:** worst coverage of country clustering 0.927; it stays primary.

## What the panel can detect

The smallest effect found 80% of the time at the 5% level with the primary method, per 1-point change in the
macro variable, against Armenia on its own (its years from 2005, equal-weighted cosine intervals). "Typical
swing" is the standard deviation of the macro variable once country and year effects are removed. The
dollar-lending line is the extra effect of a 1-point depreciation where 10 points more of loans are in foreign
currency; Armenia alone has no counterpart. Armenia's own intervals rest on 13-20
years and 2 degrees of freedom; even with the small-sample correction they cover
0.80 to 0.97 (worst: Policy rate for
Real asset growth, 13 years).

| outcome | coefficient | panel | typical swing | Armenia alone | times larger |
|---|---|---|---|---|---|
| ROA | GDP growth | 0.047 | 2.61 | 0.311 | 6.61 |
| ROA | Inflation | 0.0659 | 2.91 | 0.669 | 10.2 |
| ROA | Policy rate | 0.0586 | 3.02 | 1.1 | 18.8 |
| ROA | Dollar exchange rate | 0.0187 | 7.77 | 0.231 | 12.4 |
| ROA | FX change x 10 points more FX lending | 0.00901 |  |  |  |
| Non-interest income share | GDP growth | 0.285 | 2.61 | 1.47 | 5.16 |
| Non-interest income share | Inflation | 0.425 | 2.91 | 3.81 | 8.98 |
| Non-interest income share | Policy rate | 0.424 | 3.02 | 6.49 | 15.3 |
| Non-interest income share | Dollar exchange rate | 0.104 | 7.77 | 1.11 | 10.7 |
| Non-interest income share | FX change x 10 points more FX lending | 0.0509 |  |  |  |
| Capital ratio | GDP growth | 0.137 | 2.53 | 0.518 | 3.77 |
| Capital ratio | Inflation | 0.198 | 2.92 | 1.4 | 7.08 |
| Capital ratio | Policy rate | 0.184 | 3.02 | 1.2 | 6.51 |
| Capital ratio | Dollar exchange rate | 0.0479 | 7.77 | 0.35 | 7.31 |
| Capital ratio | FX change x 10 points more FX lending | 0.0208 |  |  |  |
| Real asset growth | GDP growth | 0.313 | 2.49 | 1.75 | 5.6 |
| Real asset growth | Inflation | 0.466 | 2.88 | 4.15 | 8.91 |
| Real asset growth | Policy rate | 0.42 | 2.99 | 4.47 | 10.6 |
| Real asset growth | Dollar exchange rate | 0.12 | 7.7 | 1.31 | 10.9 |
| Real asset growth | FX change x 10 points more FX lending | 0.053 |  |  |  |
