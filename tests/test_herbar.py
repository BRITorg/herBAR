import csv
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HERBAR = REPO_ROOT / "herbar.py"


def run_herbar(source, output_dir, *extra_args):
    output_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [sys.executable, str(HERBAR), "-s", str(source), "-o", str(output_dir), *extra_args],
        capture_output=True, text=True,
    )
    log_files = list(output_dir.glob("*.csv"))
    assert len(log_files) == 1, f"expected exactly one log file, found {log_files}"
    with open(log_files[0], newline="") as f:
        rows = list(csv.DictReader(f))
    return result, rows


def names(directory):
    return {p.name for p in directory.iterdir()}


def test_single_barcode_renames_jpg_and_matching_raw(sandbox, tmp_path):
    run_herbar(sandbox, tmp_path / "logs")

    renamed = names(sandbox)
    assert "BRIT180138.JPG" in renamed
    assert "BRIT180138.CR2" in renamed
    assert "BRIT-2015_11_20-S1-00001.JPG" not in renamed


def test_no_barcode_leaves_file_and_logs_failure(sandbox, tmp_path):
    _, rows = run_herbar(sandbox, tmp_path / "logs")

    assert "no-barcode.JPG" in names(sandbox)
    row = next(r for r in rows if r["basename"] == "no-barcode.JPG")
    assert row["status"] == "failed"
    assert row["status_details"] == "no barcodes found"


def test_duplicate_barcode_gets_unique_suffix(sandbox, tmp_path):
    # BRIT-2015_11_20-S1-00014.JPG and its two DUPLICATE copies all
    # decode to the same barcode (BRIT180123), so all three need
    # distinct filenames instead of colliding on rename.
    run_herbar(sandbox, tmp_path / "logs")

    renamed_jpgs = {n for n in names(sandbox) if n.startswith("BRIT180123") and n.endswith(".JPG")}
    renamed_raws = {n for n in names(sandbox) if n.startswith("BRIT180123") and n.endswith(".CR2")}
    assert len(renamed_jpgs) == 3
    assert len(renamed_raws) == 3


def test_multiple_barcodes_recorded_in_filename(sandbox, tmp_path):
    # BRIT_2018-08-31_S1_00009-MULTI.JPG contains two barcodes:
    # UTC00217601 and NLU0444006.
    run_herbar(sandbox, tmp_path / "logs")

    match = next(
        n for n in names(sandbox)
        if n.endswith(".JPG") and "UTC00217601" in n and "NLU0444006" in n
    )
    assert "_BARCODES[" in match


def test_dry_run_does_not_rename_files(sandbox, tmp_path):
    before = names(sandbox)
    _, rows = run_herbar(sandbox, tmp_path / "logs", "-n")

    assert names(sandbox) == before
    row = next(r for r in rows if r["basename"] == "BRIT-2015_11_20-S1-00001.JPG")
    assert row["status"] == "renamed"
    assert row["status_details"] == "dry-run - file not renamed"


def test_default_prefix_selects_matching_barcode(sandbox, tmp_path):
    run_herbar(sandbox, tmp_path / "logs", "-d", "NLU")
    assert "NLU0444006.JPG" in names(sandbox)


def test_default_prefix_with_no_match_still_logs_all_barcodes(sandbox, tmp_path):
    # Regression test: when default_prefix doesn't match any barcode on a
    # file with multiple barcodes, the multi-barcode info must not be
    # silently dropped, and an ALERT should be printed.
    result, _ = run_herbar(sandbox, tmp_path / "logs", "-d", "ZZZ")

    match = next(
        n for n in names(sandbox)
        if n.endswith(".JPG") and "UTC00217601" in n and "NLU0444006" in n
    )
    assert "_BARCODES[" in match
    assert "none matched default prefix ZZZ" in result.stdout


def test_jpeg_rename_suffix_applies_to_jpeg_only(sandbox, tmp_path):
    run_herbar(sandbox, tmp_path / "logs", "-j")

    renamed = names(sandbox)
    assert "BRIT180138_unprocessed.JPG" in renamed
    # the archival file is not the one downstream processing regenerates
    # a JPEG from, so it keeps the plain barcode name
    assert "BRIT180138.CR2" in renamed


def test_prepend_code_applies_to_both_jpeg_and_raw(sandbox, tmp_path):
    run_herbar(sandbox, tmp_path / "logs", "-c", "HERB")

    renamed = names(sandbox)
    assert "HERBBRIT180138.JPG" in renamed
    assert "HERBBRIT180138.CR2" in renamed


def test_missing_archival_file_still_renames_jpg_but_logs_failure(sandbox, tmp_path):
    # 100256.jpg decodes two barcodes (100256, 100255) but has no matching
    # raw file anywhere in image_test/.
    _, rows = run_herbar(sandbox, tmp_path / "logs")

    matching_rows = [r for r in rows if r["basename"] == "100256.jpg"]
    assert len(matching_rows) == 2
    assert {r["status"] for r in matching_rows} == {"renamed", "failed"}

    failed_row = next(r for r in matching_rows if r["status"] == "failed")
    assert failed_row["status_details"] == "missing archival file"

    assert "100256.jpg" not in names(sandbox)
    renamed = next(
        n for n in names(sandbox)
        if n.endswith(".jpg") and "100256" in n and "100255" in n
    )
    assert "_BARCODES[" in renamed


def test_tiff_input_is_scanned_and_renamed(sandbox, tmp_path):
    # TIFF_TEST-00001.tif/.CR2 are synthetic fixtures (generated, not real
    # specimen photos) covering the .tif branch of INPUT_FILE_TYPES, which
    # none of the real photos exercise.
    run_herbar(sandbox, tmp_path / "logs")

    renamed = names(sandbox)
    assert "TIFFTEST0001.tif" in renamed
    assert "TIFFTEST0001.CR2" in renamed


def test_cr3_archive_extension_is_matched(sandbox, tmp_path):
    # CR3_TEST-00001.JPG/.CR3 are synthetic fixtures covering the .CR3
    # branch of ARCHIVE_FILE_TYPES (Canon EOS R5 raw), which none of the
    # real photos exercise.
    run_herbar(sandbox, tmp_path / "logs")

    renamed = names(sandbox)
    assert "CR3TEST0001.JPG" in renamed
    assert "CR3TEST0001.CR3" in renamed
