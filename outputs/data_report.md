# Cross-country data: build and checks

*Real data from the IMF (public). Rebuilt by `python run.py --fetch`; the downloaded files and the panel stay
out of git.*

## Sources

| extract | IMF dataset | MB | downloaded | SHA-256 (first 12) |
|---|---|---|---|---|
| fsi_roa | Financial Soundness Indicators | 0.43 | 2026-10-16 | 5939c1ff0e37 |
| fsi_other | Financial Soundness Indicators | 1.03 | 2026-10-16 | 8364cc57e268 |
| gdp | Quarterly national accounts | 0.26 | 2026-10-16 | ccafbca3e05d |
| cpi | Consumer price index | 0.60 | 2026-10-16 | 18900ba26ae0 |
| policy | Interest rates | 0.13 | 2026-10-16 | e64df57d291f |
| usd_rate | Exchange rates | 1.26 | 2026-10-16 | 45bab50895ad |
| weo | World Economic Outlook, April 2026 | 0.36 | 2026-10-19 | 617faf20c439 |

## Which countries count as emerging

The IMF's World Economic Outlook (April 2026) lists 43 advanced economies (`config.yaml`); every other
economy counts as emerging or developing. Bulgaria joined that list when it adopted the euro in January 2026.

## How profits are reported, and why the panel is annual

In 111 of 119 countries with gross-income data, Q1 gross income is under half
its Q4 value in the median year: profits are reported **year to date**, so a March figure covers three months
and a December figure twelve. Reported ROA is annualized, which hides this in the level but not in its timing.
The Q4 value is the one figure that covers a full calendar year in every country, under year-to-date and
trailing-twelve-month reporting alike. The panel therefore has one row per country and year: bank ratios at Q4,
real GDP growth and inflation from the World Economic Outlook, the policy rate and the exchange rate averaged
over complete calendar years. Sample countries whose gross income does not accumulate through the year ("other"
below) are dropped in a robustness check.

## Sample

Rule: emerging or developing, with at least 10 years in 2008-2025 in which ROA, the
non-interest-income share, the capital ratio, GDP growth, inflation, the policy rate and the dollar exchange rate
are all observed. Main sample: **38 countries**; stricter sample (15+ years):
27 countries (ALB, ARM, BLR, BRA, CHL, COL, CRI, GEO, GHA, GMB, GTM, HND, HUN, IDN, KEN, MDA, MEX, MUS, MYS, NGA, PHL, PNG, POL, ROU, THA, TUR, ZAF). Two countries with otherwise long series are
out: BGR (classed as advanced); MNG (6 complete years).

| country | complete years | first | last | years with FX-loan share | income reporting |
|---|---|---|---|---|---|
| AGO | 12 | 2012 | 2024 | 14 | year to date |
| ALB | 15 | 2010 | 2024 | 16 | year to date |
| ARG | 10 | 2012 | 2024 | 14 | year to date |
| ARM | 15 | 2010 | 2024 | 15 | year to date |
| BGD | 12 | 2014 | 2025 | 4 | year to date |
| BLR | 16 | 2010 | 2025 | 13 | other |
| BRA | 18 | 2008 | 2025 | 18 | year to date |
| CHL | 18 | 2008 | 2025 | 18 | year to date |
| COL | 18 | 2008 | 2025 | 18 | year to date |
| CRI | 18 | 2008 | 2025 | 18 | year to date |
| FJI | 11 | 2011 | 2021 | 14 | year to date |
| GEO | 17 | 2008 | 2025 | 18 | year to date |
| GHA | 16 | 2008 | 2023 | 18 | year to date |
| GMB | 15 | 2008 | 2022 | 15 | year to date |
| GTM | 17 | 2009 | 2025 | 17 | year to date |
| HND | 16 | 2010 | 2025 | 16 | year to date |
| HUN | 18 | 2008 | 2025 | 0 | year to date |
| IDN | 15 | 2011 | 2025 | 15 | year to date |
| JOR | 10 | 2016 | 2025 | 11 | year to date |
| KAZ | 12 | 2009 | 2020 | 18 | year to date |
| KEN | 17 | 2008 | 2024 | 17 | year to date |
| KGZ | 14 | 2010 | 2023 | 16 | year to date |
| MDA | 16 | 2009 | 2025 | 17 | year to date |
| MEX | 18 | 2008 | 2025 | 18 | year to date |
| MUS | 17 | 2009 | 2025 | 17 | year to date |
| MYS | 18 | 2008 | 2025 | 18 | year to date |
| NGA | 18 | 2008 | 2025 | 10 | year to date |
| PER | 13 | 2010 | 2022 | 15 | year to date |
| PHL | 17 | 2009 | 2025 | 17 | year to date |
| PNG | 16 | 2008 | 2023 | 16 | year to date |
| POL | 17 | 2008 | 2025 | 18 | other |
| PRY | 10 | 2011 | 2020 | 18 | year to date |
| ROU | 16 | 2010 | 2025 | 13 | year to date |
| THA | 18 | 2008 | 2025 | 0 | year to date |
| TTO | 12 | 2014 | 2025 | 18 | year to date |
| TUR | 18 | 2008 | 2025 | 18 | year to date |
| UZB | 11 | 2014 | 2024 | 6 | year to date |
| ZAF | 17 | 2008 | 2024 | 17 | year to date |

