"""utils.system_info
Basic system info collector (mock)."""
import platform

def get_system_info():
    return {
        'platform': platform.system(),
        'platform_version': platform.version(),
        'processor': platform.processor()
    }
