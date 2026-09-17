import argparse
from hashlib import md5
import uuid
import glob
from datetime import datetime
import re
import csv
import os
import platform
from PIL import Image
from pathlib import Path
import string
from tqdm import tqdm

# File extensions that are scanned and logged
INPUT_FILE_TYPES = ['.jpg', '.jpeg', '.JPG', '.JPEG', '.tif', '.TIF', '.TIFF', '.tiff']
# File type extensions that are logged when filename matches a scanned input file
# compared case-insensitively, so case is not duplicated here
ARCHIVE_FILE_TYPES = ['.cr3', '.cr2', '.raw', '.nef', '.dng']
# Barcode symbologies accepted, others ignored
ACCEPTED_SYMBOLOGIES = ['CODE39']
# Barcode decoding backends supported by get_barcodes()
BACKENDS = ['zbar', 'zxing']
# TODO add accepted barcode string patterns
FIELD_DELIMITER = ','  # delimiter used in output CSV
PROJECT_IDS = ['TX', 'ANHC', 'VDB', 'TEST', 'Ferns', 'TORCH', 'EF']
JPG_RENAME_STRING = 'unprocessed' # string optionally added to JPG file names
# this allows downstream processing to generate a new JPG from the raw file without name conflicts
UNIQUE_QUALIFIERS = list(string.ascii_uppercase) # list of characters added to file names to make unique

def md5hash(fname):
    # from https://stackoverflow.com/questions/3431825/generating-an-md5-checksum-of-a-file
    # using this approach to ensure larger files can be read into memory
    #hash_md5 = hashlib.md5()
    hash_md5 = md5()
    try:
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except OSError as e:
        print('ERROR:', e)
        return None


def creation_date(path_to_file):
    # From https://stackoverflow.com/a/39501288
    """
    Try to get the date that a file was created, falling back to when it was
    last modified if that isn't possible.
    See http://stackoverflow.com/a/39501288/1709587 for explanation.
    """
    if platform.system() == 'Windows':
        return os.path.getctime(path_to_file)
    else:
        stat = os.stat(path_to_file)
        try:
            return stat.st_birthtime
        except AttributeError:
            # We're probably on Linux. No easy way to get creation dates here,
            # so we'll settle for when its content was last modified.
            return stat.st_mtime

# Attempts to get actual path of files with correct case
def get_actual_filename(name):
    # From https://stackoverflow.com/a/14742779
    dirs = name.split('\\')
    # disk letter
    test_name = [dirs[0].upper()]
    for d in dirs[1:]:
        test_name += ["%s[%s]" % (d[:-1], d[-1])]
    res = glob.glob('\\'.join(test_name))
    if not res:
        # File not found
        return None
    return res[0]

def casedpath(path):
    # from https://stackoverflow.com/a/35229734
    r = glob.glob(re.sub(r'([^:/\\])(?=[/\\]|$)', r'[\1]', path))
    return r and r[0] or path

def get_unique_path(path=None, qualifiers=UNIQUE_QUALIFIERS):
    if path.exists():
        #print('path exists:', path)
        # get stem
        stem = path.stem
        suffix = path.suffix
        path_parent = path.parent
        # remove previous qualifier
        if stem[-2:-1]=='_':
            original_stem = stem[:-2]
            #print('original_stem:',original_stem)
            failed_qualifier = stem[-1:]
            #print('failed_qualifier:',failed_qualifier)
            failed_qualifier_index = qualifiers.index(failed_qualifier)
            #print('failed_qualifier_index:',failed_qualifier_index)
            try:
                new_qualifier = qualifiers[failed_qualifier_index+1]
            except IndexError:
                # ran out of qualifiers
                # using UUID instead
                new_qualifier = str(uuid.uuid4())
        else:
            # No previous qualifier established
            original_stem = stem
            new_qualifier = qualifiers[0]

        # add unique to stem
        new_name = original_stem + '_' + new_qualifier + suffix
        #new_path = Path(new_name)
        new_path = path_parent / new_name
        
        return(get_unique_path(path=new_path, qualifiers=qualifiers))
    else:
        return path