## Known problems, and what the panel does about them

- **Quarterly real GDP.** Against the IMF's World Economic Outlook, the annual growth implied by the IMF's
  quarterly national-accounts series ("constant prices") is off by more than 0.2 points a year on average in
  these sample countries (mean gap in brackets): BLR (8.2), ARM (3.5), THA (1.2), TTO (0.9), NGA (0.7), ALB (0.3), MUS (0.2), BGD (0.2). For Armenia it runs above the WEO in 18 of
  18 years (3.5 points a year on average), consistent with prices leaking into the "constant
  prices" series; the largest "growth" it implies in the sample is 46
  log points (BLR 2018). The panel uses the WEO's real GDP growth. Inflation from the quarterly consumer
  price index matches the WEO to within 0.95 points a year in every sample country;
  the panel uses the WEO's.
- **Average total assets.** Quarter-on-quarter moves beyond 40 log points
  are treated as reporting breaks, and asset growth is left missing in that year: ARG 2020, ARM 2023. (Armenia's
  series halves between 2023Q2 and 2023Q3; its reported ROA does not move, so the break is in the published
  asset level only.)
- **Very high inflation.** These country-years have annual inflation above 40%: ARG 2019 (54%), ARG 2020 (42%), ARG 2021 (48%), ARG 2022 (72%), ARG 2023 (133%), ARG 2024 (220%), BLR 2011 (53%), BLR 2012 (59%), TUR 2022 (72%), TUR 2023 (54%), TUR 2024 (59%).
  The main analysis leaves them out and a robustness check keeps them. At several times the inflation of every
  other year they would dominate a straight-line fit. Argentina's figures also break in 2020, the year its banks
  adopted inflation-adjusted accounting, and its real asset growth afterwards is implausible.

## Summary statistics (main sample, complete years)

Percent, or log points x 100 for growth rates. `asset_growth` is real growth in banks' average total assets
(deflated by consumer prices); `fx_change` above zero means the local currency lost value against the dollar.

| variable | count | mean | std | min | 50% | max |
|---|---|---|---|---|---|---|
| roa | 582.00 | 2.06 | 1.38 | -8.82 | 1.84 | 8.19 |
| nii_share | 582.00 | 38.22 | 12.77 | 8.30 | 37.25 | 90.14 |
| car | 582.00 | 18.47 | 4.97 | 0.32 | 17.49 | 41.07 |
| asset_growth | 557.00 | 4.60 | 9.98 | -123.95 | 4.97 | 37.10 |
| gdp_growth | 582.00 | 3.13 | 3.79 | -18.82 | 3.64 | 13.06 |
| inflation | 582.00 | 6.58 | 8.86 | -1.71 | 4.53 | 116.28 |
| policy | 582.00 | 7.66 | 8.08 | 0.25 | 5.66 | 98.25 |
| fx_change | 582.00 | 5.56 | 12.57 | -17.35 | 2.47 | 112.74 |
| fx_loan_share | 519.00 | 28.94 | 17.62 | 0.83 | 27.93 | 76.82 |

## The most extreme country-years (main sample)

Crisis years dominate the tails (value in brackets). The plan specifies how these are treated.

| variable | lowest | highest |
|---|---|---|
| roa | NGA 2009 (-8.8), KAZ 2009 (-6.5), BGD 2025 (-4.3) | ARG 2023 (8.2), PNG 2013 (6.7), PNG 2008 (6.4) |
| nii_share | PER 2020 (8.3), ALB 2018 (8.4), ALB 2017 (9.1) | BLR 2014 (90.1), BLR 2024 (90.0), BLR 2025 (89.8) |
| car | BGD 2025 (0.3), NGA 2010 (1.8), NGA 2009 (4.1) | PNG 2021 (41.1), PNG 2023 (39.6), PNG 2020 (39.2) |
| asset_growth | ARG 2024 (-123.9), ARG 2023 (-84.5), ARG 2022 (-56.4) | UZB 2017 (37.1), HUN 2021 (33.7), NGA 2008 (30.5) |
| gdp_growth | FJI 2020 (-18.8), MUS 2020 (-15.7), PER 2020 (-11.6) | GHA 2011 (13.1), MDA 2021 (13.0), PNG 2014 (12.7) |
| inflation | FJI 2020 (-1.7), ROU 2016 (-1.6), ARM 2016 (-1.4) | ARG 2024 (116.3), ARG 2023 (84.8), ARG 2022 (54.5) |
| policy | FJI 2021 (0.2), FJI 2020 (0.2), POL 2020 (0.3) | ARG 2023 (98.2), ARG 2019 (66.1), ARG 2022 (61.6) |
| fx_change | CRI 2023 (-17.4), ZAF 2010 (-14.6), ARM 2022 (-14.5) | ARG 2024 (112.7), NGA 2024 (83.0), ARG 2023 (81.9) |
| fx_loan_share | FJI 2012 (0.8), FJI 2011 (0.9), FJI 2013 (1.1) | GEO 2009 (76.8), GEO 2010 (73.9), GEO 2008 (72.6) |
