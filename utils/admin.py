# utils/admin.py
"""Single source of truth for the Windows admin/elevation check.

Five modules used to carry their own identical `_is_admin()` copy
(auto_optimizer, turbo_manager, optimization_services, services_manager,
startup_manager). One definition, imported everywhere.
"""


def is_admin() -> bool:
    """True if the current process runs with admin/elevated privileges."""
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False
