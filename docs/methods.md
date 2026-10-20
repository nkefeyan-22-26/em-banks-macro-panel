# Methods: how and why

Each section gives the intuition, the short algebra where it helps, and where the repository shows it.

## 1. Where the information comes from

The question has two parts, and each draws on different variation:

- **Common effects:** does a banking sector move with GDP growth, inflation, the policy rate and the exchange rate?
  Every bank in a country sees the same macro values in a period, so the information is the number of distinct
  economic episodes: periods times economies, never banks.
- **Differential effects:** do banking systems with more exposure, such as more lending in dollars, react more? Here
  the information is the difference between units in how they move when the macro variables move.

**Why one country's banks cannot answer the first part.** Take N banks over T periods with regressors that vary only
over time, $y_{it} = a_i + \beta' x_t + e_{it}$. Bank fixed effects subtract each bank's mean, and the demeaned
regressor $\tilde x_t = x_t - \bar x$ is the same for every bank, so

$$\hat\beta_{FE} = \Big(\sum_i \sum_t \tilde x_t \tilde x_t'\Big)^{-1} \sum_i \sum_t \tilde x_t (y_{it} - \bar y_i)
= \Big(\sum_t \tilde x_t \tilde x_t'\Big)^{-1} \sum_t \tilde x_t (\bar y_t - \bar y),$$

the regression of the sector average $\bar y_t$ on $x_t$. Sixteen banks over 21 quarters, the design that first
asked this question, give 21 data points on it, not 336. More banks only average away bank-specific noise.

## 2. Why naive error bars are too small

Let each unit's error combine a shock that all units share and its own shock: $e_{it} = f_t + u_{it}$, with
intraclass correlation $\rho = \sigma_f^2 / (\sigma_f^2 + \sigma_u^2)$. By section 1, the estimate depends on the
period averages $\bar e_t = f_t + \bar u_t$, whose variance is $\sigma_f^2 + \sigma_u^2/N$. Treating all NT errors as
independent assumes $(\sigma_f^2 + \sigma_u^2)/N$, so the variance is understated by the factor

$$\frac{\sigma_f^2 + \sigma_u^2/N}{(\sigma_f^2 + \sigma_u^2)/N} = 1 + (N - 1)\rho$$

(Moulton 1990). With 16 banks sharing 40% of their noise, standard errors are 2.65 times too small, and persistence
makes it worse. In this study, the simulation check shows unadjusted errors covering the truth as little as 77% of
the time even after year effects (section 6).

## 3. The design: two-way fixed effects across countries

$$y_{ct} = a_c + d_t + \beta' x_{ct} + e_{ct}$$

for 38 countries' banking sectors, one row per year.

- **Country effects $a_c$** remove each banking system's normal level.
- **Year effects $d_t$** remove the shocks every emerging economy shared that year: 2009, 2020, global rates and
  the dollar. Shared shocks are what make naive error bars too small (section 2), and here they are removed from
  both sides of the regression.

$\beta$ is identified from country-specific deviations: a country growing faster than usual, relative to other
emerging economies that year. That gives hundreds of independent episodes instead of 21 overlapping quarters. The
estimates are sector-level associations, not effects on individual banks.

## 4. Error bars that allow for persistence and co-movement

- **Clustered by country (primary):** any correlation within a country over time, which is most of what remains
  after year effects.
- **Clustered by country and year:** also allows correlation across countries within a year.
- **Driscoll-Kraay:** sums the scores across countries each year, then estimates their long-run variance over time
  with a Bartlett kernel. It is the right idea for shared, persistent shocks, but it rests on the time dimension
  alone (18 years) with a short window. In the simulation check it covered the truth as little as 84% of the time.
- **One short series** (Armenia alone): HAR inference (section 11).

## 5. Few clusters and the wild cluster restricted bootstrap

Cluster-robust standard errors are reliable with many clusters; with 38 they need help. The minimum is a
$G/(G-1)$ correction with t(G - 1) critical values (Cameron and Miller 2015). Unequal cluster sizes or noise levels
shrink the effective number of clusters further (Carter, Schnepel and Steigerwald 2017). The wild cluster restricted
bootstrap (Cameron, Gelbach and Miller 2008) works as follows:

1. Estimate the model with the null imposed (the coefficient set to zero), and keep its residuals.
2. For each of B draws, give every country one random weight from Webb's six-point distribution
   ($\pm\sqrt{1.5}, \pm 1, \pm\sqrt{0.5}$), and rebuild the outcome as fitted values plus weighted residuals.
3. Re-estimate, and compute the cluster-robust t-statistic.
4. The p-value is the share of bootstrap |t| above the actual |t|.

Each country's residuals move together, so within-country correlation survives. Imposing the null improves size.
The repository's version reduces each draw to a G x G calculation and agrees with the `wildboottest` package
(`tests/test_inference.py`).

## 6. Testing the error bars before estimating

You cannot check, on real data, whether an interval contains the truth. On simulated data you can.

- **Fake panels.** The check keeps the real countries, years, gaps and macro data. It simulates outcomes with no true
  effects, using noise tuned until its statistics match the real outcomes' after country and year effects: each
  country's own noise level, year-to-year persistence, co-movement across countries, and fat tails. This is
  indirect inference, and the macro variables play no part in it.
- **Coverage.** For each method, the check counts how often the 95% interval contains the truth across 1,000 panels.
  Clustering by country covered 92.5-96.4%, and the plan's rule kept it as primary. It still covered at least 91%
  when the noise was made more persistent, more shared or more extreme.
- **Power.** The regressors are fixed and the model linear, so the power against an effect d follows exactly from
  shifting the estimates by d.

See `outputs/simulation_check.md`.

## 7. Detectable effects, and how results are read

$$\mathrm{MDE} = \big(t_{1-\alpha/2,\,df} + t_{\text{power},\,df}\big) \times SE \approx 2.8 \times SE,$$

which is the true effect found four times in five at the 5% level. Each result is read in one of three ways:

- **Relationship:** the 95% interval excludes zero. It is sized "small" or "large" against the band in the next
  point.
- **No large effect:** the interval includes zero but rules out a typical swing (one SD of the macro variable after
  country and year effects) moving the outcome by more than a quarter of its within-country SD. This is a *precise
  null*, and it is informative.
- **Cannot tell:** the interval is too wide for either reading.

The threshold was fixed in `config.yaml` before any estimate was computed.

## 8. Differential effects: dollar lending

$$y_{ct} = a_c + d_t + \beta' x_{ct} + \theta\,(\text{fx\_change}_{ct} \times s_{c,t-1}) + \lambda s_{c,t-1} + e_{ct}$$

$\theta$ asks whether a depreciation moves outcomes more where a larger share of loans, $s$, is in foreign currency:
a difference-in-differences with a continuous exposure. The share is lagged a year and centered. Lagging matters
because a depreciation raises the measured share mechanically, since foreign-currency loans are worth more in local
currency.

## 9. Effects over time: local projections

$$y_{c,t+h} - y_{c,t-1} = a^h_c + d^h_t + \beta_h' x_{ct} + \gamma_h' x_{c,t-1} + \phi_h y_{c,t-1} + e_{c,t+h}, \quad h = 0, 1, 2.$$

Each horizon is its own regression (Jordà 2005). No model of the whole system is needed, which makes the responses
robust to misspecification and easy to run in panels. The outcomes overlap across horizons, so errors are clustered
by country. One caveat: with country effects and a lagged outcome over about 15 years, Nickell (1981) bias of order
1/T affects $\phi_h$, and it can leak into $\beta_h$ when the macro variables correlate with past outcomes.

## 10. Many tests

The 16 main coefficients come with Holm-adjusted p-values (Holm 1979). Among the 48 local-projection coefficients,
about 2.4 would exclude zero by chance at 5%. Read them as patterns, not separate findings.

## 11. One country alone: HAR inference

Armenia's own 13-20 years use the equal-weighted cosine estimator (Lazarus, Lewis, Stock and Watson 2018), with
$\nu = \lfloor 0.4\,T^{2/3}\rfloor$, t($\nu$) critical values, and a small-sample factor T / (T - k). Even so, the
simulation check found about 80% coverage for the policy rate at 13-15 years: one country's history is too short.
The panel estimated without Armenia also predicts Armenia's year-to-year changes, as an out-of-sample check.

## 12. Measurement before estimation

See `outputs/data_report.md`.

- **Year-to-date reporting.** Most countries report bank profits year to date: a March figure covers three months
  and a December figure twelve. Only the Q4 value covers a full year everywhere, so the panel is annual.
- **Cross-source validation.** For eight sample countries, the IMF's quarterly "constant prices" GDP implies growth
  far from the World Economic Outlook's (Armenia by 3.5 points a year, in every year). The WEO is used.
- **Breaks.** A quarter-on-quarter move in reported assets beyond 40 log points is treated as a reporting break.
- **High inflation.** The 11 country-years above 40% inflation (Bruno and Easterly 1998) leave the main analysis; a
  robustness check keeps them.
- **Mechanical links.** A depreciation revalues foreign-currency assets, which raises measured assets and lowers ROA
  as a ratio. Inflation is the deflator of real asset growth. Both are quantified in the results.

## 13. Why no unit-root pretests, and why no IV or GMM

- **Unit roots.** Bank ratios are bounded, so they cannot wander like a random walk; they are treated as stationary,
  possibly persistent. Unit-root pretests have little power in 10-18 years. Differencing on that basis would change
  the question, and persistence is handled by the inference instead.
- **GMM.** Arellano-Bond and system GMM need many units. With 38 countries and lagged instruments, the instrument
  count soon rivals the units and biases estimates back toward OLS (Roodman 2009).
- **IV.** It needs something that moves the macro variable and affects banks only through it. Lagged macro
  variables fail that test when shocks persist.

## 14. What would make these causal

- **Monetary policy:** identified policy surprises, from high-frequency or narrative methods, instead of the policy
  rate itself.
- **Exchange rates:** shocks from outside the country, such as commodity prices or the global dollar, interacted with
  exposure measured before the shock.
- **Banks:** bank-level data across countries, so that exposure designs compare banks, not whole systems.
