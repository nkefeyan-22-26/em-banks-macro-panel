# From question to answer: the analyst's workflow

The steps, in order, that take a question like "how does the economy affect banks?" to an answer that holds up.
Each step lists what it involves, what this study did, and the mistake it prevents. Many of those mistakes come from
the first, single-country version of this question.

| Step | In one line |
|---|---|
| 1 | Pin down exactly what you want to know |
| 2 | Count the information before you estimate anything |
| 3 | Choose data that carry that information |
| 4 | Build a reproducible pipeline |
| 5 | Learn how every variable is built |
| 6 | Validate across sources; handle breaks and outliers by rule |
| 7 | Fix the sample by rule |
| 8 | Write the plan before estimating |
| 9 | Test the error bars on your own design |
| 10 | Estimate, and check the software |
| 11 | Run the planned robustness checks |
| 12 | Read size, uncertainty and mechanics, not stars |
| 13 | Communicate plainly and reproducibly |

## 1. Pin down exactly what you want to know

"How does the economy affect banks?" hides two questions:

- **Common effects:** does the whole sector move with GDP growth, rates and the exchange rate?
- **Differential effects:** do more-exposed banks or systems move more?

They need different data. Decide early whether you want an association or a causal effect, and say which. Write
down units (percent, log points), timing (same year or later), and the population (banks, banking systems,
which countries).

*Here:* sector-level associations for 38 emerging economies, plus a dollar-lending interaction.
*Prevents:* answering a question nobody asked. For example, market shares sum to one, so they cannot respond to an
economy-wide variable.

## 2. Count the information before you estimate anything

Ask where the variation that identifies each effect comes from.

- **Common effects** are identified only by different economic episodes: periods times economies. Adding banks in
  the same country adds no episodes; with fixed effects the regression collapses to the sector average
  (`docs/methods.md`, section 1).
- **Shared shocks** shrink the information further, and naive error bars miss it by $\sqrt{1 + (N-1)\rho}$.
- **Power calculation.** Before collecting or estimating, compute the smallest effect the design could detect. If
  realistic effects are smaller, change the data, not the regression.

*Here:* one country's 16 banks over 21 quarters is about 21 episodes, too few for realistic effects. Hence a panel
of countries.

## 3. Choose data that carry that information

- **Common effects:** many economies, or a long history, so that macro conditions vary independently.
- **Differential effects:** unit-level data (banks), with exposure measured before the shocks.
- **Sources:** prefer harmonized international data (IMF Financial Soundness Indicators, World Economic Outlook,
  interest and exchange rates) for comparability, and national sources for validation.
- **With truly ample data:** bank-level panels across many countries, from supervisory or commercial databases;
  exposure measures such as foreign-currency lending and funding mix; and identified shocks for causal questions.

*Here:* IMF data on 38 emerging and developing economies, 2008-2025, about 570 country-years per regression.

## 4. Build a reproducible pipeline

- Download by script, keep the raw files untouched, and record each file's URL, date, size and checksum.
- Transform only in code, with tests. Never edit data by hand.
- Keep raw data out of version control when you may not redistribute it; publish the code and derived results.

*Here:* `src/embanks/fetch.py` writes a manifest, the raw files stay out of git, and `python run.py` rebuilds every
output. Tests check the estimator against linearmodels and the bootstrap against wildboottest.

## 5. Learn how every variable is built

Read each definition. Is it a flow or a stock? What are the numerator and denominator? Is it an average? Is it
annualized? Over what window: a quarter, year to date, or the last twelve months? What units, currency, seasonal
adjustment, and constant or current prices? When the metadata are thin, test the convention in the data.

*Here:* gross income in Q1 is about a quarter of Q4 in 111 of 119 countries. So profits are reported year to date,
and only year-end values are comparable. Know the mechanical links too. A depreciation revalues foreign-currency
assets, inflation is the deflator of real growth, and shares sum to one.

## 6. Validate across sources; handle breaks and outliers by rule

- **Validate.** Compare the same concept from two or three sources. *Here:* the IMF's quarterly "constant prices" GDP
  disagreed with the WEO for eight countries, so the WEO is used.
- **Look for breaks**, sudden level shifts, and set a rule. *Here:* a quarter-on-quarter move in assets beyond 40
  log points counts as a reporting break.
- **Decide outlier treatment by rule, never by looking at results.** *Here:* years above 40% inflation leave the main
  analysis and return in a check.
- **Log every rule with its reason** (`docs/assumptions.md`).

## 7. Fix the sample by rule

Use published classifications and coverage thresholds, and record what each rule excludes.

*Here:* the IMF's April 2026 list of advanced economies, and at least 10 complete years (15 for the stricter
sample). Bulgaria is out, as now classified advanced; Mongolia is out, with only 6 complete years.

## 8. Write the plan before estimating

Fix in advance:

- the specifications, variables and sample;
- the error bars and robustness checks;
- the threshold for "too small to matter";
- the rule for switching methods if a check fails.

Log any change made before estimation, with its reason.

*Here:* `docs/plan.md`. *Prevents:* specification search, such as dropping regressors that came out insignificant.
That is how a design produces "findings" by accident.

## 9. Test the error bars on your own design

Simulate outcomes on your actual rows and regressors, with known effects and noise matched to the real data's
features. Then measure each method's coverage and the smallest detectable effect, pick the method by the
pre-set rule, and stress-test it.

*Here:* clustering by country covered the truth 92.5-96.4% of the time, unadjusted errors as little as 77%, and
Driscoll-Kraay 84% (`outputs/simulation_check.md`).

## 10. Estimate, and check the software

Run exactly the planned regressions. Re-run them in a standard package to confirm the numbers, and report
multiple-testing adjustments.

*Here:* every main regression matches linearmodels to 1e-6, and the 16 main p-values are Holm-adjusted.

## 11. Run the planned robustness checks

Use a stricter sample, put outliers back, leave out units with odd reporting, leave out each country in turn,
drop crisis years, and try alternative error bars. Report all of them, whatever they show. Robustness is not a
second chance to find significance.

## 12. Read size, uncertainty and mechanics, not stars

- **Significance and size are separate.** A clear effect can be small. *Here:* a typical depreciation goes with ROA
  0.13 points lower, against an average of 2%.
- **A precise null is a finding.** Ruling out large effects of growth on profitability is informative.
- **Separate mechanical from behavioral explanations.** Revaluation alone could account for the asset-growth result.
- **Association is not causation**, and sector-level results are not bank-level results.

## 13. Communicate plainly and reproducibly

Lead with the answer in plain words, then the uncertainty, then the limits, and what would change the
conclusion. One command should rebuild everything.

## If even more data were available

- **Bank-level panels across countries:** compare banks by exposure, measured before shocks.
- **Identified shocks:** monetary-policy surprises, or exchange-rate moves driven from outside, for causal effects.
- **Quarterly harmonized flows:** de-cumulate year-to-date figures using reporting metadata, for sharper timing.
- **Differences by regime:** non-linear effects in crises, and contrasts between pegs and floats, or high and low
  dollarization.
