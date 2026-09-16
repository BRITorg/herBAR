# based on example at https://www.geeksforgeeks.org/create-a-watchdog-in-python-to-look-for-filesystem-changes/
# copied from project carlquist_workflow to be adapted for herBAR

# import time module, Observer, FileSystemEventHandler
import time
from pathlib import Path
import argparse
import platform

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, PatternMatchingEventHandler

import qr_read
import ingest
import config

WATCHED_DIRECTORY = config.local_capture_path

def process_file(file_path = None):
    code = qr_read.detect_code(image_path=file_path)
    #print(code)
    if code:
        # rename
        image_file = Path(file_path)
        image_file_stem = image_file.stem
        image_file_suffix = image_file.suffix
        if image_file_stem == code:
            print('Already named:', image_file.name)
            return False
        else:
            new_name = code + image_file_suffix
            new_path = Path(image_file.parent / new_name)
            if new_path.exists():
                print('ALERT - File exists, can not rename:', image_file)
                return False
            else:
                renamed_path = image_file.rename(new_path)
                try:
                    ingest.ingest(renamed_path)
                    return True
                except Exception as e:
                    print(e)
                    return False
    else:
        print('ALERT - no code detected.')
        return False

class OnMyWatch:
    # Set the directory on watch
    #watchDirectory = "images"
    watch_directory = Path(WATCHED_DIRECTORY)
    watch_path = watch_directory.resolve()
    print('Watching folder:', watch_path)

    def __init__(self):
        self.observer = Observer()

    def run(self):
        event_handler = Handler()
        self.observer.schedule(event_handler, self.watch_path, recursive = True)
        self.observer.start()
        try:
            while True:
                time.sleep(5)
        except:
            self.observer.stop()
            print("Observer Stopped")

        self.observer.join()


class Handler(PatternMatchingEventHandler):
    def __init__(self):
        # Set the patterns for PatternMatchingEventHandler
        PatternMatchingEventHandler.__init__(self, patterns=['*.jpg'], ignore_directories=True, case_sensitive=False)

    @staticmethod
    def on_any_event(event):
        print(platform.system())
        print(event.event_type, event.src_path)
        if event.is_directory:
            return None
            #TODO: adapt event detection to work on Mac OS:
            # https://stackoverflow.com/a/17586617/560798
        elif event.event_type == 'created':
            # Use modified event for Windows image capture
            # Event is created, you can process it now
            #print("Watchdog received created event - % s." % event.src_path)
            #process_file(file_path=event.src_path)
            if platform.system() == 'Windows':
                process_file(file_path=event.src_path)
            #pass

        elif event.event_type == 'modified':
            # Event is modified, you can process it now
            #print("Watchdog received modified event - % s." % event.src_path)
            if platform.system() == 'Windows':
                process_file(file_path=event.src_path)

        elif event.event_type == 'closed':
            # Event is closed, you can process it now
            #print("Watchdog received closed event - % s." % event.src_path)
            if platform.system() == 'Linux':
                process_file(file_path=event.src_path)
        


# TODO add arguments for test mode vs production mode
def arg_setup():
    # set up argument parser
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input_path", required=False,
        help="File source path")
    ap.add_argument("-c", "--config-alternative", required=False,
        help="Path of alternative config file")
    ap.add_argument("-v", "--verbose", action="store_true",
        help="Detailed output.")
    ap.add_argument("-n", "--dry_run", action="store_true",
        help="Simulate the sort process without moving files or creating directories.")
    args = vars(ap.parse_args())
    return args


if __name__ == '__main__':
    # initialize settings
    # set up argparse
    args = arg_setup()
    dry_run = args['dry_run']
    verbose = args['verbose']
    input_path = args['input_path']

    # start watching capture folder
    watch = OnMyWatch()
    watch.run()
