# PC Workman dependencies

The list matches `requirements.txt` in the repository (minimum versions, not pinned).
Last checked: 2026-11-22, release 1.9.3.

| Library | License | What PC Workman uses it for |
|---|---|---|
| psutil | BSD 3-Clause | CPU, memory, disk, network and process readings |
| matplotlib | Matplotlib License (PSF-based) | Charts |
| numpy | BSD 3-Clause | Number work behind the charts |
| GPUtil | MIT | NVIDIA graphics card readings through nvidia-smi |
| Pillow | MIT-CMU (HPND) | Images and icons |
| pystray | LGPL-3.0 | The tray icon |
| pywin32 | PSF | Windows APIs: startup entries, services, window handling |
| tkinter | PSF (part of Python) | The interface |
| pandas | BSD 3-Clause | Listed in requirements, not imported by the app code in 1.9.3 |
| requests | Apache 2.0 | Listed in requirements, not imported by the app code in 1.9.3 (network calls use Python's standard library) |

Optional and not bundled: LibreHardwareMonitor (MPL 2.0) for motherboard sensors, RTSS for FPS.

All of them are open source.
