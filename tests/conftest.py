import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "image_test"

# Allow `import herbar` for unit-testing individual functions directly,
# without needing to launch it as a subprocess.
sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture
def sandbox(tmp_path):
    """A private copy of image_test/ that a test can freely rename.

    pytest gives every test its own fresh tmp_path, so the real fixtures
    in image_test/ are never touched and nothing needs to be reverted
    between runs -- just run pytest again.
    """
    dest = tmp_path / "images"
    shutil.copytree(FIXTURES_DIR, dest, ignore=shutil.ignore_patterns(".DS_Store"))
    return dest
