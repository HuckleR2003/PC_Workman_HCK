# hck_gpt/services_manager.py
"""
Windows Services Manager
Handles enabling/disabling Windows services based on user needs
"""

import subprocess
import platform
import json
import os

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

    def __init__(self, config_path="data/services_config.json"):
        self.config_path = config_path
        self.disabled_services = self.load_config()
        self.is_windows = platform.system() == "Windows"

    def load_config(self):
        """Load saved services configuration"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
        return {"disabled": [], "timestamp": None}

    def save_config(self):
        """Save current services configuration"""
        import time
        self.disabled_services["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.disabled_services, f, indent=2)
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
                text=True,
                timeout=5
            )

            if "RUNNING" in result.stdout:
                return "Running"
            elif "STOPPED" in result.stdout:
                return "Stopped"
            else:
                return "Unknown"
        except Exception as e:
            return f"Error: {str(e)}"

    def disable_service(self, service_name):
        """Disable a Windows service"""
        if not self.is_windows:
            return False, "Not Windows OS"

        try:
            # Stop the service
            subprocess.run(
                ["sc", "stop", service_name],
                capture_output=True,
                timeout=10
            )

            # Disable the service
            result = subprocess.run(
                ["sc", "config", service_name, "start=", "disabled"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return True, f"Service {service_name} disabled successfully"
            else:
                return False, f"Failed to disable {service_name}"
        except Exception as e:
            return False, f"Error: {str(e)}"

    def enable_service(self, service_name):
        """Enable a Windows service"""
        if not self.is_windows:
            return False, "Not Windows OS"

        try:
            # Enable the service
            result = subprocess.run(
                ["sc", "config", service_name, "start=", "demand"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return True, f"Service {service_name} enabled successfully"
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

        for service in services:
            if should_disable:
                success, msg = self.disable_service(service)
                if success and service not in self.disabled_services.get("disabled", []):
                    self.disabled_services.setdefault("disabled", []).append(service)
            else:
                success, msg = self.enable_service(service)
                if success and service in self.disabled_services.get("disabled", []):
                    self.disabled_services["disabled"].remove(service)

            results.append((service, success, msg))

        self.save_config()
        return True, results

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
        disabled = self.disabled_services.get("disabled", [])
        results = []

        for service in disabled:
            success, msg = self.enable_service(service)
            results.append((service, success, msg))

        if all(r[1] for r in results):
            self.disabled_services["disabled"] = []
            self.save_config()

        return results
