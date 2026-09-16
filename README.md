# herBAR
A barcode renamer for herbarium specimens

### Requirements

Python 3.*  
Pillow  
zbar  

### Getting the code

For day-to-day use, you don't need `image_test/` or `tests/` -- together
they're ~90MB, almost entirely the real specimen photos used for testing.
A sparse partial clone skips them and only downloads the files needed to
run herbar.py:

	git clone --filter=blob:none --sparse git@github.com:jbest/herBAR.git

If you later need the test images and test suite too, expand it in place:

	git sparse-checkout add image_test tests

Or just clone normally (`git clone git@github.com:jbest/herBAR.git`) to get
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

On Windows, pyzbar's wheel bundles the zbar DLL it needs, so a separate
ZBar install typically isn't required. (Worth double-checking on your
actual target machine before rolling this out broadly.)

#### Option B: pip + venv

Install ZBar for your platform (https://zbar.sourceforge.net/) -- on
macOS/Linux this is a separate system library pyzbar links against.

Download the script file (herbar.py) to your local computer, create a
virtual environment, and install the required modules:

	python3 -m venv .venv
	source .venv/bin/activate        # Windows: .venv\Scripts\activate
	pip install -r requirements.txt

### Usage

	usage: herbar.py [-h] -s SOURCE [-p {TX,ANHC,VDB,TEST,Ferns,TORCH,EF}]
                 [-d DEFAULT_PREFIX] [-b BATCH] [-o [OUTPUT]] [-n] [-c CODE]
                 [-v] [-j [JPEG_RENAME]]

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

### Testing

Tests run herbar.py against the real images in `image_test/`, decoding
their actual barcodes. Each test copies the fixtures into a temporary
directory before running, so `image_test/` itself is never modified and
nothing needs to be reset between runs.

	pip install -r requirements-dev.txt
	pytest

On Apple Silicon Macs where ZBar is only installed via an Intel-only
Homebrew (`/usr/local`), create the virtualenv with `arch -x86_64
python3 -m venv .venv` so it links against the matching zbar library.

Alternatively, with uv: `uv sync --group dev` then `uv run pytest`.
