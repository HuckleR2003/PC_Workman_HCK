"""
Hardware Sensors Module - HWMonitor Style Organization
Provides hierarchical sensor data: CPU → GPU → Motherboard → Storage → RAM
"""

import psutil
import platform
import time
from typing import Dict, List, Any, Optional

# Try GPU monitoring
try:
    import GPUtil
    HAS_GPU = True
except ImportError:
    HAS_GPU = False

# Try py-cpuinfo for detailed CPU info
try:
    import cpuinfo
    HAS_CPUINFO = True
except ImportError:
    HAS_CPUINFO = False


class HardwareSensors:
    """
    Collects and organizes hardware sensor data in HWMonitor-style hierarchy
    """

    def __init__(self):
        self.last_update = 0
        self.update_interval = 1.0  # 1 second between updates
        self._cached_data = None

        # Get static hardware info once
        self.cpu_name = self._get_cpu_name()
        self.gpu_name = self._get_gpu_name()
        self.ram_total = self._get_ram_total()

    def _get_cpu_name(self) -> str:
        """Get CPU model name"""
        if HAS_CPUINFO:
            try:
                info = cpuinfo.get_cpu_info()
                return info.get('brand_raw', 'Unknown CPU')
            except:
                pass

        # Fallback
        return f"{platform.processor()} (CPU)"

    def _get_gpu_name(self) -> str:
        """Get GPU model name"""
        if HAS_GPU:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    return gpus[0].name
            except:
                pass

        return "GPU (Not detected / Integrated)"

    def _get_ram_total(self) -> float:
        """Get total RAM in GB"""
        try:
            total_bytes = psutil.virtual_memory().total
            return round(total_bytes / (1024**3), 1)  # Convert to GB
        except:
            return 0.0

    def get_sensor_tree(self, force_update: bool = False) -> Dict[str, Any]:
        """
        Get complete sensor tree in HWMonitor-style hierarchy

        Returns:
            {
                'CPU': {...},
                'GPU': {...},
                'RAM': {...},
                'Storage': {...},
                'Motherboard': {...}
            }
        """
        # Check if we need to update (throttle to 1 second)
        now = time.time()
        if not force_update and self._cached_data and (now - self.last_update) < self.update_interval:
            return self._cached_data

        # Collect fresh data
        tree = {
            'CPU': self._get_cpu_sensors(),
            'GPU': self._get_gpu_sensors(),
            'RAM': self._get_ram_sensors(),
            'Storage': self._get_storage_sensors(),
            # 'Motherboard': self._get_motherboard_sensors(),  # Requires WMI on Windows
        }

        self._cached_data = tree
        self.last_update = now
        return tree

    def _get_cpu_sensors(self) -> Dict[str, Any]:
        """Get CPU sensor data"""
        sensors = {
            'name': self.cpu_name,
            'sensors': {}
        }

        try:
            # Package temperature (overall CPU temp)
            temps = psutil.sensors_temperatures() if hasattr(psutil, 'sensors_temperatures') else {}

            if 'coretemp' in temps:  # Linux
                core_temps = temps['coretemp']
                package_temp = max([t.current for t in core_temps if 'Package' in t.label])
                sensors['sensors']['Package Temperature'] = {
                    'value': f"{int(package_temp)}°C",
                    'raw': package_temp,
                    'unit': '°C',
                    'type': 'temperature'
                }

                # Core temperatures
                for i, temp in enumerate(core_temps):
                    if 'Core' in temp.label:
                        core_num = temp.label.split()[-1]
                        sensors['sensors'][f'Core #{core_num}'] = {
                            'value': f"{int(temp.current)}°C",
                            'raw': temp.current,
                            'unit': '°C',
                            'type': 'temperature'
                        }

            else:
                # Fallback: simulated temperature based on usage
                cpu_percent = psutil.cpu_percent(interval=0.1)
                estimated_temp = 35 + (cpu_percent * 0.5)  # Rough estimate
                sensors['sensors']['Temperature (estimated)'] = {
                    'value': f"{int(estimated_temp)}°C",
                    'raw': estimated_temp,
                    'unit': '°C',
                    'type': 'temperature'
                }

            # CPU Usage
            cpu_percent = psutil.cpu_percent(interval=None)
            sensors['sensors']['Total Usage'] = {
                'value': f"{int(cpu_percent)}%",
                'raw': cpu_percent,
                'unit': '%',
                'type': 'usage'
            }

            # Per-core usage
            per_core = psutil.cpu_percent(interval=None, percpu=True)
            for i, usage in enumerate(per_core):
                sensors['sensors'][f'Core #{i} Usage'] = {
                    'value': f"{int(usage)}%",
                    'raw': usage,
                    'unit': '%',
                    'type': 'usage'
                }

            # CPU Frequency
            freq = psutil.cpu_freq()
            if freq:
                sensors['sensors']['Clock Speed'] = {
                    'value': f"{int(freq.current)} MHz",
                    'raw': freq.current,
                    'unit': 'MHz',
                    'type': 'clock'
                }

            # Power (simulated based on usage)
            estimated_power = 65 + (cpu_percent * 0.8)  # TDP estimate
            sensors['sensors']['Power (estimated)'] = {
                'value': f"{int(estimated_power)}W",
                'raw': estimated_power,
                'unit': 'W',
                'type': 'power'
            }

        except Exception as e:
            print(f"[HardwareSensors] CPU error: {e}")

        return sensors

    def _get_gpu_sensors(self) -> Dict[str, Any]:
        """Get GPU sensor data"""
        sensors = {
            'name': self.gpu_name,
            'sensors': {}
        }

        if not HAS_GPU:
            sensors['sensors']['Status'] = {
                'value': 'Not detected / Integrated',
                'raw': 0,
                'unit': '',
                'type': 'status'
            }
            return sensors

        try:
            gpus = GPUtil.getGPUs()
            if not gpus:
                sensors['sensors']['Status'] = {
                    'value': 'No GPU detected',
                    'raw': 0,
                    'unit': '',
                    'type': 'status'
                }
                return sensors

            gpu = gpus[0]  # First GPU

            # Temperature
            sensors['sensors']['Core Temperature'] = {
                'value': f"{int(gpu.temperature)}°C",
                'raw': gpu.temperature,
                'unit': '°C',
                'type': 'temperature'
            }

            # Usage
            sensors['sensors']['GPU Usage'] = {
                'value': f"{int(gpu.load * 100)}%",
                'raw': gpu.load * 100,
                'unit': '%',
                'type': 'usage'
            }

            # Memory
            sensors['sensors']['VRAM Usage'] = {
                'value': f"{gpu.memoryUsed:.1f} GB / {gpu.memoryTotal:.1f} GB ({int((gpu.memoryUsed/gpu.memoryTotal)*100)}%)",
                'raw': (gpu.memoryUsed / gpu.memoryTotal) * 100,
                'unit': '%',
                'type': 'memory'
            }

            # Clock (if available)
            # Note: GPUtil doesn't provide clock speeds, would need nvidia-smi or similar

        except Exception as e:
            print(f"[HardwareSensors] GPU error: {e}")
            sensors['sensors']['Error'] = {
                'value': str(e),
                'raw': 0,
                'unit': '',
                'type': 'error'
            }

        return sensors

    def _get_ram_sensors(self) -> Dict[str, Any]:
        """Get RAM sensor data"""
        sensors = {
            'name': f"RAM ({self.ram_total} GB Total)",
            'sensors': {}
        }

        try:
            mem = psutil.virtual_memory()

            # Usage
            used_gb = mem.used / (1024**3)
            total_gb = mem.total / (1024**3)
            sensors['sensors']['Memory Usage'] = {
                'value': f"{used_gb:.1f} GB / {total_gb:.1f} GB ({mem.percent:.0f}%)",
                'raw': mem.percent,
                'unit': '%',
                'type': 'memory'
            }

            # Available
            avail_gb = mem.available / (1024**3)
            sensors['sensors']['Available'] = {
                'value': f"{avail_gb:.1f} GB",
                'raw': avail_gb,
                'unit': 'GB',
                'type': 'memory'
            }

            # Temperature (simulated)
            estimated_temp = 30 + (mem.percent * 0.3)
            sensors['sensors']['Temperature (estimated)'] = {
                'value': f"{int(estimated_temp)}°C",
                'raw': estimated_temp,
                'unit': '°C',
                'type': 'temperature'
            }

        except Exception as e:
            print(f"[HardwareSensors] RAM error: {e}")

        return sensors

    def _get_storage_sensors(self) -> Dict[str, Any]:
        """Get storage device sensor data"""
        sensors = {
            'name': 'Storage',
            'sensors': {}
        }

        try:
            partitions = psutil.disk_partitions()

            for i, partition in enumerate(partitions):
                try:
                    usage = psutil.disk_usage(partition.mountpoint)

                    # Clean device name
                    device_name = partition.device.replace('\\', '').replace(':', '')

                    sensors['sensors'][f'{device_name} ({partition.fstype})'] = {
                        'value': f"{usage.used / (1024**3):.1f} GB / {usage.total / (1024**3):.1f} GB ({usage.percent:.0f}%)",
                        'raw': usage.percent,
                        'unit': '%',
                        'type': 'storage'
                    }

                    # Temperature (simulated)
                    estimated_temp = 35 + (usage.percent * 0.1)
                    sensors['sensors'][f'{device_name} Temperature (est)'] = {
                        'value': f"{int(estimated_temp)}°C",
                        'raw': estimated_temp,
                        'unit': '°C',
                        'type': 'temperature'
                    }

                except (PermissionError, OSError):
                    continue

        except Exception as e:
            print(f"[HardwareSensors] Storage error: {e}")

        return sensors

    def get_sensor_color(self, sensor_type: str, raw_value: float) -> str:
        """
        Get color for sensor based on type and value
        Returns: hex color string
        """
        if sensor_type == 'temperature':
            if raw_value < 60:
                return "#10b981"  # Green - safe
            elif raw_value < 80:
                return "#fbbf24"  # Yellow - warm
            else:
                return "#ef4444"  # Red - hot

        elif sensor_type == 'usage' or sensor_type == 'memory' or sensor_type == 'storage':
            if raw_value < 70:
                return "#10b981"  # Green - normal
            elif raw_value < 90:
                return "#fbbf24"  # Yellow - high
            else:
                return "#ef4444"  # Red - critical

        else:
            return "#64748b"  # Gray - neutral

    def get_flat_sensor_list(self) -> List[Dict[str, Any]]:
        """
        Get flat list of all sensors (for "Group by Type" view)

        Returns:
            [
                {'category': 'CPU', 'name': 'Package Temperature', 'value': '52°C', ...},
                {'category': 'GPU', 'name': 'Core Temperature', 'value': '68°C', ...},
                ...
            ]
        """
        tree = self.get_sensor_tree()
        flat_list = []

        for category, data in tree.items():
            for sensor_name, sensor_data in data.get('sensors', {}).items():
                flat_list.append({
                    'category': category,
                    'category_name': data['name'],
                    'sensor_name': sensor_name,
                    'value': sensor_data['value'],
                    'raw': sensor_data['raw'],
                    'unit': sensor_data['unit'],
                    'type': sensor_data['type'],
                    'color': self.get_sensor_color(sensor_data['type'], sensor_data['raw'])
                })

        return flat_list