def log_file_data(
    batch_id=None, batch_path=None, batch_flags=None,
    image_event_id=None,
    barcodes=None,
    barcode=None,
    status=None,
    status_details=None,
    datetime_analyzed=None,
    image_path=None, new_path=None,
    file_uuid=None, file_creation_time=None, file_hash=None,
    derived_from_file=None, derived_from_uuid=None):
    basename = os.path.basename(image_path)
    file_name, file_extension = os.path.splitext(basename)

    # clean up values for writing to SQLite (doesn't like dicts)
    if barcodes:
        barcodes = str(barcodes)
    else:
        barcodes = ''
    # TODO log batch flags, barcode
    log_writer.writerow({
        'batch_id': batch_id, 'batch_path': batch_path, 'batch_flags': batch_flags,
        'project_id': project_id, 'image_event_id': image_event_id,
        'datetime_analyzed': datetime_analyzed,
        'image_path': image_path, 'basename': basename, 'file_name': file_name,
        'status': status, 'status_details': status_details, 'new_path': new_path,
        'file_creation_time': file_creation_time,
        'file_hash': file_hash, 'file_uuid': file_uuid,
        'derived_from_file': derived_from_file, 'derived_from_uuid': derived_from_uuid,
        'barcodes': barcodes, 'barcode': barcode})

def process(
    file_path=None, new_stem=None,
    uuid=None,
    derived_from_file=None, derived_from_uuid=None,
    barcode=None,
    barcodes=None,
    image_event_id=None
        ):
    global renames_failed, renames_attempted, files_processed
    files_processed += 1
    # Get file creation time
    file_creation_time = datetime.fromtimestamp(creation_date(file_path))
    # generate MD5 hash
    file_hash = md5hash(file_path)
    datetime_analyzed = datetime.now()

    #rename_status, new_path = rename(file_path=file_path, new_stem=new_stem)
    if prepend_code:
        new_stem = prepend_code + new_stem
    rename_result = rename(file_path=file_path, new_stem=new_stem)
    renames_attempted += 1
    status_details = rename_result['details']
    #print('rename_result:', rename_result)
    #if rename_status:
    if rename_result['success']:
        new_path = rename_result['new_path']
        # TODO log derivative_file_uuid and arch_file_uuid into file_uuid and derived_from_file
        log_file_data(
            batch_id=batch_id, batch_path=batch_path, batch_flags=batch_flags, # from global vars
            image_event_id=image_event_id,
            datetime_analyzed=datetime_analyzed,
            barcode=barcode, barcodes=barcodes,
            status='renamed', status_details=status_details,
            image_path=file_path, new_path=new_path,
            file_uuid=uuid, file_creation_time=file_creation_time, file_hash=file_hash,
            derived_from_file=derived_from_file, derived_from_uuid=derived_from_uuid)
    else:
        print('Rename failed:', file_path)
        renames_failed += 1
        log_file_data(
            batch_id=batch_id, batch_path=batch_path, batch_flags=batch_flags, # from global vars
            image_event_id=image_event_id,
            datetime_analyzed=datetime_analyzed,
            barcode=barcode, barcodes=barcodes,
            status='failed', status_details=status_details,
            image_path=file_path, new_path=None,
            file_uuid=uuid, file_creation_time=file_creation_time, file_hash=file_hash,
            derived_from_file=derived_from_file, derived_from_uuid=derived_from_uuid)

def rename(file_path=None, new_stem=None):
    parent_path = file_path.parent
    file_extension = file_path.suffix
    new_file_name = new_stem + file_extension
    new_path = parent_path.joinpath(new_file_name)
    # check if current filename is already correct
    if file_path==new_path:
        #print('Paths are same.')
        return{'success': True, 'details': 'file already named correctly', 'new_path': new_path}

    if file_path.exists():
        # generate unique filename for new path
        new_path = get_unique_path(path=new_path)
        # A last check to ensure it is unique
        if new_path.exists():
            print('ALERT - file exists, can not overwrite:', new_path)
            #return False, None
            return{'success': False, 'details': 'file name exists', 'new_path': None}
        else:
            try:
                if no_rename:
                    # don't rename but return True to simulate for logging
                    #return True, file_path
                    return{'success': True, 'details': 'dry-run - file not renamed', 'new_path': file_path}
                else:
                    file_path.rename(new_path)
                    #return True, new_path
                    return{'success': True, 'details': None, 'new_path': new_path}
            except OSError:
                # Possible problem with character in new filename
                print('ALERT - OSError. new_path:', new_path, 'file_path:', file_path )
                #return False, None
                return{'success': False, 'details': 'file not renamed, possible problem character in path', 'new_path': None}
            except Exception as e:
                print("Unexpected error:", e)
                raise

