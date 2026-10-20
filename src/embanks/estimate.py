"""Estimation (plan, sections 3-9): the question answered on the real panel.

Real data from the IMF; findings about real economies. Every choice was fixed in docs/plan.md before any
estimate was computed; the primary error bars (clustered by
country) were confirmed by the simulation check, and each main regression is re-run in linearmodels as a check.
"""
import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS
from matplotlib.ticker import MaxNLocator
from scipy import stats

from embanks import LABELS, md_table, panel, regressions
from embanks.inference import METHODS, ewc, fit, wild_pvalues
from embanks.plots import GRID, INK2, MUTED, SURFACE, figure, finish, style

BLUE = "#2a78d6"
FOCUS = [*panel.REGRESSORS, "fx_x_share"]


def outcomes(a, cfg, countries):
    """Each real outcome on the simulation grid, shaped (1, grid) like one simulated draw."""
    g = regressions.grid(countries, cfg)
    return {y: a[y].reindex(g).to_numpy(float)[None] for y in panel.OUTCOMES}


def crosscheck(spec, y, method):
    """Re-run a Q1 or Q2 regression in linearmodels; estimates and primary standard errors must agree."""
    d = spec.x.assign(y=y[0, spec.at])
    kw = dict(cov_type="clustered", cluster_entity=True, group_debias=True)
    if method == "two-way cluster":
        kw["cluster_time"] = True
    res = PanelOLS(d.y, d[spec.names], entity_effects=True, time_effects=True).fit(debiased=True, **kw)
    beta, se, _ = fit(spec, y)
    assert np.allclose(res.params, beta[0], rtol=1e-6), spec.kind
    assert np.allclose(res.std_errors, se[method][0], rtol=1e-6), spec.kind


def estimate(all_specs, ys, methods, rng=None, n_boot=0):
    """Estimate, 95% interval (primary method, t critical values) and p-values for every reported coefficient;
    wild cluster restricted bootstrap p-values for Q1 and Q2 when n_boot > 0. `methods` is one method, or the
    simulation check's choice per family of regressions."""
    rows = []
    for spec in all_specs:
        y = ys[spec.outcome]
        method = methods if isinstance(methods, str) else methods[
            "local projections" if spec.kind.startswith("LP") else "main and dollar-lending"]
        beta, se, df = fit(spec, y)
        for j, name in zip(spec.j, spec.focus):
            b = beta[0, j]
            half = stats.t.ppf(0.975, df[method]) * se[method][0, j]
            row = {"spec": spec.kind, "outcome": spec.outcome, "coefficient": name, "estimate": b,
                   "lo": b - half, "hi": b + half, "rows": len(spec.rows), "countries": spec.C.shape[1]}
            row |= {f"p {m}": 2 * stats.t.sf(abs(b) / se[m][0, j], df[m]) for m in METHODS}
            if n_boot and spec.lag is None:
                row["p wild"] = wild_pvalues(spec, y, j, rng, n_boot)[0]
            rows.append(row)
    return pd.DataFrame(rows)


def holm(p):
    """Holm-adjusted p-values."""
    order = np.argsort(p)
    adjusted = np.maximum.accumulate((len(p) - np.arange(len(p))) * np.asarray(p)[order])
    out = np.empty(len(p))
    out[order] = np.minimum(adjusted, 1)
    return out


def scales(all_specs, ys):
    """Typical swing of each macro variable (SD once country and year effects are removed) and the outcome's
    within-country SD, from the main Q1 samples. The dollar-lending term is scaled to a typical depreciation
    where 10 points more of loans are in foreign currency."""
    out = {}
    for spec in (s for s in all_specs if s.kind == "Q1"):
        sd_y = spec.data(ys[spec.outcome])[1][0].std()
        swing = dict(zip(spec.names, spec.xt.std(axis=0)))
        for name in panel.REGRESSORS:
            out[spec.outcome, name] = (swing[name], sd_y)
        out[spec.outcome, "fx_x_share"] = (10 * swing["fx_change"], sd_y)
    return out


def read(row, small):
    """The plan's three readings (section 9), with the small-effect threshold fixed in config.yaml."""
    lo, hi, sd_y = row["lo_s"], row["hi_s"], row["sd_y"]
    if lo > 0 or hi < 0:   # sized against the same threshold: small if inside the "not large" zone
        size = "small" if abs(row["effect"]) < small * sd_y else "large"
        return f"relationship, {size}: {'higher' if lo > 0 else 'lower'} ({row['effect']:+.2f} per typical swing)"
    bound = max(abs(lo), abs(hi))
    return (f"no large effect (rules out more than {bound:.2f})" if bound < small * sd_y
            else f"can't tell (could be up to {bound:.2f})")


