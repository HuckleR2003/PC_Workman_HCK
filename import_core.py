"""
import_core.py  ·  PC_Workman HCK - Component Registry
────────────────────────────────────────────────────────
Centralny rejestr singletonów aplikacji.

Każdy moduł rejestruje swoją instancję przez:
    register_component(name, obj)

  name  - stały klucz, np. 'core.monitor', 'hck_gpt.panel'
  obj   - instancja klasy (singleton)

API publiczne:
  register_component(name, obj, status)    -> rejestracja
  get_component(name)                      -> instancja lub None
  deregister_component(name)               -> usuwa z rejestru
  update_status(name, status, detail)      -> aktualizacja stanu runtime
  get_status(name)                         -> dict ze statusem lub None
  list_components(verbose)                 -> sformatowana lista tekstowa
  list_by_type(class_name)                 -> {name: obj} dla danej klasy
  count_components()                       -> int
  dump_registry()                          -> pełny dict do debugowania
"""

import time
import threading
import inspect

# ── Publiczny stan ──────────────────────────────────────────────────────────

STARTUP_TIME: float = time.time()   # czas uruchomienia (epoch)

COMPONENTS: dict = {}               # name -> obj           (główny rejestr)
_META:      dict = {}               # name -> {type, file, registered, seq}
_STATUS:    dict = {}               # name -> {status, detail, updated_at}
_LOG:       list = []               # chronologiczny log rejestracji
_SEQ:       int  = 0                # auto-incrementing registration counter

REGISTER_LOG = _LOG                 # alias wstecznej kompatybilności

_lock = threading.Lock()

# ── Stałe statusów ──────────────────────────────────────────────────────────

STATUS_OK       = "ok"
STATUS_WARN     = "warn"
STATUS_ERROR    = "error"
STATUS_STARTING = "starting"
STATUS_IDLE     = "idle"

# ── Oczekiwana kolejność startu (manifest) ───────────────────────────────────
# Lista komponentów w kolejności oczekiwanego rejestrowania.
# Użyj verify_startup() do sprawdzenia kompletności.
STARTUP_MANIFEST: list = [
    # seq  name
    (  1, "core.logger"),
    (  2, "core.monitor"),
    (  3, "core.analyzer"),
    (  4, "core.scheduler"),
    (  5, "core.hardware_sensors"),
    (  6, "core.hardware_detector"),
    (  7, "core.process_data_manager"),
    (  8, "core.process_classifier"),
    (  9, "core.turbo_services"),
    ( 10, "core.turbo_processes"),
    ( 11, "core.turbo_power"),
    ( 12, "core.startup_watcher"),
    ( 13, "hck_stats_engine.avg_calculator"),
    ( 14, "hck_stats_engine.db_manager"),
    ( 15, "hck_stats_engine.aggregator"),
    ( 16, "hck_stats_engine.query_api"),
    ( 17, "hck_gpt.chat_handler"),
    ( 18, "hck_gpt.engine"),
    ( 19, "hck_gpt.panel"),
    ( 20, "hck_gpt.proactive_monitor"),
    ( 21, "core.app_activity_tracker"),
    ( 22, "core.hibernation_manager"),
    ( 23, "core.live_collector"),      # always-on sensor producer (1.8.1)
    ( 24, "core.auto_optimizer"),      # always-on AUTO daemon (1.8.1)
]


# ── Helpers ─────────────────────────────────────────────────────────────────

def _resolve_file(obj) -> str | None:
    """Zwraca ścieżkę pliku źródłowego obiektu (przez inspect)."""
    try:
        return inspect.getfile(type(obj))
    except TypeError:
        try:
            return inspect.getfile(obj)
        except TypeError:
            return getattr(obj, "__file__", None)


# ── Core API ────────────────────────────────────────────────────────────────

def register_component(name: str, obj, status: str = STATUS_STARTING) -> object:
    """
    Rejestruje komponent globalnie.
    Zwraca obj - można użyć inline: self.x = register_component('x', obj)
    Każdy komponent dostaje unikalny numer kolejności startu (seq).
    """
    global _SEQ
    with _lock:
        now = time.time()
        _SEQ += 1
        seq = _SEQ
        COMPONENTS[name] = obj
        _META[name] = {
            "name":       name,
            "seq":        seq,
            "type":       type(obj).__name__,
            "file":       _resolve_file(obj),
            "registered": now,
        }
        _STATUS[name] = {
            "status":     status,
            "detail":     "",
            "updated_at": now,
        }
        _LOG.append({"name": name, "seq": seq, "at": now})
    return obj


def update_status(name: str, status: str, detail: str = "") -> None:
    """
    Aktualizuje status runtime komponentu.
    status: STATUS_OK | STATUS_WARN | STATUS_ERROR | STATUS_STARTING | STATUS_IDLE
    """
    with _lock:
        if name not in _STATUS:
            _STATUS[name] = {}
        _STATUS[name].update({
            "status":     status,
            "detail":     detail,
            "updated_at": time.time(),
        })


