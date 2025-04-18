# coding: utf-8
#-----------------------------
# 修复网站代理协议配置
#-----------------------------

import sys
import os
import json
import re

if sys.platform != 'darwin':
    os.chdir('/www/server/jh-panel')

chdir = os.getcwd()
sys.path.append(chdir + '/class/core')

import mw
import db
import time
import system_api
import site_api

systemApi = system_api.system_api()
siteApi = site_api.site_api()

class otherTools:
    def configZenlayerWebsiteGetRealIp(self, site_name):
        nginx_conf_dir = mw.getWebConfDir() + '/nginx/vhost'
        proxy_protocol_config = '''
    #REAL-IP-START
    set_real_ip_from 0.0.0.0/0; # 允许所有 IP 使用 proxy protocol
    real_ip_header proxy_protocol;  # 从代理协议头中提取客户端真实 IP

    set $final_remote_addr $remote_addr;
    set $final_proxy_add_x_forwarded_for $proxy_add_x_forwarded_for;
    if ($proxy_protocol_addr) {
        set $final_remote_addr $proxy_protocol_addr;
        set $final_proxy_add_x_forwarded_for $proxy_protocol_addr;
    }
    #REAL-IP-END
        '''
        location_config = '''
        # 获取真实ip
        proxy_set_header X-Real-IP $final_remote_addr;
        proxy_set_header X-Forwarded-For $final_proxy_add_x_forwarded_for;
        proxy_set_header REMOTE-HOST $final_remote_addr;
        '''

        # 获取网站列表
        siteList = []
        if site_name == "all":
            siteInfo = systemApi.getSiteInfo()
            for site in siteInfo.get("site_list", []):
                siteList.append(site.get("name", ""))
        else:
            siteList = site_name.split(",")
        
        for site in siteList:
            conf_file = os.path.join(nginx_conf_dir, f"{site}.conf")
            if not os.path.exists(conf_file):
                print(f"|- 配置文件 {conf_file} 不存在")
                return False

            print(f"|- 开始配置 {site} 的代理协议")

            with open(conf_file, 'r') as f:
                content = f.read()

            # 检查是否已存在 REAL-IP 配置
            if '#REAL-IP-START' in content:
                print(f"|- {site} 已配置代理协议,跳过")
                continue

            # 删除已存在的配置
            content = re.sub(r'listen\s+80\s*(?:proxy_protocol)?;', 'listen 80 proxy_protocol;', content)
            content = re.sub(r'listen\s+443\s+ssl\s+http2\s*(?:proxy_protocol)?;', 'listen 443 ssl http2 proxy_protocol;', content)
            content = re.sub(r'listen\s+\[::\]:443\s+ssl\s+http2\s*(?:proxy_protocol)?;', 'listen [::]:443 ssl http2 proxy_protocol;', content)
            content = re.sub(r'listen\s+\[::\]:80\s*(?:proxy_protocol)?;', 'listen [::]:80 proxy_protocol;', content)
            content = re.sub(r'^\s*proxy_set_header\s+X-Real-IP\s+\$[^;]+;.*$', '', content, flags=re.MULTILINE)
            content = re.sub(r'^\s*proxy_set_header\s+X-Forwarded-For\s+\$[^;]+;.*$', '', content, flags=re.MULTILINE)
            content = re.sub(r'^\s*proxy_set_header\s+REMOTE-HOST\s+\$[^;]+;.*$', '', content, flags=re.MULTILINE)

            # 在server块中添加配置
            server_block_pattern = r'(server\s*\{[^}]*\})'
            server_blocks = re.findall(server_block_pattern, content, re.DOTALL)
            
            for server_block in server_blocks:
                if 'root' in server_block:
                    # 在 root 指令后添加 REAL-IP 配置
                    new_server_block = re.sub(r'(root\s+[^;]+;)', r'\1\n' + proxy_protocol_config, server_block)
                    content = content.replace(server_block, new_server_block)

            # 在location /块中添加配置
            location_pattern = r'(location\s+/\s*\{[^}]*\})'
            locations = re.findall(location_pattern, content, re.DOTALL)
            
            for location in locations:
                # 获取最后一个 } 的缩进
                last_brace_indent = re.search(r'(\s*)\}$', location).group(1)
                # 在最后一个 } 前添加配置,保持缩进
                new_location = re.sub(r'(\s*)\}$', location_config + r'\1}', location)
                content = content.replace(location, new_location)

            with open(conf_file, 'w') as f:
                f.write(content)

            print(f"|- 已成功配置 {site_name} 的代理协议")
        return True

if __name__ == "__main__":
    other = otherTools()
    if len(sys.argv) < 2:
        print("请指定操作类型：")
        print("1. 配置单个网站：python3 other.py config_zenlayer_website_get_real_ip 域名")
        print("2. 配置所有网站：python3 other.py config_zenlayer_website_get_real_ip all")
        sys.exit(1)

    action = sys.argv[1]
    if action == "config_zenlayer_website_get_real_ip":
        if len(sys.argv) < 3:
            print("请指定域名")
            sys.exit(1)
        site_name = sys.argv[2]
        other.configZenlayerWebsiteGetRealIp(site_name)
    else:
        print("无效的操作类型") 