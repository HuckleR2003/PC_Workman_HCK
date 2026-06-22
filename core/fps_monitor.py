"""
FPS monitor  -  reads the live frame rate from RTSS shared memory.
=================================================================
Real per-game FPS on Windows needs either ETW present events (PresentMon, which
requires admin + a bundled binary) or reading another tool's published counters.
This module takes the safe, zero-risk path: it reads the *RTSSSharedMemoryV2*
shared-memory block that RivaTuner Statistics Server (bundled with MSI Afterburner,
EVGA Precision, etc.) publishes for every app it hooks.

No admin rights, no DLL injection, no anti-cheat surface - we only read a block
that RTSS already exposes. If RTSS is not running, `read_fps()` returns None and
the overlay shows "--" exactly as before.

RTSS layout (documented, stable since 2.x):
    header  : DWORD signature 'RTSS', version, appEntrySize, appArrOffset, appArrSize
    app[i]  : DWORD pid, char szName[260], DWORD flags, time0, time1, frames, frameTime
    fps     = frames * 1000 / (time1 - time0)      (time in ms)
"""
from __future__ import annotations

import struct
import sys
from typing import Optional

_SHMEM_NAME = "RTSSSharedMemoryV2"
_SIG_RTSS   = b"RTSS"

# header field offsets (all DWORD / little-endian uint32)
_H_SIGNATURE      = 0
_H_VERSION        = 4
_H_APP_ENTRY_SIZE = 8
_H_APP_ARR_OFFSET = 12
_H_APP_ARR_SIZE   = 16
_HEADER_READ      = 24            # bytes we need from the header

# app-entry field offsets (relative to the entry start)
_E_PROCESS_ID = 0
_E_TIME0      = 268
_E_TIME1      = 272
_E_FRAMES     = 276
_E_MIN_SIZE   = 280              # we read up to (but not incl.) offset 280


def _u32(buf: bytes, off: int) -> int:
    return struct.unpack_from("<I", buf, off)[0]


def _foreground_pid() -> int:
    """PID of the window currently in focus (usually the game), or 0."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return 0
        pid = ctypes.c_ulong(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return int(pid.value)
    except Exception:
        return 0


def read_fps(target_pid: Optional[int] = None) -> Optional[float]:
    """Current FPS from RTSS, or None if RTSS isn't running / has no data.

    Picks the foreground app's entry when possible, otherwise the busiest one.
    `target_pid` overrides the foreground heuristic when the caller knows the PID.
    """
    if not sys.platform.startswith("win"):
        return None

    import mmap
    # 1) map just the header to learn the array geometry
    try:
        mm = mmap.mmap(-1, _HEADER_READ, _SHMEM_NAME, access=mmap.ACCESS_READ)
    except OSError:
        return None                                  # RTSS not running
    except Exception:
        return None
    try:
        hdr = mm.read(_HEADER_READ)
    finally:
        mm.close()

    if len(hdr) < _HEADER_READ or hdr[0:4] != _SIG_RTSS:
        return None

    entry_size = _u32(hdr, _H_APP_ENTRY_SIZE)
    arr_offset = _u32(hdr, _H_APP_ARR_OFFSET)
    arr_size   = _u32(hdr, _H_APP_ARR_SIZE)
    if entry_size < _E_MIN_SIZE or arr_size <= 0 or arr_size > 4096:
        return None

    total = arr_offset + arr_size * entry_size
    if total <= 0 or total > 64 * 1024 * 1024:       # sanity guard
        return None

    # 2) map the full block and scan the app entries
    try:
        mm = mmap.mmap(-1, total, _SHMEM_NAME, access=mmap.ACCESS_READ)
    except Exception:
        return None
    try:
        blob = mm.read(total)
    finally:
        mm.close()

    if target_pid is None:
        target_pid = _foreground_pid()

    best_fps = None          # busiest entry (fallback)
    fg_fps   = None          # foreground match (preferred)
    for i in range(arr_size):
        base = arr_offset + i * entry_size
        if base + _E_MIN_SIZE > len(blob):
            break
        pid = _u32(blob, base + _E_PROCESS_ID)
        if pid == 0:
            continue
        t0     = _u32(blob, base + _E_TIME0)
        t1     = _u32(blob, base + _E_TIME1)
        frames = _u32(blob, base + _E_FRAMES)
        if t1 <= t0 or frames <= 0:
            continue
        fps = frames * 1000.0 / (t1 - t0)
        if not (0 < fps < 10000):                    # ignore garbage
            continue
        if pid == target_pid:
            fg_fps = fps
        if best_fps is None or fps > best_fps:
            best_fps = fps

    return fg_fps if fg_fps is not None else best_fps


def is_available() -> bool:
    """True if RTSS shared memory is present (Afterburner/RivaTuner running)."""
    if not sys.platform.startswith("win"):
        return False
    import mmap
    try:
        mm = mmap.mmap(-1, _HEADER_READ, _SHMEM_NAME, access=mmap.ACCESS_READ)
    except Exception:
        return False
    try:
        return mm.read(4) == _SIG_RTSS
    finally:
        mm.close()
