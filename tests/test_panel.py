"""Reading the IMF extracts and building the country-year panel, on small synthetic inputs."""
import json

import numpy as np
import pandas as pd
import pytest

from embanks import fetch, panel

YEARS = [2006, 2007, 2008]


def synthetic_quarterly(country="AAA", cumulative=True):
    """Three years of every series for one country; GDP grows 10% a year, the currency loses 5% a year."""
    quarters = pd.period_range(f"{YEARS[0]}Q1", f"{YEARS[-1]}Q4", freq="Q")
    year = quarters.year - YEARS[0]
    qtr = quarters.quarter
    d = pd.DataFrame({"gdp": 100 * 1.1 ** year * np.array([0.8, 1.0, 1.1, 1.1])[qtr - 1],
                      "cpi": 100 * 1.04 ** year, "policy": 5.0 + year, "usd_rate": 10 * 1.05 ** year,
                      "roa": 1.0 + 0.1 * qtr, "interest_share": 60.0 + year, "car": 15.0 + year,
                      "fx_loan_share": 30.0 + 2 * year, "assets": 1000 * 1.06 ** year,
                      "gross_income": (qtr if cumulative else np.ones(len(qtr))) * 10.0}, index=quarters)
    d.index = pd.MultiIndex.from_product([[country], quarters], names=["country", "quarter"])
    return d


def test_read_parses_sdmx_json(tmp_path):
    body = {"data": {"structures": [{"dimensions": {
        "series": [{"id": "COUNTRY", "values": [{"id": "ARM"}, {"id": "BRA"}, {"id": "CHL"}]},
                   {"id": "INDICATOR", "values": [{"id": "ROA"}]}],
        "observation": [{"id": "TIME_PERIOD", "values": [{"value": "2020-Q4"}, {"value": "2021-Q1"}]}]}}],
        "dataSets": [{"series": {"0:0": {"observations": {"0": ["1.5"], "1": [None]}},
                                 "1:0": {"observations": {"1": ["2.25"]}}, "2:0": {}}}]}}
    (tmp_path / "x.json").write_text(json.dumps(body))
    out = fetch.read({"paths": {"raw": tmp_path}}, "x")
    assert out[["COUNTRY", "INDICATOR", "value"]].values.tolist() == [["ARM", "ROA", 1.5], ["BRA", "ROA", 2.25]]
    assert out.quarter.tolist() == [pd.Period("2020Q4", "Q"), pd.Period("2021Q1", "Q")]


def test_read_gives_integer_years_for_annual_extracts(tmp_path):
    body = {"data": {"structures": [{"dimensions": {
        "series": [{"id": "COUNTRY", "values": [{"id": "ARM"}]}, {"id": "INDICATOR", "values": [{"id": "NGDP_RPCH"}]}],
        "observation": [{"id": "TIME_PERIOD", "values": [{"value": "2022"}, {"value": "2023"}]}]}}],
        "dataSets": [{"series": {"0:0": {"observations": {"0": ["12.6"], "1": ["8.3"]}}}}]}}
    (tmp_path / "w.json").write_text(json.dumps(body))
    out = fetch.read({"paths": {"raw": tmp_path}}, "w")
    assert out.year.tolist() == [2022, 2023] and out.value.tolist() == [12.6, 8.3]


def synthetic_weo(countries=("AAA",)):
    """WEO-style growth (10% a year) and inflation (4% a year), in log points x 100."""
    idx = pd.MultiIndex.from_product([list(countries), YEARS], names=["country", "year"])
    return pd.DataFrame({"gdp_growth": 100 * np.log(1.1), "inflation": 100 * np.log(1.04)}, index=idx)


def test_income_convention_detects_year_to_date():
    q = pd.concat([synthetic_quarterly("AAA", cumulative=True), synthetic_quarterly("BBB", cumulative=False)])
    assert panel.income_convention(q).to_dict() == {"AAA": "year to date", "BBB": "other"}


def test_annual_takes_q4_and_complete_years():
    q = synthetic_quarterly().drop(("AAA", pd.Period("2006Q2", "Q")))   # 2006 loses a quarter of rates data
    a = panel.annual(q, synthetic_weo()).loc["AAA"]
    assert np.isnan(a.loc[2006, "usd_rate"]) and np.isnan(a.loc[2007, "fx_change"])  # 2007 change needs all of 2006
    assert a.loc[2008, "fx_change"] == pytest.approx(100 * np.log(1.05))
    assert a.loc[2008, "policy"] == pytest.approx(7.0)
    assert a.loc[2008, "gdp_growth"] == pytest.approx(100 * np.log(1.1))
    assert a.loc[2008, "roa"] == pytest.approx(1.4) and a.loc[2008, "nii_share"] == pytest.approx(38.0)
    assert a.loc[2008, "asset_growth"] == pytest.approx(100 * np.log(1.06 / 1.04))
    assert a.loc[2008, "fx_loan_share_lag"] == pytest.approx(32.0)


def test_asset_break_blanks_asset_growth_in_that_year_only():
    q = synthetic_quarterly()
    q.loc[("AAA", pd.Period("2008Q3", "Q")):, "assets"] /= 2
    a = panel.annual(q, synthetic_weo(), break_limit=40).loc["AAA"]
    assert np.isnan(a.loc[2008, "asset_growth"]) and not np.isnan(a.loc[2007, "asset_growth"])


def test_sample_rule_needs_joint_years_and_excludes_advanced():
    q = pd.concat([synthetic_quarterly("AAA"), synthetic_quarterly("USA")])
    a = panel.annual(q, synthetic_weo(("AAA", "USA")))
    cfg = {"years": [2006, 2008], "advanced_economies": ["USA"]}
    assert panel.complete_years(a, cfg).to_dict() == {"AAA": 2, "USA": 2}  # growth rates start in 2007
    assert panel.sample(a, cfg, 2) == ["AAA"] and panel.sample(a, cfg, 3) == []
