"""Download the public IMF extracts (SDMX 3.0 API) and read them back as tidy tables.

Each request is saved as JSON under data/raw/ (git-ignored, not redistributed) with a manifest
recording its URL, download time, size and SHA-256. Files already on disk are not downloaded again; delete
the folder to refresh every extract.
"""
import hashlib
import json
import time
import urllib.request

import pandas as pd


def fetch(cfg):
    """Download each request in config.yaml (requests) that is not on disk; return their names."""
    cc, out = cfg, cfg["paths"]["raw"]
    out.mkdir(parents=True, exist_ok=True)
    path = out / "MANIFEST.json"
    manifest = json.loads(path.read_text()) if path.exists() else {}
    new = []
    for name, (agency, flow, version, key) in cc["requests"].items():
        if (out / f"{name}.json").exists():
            continue
        url = f"{cc['api']}/{agency}/{flow}/{version}/{key}?attributes=none&measures=all"
        with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/json"}),
                                    timeout=600) as response:
            body = response.read()
        (out / f"{name}.json").write_bytes(body)
        manifest[name] = {"url": url, "fetched": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "bytes": len(body),
                          "sha256": hashlib.sha256(body).hexdigest()}
        new.append(name)
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    return new


def read(cfg, name):
    """One downloaded extract as a long table: one column per series dimension, then the period and value.

    The period is a `quarter` (pandas Period) for quarterly extracts and an integer `year` for annual ones.
    """
    data = json.loads((cfg["paths"]["raw"] / f"{name}.json").read_text())["data"]
    dims = data["structures"][0]["dimensions"]
    series_dims = [(d["id"], [v["id"] for v in d["values"]]) for d in dims["series"]]
    times = [v["value"] for v in dims["observation"][0]["values"]]
    rows = []
    for key, series in data["dataSets"][0]["series"].items():
        labels = {dim: values[int(i)] for (dim, values), i in zip(series_dims, key.split(":"))}
        for t, obs in series.get("observations", {}).items():
            if obs and obs[0] not in (None, ""):
                rows.append({**labels, "period": times[int(t)], "value": float(obs[0])})
    out = pd.DataFrame(rows)
    period = out.pop("period").astype(str)
    if period.str.fullmatch(r"\d{4}").all():
        out.insert(len(out.columns) - 1, "year", period.astype(int))
    else:
        out.insert(len(out.columns) - 1, "quarter", pd.PeriodIndex(period.str.replace("-", ""), freq="Q"))
    return out
