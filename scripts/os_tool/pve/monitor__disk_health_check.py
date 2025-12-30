#!/usr/bin/env python3
"""
PVE硬盘健康监控脚本 - 修复对齐问题
"""

import os
import subprocess
import re
import sys
from datetime import datetime

# ========================= 配置区域 =========================
# 阈值配置
TEMP_WARNING = 55      # 温度警告阈值(℃)
TEMP_CRITICAL = 70     # 温度危险阈值(℃)
PERCENT_USED_WARN = 80  # 已用寿命百分比警告阈值(%)

# SATA设备关键参数映射
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

def strip_ansi(text):
    """移除ANSI颜色码"""
    return ANSI_ESCAPE_RE.sub('', text) if text else text

class ReportLogger:
    """记录最终报告并同步打印"""
    def __init__(self):
        self.lines = []
    
    def log(self, message=""):
        print(message)
        self.capture(message)
    
    def write_to_file(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        content = '\n'.join(self.lines).rstrip() + '\n'
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    def capture(self, message=""):
        self.lines.append(strip_ansi(message))

# ========================= 工具函数 =========================
def color_text(text, color):
    """为文本添加颜色"""
    return f"{color}{text}{Colors.END}"

def run_command(cmd):
    """执行shell命令并返回输出"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

def print_command_output(cmd, stdout, stderr, logger=None):
    """打印命令原始输出并可选写入日志"""
    header = f"\n{color_text('>>> 原始命令输出:', Colors.PURPLE)} {cmd}"
    print(header)
    if logger:
        logger.capture(header)
    
    if stdout.strip():
        output_text = stdout.rstrip()
    else:
        output_text = color_text("[无标准输出]", Colors.YELLOW)
    print(output_text)
    if logger:
        logger.capture(output_text)
    
    if stderr.strip():
        stderr_label = color_text("[stderr]", Colors.ORANGE)
        stderr_text = color_text(stderr.rstrip(), Colors.ORANGE)
        print(stderr_label)
        if logger:
            logger.capture(stderr_label)
        print(stderr_text)
        if logger:
            logger.capture(stderr_text)
    
    print()
    if logger:
        logger.capture("")

def get_display_width(text):
    """获取字符串在终端的显示宽度（中文字符算2个宽度）"""
    width = 0
    for char in text:
        # 判断是否为中文字符（粗略判断）
        if ord(char) > 127:
            width += 2
        else:
            width += 1
    return width

def pad_string(text, width, align='left'):
    """将字符串填充到指定显示宽度"""
    display_width = get_display_width(text)
    if display_width >= width:
        return text
    
    padding = width - display_width
    if align == 'left':
        return text + ' ' * padding
    else:  # right
        return ' ' * padding + text

def to_int(value, default=0):
    """尝试转换为整数，必要时抽取字符串中的数字"""
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

def parse_sata_attributes(output):
    """解析SATA设备的SMART属性"""
    attrs = {}
    lines = output.strip().split('\n')
    
    for line in lines:
        if re.match(r'^\s*\d+', line):
            parts = re.split(r'\s+', line.strip(), maxsplit=10)
            if len(parts) >= 10:
                attr_id = parts[0]
                attr_name = parts[1]
                raw_value = parts[9]
                if len(parts) > 10:
                    raw_value = f"{raw_value} {parts[10]}"
                
                attrs[attr_id] = {
                    'name': attr_name,
                    'value': to_int(parts[3]),
                    'worst': to_int(parts[4]),
                    'threshold': to_int(parts[5]),
                    'raw': raw_value,
                    'raw_int': to_int(raw_value),
                    'type': parts[6] if len(parts) > 6 else '',
                    'when_failed': parts[8] if len(parts) > 8 else '-'
                }
    return attrs

def parse_nvme_info(output):
    """解析NVMe设备的SMART信息"""
    info = {}
    lines = output.strip().split('\n')
    
    current_section = None
    for line in lines:
        line = line.strip()
        
        # 检测章节标题
        if line.startswith('=== START OF SMART DATA SECTION ==='):
            current_section = 'smart'
        elif line.startswith('SMART/Health Information'):
            current_section = 'health'
        
        # 解析键值对
        if ':' in line and current_section == 'health':
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            
            # 简化和标准化键名
            key_lower = key.lower().replace(' ', '_')
            
            # 提取数值
            num_match = re.search(r'(\d+\.?\d*)', value)
            if num_match:
                info[key_lower] = num_match.group(1)
            else:
                info[key_lower] = value
    
    return info

# ========================= 设备检查类 =========================
class DiskChecker:
    def __init__(self, device, raw_output=None, logger=None):
        self.device = device
        self.name = device.split('/')[-1]
        self.is_nvme = 'nvme' in device
        self.info = {}
        self.issues = []
        self.status = "正常"
        self.attributes = []
        self.raw_smart_output = raw_output or ""
        self.logger = logger
    
    def log(self, message=""):
        if self.logger:
            self.logger.log(message)
        else:
            print(message)
        
    def get_basic_info(self):
        """获取设备基本信息"""
        output = self.raw_smart_output
        
        info = {
            'model': '未知',
            'serial': '未知',
            'firmware': '未知',
            'capacity': '未知',
            'type': 'SSD' if self.is_nvme else 'SATA'
        }
        
        if not output:
            return info
        
        for line in output.split('\n'):
            line_lower = line.lower()
            if 'model number:' in line_lower or 'device model:' in line_lower:
                info['model'] = line.split(':', 1)[1].strip()
            elif 'serial number:' in line_lower:
                info['serial'] = line.split(':', 1)[1].strip()
            elif 'firmware version:' in line_lower:
                info['firmware'] = line.split(':', 1)[1].strip()
            elif 'user capacity:' in line_lower or 'total nvm capacity:' in line_lower:
                capacity_match = re.search(r'\[(.*?)\]', line)
                if capacity_match:
                    info['capacity'] = capacity_match.group(1)
            elif 'rotation rate:' in line_lower:
                if 'solid state' in line_lower:
                    info['type'] = 'SSD'
                else:
                    info['type'] = 'HDD'
        
        return info
    
    def check_health(self):
        """检查设备健康状态"""
        output = self.raw_smart_output
        if 'PASSED' in output or 'OK' in output:
            return "通过"
        else:
            return "失败"
    
    def check_sata_disk(self):
        """检查SATA设备"""
        attrs = parse_sata_attributes(self.raw_smart_output)
        
        name_width = 24
        key_width = 24
        self.log(f"    {color_text('SATA详细参数:', Colors.CYAN)}")
        self.log(f"    {pad_string('名称', name_width)} {pad_string('参数', key_width)} {pad_string('当前值', 8)} {pad_string('阈值', 8)} {pad_string('原始值', 12)} 状态")
        self.log(f"    {'-' * (name_width + key_width + 40)}")
        
        for attr_id, attr_data in attrs.items():
            if attr_id in SATA_PARAMS:
                cn_name, en_name = SATA_PARAMS[attr_id]
                
                value = attr_data['value']
                threshold = attr_data['threshold']
                raw = attr_data['raw']
                raw_value = attr_data.get('raw_int', to_int(raw))
                when_failed = attr_data['when_failed']
                
                # 判断状态
                status = "正常"
                status_color = Colors.GREEN
                
                # 特定参数的特殊判断
                if attr_id == "5":  # 重新分配扇区计数
                    if raw_value > 0:
                        status = "异常"
                        status_color = Colors.RED
                        self.issues.append(f"坏块:{raw_value}")
                        self.status = "异常"
                    elif when_failed != '-':
                        status = "警告"
                        status_color = Colors.ORANGE
                        if self.status == "正常":
                            self.status = "警告"
                
                elif attr_id == "187":  # 报告不可纠正错误
                    if raw_value > 0:
                        status = "异常"
                        status_color = Colors.RED
                        self.issues.append(f"不可纠正错误:{raw_value}")
                        self.status = "异常"
                
                elif attr_id == "194":  # 温度
                    temp = raw_value
                    if temp >= TEMP_CRITICAL:
                        status = "危险"
                        status_color = Colors.RED
                        self.issues.append(f"高温:{temp}℃")
                        self.status = "异常"
                    elif temp >= TEMP_WARNING:
                        status = "警告"
                        status_color = Colors.ORANGE
                        if self.status == "异常":
                            self.status = "异常"
                        elif self.status == "正常":
                            self.status = "警告"
                
                elif attr_id == "231":  # SSD剩余寿命
                    life = raw_value if raw_value > 0 else value
                    if life <= 10:
                        status = "危险"
                        status_color = Colors.RED
                        self.issues.append(f"寿命:{life}%")
                        self.status = "异常"
                    elif life <= 30:
                        status = "警告"
                        status_color = Colors.ORANGE
                        if self.status == "异常":
                            self.status = "异常"
                        elif self.status == "正常":
                            self.status = "警告"
                
                # 对于其他参数，如果当前值小于等于阈值且不为0，标记为警告
                elif threshold > 0 and value <= threshold:
                    status = "警告"
                    status_color = Colors.ORANGE
                    if self.status == "正常":
                        self.status = "警告"
                
                # 保存属性信息用于汇总
                self.attributes.append({
                    'name': cn_name,
                    'value': value,
                    'threshold': threshold,
                    'raw': raw,
                    'status': status,
                    'status_color': status_color
                })
                
                # 显示参数
                cn_display = pad_string(cn_name, name_width)
                key_display = pad_string(en_name, key_width)
                value_display = pad_string(str(value), 8)
                threshold_display = pad_string(str(threshold), 8)
                raw_display = pad_string(raw, 12)
                
                self.log(f"    {cn_display} {key_display} {value_display} {threshold_display} {raw_display} {color_text(status, status_color)}")
    
    def check_nvme_disk(self):
        """检查NVMe设备"""
        info = parse_nvme_info(self.raw_smart_output)
        
        name_width = 24
        key_width = 24
        self.log(f"    {color_text('NVMe详细参数:', Colors.CYAN)}")
        self.log(f"    {pad_string('名称', name_width)} {pad_string('参数', key_width)} {pad_string('值', 20)} 状态")
        self.log(f"    {'-' * (name_width + key_width + 30)}")
        
        # NVMe关键参数检查
        nvme_params = [
            ("temperature", "温度", "℃"),
            ("available_spare", "可用备用空间", "%"),
            ("available_spare_threshold", "备用空间阈值", "%"),
            ("percentage_used", "已用寿命", "%"),
            ("power_on_hours", "通电时间", "小时"),
            ("unsafe_shutdowns", "不安全关机", "次"),
            ("media_and_data_integrity_errors", "媒体错误", "个"),
            ("data_units_written", "写入数据", ""),
            ("data_units_read", "读取数据", "")
        ]
        
        for key, cn_name, unit in nvme_params:
            if key in info:
                value_str = info[key]
                
                # 尝试转换为数值
                try:
                    if '.' in value_str:
                        value_num = float(value_str)
                    else:
                        value_num = int(value_str)
                    is_numeric = True
                except:
                    value_num = 0
                    is_numeric = False
                
                status = "正常"
                status_color = Colors.GREEN
                
                # 根据不同参数应用规则
                if key == 'available_spare' and is_numeric:
                    if value_num < 10:
                        status = "异常"
                        status_color = Colors.RED
                        self.issues.append(f"备用空间:{value_num}%")
                        self.status = "异常"
                    elif value_num < 20:
                        status = "警告"
                        status_color = Colors.ORANGE
                        if self.status == "正常":
                            self.status = "警告"
                
                elif key == 'percentage_used' and is_numeric:
                    if value_num >= PERCENT_USED_WARN:
                        status = "警告"
                        status_color = Colors.ORANGE
                        if self.status == "正常":
                            self.status = "警告"
                        self.issues.append(f"寿命:{value_num}%")
                
                elif key == 'media_and_data_integrity_errors' and is_numeric:
                    if value_num > 0:
                        status = "异常"
                        status_color = Colors.RED
                        self.issues.append(f"媒体错误:{value_num}")
                        self.status = "异常"
                
                elif key == 'temperature' and is_numeric:
                    if value_num >= TEMP_CRITICAL:
                        status = "危险"
                        status_color = Colors.RED
                        self.issues.append(f"高温:{value_num}℃")
                        self.status = "异常"
                    elif value_num >= TEMP_WARNING:
                        status = "警告"
                        status_color = Colors.ORANGE
                        if self.status == "异常":
                            self.status = "异常"
                        elif self.status == "正常":
                            self.status = "警告"
                
                elif key == 'unsafe_shutdowns' and is_numeric:
                    if value_num > 0:
                        status = "警告"
                        status_color = Colors.ORANGE
                        if self.status == "正常":
                            self.status = "警告"
                        self.issues.append(f"不安全关机:{value_num}")
                
                # 格式化显示值
                if is_numeric and unit:
                    display_value = f"{value_num}{unit}"
                else:
                    display_value = str(value_str)
                
                # 保存属性信息
                self.attributes.append({
                    'name': cn_name,
                    'value': display_value,
                    'status': status,
                    'status_color': status_color
                })
                
                # 显示参数
                cn_display = pad_string(cn_name, name_width)
                key_display = pad_string(key, key_width)
                value_display = pad_string(display_value, 20)
                
                self.log(f"    {cn_display} {key_display} {value_display} {color_text(status, status_color)}")
    
    def check(self):
        """执行完整的设备检查"""
        self.log(f"\n{color_text('=' * 60, Colors.YELLOW)}")
        self.log(f"{color_text('设备:', Colors.CYAN)} {self.device}")
        
        # 获取基本信息
        self.info = self.get_basic_info()
        self.log(f"{color_text('型号:', Colors.CYAN)} {self.info['model']}")
        self.log(f"{color_text('序列号:', Colors.CYAN)} {self.info['serial']}")
        self.log(f"{color_text('容量:', Colors.CYAN)} {self.info['capacity']}")
        self.log(f"{color_text('类型:', Colors.CYAN)} {self.info['type']}")
        
        # 检查健康状态
        health = self.check_health()
        health_color = Colors.GREEN if health == "通过" else Colors.RED
        self.log(f"{color_text('健康状态:', Colors.CYAN)} {color_text(health, health_color)}")
        
        if health != "通过":
            self.status = "异常"
            self.issues.append("健康检查失败")
            return {
                'device': self.device,
                'model': self.info['model'],
                'status': self.status,
                'issues': ', '.join(self.issues) if self.issues else '无',
                'type': self.info['type']
            }
        
        # 根据设备类型检查详细参数
        if self.is_nvme:
            self.check_nvme_disk()
        else:
            self.check_sata_disk()
        
        self.log(f"{color_text('=' * 60, Colors.YELLOW)}")
        
        return {
            'device': self.device,
            'model': self.info['model'],
            'status': self.status,
            'issues': ', '.join(self.issues) if self.issues else '无',
            'type': self.info['type']
        }

# ========================= 主程序 =========================
def main():
    """主函数"""
    report_logger = ReportLogger()
    scan_cmd = "smartctl --scan"
    scan_output, scan_err, _ = run_command(scan_cmd)
    print_command_output(scan_cmd, scan_output, scan_err, report_logger)
    
    devices = []
    
    if scan_output.strip():
        for line in scan_output.strip().split('\n'):
            if line:
                device = line.split()[0]
                devices.append(device)
    else:
        # 后备检测方法
        for pattern in ["/dev/sd?", "/dev/nvme?n?"]:
            cmd = f"ls {pattern} 2>/dev/null"
            output, _, _ = run_command(cmd)
            if output:
                devices.extend(output.strip().split())

    raw_outputs = {}
    for device in devices:
        smart_cmd = f"smartctl -a {device}"
        stdout, stderr, _ = run_command(smart_cmd)
        print_command_output(smart_cmd, stdout, stderr, report_logger)
        raw_outputs[device] = stdout
    
    if not devices:
        print(color_text("错误：未检测到任何硬盘设备！", Colors.RED))
        sys.exit(1)
    
    report_time = datetime.now()
    report_time_str = report_time.strftime('%Y-%m-%d %H:%M:%S')
    
    report_logger.log(f"{color_text('PVE硬盘健康检查报告', Colors.YELLOW)}")
    report_logger.log(f"检查时间: {report_time_str}")
    report_logger.log("")
    
    # 检查每个设备
    results = []
    for device in devices:
        checker = DiskChecker(device, raw_outputs.get(device, ""), report_logger)
        result = checker.check()
        if result:
            results.append(result)
    
    # 生成汇总报告
    report_logger.log(f"\n{color_text('=' * 60, Colors.YELLOW)}")
    report_logger.log(f"{color_text('硬盘健康检查汇总报告', Colors.CYAN)}")
    report_logger.log(f"{color_text('=' * 60, Colors.YELLOW)}")
    summary_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    report_logger.log(f"检查时间: {summary_time_str}")
    
    total = len(results)
    healthy = sum(1 for r in results if r['status'] == '正常')
    warning = sum(1 for r in results if r['status'] == '警告')
    critical = sum(1 for r in results if r['status'] == '异常')
    
    report_logger.log(f"检测设备: {total}")
    report_logger.log(f"{color_text('健康设备:', Colors.GREEN)} {healthy}")
    report_logger.log(f"{color_text('警告设备:', Colors.ORANGE)} {warning}")
    report_logger.log(f"{color_text('异常设备:', Colors.RED)} {critical}")
    
    # 设备状态表
    if results:
        report_logger.log(f"\n{color_text('设备状态表:', Colors.CYAN)}")
        report_logger.log(f"{'-' * 80}")
        header = f"| {pad_string('设备', 8)} | {pad_string('型号', 20)} | {pad_string('类型', 6)} | {pad_string('状态', 8)} | {pad_string('问题摘要', 30)} |"
        report_logger.log(header)
        report_logger.log(f"{'-' * 80}")
        
        for r in results:
            status_color = (
                Colors.RED if r['status'] == '异常' else
                Colors.ORANGE if r['status'] == '警告' else Colors.GREEN
            )
            
            # 截短过长的字符串
            device_short = r['device'].split('/')[-1]
            model_short = r['model']
            if len(model_short) > 20:
                model_short = model_short[:17] + "..."
            
            issues_short = r['issues']
            if len(issues_short) > 30:
                issues_short = issues_short[:27] + "..."
            
            report_logger.log(
                f"| {pad_string(device_short, 8)} | {pad_string(model_short, 20)} | "
                f"{pad_string(r['type'], 6)} | {color_text(pad_string(r['status'], 8), status_color)} | "
                f"{pad_string(issues_short, 30)} |"
            )
        
        report_logger.log(f"{'-' * 80}")
    
    # 给出建议
    exit_code = 0
    if critical > 0:
        report_logger.log(f"\n{color_text('⚠️ 警告：发现异常设备，请立即备份数据！', Colors.RED)}")
        exit_code = 1
    elif warning > 0:
        report_logger.log(f"\n{color_text('⚠️ 注意：发现警告设备，请保持关注。', Colors.ORANGE)}")
    else:
        report_logger.log(f"\n{color_text('✓ 所有硬盘状态正常。', Colors.GREEN)}")
    
    report_filename = f"pve_disk_health_report_{report_time.strftime('%Y%m%d_%H%M%S')}.txt"
    report_path = os.path.join('/tmp', report_filename)
    report_logger.write_to_file(report_path)
    print(color_text(f"报告已保存到: {report_path}", Colors.CYAN))
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
