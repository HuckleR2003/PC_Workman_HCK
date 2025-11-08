"""utils.file_utils
Helpers for file rotation and cleanup."""
import os, glob

def rotate_old_logs(path_pattern, keep=90):
    files = sorted(glob.glob(path_pattern))
    if len(files) <= keep:
        return
    for f in files[:-keep]:
        try:
            os.remove(f)
        except Exception:
            pass
