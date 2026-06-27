# -*- mode: python ; coding: utf-8 -*-
# PCWorkman.spec — v1.7.7 build configuration
import os
block_cipher = None
project_root = os.path.dirname(os.path.abspath(SPEC))

# ── Data files bundled into the exe package ───────────────────────────────────
datas = [
    (os.path.join(project_root, 'data', 'icons'),            os.path.join('data', 'icons')),
    (os.path.join(project_root, 'data', 'process_info'),     os.path.join('data', 'process_info')),
    (os.path.join(project_root, 'data', 'services_config.json'), 'data'),
    (os.path.join(project_root, 'data', 'process_library.json'), 'data'),
    *([
        (os.path.join(project_root, 'assets'), 'assets')
    ] if os.path.isdir(os.path.join(project_root, 'assets')) else []),
    *([
        (os.path.join(project_root, 'settings'), 'settings')
    ] if os.path.isdir(os.path.join(project_root, 'settings')) else []),
    # Inter font (optional — bundled if present, graceful fallback to Segoe UI)
    *([
        (os.path.join(project_root, 'data', 'fonts'), os.path.join('data', 'fonts'))
    ] if os.path.isdir(os.path.join(project_root, 'data', 'fonts')) else []),
    # locales
    *([
        (os.path.join(project_root, 'locales'), 'locales')
    ] if os.path.isdir(os.path.join(project_root, 'locales')) else []),
]

# ── Hidden imports — all dynamic/late imports that PyInstaller misses ─────────
hiddenimports = [
    # Pillow
    'PIL.Image', 'PIL.ImageTk', 'PIL.ImageDraw', 'PIL.ImageFont',
    # pystray
    'pystray._win32',
    # matplotlib
    'matplotlib.backends.backend_tkagg',
    'matplotlib.backends.backend_agg',
    # ── Core ──────────────────────────────────────────────────────────────────
    'core',
    'core.monitor',
    'core.logger',
    'core.analyzer',
    'core.app_activity_tracker',
    'core.scheduler',
    'core.thermal_baseline',
    'core.voltage_analyzer',
    'core.process_classifier',
    'core.process_data_manager',
    'core.hardware_sensors',
    'core.hardware_detector',
    'core.fps_monitor',
    'core.network',
    'core.telemetry',
    'core.hibernation_manager',
    'core.process_definitions',
    # ── Stats Engine ──────────────────────────────────────────────────────────
    'hck_stats_engine',
    'hck_stats_engine.avg_calculator',
    'hck_stats_engine.db_manager',
    'hck_stats_engine.aggregator',
    'hck_stats_engine.process_aggregator',
    'hck_stats_engine.query_api',
    'hck_stats_engine.events',
    'hck_stats_engine.constants',
    # ── hck_GPT — AI assistant (all subpackages) ──────────────────────────────
    'hck_gpt',
    'hck_gpt.chat_handler',
    'hck_gpt.insights',
    'hck_gpt.panel',
    'hck_gpt.tooltip',
    'hck_gpt.process_library',
    'hck_gpt.services_manager',
    'hck_gpt.service_setup_wizard',
    # intents
    'hck_gpt.intents',
    'hck_gpt.intents.parser',
    'hck_gpt.intents.vocabulary',
    'hck_gpt.intents.lang_detect',
    'hck_gpt.intents.ml_classifier',
    'hck_gpt.intents.train_classifier',
    # responses
    'hck_gpt.responses',
    'hck_gpt.responses.builder',
    # memory
    'hck_gpt.memory',
    'hck_gpt.memory.session_memory',
    'hck_gpt.memory.proactive_monitor',
    'hck_gpt.memory.user_knowledge',
    # context
    'hck_gpt.context',
    'hck_gpt.context.system_context',
    'hck_gpt.context.hardware_scanner',
    # engine (Ollama hybrid)
    'hck_gpt.engine',
    'hck_gpt.engine.hybrid_engine',
    # ── UI — windows ──────────────────────────────────────────────────────────
    'ui',
    'ui.theme',
    'ui.dialogs',
    'ui.splash_screen',
    'ui.system_tray',
    'ui.overlay_mini_monitor',
    'ui.windows',
    'ui.windows.main_window',
    'ui.windows.main_window_expanded',
    # ── UI — components ───────────────────────────────────────────────────────
    'ui.components',
    'ui.components.led_bars',
    'ui.components.charts',
    'ui.components.process_tooltip',
    'ui.components.sensor_tree',
    'ui.components.sensor_kb',
    'ui.components.hardware_graphs',
    'ui.components.fan_curve_editor',
    'ui.components.fan_dashboard',
    'ui.components.pro_info_table',
    'ui.components.pc_map',
    'ui.components.interactive_chart',
    'ui.components.sidebar_nav',
    'ui.components.yourpc_page',
    'ui.components.system_toast',
    'ui.components.ingame_overlay',
    # ── UI — pages ────────────────────────────────────────────────────────────
    'ui.pages',
    'ui.pages.page_all_stats',
    'ui.pages.page_day_stats',
    'ui.pages.optimization_services',
    'ui.pages.monitoring_alerts',
    'ui.pages.stability_tests',
    'ui.pages.first_setup_drivers',
    'ui.pages.fan_control',
    'ui.pages.fan_control.hardware_info',
    'ui.pages.fan_control.usage_stats',
    'ui.pages.startup_manager',
    'ui.pages.services_manager',
    # ── Utils ─────────────────────────────────────────────────────────────────
    'utils',
    'utils.fonts',
    'utils.i18n',
    'utils.paths',
    # ── hck_gpt.data (DeepMonitor metrics) ───────────────────────────────────
    'hck_gpt.data',
    'hck_gpt.data.metrics_store',
    # ── ui.guide ─────────────────────────────────────────────────────────────
    'ui.guide',
    'ui.guide.live_guide',
    # ── ui.pages extras ───────────────────────────────────────────────────────
    'ui.pages.settings_page',
    # ── Stdlib modules that PyInstaller sometimes misses on Python 3.14 ───────
    'sqlite3',
    'unittest',
    'unittest.mock',
    'ctypes',
    'ctypes.util',
    'ctypes.wintypes',
    'winreg',
    'platform',
    'subprocess',
    # ── Entry point helper ────────────────────────────────────────────────────
    'import_core',
]

a = Analysis(
    [os.path.join(project_root, 'startup.py')],
    pathex=[project_root],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[os.path.join(project_root, 'pyi_rth_subprocess.py')],
    excludes=['pytest', '_pytest'],   # unittest kept — stdlib, needed transitively
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PC Workman HCK',
    debug=False,
    strip=False,
    upx=False,
    console=True,   # Shows diagnostic console — hides itself on successful launch
    icon=os.path.join(project_root, 'data', 'icons', 'PCWorkman.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='PC_Workman_HCK_1.8.0',
)
