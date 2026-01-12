#!/usr/bin/env python3
"""
PVE硬件全面健康报告脚本
聚合 CPU/内存/磁盘/网络/温度/风扇/电源等信息并标记风险

功能特性:
- 采集系统资源信息（CPU、内存、磁盘、网络）
- 采集硬件健康信息（SMART、温度、风扇、电压、电源）
- 支持自定义阈值配置
- 生成多种格式报告（文本、JSON、HTML）
- 自动识别和标记风险隐患
- 支持自动安装监控工具（lm-sensors、ipmitool）

使用示例:
    # 基本使用（使用默认阈值）
    python3 monitor__hardware_report.py
    
    # 自定义阈值
    python3 monitor__hardware_report.py --cpu-warn 70 --cpu-crit 85 --disk-warn 75
    
    # 指定网卡接口
    python3 monitor__hardware_report.py --network-interfaces eth0,enp2s0
    
    # 自动安装监控工具
    python3 monitor__hardware_report.py --auto-install
    
    # 自定义日志目录
    python3 monitor__hardware_report.py --log-dir /var/log/pve

输出文件:
    - hardware_report_YYYYMMDD_HHMMSS.log  # 文本报告（无颜色）
    - hardware_report_YYYYMMDD_HHMMSS.html # HTML报告（美观可视化）
    - hardware_report.json                  # JSON报告（最新数据）
"""

import os
import subprocess
import re
import sys
import json
import argparse
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional

# ========================= 配置区域 =========================
# 默认阈值配置
DEFAULT_THRESHOLDS = {
    'cpu_warn': 80,
    'cpu_crit': 90,
    'mem_warn': 80,
    'mem_crit': 90,
    'disk_warn': 80,
    'disk_crit': 90,
    'temp_warn': 70,
    'temp_crit': 80,
    'io_wait_warn': 20,
    'io_wait_crit': 40,
}

# SATA设备关键参数映射（复用自 monitor__disk_health_check.py）
SATA_PARAMS = {
    "5": ("重新分配扇区计数", "Reallocated_Sector_Ct"),
    "9": ("通电时间", "Power_On_Hours"),
    "12": ("电源循环计数", "Power_Cycle_Count"),
    "187": ("报告不可纠正错误", "Reported_Uncorrect"),
    "194": ("温度", "Temperature_Celsius"),
    "231": ("剩余寿命百分比", "SSD_Life_Left"),
    "241": ("总计写入", "Total_LBAs_Written"),
    "242": ("总计读取", "Total_LBAs_Read")
}

SMART_LIFE_WARN = 30
SMART_LIFE_CRIT = 10
NVME_SPARE_WARN = 20
NVME_SPARE_CRIT = 10
NVME_USED_WARN = 80
NVME_USED_CRIT = 95

# 颜色定义
class Colors:
    RED = '\033[1;31m'
    ORANGE = '\033[1;33m'
    GREEN = '\033[1;32m'
    YELLOW = '\033[1;33m'
    CYAN = '\033[1;36m'
    PURPLE = '\033[1;35m'
    END = '\033[0m'

ANSI_ESCAPE_RE = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')

def strip_ansi(text: str) -> str:
    """移除ANSI颜色码"""
    return ANSI_ESCAPE_RE.sub('', text) if text else text

def color_text(text: str, color: str) -> str:
    """为文本添加颜色"""
    return f"{color}{text}{Colors.END}"

