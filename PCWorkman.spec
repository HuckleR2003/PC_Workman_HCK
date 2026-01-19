# -*- mode: python ; coding: utf-8 -*-
import os
block_cipher = None
project_root = os.path.dirname(os.path.abspath(SPEC))

datas = [
    (os.path.join(project_root, 'data', 'icons'), os.path.join('data', 'icons')),
    (os.path.join(project_root, 'settings'), 'settings'),
    (os.path.join(project_root, 'data', 'process_info'), os.path.join('data', 'process_info')),
    (os.path.join(project_root, 'data', 'cache'), os.path.join('data', 'cache')),
    (os.path.join(project_root, 'data', 'logs'), os.path.join('data', 'logs')),
    (os.path.join(project_root, 'data', 'services_config.json'), 'data'),
]

hiddenimports = [
    'PIL.Image', 'PIL.ImageTk', 'PIL.ImageDraw',
    'pystray._win32',
    'matplotlib.backends.backend_tkagg',
    'core', 'core.monitor', 'core.logger', 'core.analyzer', 'core.scheduler',
    'core.process_classifier', 'core.process_data_manager', 'core.hardware_sensors', 'core.process_definitions',
    'ui', 'ui.theme', 'ui.dialogs', 'ui.splash_screen', 'ui.system_tray', 'ui.overlay_widget',
    'ui.overlay_mini_monitor', 'ui.hck_gpt_panel',
    'ui.windows', 'ui.windows.main_window', 'ui.windows.main_window_expanded',
    'ui.components', 'ui.components.led_bars', 'ui.components.charts', 'ui.components.expandable_list',
    'ui.components.process_tooltip', 'ui.components.sensor_tree', 'ui.components.hardware_graphs',
    'ui.components.fan_curve_editor', 'ui.components.fan_dashboard', 'ui.components.pro_info_table',
    'ui.pages', 'ui.pages.page_all_stats', 'ui.pages.page_day_stats',
    'hck_stats_engine', 'hck_stats_engine.avg_calculator', 'hck_stats_engine.trend_analysis', 'hck_stats_engine.time_utils',
    'hck_gpt', 'hck_gpt.services_manager', 'hck_gpt.service_setup_wizard', 'hck_gpt.chat_handler',
    'utils', 'utils.file_utils', 'utils.net_utils', 'utils.system_info',
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
    excludes=['test', 'tests', 'pytest'],  # Keep unittest - used by main_window
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
    upx=True,
    console=True,
    icon=os.path.join(project_root, 'data', 'icons', 'HCKintro.png'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='.',  # Output directly to dist folder (cleaner structure)
)
