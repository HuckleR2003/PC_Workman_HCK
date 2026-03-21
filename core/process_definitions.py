# core/process_definitions.py
"""
Process Definitions Database
Contains descriptions and information about common processes
"""

PROCESS_DEFINITIONS = {
    # Browsers
    'chrome.exe': {
        'full_name': 'Google Chrome',
        'category': 'Web Browser',
        'description': 'Google Chrome is a cross-platform web browser developed by Google. Known for high RAM usage due to multi-process architecture.',
        'purpose': 'Web browsing, running web applications',
        'normal_behavior': 'High RAM usage (200-2000MB), moderate CPU usage',
        'warning': 'Each tab runs as separate process. Mocny Rywal - consumes significant RAM!',
        'developer': 'Google LLC'
    },
    'firefox.exe': {
        'full_name': 'Mozilla Firefox',
        'category': 'Web Browser',
        'description': 'Mozilla Firefox is a free and open-source web browser developed by the Mozilla Foundation.',
        'purpose': 'Web browsing with focus on privacy',
        'normal_behavior': 'Moderate RAM usage (150-1000MB), low-moderate CPU',
        'warning': 'Mocny Rywal - multiple processes for tabs and extensions',
        'developer': 'Mozilla Foundation'
    },
    'msedge.exe': {
        'full_name': 'Microsoft Edge',
        'category': 'Web Browser',
        'description': 'Microsoft Edge is a Chromium-based web browser developed by Microsoft.',
        'purpose': 'Web browsing, integrated with Windows',
        'normal_behavior': 'High RAM usage (similar to Chrome)',
        'warning': 'Mocny Rywal - Chromium-based architecture',
        'developer': 'Microsoft Corporation'
    },

    # Development Tools
    'code.exe': {
        'full_name': 'Visual Studio Code',
        'category': 'Development Tool',
        'description': 'VS Code is a source-code editor developed by Microsoft. Built on Electron framework.',
        'purpose': 'Code editing, development, debugging',
        'normal_behavior': 'Moderate RAM (200-800MB), low-moderate CPU',
        'warning': 'Can use significant RAM with many extensions',
        'developer': 'Microsoft Corporation'
    },
    'devenv.exe': {
        'full_name': 'Visual Studio IDE',
        'category': 'Development Tool',
        'description': 'Microsoft Visual Studio integrated development environment.',
        'purpose': 'Full-featured IDE for .NET and C++ development',
        'normal_behavior': 'High RAM usage (500-2000MB), moderate CPU',
        'warning': 'Resource-intensive application',
        'developer': 'Microsoft Corporation'
    },

    # System Processes
    'explorer.exe': {
        'full_name': 'Windows Explorer',
        'category': 'System Process',
        'description': 'Windows Explorer provides the Windows desktop environment, taskbar, and file management.',
        'purpose': 'Desktop shell and file explorer',
        'normal_behavior': 'Low RAM (50-200MB), minimal CPU',
        'warning': 'CRITICAL PROCESS - Do not terminate!',
        'developer': 'Microsoft Corporation'
    },
    'dwm.exe': {
        'full_name': 'Desktop Window Manager',
        'category': 'System Process',
        'description': 'DWM manages visual effects, animations, and desktop composition in Windows.',
        'purpose': 'Graphics rendering and window management',
        'normal_behavior': 'Low-moderate RAM (50-150MB), low CPU (0-5%)',
        'warning': 'CRITICAL - Handles Aero effects and transparency',
        'developer': 'Microsoft Corporation'
    },
    'system': {
        'full_name': 'System',
        'category': 'System Process',
        'description': 'Core Windows system process managing kernel-mode drivers and system threads.',
        'purpose': 'System-level operations',
        'normal_behavior': 'Low RAM, very low CPU unless I/O operations',
        'warning': 'CRITICAL SYSTEM PROCESS - Never terminate!',
        'developer': 'Microsoft Corporation'
    },
    'svchost.exe': {
        'full_name': 'Service Host',
        'category': 'System Process',
        'description': 'Generic host process for Windows services. Multiple instances normal.',
        'purpose': 'Hosts multiple Windows services',
        'normal_behavior': 'Variable - depends on hosted services',
        'warning': 'CRITICAL - Multiple instances are normal',
        'developer': 'Microsoft Corporation'
    },

    # Communication
    'discord.exe': {
        'full_name': 'Discord',
        'category': 'Communication',
        'description': 'Discord is a VoIP and instant messaging platform. Built on Electron.',
        'purpose': 'Voice chat, messaging, streaming',
        'normal_behavior': 'Moderate RAM (150-400MB), low-moderate CPU',
        'warning': 'Can use significant resources during voice/video calls',
        'developer': 'Discord Inc.'
    },
    'teams.exe': {
        'full_name': 'Microsoft Teams',
        'category': 'Communication',
        'description': 'Microsoft Teams is a collaboration and communication platform.',
        'purpose': 'Video meetings, chat, collaboration',
        'normal_behavior': 'High RAM (300-800MB), moderate CPU',
        'warning': 'Resource-intensive, especially during video calls',
        'developer': 'Microsoft Corporation'
    },

    # Gaming
    'steam.exe': {
        'full_name': 'Steam Client',
        'category': 'Gaming Platform',
        'description': 'Steam is a digital distribution platform for video games.',
        'purpose': 'Game library, downloads, community features',
        'normal_behavior': 'Moderate RAM (100-400MB), low CPU',
        'warning': 'Can use significant bandwidth when downloading',
        'developer': 'Valve Corporation'
    },

    # Default/Unknown
    '_default': {
        'full_name': 'Unknown Process',
        'category': 'Unknown',
        'description': 'This process is not in our database yet.',
        'purpose': 'Unknown - Research recommended',
        'normal_behavior': 'Variable',
        'warning': 'If you don\'t recognize this process, research it online',
        'developer': 'Unknown'
    }
}


def get_process_definition(process_name):
    """
    Get definition for a process

    Args:
        process_name: Process name (e.g., 'chrome.exe')

    Returns:
        dict: Process definition
    """
    process_name = process_name.lower()

    if process_name in PROCESS_DEFINITIONS:
        return PROCESS_DEFINITIONS[process_name]
    else:
        return PROCESS_DEFINITIONS['_default']
