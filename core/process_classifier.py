# core/process_classifier.py
"""
Enhanced Process Classifier for PC Workman
Classifies processes into: Programs, Browsers, System
"""

from import_core import register_component
import json
import os

# Process classification database
# 🔍 = Browser (Mocny Rywal!)
BROWSER_PROCESSES = {
    'chrome.exe': {'name': 'Google Chrome', 'icon': '🔍', 'rival': True},
    'firefox.exe': {'name': 'Mozilla Firefox', 'icon': '🔍', 'rival': True},
    'msedge.exe': {'name': 'Microsoft Edge', 'icon': '🔍', 'rival': True},
    'opera.exe': {'name': 'Opera', 'icon': '🔍', 'rival': True},
    'brave.exe': {'name': 'Brave', 'icon': '🔍', 'rival': True},
    'vivaldi.exe': {'name': 'Vivaldi', 'icon': '🔍', 'rival': True},
    'safari.exe': {'name': 'Safari', 'icon': '🔍', 'rival': True},
    'iexplore.exe': {'name': 'Internet Explorer', 'icon': '🔍', 'rival': True},
}

SYSTEM_PROCESSES = {
    'system': {'name': 'System', 'icon': '', 'critical': True},
    'explorer.exe': {'name': 'Windows Explorer', 'icon': '', 'critical': True},
    'svchost.exe': {'name': 'Service Host', 'icon': '', 'critical': True},
    'dwm.exe': {'name': 'Desktop Window Manager', 'icon': '', 'critical': True},
    'csrss.exe': {'name': 'Client/Server Runtime', 'icon': '', 'critical': True},
    'lsass.exe': {'name': 'Local Security Authority', 'icon': '', 'critical': True},
    'services.exe': {'name': 'Services Control Manager', 'icon': '', 'critical': True},
    'winlogon.exe': {'name': 'Windows Logon', 'icon': '', 'critical': True},
    'smss.exe': {'name': 'Session Manager', 'icon': '', 'critical': True},
    'wininit.exe': {'name': 'Windows Init', 'icon': '', 'critical': True},
    'taskhostw.exe': {'name': 'Task Host Window', 'icon': '', 'critical': False},
    'searchindexer.exe': {'name': 'Search Indexer', 'icon': '', 'critical': False},
    'spoolsv.exe': {'name': 'Print Spooler', 'icon': '', 'critical': False},
    'audiodg.exe': {'name': 'Audio Device Graph', 'icon': '', 'critical': False},
    'conhost.exe': {'name': 'Console Host', 'icon': '', 'critical': False},
}

PROGRAM_CATEGORIES = {
    # Development Tools
    'code.exe': {'name': 'VS Code', 'icon': '', 'category': 'Development'},
    'devenv.exe': {'name': 'Visual Studio', 'icon': '', 'category': 'Development'},
    'pycharm64.exe': {'name': 'PyCharm', 'icon': '', 'category': 'Development'},
    'idea64.exe': {'name': 'IntelliJ IDEA', 'icon': '', 'category': 'Development'},
    'sublime_text.exe': {'name': 'Sublime Text', 'icon': '', 'category': 'Development'},
    'notepad++.exe': {'name': 'Notepad++', 'icon': '', 'category': 'Development'},
    'atom.exe': {'name': 'Atom', 'icon': '', 'category': 'Development'},

    # Gaming
    'steam.exe': {'name': 'Steam', 'icon': '', 'category': 'Gaming'},
    'epicgameslauncher.exe': {'name': 'Epic Games', 'icon': '', 'category': 'Gaming'},
    'battlenet.exe': {'name': 'Battle.net', 'icon': '', 'category': 'Gaming'},
    'origin.exe': {'name': 'Origin', 'icon': '', 'category': 'Gaming'},
    'uplay.exe': {'name': 'Uplay', 'icon': '', 'category': 'Gaming'},
    'gog.exe': {'name': 'GOG Galaxy', 'icon': '', 'category': 'Gaming'},

    # Communication
    'discord.exe': {'name': 'Discord', 'icon': '', 'category': 'Communication'},
    'slack.exe': {'name': 'Slack', 'icon': '', 'category': 'Communication'},
    'teams.exe': {'name': 'Microsoft Teams', 'icon': '', 'category': 'Communication'},
    'skype.exe': {'name': 'Skype', 'icon': '', 'category': 'Communication'},
    'zoom.exe': {'name': 'Zoom', 'icon': '', 'category': 'Communication'},

    # Media
    'spotify.exe': {'name': 'Spotify', 'icon': '', 'category': 'Media'},
    'vlc.exe': {'name': 'VLC Media Player', 'icon': '', 'category': 'Media'},
    'obs64.exe': {'name': 'OBS Studio', 'icon': '', 'category': 'Media'},
    'photoshop.exe': {'name': 'Photoshop', 'icon': '', 'category': 'Media'},
    'gimp.exe': {'name': 'GIMP', 'icon': '', 'category': 'Media'},

    # Utilities
    'winrar.exe': {'name': 'WinRAR', 'icon': '', 'category': 'Utilities'},
    '7zfm.exe': {'name': '7-Zip', 'icon': '', 'category': 'Utilities'},
    'notepad.exe': {'name': 'Notepad', 'icon': '', 'category': 'Utilities'},
    'calc.exe': {'name': 'Calculator', 'icon': '', 'category': 'Utilities'},
}


