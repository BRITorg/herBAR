import herbar


def test_matches_same_case():
    assert herbar.find_archive_file("BRIT-001", ["BRIT-001.JPG", "BRIT-001.CR2"]) == "BRIT-001.CR2"


def test_matches_regardless_of_stem_and_extension_case():
    # Simulates what a case-sensitive filesystem (e.g. Linux) would show:
    # the raw file's case doesn't line up with the JPEG's case at all.
    # This must still match, since the comparison is done in Python
    # rather than relying on the filesystem's own case-folding.
    assert herbar.find_archive_file("BRIT-001", ["BRIT-001.jpg", "brit-001.CR2"]) == "brit-001.CR2"


def test_matches_cr3_extension():
    assert herbar.find_archive_file("IMG_0001", ["IMG_0001.JPG", "IMG_0001.CR3"]) == "IMG_0001.CR3"


def test_returns_none_when_no_archive_file_present():
    assert herbar.find_archive_file("missing", ["other.CR2", "missing.JPG"]) is None


def test_ignores_similarly_named_but_different_stem():
    assert herbar.find_archive_file("BRIT-001", ["BRIT-0010.CR2", "BRIT-001_B.CR2"]) is None
