# core/process_data_manager.py
"""
Process Data Manager - Enhanced tracking of process usage
Saves detailed process data with classification and statistics
"""

from import_core import register_component
import json
import os
import time
from datetime import datetime
from collections import defaultdict, deque

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'process_info')
os.makedirs(DATA_DIR, exist_ok=True)

PROCESS_HISTORY_FILE = os.path.join(DATA_DIR, 'process_history.json')
PROCESS_STATS_FILE = os.path.join(DATA_DIR, 'process_statistics.json')
DAILY_SUMMARY_FILE = os.path.join(DATA_DIR, 'daily_summary.json')


class ProcessDataManager:
    """Manages detailed process data collection and statistics"""

    def __init__(self):
        self.name = "core.process_data_manager"
        register_component(self.name, self)

        # In-memory buffers
        self.current_session = {
            'start_time': time.time(),
            'processes': defaultdict(lambda: {
                'total_cpu_time': 0.0,
                'total_ram_time': 0.0,
                'peak_cpu': 0.0,
                'peak_ram': 0.0,
                'samples': 0,
                'first_seen': None,
                'last_seen': None,
                'classifications': {}
            })
        }

        # Recent snapshots (last hour)
        self.recent_snapshots = deque(maxlen=3600)  # 1 hour at 1 sample/sec

        # Load existing statistics
        self.statistics = self._load_statistics()
        self.daily_summary = self._load_daily_summary()

    def _load_statistics(self):
        """Load process statistics from file"""
        if os.path.exists(PROCESS_STATS_FILE):
            try:
                with open(PROCESS_STATS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            'total_runtime_seconds': 0,
            'processes': {},
            'last_updated': None
        }

    def _load_daily_summary(self):
        """Load daily summary from file"""
        if os.path.exists(DAILY_SUMMARY_FILE):
            try:
                with open(DAILY_SUMMARY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def record_process_snapshot(self, processes_list, classifier):
        """
        Record current process snapshot with classification

        Args:
            processes_list: List of process dicts [{pid, name, cpu_percent, ram_MB}, ...]
            classifier: ProcessClassifier instance
        """
        timestamp = time.time()

        # Create snapshot with classifications
        snapshot = {
            'timestamp': timestamp,
            'iso_time': datetime.utcfromtimestamp(timestamp).isoformat(),
            'processes': []
        }

        for proc in processes_list:
            proc_name = proc.get('name', 'unknown').lower()
            cpu = proc.get('cpu_percent', 0.0)
            ram = proc.get('ram_MB', 0.0)

            # Classify process
            classification = classifier.classify_process(proc_name)

            # Update session data
            session_data = self.current_session['processes'][proc_name]
            session_data['total_cpu_time'] += cpu
            session_data['total_ram_time'] += ram
            session_data['peak_cpu'] = max(session_data['peak_cpu'], cpu)
            session_data['peak_ram'] = max(session_data['peak_ram'], ram)
            session_data['samples'] += 1

            if session_data['first_seen'] is None:
                session_data['first_seen'] = timestamp

            session_data['last_seen'] = timestamp
            session_data['classifications'] = classification

            # Add to snapshot
            snapshot['processes'].append({
                'pid': proc.get('pid'),
                'name': proc_name,
                'display_name': classification['display_name'],
                'type': classification['type'],
                'category': classification['category'],
                'icon': classification['icon'],
                'cpu_percent': cpu,
                'ram_MB': ram,
                'is_rival': classification['is_rival'],
                'is_critical': classification['is_critical']
            })

        # Add to recent snapshots
        self.recent_snapshots.append(snapshot)

        # Periodic save (every 5 minutes)
        if int(timestamp) % 300 == 0:
            self.save_statistics()

    def get_top_processes_by_time(self, n=10, metric='cpu'):
        """
        Get top N processes by total usage time in current session

        Args:
            n: Number of processes to return
            metric: 'cpu' or 'ram'

        Returns:
            list: Top processes with statistics
        """
        processes = []

        for proc_name, data in self.current_session['processes'].items():
            if data['samples'] == 0:
                continue

            avg_cpu = data['total_cpu_time'] / data['samples']
            avg_ram = data['total_ram_time'] / data['samples']

            runtime = data['last_seen'] - data['first_seen'] if data['first_seen'] else 0

            processes.append({
                'name': proc_name,
                'display_name': data['classifications'].get('display_name', proc_name),
                'type': data['classifications'].get('type', 'unknown'),
                'category': data['classifications'].get('category', 'Unknown'),
                'icon': data['classifications'].get('icon', '❓'),
                'avg_cpu': round(avg_cpu, 2),
                'avg_ram': round(avg_ram, 2),
                'peak_cpu': round(data['peak_cpu'], 2),
                'peak_ram': round(data['peak_ram'], 2),
                'runtime_seconds': round(runtime, 1),
                'samples': data['samples'],
                'is_rival': data['classifications'].get('is_rival', False)
            })

        # Sort by metric
        if metric == 'ram':
            processes.sort(key=lambda x: x['avg_ram'], reverse=True)
        else:
            processes.sort(key=lambda x: x['avg_cpu'], reverse=True)

        return processes[:n]

    def get_snapshot_at_time(self, timestamp):
        """
        Get process snapshot closest to specified timestamp

        Args:
            timestamp: Unix timestamp

        Returns:
            dict or None: Snapshot data
        """
        if not self.recent_snapshots:
            return None

        # Find closest snapshot
        closest = min(
            self.recent_snapshots,
            key=lambda s: abs(s['timestamp'] - timestamp)
        )

        return closest

    def get_top_processes_at_time(self, timestamp, n=5, process_type='user'):
        """
        Get TOP N processes at specific time

        Args:
            timestamp: Unix timestamp
            n: Number of processes to return
            process_type: 'user', 'system', or 'all'

        Returns:
            list: Top processes [{name, cpu, ram, type, icon}, ...]
        """
        snapshot = self.get_snapshot_at_time(timestamp)

        if not snapshot or 'processes' not in snapshot:
            return []

        processes = snapshot['processes']

        # Filter by type
        if process_type == 'user':
            processes = [p for p in processes if p.get('type') in ['program', 'browser']]
        elif process_type == 'system':
            processes = [p for p in processes if p.get('type') == 'system']

        # Sort by CPU usage
        processes_sorted = sorted(
            processes,
            key=lambda p: p.get('cpu_percent', 0) + p.get('ram_MB', 0) * 0.01,
            reverse=True
        )

        return processes_sorted[:n]

    def get_time_range_data(self, start_time, end_time):
        """
        Get all snapshots within time range

        Args:
            start_time: Start timestamp
            end_time: End timestamp

        Returns:
            list: Snapshots in range
        """
        return [
            s for s in self.recent_snapshots
            if start_time <= s['timestamp'] <= end_time
        ]

    def get_process_timeline(self, process_name, duration_seconds=3600):
        """
        Get usage timeline for specific process

        Args:
            process_name: Process name
            duration_seconds: Look-back duration

        Returns:
            list: Timeline data points
        """
        cutoff = time.time() - duration_seconds
        timeline = []

        for snapshot in self.recent_snapshots:
            if snapshot['timestamp'] < cutoff:
                continue

            # Find process in snapshot
            for proc in snapshot['processes']:
                if proc['name'].lower() == process_name.lower():
                    timeline.append({
                        'timestamp': snapshot['timestamp'],
                        'cpu_percent': proc['cpu_percent'],
                        'ram_MB': proc['ram_MB']
                    })
                    break

        return timeline

    def save_statistics(self):
        """Save current statistics to file"""
        try:
            # Update global statistics
            session_duration = time.time() - self.current_session['start_time']
            self.statistics['total_runtime_seconds'] += session_duration
            self.statistics['last_updated'] = datetime.now().isoformat()

            # Merge session data into global stats
            for proc_name, session_data in self.current_session['processes'].items():
                if proc_name not in self.statistics['processes']:
                    self.statistics['processes'][proc_name] = {
                        'total_cpu_time': 0.0,
                        'total_ram_time': 0.0,
                        'peak_cpu': 0.0,
                        'peak_ram': 0.0,
                        'total_samples': 0,
                        'classification': {}
                    }

                stats = self.statistics['processes'][proc_name]
                stats['total_cpu_time'] += session_data['total_cpu_time']
                stats['total_ram_time'] += session_data['total_ram_time']
                stats['peak_cpu'] = max(stats['peak_cpu'], session_data['peak_cpu'])
                stats['peak_ram'] = max(stats['peak_ram'], session_data['peak_ram'])
                stats['total_samples'] += session_data['samples']
                stats['classification'] = session_data['classifications']

            # Save to file
            with open(PROCESS_STATS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.statistics, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"[ProcessDataManager] Failed to save statistics: {e}")

    def get_session_summary(self):
        """Get summary of current session"""
        duration = time.time() - self.current_session['start_time']

        total_processes = len(self.current_session['processes'])
        top_cpu = self.get_top_processes_by_time(5, 'cpu')
        top_ram = self.get_top_processes_by_time(5, 'ram')

        return {
            'session_duration': duration,
            'total_unique_processes': total_processes,
            'top_cpu_consumers': top_cpu,
            'top_ram_consumers': top_ram,
            'total_snapshots': len(self.recent_snapshots)
        }


# Register instance
process_data_manager = ProcessDataManager()