def decode_zbar(image):
    try:
        from pyzbar.pyzbar import decode
    except ImportError:
        raise SystemExit("--backend zbar requires pyzbar. Run: pip install pyzbar")
    return [
        {'type': str(result.type), 'data': result.data.decode('UTF-8')}
        for result in decode(image)]

def decode_zxing(image):
    try:
        import zxingcpp
    except ImportError:
        raise SystemExit("--backend zxing requires zxing-cpp. Run: pip install zxing-cpp")
    return [
        {'type': result.format.name.upper(), 'data': result.text}
        for result in zxingcpp.read_barcodes(image)]

def get_barcodes(file_path=None):
    # read barcodes from JPG using the selected decoder backend
    image = Image.open(file_path)
    if backend == 'zbar':
        raw_barcodes = decode_zbar(image)
    else:
        raw_barcodes = decode_zxing(image)

    if raw_barcodes:
        matching_barcodes = []
        for barcode in raw_barcodes:
            # Keep only codes that match accepted symbologies
            if barcode['type'] in ACCEPTED_SYMBOLOGIES:
                matching_barcodes.append(barcode)
                if verbose:
                    print(barcode['type'], barcode['data'])
        return matching_barcodes
    else:
        print('No barcodes found:', file_path)
        return None

def get_default_barcode(barcodes=None, default_prefix=None):
    #print('barcodes:', barcodes)
    if default_prefix:
        # return first barcode which matches default prefix
        # not cases sensitive
        for barcode in barcodes:
            if barcode['data'].lower().startswith(default_prefix.lower()):
                return barcode['data'], True
        # if no match, return first barcode
        return barcodes[0]['data'], False
    else:
        # return first barcode if no default prefix is specified
        return barcodes[0]['data'], False

def find_archive_file(file_stem, sibling_names):
    """Return the sibling filename that pairs with file_stem as its
    archival file, or None if there isn't one.

    Stem and extension are compared case-insensitively in Python so the
    match is consistent regardless of the filesystem's own case
    sensitivity (relying on filesystem case-folding is inconsistent
    across platforms: case-insensitive on macOS/Windows by default,
    case-sensitive on Linux).
    """
    file_stem_lower = file_stem.lower()
    for sibling in sibling_names:
        sibling_path = Path(sibling)
        if (sibling_path.stem.lower() == file_stem_lower
                and sibling_path.suffix.lower() in ARCHIVE_FILE_TYPES):
            return sibling
    return None

