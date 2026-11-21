"""Code page of Windows console tools (powercfg, sc, ipconfig...).

They write in the OEM code page - cp852 on Polish Windows - and Python's
text=True reads with the ANSI one (cp1250), so the power plan showed as
"Zr˘wnowaľony" instead of "Zrównoważony" (second long test, 2026-11-17).
Pass encoding=OEM_ENCODING to subprocess.run next to text=True.
"""


def _oem() -> str:
    try:
        import ctypes
        cp = int(ctypes.windll.kernel32.GetOEMCP())
        if cp > 0:
            import codecs
            codecs.lookup(f"cp{cp}")
            return f"cp{cp}"
    except Exception:
        pass
    return "utf-8"


OEM_ENCODING = _oem()
