"""Data checks for the cross-country panel, written to outputs/data_report.md."""
import json

import numpy as np
import pandas as pd

from embanks import md_table, panel

DATASETS = {"fsi_roa": "Financial Soundness Indicators", "fsi_other": "Financial Soundness Indicators",
            "gdp": "Quarterly national accounts", "cpi": "Consumer price index", "policy": "Interest rates",
            "usd_rate": "Exchange rates", "weo": "World Economic Outlook, April 2026"}
SUMMARY = [*panel.OUTCOMES, *panel.REGRESSORS, "fx_loan_share"]


def sources(cfg):
    """One row per downloaded extract, from the download manifest."""
    manifest = json.loads((cfg["paths"]["raw"] / "MANIFEST.json").read_text())
    return pd.DataFrame([{"extract": k, "IMF dataset": DATASETS[k], "MB": v["bytes"] / 1e6,
                          "downloaded": v["fetched"][:10], "SHA-256 (first 12)": v["sha256"][:12]}
                         for k, v in manifest.items()])


def source_gaps(cfg, q, a, countries):
    """Annual growth implied by the IMF's quarterly GDP and CPI series, and its gap to the WEO figures the panel uses
    (log points x 100), by country and year inside the window."""
    first, last = cfg["years"]
    d = q.loc[countries, ["gdp", "cpi"]].reset_index()
    d["year"] = d.quarter.dt.year
    g = d.groupby(["country", "year"])
    yearly = pd.concat([g.gdp.sum(), g.cpi.mean()], axis=1).where(g[["gdp", "cpi"]].count() == 4)
    wide = yearly.unstack("country")
    wide = wide.reindex(range(wide.index.min(), wide.index.max() + 1))
    growth = (100 * np.log(wide)).diff().stack("country").reorder_levels(["country", "year"]).sort_index()
    both = growth.join(a[["gdp_growth", "inflation"]]).loc[(slice(None), slice(first, last)), :]
    return pd.DataFrame({"quarterly-series GDP growth": both.gdp, "real GDP growth": both.gdp - both.gdp_growth,
                         "inflation": both.cpi - both.inflation})


def by_country(a, cfg, countries):
    """Complete years, their span, FX-loan-share years and the income-reporting flag for each sample country."""
    first, last = cfg["years"]
    w = a.loc[(countries, slice(first, last)), :]
    ok = w[panel.CORE].notna().all(axis=1)
    span = ok[ok].reset_index().groupby("country").year.agg(["min", "max"])
    return pd.DataFrame({"complete years": ok.groupby(level="country").sum(),
                         "first": span["min"], "last": span["max"],
                         "years with FX-loan share": w.fx_loan_share.notna().groupby(level="country").sum(),
                         "income reporting": w.income_reporting.groupby(level="country").first()})


def extremes(w, n=3):
    """The n lowest and n highest country-years for each summarized variable."""
    rows = []
    for col in SUMMARY:
        s = w[col].dropna().sort_values()
        label = lambda part: ", ".join(f"{c} {y} ({v:.1f})" for (c, y), v in part.items())
        rows.append({"variable": col, "lowest": label(s.head(n)), "highest": label(s.tail(n)[::-1])})
    return pd.DataFrame(rows)