# ========================= 工具函数 =========================
def run_command(cmd: str, timeout: int = 30) -> Tuple[str, str, int]:
    """执行shell命令并返回输出"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", f"命令超时: {cmd}", 1
    except Exception as e:
        return "", str(e), 1

def to_int(value: Any, default: int = 0) -> int:
    """尝试转换为整数"""
    if isinstance(value, int):
        return value
    if value is None:
        return default
    value_str = str(value).strip()
    if not value_str:
        return default
    try:
        return int(value_str)
    except ValueError:
        match = re.search(r'-?\d+', value_str)
        return int(match.group()) if match else default

def to_float(value: Any, default: float = 0.0) -> float:
    """尝试转换为浮点数"""
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        return default
    value_str = str(value).strip()
    if not value_str:
        return default
    try:
        return float(value_str)
    except ValueError:
        match = re.search(r'-?\d+\.?\d*', value_str)
        return float(match.group()) if match else default

def parse_sata_attributes(output: str) -> Dict[str, Dict[str, Any]]:
    """解析SATA设备的SMART属性"""
    attrs = {}
    lines = output.strip().split('\n')
    for line in lines:
        if re.match(r'^\s*\d+', line):
            parts = re.split(r'\s+', line.strip(), maxsplit=10)
            if len(parts) >= 10:
                attr_id = parts[0]
                raw_value = parts[9]
                if len(parts) > 10:
                    raw_value = f"{raw_value} {parts[10]}"
                attrs[attr_id] = {
                    'id': attr_id,
                    'name': parts[1],
                    'value': to_int(parts[3]),
                    'worst': to_int(parts[4]),
                    'threshold': to_int(parts[5]),
                    'raw': raw_value,
                    'raw_int': to_int(raw_value),
                    'type': parts[6] if len(parts) > 6 else '',
                    'when_failed': parts[8] if len(parts) > 8 else '-'
                }
    return attrs

def parse_nvme_info(output: str) -> Dict[str, Any]:
    """解析NVMe设备的SMART信息"""
    info = {}
    lines = output.strip().split('\n')
    current_section = None
    for line in lines:
        line = line.strip()
        if line.startswith('=== START OF SMART DATA SECTION ==='):
            current_section = 'smart'
        elif line.startswith('SMART/Health Information'):
            current_section = 'health'
        if ':' in line and current_section == 'health':
            key, value = line.split(':', 1)
            key = key.strip().lower().replace(' ', '_')
            value = value.strip()
            num_match = re.search(r'(\d+\.?\d*)', value)
            info[key] = num_match.group(1) if num_match else value
    return info

def get_status_color(status: str) -> str:
    """根据状态返回颜色"""
    status_map = {
        'normal': Colors.GREEN,
        'warning': Colors.ORANGE,
        'critical': Colors.RED,
        'unknown': Colors.YELLOW
    }
    return status_map.get(status.lower(), Colors.END)

def determine_status(value: float, warn_threshold: float, crit_threshold: float, reverse: bool = False) -> str:
    """
    根据阈值判断状态
    reverse=True 表示值越低越危险（如剩余空间）
    """
    if reverse:
        if value <= crit_threshold:
            return 'critical'
        elif value <= warn_threshold:
            return 'warning'
        else:
            return 'normal'
    else:
        if value >= crit_threshold:
            return 'critical'
        elif value >= warn_threshold:
            return 'warning'
        else:
            return 'normal'

# ========================= 数据采集模块 =========================

class CPUCollector:
    """CPU信息采集器"""
    
    @staticmethod
    def collect() -> Dict[str, Any]:
        """采集CPU信息"""
        result = {
            'status': 'unknown',
            'usage': 0.0,
            'load': [0.0, 0.0, 0.0],
            'top_processes': [],
            'error': None
        }
        
        # 获取CPU使用率（使用 mpstat）
        stdout, stderr, code = run_command("mpstat 1 1 | tail -1")
        if code == 0 and stdout:
            match = re.search(r'(\d+\.\d+)\s+$', stdout)
            if match:
                idle = to_float(match.group(1))
                result['usage'] = round(100 - idle, 2)
        else:
            # 备用方法：使用 top
            stdout, stderr, code = run_command("top -bn1 | grep 'Cpu(s)'")
            if code == 0 and stdout:
                match = re.search(r'(\d+\.\d+)\s*id', stdout)
                if match:
                    idle = to_float(match.group(1))
                    result['usage'] = round(100 - idle, 2)
        
        # 获取负载
        stdout, stderr, code = run_command("cat /proc/loadavg")
        if code == 0 and stdout:
            parts = stdout.split()
            if len(parts) >= 3:
                result['load'] = [to_float(parts[0]), to_float(parts[1]), to_float(parts[2])]
        
        # 获取TOP5进程
        stdout, stderr, code = run_command("ps aux --sort=-%cpu | head -6 | tail -5")
        if code == 0 and stdout:
            for line in stdout.strip().split('\n'):
                parts = line.split(None, 10)
                if len(parts) >= 11:
                    result['top_processes'].append({
                        'user': parts[0],
                        'pid': parts[1],
                        'cpu': to_float(parts[2]),
                        'mem': to_float(parts[3]),
                        'command': parts[10]
                    })
        
        return result

class MemoryCollector:
    """内存信息采集器"""
    
    @staticmethod
    def collect() -> Dict[str, Any]:
        """采集内存信息"""
        result = {
            'status': 'unknown',
            'total': 0,
            'used': 0,
            'free': 0,
            'available': 0,
            'buffers': 0,
            'cached': 0,
            'swap_total': 0,
            'swap_used': 0,
            'swap_free': 0,
            'usage_percent': 0.0,
            'error': None
        }
        
        stdout, stderr, code = run_command("free -b")
        if code != 0:
            result['error'] = stderr or "无法获取内存信息"
            return result
        
        lines = stdout.strip().split('\n')
        for line in lines:
            if line.startswith('Mem:'):
                parts = line.split()
                if len(parts) >= 7:
                    result['total'] = to_int(parts[1])
                    result['used'] = to_int(parts[2])
                    result['free'] = to_int(parts[3])
                    result['buffers'] = to_int(parts[5])
                    result['cached'] = to_int(parts[6])
                    # 计算可用内存
                    result['available'] = result['free'] + result['buffers'] + result['cached']
                    # 计算使用率
                    if result['total'] > 0:
                        result['usage_percent'] = round((result['used'] / result['total']) * 100, 2)
            elif line.startswith('Swap:'):
                parts = line.split()
                if len(parts) >= 4:
                    result['swap_total'] = to_int(parts[1])
                    result['swap_used'] = to_int(parts[2])
                    result['swap_free'] = to_int(parts[3])
        
        return result

class DiskCollector:
    """磁盘信息采集器"""
    
    @staticmethod
    def collect() -> Dict[str, Any]:
        """采集磁盘容量和使用情况"""
        result = {
            'status': 'unknown',
            'filesystems': [],
            'large_disks': [],
            'error': None
        }
        
        # 使用 df -h -l 只显示本地文件系统，排除网络文件系统
        # 使用 -x 排除临时文件系统
        stdout, stderr, code = run_command("df -h -l -x tmpfs -x devtmpfs -x squashfs")
        if code != 0:
            result['error'] = stderr or "无法获取磁盘信息"
            return result
        
        lines = stdout.strip().split('\n')[1:]  # 跳过表头
        for line in lines:
            parts = line.split()
            if len(parts) >= 6:
                filesystem = parts[0]
                size = parts[1]
                used = parts[2]
                avail = parts[3]
                use_percent_str = parts[4].rstrip('%')
                mountpoint = parts[5]
                
                # 过滤掉非本地磁盘设备（如loop设备、overlay等）
                if filesystem.startswith('loop') or filesystem.startswith('overlay'):
                    continue
                
                use_percent = to_float(use_percent_str)
                
                fs_info = {
                    'filesystem': filesystem,
                    'size': size,
                    'used': used,
                    'available': avail,
                    'use_percent': use_percent,
                    'mountpoint': mountpoint
                }
                result['filesystems'].append(fs_info)
                
                # 标记大于512G的数据盘
                if 'T' in size or (('G' in size) and to_float(size.rstrip('GT')) > 512):
                    result['large_disks'].append(fs_info)
        
        return result
    
    @staticmethod
    def collect_smart() -> Dict[str, Any]:
        """采集磁盘SMART健康信息（复用逻辑）"""
        result = {
            'status': 'unknown',
            'devices': [],
            'error': None
        }
        
        # 扫描设备
        stdout, stderr, code = run_command("smartctl --scan")
        devices = []
        if code == 0 and stdout:
            for line in stdout.strip().split('\n'):
                if line:
                    device = line.split()[0]
                    devices.append(device)
        elif code != 0 and stderr:
            if 'command not found' in stderr.lower() or 'not found' in stderr.lower():
                result['error'] = "smartctl 未安装，无法读取SMART信息"
                return result
        
        if not devices:
            # 备用检测
            for pattern in ["/dev/sd?", "/dev/nvme?n?"]:
                stdout, _, _ = run_command(f"ls {pattern} 2>/dev/null")
                if stdout:
                    devices.extend(stdout.strip().split())
        
        # 检查每个设备
        for device in devices:
            stdout, stderr, code = run_command(f"smartctl -a {device}")
            is_nvme = 'nvme' in device
            device_info = {
                'device': device,
                'model': '未知',
                'serial': '未知',
                'firmware': '未知',
                'capacity': '未知',
                'type': 'SSD' if is_nvme else 'SATA',
                'is_nvme': is_nvme,
                'health': 'unknown',
                'temperature': None,
                'attributes': [],
                'nvme': {},
                'health_score': None,
                'errors': []
            }
            
            if code != 0 or not stdout:
                device_info['errors'].append(f"无法读取SMART数据: {stderr}")
                result['devices'].append(device_info)
                continue
            
            # 解析基本信息
            for line in stdout.split('\n'):
                line_lower = line.lower()
                if 'model number:' in line_lower or 'device model:' in line_lower:
                    device_info['model'] = line.split(':', 1)[1].strip()
                elif 'serial number:' in line_lower:
                    device_info['serial'] = line.split(':', 1)[1].strip()
                elif 'firmware version:' in line_lower:
                    device_info['firmware'] = line.split(':', 1)[1].strip()
                elif 'user capacity:' in line_lower or 'total nvm capacity:' in line_lower:
                    capacity_match = re.search(r'\[(.*?)\]', line)
                    if capacity_match:
                        device_info['capacity'] = capacity_match.group(1)
                elif 'rotation rate:' in line_lower:
                    if 'solid state' in line_lower:
                        device_info['type'] = 'SSD'
                    else:
                        device_info['type'] = 'HDD'
                elif 'smart overall-health' in line_lower or 'smart health status:' in line_lower:
                    if 'PASSED' in line or 'OK' in line:
                        device_info['health'] = 'passed'
                    else:
                        device_info['health'] = 'failed'

            # 解析温度与详细参数
            if is_nvme:
                nvme_info = parse_nvme_info(stdout)
                device_info['nvme'] = nvme_info
                temp_match = re.search(r'(?:Temperature|Composite Temperature):\s*(\d+)', stdout)
                if not temp_match:
                    temp_match = re.search(r'Temperature Sensor 1:\s*(\d+)', stdout)
                if temp_match:
                    device_info['temperature'] = to_int(temp_match.group(1))
                elif 'temperature' in nvme_info:
                    device_info['temperature'] = to_int(nvme_info.get('temperature'))
                if 'percentage_used' in nvme_info:
                    used = to_float(nvme_info.get('percentage_used'))
                    if used >= 0:
                        device_info['health_score'] = max(0, min(100, int(round(100 - used))))
            else:
                attrs = parse_sata_attributes(stdout)
                for attr_id, (cn_name, en_name) in SATA_PARAMS.items():
                    if attr_id in attrs:
                        attr_data = dict(attrs[attr_id])
                        attr_data['cn_name'] = cn_name
                        attr_data['key'] = en_name
                        device_info['attributes'].append(attr_data)
                if '194' in attrs:
                    device_info['temperature'] = attrs['194'].get('raw_int')
                elif '190' in attrs:
                    device_info['temperature'] = attrs['190'].get('raw_int')
                if '231' in attrs:
                    life_raw = attrs['231'].get('raw_int', 0)
                    life_val = attrs['231'].get('value', 0)
                    life = life_raw if life_raw > 0 else life_val
                    if life >= 0:
                        device_info['health_score'] = max(0, min(100, int(life)))
            
            result['devices'].append(device_info)
        
        return result
    
    @staticmethod
    def collect_io() -> Dict[str, Any]:
        """采集磁盘IO信息"""
        result = {
            'status': 'unknown',
            'devices': [],
            'error': None
        }
        
        stdout, stderr, code = run_command("iostat -dx 1 2 | tail -n +4")
        if code != 0:
            result['error'] = stderr or "无法获取IO信息（可能需要安装 sysstat）"
            return result
        
        lines = stdout.strip().split('\n')
        # 跳过第一组数据，使用第二组
        data_lines = []
        found_second = False
        for line in lines:
            if line.startswith('Device'):
                if found_second:
                    break
                found_second = True
                continue
            if found_second and line.strip():
                data_lines.append(line)
        
        for line in data_lines:
            parts = line.split()
            if len(parts) >= 14:
                result['devices'].append({
                    'device': parts[0],
                    'rrqm_s': to_float(parts[1]),
                    'wrqm_s': to_float(parts[2]),
                    'r_s': to_float(parts[3]),
                    'w_s': to_float(parts[4]),
                    'rkB_s': to_float(parts[5]),
                    'wkB_s': to_float(parts[6]),
                    'avgrq_sz': to_float(parts[7]),
                    'avgqu_sz': to_float(parts[8]),
                    'await': to_float(parts[9]),
                    'r_await': to_float(parts[10]),
                    'w_await': to_float(parts[11]),
                    'svctm': to_float(parts[12]),
                    'util': to_float(parts[13])
                })
        
        return result

class NetworkCollector:
    """网络信息采集器"""
    
    @staticmethod
    def collect(interfaces: List[str] = None) -> Dict[str, Any]:
        """
        采集网络接口信息
        
        Args:
            interfaces: 要监控的网卡接口列表，如 ['eth0', 'enp2s0']
                       如果为 None 或空列表，则自动检测物理网卡
        """
        result = {
            'status': 'unknown',
            'interfaces': [],
            'error': None
        }
        
        # 如果指定了接口列表，直接使用指定的接口
        if interfaces:
            for ifname in interfaces:
                iface_data = NetworkCollector._collect_interface(ifname)
                if iface_data:
                    result['interfaces'].append(iface_data)
            return result
        
        # 否则自动检测物理网卡（只检测常见的物理网卡命名模式）
        stdout, stderr, code = run_command("ip -s link")
        if code != 0:
            result['error'] = stderr or "无法获取网络信息"
            return result
        
        lines = stdout.strip().split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]
            # 匹配接口行
            match = re.match(r'^\d+:\s+(\S+):', line)
            if match:
                ifname = match.group(1)
                
                # 只检测物理网卡接口（白名单模式）
                # eth*: 传统以太网接口
                # enp*: 新式PCI以太网接口
                # eno*: 板载以太网接口
                # ens*: 热插拔以太网接口
                # em*: Dell等厂商的以太网接口
                # wlan*: 无线网卡
                # wlp*: 新式无线网卡
                is_physical = (
                    ifname.startswith('eth') or
                    ifname.startswith('enp') or
                    ifname.startswith('eno') or
                    ifname.startswith('ens') or
                    ifname.startswith('em') or
                    ifname.startswith('wlan') or
                    ifname.startswith('wlp')
                )
                
                if not is_physical:
                    i += 5
                    continue
                
                # 检查网线连接状态
                stdout_ethtool, _, code_ethtool = run_command(f"ethtool {ifname} 2>/dev/null")
                if code_ethtool == 0 and stdout_ethtool:
                    if 'Link detected: yes' in stdout_ethtool:
                        iface_data = NetworkCollector._collect_interface(ifname)
                        if iface_data:
                            result['interfaces'].append(iface_data)
                
                i += 5
            else:
                i += 1
        
        return result
    
    @staticmethod
    def _collect_interface(ifname: str) -> Optional[Dict[str, Any]]:
        """采集单个网卡接口的信息"""
        # 获取接口统计信息
        stdout, stderr, code = run_command(f"ip -s link show {ifname}")
        if code != 0:
            return None
        
        lines = stdout.strip().split('\n')
        if len(lines) < 5:
            return None
        
        # 解析状态
        state = 'DOWN'
        if 'state UP' in lines[0]:
            state = 'UP'
        elif 'state DOWN' in lines[0]:
            state = 'DOWN'
        elif 'state UNKNOWN' in lines[0]:
            state = 'UNKNOWN'
        
        # 解析统计信息
        rx_bytes = 0
        rx_packets = 0
        rx_errors = 0
        tx_bytes = 0
        tx_packets = 0
        tx_errors = 0
        
        # RX 统计（通常在第3行）
        for i, line in enumerate(lines):
            if 'RX:' in line or (i >= 2 and i <= 3):
                rx_line = lines[i].strip() if 'RX:' in line else line.strip()
                rx_parts = rx_line.split()
                if len(rx_parts) >= 3:
                    # 跳过 "RX:" 标签
                    start_idx = 1 if rx_parts[0] == 'RX:' else 0
                    if len(rx_parts) > start_idx + 2:
                        rx_bytes = to_int(rx_parts[start_idx])
                        rx_packets = to_int(rx_parts[start_idx + 1])
                        rx_errors = to_int(rx_parts[start_idx + 2])
                break
        
        # TX 统计（通常在第5行）
        for i, line in enumerate(lines):
            if 'TX:' in line or (i >= 4 and i <= 5):
                tx_line = lines[i].strip() if 'TX:' in line else line.strip()
                tx_parts = tx_line.split()
                if len(tx_parts) >= 3:
                    # 跳过 "TX:" 标签
                    start_idx = 1 if tx_parts[0] == 'TX:' else 0
                    if len(tx_parts) > start_idx + 2:
                        tx_bytes = to_int(tx_parts[start_idx])
                        tx_packets = to_int(tx_parts[start_idx + 1])
                        tx_errors = to_int(tx_parts[start_idx + 2])
                break
        
        # 获取速率
        speed = None
        stdout_ethtool, _, code_ethtool = run_command(f"ethtool {ifname} 2>/dev/null")
        if code_ethtool == 0 and stdout_ethtool:
            match_speed = re.search(r'Speed:\s*(\S+)', stdout_ethtool)
            if match_speed:
                speed = match_speed.group(1)
        
        return {
            'name': ifname,
            'state': state,
            'rx_bytes': rx_bytes,
            'rx_packets': rx_packets,
            'rx_errors': rx_errors,
            'tx_bytes': tx_bytes,
            'tx_packets': tx_packets,
            'tx_errors': tx_errors,
            'speed': speed
        }

class SensorCollector:
    """传感器信息采集器（温度、风扇、电压）"""
    
    @staticmethod
    def collect(auto_install: bool = False) -> Dict[str, Any]:
        """
        采集传感器信息
        
        Args:
            auto_install: 是否自动安装缺失的工具
        """
        result = {
            'status': 'unknown',
            'temperatures': [],
            'fans': [],
            'voltages': [],
            'error': None,
            'installed_tools': []
        }
        
        # 检查并安装 lm-sensors
        sensors_available = SensorCollector._check_tool('sensors')
        if not sensors_available and auto_install:
            if SensorCollector._install_lm_sensors():
                result['installed_tools'].append('lm-sensors')
                sensors_available = True
        
        # 检查并安装 ipmitool
        ipmitool_available = SensorCollector._check_tool('ipmitool')
        if not ipmitool_available and auto_install:
            if SensorCollector._install_ipmitool():
                result['installed_tools'].append('ipmitool')
                ipmitool_available = True
        
        # 尝试使用 sensors
        if sensors_available:
            stdout, stderr, code = run_command("sensors 2>/dev/null")
            if code == 0 and stdout:
                SensorCollector._parse_sensors(stdout, result)
        
        # 尝试使用 ipmitool
        if ipmitool_available:
            stdout, stderr, code = run_command("ipmitool sensor 2>/dev/null")
            if code == 0 and stdout:
                SensorCollector._parse_ipmitool(stdout, result)
        
        if not result['temperatures'] and not result['fans'] and not result['voltages']:
            if not sensors_available and not ipmitool_available:
                result['error'] = "未检测到传感器工具（lm-sensors 和 ipmitool 均不可用）"
            else:
                result['error'] = "未检测到传感器数据（硬件可能不支持或需要加载内核模块）"
        
        return result
    
    @staticmethod
    def _check_tool(tool_name: str) -> bool:
        """检查工具是否已安装"""
        stdout, stderr, code = run_command(f"which {tool_name}")
        return code == 0 and stdout.strip() != ''
    
    @staticmethod
    def _install_lm_sensors() -> bool:
        """安装 lm-sensors"""
        print("  正在安装 lm-sensors...")
        
        # 检测包管理器并安装
        if SensorCollector._check_tool('apt-get'):
            stdout, stderr, code = run_command("apt-get update -qq && apt-get install -y lm-sensors", timeout=120)
            if code == 0:
                print("  ✓ lm-sensors 安装成功")
                # 尝试检测传感器
                run_command("sensors-detect --auto", timeout=60)
                return True
        elif SensorCollector._check_tool('yum'):
            stdout, stderr, code = run_command("yum install -y lm_sensors", timeout=120)
            if code == 0:
                print("  ✓ lm-sensors 安装成功")
                run_command("sensors-detect --auto", timeout=60)
                return True
        elif SensorCollector._check_tool('dnf'):
            stdout, stderr, code = run_command("dnf install -y lm_sensors", timeout=120)
            if code == 0:
                print("  ✓ lm-sensors 安装成功")
                run_command("sensors-detect --auto", timeout=60)
                return True
        
        print("  ✗ lm-sensors 安装失败")
        return False
    
    @staticmethod
    def _install_ipmitool() -> bool:
        """安装 ipmitool"""
        print("  正在安装 ipmitool...")
        
        # 检测包管理器并安装
        if SensorCollector._check_tool('apt-get'):
            stdout, stderr, code = run_command("apt-get install -y ipmitool", timeout=120)
            if code == 0:
                print("  ✓ ipmitool 安装成功")
                # 加载 IPMI 内核模块
                run_command("modprobe ipmi_devintf 2>/dev/null")
                run_command("modprobe ipmi_si 2>/dev/null")
                return True
        elif SensorCollector._check_tool('yum'):
            stdout, stderr, code = run_command("yum install -y ipmitool", timeout=120)
            if code == 0:
                print("  ✓ ipmitool 安装成功")
                run_command("modprobe ipmi_devintf 2>/dev/null")
                run_command("modprobe ipmi_si 2>/dev/null")
                return True
        elif SensorCollector._check_tool('dnf'):
            stdout, stderr, code = run_command("dnf install -y ipmitool", timeout=120)
            if code == 0:
                print("  ✓ ipmitool 安装成功")
                run_command("modprobe ipmi_devintf 2>/dev/null")
                run_command("modprobe ipmi_si 2>/dev/null")
                return True
        
        print("  ✗ ipmitool 安装失败")
        return False
    
    @staticmethod
    def _parse_sensors(output: str, result: Dict[str, Any]):
        """解析 sensors 命令输出"""
        for line in output.split('\n'):
            line = line.strip()
            if not line or ':' not in line:
                continue
            
            # 温度
            if '°C' in line or 'C' in line:
                match = re.match(r'(.+?):\s*\+?(-?\d+\.?\d*)', line)
                if match:
                    name = match.group(1).strip()
                    value = to_float(match.group(2))
                    result['temperatures'].append({
                        'name': name,
                        'value': value,
                        'unit': '°C'
                    })
            
            # 风扇
            elif 'fan' in line.lower() and 'RPM' in line:
                match = re.match(r'(.+?):\s*(\d+)', line)
                if match:
                    name = match.group(1).strip()
                    value = to_int(match.group(2))
                    result['fans'].append({
                        'name': name,
                        'value': value,
                        'unit': 'RPM'
                    })
            
            # 电压
            elif 'V' in line and not 'RPM' in line:
                match = re.match(r'(.+?):\s*\+?(-?\d+\.?\d*)', line)
                if match:
                    name = match.group(1).strip()
                    value = to_float(match.group(2))
                    if 0 < value < 100:  # 合理的电压范围
                        result['voltages'].append({
                            'name': name,
                            'value': value,
                            'unit': 'V'
                        })
    
    @staticmethod
    def _parse_ipmitool(output: str, result: Dict[str, Any]):
        """解析 ipmitool sensor 命令输出"""
        for line in output.split('\n'):
            parts = line.split('|')
            if len(parts) < 3:
                continue
            
            name = parts[0].strip()
            value_str = parts[1].strip()
            unit = parts[2].strip()
            
            if not value_str or value_str == 'na':
                continue
            
            value = to_float(value_str)
            
            # 分类
            if unit == 'degrees C':
                result['temperatures'].append({
                    'name': name,
                    'value': value,
                    'unit': '°C'
                })
            elif unit == 'RPM':
                result['fans'].append({
                    'name': name,
                    'value': value,
                    'unit': 'RPM'
                })
            elif unit == 'Volts':
                result['voltages'].append({
                    'name': name,
                    'value': value,
                    'unit': 'V'
                })

class PowerCollector:
    """电源信息采集器"""
    
    @staticmethod
    def collect() -> Dict[str, Any]:
        """采集电源信息"""
        result = {
            'status': 'unknown',
            'supplies': [],
            'error': None
        }
        
        # 尝试使用 ipmitool
        stdout, stderr, code = run_command("ipmitool chassis status 2>/dev/null")
        if code == 0 and stdout:
            for line in stdout.split('\n'):
                if 'Power' in line:
                    result['supplies'].append({
                        'info': line.strip()
                    })
        
        # 尝试从 /sys 读取
        stdout, stderr, code = run_command("find /sys/class/hwmon -name 'power*_input' 2>/dev/null")
        if code == 0 and stdout:
            for path in stdout.strip().split('\n'):
                if path:
                    value_stdout, _, value_code = run_command(f"cat {path} 2>/dev/null")
                    if value_code == 0 and value_stdout:
                        value = to_float(value_stdout) / 1000000  # 转换为瓦特
                        result['supplies'].append({
                            'path': path,
                            'power': value,
                            'unit': 'W'
                        })
        
        if not result['supplies']:
            result['error'] = "未检测到电源信息（可能需要 IPMI 支持）"
        
        return result

# ========================= 报告生成器 =========================

class HardwareReporter:
    """硬件报告生成器"""
    
    def __init__(self, thresholds: Dict[str, float], network_interfaces: List[str] = None, auto_install: bool = False):
        self.thresholds = thresholds
        self.network_interfaces = network_interfaces
        self.auto_install = auto_install
        self.report_data = {}
        self.issues = []
        self.report_lines = []
    
    def collect_all(self):
        """采集所有硬件信息"""
        self.log_section("正在采集硬件信息...")
        
        # CPU
        self.log("采集 CPU 信息...")
        self.report_data['cpu'] = CPUCollector.collect()
        
        # 内存
        self.log("采集内存信息...")
        self.report_data['memory'] = MemoryCollector.collect()
        
        # 磁盘容量
        self.log("采集磁盘容量信息...")
        self.report_data['disk'] = DiskCollector.collect()
        
        # 磁盘SMART
        self.log("采集磁盘 SMART 信息...")
        self.report_data['smart'] = DiskCollector.collect_smart()
        
        # 磁盘IO
        self.log("采集磁盘 IO 信息...")
        self.report_data['io'] = DiskCollector.collect_io()
        
        # 网络
        self.log("采集网络信息...")
        self.report_data['network'] = NetworkCollector.collect(self.network_interfaces)
        
        # 传感器
        self.log("采集传感器信息...")
        self.report_data['sensors'] = SensorCollector.collect(self.auto_install)
        
        # 电源
        self.log("采集电源信息...")
        self.report_data['power'] = PowerCollector.collect()
        
        self.log_section("数据采集完成")
    
    def analyze_and_report(self):
        """分析数据并生成报告"""
        self.log_section("=" * 80)
        self.log_section("PVE 硬件健康报告", Colors.YELLOW)
        self.log_section("=" * 80)
        self.log(f"报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log("")
        
        # 先生成隐患摘要（在顶部显示）
        self._analyze_all_and_collect_issues()
        self._generate_summary()
        
        # 详细信息
        self.log_section("=" * 80)
        self.log_section("详细信息", Colors.CYAN)
        self.log_section("=" * 80)
        self.log("")
        
        # 分析各项指标
        self._analyze_cpu()
        self._analyze_memory()
        self._analyze_disk()
        self._analyze_smart()
        self._analyze_io()
        self._analyze_network()
        self._analyze_sensors()
        self._analyze_power()
    
    def _analyze_all_and_collect_issues(self):
        """预先分析所有数据并收集问题"""
        # CPU
        cpu = self.report_data.get('cpu', {})
        if not cpu.get('error'):
            usage = cpu.get('usage', 0)
            status = determine_status(usage, self.thresholds['cpu_warn'], self.thresholds['cpu_crit'])
            if status != 'normal':
                self.issues.append({
                    'category': 'CPU',
                    'severity': 'warning',  # 强制使用 warning，不使用 critical
                    'message': f'CPU 使用率 {usage}%',
                    'detail': f'当前使用率较高'
                })
        
        # 内存
        mem = self.report_data.get('memory', {})
        if not mem.get('error'):
            usage_percent = mem.get('usage_percent', 0)
            status = determine_status(usage_percent, self.thresholds['mem_warn'], self.thresholds['mem_crit'])
            if status != 'normal':
                self.issues.append({
                    'category': '内存',
                    'severity': 'warning',  # 强制使用 warning，不使用 critical
                    'message': f'内存使用率 {usage_percent}%',
                    'detail': f'当前使用率较高'
                })
        
        # 磁盘容量（不在这里添加，因为在_analyze_disk中已经添加过了）
        disk = self.report_data.get('disk', {})
        if not disk.get('error'):
            for fs in disk.get('filesystems', []):
                use_percent = fs['use_percent']
                status = determine_status(use_percent, self.thresholds['disk_warn'], self.thresholds['disk_crit'])
                if status != 'normal':
                    # 检查是否已经添加过这个问题
                    already_exists = any(
                        i['category'] == '磁盘容量' and 
                        i['message'] == f'{fs["mountpoint"]} 使用率 {use_percent}%'
                        for i in self.issues
                    )
                    if not already_exists:
                        self.issues.append({
                            'category': '磁盘容量',
                            'severity': status,
                            'message': f'{fs["mountpoint"]} 使用率 {use_percent}%',
                            'detail': f'挂载点 {fs["mountpoint"]} 空间不足'
                        })
        
        # 磁盘SMART
        smart = self.report_data.get('smart', {})
        if not smart.get('error'):
            for dev in smart.get('devices', []):
                health = dev.get('health', 'unknown')
                if health == 'failed':
                    self.issues.append({
                        'category': '磁盘健康',
                        'severity': 'critical',
                        'message': f'{dev["device"]} SMART 检查失败',
                        'detail': f'磁盘 {dev["device"]} 健康检查未通过'
                    })

                if dev.get('errors'):
                    self.issues.append({
                        'category': '磁盘健康',
                        'severity': 'warning',
                        'message': f'{dev["device"]} SMART 读取异常',
                        'detail': '; '.join(dev.get('errors', []))
                    })

                attrs = {attr['id']: attr for attr in dev.get('attributes', [])}
                if attrs:
                    reallocated = attrs.get('5', {})
                    if reallocated.get('raw_int', 0) > 0:
                        self.issues.append({
                            'category': '磁盘健康',
                            'severity': 'critical',
                            'message': f'{dev["device"]} 重新分配扇区 {reallocated["raw_int"]}',
                            'detail': f'磁盘 {dev["device"]} 存在坏块迹象'
                        })
                    uncorrect = attrs.get('187', {})
                    if uncorrect.get('raw_int', 0) > 0:
                        self.issues.append({
                            'category': '磁盘健康',
                            'severity': 'critical',
                            'message': f'{dev["device"]} 不可纠正错误 {uncorrect["raw_int"]}',
                            'detail': f'磁盘 {dev["device"]} 出现不可纠正错误'
                        })
                    life_attr = attrs.get('231', {})
                    if life_attr:
                        life_raw = life_attr.get('raw_int', 0)
                        life_val = life_attr.get('value', 0)
                        life = life_raw if life_raw > 0 else life_val
                        if life <= SMART_LIFE_CRIT:
                            self.issues.append({
                                'category': '磁盘寿命',
                                'severity': 'critical',
                                'message': f'{dev["device"]} 剩余寿命 {life}%',
                                'detail': f'磁盘 {dev["device"]} 寿命告急'
                            })
                        elif life <= SMART_LIFE_WARN:
                            self.issues.append({
                                'category': '磁盘寿命',
                                'severity': 'warning',
                                'message': f'{dev["device"]} 剩余寿命 {life}%',
                                'detail': f'磁盘 {dev["device"]} 寿命偏低'
                            })
                    for attr in attrs.values():
                        threshold = attr.get('threshold', 0)
                        value = attr.get('value', 0)
                        if threshold > 0 and value <= threshold:
                            self.issues.append({
                                'category': '磁盘健康',
                                'severity': 'warning',
                                'message': f'{dev["device"]} SMART 指标 {attr.get("cn_name", attr.get("name", ""))} 低于阈值',
                                'detail': f'当前值 {value} 阈值 {threshold}'
                            })

                nvme = dev.get('nvme', {})
                if nvme:
                    if 'available_spare' in nvme:
                        spare = to_float(nvme.get('available_spare'))
                        spare_status = determine_status(spare, NVME_SPARE_WARN, NVME_SPARE_CRIT, reverse=True)
                        if spare_status != 'normal':
                            self.issues.append({
                                'category': '磁盘寿命',
                                'severity': spare_status,
                                'message': f'{dev["device"]} 可用备用空间 {spare}%',
                                'detail': f'磁盘 {dev["device"]} 备用空间不足'
                            })
                    if 'percentage_used' in nvme:
                        used = to_float(nvme.get('percentage_used'))
                        if used >= NVME_USED_WARN:
                            used_status = determine_status(used, NVME_USED_WARN, NVME_USED_CRIT)
                            self.issues.append({
                                'category': '磁盘寿命',
                                'severity': used_status,
                                'message': f'{dev["device"]} 已用寿命 {used}%',
                                'detail': f'磁盘 {dev["device"]} 寿命接近阈值'
                            })
                    media_errors = to_int(nvme.get('media_and_data_integrity_errors'))
                    if media_errors > 0:
                        self.issues.append({
                            'category': '磁盘健康',
                            'severity': 'critical',
                            'message': f'{dev["device"]} 媒体错误 {media_errors}',
                            'detail': f'磁盘 {dev["device"]} 检测到媒体/数据完整性错误'
                        })
                    unsafe_shutdowns = to_int(nvme.get('unsafe_shutdowns'))
                    if unsafe_shutdowns > 0:
                        self.issues.append({
                            'category': '磁盘健康',
                            'severity': 'warning',
                            'message': f'{dev["device"]} 不安全关机 {unsafe_shutdowns}',
                            'detail': f'磁盘 {dev["device"]} 存在不安全关机记录'
                        })
                
                temp = dev.get('temperature')
                if temp is not None:
                    temp_status = determine_status(temp, self.thresholds['temp_warn'], self.thresholds['temp_crit'])
                    if temp_status != 'normal':
                        self.issues.append({
                            'category': '磁盘温度',
                            'severity': temp_status,
                            'message': f'{dev["device"]} 温度 {temp}°C',
                            'detail': f'磁盘 {dev["device"]} 温度过高'
                        })
        
        # 磁盘IO
        io = self.report_data.get('io', {})
        if not io.get('error'):
            for dev in io.get('devices', []):
                if dev['await'] > self.thresholds['io_wait_crit']:
                    self.issues.append({
                        'category': '磁盘IO',
                        'severity': 'critical',
                        'message': f'{dev["device"]} IO等待 {dev["await"]:.2f}ms',
                        'detail': f'磁盘 {dev["device"]} IO响应时间过长'
                    })
                elif dev['await'] > self.thresholds['io_wait_warn']:
                    self.issues.append({
                        'category': '磁盘IO',
                        'severity': 'warning',
                        'message': f'{dev["device"]} IO等待 {dev["await"]:.2f}ms',
                        'detail': f'磁盘 {dev["device"]} IO响应时间较长'
                    })
        
        # 网络
        net = self.report_data.get('network', {})
        if not net.get('error'):
            for iface in net.get('interfaces', []):
                if iface['rx_errors'] > 0 or iface['tx_errors'] > 0:
                    self.issues.append({
                        'category': '网络',
                        'severity': 'warning',
                        'message': f'{iface["name"]} 有网络错误',
                        'detail': f'接口 {iface["name"]} 检测到 {iface["rx_errors"]+iface["tx_errors"]} 个错误'
                    })
        
        # 传感器
        sensors = self.report_data.get('sensors', {})
        if not sensors.get('error'):
            for temp in sensors.get('temperatures', []):
                value = temp['value']
                status = determine_status(value, self.thresholds['temp_warn'], self.thresholds['temp_crit'])
                if status != 'normal':
                    self.issues.append({
                        'category': '温度',
                        'severity': status,
                        'message': f'{temp["name"]} {value}°C',
                        'detail': f'传感器 {temp["name"]} 温度过高'
                    })
            
            for fan in sensors.get('fans', []):
                value = fan['value']
                if value == 0:
                    self.issues.append({
                        'category': '风扇',
                        'severity': 'critical',
                        'message': f'{fan["name"]} 停转',
                        'detail': f'风扇 {fan["name"]} 转速为 0'
                    })
                elif value < 500:
                    self.issues.append({
                        'category': '风扇',
                        'severity': 'warning',
                        'message': f'{fan["name"]} 转速低 ({value} RPM)',
                        'detail': f'风扇 {fan["name"]} 转速异常'
                    })
    
    def _analyze_cpu(self):
        """分析CPU"""
        self.log_section("CPU 信息", Colors.CYAN)
        cpu = self.report_data.get('cpu', {})
        
        if cpu.get('error'):
            self.log(f"  {color_text('错误:', Colors.RED)} {cpu['error']}")
            return
        
        usage = cpu.get('usage', 0)
        load = cpu.get('load', [0, 0, 0])
        
        status = determine_status(usage, self.thresholds['cpu_warn'], self.thresholds['cpu_crit'])
        # CPU只显示警告色（橙色）或正常色（绿色），不显示红色
        if status == 'critical':
            status_color = Colors.ORANGE
        else:
            status_color = get_status_color(status)
        
        self.log(f"  当前使用率: {color_text(f'{usage}%', status_color)}")
        self.log(f"  系统负载: {load[0]}, {load[1]}, {load[2]} (1分钟, 5分钟, 15分钟)")
        self.log(f"  阈值设置: 警告 {self.thresholds['cpu_warn']}% / 危险 {self.thresholds['cpu_crit']}%")
        
        # TOP进程
        top_procs = cpu.get('top_processes', [])
        if top_procs:
            self.log(f"  CPU使用率TOP5进程:")
            for i, proc in enumerate(top_procs[:5], 1):
                self.log(f"    {i}. {proc['command'][:50]}: {proc['cpu']}% (PID: {proc['pid']})")
        
        self.log("")
    
    def _analyze_memory(self):
        """分析内存"""
        self.log_section("内存信息", Colors.CYAN)
        mem = self.report_data.get('memory', {})
        
        if mem.get('error'):
            self.log(f"  {color_text('错误:', Colors.RED)} {mem['error']}")
            return
        
        total = mem.get('total', 0)
        used = mem.get('used', 0)
        available = mem.get('available', 0)
        usage_percent = mem.get('usage_percent', 0)
        
        status = determine_status(usage_percent, self.thresholds['mem_warn'], self.thresholds['mem_crit'])
        # 内存只显示警告色（橙色）或正常色（绿色），不显示红色
        if status == 'critical':
            status_color = Colors.ORANGE
        else:
            status_color = get_status_color(status)
        
        self.log(f"  总内存: {self._format_bytes(total)}")
        self.log(f"  已使用: {self._format_bytes(used)} ({color_text(f'{usage_percent}%', status_color)})")
        self.log(f"  可用: {self._format_bytes(available)}")
        self.log(f"  阈值设置: 警告 {self.thresholds['mem_warn']}% / 危险 {self.thresholds['mem_crit']}%")
        
        swap_total = mem.get('swap_total', 0)
        swap_used = mem.get('swap_used', 0)
        if swap_total > 0:
            swap_percent = round((swap_used / swap_total) * 100, 2)
            swap_color = Colors.ORANGE if swap_percent > 50 else Colors.GREEN
            self.log(f"  Swap: {self._format_bytes(swap_used)} / {self._format_bytes(swap_total)} ({color_text(f'{swap_percent}%', swap_color)})")
        
        self.log("")
    
    def _analyze_disk(self):
        """分析磁盘容量"""
        self.log_section("磁盘容量信息", Colors.CYAN)
        disk = self.report_data.get('disk', {})
        
        if disk.get('error'):
            self.log(f"  {color_text('错误:', Colors.RED)} {disk['error']}")
            return
        
        filesystems = disk.get('filesystems', [])
        if not filesystems:
            self.log("  未检测到文件系统")
            return
        
        for fs in filesystems:
            use_percent = fs['use_percent']
            status = determine_status(use_percent, self.thresholds['disk_warn'], self.thresholds['disk_crit'])
            status_color = get_status_color(status)
            
            self.log(f"  {fs['mountpoint']} ({fs['filesystem']})")
            self.log(f"    大小: {fs['size']}, 已用: {fs['used']}, 可用: {fs['available']}, 使用率: {color_text(f'{use_percent}%', status_color)}")
        
        # 大磁盘提示
        large_disks = disk.get('large_disks', [])
        if large_disks:
            self.log(f"  {color_text('大容量磁盘 (>512G):', Colors.PURPLE)}")
            for ld in large_disks:
                self.log(f"    {ld['mountpoint']}: {ld['size']}")
        
        self.log("")
    
    def _analyze_smart(self):
        """分析磁盘SMART"""
        self.log_section("磁盘 SMART 健康信息", Colors.CYAN)
        smart = self.report_data.get('smart', {})
        
        if smart.get('error'):
            self.log(f"  {color_text('错误:', Colors.RED)} {smart['error']}")
            return
        
        devices = smart.get('devices', [])
        if not devices:
            self.log("  未检测到磁盘设备")
            return
        
        for dev in devices:
            health = dev.get('health', 'unknown')
            health_color = Colors.GREEN if health == 'passed' else Colors.RED if health == 'failed' else Colors.YELLOW
            
            self.log(f"  设备: {dev['device']}")
            self.log(f"    型号: {dev['model']}")
            if dev.get('serial') and dev['serial'] != '未知':
                self.log(f"    序列号: {dev['serial']}")
            if dev.get('firmware') and dev['firmware'] != '未知':
                self.log(f"    固件版本: {dev['firmware']}")
            if dev.get('capacity') and dev['capacity'] != '未知':
                self.log(f"    容量: {dev['capacity']}")
            if dev.get('type'):
                self.log(f"    类型: {dev['type']}")
            self.log(f"    健康状态: {color_text(health.upper(), health_color)}")
            if dev.get('health_score') is not None:
                self.log(f"    健康度: {dev['health_score']}%")
            
            temp = dev.get('temperature')
            if temp is not None:
                temp_status = determine_status(temp, self.thresholds['temp_warn'], self.thresholds['temp_crit'])
                temp_color = get_status_color(temp_status)
                self.log(f"    温度: {color_text(f'{temp}°C', temp_color)}")

            if dev.get('is_nvme'):
                nvme = dev.get('nvme', {})
                if nvme:
                    if 'available_spare' in nvme:
                        spare = to_float(nvme.get('available_spare'))
                        spare_status = determine_status(spare, NVME_SPARE_WARN, NVME_SPARE_CRIT, reverse=True)
                        spare_color = get_status_color(spare_status)
                        self.log(f"    备用空间: {color_text(f'{spare}%', spare_color)}")
                    if 'percentage_used' in nvme:
                        used = to_float(nvme.get('percentage_used'))
                        used_status = determine_status(used, NVME_USED_WARN, NVME_USED_CRIT)
                        used_color = get_status_color(used_status)
                        self.log(f"    已用寿命: {color_text(f'{used}%', used_color)}")
                    media_errors = to_int(nvme.get('media_and_data_integrity_errors'))
                    if media_errors:
                        media_color = Colors.RED if media_errors > 0 else Colors.GREEN
                        self.log(f"    媒体错误: {color_text(str(media_errors), media_color)}")
                    unsafe_shutdowns = to_int(nvme.get('unsafe_shutdowns'))
                    if unsafe_shutdowns:
                        unsafe_color = Colors.ORANGE if unsafe_shutdowns > 0 else Colors.GREEN
                        self.log(f"    不安全关机: {color_text(str(unsafe_shutdowns), unsafe_color)}")
            else:
                attrs = {attr['id']: attr for attr in dev.get('attributes', [])}
                if attrs:
                    reallocated = attrs.get('5')
                    if reallocated:
                        raw = reallocated.get('raw_int', 0)
                        raw_color = Colors.RED if raw > 0 else Colors.GREEN
                        self.log(f"    重新分配扇区: {color_text(str(raw), raw_color)}")
                    uncorrect = attrs.get('187')
                    if uncorrect:
                        raw = uncorrect.get('raw_int', 0)
                        raw_color = Colors.RED if raw > 0 else Colors.GREEN
                        self.log(f"    不可纠正错误: {color_text(str(raw), raw_color)}")
                    life_attr = attrs.get('231')
                    if life_attr:
                        life_raw = life_attr.get('raw_int', 0)
                        life_val = life_attr.get('value', 0)
                        life = life_raw if life_raw > 0 else life_val
                        life_status = determine_status(life, SMART_LIFE_WARN, SMART_LIFE_CRIT, reverse=True)
                        life_color = get_status_color(life_status)
                        self.log(f"    剩余寿命: {color_text(f'{life}%', life_color)}")
                    power_on = attrs.get('9')
                    if power_on:
                        self.log(f"    通电时间: {power_on.get('raw', '-')}")
                    power_cycle = attrs.get('12')
                    if power_cycle:
                        self.log(f"    电源循环: {power_cycle.get('raw', '-')}")
                    total_written = attrs.get('241')
                    if total_written:
                        self.log(f"    总写入: {total_written.get('raw', '-')}")
                    total_read = attrs.get('242')
                    if total_read:
                        self.log(f"    总读取: {total_read.get('raw', '-')}")
            
            errors = dev.get('errors', [])
            if errors:
                for err in errors:
                    self.log(f"    {color_text('错误:', Colors.ORANGE)} {err}")
        
        self.log("")
    
    def _analyze_io(self):
        """分析磁盘IO"""
        self.log_section("磁盘 IO 信息", Colors.CYAN)
        io = self.report_data.get('io', {})
        
        if io.get('error'):
            self.log(f"  {color_text('提示:', Colors.YELLOW)} {io['error']}")
            return
        
        devices = io.get('devices', [])
        if not devices:
            self.log("  未检测到IO统计")
            return
        
        for dev in devices:
            self.log(f"  设备: {dev['device']}")
            self.log(f"    读取: {dev['r_s']:.2f} r/s, {dev['rkB_s']:.2f} kB/s")
            self.log(f"    写入: {dev['w_s']:.2f} w/s, {dev['wkB_s']:.2f} kB/s")
            self.log(f"    平均等待时间: {dev['await']:.2f} ms")
            self.log(f"    使用率: {dev['util']:.2f}%")
        
        self.log("")
    
    def _analyze_network(self):
        """分析网络"""
        self.log_section("网络接口信息", Colors.CYAN)
        net = self.report_data.get('network', {})
        
        if net.get('error'):
            self.log(f"  {color_text('错误:', Colors.RED)} {net['error']}")
            return
        
        interfaces = net.get('interfaces', [])
        if not interfaces:
            self.log("  未检测到网络接口")
            return
        
        for iface in interfaces:
            state = iface['state']
            state_color = Colors.GREEN if state == 'UP' else Colors.ORANGE if state == 'UNKNOWN' else Colors.RED
            
            self.log(f"  接口: {iface['name']} ({color_text(state, state_color)})")
            if iface.get('speed'):
                self.log(f"    速率: {iface['speed']}")
            self.log(f"    接收: {self._format_bytes(iface['rx_bytes'])} ({iface['rx_packets']} 包, {iface['rx_errors']} 错误)")
            self.log(f"    发送: {self._format_bytes(iface['tx_bytes'])} ({iface['tx_packets']} 包, {iface['tx_errors']} 错误)")
        
        self.log("")
    
    def _analyze_sensors(self):
        """分析传感器"""
        self.log_section("传感器信息", Colors.CYAN)
        sensors = self.report_data.get('sensors', {})
        
        if sensors.get('error'):
            self.log(f"  {color_text('提示:', Colors.YELLOW)} {sensors['error']}")
            return
        
        # 温度
        temps = sensors.get('temperatures', [])
        if temps:
            self.log("  温度传感器:")
            for temp in temps:
                value = temp['value']
                status = determine_status(value, self.thresholds['temp_warn'], self.thresholds['temp_crit'])
                status_color = get_status_color(status)
                unit = temp['unit']
                self.log(f"    {temp['name']}: {color_text(f'{value}{unit}', status_color)}")
        
        # 风扇
        fans = sensors.get('fans', [])
        if fans:
            self.log("  风扇传感器:")
            for fan in fans:
                value = fan['value']
                unit = fan['unit']
                # 风扇转速为0或过低可能有问题
                fan_color = Colors.RED if value == 0 else Colors.ORANGE if value < 500 else Colors.GREEN
                self.log(f"    {fan['name']}: {color_text(f'{value} {unit}', fan_color)}")
        
        # 电压
        voltages = sensors.get('voltages', [])
        if voltages:
            self.log("  电压传感器:")
            for volt in voltages:
                volt_value = volt['value']
                volt_unit = volt['unit']
                self.log(f"    {volt['name']}: {volt_value}{volt_unit}")
        
        self.log("")
    
    def _analyze_power(self):
        """分析电源"""
        self.log_section("电源信息", Colors.CYAN)
        power = self.report_data.get('power', {})
        
        if power.get('error'):
            self.log(f"  {color_text('提示:', Colors.YELLOW)} {power['error']}")
            return
        
        supplies = power.get('supplies', [])
        if not supplies:
            self.log("  未检测到电源信息")
            return
        
        for supply in supplies:
            if 'info' in supply:
                self.log(f"  {supply['info']}")
            elif 'power' in supply:
                pwr = supply['power']
                pwr_unit = supply['unit']
                self.log(f"  功率: {pwr:.2f} {pwr_unit}")
        
        self.log("")
    
    def _generate_summary(self):
        """生成隐患摘要"""
        self.log_section("=" * 80)
        self.log_section("概要信息", Colors.YELLOW)
        self.log_section("=" * 80)
        
        if not self.issues:
            self.log(color_text("✓ 服务运行正常，继续保持！", Colors.GREEN))
            self.log("")
            return
        
        # 按严重度排序
        critical = [i for i in self.issues if i['severity'] == 'critical']
        warning = [i for i in self.issues if i['severity'] == 'warning']
        
        # 按类别分组
        issues_by_category = {}
        for issue in self.issues:
            category = issue['category']
            if category not in issues_by_category:
                issues_by_category[category] = []
            issues_by_category[category].append(issue)
        
        # 生成概要列表
        summary_items = []
        for category, items in issues_by_category.items():
            has_critical = any(i['severity'] == 'critical' for i in items)
            color = Colors.RED if has_critical else Colors.ORANGE
            messages = [i['message'] for i in items]
            summary_items.append(color_text(f"• {category}: {', '.join(messages)}", color))
        
        self.log("发现以下隐患:")
        for item in summary_items:
            self.log(f"  {item}")
        self.log("")
    
    def save_reports(self, log_dir: str = '/tmp/logs/pve') -> str:
        """
        保存报告到文件
        
        Returns:
            str: HTML报告文件路径
        """
        os.makedirs(log_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 保存文本报告（无颜色）
        text_report_path = os.path.join(log_dir, f'hardware_report_{timestamp}.log')
        with open(text_report_path, 'w', encoding='utf-8') as f:
            for line in self.report_lines:
                f.write(strip_ansi(line) + '\n')
        
        # 保存JSON报告
        json_report_path = os.path.join(log_dir, 'hardware_report.json')
        json_data = {
            'timestamp': datetime.now().isoformat(),
            'data': self.report_data,
            'issues': self.issues,
            'thresholds': self.thresholds
        }
        with open(json_report_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        # 保存HTML报告
        html_report_path = os.path.join(log_dir, f'hardware_report_{timestamp}.html')
        html_content = self._generate_html_report()
        with open(html_report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # 保留最近5份日志
        self._cleanup_old_logs(log_dir, 'hardware_report_*.log', 5)
        self._cleanup_old_logs(log_dir, 'hardware_report_*.html', 5)
        
        self.log("")
        self.log(color_text(f"报告已保存:", Colors.CYAN))
        self.log(f"  文本报告: {text_report_path}")
        self.log(f"  JSON报告: {json_report_path}")
        self.log(f"  HTML报告: {html_report_path}")
        
        return html_report_path
    
    def _cleanup_old_logs(self, log_dir: str, pattern: str, keep: int):
        """清理旧日志，保留最近N份"""
        import glob
        logs = sorted(glob.glob(os.path.join(log_dir, pattern)))
        if len(logs) > keep:
            for old_log in logs[:-keep]:
                try:
                    os.remove(old_log)
                except:
                    pass
    
    def _generate_html_report(self) -> str:
        """生成HTML格式的报告"""
        now = datetime.now()
        hostname = run_command("hostname")[0].strip() or "PVE服务器"
        
        # 生成概要信息
        summary_items = []
        if not self.issues:
            summary_items.append("<li><span style='color: green;'>✓ 服务运行正常，未发现硬件隐患，继续保持！</span></li>")
        else:
            # 按类别分组
            issues_by_category = {}
            for issue in self.issues:
                category = issue['category']
                if category not in issues_by_category:
                    issues_by_category[category] = []
                issues_by_category[category].append(issue)
            
            # 生成概要列表
            for category, items in issues_by_category.items():
                has_critical = any(i['severity'] == 'critical' for i in items)
                color = 'red' if has_critical else 'orange'
                messages = [i['message'] for i in items]
                summary_items.append(f"<li><span style='color: {color};'>{category}: {', '.join(messages)}</span></li>")
            
        summary_content = '\n'.join(summary_items)
        
        # 生成系统状态表格
        sysinfo_rows = []
        
        # CPU信息
        cpu = self.report_data.get('cpu', {})
        if not cpu.get('error'):
            usage = cpu.get('usage', 0)
            load = cpu.get('load', [0, 0, 0])
            status = determine_status(usage, self.thresholds['cpu_warn'], self.thresholds['cpu_crit'])
            color = 'orange' if status != 'normal' else 'auto'
            
            cpu_desc = f"使用率: <span style='color: {color}'>{usage}%</span><br/>"
            cpu_desc += f"负载: {load[0]}, {load[1]}, {load[2]} (1/5/15分钟)<br/>"
            cpu_desc += f""
            
            top_procs = cpu.get('top_processes', [])
            if top_procs:
                cpu_desc += "<br/>TOP5进程:<br/>" + "<br/>".join([
                    f"{i+1}. {proc['command'][:50]}: {proc['cpu']}% (PID: {proc['pid']})" 
                    for i, proc in enumerate(top_procs[:5])
                ])
            
            sysinfo_rows.append(f"<tr><td>CPU</td><td>{cpu_desc}</td></tr>")
        
        # 内存信息
        mem = self.report_data.get('memory', {})
        if not mem.get('error'):
            total = mem.get('total', 0)
            used = mem.get('used', 0)
            available = mem.get('available', 0)
            usage_percent = mem.get('usage_percent', 0)
            status = determine_status(usage_percent, self.thresholds['mem_warn'], self.thresholds['mem_crit'])
            color = 'orange' if status != 'normal' else 'auto'
            
            mem_desc = f"总内存: {self._format_bytes(total)}<br/>"
            mem_desc += f"已使用: {self._format_bytes(used)} (<span style='color: {color}'>{usage_percent}%</span>)<br/>"
            mem_desc += f"可用: {self._format_bytes(available)}<br/>"
            mem_desc += f"阈值: 警告 {self.thresholds['mem_warn']}% / 危险 {self.thresholds['mem_crit']}%"
            
            swap_total = mem.get('swap_total', 0)
            swap_used = mem.get('swap_used', 0)
            if swap_total > 0:
                swap_percent = round((swap_used / swap_total) * 100, 2)
                swap_color = 'orange' if swap_percent > 50 else 'auto'
                mem_desc += f"<br/>Swap: {self._format_bytes(swap_used)} / {self._format_bytes(swap_total)} (<span style='color: {swap_color}'>{swap_percent}%</span>)"
            
            sysinfo_rows.append(f"<tr><td>内存</td><td>{mem_desc}</td></tr>")
        
        sysinfo_content = '<tbody>' + '\n'.join(sysinfo_rows) + '\n</tbody>' if sysinfo_rows else '<tbody><tr><td colspan="2">无系统信息</td></tr></tbody>'
        
        # 生成磁盘容量信息表格
        disk_capacity_rows = []
        disk = self.report_data.get('disk', {})
        if not disk.get('error'):
            for fs in disk.get('filesystems', []):
                use_percent = fs['use_percent']
                status = determine_status(use_percent, self.thresholds['disk_warn'], self.thresholds['disk_crit'])
                color = 'red' if status == 'critical' else 'orange' if status == 'warning' else 'auto'
                
                disk_desc = f"大小: {fs['size']}<br/>"
                disk_desc += f"已用: {fs['used']}<br/>"
                disk_desc += f"可用: {fs['available']}<br/>"
                disk_desc += f"使用率: <span style='color: {color}'>{use_percent}%</span>"
                
                disk_capacity_rows.append(f"<tr><td>{fs['mountpoint']}</td><td>{disk_desc}</td></tr>")
        
        disk_capacity_content = '<tbody>' + '\n'.join(disk_capacity_rows) + '\n</tbody>' if disk_capacity_rows else '<tbody><tr><td colspan="2">无磁盘容量信息</td></tr></tbody>'
        
        # 生成磁盘健康度信息表格（SMART + IO）
        disk_health_rows = []
        
        # 磁盘SMART
        smart = self.report_data.get('smart', {})
        if not smart.get('error'):
            for dev in smart.get('devices', []):
                health = dev.get('health', 'unknown')
                health_color = 'green' if health == 'passed' else 'red' if health == 'failed' else 'orange'
                
                smart_desc = f"型号: {dev['model']}<br/>"
                if dev.get('serial') and dev['serial'] != '未知':
                    smart_desc += f"序列号: {dev['serial']}<br/>"
                if dev.get('capacity') and dev['capacity'] != '未知':
                    smart_desc += f"容量: {dev['capacity']}<br/>"
                if dev.get('type'):
                    smart_desc += f"类型: {dev['type']}<br/>"
                smart_desc += f"健康状态: <span style='color: {health_color}'>{health.upper()}</span><br/>"
                if dev.get('health_score') is not None:
                    smart_desc += f"健康度: {dev['health_score']}%<br/>"
                
                temp = dev.get('temperature')
                if temp is not None:
                    temp_status = determine_status(temp, self.thresholds['temp_warn'], self.thresholds['temp_crit'])
                    temp_color = 'red' if temp_status == 'critical' else 'orange' if temp_status == 'warning' else 'auto'
                    smart_desc += f"温度: <span style='color: {temp_color}'>{temp}°C</span>"

                if dev.get('is_nvme'):
                    nvme = dev.get('nvme', {})
                    if nvme:
                        if 'available_spare' in nvme:
                            spare = to_float(nvme.get('available_spare'))
                            spare_status = determine_status(spare, NVME_SPARE_WARN, NVME_SPARE_CRIT, reverse=True)
                            spare_color = 'red' if spare_status == 'critical' else 'orange' if spare_status == 'warning' else 'auto'
                            smart_desc += f"<br/>备用空间: <span style='color: {spare_color}'>{spare}%</span>"
                        if 'percentage_used' in nvme:
                            used = to_float(nvme.get('percentage_used'))
                            used_status = determine_status(used, NVME_USED_WARN, NVME_USED_CRIT)
                            used_color = 'red' if used_status == 'critical' else 'orange' if used_status == 'warning' else 'auto'
                            smart_desc += f"<br/>已用寿命: <span style='color: {used_color}'>{used}%</span>"
                        media_errors = to_int(nvme.get('media_and_data_integrity_errors'))
                        if media_errors:
                            media_color = 'red' if media_errors > 0 else 'auto'
                            smart_desc += f"<br/>媒体错误: <span style='color: {media_color}'>{media_errors}</span>"
                        unsafe_shutdowns = to_int(nvme.get('unsafe_shutdowns'))
                        if unsafe_shutdowns:
                            unsafe_color = 'orange' if unsafe_shutdowns > 0 else 'auto'
                            smart_desc += f"<br/>不安全关机: <span style='color: {unsafe_color}'>{unsafe_shutdowns}</span>"
                else:
                    attrs = {attr['id']: attr for attr in dev.get('attributes', [])}
                    if attrs:
                        reallocated = attrs.get('5')
                        if reallocated:
                            raw = reallocated.get('raw_int', 0)
                            raw_color = 'red' if raw > 0 else 'auto'
                            smart_desc += f"<br/>重新分配扇区: <span style='color: {raw_color}'>{raw}</span>"
                        uncorrect = attrs.get('187')
                        if uncorrect:
                            raw = uncorrect.get('raw_int', 0)
                            raw_color = 'red' if raw > 0 else 'auto'
                            smart_desc += f"<br/>不可纠正错误: <span style='color: {raw_color}'>{raw}</span>"
                        life_attr = attrs.get('231')
                        if life_attr:
                            life_raw = life_attr.get('raw_int', 0)
                            life_val = life_attr.get('value', 0)
                            life = life_raw if life_raw > 0 else life_val
                            life_status = determine_status(life, SMART_LIFE_WARN, SMART_LIFE_CRIT, reverse=True)
                            life_color = 'red' if life_status == 'critical' else 'orange' if life_status == 'warning' else 'auto'
                            smart_desc += f"<br/>剩余寿命: <span style='color: {life_color}'>{life}%</span>"
                
                disk_health_rows.append(f"<tr><td>SMART ({dev['device']})</td><td>{smart_desc}</td></tr>")
        
        # 磁盘IO
        io = self.report_data.get('io', {})
        if not io.get('error'):
            for dev in io.get('devices', []):
                io_desc = f"读取: {dev['r_s']:.2f} r/s, {dev['rkB_s']:.2f} kB/s<br/>"
                io_desc += f"写入: {dev['w_s']:.2f} w/s, {dev['wkB_s']:.2f} kB/s<br/>"
                
                await_val = dev['await']
                await_color = 'red' if await_val > self.thresholds['io_wait_crit'] else 'orange' if await_val > self.thresholds['io_wait_warn'] else 'auto'
                io_desc += f"平均等待: <span style='color: {await_color}'>{await_val:.2f} ms</span><br/>"
                io_desc += f"使用率: {dev['util']:.2f}%"
                
                disk_health_rows.append(f"<tr><td>IO ({dev['device']})</td><td>{io_desc}</td></tr>")
        
        disk_health_content = '<tbody>' + '\n'.join(disk_health_rows) + '\n</tbody>' if disk_health_rows else '<tbody><tr><td colspan="2">无磁盘健康度信息</td></tr></tbody>'
        
        # 生成网络信息表格
        network_rows = []
        net = self.report_data.get('network', {})
        if not net.get('error'):
            for iface in net.get('interfaces', []):
                state = iface['state']
                state_color = 'green' if state == 'UP' else 'orange' if state == 'UNKNOWN' else 'red'
                
                net_desc = f"状态: <span style='color: {state_color}'>{state}</span><br/>"
                if iface.get('speed'):
                    net_desc += f"速率: {iface['speed']}<br/>"
                net_desc += f"接收: {self._format_bytes(iface['rx_bytes'])} ({iface['rx_packets']} 包, "
                rx_err_color = 'red' if iface['rx_errors'] > 0 else 'auto'
                net_desc += f"<span style='color: {rx_err_color}'>{iface['rx_errors']} 错误</span>)<br/>"
                net_desc += f"发送: {self._format_bytes(iface['tx_bytes'])} ({iface['tx_packets']} 包, "
                tx_err_color = 'red' if iface['tx_errors'] > 0 else 'auto'
                net_desc += f"<span style='color: {tx_err_color}'>{iface['tx_errors']} 错误</span>)"
                
                network_rows.append(f"<tr><td>{iface['name']}</td><td>{net_desc}</td></tr>")
        
        network_content = '<tbody>' + '\n'.join(network_rows) + '\n</tbody>' if network_rows else '<tbody><tr><td colspan="2">无网络信息</td></tr></tbody>'
        
        # 生成传感器信息表格
        sensor_rows = []
        sensors = self.report_data.get('sensors', {})
        if not sensors.get('error'):
            # 温度传感器
            temps = sensors.get('temperatures', [])
            if temps:
                for temp in temps:
                    value = temp['value']
                    status = determine_status(value, self.thresholds['temp_warn'], self.thresholds['temp_crit'])
                    color = 'red' if status == 'critical' else 'orange' if status == 'warning' else 'auto'
                    sensor_rows.append(f"<tr><td>温度 ({temp['name']})</td><td><span style='color: {color}'>{value}{temp['unit']}</span></td></tr>")
            
            # 风扇传感器
            fans = sensors.get('fans', [])
            if fans:
                for fan in fans:
                    value = fan['value']
                    color = 'red' if value == 0 else 'orange' if value < 500 else 'auto'
                    sensor_rows.append(f"<tr><td>风扇 ({fan['name']})</td><td><span style='color: {color}'>{value} {fan['unit']}</span></td></tr>")
            
            # 电压传感器
            voltages = sensors.get('voltages', [])
            if voltages:
                for volt in voltages:
                    sensor_rows.append(f"<tr><td>电压 ({volt['name']})</td><td>{volt['value']}{volt['unit']}</td></tr>")
        
        sensor_content = '<tbody>' + '\n'.join(sensor_rows) + '\n</tbody>' if sensor_rows else '<tbody><tr><td colspan="2">无传感器信息或未安装监控工具</td></tr></tbody>'
        
        # 生成电源信息表格
        power_rows = []
        power = self.report_data.get('power', {})
        if not power.get('error'):
            supplies = power.get('supplies', [])
            for supply in supplies:
                if 'info' in supply:
                    power_rows.append(f"<tr><td>电源信息</td><td>{supply['info']}</td></tr>")
                elif 'power' in supply:
                    power_rows.append(f"<tr><td>功率</td><td>{supply['power']:.2f} {supply['unit']}</td></tr>")
        
        power_content = '<tbody>' + '\n'.join(power_rows) + '\n</tbody>' if power_rows else '<tbody><tr><td colspan="2">无电源信息</td></tr></tbody>'
        
        # HTML模板（参考 report.py 格式）
        html_template = """<div id="content" class="netease_mail_readhtml netease_mail_readhtml_webmail">
