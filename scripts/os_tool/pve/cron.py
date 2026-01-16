# coding: utf-8
#-----------------------------
# PVE定时任务管理
#-----------------------------
import sys
import os
import json
import re
import time
import uuid

if sys.platform != 'darwin':
    os.chdir('/www/server/jh-panel')

chdir = os.getcwd()
sys.path.append(chdir + '/class/core')
sys.path.append(chdir + '/class/plugin')

import mw

def prompt(tip, default_choice=""):
    print(f"\033[1;32m?\033[0m \033[1m{tip}\033[0m", end="")
    choice = input()
    return choice if choice else default_choice

def show_error(tip):
    print(f"\033[1;31m× {tip}\033[0m")

def show_info(tip):
    print(f"\033[1;32m{tip}\033[0m")

def show_banner():
    show_info("===================================================================")
    show_info("             PVE 定时任务管理工具")
    show_info("===================================================================")

class pve_cron_tool:
    def _get_pve_crons(self):
        try:
            crontab_content = mw.execShell('crontab -l')[0]
        except:
            crontab_content = ""
            
        lines = crontab_content.splitlines()
        pve_crons = []
        for line in lines:
            if "# PVE_CRON_JOB:" in line:
                parts = line.split("# PVE_CRON_JOB:", 1)
                cron_part = parts[0].strip()
                comment_part = parts[1].strip()
                
                cron_parts = cron_part.split()
                if len(cron_parts) < 6:
                    continue
                
                cron_expression = " ".join(cron_parts[0:5])
                command = " ".join(cron_parts[5:])
                
                try:
                    meta = json.loads(comment_part)
                    pve_crons.append({
                        "id": meta.get("id"),
                        "name": meta.get("name"),
                        "cron_expression": cron_expression,
                        "command": command,
                        "line": line
                    })
                except json.JSONDecodeError:
                    continue
        return pve_crons
    
    def _write_crontab(self, content):
        mw.writeFile('/tmp/crontab.tmp', content)
        mw.execShell("crontab /tmp/crontab.tmp")
        if os.path.exists('/tmp/crontab.tmp'):
            os.remove('/tmp/crontab.tmp')

    def list_crons(self):
        crons = self._get_pve_crons()
        show_info("\n---------- PVE 定时任务列表 ----------")
        if not crons:
            show_info("没有找到PVE相关的定时任务。")
            return

        print_str = "{:<5} {:<10} {:<25} {:<20} {:<30}".format("编号", "ID", "名称", "Cron表达式", "命令")
        show_info(print_str)
        show_info("-" * 120)
        for i, cron in enumerate(crons):
            # Shorten ID for display
            display_id = cron['id'][:8] if cron['id'] else "N/A"
            print_str = "{:<5} {:<10} {:<25} {:<20} {:<30}".format(
                i + 1,
                display_id, 
                cron['name'], 
                cron['cron_expression'], 
                cron['command']
            )
            print(print_str)
        show_info("-" * 120)
        return crons

    def add_cron(self):
        show_info("\n---------- 添加新的PVE定时任务 ----------")
        name = prompt("请输入任务名称: ")
        if not name:
            show_error("任务名称不能为空。")
            return

        show_info("请选择任务类型:")
        show_info("1. 发送硬件报告")
        show_info("2. 自定义脚本")
        task_choice = prompt("请输入选项 (1-2): ")
        
        command = ''
        if task_choice == '1':
            command = 'python3 ' + chdir + '/scripts/os_tool/pve/monitor__hardware_report.py'
        elif task_choice == '2':
            command = prompt("请输入要执行的脚本或命令: ")
        else:
            show_error("无效选项")
            return

        if not command:
            show_error("命令不能为空。")
            return

        cron_expression = prompt("请输入cron表达式 (例如: '0 0 * * *' 表示每天午夜): ")
        # Basic validation
        if len(cron_expression.split()) < 5:
             show_error("无效的cron表达式格式。")
             return
        
        show_info("\n你将要添加以下任务:")
        show_info(f"  名称: {name}")
        show_info(f"  Cron表达式: {cron_expression}")
        show_info(f"  命令: {command}")
        
        confirm = prompt("确认添加吗? (y/n): ", "n")
        if confirm.lower() == 'y':
            self._add_cron_job(name, cron_expression, command)
            show_info("定时任务添加成功!")
            self.list_crons()
        else:
            show_info("已取消添加。")

    def _add_cron_job(self, name, cron_expression, command):
        job_id = str(uuid.uuid4())
        meta = {"id": job_id, "name": name}
        comment = f"# PVE_CRON_JOB: {json.dumps(meta)}"
        new_line = f"{cron_expression} {command} {comment}"
        
        try:
            crontab_content = mw.execShell('crontab -l')[0]
        except:
            crontab_content = ""

        # Ensure newline at end of existing content if needed
        if crontab_content and not crontab_content.endswith('\n'):
            crontab_content += "\n"
            
        new_crontab_content = crontab_content + new_line + "\n"
        self._write_crontab(new_crontab_content)

    def edit_cron(self):
        crons = self.list_crons()
        if not crons:
            return

        try:
            choice_str = prompt("请选择要编辑的定时任务 (输入编号): ")
            choice = int(choice_str)
            if choice < 1 or choice > len(crons):
                show_error("无效的选项。")
                return

            cron_to_edit = crons[choice - 1]
            
            show_info("正在编辑任务: " + cron_to_edit['name'])
            show_info("输入新值或按回车键保留当前值。")
            
            new_name = prompt(f"新任务名称 (当前: {cron_to_edit['name']}) [回车保留]: ") or cron_to_edit['name']
            new_cron_expression = prompt(f"新cron表达式 (当前: {cron_to_edit['cron_expression']}) [回车保留]: ") or cron_to_edit['cron_expression']
            new_command = prompt(f"新命令 (当前: {cron_to_edit['command']}) [回车保留]: ") or cron_to_edit['command']

            show_info("\n你将要更新任务为:")
            show_info(f"  名称: {new_name}")
            show_info(f"  Cron表达式: {new_cron_expression}")
            show_info(f"  命令: {new_command}")

            confirm = prompt("确认修改吗? (y/n): ", "n")
            if confirm.lower() != 'y':
                show_info("已取消修改。")
                return
            
            new_meta = {"id": cron_to_edit["id"], "name": new_name}
            new_comment = f"# PVE_CRON_JOB: {json.dumps(new_meta)}"
            new_line = f"{new_cron_expression} {new_command} {new_comment}"
            
            try:
                crontab_content = mw.execShell('crontab -l')[0]
            except:
                crontab_content = ""
            lines = crontab_content.splitlines()
            
            new_lines = []
            for line in lines:
                if line == cron_to_edit["line"]:
                    new_lines.append(new_line)
                else:
                    new_lines.append(line)
            
            new_crontab_content = "\n".join(new_lines) + "\n"
            self._write_crontab(new_crontab_content)
            
            show_info("定时任务编辑成功。")
            self.list_crons()

        except ValueError:
            show_error("无效的输入，请输入数字。")

    def delete_cron(self):
        crons = self.list_crons()
        if not crons:
            return

        try:
            choice_str = prompt("请选择要删除的定时任务 (输入编号): ")
            choice = int(choice_str)
            if choice < 1 or choice > len(crons):
                show_error("无效的选项。")
                return

            cron_to_delete = crons[choice - 1]
            confirm = prompt(f"你确定要删除任务 '{cron_to_delete['name']}'吗? (y/n): ", "n")
            if confirm.lower() == 'y':
                try:
                    crontab_content = mw.execShell('crontab -l')[0]
                except:
                    crontab_content = ""
                lines = crontab_content.splitlines()
                
                new_lines = []
                for line in lines:
                    if line != cron_to_delete["line"]:
                        new_lines.append(line)
                
                new_crontab_content = "\n".join(new_lines) + "\n"
                self._write_crontab(new_crontab_content)

                show_info("定时任务删除成功。")
                self.list_crons()
            else:
                show_info("已取消删除。")
        except ValueError:
            show_error("无效的输入，请输入数字。")

    def run(self):
        show_banner()
        while True:
            show_info("\n主菜单:")
            show_info("1. 定时任务列表")
            show_info("2. 添加定时任务")
            show_info("3. 编辑定时任务")
            show_info("4. 删除定时任务")
            show_info("0. 退出")
            choice = prompt("请输入你的选择: ")

            if choice == '1':
                self.list_crons()
            elif choice == '2':
                self.add_cron()
            elif choice == '3':
                self.edit_cron()
            elif choice == '4':
                self.delete_cron()
            elif choice == '0':
                break
            else:
                show_error("无效的选择，请重新输入。")


if __name__ == "__main__":
    tool = pve_cron_tool()
    if len(sys.argv) > 1:
        if sys.argv[1] == 'list':
            tool.list_crons()
        elif sys.argv[1] == 'add':
            tool.add_cron()
        elif sys.argv[1] == 'edit':
            tool.edit_cron()
        elif sys.argv[1] == 'delete':
            tool.delete_cron()
    else:
        tool.run()