"""core.net_check - a quick look at the internet connection (2026-11-20).

hck_GPT answered "internet is slow" with a general checklist. Now it tests
first, in about two to four seconds, and says what it measured:

  * the home router (the default gateway): reachable, how fast, any loss;
  * google.com: the name resolved (DNS), ping, jitter, loss;
  * 1.1.1.1 by address, so a DNS fault can be told apart from no internet;
  * a TCP connection to google.com:443, which works where ICMP is blocked.

Pings go through IcmpSendEcho (iphlpapi.dll): no administrator rights, and
no parsing of ping.exe output, which Windows translates (Polish "czas=").

speed_test() downloads a test file from Cloudflare's speed endpoint and
measures the download rate. It sends nothing about the user, but it does go
out to a server, so it runs only when the user asks for it.

    check() -> dict        verdict(result) -> (level, key)
"""
from __future__ import annotations

import socket
import time
from typing import Dict, List, Optional, Tuple

TARGET = "google.com"
BY_ADDRESS = "1.1.1.1"
PINGS = 4
TIMEOUT_MS = 1000
SPEED_URL = "https://speed.cloudflare.com/__down?bytes={n}"
SPEED_BYTES = 25_000_000


# ── ping without ping.exe ────────────────────────────────────────────────
def _icmp_ms(ip: str, timeout_ms: int = TIMEOUT_MS) -> Optional[float]:
    """Round trip in ms to an IPv4 address, None when there is no reply."""
    try:
        import ctypes
        from ctypes import wintypes

        class _IPOpt(ctypes.Structure):
            _fields_ = [("Ttl", ctypes.c_ubyte), ("Tos", ctypes.c_ubyte),
                        ("Flags", ctypes.c_ubyte), ("OptionsSize", ctypes.c_ubyte),
                        ("OptionsData", ctypes.c_void_p)]

        class _Reply(ctypes.Structure):
            _fields_ = [("Address", wintypes.ULONG), ("Status", wintypes.ULONG),
                        ("RoundTripTime", wintypes.ULONG), ("DataSize", wintypes.USHORT),
                        ("Reserved", wintypes.USHORT), ("Data", ctypes.c_void_p),
                        ("Options", _IPOpt)]
        iph = ctypes.windll.iphlpapi
        iph.IcmpCreateFile.restype = wintypes.HANDLE
        h = iph.IcmpCreateFile()
        if not h or h == wintypes.HANDLE(-1).value:
            return None
        try:
            addr = int.from_bytes(socket.inet_aton(ip), "little")
            data = b"pcworkman"
            size = ctypes.sizeof(_Reply) + len(data) + 8
            buf = ctypes.create_string_buffer(size)
            n = iph.IcmpSendEcho(wintypes.HANDLE(h), wintypes.ULONG(addr), data, len(data),
                                 None, buf, size, timeout_ms)
            if n == 0:
                return None
            rep = _Reply.from_buffer_copy(buf)
            if rep.Status != 0:
                return None
            return float(max(rep.RoundTripTime, 0.5))
        finally:
            iph.IcmpCloseHandle(wintypes.HANDLE(h))
    except Exception:
        return None


def ping(ip: str, count: int = PINGS, timeout_ms: int = TIMEOUT_MS) -> Dict:
    """{"sent", "lost", "avg", "min", "max", "jitter"} in ms (None when all lost)."""
    times: List[float] = []
    for i in range(count):
        t = _icmp_ms(ip, timeout_ms)
        if t is not None:
            times.append(t)
        if i < count - 1:
            time.sleep(0.15)
    out = {"sent": count, "lost": count - len(times), "avg": None, "min": None,
           "max": None, "jitter": None}
    if times:
        out.update(avg=sum(times) / len(times), min=min(times), max=max(times),
                   jitter=(sum(abs(a - b) for a, b in zip(times, times[1:])) / (len(times) - 1)
                           if len(times) > 1 else 0.0))
    return out


def gateway() -> Optional[str]:
    """The default gateway (the home router), from the IPv4 route table."""
    try:
        import ctypes
        from ctypes import wintypes

        class _Row(ctypes.Structure):
            _fields_ = [("dwForwardDest", wintypes.DWORD), ("dwForwardMask", wintypes.DWORD),
                        ("dwForwardPolicy", wintypes.DWORD), ("dwForwardNextHop", wintypes.DWORD),
                        ("dwForwardIfIndex", wintypes.DWORD), ("dwForwardType", wintypes.DWORD),
                        ("dwForwardProto", wintypes.DWORD), ("dwForwardAge", wintypes.DWORD),
                        ("dwForwardNextHopAS", wintypes.DWORD), ("dwForwardMetric1", wintypes.DWORD),
                        ("dwForwardMetric2", wintypes.DWORD), ("dwForwardMetric3", wintypes.DWORD),
                        ("dwForwardMetric4", wintypes.DWORD), ("dwForwardMetric5", wintypes.DWORD)]
        row = _Row()
        # the route Windows would use to reach 8.8.8.8: its next hop is the gateway
        dest = int.from_bytes(socket.inet_aton("8.8.8.8"), "little")
        if ctypes.windll.iphlpapi.GetBestRoute(wintypes.DWORD(dest), 0, ctypes.byref(row)) != 0:
            return None
        hop = socket.inet_ntoa(int(row.dwForwardNextHop).to_bytes(4, "little"))
        return None if hop == "0.0.0.0" else hop
    except Exception:
        return None