<style>
h3 { font-size: bold; }
table {
    border-top: 1px solid #999;
    border-left: 1px solid #999;
    border-spacing: 0;
    width: 100%%;
}
table tr td {
    padding: 5px;
    line-height: 20px;
    border-right: 1px solid #999;
    border-bottom: 1px solid #999;
}
table tr td:first-child {
    width: 30%%;
}
table tr td:nth-child(2) {
    width: 70%%;
}
.system-table tr td:first-child {
    width: 40%%;
}
.system-table tr td:nth-child(2) {
    width: 60%%;
}
</style>

<h2>%(hostname)s(%(ip)s)-PVE硬件健康报告</h2>
<h3 style="color: #cecece">报告时间：%(report_time)s</h3>
<div style="display: flex; flex-direction: column;align-items: center;">
    <h3>概要信息：</h3>
    <ul>
%(summary_content)s
    </ul>
</div>

<h3>系统状态：</h3>
<table border class="system-table">
%(sysinfo_content)s
</table>

<h3>磁盘容量：</h3>
<table border>
%(disk_capacity_content)s
</table>

<h3>磁盘健康度：</h3>
<table border>
%(disk_health_content)s
</table>

<h3>网络接口：</h3>
<table border>
%(network_content)s
</table>

<h3>传感器信息：</h3>
<table border>
%(sensor_content)s
</table>

