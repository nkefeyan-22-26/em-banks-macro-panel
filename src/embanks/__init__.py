"""Emerging-market banks and the macroeconomy: a cross-country panel built from public IMF data."""
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]

LABELS = {"roa": "ROA", "nii_share": "Non-interest income share", "car": "Capital ratio",
          "asset_growth": "Real asset growth", "gdp_growth": "GDP growth", "inflation": "Inflation",
          "policy": "Policy rate", "fx_change": "Dollar exchange rate", "fx_x_share": "FX change x FX-loan share",
          "fx_x_share (per 10 points)": "FX change x 10 points more FX lending"}

def load_config(quick=False):
    """Read config.yaml and resolve its paths against the repository root."""
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text())
    cfg["paths"] = {k: ROOT / v for k, v in cfg["paths"].items()}
    cfg["quick"] = quick
    return cfg

def md_table(df, fmt="{:.3f}", index=True):
    """Render a DataFrame as a GitHub markdown table.

    `fmt` is one format spec for every float, or a dict of column -> spec
    (columns missing from the dict get three decimals).
    """
    d = df.reset_index() if index else df

    def cell(col, v):
        if isinstance(v, (float, np.floating)):
            spec = fmt.get(col, "{:.3f}") if isinstance(fmt, dict) else fmt
            return "" if np.isnan(v) else spec.format(v)
        return str(v)

    lines = ["| " + " | ".join(map(str, d.columns)) + " |", "|" + "---|" * d.shape[1]]
    for row in d.itertuples(index=False):
        lines.append("| " + " | ".join(cell(c, v) for c, v in zip(d.columns, row)) + " |")
    return "\n".join(lines)