def adapter() -> Dict:
    """{"kind": "wifi" | "ethernet" | "other" | None, "name", "speed_mbps"} of
    the adapter that is up and carries the default route (best guess)."""
    try:
        import psutil
        stats = psutil.net_if_stats()
        best = None
        for name, st in stats.items():
            low = name.lower()
            if not st.isup or "loopback" in low or "vethernet" in low or "virtual" in low \
                    or "bluetooth" in low or low.startswith(("vmware", "virtualbox", "tailscale", "zerotier")):
                continue
            kind = ("wifi" if any(k in low for k in ("wi-fi", "wifi", "wlan", "wireless", "bezprzew"))
                    else "ethernet" if any(k in low for k in ("ethernet", "lan", "eth", "przewod")) else "other")
            cand = {"kind": kind, "name": name, "speed_mbps": st.speed or None}
            if best is None or (best["kind"] == "other" and kind != "other"):
                best = cand
        return best or {"kind": None, "name": "", "speed_mbps": None}
    except Exception:
        return {"kind": None, "name": "", "speed_mbps": None}


def _dns_ms(host: str) -> Tuple[Optional[str], Optional[float]]:
    t = time.perf_counter()
    try:
        ip = socket.getaddrinfo(host, 443, socket.AF_INET, socket.SOCK_STREAM)[0][4][0]
        return ip, (time.perf_counter() - t) * 1000
    except Exception:
        return None, None


def _tcp_ms(ip: str, port: int = 443, timeout: float = 3.0) -> Optional[float]:
    t = time.perf_counter()
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return (time.perf_counter() - t) * 1000
    except Exception:
        return None


def check() -> Dict:
    """The quick test. Takes 2-4 s; offline it ends sooner."""
    res = {"ts": time.time(), "target": TARGET, "adapter": adapter(), "gateway": None,
           "gw": None, "dns_ip": None, "dns_ms": None, "web": None, "raw": None, "tcp_ms": None}
    gw = gateway()
    res["gateway"] = gw
    if gw:
        res["gw"] = ping(gw, count=3, timeout_ms=600)
    ip, ms = _dns_ms(TARGET)
    res["dns_ip"], res["dns_ms"] = ip, ms
    if ip:
        res["web"] = ping(ip)
        res["tcp_ms"] = _tcp_ms(ip)
    res["raw"] = ping(BY_ADDRESS, count=2)
    return res


def _ok(p: Optional[Dict]) -> bool:
    return bool(p) and p["lost"] < p["sent"]


def verdict(r: Dict) -> Tuple[str, str]:
    """(level, key): level "ok" | "warn" | "bad"; key names the finding."""
    gw_ok = _ok(r.get("gw"))
    web, raw = r.get("web"), r.get("raw")
    reach = _ok(web) or r.get("tcp_ms") is not None or _ok(raw)
    if not r.get("gateway") and not reach:
        return "bad", "no_network"          # no route at all: cable / Wi-Fi off
    if r.get("gateway") and not gw_ok and not reach:
        return "bad", "no_router"           # route exists, router silent
    if not reach:
        return "bad", "no_internet"         # router answers, the internet does not
    if r.get("dns_ip") is None:
        return "bad", "dns"                 # addresses work, names do not
    if r.get("gw") and r["gw"]["lost"] > 0:
        return "warn", "local_loss"
    if web and web["lost"] > 0:
        return "warn", "loss"
    avg = (web or {}).get("avg") or r.get("tcp_ms") or 0
    jit = (web or {}).get("jitter") or 0
    gw_avg = (r.get("gw") or {}).get("avg") or 0
    if gw_avg > 20:
        return "warn", "slow_local"         # the Wi-Fi hop itself is slow
    if avg > 100:
        return "warn", "high_ping"
    if jit > 25:
        return "warn", "jitter"
    if (r.get("dns_ms") or 0) > 300:
        return "warn", "slow_dns"
    return "ok", "good"


def speed_test(n_bytes: int = SPEED_BYTES, timeout: float = 25.0) -> Dict:
    """Download speed in Mb/s from Cloudflare's test endpoint. Only on request."""
    import urllib.request
    url = SPEED_URL.format(n=int(n_bytes))
    req = urllib.request.Request(url, headers={"User-Agent": "PCWorkman-speedtest"})
    got, t0 = 0, time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            while True:
                chunk = resp.read(256 * 1024)
                if not chunk:
                    break
                got += len(chunk)
                if time.perf_counter() - t0 > timeout:
                    break
        secs = max(1e-3, time.perf_counter() - t0)
        return {"ok": got > 0, "mbps": got * 8 / secs / 1e6, "bytes": got, "secs": secs}
    except Exception as e:
        return {"ok": False, "mbps": None, "bytes": got, "secs": time.perf_counter() - t0,
                "error": type(e).__name__}
