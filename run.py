"""Rebuild everything: download the IMF data, build the panel, check it, test the error bars, estimate.

    python run.py --fetch   # download any IMF extract not yet on disk, then build everything
    python run.py           # rebuild from the downloaded files
    python run.py --quick   # the same with a reduced simulation check
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from embanks import checks, estimate, fetch, load_config, panel, simcheck  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Emerging-market banks and the macroeconomy, from public IMF data.")
    parser.add_argument("--fetch", action="store_true", help="download the IMF extracts first")
    parser.add_argument("--quick", action="store_true", help="reduced simulation check")
    args = parser.parse_args()
    cfg = load_config(quick=args.quick)
    if args.fetch:
        print("downloaded:", ", ".join(fetch.fetch(cfg)) or "nothing new")
    q, a, samples = panel.build(cfg)
    checks.report(cfg, q, a, samples)
    print(f"panel: {len(samples['main'])} countries (main), {len(samples['strict'])} (strict); outputs/data_report.md")
    _, _, _, decision, power, _ = simcheck.run(cfg, a, samples)
    methods = {family: choice for family, (choice, _) in decision.items()}
    print("simulation check:", "; ".join(f"{k}: {v}" for k, v in methods.items()), "(outputs/simulation_check.md)")
    estimate.run(cfg, a, samples, power, methods)
    print("estimates: outputs/results.md")


if __name__ == "__main__":
    main()
