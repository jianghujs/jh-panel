#!/usr/bin/env python3
"""
PVE硬件全面健康报告脚本
聚合 CPU/内存/磁盘/网络/温度/风扇/电源等信息并标记风险
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
        
        stdout, stderr, code = run_command("df -h")
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
        
        if not devices:
            # 备用检测
            for pattern in ["/dev/sd?", "/dev/nvme?n?"]:
                stdout, _, _ = run_command(f"ls {pattern} 2>/dev/null")
                if stdout:
                    devices.extend(stdout.strip().split())
        
        # 检查每个设备
        for device in devices:
            stdout, stderr, code = run_command(f"smartctl -a {device}")
            device_info = {
                'device': device,
                'model': '未知',
                'health': 'unknown',
                'temperature': None,
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
                elif 'smart overall-health' in line_lower or 'smart health status:' in line_lower:
                    if 'PASSED' in line or 'OK' in line:
                        device_info['health'] = 'passed'
                    else:
                        device_info['health'] = 'failed'
            
            # 解析温度
            is_nvme = 'nvme' in device
            if is_nvme:
                match = re.search(r'Temperature:\s*(\d+)', stdout)
                if match:
                    device_info['temperature'] = to_int(match.group(1))
            else:
                # SATA设备
                for line in stdout.split('\n'):
                    if re.match(r'^\s*194\s', line):
                        parts = line.split()
                        if len(parts) >= 10:
                            device_info['temperature'] = to_int(parts[9])
                        break
            
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
    def collect() -> Dict[str, Any]:
        """采集网络接口信息"""
        result = {
            'status': 'unknown',
            'interfaces': [],
            'error': None
        }
        
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
                state = 'DOWN'
                if 'state UP' in line:
                    state = 'UP'
                elif 'state DOWN' in line:
                    state = 'DOWN'
                elif 'state UNKNOWN' in line:
                    state = 'UNKNOWN'
                
                # 解析统计信息
                rx_bytes = 0
                rx_packets = 0
                rx_errors = 0
                tx_bytes = 0
                tx_packets = 0
                tx_errors = 0
                
                if i + 2 < len(lines):
                    rx_line = lines[i + 2].strip()
                    rx_parts = rx_line.split()
                    if len(rx_parts) >= 3:
                        rx_bytes = to_int(rx_parts[0])
                        rx_packets = to_int(rx_parts[1])
                        rx_errors = to_int(rx_parts[2])
                
                if i + 4 < len(lines):
                    tx_line = lines[i + 4].strip()
                    tx_parts = tx_line.split()
                    if len(tx_parts) >= 3:
                        tx_bytes = to_int(tx_parts[0])
                        tx_packets = to_int(tx_parts[1])
                        tx_errors = to_int(tx_parts[2])
                
                # 获取速率（如果可用）
                speed = None
                stdout2, _, code2 = run_command(f"ethtool {ifname} 2>/dev/null | grep Speed")
                if code2 == 0 and stdout2:
                    match_speed = re.search(r'Speed:\s*(\S+)', stdout2)
                    if match_speed:
                        speed = match_speed.group(1)
                
                result['interfaces'].append({
                    'name': ifname,
                    'state': state,
                    'rx_bytes': rx_bytes,
                    'rx_packets': rx_packets,
                    'rx_errors': rx_errors,
                    'tx_bytes': tx_bytes,
                    'tx_packets': tx_packets,
                    'tx_errors': tx_errors,
                    'speed': speed
                })
                
                i += 5
            else:
                i += 1
        
        return result

class SensorCollector:
    """传感器信息采集器（温度、风扇、电压）"""
    
    @staticmethod
    def collect() -> Dict[str, Any]:
        """采集传感器信息"""
        result = {
            'status': 'unknown',
            'temperatures': [],
            'fans': [],
            'voltages': [],
            'error': None
        }
        
        # 尝试使用 sensors
        stdout, stderr, code = run_command("sensors 2>/dev/null")
        if code == 0 and stdout:
            SensorCollector._parse_sensors(stdout, result)
        
        # 尝试使用 ipmitool
        stdout, stderr, code = run_command("ipmitool sensor 2>/dev/null")
        if code == 0 and stdout:
            SensorCollector._parse_ipmitool(stdout, result)
        
        if not result['temperatures'] and not result['fans'] and not result['voltages']:
            result['error'] = "未检测到传感器（可能需要安装 lm-sensors 或 ipmitool）"
        
        return result
    
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
    
    def __init__(self, thresholds: Dict[str, float]):
        self.thresholds = thresholds
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
        self.report_data['network'] = NetworkCollector.collect()
        
        # 传感器
        self.log("采集传感器信息...")
        self.report_data['sensors'] = SensorCollector.collect()
        
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
        
        # 分析各项指标
        self._analyze_cpu()
        self._analyze_memory()
        self._analyze_disk()
        self._analyze_smart()
        self._analyze_io()
        self._analyze_network()
        self._analyze_sensors()
        self._analyze_power()
        
        # 生成隐患摘要
        self._generate_summary()
    
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
        status_color = get_status_color(status)
        
        self.log(f"  CPU 使用率: {color_text(f'{usage}%', status_color)} (阈值: {self.thresholds['cpu_warn']}%/{self.thresholds['cpu_crit']}%)")
        self.log(f"  系统负载: {load[0]}, {load[1]}, {load[2]} (1分钟, 5分钟, 15分钟)")
        
        if status != 'normal':
            self.issues.append({
                'category': 'CPU',
                'severity': status,
                'message': f'CPU 使用率 {usage}%',
                'detail': f'当前使用率超过{"警告" if status == "warning" else "危险"}阈值'
            })
        
        # TOP进程
        top_procs = cpu.get('top_processes', [])
        if top_procs:
            self.log(f"  TOP 5 进程:")
            for proc in top_procs[:5]:
                self.log(f"    PID {proc['pid']}: {proc['command'][:50]} (CPU: {proc['cpu']}%, MEM: {proc['mem']}%)")
        
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
        status_color = get_status_color(status)
        
        self.log(f"  总内存: {self._format_bytes(total)}")
        self.log(f"  已使用: {self._format_bytes(used)} ({color_text(f'{usage_percent}%', status_color)})")
        self.log(f"  可用: {self._format_bytes(available)}")
        
        swap_total = mem.get('swap_total', 0)
        swap_used = mem.get('swap_used', 0)
        if swap_total > 0:
            swap_percent = round((swap_used / swap_total) * 100, 2)
            self.log(f"  Swap: {self._format_bytes(swap_used)} / {self._format_bytes(swap_total)} ({swap_percent}%)")
        
        if status != 'normal':
            self.issues.append({
                'category': '内存',
                'severity': status,
                'message': f'内存使用率 {usage_percent}%',
                'detail': f'当前使用率超过{"警告" if status == "warning" else "危险"}阈值'
            })
        
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
            
            if status != 'normal':
                self.issues.append({
                    'category': '磁盘容量',
                    'severity': status,
                    'message': f'{fs["mountpoint"]} 使用率 {use_percent}%',
                    'detail': f'挂载点 {fs["mountpoint"]} 空间不足'
                })
        
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
            self.log(f"    健康状态: {color_text(health.upper(), health_color)}")
            
            temp = dev.get('temperature')
            if temp is not None:
                temp_status = determine_status(temp, self.thresholds['temp_warn'], self.thresholds['temp_crit'])
                temp_color = get_status_color(temp_status)
                self.log(f"    温度: {color_text(f'{temp}°C', temp_color)}")
                
                if temp_status != 'normal':
                    self.issues.append({
                        'category': '磁盘温度',
                        'severity': temp_status,
                        'message': f'{dev["device"]} 温度 {temp}°C',
                        'detail': f'磁盘 {dev["device"]} 温度过高'
                    })
            
            errors = dev.get('errors', [])
            if errors:
                for err in errors:
                    self.log(f"    {color_text('错误:', Colors.ORANGE)} {err}")
            
            if health == 'failed':
                self.issues.append({
                    'category': '磁盘健康',
                    'severity': 'critical',
                    'message': f'{dev["device"]} SMART 检查失败',
                    'detail': f'磁盘 {dev["device"]} 健康检查未通过'
                })
        
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
            
            # 检查IO等待时间
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
            
            # 检查错误
            if iface['rx_errors'] > 0 or iface['tx_errors'] > 0:
                self.issues.append({
                    'category': '网络',
                    'severity': 'warning',
                    'message': f'{iface["name"]} 有网络错误',
                    'detail': f'接口 {iface["name"]} 检测到 {iface["rx_errors"]+iface["tx_errors"]} 个错误'
                })
        
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
                
                if status != 'normal':
                    self.issues.append({
                        'category': '温度',
                        'severity': status,
                        'message': f'{temp["name"]} {value}°C',
                        'detail': f'传感器 {temp["name"]} 温度过高'
                    })
        
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
        self.log_section("硬件隐患摘要", Colors.YELLOW)
        self.log_section("=" * 80)
        
        if not self.issues:
            self.log(color_text("✓ 未发现硬件隐患，所有指标正常。", Colors.GREEN))
            return
        
        # 按严重度排序
        critical = [i for i in self.issues if i['severity'] == 'critical']
        warning = [i for i in self.issues if i['severity'] == 'warning']
        
        self.log(f"发现 {len(self.issues)} 个隐患:")
        self.log(f"  {color_text('危险:', Colors.RED)} {len(critical)} 个")
        self.log(f"  {color_text('警告:', Colors.ORANGE)} {len(warning)} 个")
        self.log("")
        
        if critical:
            self.log(color_text("危险隐患:", Colors.RED))
            for issue in critical:
                self.log(f"  [{issue['category']}] {issue['message']}")
                self.log(f"    详情: {issue['detail']}")
            self.log("")
        
        if warning:
            self.log(color_text("警告隐患:", Colors.ORANGE))
            for issue in warning:
                self.log(f"  [{issue['category']}] {issue['message']}")
                self.log(f"    详情: {issue['detail']}")
            self.log("")
        
        # 建议
        if critical:
            self.log(color_text("⚠️ 建议: 发现危险隐患，请立即处理！", Colors.RED))
        elif warning:
            self.log(color_text("⚠️ 建议: 发现警告隐患，请保持关注。", Colors.ORANGE))
    
    def save_reports(self, log_dir: str = '/tmp/logs/pve'):
        """保存报告到文件"""
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
        
        # 保留最近5份日志
        self._cleanup_old_logs(log_dir, 'hardware_report_*.log', 5)
        
        self.log("")
        self.log(color_text(f"报告已保存:", Colors.CYAN))
        self.log(f"  文本报告: {text_report_path}")
        self.log(f"  JSON报告: {json_report_path}")
    
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
    
    # 创建报告器
    reporter = HardwareReporter(thresholds)
    
    # 采集数据
    reporter.collect_all()
    
    # 分析并生成报告
    reporter.analyze_and_report()
    
    # 保存报告
    reporter.save_reports(args.log_dir)
    
    # 根据隐患数量返回退出码
    critical_count = sum(1 for i in reporter.issues if i['severity'] == 'critical')
    if critical_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()

