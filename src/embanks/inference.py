"""Estimators: two-way fixed effects with four kinds of standard error for many outcome draws at once, the
wild cluster restricted bootstrap, and equal-weighted cosine intervals for a single short time series."""
import numpy as np

METHODS = ["unadjusted", "country cluster", "two-way cluster", "Driscoll-Kraay"]

PRIMARY = "country cluster"

WEBB = np.array([-np.sqrt(1.5), -1.0, -np.sqrt(0.5), np.sqrt(0.5), 1.0, np.sqrt(1.5)])

def nw_lag(n_quarters):
    """Newey-West rule of thumb: floor(4 (T/100)^(2/9))."""
    return int(np.floor(4 * (n_quarters / 100) ** (2 / 9)))

def kernel_meat(h, lag):
    """Bartlett-weighted long-run covariance of score series h, shape (R, T, K)."""
    s = np.einsum("rtk,rtl->rkl", h, h)
    for j in range(1, lag + 1):
        g = np.einsum("rtk,rtl->rkl", h[:, j:], h[:, :-j])
        s += (1 - j / (lag + 1)) * (g + g.transpose(0, 2, 1))
    return s

def fit(spec, y):
    """Slopes and four kinds of standard error for each outcome draw (rows of y, on the grid), with t df.

    Matches linearmodels PanelOLS(entity_effects=True, time_effects=True) with debiased=True and, for the
    clustered kinds, group_debias=True (tests/test_inference.py).
    """
    xt, yt = spec.data(y)
    xt = np.broadcast_to(xt, (len(yt),) + xt.shape[-2:])
    n, k = xt.shape[1:]
    bread = np.linalg.inv(np.einsum("rnk,rnl->rkl", xt, xt))
    beta = np.einsum("rkl,rnl,rn->rk", bread, xt, yt)
    e = yt - np.einsum("rnk,rk->rn", xt, beta)
    s = xt * e[..., None]
    by_c, by_t = np.einsum("ng,rnk->rgk", spec.C, s), np.einsum("nt,rnk->rtk", spec.T, s)
    g, t = spec.C.shape[1], spec.T.shape[1]

    def outer(z):
        return np.einsum("rgk,rgl->rkl", z, z)

    def debias(m):
        return m / (m - 1) * (n - 1) / n

    meat = {"country cluster": debias(g) * outer(by_c),
            "two-way cluster": debias(g) * outer(by_c) + debias(t) * outer(by_t) - outer(s),
            "Driscoll-Kraay": kernel_meat(by_t, spec.bandwidth)}
    scale = n / (n - spec.neff - k)
    var = {"unadjusted": (scale * (e ** 2).sum(axis=1) / n)[:, None, None] * bread}
    var |= {m: scale * bread @ v @ bread for m, v in meat.items()}
    se = {m: np.sqrt(np.clip(np.diagonal(v, axis1=1, axis2=2), 0, None)) for m, v in var.items()}
    se = {m: np.where(v > 0, v, np.nan) for m, v in se.items()}   # a negative two-way variance gives no interval
    df = {"unadjusted": n - spec.neff - k, "country cluster": g - 1, "two-way cluster": min(g, t) - 1,
          "Driscoll-Kraay": t - k - 1}
    return beta, se, df

def wild_pvalues(spec, y, j, rng, n_boot):
    """Wild cluster restricted bootstrap p-values of H0: beta_j = 0, Webb weights by country, one per draw.

    With u the restricted residuals and w the weights that give beta_j, a bootstrap draw v (one weight per
    country) has numerator (C'(w u))'v and cluster scores C' diag(w) M_Z diag(u) C v: G x G work per draw.
    """
    xt = spec.xt
    bread = np.linalg.inv(xt.T @ xt)
    w = xt @ bread[:, j]
    mz = spec.M - xt @ bread @ xt.T
    xr = np.delete(xt, j, axis=1)
    pr = xr @ np.linalg.solve(xr.T @ xr, xr.T)
    _, yt = spec.data(y)
    out = np.empty(len(yt))
    for r, yr in enumerate(yt):
        t0 = (w @ yr) / np.sqrt(((spec.C.T @ (w * (mz @ yr))) ** 2).sum())
        u = yr - pr @ yr
        num = spec.C.T @ (w * u)
        a = spec.C.T @ (w[:, None] * (mz @ (u[:, None] * spec.C)))
        v = rng.choice(WEBB, size=(spec.C.shape[1], n_boot))
        out[r] = (np.abs((num @ v) / np.sqrt(((a @ v) ** 2).sum(axis=0))) > abs(t0)).mean()
    return out

def ewc(x, y):
    """OLS of each row of y (R, T) on x (T, k) with equal-weighted cosine standard errors (Lazarus, Lewis, Stock
    and Watson 2018), nu = floor(0.4 T^(2/3)), variance scaled by T / (T - k); t(nu) critical values."""
    n, k = x.shape
    nu = max(1, int(0.4 * n ** (2 / 3)))
    bread = np.linalg.inv(x.T @ x)
    beta = y @ x @ bread
    z = x[None] * (y - beta @ x.T)[..., None]
    basis = np.sqrt(2 / n) * np.cos(np.pi * np.outer(np.arange(1, nu + 1), np.arange(n) + 0.5) / n)
    lam = np.einsum("jt,rtk->rjk", basis, z)
    var = n * bread @ (np.einsum("rjk,rjl->rkl", lam, lam) / nu) @ bread
    return beta, np.sqrt(np.diagonal(var, axis1=1, axis2=2) * n / (n - k)), nu