<h3>电源信息：</h3>
<table border>
%(power_content)s
</table>

<div style="clear:both;height:1px;"></div>
</div>

<script>
var _n = document.querySelectorAll('[formAction], [onclick]');
for(var i=0;i<_n.length;i++){ 
	var _nc = _n[i];
	if (_nc.getAttribute('formAction')) {
		_nc.setAttribute('__formAction', _nc.getAttribute('formAction')), _nc.removeAttribute('formAction');
	}
	if (_nc.getAttribute('onclick')) {
		_nc.setAttribute('__onclick', _nc.getAttribute('onclick')), _nc.removeAttribute('onclick');
	}
}
</script>
<style type="text/css">
* {
  white-space: normal !important;
  word-break: break-word !important;
}
body{font-size:14px;font-family:arial,verdana,sans-serif;line-height:1.666;padding:0;margin:0;overflow:auto;white-space:normal;word-wrap:break-word;min-height:100px}
td, input, button, select, body{font-family:Helvetica, 'Microsoft Yahei', verdana}
pre {white-space:pre-wrap !important;white-space:-moz-pre-wrap;white-space:-pre-wrap;white-space:-o-pre-wrap;word-wrap:break-word;width:95%%}
pre * { white-space: unset !important; }
th,td{font-family:arial,verdana,sans-serif;line-height:1.666}
img{ border:0}
header,footer,section,aside,article,nav,hgroup,figure,figcaption{display:block}
blockquote{margin-right:0px}
</style>"""
        
        # 获取IP地址
        ip_output, _, _ = run_command("hostname -I | awk '{print $1}'")
        ip_addr = ip_output.strip() or "未知"
        
        return html_template % {
            'hostname': hostname,
            'ip': ip_addr,
            'report_time': now.strftime('%Y-%m-%d %H:%M:%S'),
            'summary_content': summary_content,
            'sysinfo_content': sysinfo_content,
            'disk_capacity_content': disk_capacity_content,
            'disk_health_content': disk_health_content,
            'network_content': network_content,
            'sensor_content': sensor_content,
            'power_content': power_content
        }
    
    def send_email(self, html_report_path: str, recipient: str = None, subject: str = None) -> bool:
        """
        通过 pve_tools.sh 发送HTML报告
        
        Args:
            html_report_path: HTML报告文件路径
            recipient: 收件人邮箱（如果为None，使用PVE配置的默认邮箱）
            subject: 邮件主题（如果为None，自动生成）
        
        Returns:
            bool: 发送成功返回True，失败返回False
        """
        try:
            # 检查HTML报告是否存在
            if not os.path.exists(html_report_path):
                self.log(color_text(f"错误: HTML报告文件不存在: {html_report_path}", Colors.RED))
                return False
            
            # 检查 pve_tools.sh 是否存在
            script_dir = os.path.dirname(os.path.abspath(__file__))
            pve_tools_path = os.path.join(script_dir, 'pve_tools.sh')
            
            if not os.path.exists(pve_tools_path):
                self.log(color_text(f"错误: pve_tools.sh 不存在: {pve_tools_path}", Colors.RED))
                return False
            
            # 确保脚本可执行
            os.chmod(pve_tools_path, 0o755)
            
            # 获取主机名
            hostname_output, _, _ = run_command("hostname")
            hostname = hostname_output.strip() or "PVE服务器"
            
            # 生成邮件主题
            if subject is None:
                critical_count = sum(1 for i in self.issues if i['severity'] == 'critical')
                warning_count = sum(1 for i in self.issues if i['severity'] == 'warning')
                
                if critical_count > 0:
                    status_text = f"⚠️ 危险 {critical_count} 个"
                elif warning_count > 0:
                    status_text = f"⚠️ 警告 {warning_count} 个"
                else:
                    status_text = "✓ 正常"
                
                subject = f"[{hostname}] 硬件健康报告 - {status_text}"
            
            # 如果没有指定收件人，从 pve_tools.sh 获取
            if recipient is None:
                stdout, _, code = run_command(f"bash {pve_tools_path} get-pve-email")
                if code == 0 and stdout.strip():
                    recipient = stdout.strip()
            
            if not recipient:
                self.log(color_text("错误: 未配置收件人邮箱", Colors.RED))
                self.log("请配置邮箱:")
                self.log("  方法1: 在 /etc/aliases 中添加 'root: your@email.com' 并运行 newaliases")
                self.log("  方法2: 在 /etc/pve/notifications.cfg 中配置邮箱")
                self.log("  方法3: 使用 --email 参数指定收件人")
                return False
            
            # 使用 pve_tools.sh 发送邮件
            cmd = f"bash {pve_tools_path} send-email --to '{recipient}' --subject '{subject}' --body-file '{html_report_path}' --html"
            stdout, stderr, code = run_command(cmd, timeout=30)
            
            if code == 0:
                self.log(color_text(f"✓ 邮件已发送至: {recipient}", Colors.GREEN))
                if stdout.strip():
                    self.log(f"  {stdout.strip()}")
                return True
            else:
                self.log(color_text(f"✗ 邮件发送失败", Colors.RED))
                if stderr.strip():
                    self.log(f"  错误信息: {stderr.strip()}")
                return False
            
        except Exception as e:
            self.log(color_text(f"发送邮件时出错: {str(e)}", Colors.RED))
            return False
    
    def log(self, message: str = ""):
        """记录日志"""
        print(message)
        self.report_lines.append(message)
    
    def log_section(self, message: str, color: str = None):
        """记录章节标题"""
        if color:
            self.log(color_text(message, color))
        else:
            self.log(message)
    
    @staticmethod
    def _format_bytes(bytes_val: int) -> str:
        """格式化字节数"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024
        return f"{bytes_val:.2f} PB"