def variants(a, samples):
    """The plan's robustness checks 1-5 (check 6 needs a download that was not requested)."""
    main = samples["main"]
    reporting = a.income_reporting.groupby(level="country").first()
    years = a.index.get_level_values("year")
    return {"stricter sample": (samples["strict"], None),
            "keep high inflation": (main, pd.Series(False, index=a.index)),
            "drop BLR, POL": ([c for c in main if reporting.get(c) != "other"], None),
            "drop 2020-21": (main, a.high_inflation | pd.Series(np.isin(years, [2020, 2021]), index=a.index))}


def robustness(a, cfg, samples, method):
    """Q1 and Q2 estimates under each robustness check, and the range when each country is left out in turn."""
    cols = {}
    for name, (countries, drop) in variants(a, samples).items():
        sp = [s for s in regressions.specs(a, cfg, countries, drop, horizons=[])]
        cols[name] = estimate(sp, outcomes(a, cfg, countries), method)
    loo = []
    for c in samples["main"]:
        rest = [k for k in samples["main"] if k != c]
        loo.append(estimate(regressions.specs(a, cfg, rest, horizons=[]), outcomes(a, cfg, rest), method))
    loo = pd.concat(loo).groupby(["spec", "outcome", "coefficient"], sort=False).estimate.agg(["min", "max"])
    return cols, loo


def armenia(a, cfg, samples, method):
    """Armenia alone (equal-weighted cosine intervals), and how well the panel estimated without Armenia predicts
    Armenia's year-to-year changes from its own macro data."""
    alone = []
    for outcome in panel.OUTCOMES:
        d = regressions.armenia_rows(a, outcome)
        x = np.column_stack([np.ones(len(d)), d[panel.REGRESSORS].to_numpy()])
        beta, se, nu = ewc(x, d[outcome].to_numpy()[None])
        half = stats.t.ppf(0.975, nu) * se[0]
        for j, name in enumerate(panel.REGRESSORS, start=1):
            alone.append({"outcome": outcome, "coefficient": name, "estimate": beta[0, j],
                          "lo": beta[0, j] - half[j], "hi": beta[0, j] + half[j], "years": len(d), "nu": nu})
    rest = [c for c in samples["main"] if c != "ARM"]
    fit = estimate([s for s in regressions.specs(a, cfg, rest, horizons=[]) if s.kind == "Q1"],
                   outcomes(a, cfg, rest), method).set_index(["outcome", "coefficient"]).estimate
    tracking = []
    for outcome in panel.OUTCOMES:
        d = regressions.armenia_rows(a, outcome)
        step = d.index.to_series().diff() == 1
        dy = d[outcome].diff()[step]
        pred = d[panel.REGRESSORS].diff()[step] @ fit.loc[outcome].reindex(panel.REGRESSORS).to_numpy()
        tracking.append({"outcome": LABELS[outcome], "year-to-year changes": int(step.sum()),
                         "correlation": np.corrcoef(pred, dy)[0, 1],
                         "same direction": f"{int((np.sign(pred) == np.sign(dy)).sum())} of {int(step.sum())}",
                         "share of variation explained": 1 - ((dy - pred) ** 2).sum() / ((dy - dy.mean()) ** 2).sum()})
    return pd.DataFrame(alone), pd.DataFrame(tracking)


def cell(est, lo, hi, digits=3):
    """'estimate [lo, hi]', bold when the interval excludes zero."""
    text = f"{est:.{digits}f} [{lo:.{digits}f}, {hi:.{digits}f}]"
    return f"**{text}**" if lo > 0 or hi < 0 else text


def plot_main(res, path):
    """Forest plot per outcome: effect of a typical swing with its 95% interval; the small-effect zone shaded."""
    size = (12, 4.8)
    fig, axes = figure("Real data, 38 emerging economies, 2008-2025: how bank outcomes move with the economy",
                       "Change in each outcome when the macro variable is one typical swing above its usual level, "
                       "95% intervals clustered by country. Shaded: smaller than a quarter of the outcome's usual "
                       "variation (the plan's threshold).",
                       1, 4, size)
    for ax, outcome in zip(axes[0], panel.OUTCOMES):
        d = res[res.outcome == outcome].set_index("coefficient").loc[FOCUS]
        ys = np.arange(len(d))
        band = d.small_zone.iloc[0]
        ax.axvspan(-band, band, color=GRID, alpha=0.6, linewidth=0, zorder=0)
        ax.axvline(0, color=MUTED, linewidth=1, zorder=1)
        ax.hlines(ys, d.lo_s, d.hi_s, color=BLUE, linewidth=2, zorder=2)
        ax.scatter(d.effect, ys, s=40, color=BLUE, edgecolor=SURFACE, linewidth=1.5, zorder=3)
        ax.set_yticks(ys, ["GDP growth", "Inflation", "Policy rate", "Dollar exchange rate",
                           "Depreciation x 10 pts\nmore FX lending"])
        ax.set_ylim(len(d) - 0.5, -0.5)
        ax.set_title(f"{LABELS[outcome]} (points)", color=INK2, fontsize=9, loc="left")
        ax.xaxis.set_major_locator(MaxNLocator(5))
        style(ax)
        if outcome != panel.OUTCOMES[0]:
            ax.set_yticklabels([])
    finish(fig, axes[0, 0], path, size[1], 0.84)