def walk(path=None):
    global files_analyzed, renames_failed, missing_barcodes, files_processed
    for root, dirs, files in os.walk(path):
        for file in tqdm(files, ascii=True, desc='renaming images'):
            files_analyzed += 1
            #print('increment file count:', file)
            file_path_string = os.path.join(root, file)
            file_path = Path(file_path_string)
            if file_path.suffix in INPUT_FILE_TYPES:
                # Get barcodes
                barcodes = get_barcodes(file_path=file_path)
                if barcodes:
                    file_stem = file_path.stem
                    # find archive file matching stem
                    matched_archive_name = find_archive_file(file_stem, files)
                    arch_file_path = file_path.parent / matched_archive_name if matched_archive_name else None
                    image_event_id = str(uuid.uuid4())
                    arch_file_uuid = str(uuid.uuid4())
                    derivative_file_uuid = str(uuid.uuid4())

                    # assume first barcode
                    # TODO check barcode pattern
                    # Get first barcode value for file name
                    #barcode = barcodes[0]['data']
                    barcode, prefix_matched = get_default_barcode(barcodes=barcodes, default_prefix=default_prefix)
                    # Handle multiple barcodes
                    if default_prefix and prefix_matched:
                        # a default prefix was designated and matched a barcode, don't capture multiple barcodes
                        multi_string = ''
                    else:
                        if len(barcodes) > 1:
                            #print(barcodes)
                            barcode_values = [b['data'] for b in barcodes]
                            multi_string = '_BARCODES[' + ','.join(barcode_values) + ']'
                            if default_prefix:
                                print('ALERT - multiple barcodes found, none matched default prefix', default_prefix, '. Using default barcode of', len(barcodes), ':', barcode)
                            else:
                                print('ALERT - multiple barcodes found. Using default barcode of', len(barcodes), ':', barcode)
                        else:
                            # only one barcode, use empty multi value
                            multi_string = ''
                    # process JPEG

                    #print('multi_string:', multi_string, type(multi_string))
                    #print('barcode:', barcode, type(barcode))

                    if jpeg_rename:
                        # append JPEG string
                        jpeg_stem = barcode + multi_string  + '_' + jpeg_rename
                    else:
                        jpeg_stem = barcode + multi_string
                        #pass
                    # TODO add derived from uuid
                    archival_stem = barcode + multi_string
                    process(
                        file_path=file_path,
                        new_stem=jpeg_stem,
                        uuid=derivative_file_uuid,
                        derived_from_uuid=arch_file_uuid,
                        derived_from_file=arch_file_path,
                        barcode=barcode,
                        barcodes=barcodes,
                        image_event_id=image_event_id)
                    if arch_file_path:
                        # process archival
                        process(
                            file_path=arch_file_path,
                            new_stem=archival_stem,
                            uuid=arch_file_uuid,
                            derived_from_uuid=None,
                            derived_from_file=None,
                            barcode=barcode,
                            barcodes=barcodes,
                            image_event_id=image_event_id)
                    else:
                        print('archival file not found for:', file_path)
                        #files_processed += 1 # not actually processed, but incremented for stats
                        datetime_analyzed = datetime.now()
                        log_file_data(
                            batch_id=batch_id, batch_path=batch_path, batch_flags=batch_flags, # from global vars
                            image_event_id=None,
                            datetime_analyzed=datetime_analyzed,
                            barcode=None, barcodes=None,
                            status='failed', status_details='missing archival file',
                            image_path=file_path, new_path=None,
                            )
                else:
                    # no barcodes found
                    missing_barcodes += 1
                    files_processed += 1 # not actually processed, but incremented for stats
                    datetime_analyzed = datetime.now()
                    log_file_data(
                        batch_id=batch_id, batch_path=batch_path, batch_flags=batch_flags, # from global vars
                        image_event_id=None,
                        datetime_analyzed=datetime_analyzed,
                        barcode=None, barcodes=None,
                        status='failed', status_details='no barcodes found',
                        image_path=file_path, new_path=None,
                        #file_uuid=uuid, file_creation_time=file_creation_time, file_hash=file_hash,
                        #derived_from_file=derived_from_file, derived_from_uuid=derived_from_uuid
                        )


