"""Simulation check (plan, section 6): are the error bars honest for this panel, and what can it detect?

The fake panels keep everything real except the bank outcomes: the same countries, years and gaps, and the real
IMF macro data. The outcomes are pure noise built to behave like the real outcomes' noise once country and year
effects are removed: each country's own noise level, persistence from year to year, shocks shared by some
countries in the same year, and fat tails. The macro variables play no part in measuring that noise. Every true
effect is zero, so an interval covers the truth when it contains zero; because the design is fixed and the model
linear, the power against an effect d follows exactly from shifting the estimates by d."""
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter
from scipy import stats

from embanks import LABELS, md_table, panel
from embanks.inference import METHODS, PRIMARY, ewc, fit, wild_pvalues
from embanks.plots import GRID, INK2, MUTED, SURFACE, figure, finish, style
from embanks.regressions import armenia_rows, grid, specs

CANDIDATES = ["country cluster", "wild bootstrap", "two-way cluster", "Driscoll-Kraay"]  # listed in the plan

RHO, PHI = np.arange(0, 0.951, 0.05), np.arange(0, 0.901, 0.05)

NU = [np.inf, 30, 15, 10, 7, 5, 4, 3]

COLORS = {"roa": "#2a78d6", "nii_share": "#eb6834", "car": "#1baf7a", "asset_growth": "#eda100"}

def ar1(e, ar):
    """AR(1) series along the last axis from innovations `e`, started at its stationary distribution."""
    u = np.empty_like(e)
    u[..., 0] = e[..., 0] / np.sqrt(1 - ar ** 2)
    for t in range(1, e.shape[-1]):
        u[..., t] = ar * u[..., t - 1] + e[..., t]
    return u

def innovations(rng, shape, nu):
    """Unit-variance shocks: normal, or Student-t with nu degrees of freedom."""
    return rng.standard_normal(shape) if np.isinf(nu) else rng.standard_t(nu, shape) / np.sqrt(nu / (nu - 2))

def draw(rng, reps, scales, n_years, rho, phi, nu):
    """Noise on the grid, (reps, countries x years): each country's scale times a unit-variance mix of its own
    AR(1) shocks (share 1 - phi) and a shared AR(1) shock with a random country loading (share phi)."""
    own = ar1(np.sqrt(1 - rho ** 2) * innovations(rng, (reps, len(scales), n_years), nu), rho)
    shared = ar1(np.sqrt(1 - rho ** 2) * innovations(rng, (reps, 1, n_years), nu), rho)
    loading = rng.standard_normal((reps, len(scales), 1))
    e = scales[None, :, None] * (np.sqrt(1 - phi) * own + np.sqrt(phi) * loading * shared)
    return e.reshape(reps, -1)

def moments(r, spec):
    """Noise statistics of residuals r (S, n): year-to-year correlation, tail weight (kurtosis after scaling
    each country to unit size) and variance."""
    a, b = r[:, spec.pairs[0]], r[:, spec.pairs[1]]
    a, b = a - a.mean(axis=1, keepdims=True), b - b.mean(axis=1, keepdims=True)
    rms = np.sqrt((r ** 2) @ spec.C / spec.C.sum(axis=0))
    z = r / (rms @ spec.C.T)
    return {"lag1": (a * b).sum(axis=1) / np.sqrt((a ** 2).sum(axis=1) * (b ** 2).sum(axis=1)),
            "kurt": (z ** 4).mean(axis=1) / (z ** 2).mean(axis=1) ** 2, "var": (r ** 2).mean(axis=1)}

def cross(r, spec):
    """Mean absolute correlation between countries' residuals (pairs with at least 8 common years), per row."""
    out = []
    for row in r:
        c = pd.Series(row, spec.rows).unstack("country").corr(min_periods=8).to_numpy()
        out.append(np.nanmean(np.abs(c[np.triu_indices_from(c, 1)])))
    return np.array(out)