class ProcessClassifier:
    """Enhanced process classification with detailed categorization"""

    def __init__(self):
        self.name = "core.process_classifier"
        register_component(self.name, self)

        # Load custom patterns if exists
        self.custom_patterns = self._load_custom_patterns()

    def _load_custom_patterns(self):
        """Load user-defined process patterns"""
        pattern_file = os.path.join('data', 'process_info', 'process_patterns.json')
        if os.path.exists(pattern_file):
            try:
                with open(pattern_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def classify_process(self, process_name):
        """
        Classify a process into category

        Args:
            process_name: Process executable name (e.g., 'chrome.exe')

        Returns:
            dict: {
                'type': 'browser' | 'system' | 'program' | 'unknown',
                'display_name': str,
                'icon': str (emoji),
                'category': str (for programs),
                'is_rival': bool (for browsers),
                'is_critical': bool (for system)
            }
        """
        process_lower = process_name.lower().strip()

        # Check browsers (RAM rivals!)
        if process_lower in BROWSER_PROCESSES:
            info = BROWSER_PROCESSES[process_lower]
            return {
                'type': 'browser',
                'display_name': info['name'],
                'icon': info['icon'],
                'category': 'Browser',
                'is_rival': info.get('rival', True),
                'is_critical': False,
                'description': f"{info['name']} - Mocny Rywal! 💪"
            }

        # Check system processes
        if process_lower in SYSTEM_PROCESSES:
            info = SYSTEM_PROCESSES[process_lower]
            return {
                'type': 'system',
                'display_name': info['name'],
                'icon': info['icon'],
                'category': 'System',
                'is_rival': False,
                'is_critical': info.get('critical', False),
                'description': f"{info['name']} - System Process"
            }

        # Check known programs
        if process_lower in PROGRAM_CATEGORIES:
            info = PROGRAM_CATEGORIES[process_lower]
            return {
                'type': 'program',
                'display_name': info['name'],
                'icon': info['icon'],
                'category': info.get('category', 'Program'),
                'is_rival': False,
                'is_critical': False,
                'description': f"{info['name']} - {info.get('category', 'Program')}"
            }

        # Check custom patterns
        if process_lower in self.custom_patterns:
            info = self.custom_patterns[process_lower]
            return {
                'type': info.get('type', 'program'),
                'display_name': info.get('name', process_name),
                'icon': info.get('icon', '📦'),
                'category': info.get('category', 'Custom'),
                'is_rival': info.get('is_rival', False),
                'is_critical': info.get('is_critical', False),
                'description': info.get('description', process_name)
            }

        # Unknown process
        return {
            'type': 'unknown',
            'display_name': process_name,
            'icon': '❓',
            'category': 'Unknown',
            'is_rival': False,
            'is_critical': False,
            'description': process_name
        }

    def is_user_process(self, process_name):
        """Check if process is a user application (not system)"""
        classification = self.classify_process(process_name)
        return classification['type'] in ['browser', 'program', 'unknown']

    def is_system_process(self, process_name):
        """Check if process is a system process"""
        classification = self.classify_process(process_name)
        return classification['type'] == 'system'

    def get_process_display_info(self, process_name, cpu_percent, ram_mb):
        """
        Get formatted display info for a process

        Returns:
            dict: Display-ready information
        """
        classification = self.classify_process(process_name)

        return {
            'name': classification['display_name'],
            'icon': classification['icon'],
            'category': classification['category'],
            'type': classification['type'],
            'cpu_percent': cpu_percent,
            'ram_mb': ram_mb,
            'is_rival': classification['is_rival'],
            'is_critical': classification['is_critical'],
            'description': classification['description']
        }


# Register instance
classifier = ProcessClassifier()
