"""The batch estimator against linearmodels, the wild bootstrap against wildboottest, the noise generator and the
short-series intervals."""
import warnings

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from linearmodels.panel import PanelOLS
from scipy import stats

from embanks import inference, regressions, simcheck


@pytest.fixture(scope="module")
def unbalanced():
    """Twelve countries over 2008-2020 with gaps, four regressors and a persistent, unequal noise."""
    rng = np.random.default_rng(7)
    idx = pd.MultiIndex.from_product([[f"C{i:02d}" for i in range(12)], range(2008, 2021)], names=["country", "year"])
    keep = rng.random(len(idx)) > 0.2
    keep[::13] = True  # every country keeps its first year
    idx = idx[keep]
    x = pd.DataFrame(rng.normal(size=(len(idx), 4)), index=idx, columns=["gdp_growth", "inflation", "policy", "fx_change"])
    scale = np.repeat(rng.uniform(0.5, 3, 12), 13)[keep]
    y = x @ np.array([0.3, 0.0, -0.2, 0.1]) + scale * rng.normal(size=len(idx))
    spec = regressions.Spec("Q1", "roa", idx, x, np.arange(len(idx)))
    return spec, x, y


def test_fit_matches_linearmodels(unbalanced):
    spec, x, y = unbalanced
    beta, se, _ = inference.fit(spec, y.to_numpy()[None])
    mod = PanelOLS(y, x, entity_effects=True, time_effects=True)
    options = {"unadjusted": dict(cov_type="unadjusted"),
               "country cluster": dict(cov_type="clustered", cluster_entity=True, group_debias=True),
               "two-way cluster": dict(cov_type="clustered", cluster_entity=True, cluster_time=True, group_debias=True),
               "Driscoll-Kraay": dict(cov_type="kernel", kernel="bartlett", bandwidth=spec.bandwidth)}
    for name, kw in options.items():
        res = mod.fit(debiased=True, **kw)
        assert np.allclose(beta[0], res.params.to_numpy(), rtol=1e-8)
        assert np.allclose(se[name][0], res.std_errors.to_numpy(), rtol=1e-8), name


def test_wild_bootstrap_matches_wildboottest(unbalanced):
    from wildboottest.wildboottest import wildboottest
    spec, x, y = unbalanced
    mine = inference.wild_pvalues(spec, y.to_numpy()[None], 0, np.random.default_rng(1), 9999)[0]
    d = x.join(y.rename("y")).reset_index()
    dummies = [pd.get_dummies(d[c].astype(str), prefix=c, drop_first=True, dtype=float) for c in ("country", "year")]
    model = sm.OLS(d.y.to_numpy(), sm.add_constant(pd.concat([d[x.columns], *dummies], axis=1)))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = wildboottest(model, B=9999, cluster=pd.factorize(d.country)[0], param="gdp_growth", weights_type="webb",
                           impose_null=True, seed=2, show=False)
    assert mine == pytest.approx(float(res["p-value"].iloc[0]), abs=0.02)


def test_noise_has_the_requested_structure():
    rng = np.random.default_rng(3)
    scales = np.array([1.0, 2.0, 4.0])
    e = simcheck.draw(rng, 20000, scales, 12, rho=0.6, phi=0.3, nu=np.inf).reshape(20000, 3, 12)
    assert e.std(axis=(0, 2)) == pytest.approx(scales, rel=0.02)
    z = e / scales[None, :, None]
    assert np.corrcoef(z[:, :, 1:].ravel(), z[:, :, :-1].ravel())[0, 1] == pytest.approx(0.6, abs=0.02)
    # random loadings: no average co-movement between countries, but sizable co-movement in each panel
    pair = (z[:, 0] * z[:, 1]).mean(axis=1)
    assert abs(pair.mean()) < 0.02 and np.abs(pair).mean() > 0.15


def test_equal_weighted_cosine_intervals_are_honest_for_iid_noise():
    rng = np.random.default_rng(4)
    n = 20
    x = np.column_stack([np.ones(n), rng.normal(size=n)])
    beta, se, nu = inference.ewc(x, rng.normal(size=(4000, n)))
    assert nu == 2
    assert (np.abs(beta[:, 1]) <= stats.t.ppf(0.975, nu) * se[:, 1]).mean() == pytest.approx(0.95, abs=0.02)