if __name__ == "__main__":
    # set up argument parser
    ap = argparse.ArgumentParser()
    ap.add_argument("-s", "--source", required=True,
        help="Path to the directory that contains the images to be analyzed.")
    ap.add_argument("-p", "--project", required=False, choices=PROJECT_IDS,
        help="Project name for filtering in database")
    ap.add_argument("-d", "--default_prefix", required=False,
        help="Barcode prefix string which will be used as the primary barcode when multiple barcodes are found. \
        Suppresses multiple barcode names in filename only when a barcode matches the prefix; \
        otherwise all barcodes found are still recorded in the filename.")
    ap.add_argument("-b", "--batch", required=False,
        help="Flags written to batch_flags, can be used for filtering downstream data.")
    ap.add_argument("-o", "--output", nargs='?', default='primary', const='secondary',
        help="Path to the directory where log file is written. \
        By default (no -o switch used) log will be written to location of script. \
        If just the -o switch is used, log is written to directory indicated in source argument. \
        An absolute or relative path may also be provided.")
    ap.add_argument("-n", "--no_rename", required=False, action='store_true',
        help="Files will not be renamed, only log file generated.")
    ap.add_argument("-c", "--code", required=False,
        help="Collection or herbarium code prepended to barcode values.")
    ap.add_argument("-v", "--verbose", required=False, action='store_true',
        help="Detailed output for each file processed.")
    ap.add_argument("-j", "--jpeg_rename", nargs='?', default=False, const=JPG_RENAME_STRING,
        help="String will be added to JPEG file names to prevent name conflicts downstream.")
    ap.add_argument("--backend", required=False, choices=BACKENDS, default='zxing',
        help="Barcode decoding library to use: 'zxing' (zxing-cpp, default) or 'zbar' (pyzbar).")
    args = vars(ap.parse_args())

    analysis_start_time = datetime.now()
    batch_id = str(uuid.uuid4())
    batch_path = os.path.realpath(args["source"])
    project_id = args["project"]
    no_rename = args["no_rename"]
    prepend_code = args["code"]
    verbose = args["verbose"]
    output_location = args["output"]
    jpeg_rename = args["jpeg_rename"]
    backend = args["backend"]
    #print('prepend_code', prepend_code)

    if args["batch"]:
        batch_flags = args["batch"]
        if verbose:
            print('Batch flags:', batch_flags)
    else:
        batch_flags = None

    if args["default_prefix"]:
        default_prefix = args["default_prefix"]
    else:
        default_prefix = None

    # Create log file for results
    log_file_name = analysis_start_time.date().isoformat() + '_' + batch_id + '.csv'
    # Create and test log output path
    if output_location == 'primary':
        # No alternative log path specified (uses script path)
        #TODO explicitly get script directory
        log_file_path = log_file_name
    elif output_location == 'secondary':
        # Alternative path specified implicitly (uses source directory path)
        output_directory = os.path.realpath(args["source"])
        print('output_directory:', output_directory)
        log_file_path = os.path.join(output_directory, log_file_name)
    else:
        # Explicit alternative path specified
        output_directory = os.path.realpath(output_location)
        print('output_directory:', output_directory)
        #TODO make sure directory exists and is writeable, otherwise, fall back to primary location
        log_file_path = os.path.join(output_directory, log_file_name)

    csvfile = open(log_file_path, 'w', newline='')
    # write header
    fieldnames = [
        'batch_id', 'batch_path', 'batch_flags', 'project_id',
        'image_event_id', 'datetime_analyzed', 'barcodes', 'barcode',
        'status', 'status_details',
        'image_path', 'basename', 'file_name', 'new_path',
        'file_creation_time',
        'file_hash', 'file_uuid', 'derived_from_file', 'derived_from_uuid']
    log_writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    log_writer.writeheader()

    directory_path = os.path.realpath(args["source"])
    files_analyzed = 0
    files_processed = 0
    renames_attempted = 0
    renames_failed = 0
    missing_barcodes = 0

    # Start scanning input directory
    print('scanning:', batch_path)
    try:
        walk(path=batch_path)
    finally:
        # Ensure CSV log file is flushed and closed even if scanning raises
        csvfile.close()
    # Scan complete

    analysis_end_time = datetime.now()

    print('Started:', analysis_start_time)
    print('Completed:', analysis_end_time)
    # files_analyzed is the total number of files encountered in directory which is scanned
    print('Files analyzed:', files_analyzed)
    # files_processed is number of files which match the expected extensions for image files
    print('Files processed:', files_processed)
    print('Renames attempted:', renames_attempted)
    if renames_attempted > 0:
        print('Renames failed:', renames_failed, '({:.1%})'.format(renames_failed/renames_attempted))
        print('Missing barcodes:', missing_barcodes, '({:.1%})'.format(missing_barcodes/files_analyzed))
    else:
        print('Input directory not found or contains no images matching search pattern.')
    print('Duration:', analysis_end_time - analysis_start_time)
    if files_analyzed > 0:
        print('Time per file:', (analysis_end_time - analysis_start_time) / files_analyzed)
    print('Report written to:', log_file_path)
