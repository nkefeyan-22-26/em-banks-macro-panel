"""Repository hygiene: the IMF downloads and the panel built from them never enter version control."""
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("path", ["data/raw/weo.json", "data/raw/MANIFEST.json", "data/processed/panel_annual.csv"])
def test_data_files_are_git_ignored(path):
    assert subprocess.run(["git", "check-ignore", "-q", path], cwd=ROOT).returncode == 0
