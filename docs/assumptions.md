# Assumptions and defaults

Every choice the study relies on, each with a one-line rationale. The plan is in `docs/plan.md`; the data checks
are in `outputs/data_report.md`.

## Data

| Decision | Rationale |
|---|---|
| Seven IMF extracts (about 3.9 MB), downloaded by `python run.py --fetch` into the git-ignored `data/raw/`, with a manifest of URL, date, size and SHA-256 | Public data rebuilt from the source rather than redistributed. The outputs in this repository come from the downloads of 2026-10-16 (six extracts) and 2026-10-19 (the WEO). |
| Real GDP growth and inflation from the World Economic Outlook (April 2026), not from the quarterly series | The annual growth implied by the IMF's quarterly "constant prices" GDP disagrees with the WEO for several sample countries (Belarus by 8.2 points a year, Armenia by 3.5). Quarterly CPI inflation agrees with the WEO and is kept as a check. |
| Emerging or developing = not among the 43 advanced economies of the April 2026 World Economic Outlook | A fixed, published list. Bulgaria counts as advanced (euro area since January 2026). |
| One row per country and year; bank ratios at Q4 | Income-based ratios are reported year to date in most countries (111 of 119), so only Q4 covers a full year everywhere. |
| The policy rate and the exchange rate are averaged over complete calendar years; growth rates in log points x 100 | Matches the annual bank ratios; logs keep large crisis moves symmetric. |
| Main sample: at least 10 years in 2008-2025 with every core variable jointly observed (38 countries); strict sample: 15 years (27) | Enough years per country for within-country variation; complete years so every row has every core variable. |
| Country-years with inflation above 40% a year leave the main analysis (11 of 582); a robustness check keeps them | A few points at several times every other year's inflation would decide the fit; Argentina's accounts change basis in 2020. |
| Average total assets: a quarter-on-quarter move beyond 40 log points is a reporting break, and asset growth is left missing that year | Catches Armenia 2023 and Argentina 2020 (its switch to inflation-adjusted accounting); Turkey's 32-point jump after the 2021 lira crash is plausibly genuine and stays. |
| Ratios are not re-derived from components | The net-income component did not come through in the extracts, and Q4 ratios need no rebuilding. |
| Robustness check 6 (a short-term market rate where the policy rate is missing) not run | It needs a series that was not downloaded. |

## Simulation check (plan, section 6)

| Decision | Rationale |
|---|---|
| The real rows and macro data, simulated outcomes with no true effects, 1,000 panels per setting (`--quick` 200); wild bootstrap on the first 200, with 199 draws each | Tests every error-bar method on this panel's own shape before any estimate. Every finding uses real data only. |
| Noise: each country's own scale (from its residuals after country and year effects) times a unit-variance mix of its own AR(1) shocks and a shared AR(1) shock with a random country loading; Student-t or normal shocks | Reproduces the four features measured in the real residuals: unequal noise across countries, persistence, co-movement that year effects cannot remove, and fat tails. |
| Calibration: persistence, shared share and tails picked on grids, one at a time, to match the real year-to-year correlation, mean absolute cross-country correlation and kurtosis; then the overall size to match the variance | Indirect inference: the simulated residuals go through the same country and year effects as the real ones. The macro variables are not used. |
| Stress settings: persistence 0.9, shared share 0.5, t(3) shocks | Shows whether the chosen method survives noise worse than measured. |
| Detectable effects: the smallest shift of the estimates rejected in 80% of panels at 5% | Exact for this design: the regressors are fixed and the model linear, so shifting the truth shifts the estimates and leaves the standard errors unchanged. |
| Armenia alone: equal-weighted cosine variance with nu = floor(0.4 T^(2/3)), times T / (T - k), t(nu) critical values; noise sized like Armenia's own outcome around its mean, with the panel's persistence | The small-sample factor lifts the worst coverage from 0.74 to about 0.80 (policy rate, 13-15 years); Armenia's own variation has no year effects to remove. |

## Estimation and reading

| Decision | Rationale |
|---|---|
| Primary error bars: clustered by country (debiased, with the G/(G - 1) group correction), t(G - 1) critical values | Kept by the plan's rule after the simulation check (worst coverage 0.925). |
| Wild cluster restricted bootstrap p-values (Webb weights, 9,999 draws, by country); Holm adjustment over the 16 main coefficients | Plan, section 6. |
| Every main and dollar-lending regression is re-run in linearmodels during estimation and must agree to 1e-6 | Guards the fast estimator on the real data, not only in tests. |
| Reading rule (plan, section 9): "no large effect" when the 95% interval rules out a typical swing moving the outcome by more than 0.25 within-country SDs; relationships labelled small or large against the same band | Fixed in `config.yaml` before any estimate was computed. A typical swing is the macro variable's SD after country and year effects. |
| Mechanical links (revaluation of foreign-currency assets; inflation as the deflator of asset growth) quantified from sample means, not estimated | Back-of-envelope checks of how much of a relationship measurement alone could produce. |