def get_status(name: str) -> dict | None:
    """Zwraca {status, detail, updated_at} lub None jeśli nie zarejestrowany."""
    return _STATUS.get(name)


def get_component(name: str):
    """Zwraca zarejestrowany komponent lub None."""
    return COMPONENTS.get(name)


def deregister_component(name: str) -> bool:
    """Usuwa komponent z rejestru. Zwraca True jeśli istniał."""
    with _lock:
        existed = name in COMPONENTS
        COMPONENTS.pop(name, None)
        _META.pop(name, None)
        _STATUS.pop(name, None)
    return existed


def count_components() -> int:
    """Liczba aktualnie zarejestrowanych komponentów."""
    return len(COMPONENTS)


def list_components(verbose: bool = False, show_ids: bool = False) -> str:
    """
    Zwraca sformatowaną listę komponentów z numerem kolejności startu.
    verbose=True  -> dodaje typ klasy, plik i status
    show_ids      -> parametr zachowany dla wstecznej kompatybilności
    """
    if not _META:
        return "(brak zarejestrowanych komponentów)"
    # Sort by registration sequence
    items = sorted(_META.items(), key=lambda kv: kv[1].get("seq", 999))
    lines = []
    for name, meta in items:
        st     = _STATUS.get(name, {})
        status = st.get("status", "?")
        seq    = meta.get("seq", 0)
        if verbose:
            cls_name  = meta.get("type", "?")
            src_file  = meta.get("file") or ""
            lines.append(
                f"[{seq:02d}] {name:<42} [{cls_name:<26}] {status:<10}  {src_file}"
            )
        else:
            lines.append(f"[{seq:02d}] {name}  [{status}]")
    return "\n".join(lines)


def verify_startup() -> dict:
    """
    Sprawdza kompletnosc startu wzgledem STARTUP_MANIFEST.
    Zwraca {
        'ok':      bool,            # True jezeli wszystkie z manifestu sa zarejestrowane
        'missing': list[str],       # komponenty z manifestu ktore nie zostaly zarejestrowane
        'extra':   list[str],       # zarejestrowane ale nie w manifescie
        'report':  str,             # sformatowany raport czytelny dla czlowieka
    }
    """
    manifest_names = {name for _, name in STARTUP_MANIFEST}
    registered     = set(COMPONENTS.keys())

    missing = sorted(manifest_names - registered)
    extra   = sorted(registered - manifest_names)

    lines = ["=== PC Workman Startup Verification ==="]
    lines.append(f"Registered: {len(registered)}  |  Manifest: {len(manifest_names)}")
    lines.append("")

    # Show manifest order with tick/cross
    for seq, name in STARTUP_MANIFEST:
        st = _STATUS.get(name, {}).get("status", "-")
        tick = "[OK]" if name in registered else "[XX]"
        lines.append(f"  {seq:02d}. {tick}  {name:<44}  {st}")

    if extra:
        lines.append("")
        lines.append(f"Extra (not in manifest): {', '.join(extra)}")

    all_ok = len(missing) == 0
    lines.append("")
    lines.append("STARTUP OK" if all_ok else f"MISSING: {', '.join(missing)}")

    return {
        "ok":      all_ok,
        "missing": missing,
        "extra":   extra,
        "report":  "\n".join(lines),
    }


def list_by_type(class_name: str) -> dict:
    """Zwraca {name: obj} dla wszystkich komponentów danej klasy."""
    return {
        name: obj
        for name, obj in COMPONENTS.items()
        if _META.get(name, {}).get("type") == class_name
    }


def dump_registry() -> dict:
    """
    Pełny dump rejestru - do debugowania, diagnostyki i monitoring page.
    Zwraca:
        {startup_time, uptime_s, count, components: {name: {meta + status}}}
    """
    return {
        "startup_time": STARTUP_TIME,
        "uptime_s":     round(time.time() - STARTUP_TIME, 1),
        "count":        len(COMPONENTS),
        "components": {
            name: {
                **_META.get(name, {}),
                "status_info": _STATUS.get(name, {}),
            }
            for name in COMPONENTS
        },
    }


# ── Self-test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    class _FakeMonitor:
        pass

    class _FakeLogger:
        pass

    class _FakeEngine:
        pass

    register_component("core.monitor", _FakeMonitor())
    register_component("core.logger",  _FakeLogger())
    register_component("hck_gpt.engine", _FakeEngine())

    update_status("core.monitor", STATUS_OK,    "uruchomiony")
    update_status("core.logger",  STATUS_OK)
    update_status("hck_gpt.engine", STATUS_IDLE, "oczekuje na wiadomość")

    print(list_components(verbose=True))
    print()
    reg = dump_registry()
    print(f"Uptime : {reg['uptime_s']} s")
    print(f"Łącznie: {reg['count']} komponentów")