# Singleton instance
_hardware_sensors_instance = None

def get_hardware_sensors() -> HardwareSensors:
    """Get singleton HardwareSensors instance"""
    global _hardware_sensors_instance
    if _hardware_sensors_instance is None:
        _hardware_sensors_instance = HardwareSensors()
    return _hardware_sensors_instance


if __name__ == "__main__":
    # Test hardware sensors
    sensors = HardwareSensors()

    print("=== SENSOR TREE ===")
    tree = sensors.get_sensor_tree()

    for category, data in tree.items():
        print(f"\n▼ {category} - {data['name']}")
        for sensor_name, sensor_data in data.get('sensors', {}).items():
            color = sensors.get_sensor_color(sensor_data['type'], sensor_data['raw'])
            print(f"  ├─ {sensor_name}: {sensor_data['value']} (color: {color})")

    print("\n=== FLAT LIST (Group by Type) ===")
    flat = sensors.get_flat_sensor_list()

    # Group by type
    by_type = {}
    for sensor in flat:
        sensor_type = sensor['type']
        if sensor_type not in by_type:
            by_type[sensor_type] = []
        by_type[sensor_type].append(sensor)

    for sensor_type, sensors_list in by_type.items():
        print(f"\n▼ {sensor_type.upper()}")
        for sensor in sensors_list:
            print(f"  ├─ {sensor['category']} - {sensor['sensor_name']}: {sensor['value']}")