# ========================= 主程序 =========================

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='PVE 硬件全面健康报告')
    parser.add_argument('--cpu-warn', type=float, default=DEFAULT_THRESHOLDS['cpu_warn'], help='CPU警告阈值(百分比)')
    parser.add_argument('--cpu-crit', type=float, default=DEFAULT_THRESHOLDS['cpu_crit'], help='CPU危险阈值(百分比)')
    parser.add_argument('--mem-warn', type=float, default=DEFAULT_THRESHOLDS['mem_warn'], help='内存警告阈值(百分比)')
    parser.add_argument('--mem-crit', type=float, default=DEFAULT_THRESHOLDS['mem_crit'], help='内存危险阈值(百分比)')
    parser.add_argument('--disk-warn', type=float, default=DEFAULT_THRESHOLDS['disk_warn'], help='磁盘警告阈值(百分比)')
    parser.add_argument('--disk-crit', type=float, default=DEFAULT_THRESHOLDS['disk_crit'], help='磁盘危险阈值(百分比)')
    parser.add_argument('--temp-warn', type=float, default=DEFAULT_THRESHOLDS['temp_warn'], help='温度警告阈值(摄氏度)')
    parser.add_argument('--temp-crit', type=float, default=DEFAULT_THRESHOLDS['temp_crit'], help='温度危险阈值(摄氏度)')
    parser.add_argument('--io-wait-warn', type=float, default=DEFAULT_THRESHOLDS['io_wait_warn'], help='IO等待警告阈值(毫秒)')
    parser.add_argument('--io-wait-crit', type=float, default=DEFAULT_THRESHOLDS['io_wait_crit'], help='IO等待危险阈值(毫秒)')
    parser.add_argument('--network-interfaces', type=str, default=None, help='要监控的网卡接口列表，用逗号分隔，如: eth0,enp2s0 (默认自动检测物理网卡)')
    parser.add_argument('--auto-install', action='store_true', help='自动安装缺失的监控工具（lm-sensors, ipmitool等）')
    parser.add_argument('--send-email', action='store_true', help='发送HTML报告到邮箱')
    parser.add_argument('--email', type=str, default=None, help='收件人邮箱地址（默认使用PVE配置的邮箱）')
    parser.add_argument('--email-subject', type=str, default=None, help='邮件主题（默认自动生成）')
    parser.add_argument('--log-dir', type=str, default='/tmp/logs/pve', help='日志保存目录')
    
    args = parser.parse_args()
    
    # 构建阈值字典
    thresholds = {
        'cpu_warn': args.cpu_warn,
        'cpu_crit': args.cpu_crit,
        'mem_warn': args.mem_warn,
        'mem_crit': args.mem_crit,
        'disk_warn': args.disk_warn,
        'disk_crit': args.disk_crit,
        'temp_warn': args.temp_warn,
        'temp_crit': args.temp_crit,
        'io_wait_warn': args.io_wait_warn,
        'io_wait_crit': args.io_wait_crit,
    }
    
    # 解析网卡接口列表
    network_interfaces = None
    if args.network_interfaces:
        network_interfaces = [iface.strip() for iface in args.network_interfaces.split(',') if iface.strip()]
    
    # 创建报告器
    reporter = HardwareReporter(thresholds, network_interfaces, args.auto_install)
    
    # 采集数据
    reporter.collect_all()
    
    # 分析并生成报告
    reporter.analyze_and_report()
    
    # 保存报告
    html_report_path = reporter.save_reports(args.log_dir)
    
    # 发送邮件
    if args.send_email:
        reporter.log("")
        reporter.send_email(html_report_path, args.email, args.email_subject)
    else:
        # 如果没有指定发送邮件参数，询问用户是否发送
        reporter.log("")
        try:
            user_input = input(color_text("是否发送邮件报告？(y/n): ", Colors.CYAN)).strip().lower()
            if user_input in ['y', 'yes', '是']:
                reporter.log("")
                reporter.send_email(html_report_path, args.email, args.email_subject)
        except (KeyboardInterrupt, EOFError):
            reporter.log("")
            reporter.log(color_text("已取消发送邮件", Colors.YELLOW))
    
    # 根据隐患数量返回退出码
    critical_count = sum(1 for i in reporter.issues if i['severity'] == 'critical')
    if critical_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