def report(cfg, q, a, samples):
    """Write outputs/data_report.md."""
    cc = cfg
    first, last = cc["years"]
    main = samples["main"]
    w = a.loc[(main, slice(first, last)), :]
    w = w[w[panel.CORE].notna().all(axis=1)]
    conv = a.income_reporting.groupby(level="country").first().dropna()
    stats = w[SUMMARY].describe().T[["count", "mean", "std", "min", "50%", "max"]].rename_axis("variable")
    years = panel.complete_years(a, cfg)
    short = "; ".join(f"{c} ({'classed as advanced' if c in cc['advanced_economies'] else f'{years.get(c, 0)} complete years'})"
                      for c in ("BGR", "MNG"))
    gaps = source_gaps(cfg, q, a, main)
    mean_gap = gaps[["real GDP growth", "inflation"]].abs().groupby(level="country").mean()
    off = mean_gap["real GDP growth"].sort_values(ascending=False)
    off = ", ".join(f"{c} ({v:.1f})" for c, v in off[off > 0.2].items())
    arm = gaps.loc["ARM", "real GDP growth"].dropna()
    top = gaps["quarterly-series GDP growth"].idxmax()
    breaks = ", ".join(f"{c} {y}" for c, y in panel.asset_breaks(q.loc[main], cc["asset_break_logpts"])) or "none"
    hot = w[w.high_inflation]
    hot = ", ".join(f"{c} {y} ({np.expm1(v / 100):.0%})" for (c, y), v in hot.inflation.items())
    text = f"""# Cross-country data: build and checks

*Real data from the IMF (public). Rebuilt by `python run.py --fetch`; the downloaded files and the panel stay
out of git.*

## Sources

{md_table(sources(cfg), fmt="{:.2f}", index=False)}

## Which countries count as emerging

The IMF's World Economic Outlook (April 2026) lists 43 advanced economies (`config.yaml`); every other
economy counts as emerging or developing. Bulgaria joined that list when it adopted the euro in January 2026.

## How profits are reported, and why the panel is annual

In {(conv == "year to date").sum()} of {len(conv)} countries with gross-income data, Q1 gross income is under half
its Q4 value in the median year: profits are reported **year to date**, so a March figure covers three months
and a December figure twelve. Reported ROA is annualized, which hides this in the level but not in its timing.
The Q4 value is the one figure that covers a full calendar year in every country, under year-to-date and
trailing-twelve-month reporting alike. The panel therefore has one row per country and year: bank ratios at Q4,
real GDP growth and inflation from the World Economic Outlook, the policy rate and the exchange rate averaged
over complete calendar years. Sample countries whose gross income does not accumulate through the year ("other"
below) are dropped in a robustness check.

## Sample

Rule: emerging or developing, with at least {cc["min_years"]} years in {first}-{last} in which ROA, the
non-interest-income share, the capital ratio, GDP growth, inflation, the policy rate and the dollar exchange rate
are all observed. Main sample: **{len(main)} countries**; stricter sample ({cc["min_years_strict"]}+ years):
{len(samples["strict"])} countries ({", ".join(samples["strict"])}). Two countries with otherwise long series are
out: {short}.

{md_table(by_country(a, cfg, main), fmt="{:.0f}")}

## Known problems, and what the panel does about them

- **Quarterly real GDP.** Against the IMF's World Economic Outlook, the annual growth implied by the IMF's
  quarterly national-accounts series ("constant prices") is off by more than 0.2 points a year on average in
  these sample countries (mean gap in brackets): {off}. For Armenia it runs above the WEO in {(arm > 0).sum()} of
  {len(arm)} years ({arm.mean():.1f} points a year on average), consistent with prices leaking into the "constant
  prices" series; the largest "growth" it implies in the sample is {gaps["quarterly-series GDP growth"].max():.0f}
  log points ({top[0]} {top[1]}). The panel uses the WEO's real GDP growth. Inflation from the quarterly consumer
  price index matches the WEO to within {mean_gap["inflation"].max():.2f} points a year in every sample country;
  the panel uses the WEO's.
- **Average total assets.** Quarter-on-quarter moves beyond {cfg["asset_break_logpts"]} log points
  are treated as reporting breaks, and asset growth is left missing in that year: {breaks}. (Armenia's
  series halves between 2023Q2 and 2023Q3; its reported ROA does not move, so the break is in the published
  asset level only.)
- **Very high inflation.** These country-years have annual inflation above {cc["high_inflation_pct"]}%: {hot}.
  The main analysis leaves them out and a robustness check keeps them. At several times the inflation of every
  other year they would dominate a straight-line fit. Argentina's figures also break in 2020, the year its banks
  adopted inflation-adjusted accounting, and its real asset growth afterwards is implausible.

## Summary statistics (main sample, complete years)

Percent, or log points x 100 for growth rates. `asset_growth` is real growth in banks' average total assets
(deflated by consumer prices); `fx_change` above zero means the local currency lost value against the dollar.

{md_table(stats, fmt="{:.2f}")}

## The most extreme country-years (main sample)

Crisis years dominate the tails (value in brackets). The plan specifies how these are treated.

{md_table(extremes(w), index=False)}
"""
    out = cfg["paths"]["outputs"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "data_report.md").write_text(text)
    return text
