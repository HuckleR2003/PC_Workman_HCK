# hck_gpt/services_manager.py
"""
Windows Services Manager
Handles enabling/disabling Windows services based on user needs
"""

import subprocess
import platform
import json
import os

# No console flash + never crash the subprocess reader thread on stray bytes.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class ServicesManager:
    """Manages Windows services optimization"""

    # Service mappings - service name: (display name, description)
    SERVICES = {
        "printer": {
            "services": ["Spooler"],
            "display": "Print Spooler",
            "description": "Printer support"
        },
        "bluetooth": {
            "services": ["bthserv", "BluetoothUserService"],
            "display": "Bluetooth Support",
            "description": "Bluetooth device connectivity"
        },
        "remote": {
            "services": ["RemoteRegistry", "RemoteAccess", "TermService"],
            "display": "Remote Desktop & Registry",
            "description": "Remote PC access and management"
        },
        "fax": {
            "services": ["Fax"],
            "display": "Fax Service",
            "description": "Fax sending and receiving"
        },
        "tablet": {
            "services": ["TabletInputService"],
            "display": "Tablet Input Service",
            "description": "Tablet and pen input"
        },
        "xbox": {
            "services": ["XblAuthManager", "XblGameSave", "XboxNetApiSvc", "XboxGipSvc"],
            "display": "Xbox Services",
            "description": "Xbox Live and gaming features"
        },
        "telemetry": {
            "services": ["DiagTrack", "dmwappushservice"],
            "display": "Telemetry & Diagnostics",
            "description": "Microsoft telemetry and diagnostics"
        }
    }

    def __init__(self, config_path=None):
        if config_path is None:
            try:
                from utils.paths import APP_DIR
                config_path = os.path.join(
                    APP_DIR, "data", "services_config.json")
            except Exception:
                config_path = os.path.join("data", "services_config.json")
        self.config_path = config_path
        self.disabled_services = self.load_config()
        self.disabled_services.setdefault("disabled", [])
        self.disabled_services.setdefault("original_start_types", {})
        self.disabled_services.setdefault("original_running", {})
        self.is_windows = platform.system() == "Windows"

    def load_config(self):
        """Load saved services configuration"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
        return {
            "disabled": [],
            "original_start_types": {},
            "original_running": {},
            "timestamp": None,
        }

    def save_config(self):
        """Save current services configuration"""
        import time
        self.disabled_services["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.disabled_services, f, indent=2,
                          ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def get_service_status(self, service_name):
        """Check if a Windows service is running"""
        if not self.is_windows:
            return "N/A - Not Windows"

        try:
            result = subprocess.run(
                ["sc", "query", service_name],
                capture_output=True,
                text=True, errors="replace",
                timeout=5, creationflags=_NO_WINDOW
            )

            if "RUNNING" in result.stdout:
                return "Running"
            elif "STOPPED" in result.stdout:
                return "Stopped"
            else:
                return "Unknown"
        except Exception as e:
            return f"Error: {str(e)}"

    def get_service_start_type(self, service_name):
        """Return demand/auto/delayed-auto/disabled, or None when unknown."""
        if not self.is_windows:
            return None
        try:
            import winreg
            path = (
                r"SYSTEM\CurrentControlSet\Services"
                + "\\" + service_name
            )
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as key:
                start, _ = winreg.QueryValueEx(key, "Start")
                delayed = 0
                try:
                    delayed, _ = winreg.QueryValueEx(
                        key, "DelayedAutoStart")
                except OSError:
                    pass
            if int(start) == 2:
                return "delayed-auto" if int(delayed or 0) else "auto"
            if int(start) == 3:
                return "demand"
            if int(start) == 4:
                return "disabled"
            return None
        except Exception:
            return None

    def disable_service(self, service_name):
        """Disable a Windows service"""
        if not self.is_windows:
            return False, "Not Windows OS"

        try:
            # Change startup configuration first. The old order stopped the
            # service and only then attempted this command, so an access error
            # could leave a service stopped without a saved reversible change.
            result = subprocess.run(
                ["sc", "config", service_name, "start=", "disabled"],
                capture_output=True,
                text=True, errors="replace",
                timeout=10, creationflags=_NO_WINDOW
            )

            if result.returncode == 0:
                subprocess.run(
                    ["sc", "stop", service_name],
                    capture_output=True,
                    timeout=10, creationflags=_NO_WINDOW
                )
                return True, f"Service {service_name} disabled successfully"
            else:
                return False, f"Failed to disable {service_name}"
        except Exception as e:
            return False, f"Error: {str(e)}"

    def start_service(self, service_name):
        """Start a service that was running before PC Workman changed it."""
        if not self.is_windows:
            return False, "Not Windows OS"
        try:
            result = subprocess.run(
                ["sc", "start", service_name],
                capture_output=True,
                text=True, errors="replace",
                timeout=10, creationflags=_NO_WINDOW
            )
            # 1056 means the service is already running.
            already_running = (
                "1056" in (result.stdout or "")
                or "already running" in (result.stdout or "").lower()
            )
            if result.returncode == 0 or already_running:
                return True, f"Service {service_name} started"
            return False, f"Failed to start {service_name}"
        except Exception as e:
            return False, f"Error: {str(e)}"

    def _restore_service_state(self, service_name):
        original_types = self.disabled_services.setdefault(
            "original_start_types", {})
        original_running = self.disabled_services.setdefault(
            "original_running", {})
        start_type = original_types.get(service_name, "demand")
        success, msg = self.enable_service(service_name, start_type)
        if success and original_running.get(service_name, False):
            success, start_msg = self.start_service(service_name)
            msg = f"{msg}; {start_msg}"
        return success, msg

    def enable_service(self, service_name, start_type="demand"):
        """Restore a Windows service to a validated startup type."""
        if not self.is_windows:
            return False, "Not Windows OS"

        try:
            start_type = (
                start_type if start_type in
                ("demand", "auto", "delayed-auto") else "demand"
            )
            # Enable the service
            result = subprocess.run(
                ["sc", "config", service_name, "start=", start_type],
                capture_output=True,
                text=True, errors="replace",
                timeout=10, creationflags=_NO_WINDOW
            )

            if result.returncode == 0:
                return True, (
                    f"Service {service_name} restored to {start_type}")
            else:
                return False, f"Failed to enable {service_name}"
        except Exception as e:
            return False, f"Error: {str(e)}"

    def apply_optimization(self, category, should_disable=True):
        """
        Apply service optimization for a category

        Args:
            category: Service category (e.g., 'printer', 'bluetooth')
            should_disable: True to disable, False to enable
        """
        if category not in self.SERVICES:
            return False, f"Unknown category: {category}"

        services = self.SERVICES[category]["services"]
        results = []
        original_types = self.disabled_services.setdefault(
            "original_start_types", {})
        original_running = self.disabled_services.setdefault(
            "original_running", {})

        for service in services:
            if should_disable:
                original = self.get_service_start_type(service)
                if original == "disabled":
                    success, msg = True, (
                        f"Service {service} was already disabled; unchanged")
                else:
                    # Preserve the exact reversible state before touching it.
                    # `demand` is the conservative fallback when Windows does
                    # not expose the original type but the disable later works.
                    original_types.setdefault(service, original or "demand")
                    original_running.setdefault(
                        service, self.get_service_status(service) == "Running")
                    success, msg = self.disable_service(service)
                    if not success:
                        original_types.pop(service, None)
                        original_running.pop(service, None)
                if (success and original != "disabled"
                        and service not in
                        self.disabled_services.get("disabled", [])):
                    self.disabled_services.setdefault("disabled", []).append(service)
            else:
                success, msg = self._restore_service_state(service)
                if success and service in self.disabled_services.get("disabled", []):
                    self.disabled_services["disabled"].remove(service)
                    original_types.pop(service, None)
                    original_running.pop(service, None)

            results.append((service, success, msg))

        saved = self.save_config()
        all_ok = bool(results) and all(row[1] for row in results) and saved
        return all_ok, results

    def get_disabled_services_summary(self):
        """Get summary of currently disabled services"""
        disabled = self.disabled_services.get("disabled", [])
        timestamp = self.disabled_services.get("timestamp", "Never")

        summary = {
            "count": len(disabled),
            "services": disabled,
            "timestamp": timestamp
        }

        return summary

    def restore_all_services(self):
        """Re-enable all previously disabled services"""
        disabled = list(self.disabled_services.get("disabled", []))
        original_types = self.disabled_services.setdefault(
            "original_start_types", {})
        original_running = self.disabled_services.setdefault(
            "original_running", {})
        results = []

        for service in disabled:
            success, msg = self._restore_service_state(service)
            results.append((service, success, msg))
            if success:
                try:
                    self.disabled_services["disabled"].remove(service)
                except ValueError:
                    pass
                original_types.pop(service, None)
                original_running.pop(service, None)

        self.save_config()

        return results