def calibrate(spec, y, countries, n_years, draws, seed):
    """Noise settings for one outcome, chosen so simulated residuals match the real ones (after country and
    year effects): persistence from the year-to-year correlation, the shared share from the cross-country
    correlation, the tails from the kurtosis, and the overall size from the variance."""
    r = spec.M @ y
    target = {k: v[0] for k, v in moments(r[None], spec).items()} | {"cross": cross(r[None], spec)[0]}
    rms = pd.Series(r).groupby(spec.rows.get_level_values("country")).apply(lambda v: np.sqrt((v ** 2).mean()))
    scales = rms.reindex(countries).fillna(rms.median()).to_numpy()

    def residuals(rho, phi=0.0, nu=np.inf):  # common random numbers across candidate settings
        return draw(np.random.default_rng(seed), draws, scales, n_years, rho, phi, nu)[:, spec.at] @ spec.M

    rho = min(RHO, key=lambda v: abs(moments(residuals(v), spec)["lag1"].mean() - target["lag1"]))
    phi = min(PHI, key=lambda v: abs(cross(residuals(rho, v), spec).mean() - target["cross"]))
    nu = min(NU, key=lambda v: abs(moments(residuals(rho, phi, v), spec)["kurt"].mean() - target["kurt"]))
    r_sim = residuals(rho, phi, nu)
    fitted = {k: v.mean() for k, v in moments(r_sim, spec).items()} | {"cross": cross(r_sim, spec).mean()}
    size = np.sqrt(target["var"] / fitted["var"])
    fitted["var"] *= size ** 2
    return {"scales": size * scales, "rho": rho, "phi": phi, "nu": nu, "target": target, "fitted": fitted}

def scenario(all_specs, params, n_years, reps, wild, n_boot, seed):
    """Coverage of each method for every reported coefficient; the draws' estimates are kept for power."""
    rows, kept = [], {}
    seeds = seed.spawn(2 * len(panel.OUTCOMES))
    for i, outcome in enumerate(panel.OUTCOMES):
        p = params[outcome]
        y = draw(np.random.default_rng(seeds[2 * i]), reps, p["scales"], n_years, p["rho"], p["phi"], p["nu"])
        boot = np.random.default_rng(seeds[2 * i + 1])
        for spec in (s for s in all_specs if s.outcome == outcome):
            beta, se, df = fit(spec, y)
            for j, name in zip(spec.j, spec.focus):
                b = beta[:, j]
                for m in METHODS:
                    covered = np.abs(b) <= stats.t.ppf(0.975, df[m]) * se[m][:, j]
                    rows.append({"spec": spec.kind, "outcome": outcome, "coefficient": name, "method": m,
                                 "coverage": covered.mean()})
                if spec.lag is None and wild:
                    p_values = wild_pvalues(spec, y[:wild], j, boot, n_boot)
                    rows.append({"spec": spec.kind, "outcome": outcome, "coefficient": name,
                                 "method": "wild bootstrap", "coverage": (p_values >= 0.05).mean()})
                kept[spec.kind, outcome, name] = (b, {m: v[:, j] for m, v in se.items()}, df, spec.xt[:, j].std())
    return pd.DataFrame(rows), kept

def detectable(b, se, crit, power=0.8):
    """Smallest effect rejected (|estimate| > crit x SE) in at least `power` of the draws."""
    shifts = np.linspace(0, 40, 4001) * np.nanmedian(se)
    reject = (np.abs(b[None] + shifts[:, None]) > crit * se[None]).mean(axis=1)
    return shifts[np.argmax(reject >= power)] if (reject >= power).any() else np.nan

def armenia_alone(a, params, reps, seed):
    """Armenia on its own (plan, section 8), on simulated noise: the size of Armenia's own outcome around its mean
    (no year effects to remove it) and the panel's persistence. Without the T / (T - k) factor in `ewc`, 13-15
    years and five coefficients make the residuals look smaller than the noise."""
    rng, rows = np.random.default_rng(seed), []
    for outcome in panel.OUTCOMES:
        d = armenia_rows(a, outcome)
        n = len(d)
        x = np.column_stack([np.ones(n), d[panel.REGRESSORS].to_numpy()])
        rho = params[outcome]["rho"]
        e = d[outcome].std() * ar1(np.sqrt(1 - rho ** 2) * rng.standard_normal((reps, n)), rho)
        beta, se, nu = ewc(x, e)
        crit = stats.t.ppf(0.975, nu)
        for j, name in enumerate(panel.REGRESSORS, start=1):
            rows.append({"outcome": outcome, "coefficient": name, "years": n, "nu": nu,
                         "coverage": (np.abs(beta[:, j]) <= crit * se[:, j]).mean(),
                         "detectable": detectable(beta[:, j], se[:, j], crit)})
    return pd.DataFrame(rows)

