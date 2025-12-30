#!/usr/bin/env python3
"""
PVE硬盘健康监控脚本 - 修复对齐问题
"""

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

def parse_sata_attributes(output):
    """解析SATA设备的SMART属性"""
    attrs = {}
    lines = output.strip().split('\n')
    
    for line in lines:
        if re.match(r'^\s*\d+', line):
            parts = re.split(r'\s+', line.strip())
            if len(parts) >= 10:
                attr_id = parts[0]
                # 有些属性名可能包含空格，需要特殊处理
                attr_name = parts[1]
                if len(parts) > 10:
                    # 合并多余的字段作为属性名
                    for i in range(2, len(parts)-9):
                        attr_name += " " + parts[i]
                
                attrs[attr_id] = {
                    'name': attr_name,
                    'value': int(parts[-6]) if parts[-6].isdigit() else 0,
                    'worst': int(parts[-5]) if parts[-5].isdigit() else 0,
                    'threshold': int(parts[-4]) if parts[-4].isdigit() else 0,
                    'raw': parts[-1] if parts[-1] else '0',
                    'type': parts[-3] if len(parts) > 7 else '',
                    'when_failed': parts[-2] if len(parts) > 8 else '-'
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
    def __init__(self, device):
        self.device = device
        self.name = device.split('/')[-1]
        self.is_nvme = 'nvme' in device
        self.info = {}
        self.issues = []
        self.status = "正常"
        self.attributes = []
        
    def get_basic_info(self):
        """获取设备基本信息"""
        cmd = f"smartctl -i {self.device}"
        output, _, _ = run_command(cmd)
        
        info = {
            'model': '未知',
            'serial': '未知',
            'firmware': '未知',
            'capacity': '未知',
            'type': 'SATA'
        }
        
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
        cmd = f"smartctl -H {self.device}"
        output, _, returncode = run_command(cmd)
        
        if 'PASSED' in output or 'OK' in output:
            return "通过"
        else:
            return "失败"
    
    def check_sata_disk(self):
        """检查SATA设备"""
        cmd = f"smartctl -A {self.device}"
        output, _, _ = run_command(cmd)
        attrs = parse_sata_attributes(output)
        
        print(f"    {color_text('SATA详细参数:', Colors.CYAN)}")
        print(f"    {pad_string('参数名', 24)} {pad_string('当前值', 8)} {pad_string('阈值', 8)} {pad_string('原始值', 12)} 状态")
        print(f"    {'-' * 70}")
        
        for attr_id, attr_data in attrs.items():
            if attr_id in SATA_PARAMS:
                cn_name, en_name = SATA_PARAMS[attr_id]
                
                value = attr_data['value']
                threshold = attr_data['threshold']
                raw = attr_data['raw']
                when_failed = attr_data['when_failed']
                
                # 判断状态
                status = "正常"
                status_color = Colors.GREEN
                
                # 特定参数的特殊判断
                if attr_id == "5":  # 重新分配扇区计数
                    if int(raw) > 0:
                        status = "异常"
                        status_color = Colors.RED
                        self.issues.append(f"坏块:{raw}")
                        self.status = "异常"
                    elif when_failed != '-':
                        status = "警告"
                        status_color = Colors.ORANGE
                        if self.status == "正常":
                            self.status = "警告"
                
                elif attr_id == "187":  # 报告不可纠正错误
                    if int(raw) > 0:
                        status = "异常"
                        status_color = Colors.RED
                        self.issues.append(f"不可纠正错误:{raw}")
                        self.status = "异常"
                
                elif attr_id == "194":  # 温度
                    temp = int(raw) if raw.isdigit() else 0
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
                    life = int(raw) if raw.isdigit() else 100
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
                param_display = pad_string(cn_name, 24)
                value_display = pad_string(str(value), 8)
                threshold_display = pad_string(str(threshold), 8)
                raw_display = pad_string(raw, 12)
                
                print(f"    {param_display} {value_display} {threshold_display} {raw_display} {color_text(status, status_color)}")
    
    def check_nvme_disk(self):
        """检查NVMe设备"""
        cmd = f"smartctl -a {self.device}"
        output, _, _ = run_command(cmd)
        info = parse_nvme_info(output)
        
        print(f"    {color_text('NVMe详细参数:', Colors.CYAN)}")
        print(f"    {pad_string('参数名', 24)} {pad_string('值', 20)} 状态")
        print(f"    {'-' * 60}")
        
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
                param_display = pad_string(cn_name, 24)
                value_display = pad_string(display_value, 20)
                
                print(f"    {param_display} {value_display} {color_text(status, status_color)}")
    
    def check(self):
        """执行完整的设备检查"""
        print(f"\n{color_text('=' * 60, Colors.YELLOW)}")
        print(f"{color_text('设备:', Colors.CYAN)} {self.device}")
        
        # 获取基本信息
        self.info = self.get_basic_info()
        print(f"{color_text('型号:', Colors.CYAN)} {self.info['model']}")
        print(f"{color_text('序列号:', Colors.CYAN)} {self.info['serial']}")
        print(f"{color_text('容量:', Colors.CYAN)} {self.info['capacity']}")
        print(f"{color_text('类型:', Colors.CYAN)} {self.info['type']}")
        
        # 检查健康状态
        health = self.check_health()
        health_color = Colors.GREEN if health == "通过" else Colors.RED
        print(f"{color_text('健康状态:', Colors.CYAN)} {color_text(health, health_color)}")
        
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
        
        print(f"{color_text('=' * 60, Colors.YELLOW)}")
        
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
    print(f"{color_text('PVE硬盘健康检查报告', Colors.YELLOW)}")
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 检测所有硬盘
    output, _, _ = run_command("smartctl --scan")
    devices = []
    
    if output.strip():
        for line in output.strip().split('\n'):
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
    
    if not devices:
        print(color_text("错误：未检测到任何硬盘设备！", Colors.RED))
        sys.exit(1)
    
    # 检查每个设备
    results = []
    for device in devices:
        checker = DiskChecker(device)
        result = checker.check()
        if result:
            results.append(result)
    
    # 生成汇总报告
    print(f"\n{color_text('=' * 60, Colors.YELLOW)}")
    print(f"{color_text('硬盘健康检查汇总报告', Colors.CYAN)}")
    print(f"{color_text('=' * 60, Colors.YELLOW)}")
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    total = len(results)
    healthy = sum(1 for r in results if r['status'] == '正常')
    warning = sum(1 for r in results if r['status'] == '警告')
    critical = sum(1 for r in results if r['status'] == '异常')
    
    print(f"检测设备: {total}")
    print(f"{color_text('健康设备:', Colors.GREEN)} {healthy}")
    print(f"{color_text('警告设备:', Colors.ORANGE)} {warning}")
    print(f"{color_text('异常设备:', Colors.RED)} {critical}")
    
    # 设备状态表
    if results:
        print(f"\n{color_text('设备状态表:', Colors.CYAN)}")
        print(f"{'-' * 80}")
        header = f"| {pad_string('设备', 8)} | {pad_string('型号', 20)} | {pad_string('类型', 6)} | {pad_string('状态', 8)} | {pad_string('问题摘要', 30)} |"
        print(header)
        print(f"{'-' * 80}")
        
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
            
            print(f"| {pad_string(device_short, 8)} | {pad_string(model_short, 20)} | "
                  f"{pad_string(r['type'], 6)} | {color_text(pad_string(r['status'], 8), status_color)} | "
                  f"{pad_string(issues_short, 30)} |")
        
        print(f"{'-' * 80}")
    
    # 给出建议
    if critical > 0:
        print(f"\n{color_text('⚠️ 警告：发现异常设备，请立即备份数据！', Colors.RED)}")
        sys.exit(1)
    elif warning > 0:
        print(f"\n{color_text('⚠️ 注意：发现警告设备，请保持关注。', Colors.ORANGE)}")
        sys.exit(0)
    else:
        print(f"\n{color_text('✓ 所有硬盘状态正常。', Colors.GREEN)}")
        sys.exit(0)

if __name__ == "__main__":
    main()