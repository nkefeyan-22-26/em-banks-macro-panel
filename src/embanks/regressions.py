"""The plan's regressions on the panel's real rows: question 1, question 2 and local projections, positioned on
a complete country-year grid so that simulated and real outcomes go through exactly the same code."""
import numpy as np
import pandas as pd

from embanks import panel
from embanks.inference import nw_lag

def grid(countries, cfg):
    """Every country-year the simulation draws: main-sample countries, the window plus one year before it."""
    first, last = cfg["years"]
    return pd.MultiIndex.from_product([countries, range(first - 1, last + 1)], names=["country", "year"])

class Spec:
    """One regression of the plan on the panel's real rows, with positions on the simulation grid.

    The outcome is y[t] (Q1, Q2) or y[t+h] - y[t-1] with y[t-1] as an extra control (local projections).
    """

    def __init__(self, kind, outcome, rows, x, at, lead=None, lag=None, focus=None):
        self.kind, self.outcome, self.rows, self.x, self.at, self.lead, self.lag = kind, outcome, rows, x, at, lead, lag
        self.focus = focus or panel.REGRESSORS
        self.names = list(x.columns) + (["y_lag"] if lag is not None else [])
        self.j = [self.names.index(f) for f in self.focus]
        country, year = rows.get_level_values("country"), rows.get_level_values("year")
        self.C = pd.get_dummies(country, dtype=float).to_numpy()      # n x countries
        self.T = pd.get_dummies(year, dtype=float).to_numpy()         # n x years, in year order
        d = np.hstack([self.C, self.T])
        self.M = np.eye(len(d)) - d @ np.linalg.pinv(d)               # removes country and year effects
        self.neff = np.linalg.matrix_rank(d)
        self.xt = self.M @ x.to_numpy(float)
        self.bandwidth = nw_lag(self.T.shape[1])
        prev = pd.Series(np.arange(len(rows)), rows).reindex(pd.MultiIndex.from_arrays([country, year - 1]))
        ok = prev.notna().to_numpy()
        self.pairs = np.arange(len(rows))[ok], prev.to_numpy()[ok].astype(int)  # consecutive years, same country

    def data(self, y):
        """Regressors and outcome, both net of country and year effects, for outcome draws y (R, grid)."""
        dep = y[:, self.at] if self.lead is None else y[:, self.lead] - y[:, self.lag]
        if self.lag is None:
            return self.xt, dep @ self.M
        ctrl = (y[:, self.lag] @ self.M)[..., None]
        return np.concatenate([np.broadcast_to(self.xt, ctrl.shape[:2] + self.xt.shape[1:]), ctrl], axis=2), dep @ self.M

def specs(a, cfg, countries, drop=None, horizons=None):
    """The plan's regressions for every outcome: Q1, Q2 and local projections at each horizon.

    `drop` marks country-years left out (default: the high-inflation years); `horizons` overrides the config.
    """
    first, last = cfg["years"]
    g = grid(countries, cfg)
    w = a.reindex(g)
    drop = a.high_inflation if drop is None else drop
    year, pos = g.get_level_values("year").to_numpy(), np.arange(len(g))
    keep = (year >= first) & ~drop.reindex(g).fillna(False).astype(bool).to_numpy()
    have_x = w[panel.REGRESSORS].notna().all(axis=1).to_numpy()
    lagged = w[panel.REGRESSORS].groupby(level="country").shift(1).add_prefix("lag_")
    out = []
    for y in panel.OUTCOMES:
        has_y = w[y].notna().to_numpy()
        base = keep & has_y & have_x
        out.append(Spec("Q1", y, g[base], w.loc[base, panel.REGRESSORS], pos[base]))
        q2 = base & w.fx_loan_share_lag.notna().to_numpy()
        s = w.fx_loan_share_lag[q2] - w.fx_loan_share_lag[q2].mean()
        x2 = w.loc[q2, panel.REGRESSORS].assign(fx_x_share=w.fx_change[q2] * s, fx_share=s)
        out.append(Spec("Q2", y, g[q2], x2, pos[q2], focus=["fx_x_share"]))
        for h in cfg["simulation"]["horizons"] if horizons is None else horizons:
            ok = (keep & have_x & lagged.notna().all(axis=1).to_numpy() & (year <= last - h)
                  & np.roll(has_y, -h) & np.roll(has_y, 1))   # same country: guarded by the year limits
            x = pd.concat([w[panel.REGRESSORS], lagged], axis=1)[ok]
            out.append(Spec(f"LP h={h}", y, g[ok], x, pos[ok], lead=pos[ok] + h, lag=pos[ok] - 1))
    return out

def armenia_rows(a, outcome):
    """Armenia's own years from 2005 with the outcome and every macro variable observed."""
    arm = a.loc["ARM"].loc[2005:]
    return arm[arm[[outcome, *panel.REGRESSORS]].notna().all(axis=1) & ~arm.high_inflation.astype(bool)]