def decide(cov):
    """The plan's rule: keep country clustering unless it covers under 90% for some coefficient; then the
    best-covering listed method (by its worst coefficient) becomes primary."""
    out = {}
    for family, d in (("main and dollar-lending", cov[cov.spec.isin(["Q1", "Q2"])]),
                      ("local projections", cov[cov.spec.str.startswith("LP")])):
        worst = d.groupby("method").coverage.min()
        out[family] = (PRIMARY if worst[PRIMARY] >= 0.90 else worst.reindex(CANDIDATES).idxmax(), worst)
    return out

def plot_coverage(cov, path):
    """Strip plot: one dot per coefficient and method, colored by outcome, for the calibrated noise."""
    size = (12, 5.6)
    fig, axes = figure("Simulated outcomes on the real panel: how often 95% intervals contain the truth",
                       "One dot per coefficient; noise like the real outcomes', no true effects. Honest methods sit "
                       "on the 95% line; the plan switches methods if the primary one falls below 90%.", 1, 2, size)
    order = ["unadjusted", "country cluster", "wild bootstrap", "two-way cluster", "Driscoll-Kraay"]
    jitter = np.random.default_rng(0)
    lo = np.floor((cov.coverage.min() - 0.03) * 20) / 20
    for ax, (title, d) in zip(axes[0], (("Main and dollar-lending regressions", cov[cov.spec.isin(["Q1", "Q2"])]),
                                        ("Effects 0-2 years ahead (local projections)",
                                         cov[cov.spec.str.startswith("LP")]))):
        methods = [m for m in order if m in set(d.method)]
        for outcome, color in COLORS.items():
            for i, m in enumerate(methods):
                v = d[(d.method == m) & (d.outcome == outcome)].coverage
                ax.scatter(v, i + jitter.uniform(-0.2, 0.2, len(v)), s=26, color=color, edgecolor=SURFACE,
                           linewidth=1, zorder=3, label=LABELS[outcome] if i == 0 else None)
        for level, text, side in ((0.95, " 95% target", "left"), (0.90, "90%: switch ", "right")):
            ax.axvline(level, color=MUTED, linewidth=1)
            ax.text(level, -0.5, text, color=INK2, fontsize=7, ha=side, va="center")
        ax.set_yticks(range(len(methods)), methods)
        ax.set_ylim(len(methods) - 0.4, -0.75)
        ax.set_xlim(lo, 1.0)
        ax.set_title(title, color=INK2, fontsize=9, loc="left")
        ax.set_xlabel("share of simulated panels whose interval contains the truth", color=INK2, fontsize=9)
        style(ax)
    finish(fig, axes[0, 0], path, size[1], 0.86, ncol=4)

def plot_detectable(power, path, armenia_years):
    """Dumbbells: smallest effect detectable 80% of the time, panel against Armenia alone (log scale)."""
    size = (12, 4.6)
    fig, axes = figure("Simulated outcomes on the real panel: the smallest effect each design can detect",
                       "Change in the outcome per 1-point change in each macro variable, detected 80% of the time "
                       "at 5% (log scale; smaller is better).", 1, 4, size)
    for ax, outcome in zip(axes[0], panel.OUTCOMES):
        d = power[power.outcome == outcome].set_index("coefficient").loc[panel.REGRESSORS]
        ys = np.arange(len(d))
        ax.hlines(ys, d.panel, d.armenia, color=GRID, linewidth=2, zorder=1)
        ax.scatter(d.armenia, ys, s=40, color="#2a78d6", edgecolor=SURFACE, linewidth=1.5, zorder=3,
                   label=f"Armenia alone ({armenia_years} years)")
        ax.scatter(d.panel, ys, s=40, color="#eb6834", edgecolor=SURFACE, linewidth=1.5, zorder=3,
                   label="Panel of 38 emerging economies")
        ax.set_xscale("log")
        ax.xaxis.set_major_locator(LogLocator(base=10, subs=(1, 2, 5)))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.set_yticks(ys, [LABELS[c] for c in d.index])
        ax.set_ylim(len(d) - 0.5, -0.5)
        ax.set_title(f"{LABELS[outcome]} (points)", color=INK2, fontsize=9, loc="left")
        style(ax)
        if outcome != panel.OUTCOMES[0]:
            ax.set_yticklabels([])
    finish(fig, axes[0, 0], path, size[1], 0.78)

