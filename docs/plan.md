# Plan: written before any estimate

*Status: fixed on 2026-10-19, before any estimate was computed; then the simulation check (section 6) and the
estimation (`outputs/results.md`) ran as written.* When the plan was fixed, the data had been downloaded, built and
checked (`outputs/data_report.md`): coverage, reporting conventions, summary statistics and extreme values. No
relationship between a bank outcome and a macro variable had been looked at. Anything not listed here is reported
as exploratory. Data: public IMF series.

## 1. The question

The question, first asked of 16 Armenian banks in 2024, put to data that can answer it: **in emerging economies, how do real GDP growth,
inflation, the policy interest rate and the exchange rate against the dollar relate to the banking sector's
profitability, non-interest income, capital and growth?** A second question follows: **do currency
depreciations hurt banking systems that lend more in foreign currency more?**

The answers are conditional associations, not causal effects. Central banks set rates in response to the
economy, and banking trouble feeds back into growth. "Effect" below means "how the outcome moves with one
macro variable, holding the others and the fixed effects constant".

## 2. Data

One row per country and year, 2008-2025. Most compilers report income year to date, so a March figure covers three
months and a December figure twelve (data report). Bank ratios are therefore taken at Q4. Macro
variables are calendar-year values.

| Variable | Definition | Source |
|---|---|---|
| `roa` | Net income before tax / average total assets, % (Q4) | IMF Financial Soundness Indicators |
| `nii_share` | Non-interest income / gross income, % = 100 - interest margin share (Q4) | same |
| `car` | Regulatory capital / risk-weighted assets, % (Q4) | same |
| `asset_growth` | Real growth of average total assets: log change x 100 minus inflation (Q4); missing in years with a reporting break | same |
| `gdp_growth` | Real GDP growth, log points x 100 | IMF World Economic Outlook, April 2026 |
| `inflation` | Consumer-price inflation, annual average, log points x 100 | same; the quarterly IMF consumer price index agrees to within 1 point a year |
| `policy` | Policy rate, annual average of quarterly values, % | IMF interest rates |
| `fx_change` | Change in local currency per dollar, annual average, log points x 100; above zero = depreciation | IMF exchange rates |
| `fx_loan_share` | Foreign-currency loans / total loans, % (Q4 of the previous year) | IMF Financial Soundness Indicators |

`asset_growth` stands in for market share, the bank-level outcome of the original question, which has no
sector-level counterpart. It is the
least reliable of the four outcomes (reporting breaks) and is treated as secondary.

**Sample rule.** Emerging or developing (IMF WEO, April 2026) and at least 10 years in which every outcome
except `asset_growth` and every macro variable is observed: **38 countries** and 582 country-years. The stricter
sample needs 15 or more years: 27 countries.

**Very high inflation.** Country-years with inflation above 40% a year are left out of the main analysis:
11 of 582 (Argentina 2019-2024, Belarus 2011-2012, Turkey 2022-2024). At several times the inflation of
every other year, a few such points would decide the fitted line on their own. Argentina's bank accounts also
change basis in 2020. Robustness check 2 puts them back.

## 3. Main specification (question 1)

For each outcome *y*, country *c*, year *t*:

    y[c,t] = a[c] + d[t] + b_g gdp_growth[c,t] + b_pi inflation[c,t] + b_r policy[c,t] + b_e fx_change[c,t] + e[c,t]

- `a[c]`, country fixed effects, absorb each banking system's normal level.
- `d[t]`, year fixed effects, absorb shocks every emerging economy shared: 2008-09, 2020, swings in global
  rates and the dollar. Shocks every unit shares are what make naive error bars too small (docs/methods.md,
  section 2), so they are removed from both sides of the regression.
- That leaves 16 coefficients of interest (4 outcomes x 4 macro variables). Each is read as: in a year when this
  country's growth (say) is 1 point higher than usual for it, relative to other emerging economies that year,
  the outcome is b points higher.

## 4. How the effects unfold (secondary)

Local projections, h = 0, 1 and 2 years ahead:

    y[c,t+h] - y[c,t-1] = a_h[c] + d_h[t] + B_h' x[c,t] + controls: y[c,t-1] and x[c,t-1] + e[c,t+h]

These are reported as four response paths per outcome, with the same inference as below.

