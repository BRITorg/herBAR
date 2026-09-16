import shutil
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "image_test"


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
