"""utils.net_utils
Simple network check (mock)."""
import socket

def is_online(host='8.8.8.8', port=53, timeout=2):
    try:
        socket.setdefaulttimeout(timeout)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False
