# herBAR
A barcode renamer for herbarium specimens

When herbarium specimens are photographed, each image is initially saved
under a generic camera-assigned filename rather than the specimen's own
barcode identifier. herbar.py scans a directory of specimen photos,
decodes the CODE39 barcode printed on each specimen label (using either
[zxing-cpp](https://github.com/zxing-cpp/zxing-cpp) or
[pyzbar](https://github.com/NaturalHistoryMuseum/pyzbar)/ZBar, selectable with
`--backend`), and renames the image to that barcode value -- along with any matching raw
archival file (CR2, CR3, NEF, DNG, etc.) captured alongside it. It
handles the messy real-world cases that come up during a digitization
batch: missing or unreadable barcodes, multiple barcodes on one image,
and duplicate barcode values across different files. Every file it
processes -- renamed or not -- is recorded in a CSV log for review, and
a dry-run mode lets you preview what would happen before renaming
anything for real.

### Requirements

Python 3.*  
Pillow  
A barcode decoding backend -- either works, selected at runtime with `--backend`:
  - `zxing` (default) via [zxing-cpp](https://github.com/zxing-cpp/zxing-cpp), a self-contained wheel
    with no system library dependency
  - `zbar` via [pyzbar](https://github.com/NaturalHistoryMuseum/pyzbar), which needs a separate
    system ZBar install (see Installation below)

### Getting the code

For day-to-day use, you don't need `image_test/` or `tests/` -- together
they're ~90MB, almost entirely the real specimen photos used for testing.
A sparse partial clone skips them and only downloads the files needed to
run herbar.py:

	git clone --filter=blob:none --sparse git@github.com:BRITorg/herBAR.git

If you later need the test images and test suite too, expand it in place:

	git sparse-checkout add image_test tests

Or just clone normally (`git clone git@github.com:BRITorg/herBAR.git`) to get
everything from the start.

### Installation

#### Option A: uv (recommended, especially on Windows)

[uv](https://docs.astral.sh/uv/) installs Python dependencies from a single
binary, without a separate venv-create/activate step.

1. Install uv once per machine:
   - Windows (PowerShell): `irm https://astral.sh/uv/install.ps1 | iex`
   - macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. From this repo's directory, just run herbar.py through uv -- the first
   run creates the environment and installs the pinned dependencies
   automatically:

    uv run herbar.py -s <path-to-images>

This installs both decoding backends. The default (`--backend zxing`)
needs nothing further -- no system library required. If you use
`--backend zbar` on Windows, pyzbar's wheel bundles the zbar DLL it
needs, so a separate ZBar install typically isn't required (worth
double-checking on your actual target machine before rolling this out
broadly).

#### Option B: pip + venv

Download the script file (herbar.py) to your local computer, create a
virtual environment, and install the required modules:

	python3 -m venv .venv
	source .venv/bin/activate        # Windows: .venv\Scripts\activate
	pip install -r requirements.txt

This installs both decoding backends. The default (`--backend zxing`)
needs nothing further. If you plan to use `--backend zbar` instead,
also install ZBar for your platform (https://zbar.sourceforge.net/) --
on macOS/Linux this is a separate system library pyzbar links against.

### Usage

	usage: herbar.py [-h] -s SOURCE [-p {TX,ANHC,VDB,TEST,Ferns,TORCH,EF}]
                 [-d DEFAULT_PREFIX] [-b BATCH] [-o [OUTPUT]] [-n] [-c CODE]
                 [-v] [-j [JPEG_RENAME]] [--backend {zbar,zxing}]

	optional arguments:
	-h, --help            show this help message and exit
	-s SOURCE, --source SOURCE
                        Path to the directory that contains the images to be
                        analyzed.
	-p {TX,ANHC,VDB,TEST,Ferns,TORCH,EF}, --project {TX,ANHC,VDB,TEST,Ferns,TORCH,EF}
                        Project name for filtering in database
	-d DEFAULT_PREFIX, --default_prefix DEFAULT_PREFIX
                        Barcode prefix string which will be used as the
                        primary barcode when multiple barcodes are found.
                        Suppresses multiple barcode names in filename only
                        when a barcode matches the prefix; otherwise all
                        barcodes found are still recorded in the filename.
	-b BATCH, --batch BATCH
                        Flags written to batch_flags, can be used for
                        filtering downstream data.
	-o [OUTPUT], --output [OUTPUT]
                        Path to the directory where log file is written. By
                        default (no -o switch used) log will be written to
                        location of script. If just the -o switch is used, log
                        is written to directory indicated in source argument.
                        An absolute or relative path may also be provided.
	-n, --no_rename       Files will not be renamed, only log file generated.
	-c CODE, --code CODE  Collection or herbarium code prepended to barcode
                        values.
	-v, --verbose         Detailed output for each file processed.
	-j [JPEG_RENAME], --jpeg_rename [JPEG_RENAME]
                        String will be added to JPEG file names to prevent
                        name conflicts downstream.
	--backend {zbar,zxing}
                        Barcode decoding library to use: 'zxing' (zxing-cpp,
                        default) or 'zbar' (pyzbar). Only the backend you
                        select needs to be installed -- see Requirements.

### Testing

Tests run herbar.py against the real images in `image_test/`, decoding
their actual barcodes. Each test copies the fixtures into a temporary
directory before running, so `image_test/` itself is never modified and
nothing needs to be reset between runs.

	pip install -r requirements-dev.txt
	pytest

This exercises the default `zxing` backend, which needs no system
library. To run the suite against `zbar` instead, add `"--backend",
"zbar"` to the `run_herbar()` helper in `tests/test_herbar.py` -- on
Apple Silicon Macs where ZBar is only installed via an Intel-only
Homebrew (`/usr/local`), that also requires creating the virtualenv
with `arch -x86_64 python3 -m venv .venv` so it links against the
matching zbar library.

Alternatively, with uv: `uv sync --group dev` then `uv run pytest`.
