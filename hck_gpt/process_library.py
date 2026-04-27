# hck_gpt/process_library.py
"""
Process Library - Loads and queries process information
"""

import json
import os


class ProcessLibrary:
    """Loads process definitions from JSON and provides lookups"""
    
    def __init__(self):
        self.processes = {}
        self._load_library()
    
    def _load_library(self):
        """Load process_library.json"""
        try:
            # Path relative to project root
            lib_path = os.path.join(
                os.path.dirname(__file__), 
                '..', 
                'data', 
                'process_library.json'
            )
            
            if os.path.exists(lib_path):
                with open(lib_path, 'r', encoding='utf-8') as f:
                    self.processes = json.load(f)
                print(f"[ProcessLibrary] Loaded {len(self.processes)} process definitions")
            else:
                print(f"[ProcessLibrary] Warning: {lib_path} not found")
        
        except Exception as e:
            print(f"[ProcessLibrary] Load error: {e}")
            self.processes = {}
    
    def get_process_info(self, process_name):
        """
        Get process information by name (case-insensitive)
        
        Args:
            process_name: e.g. "chrome.exe", "python.exe"
        
        Returns:
            dict or None: Process info if found
        """
        # Normalize name
        process_name = process_name.lower().strip()
        
        return self.processes.get(process_name)
    
    def format_tooltip_text(self, process_name):
        """
        Format tooltip text for display
        
        Returns:
            str: Formatted tooltip or None if process not found
        """
        info = self.get_process_info(process_name)
        
        if not info:
            return None
        
        # tooltip text
        lines = []
        lines.append(f" {info['name']}")
        lines.append(f" {info['vendor']}")
        lines.append("")
        lines.append(f" {info['description']}")
        lines.append("")
        lines.append(f" Power: {info['power_usage'].replace('_', ' ').title()}")
        lines.append(f" Safety: {info['safety'].title()}")
        lines.append(f" CPU: {info['typical_cpu']}")
        lines.append(f" RAM: {info['typical_ram']}")
        
        return "\n".join(lines)


# Singleton instance
process_library = ProcessLibrary()