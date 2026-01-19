# PyInstaller runtime hook - hide console windows for all subprocesses
import sys
import subprocess

if sys.platform == 'win32':
    # Save original functions
    _original_popen_init = subprocess.Popen.__init__

    def _patched_popen_init(self, *args, **kwargs):
        # Add CREATE_NO_WINDOW flag to hide console
        if 'creationflags' not in kwargs:
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        else:
            kwargs['creationflags'] |= subprocess.CREATE_NO_WINDOW
        return _original_popen_init(self, *args, **kwargs)

    subprocess.Popen.__init__ = _patched_popen_init