def plot_paths(lp, path):
    """Local projections: effect of a typical swing 0, 1 and 2 years ahead, one panel per outcome and variable."""
    size = (12, 9)
    fig, axes = figure("Real data: how the effects unfold over two years",
                       "Change in each outcome h years after a typical swing in the macro variable (local "
                       "projections), 95% intervals clustered by country.", 4, 4, size)
    for i, outcome in enumerate(panel.OUTCOMES):
        for k, name in enumerate(panel.REGRESSORS):
            ax = axes[i, k]
            d = lp[(lp.outcome == outcome) & (lp.coefficient == name)].sort_values("h")
            ax.axhline(0, color=MUTED, linewidth=1)
            ax.vlines(d.h, d.lo_s, d.hi_s, color=BLUE, linewidth=2)
            ax.plot(d.h, d.effect, color=BLUE, linewidth=1.5, marker="o", markersize=6, markeredgecolor=SURFACE,
                    markeredgewidth=1.5)
            ax.set_xticks([0, 1, 2])
            ax.set_xlim(-0.4, 2.4)
            style(ax)
            if i == 0:
                ax.set_title(LABELS[name], color=INK2, fontsize=9, loc="left")
            if k == 0:
                ax.set_ylabel(LABELS[outcome], color=INK2, fontsize=9)
            if i == len(panel.OUTCOMES) - 1:
                ax.set_xlabel("years ahead", color=INK2, fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(path, dpi=160, facecolor=SURFACE)


def run(cfg, a, samples, power, methods):
    """Estimate everything the plan lists and write outputs/results.md with two figures.

    `methods` maps each family of regressions to the error-bar method the simulation check kept as primary."""
    if not set(methods.values()) <= set(METHODS):
        raise NotImplementedError("intervals by bootstrap inversion are not implemented")
    method = methods["main and dollar-lending"]
    cc = cfg
    main = samples["main"]
    all_specs = regressions.specs(a, cfg, main)
    ys = outcomes(a, cfg, main)
    for spec in (s for s in all_specs if s.kind in ("Q1", "Q2")):
        crosscheck(spec, ys[spec.outcome], method)
    rng = np.random.default_rng(np.random.SeedSequence([cfg["seed"], 3]))
    res = estimate(all_specs, ys, methods, rng, cc["reading"]["wild_bootstrap_B"])
    sc = scales(all_specs, ys)
    res["swing"] = [sc[o, c][0] for o, c in zip(res.outcome, res.coefficient)]
    res["sd_y"] = [sc[o, c][1] for o, c in zip(res.outcome, res.coefficient)]
    res = res.assign(effect=res.estimate * res.swing, lo_s=res.lo * res.swing, hi_s=res.hi * res.swing,
                     small_zone=cc["reading"]["small_effect_sd"] * res.sd_y)
    q = res[res.spec.isin(["Q1", "Q2"])].copy()
    q["reading"] = [read(r, cc["reading"]["small_effect_sd"]) for r in q.to_dict("records")]
    q1 = q.spec == "Q1"
    q.loc[q1, "Holm p"] = holm(q.loc[q1, "p wild"].to_numpy())
    mde = power.set_index(["outcome", "coefficient"]).panel
    q["detectable"] = [mde.get((o, c), np.nan) / (10 if c == "fx_x_share" else 1)
                       for o, c in zip(q.outcome, q.coefficient)]
    lp = res[res.spec.str.startswith("LP")].assign(h=lambda d: d.spec.str[-1].astype(int))
    q1 = {sp.outcome: sp for sp in all_specs if sp.kind == "Q1"}
    rows = q1["asset_growth"].rows
    swing_fx = sc["asset_growth", "fx_change"][0]
    share = a.fx_loan_share_lag.reindex(rows).mean()
    roa = a.roa.reindex(q1["roa"].rows).mean()
    context = {"share": share, "swing_fx": swing_fx, "revalue": share / 100 * swing_fx,
               "roa": roa, "roa_mech": roa * share / 100 * swing_fx / 100,
               "lp_bold": int(((lp.lo > 0) | (lp.hi < 0)).sum()), "lp_n": len(lp)}
    cols, loo = robustness(a, cfg, samples, method)
    alone, tracking = armenia(a, cfg, samples, method)
    out = cfg["paths"]["outputs"]
    plot_main(q, out / "results_main.png")
    plot_paths(lp, out / "results_over_time.png")
    write(cfg, q, lp, cols, loo, alone, tracking, methods, context)
    return q, lp, cols, loo, alone, tracking


def write(cfg, q, lp, cols, loo, alone, tracking, methods, context):
    """Write outputs/results.md."""
    small = cfg["reading"]["small_effect_sd"]
    main = pd.DataFrame([{"outcome": LABELS[r["outcome"]],
                          "macro variable": ("Depreciation x 10 pts more FX lending" if r["coefficient"] == "fx_x_share"
                                             else LABELS[r["coefficient"]]),
                          "per 1 point [95% interval]": cell(r["estimate"], r["lo"], r["hi"]),
                          "per typical swing": cell(r["effect"], r["lo_s"], r["hi_s"], 2),
                          "bootstrap p": r["p wild"], "Holm p": r["Holm p"],
                          "smallest detectable": r["detectable"], "reading": r["reading"]}
                         for r in q.to_dict("records")])
    paths = lp.assign(text=[cell(e, lo, hi, 2) for e, lo, hi in zip(lp.effect, lp.lo_s, lp.hi_s)]).pivot_table(
        index=["outcome", "coefficient"], columns="h", values="text", aggfunc="first", sort=False)
    paths = paths.rename(index=LABELS).rename(columns=lambda h: f"{h} years ahead").rename_axis(columns=None)
    rob = q.set_index(["spec", "outcome", "coefficient"])[["estimate", "lo", "hi"]]
    table = pd.DataFrame({"main": [cell(*v) for v in rob.to_numpy()]}, index=rob.index)
    for name, d in cols.items():
        d = d.set_index(["spec", "outcome", "coefficient"])[["estimate", "lo", "hi"]].reindex(rob.index)
        table[name] = [cell(*v) for v in d.to_numpy()]
    table["leave one country out"] = [f"{lo:.3f} to {hi:.3f}" for lo, hi in loo.reindex(rob.index).to_numpy()]
    table = table.droplevel("spec").rename(index=LABELS).rename(index={"fx_x_share": "FX change x FX-loan share"})
    arm = alone.assign(outcome=alone.outcome.map(LABELS), coefficient=alone.coefficient.map(LABELS),
                       interval=[cell(e, lo, hi) for e, lo, hi in zip(alone.estimate, alone.lo, alone.hi)])
    panel_cells = q[q.spec == "Q1"].set_index(["outcome", "coefficient"])
    arm["panel"] = [cell(*panel_cells.loc[(o, c), ["estimate", "lo", "hi"]])
                    for o, c in zip(alone.outcome, alone.coefficient)]
    groups = {k: [f"{a} - {b}" + (" (small)" if ", small" in r else "")
                  for a, b, r in zip(main.outcome, main["macro variable"], main.reading) if r.startswith(k)]
              for k in ("relationship", "no large effect", "can't tell")}
    asset_fx = q.set_index(["outcome", "coefficient"]).loc[("asset_growth", "fx_change")]
    roa_fx = q.set_index(["outcome", "coefficient"]).loc[("roa", "fx_change")]

    def share_of(mech, row):   # where a mechanical effect sits relative to the estimate's interval
        lo, hi = sorted((row.lo_s, row.hi_s))
        return ("within the interval, so it could account for the whole estimate" if lo <= mech <= hi
                else "outside the interval, so it accounts for only part of the estimate")
    n = q[q.spec == "Q1"].groupby("outcome")[["rows", "countries"]].first()
    text = f"""# Results: the original question on real data

*Real data from the IMF, 2008-2025; findings about real economies, not simulated.* Every choice below was fixed
before any estimate was computed (`docs/plan.md`). Error bars: {methods["main and dollar-lending"]}
for the main and dollar-lending regressions and {methods["local projections"]} for effects over time, as the
simulation check selected (`simulation_check.md`); each main regression was re-run in linearmodels and agrees.

Sample: {n.countries.max()} emerging and developing economies; {", ".join(f"{LABELS[o]} {r} country-years"
for o, r in n.rows.items())}; the 11 country-years with inflation above 40% are left out (a robustness check keeps
them). Each regression has country and year effects. Read the estimates as associations, not causal effects.

## In short

A **typical swing** is how far a macro variable usually moves from its normal level for that country, once
shocks shared by every emerging economy that year are removed (GDP growth about 2.6 points, inflation 2.9,
policy rate 3.0, dollar exchange rate 7.8). Readings follow the plan: a relationship when the 95% interval
excludes zero; "no large effect" when it includes zero but rules out a typical swing moving the outcome by more
than {small} of its within-country standard deviation; otherwise the data cannot tell. A relationship is called
small when its estimated effect falls inside that same band.

- **Relationships ({len(groups["relationship"])}):** {"; ".join(groups["relationship"]) or "none"}.
- **No large effect ({len(groups["no large effect"])}):** {"; ".join(groups["no large effect"]) or "none"}.
- **Cannot tell ({len(groups["can't tell"])}):** {"; ".join(groups["can't tell"]) or "none"}.

## Mechanical links to keep in mind

Some of these relationships are partly built into how the variables are measured:

- **The dollar and bank assets.** Assets are measured in local currency, so a depreciation raises the value of
  foreign-currency assets without any new lending. With {context["share"]:.0f}% of loans in foreign currency on
  average, a typical depreciation ({context["swing_fx"]:.1f}%) would by revaluation alone raise measured assets by
  about {context["revalue"]:.1f}% (loans only; other foreign-currency assets add to it), against the estimated
  {asset_fx.effect:.1f} points [{asset_fx.lo_s:.1f}, {asset_fx.hi_s:.1f}]: {share_of(context["revalue"], asset_fx)}.
  The over-time results show part of it reversing.
- **The dollar and ROA.** The same revaluation enlarges ROA's denominator: at an average ROA of
  {context["roa"]:.2f}%, that alone would lower ROA by about {context["roa_mech"]:.2f} points for a typical depreciation,
  against the estimated {roa_fx.effect:.2f} [{roa_fx.lo_s:.2f}, {roa_fx.hi_s:.2f}]: {share_of(-context["roa_mech"], roa_fx)}.
  The point estimate is larger, which leans toward lower profits as well, but the data cannot settle it.
- **Inflation and real asset growth.** Real growth is nominal growth minus inflation, so when balance sheets lag
  prices, real growth falls with inflation on impact; the over-time results show it recovering after two years.
- **Many tests.** The over-time results contain {context["lp_n"]} coefficients; {context["lp_bold"]} have intervals
  excluding zero, against about {0.05 * context["lp_n"]:.1f} expected by chance alone. Read them as patterns, not
  as separate findings.

## Main results (question 1) and dollar lending (question 2)

Bold: the 95% interval excludes zero. "Bootstrap p": wild cluster restricted bootstrap by country (9,999 draws);
"Holm p" adjusts it for testing 16 coefficients. "Smallest detectable": the effect per 1 point this panel finds
80% of the time (simulation check). Units: points of the outcome (ROA, capital ratio and the non-interest-income
share in percent; asset growth in log points x 100). The dollar-lending line is the extra effect of a 1-point
depreciation where 10 points more of loans are in foreign currency (per typical swing: a typical depreciation).

{md_table(main, fmt={"bootstrap p": "{:.3f}", "Holm p": "{:.3f}", "smallest detectable": "{:.3g}"}, index=False)}

![Main results](results_main.png)

## How the effects unfold

Change in each outcome 0, 1 and 2 years after a typical swing, controlling for last year's outcome and macro
variables (local projections). Bold: the interval excludes zero.

{md_table(paths)}

![Over time](results_over_time.png)

## Robustness (plan, section 7)

Per-1-point estimates with 95% intervals; bold excludes zero. Check 6 (a market interest rate where the policy
rate is missing) needs another download and was not run.

{md_table(table)}

## Armenia (plan, section 8)

**Armenia alone**, against the panel (per 1 point, 95% intervals). Armenia's own intervals use the method for short
series (equal-weighted cosine, t critical values with {alone.nu.max()} degrees of freedom), on {alone.years.min()}
to {alone.years.max()} years.

{md_table(arm[["outcome", "coefficient", "years", "interval", "panel"]].rename(
        columns={"interval": "Armenia alone", "panel": "38-country panel"}), index=False)}

**Does the emerging-market pattern describe Armenia?** The panel estimated without Armenia, applied to Armenia's
own year-to-year changes in the four macro variables (no Armenian data used to fit it):

{md_table(tracking, fmt="{:.2f}", index=False)}
"""
    (cfg["paths"]["outputs"] / "results.md").write_text(text)