## 5. Dollar lending (question 2)

    y[c,t] = a[c] + d[t] + B' x[c,t] + theta fx_change[c,t] x s[c,t-1] + lambda s[c,t-1] + e[c,t]

`s` is the foreign-currency loan share, lagged one year and centered at the sample mean. It is lagged
because a depreciation raises the measured share mechanically: foreign-currency loans are worth more in local
currency. A negative `theta` for ROA and capital means depreciations hurt more where more lending is in
dollars. The sample is main-sample countries with loan-share data (Hungary and Thailand have none; Bangladesh and
Uzbekistan have only a few years).

## 6. Error bars

- **Primary:** clustered by country, with critical values from t(G - 1), where G is the number of countries.
  After the year effects, what remains is mostly persistence within a country over time, which clustering on
  the country allows for; with few clusters it needs small-sample critical values (docs/methods.md, section 5).
- **p-values for the 16 coefficients and for theta:** wild cluster restricted bootstrap (Webb weights,
  B = 9,999, clustered by country). Holm-adjusted p-values across the 16 are shown alongside.
- **Robustness:** Driscoll-Kraay, and clustering by both country and year.
- **Checked first, by simulation.** Before any estimate is seen, fake data are built with this panel's shape
  (its countries, years and gaps) and its noise. The noise is measured from the outcomes after removing only
  country and year effects, so the macro variables play no part. Known effects are planted. The check reports
  how often each method's 95% interval covers the truth, and the smallest effect detectable with 80% power. If
  the primary method covers less than 90% for any coefficient, the best-covering listed method becomes
  primary. That choice is made before estimation.

## 7. Robustness (all fixed now)

1. Stricter sample (15 or more years).
2. Keep the 11 country-years with inflation above 40% a year.
3. Drop countries whose profits do not accumulate through the year (Belarus, Poland).
4. Leave one country out at a time; report the range of estimates.
5. Drop 2020-2021.
6. A wider sample that uses a short-term market rate where the policy rate is missing. This needs another
   download, so it is only run if approved.

## 8. Armenia

1. **Armenia alone.** The same regressions on Armenia's own years (2005 on for ROA, about 20 at most). The
   intervals use the method recommended for short time series: an equal-weighted cosine estimator with
   t critical values (Lazarus, Lewis, Stock and Watson 2018), with its variance scaled by years / (years -
   coefficients). The simulation check showed that without that correction, five coefficients from 13-20
   years leave intervals too narrow (as low as 74% coverage). They are expected to be wide: one country's history is
   too short, which is why the question needed a panel of countries.
2. **Does the emerging-market pattern describe Armenia?** Estimate the panel without Armenia, predict
   Armenia's year-to-year changes from its own macro data, and report how well the predictions track
   what happened.

## 9. How results will be read

Each coefficient is reported with its 95% interval and its minimum detectable effect, in one of three ways.
"Narrow" was fixed in `config.yaml` before any estimate was computed: the interval rules out a typical swing in
the macro variable (its standard deviation once country and year effects are removed) moving the outcome by more
than 0.25 of the outcome's within-country standard deviation. Relationships are also labelled small or large
against the same band.

- the interval excludes zero: evidence of a relationship;
- the interval includes zero but is narrow: no large effect, with the largest effect it rules out stated;
- the interval is wide: the data cannot tell.

## 10. Changes from the first outline, made before estimation, and why

| First outline | Now | Why |
|---|---|---|
| Quarterly panel, effects over 8 quarters | Annual panel, effects over 2 years | Profits are reported year to date in 111 of 119 countries; only the Q4 figure covers the same period everywhere |
| GDP from IMF quarterly national accounts | IMF World Economic Outlook annual growth | The quarterly series disagrees with other sources for several sample countries, including Armenia (data report) |
| Credit growth | Real asset growth | Credit was not in the downloaded extracts; total assets were |
| 27 countries (counted with quarterly GDP) | 38 countries | WEO growth filled the gap for 13 countries; Bulgaria is now classed as advanced; Mongolia has too few complete years |
| Every country-year in the main analysis | Years above 40% inflation in a robustness check only | Argentina, now in the sample, has inflation of up to 220% a year |
| Armenia-alone intervals as published (section 8) | With a small-sample correction | The simulation check, before any estimate, found them too narrow for 13-20 years |