def report(cfg, params, cov, stress, decision, power, alone, reps, wild):
    """Write outputs/simulation_check.md."""
    sim = cfg["simulation"]
    calib = pd.DataFrame([{"outcome": LABELS[o],
                           "year-to-year corr. (real / sim.)": f"{p['target']['lag1']:.2f} / {p['fitted']['lag1']:.2f}",
                           "cross-country |corr.| (real / sim.)": f"{p['target']['cross']:.2f} / {p['fitted']['cross']:.2f}",
                           "tail weight (real / sim.)": f"{p['target']['kurt']:.1f} / {p['fitted']['kurt']:.1f}",
                           "persistence": p["rho"], "shared share": p["phi"],
                           "tails (t df)": "normal" if np.isinf(p["nu"]) else f"{p['nu']:.0f}"}
                          for o, p in params.items()])
    order = ["unadjusted", "country cluster", "wild bootstrap", "two-way cluster", "Driscoll-Kraay"]

    def table(d):
        t = d.pivot_table(index=["outcome", "coefficient"], columns="method", values="coverage", sort=False)
        t = t.reindex(columns=[m for m in order if m in t.columns])
        return t.rename(index=LABELS).rename_axis(columns=None)

    lp = cov[cov.spec.str.startswith("LP")].groupby(["spec", "method"]).coverage.agg(["min", "mean"])
    lp = lp.unstack("method").swaplevel(axis=1).sort_index(axis=1)
    lp = pd.DataFrame({f"{m} (worst / mean)": lp[m].apply(lambda r: f"{r['min']:.3f} / {r['mean']:.3f}", axis=1)
                       for m in order if m in lp.columns.get_level_values(0)})
    worst = pd.DataFrame({name: d[d.spec.isin(["Q1", "Q2"])].groupby("method").coverage.min()
                          for name, d in {"calibrated": cov, **stress}.items()}).T.reindex(columns=order)
    lines = [f"- **{family}:** worst coverage of country clustering {w[PRIMARY]:.3f}; "
             + (f"it stays primary." if choice == PRIMARY else f"**{choice} becomes primary** (worst {w[choice]:.3f}).")
             for family, (choice, w) in decision.items()]
    worst_alone = alone.loc[alone.coverage.idxmin()]
    pw = power.assign(outcome=power.outcome.map(LABELS), coefficient=power.coefficient.map(LABELS)
                      .where(power.coefficient != "fx_x_share", LABELS["fx_x_share (per 10 points)"]))
    text = f"""# Simulation check: are the error bars honest for this panel?

*Simulated bank outcomes on the real panel.* The countries, years, gaps and IMF macro data are real; the bank
outcomes are made up, with no true effects, and noise built to behave like the real outcomes' noise. Run before
any estimate, as the plan requires (`docs/plan.md`, section 6). {reps} simulated panels per
setting; the wild bootstrap uses the first {wild} with {sim["wild_bootstrap"]["B"]} draws each.

## The noise

For each outcome, the real values are stripped of country and year effects (no macro variable is used), and the
simulated noise is tuned until it matches what is left: each country keeps its own noise level, and three
settings are chosen to match the statistics below. "Persistence" is the year-to-year correlation of a country's
shocks; "shared share" is the part of the noise that comes from a shock some countries share in a year, with
country-specific exposure that the year effects cannot remove; "tails" sets how often extreme years occur.

{md_table(calib, fmt="{:.2f}", index=False)}

## Coverage with this noise

Share of simulated panels whose 95% interval contains the true value (honest = 0.95; with {reps} panels, about
+/- {2 * np.sqrt(0.95 * 0.05 / reps):.3f} is simulation noise; +/- {2 * np.sqrt(0.95 * 0.05 / wild):.3f} for the wild
bootstrap).

**Main regressions (question 1) and dollar lending (question 2, the last line of each outcome):**

{md_table(table(cov[cov.spec.isin(["Q1", "Q2"])]), fmt="{:.3f}")}

**Effects over time** (local projections; worst and mean over the 16 outcome-variable pairs at each horizon):

{md_table(lp.rename_axis("horizon"))}

**With one feature of the noise pushed harder** (worst coverage over the 20 coefficients of questions 1 and 2):

{md_table(worst.rename_axis("noise"), fmt="{:.3f}")}

## Decision (fixed in the plan before this check)

{chr(10).join(lines)}

## What the panel can detect

The smallest effect found 80% of the time at the 5% level with the primary method, per 1-point change in the
macro variable, against Armenia on its own (its years from 2005, equal-weighted cosine intervals). "Typical
swing" is the standard deviation of the macro variable once country and year effects are removed. The
dollar-lending line is the extra effect of a 1-point depreciation where 10 points more of loans are in foreign
currency; Armenia alone has no counterpart. Armenia's own intervals rest on {alone.years.min()}-{alone.years.max()}
years and {alone.nu.max()} degrees of freedom; even with the small-sample correction they cover
{alone.coverage.min():.2f} to {alone.coverage.max():.2f} (worst: {LABELS[worst_alone.coefficient]} for
{LABELS[worst_alone.outcome]}, {worst_alone.years} years).

{md_table(pw[["outcome", "coefficient", "panel", "typical swing", "armenia", "times larger"]].rename(columns={
        "panel": "panel", "armenia": "Armenia alone"}), fmt="{:.3g}", index=False)}
"""
    out = cfg["paths"]["outputs"]
    (out / "simulation_check.md").write_text(text)

