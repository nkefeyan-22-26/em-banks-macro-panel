"""Country-year panel built from the IMF extracts.

Most compilers report income-based FSIs year to date: a March value covers one quarter and a December value the
whole year (gross income in Q1 is about a quarter of its Q4 value in 111 of 119 countries). Bank ratios are
therefore taken at Q4, which covers the calendar year under year-to-date and trailing-twelve-month reporting
alike. Real GDP growth and inflation come from the World Economic Outlook, because the quarterly national-accounts
series disagrees with other sources for several countries (data report). The policy rate and the exchange rate
are averaged over complete calendar years.
"""
import numpy as np
import pandas as pd

from embanks import fetch

FSI = {"ROA_CFSI_PT": "roa", "FSI99_CFSI_PT": "interest_share", "FSI688_CFSI_PT": "car",
       "FSI131_AFSI_PT": "fx_loan_share", "ROA_ATA_XDC": "assets", "FSI99_GINC_XDC": "gross_income"}
QUARTERLY = ["gdp", "cpi", "policy", "usd_rate"]  # gdp and cpi only check the WEO figures
RATES = ["policy", "usd_rate"]
OUTCOMES = ["roa", "nii_share", "car", "asset_growth"]
REGRESSORS = ["gdp_growth", "inflation", "policy", "fx_change"]
CORE = ["roa", "nii_share", "car", *REGRESSORS]  # what the sample rule requires, jointly, in a year


def quarterly(cfg):
    """Every series in one country-quarter table, from 2000 on; country codes limited to ISO alpha-3."""
    fsi = pd.concat([fetch.read(cfg, "fsi_roa"), fetch.read(cfg, "fsi_other")])
    parts = [fsi[fsi.INDICATOR.isin(FSI)].assign(series=lambda d: d.INDICATOR.map(FSI))]
    parts += [fetch.read(cfg, name).assign(series=name) for name in QUARTERLY]
    long = pd.concat(parts)
    long = long[long.COUNTRY.str.fullmatch("[A-Z]{3}") & (long.quarter.dt.year >= 2000)]
    return (long.pivot(index=["COUNTRY", "quarter"], columns="series", values="value")
            .rename_axis(index=["country", "quarter"], columns=None))


def weo(cfg):
    """WEO real GDP growth and inflation, percent changes converted to log points x 100, 2000 to the window's end."""
    w = fetch.read(cfg, "weo")
    w = w[w.COUNTRY.str.fullmatch("[A-Z]{3}") & w.year.between(2000, cfg["years"][1])]
    t = w.pivot(index=["COUNTRY", "year"], columns="INDICATOR", values="value")[["NGDP_RPCH", "PCPIPCH"]]
    return (100 * np.log1p(t / 100)).set_axis(["gdp_growth", "inflation"], axis=1).rename_axis(
        index=["country", "year"], columns=None)


def income_convention(q):
    """'year to date' where gross income in Q1 is under half its Q4 value in the median year, else 'other'."""
    gi = q["gross_income"].dropna().reset_index()
    gi["year"], gi["qtr"] = gi.quarter.dt.year, gi.quarter.dt.quarter
    p = gi.pivot_table(index=["country", "year"], columns="qtr", values="gross_income")
    ratio = (p[1] / p[4]).groupby(level="country").median().dropna()
    return pd.Series(np.where(ratio < 0.5, "year to date", "other"), index=ratio.index, name="income_reporting")


def asset_breaks(q, limit):
    """Country-years containing a quarter-on-quarter move in average total assets beyond `limit` log points x 100."""
    jump = 100 * np.log(q.assets.where(q.assets > 0)).groupby(level="country").diff().abs() > limit
    hit = jump[jump].reset_index()
    return pd.MultiIndex.from_arrays([hit.country, hit.quarter.dt.year], names=["country", "year"]).unique()


def annual(q, growth_and_inflation, break_limit=40):
    """Country-year table: bank ratios at Q4, WEO growth and inflation, the policy rate and exchange rate averaged
    over complete years; growth rates in log points x 100.

    Asset growth is left missing in years with a reporting break in average total assets (see asset_breaks).
    """
    d = q.reset_index()
    d["year"] = d.quarter.dt.year
    g = d.groupby(["country", "year"])
    rates = g[RATES].mean().where(g[RATES].count() == 4)
    bank = d[d.quarter.dt.quarter == 4].set_index(["country", "year"])[list(FSI.values())]
    a = rates.join(bank, how="outer").join(growth_and_inflation, how="outer")
    years = a.index.get_level_values("year")
    a = a.reindex(pd.MultiIndex.from_product([a.index.get_level_values("country").unique().sort_values(),
                                              range(years.min(), years.max() + 1)], names=["country", "year"]))

    def growth(col):
        return 100 * np.log(a[col].where(a[col] > 0)).groupby(level="country").diff()

    a = a.assign(fx_change=growth("usd_rate"), nii_share=100 - a.interest_share,
                 asset_growth=growth("assets") - a.inflation,
                 fx_loan_share_lag=a.fx_loan_share.groupby(level="country").shift())
    a.loc[a.index.isin(asset_breaks(q, break_limit)), "asset_growth"] = np.nan
    return a


def complete_years(a, cfg):
    """Years inside the window in which every CORE variable is observed, by country."""
    first, last = cfg["years"]
    inside = a[a.index.get_level_values("year").to_series().between(first, last).to_numpy()]
    return inside[CORE].notna().all(axis=1).groupby(level="country").sum()


def sample(a, cfg, min_years):
    """Emerging and developing economies with at least `min_years` complete years."""
    years = complete_years(a, cfg)
    keep = (years >= min_years) & ~years.index.isin(cfg["advanced_economies"])
    return sorted(years.index[keep])


def build(cfg):
    """Quarterly table, annual panel and samples; the panel is written to the git-ignored processed folder."""
    q = quarterly(cfg)
    cc = cfg
    a = annual(q, weo(cfg), cc["asset_break_logpts"]).join(income_convention(q))
    a["high_inflation"] = a.inflation > 100 * np.log1p(cc["high_inflation_pct"] / 100)
    samples = {"main": sample(a, cfg, cc["min_years"]), "strict": sample(a, cfg, cc["min_years_strict"])}
    out = cfg["paths"]["processed"]
    out.mkdir(parents=True, exist_ok=True)
    a.to_csv(out / "panel_annual.csv")
    return q, a, samples