def run(cfg, a, samples):
    """Calibrate the noise, run the calibrated and stress settings, apply the plan's rule, write the outputs."""
    sim = cfg["simulation"]
    reps = sim["reps_quick"] if cfg["quick"] else sim["reps"]
    wild = sim["wild_bootstrap"]["reps_quick" if cfg["quick"] else "reps"]
    countries = samples["main"]
    n_years = len(grid(countries, cfg).get_level_values("year").unique())
    all_specs = specs(a, cfg, countries)
    seeds = np.random.SeedSequence([cfg["seed"], 2]).spawn(3 + len(sim["stress"]))
    q1 = {s.outcome: s for s in all_specs if s.kind == "Q1"}
    draws = max(20, sim["calibration_draws"] // (3 if cfg["quick"] else 1))
    params = {y: calibrate(q1[y], a[y].reindex(q1[y].rows).to_numpy(), countries, n_years, draws,
                           seeds[0].generate_state(1)[0]) for y in panel.OUTCOMES}
    cov, kept = scenario(all_specs, params, n_years, reps, wild, sim["wild_bootstrap"]["B"], seeds[1])
    stress = {name: scenario(all_specs, {y: {**p, **change} for y, p in params.items()}, n_years, reps, wild,
                             sim["wild_bootstrap"]["B"], seeds[3 + i])[0]
              for i, (name, change) in enumerate(sim["stress"].items())}
    decision = decide(cov)
    alone = armenia_alone(a, params, reps, seeds[2])
    rows = []
    for (kind, outcome, name), (b, se, df, swing) in kept.items():
        if kind in ("Q1", "Q2"):   # the dollar-lending coefficient per 10 points of foreign-currency lending
            unit = 10 if kind == "Q2" else 1
            rows.append({"outcome": outcome, "coefficient": name, "typical swing": swing if unit == 1 else np.nan,
                         "panel": unit * detectable(b, se[PRIMARY], stats.t.ppf(0.975, df[PRIMARY]))})
    power = pd.DataFrame(rows).merge(alone.rename(columns={"detectable": "armenia"})[
        ["outcome", "coefficient", "armenia"]], on=["outcome", "coefficient"], how="left")
    power["times larger"] = power.armenia / power.panel
    out = cfg["paths"]["outputs"]
    plot_coverage(cov, out / "simulation_coverage.png")
    plot_detectable(power, out / "simulation_detectable.png", f"{alone.years.min()}-{alone.years.max()}")
    report(cfg, params, cov, stress, decision, power, alone, reps, wild)
    return params, cov, stress, decision, power, alone
