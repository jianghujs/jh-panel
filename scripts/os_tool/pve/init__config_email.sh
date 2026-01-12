#!/bin/bash
#
# PVE 邮件发送配置脚本
# 用于配置 Postfix SMTP 中继和 PVE 邮箱设置
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置文件路径
POSTFIX_MAIN_CF="/etc/postfix/main.cf"
POSTFIX_SASL_PASSWD="/etc/postfix/sasl_passwd"
POSTFIX_SASL_PASSWD_DB="/etc/postfix/sasl_passwd.db"

echo -e "${CYAN}================================${NC}"
echo -e "${CYAN}PVE 邮件发送配置工具${NC}"
echo -e "${CYAN}================================${NC}"
echo ""

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}✗ 请使用 root 权限运行此脚本${NC}"
    exit 1
fi

# 检查是否在PVE系统上
if ! command -v pveum &> /dev/null; then
    echo -e "${YELLOW}⚠ 警告: 未检测到 PVE 环境，将仅配置 Postfix${NC}"
    PVE_AVAILABLE=false
else
    PVE_AVAILABLE=true
    echo -e "${GREEN}✓ 检测到 PVE 环境${NC}"
fi
echo ""

# 检查Postfix是否安装
if ! command -v postfix &> /dev/null; then
    echo -e "${YELLOW}Postfix 未安装，正在安装...${NC}"
    apt-get update
    apt-get install -y postfix mailutils
    echo -e "${GREEN}✓ Postfix 安装完成${NC}"
    echo ""
fi

# 显示当前配置
echo -e "${CYAN}当前配置状态:${NC}"
echo "----------------------------------------"
if [ -f "$POSTFIX_MAIN_CF" ]; then
    CURRENT_RELAYHOST=$(postconf -h relayhost 2>/dev/null || echo "")
    CURRENT_MYHOSTNAME=$(postconf -h myhostname 2>/dev/null || echo "")
    CURRENT_SMTPUTF8=$(postconf -h smtputf8_enable 2>/dev/null || echo "")
    echo "  Postfix relayhost: ${CURRENT_RELAYHOST:-未配置}"
    echo "  Postfix myhostname: ${CURRENT_MYHOSTNAME:-未配置}"
    echo "  Postfix smtputf8_enable: ${CURRENT_SMTPUTF8:-未配置}"
else
    echo "  Postfix 配置文件不存在"
fi

if [ "$PVE_AVAILABLE" = true ]; then
    PVE_USER_EMAIL=$(pveum user list --output-format json 2>/dev/null | grep -A 5 '"userid":"root@pam"' | grep '"email"' | cut -d'"' -f4 || echo "")
    if [ -n "$PVE_USER_EMAIL" ]; then
        echo "  PVE root@pam 邮箱: $PVE_USER_EMAIL"
    else
        echo "  PVE root@pam 邮箱: 未配置"
    fi
    
    if [ -f /etc/pve/datacenter.cfg ]; then
        DC_EMAIL=$(grep -E "^email:" /etc/pve/datacenter.cfg 2>/dev/null | cut -d' ' -f2 || echo "")
        if [ -n "$DC_EMAIL" ]; then
            echo "  PVE Datacenter 邮箱: $DC_EMAIL"
        else
            echo "  PVE Datacenter 邮箱: 未配置"
        fi
    fi
fi
echo ""

# 主菜单
show_menu() {
    echo -e "${CYAN}请选择配置选项:${NC}"
    echo "  1) 一键配置完整邮件系统 (推荐)"
    echo "  2) 配置 SMTP 中继服务器 (relayhost)"
    echo "  3) 配置 SMTP 认证 (用户名/密码)"
    echo "  4) 配置 PVE root@pam 用户邮箱"
    echo "  5) 配置 PVE Datacenter 邮箱"
    echo "  6) 查看当前配置"
    echo "  7) 测试邮件发送"
    echo "  8) 移除 SMTP 中继配置"
    echo "  9) 退出"
    echo ""
    read -p "请选择 [1-9]: " choice
}

# 一键配置向导
configure_email_wizard() {
    echo ""
    echo -e "${CYAN}================================${NC}"
    echo -e "${CYAN}PVE 邮件配置向导${NC}"
    echo -e "${CYAN}================================${NC}"
    echo ""
    echo "此向导将引导您完成以下配置："
    echo "  1. SMTP 邮件发送服务配置（可选）"
    echo "  2. PVE root@pam 用户接收邮箱（必需）"
    echo "  3. PVE Datacenter 邮箱（可选，作为备选）"
    echo ""
    read -p "按 Enter 开始配置..."
    echo ""
    
    # 步骤1: 配置SMTP服务
    echo -e "${CYAN}[步骤 1/3] 配置 SMTP 邮件发送服务${NC}"
    echo "----------------------------------------"
    echo "SMTP 服务用于实际发送邮件。"
    echo "如果您的服务器可以直接发送邮件，可以跳过此步骤。"
    echo "如果需要使用外部SMTP服务器（如Gmail、QQ邮箱等），请配置此项。"
    echo ""
    
    CURRENT_RELAYHOST=$(postconf -h relayhost 2>/dev/null || echo "")
    if [ -n "$CURRENT_RELAYHOST" ]; then
        echo -e "${YELLOW}当前已配置 SMTP 中继: $CURRENT_RELAYHOST${NC}"
        read -p "是否重新配置 SMTP 服务? [y/N]: " config_smtp
        if [[ ! "$config_smtp" =~ ^[Yy]$ ]]; then
            config_smtp="skip"
        fi
    else
        read -p "是否配置 SMTP 服务? [Y/n]: " config_smtp
        if [[ "$config_smtp" =~ ^[Nn]$ ]]; then
            config_smtp="skip"
        fi
    fi
    
    if [ "$config_smtp" != "skip" ]; then
        # 配置relayhost
        echo ""
        echo "常用SMTP服务器示例:"
        echo "  - Gmail: [smtp.gmail.com]:587"
        echo "  - Outlook: [smtp-mail.outlook.com]:587"
        echo "  - QQ邮箱: [smtp.qq.com]:587"
        echo "  - 163邮箱: [smtp.163.com]:587"
        echo ""
        
        read -p "请输入 SMTP 服务器地址 (格式: [smtp.example.com]:587): " relayhost
        
        if [ -n "$relayhost" ]; then
            # 备份配置文件
            if [ -f "$POSTFIX_MAIN_CF" ]; then
                cp "$POSTFIX_MAIN_CF" "${POSTFIX_MAIN_CF}.bak.$(date +%Y%m%d_%H%M%S)"
            fi
            
            # 配置relayhost
            if grep -q "^relayhost" "$POSTFIX_MAIN_CF" 2>/dev/null; then
                sed -i "s|^relayhost.*|relayhost = $relayhost|" "$POSTFIX_MAIN_CF"
            else
                echo "relayhost = $relayhost" >> "$POSTFIX_MAIN_CF"
            fi
            
            # 配置TLS支持
            if ! grep -q "^smtp_use_tls" "$POSTFIX_MAIN_CF" 2>/dev/null; then
                echo "smtp_use_tls = yes" >> "$POSTFIX_MAIN_CF"
            fi
            
            if ! grep -q "^smtp_tls_security_level" "$POSTFIX_MAIN_CF" 2>/dev/null; then
                echo "smtp_tls_security_level = encrypt" >> "$POSTFIX_MAIN_CF"
            fi
            
            # 重新加载Postfix
            postfix check
            if [ $? -eq 0 ]; then
                systemctl reload postfix
                echo -e "${GREEN}✓ SMTP 中继服务器配置成功${NC}"
            else
                echo -e "${RED}✗ Postfix 配置检查失败${NC}"
                return 1
            fi
            
            # 配置SMTP认证
            echo ""
            echo "大多数SMTP服务器需要身份验证。"
            echo "注意: 某些邮件服务商需要使用应用专用密码"
            echo "  - Gmail: 需要在Google账号中生成应用专用密码"
            echo "  - QQ邮箱: 需要使用授权码而非登录密码"
            echo ""
            
            read -p "是否配置 SMTP 认证? [Y/n]: " config_auth
            if [[ ! "$config_auth" =~ ^[Nn]$ ]]; then
                read -p "请输入 SMTP 用户名/邮箱: " smtp_user
                if [ -n "$smtp_user" ]; then
                    read -sp "请输入 SMTP 密码/授权码: " smtp_pass
                    echo ""
                    
                    if [ -n "$smtp_pass" ]; then
                        # 创建sasl_passwd文件
                        echo "$relayhost $smtp_user:$smtp_pass" > "$POSTFIX_SASL_PASSWD"
                        chmod 600 "$POSTFIX_SASL_PASSWD"
                        
                        # 生成数据库文件
                        postmap "$POSTFIX_SASL_PASSWD"
                        chmod 600 "$POSTFIX_SASL_PASSWD_DB"
                        
                        # 配置SASL认证
                        if ! grep -q "^smtp_sasl_auth_enable" "$POSTFIX_MAIN_CF" 2>/dev/null; then
                            echo "smtp_sasl_auth_enable = yes" >> "$POSTFIX_MAIN_CF"
                        else
                            sed -i 's/^smtp_sasl_auth_enable.*/smtp_sasl_auth_enable = yes/' "$POSTFIX_MAIN_CF"
                        fi
                        
                        if ! grep -q "^smtp_sasl_password_maps" "$POSTFIX_MAIN_CF" 2>/dev/null; then
                            echo "smtp_sasl_password_maps = hash:$POSTFIX_SASL_PASSWD" >> "$POSTFIX_MAIN_CF"
                        else
                            sed -i "s|^smtp_sasl_password_maps.*|smtp_sasl_password_maps = hash:$POSTFIX_SASL_PASSWD|" "$POSTFIX_MAIN_CF"
                        fi
                        
                        if ! grep -q "^smtp_sasl_security_options" "$POSTFIX_MAIN_CF" 2>/dev/null; then
                            echo "smtp_sasl_security_options = noanonymous" >> "$POSTFIX_MAIN_CF"
                        fi
                        
                        if ! grep -q "^smtp_sasl_tls_security_options" "$POSTFIX_MAIN_CF" 2>/dev/null; then
                            echo "smtp_sasl_tls_security_options = noanonymous" >> "$POSTFIX_MAIN_CF"
                        fi
                        
                        # 重新加载Postfix
                        postfix check
                        if [ $? -eq 0 ]; then
                            systemctl reload postfix
                            echo -e "${GREEN}✓ SMTP 认证配置成功${NC}"
                        else
                            echo -e "${RED}✗ Postfix 配置检查失败${NC}"
                            return 1
                        fi
                    fi
                fi
            fi
        fi
    else
        echo -e "${YELLOW}跳过 SMTP 服务配置${NC}"
    fi
    
    echo ""
    echo -e "${CYAN}[步骤 2/3] 配置 PVE root@pam 用户接收邮箱${NC}"
    echo "----------------------------------------"
    
    if [ "$PVE_AVAILABLE" != true ]; then
        echo -e "${YELLOW}⚠ PVE 环境不可用，跳过此步骤${NC}"
    else
        echo "此邮箱用于接收 PVE 系统通知和告警。"
        echo ""
        
        CURRENT_EMAIL=$(pveum user list --output-format json 2>/dev/null | grep -A 5 '"userid":"root@pam"' | grep '"email"' | cut -d'"' -f4 || echo "")
        if [ -n "$CURRENT_EMAIL" ]; then
            echo -e "${YELLOW}当前邮箱: $CURRENT_EMAIL${NC}"
            read -p "是否修改? [y/N]: " modify
            if [[ "$modify" =~ ^[Yy]$ ]]; then
                read -p "请输入新的邮箱地址: " email
            else
                email="$CURRENT_EMAIL"
            fi
        else
            read -p "请输入邮箱地址: " email
        fi
        
        if [ -n "$email" ]; then
            # 验证邮箱格式
            if [[ ! "$email" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
                echo -e "${YELLOW}⚠ 邮箱格式可能不正确，但将继续配置${NC}"
            fi
            
            if pveum user modify root@pam -email "$email" 2>/dev/null; then
                echo -e "${GREEN}✓ PVE root@pam 用户邮箱配置成功: $email${NC}"
            else
                echo -e "${RED}✗ 配置失败，请检查权限和邮箱格式${NC}"
                return 1
            fi
        else
            echo -e "${YELLOW}⚠ 未配置邮箱，将使用系统默认${NC}"
        fi
    fi
    
    echo ""
    echo -e "${CYAN}[步骤 3/3] 配置 PVE Datacenter 邮箱（可选）${NC}"
    echo "----------------------------------------"
    
    if [ "$PVE_AVAILABLE" != true ]; then
        echo -e "${YELLOW}⚠ PVE 环境不可用，跳过此步骤${NC}"
    else
        echo "Datacenter 邮箱作为备选邮箱，当用户未配置邮箱时使用。"
        echo "这是可选的，您可以跳过此步骤。"
        echo ""
        
        DC_CFG="/etc/pve/datacenter.cfg"
        if [ -f "$DC_CFG" ]; then
            CURRENT_DC_EMAIL=$(grep -E "^email:" "$DC_CFG" 2>/dev/null | cut -d' ' -f2 || echo "")
            if [ -n "$CURRENT_DC_EMAIL" ]; then
                echo -e "${YELLOW}当前 Datacenter 邮箱: $CURRENT_DC_EMAIL${NC}"
                read -p "是否配置/修改 Datacenter 邮箱? [y/N]: " config_dc
            else
                read -p "是否配置 Datacenter 邮箱? [y/N]: " config_dc
            fi
        else
            read -p "是否配置 Datacenter 邮箱? [y/N]: " config_dc
        fi
        
        if [[ "$config_dc" =~ ^[Yy]$ ]]; then
            read -p "请输入 Datacenter 邮箱地址: " dc_email
            
            if [ -n "$dc_email" ]; then
                # 验证邮箱格式
                if [[ ! "$dc_email" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
                    echo -e "${YELLOW}⚠ 邮箱格式可能不正确，但将继续配置${NC}"
                fi
                
                # 备份配置文件
                if [ -f "$DC_CFG" ]; then
                    cp "$DC_CFG" "${DC_CFG}.bak.$(date +%Y%m%d_%H%M%S)"
                fi
                
                # 更新或添加邮箱配置
                if grep -q "^email:" "$DC_CFG" 2>/dev/null; then
                    sed -i "s|^email:.*|email: $dc_email|" "$DC_CFG"
                else
                    echo "email: $dc_email" >> "$DC_CFG"
                fi
                
                echo -e "${GREEN}✓ PVE Datacenter 邮箱配置成功: $dc_email${NC}"
            else
                echo -e "${YELLOW}⚠ 未输入邮箱，跳过 Datacenter 邮箱配置${NC}"
            fi
        else
            echo -e "${YELLOW}跳过 Datacenter 邮箱配置${NC}"
        fi
    fi
    
    echo ""
    echo -e "${CYAN}================================${NC}"
    echo -e "${GREEN}配置完成！${NC}"
    echo -e "${CYAN}================================${NC}"
    echo ""
    echo "配置总结:"
    if [ -n "$(postconf -h relayhost 2>/dev/null)" ]; then
        echo -e "  ${GREEN}✓${NC} SMTP 服务: 已配置"
    else
        echo -e "  ${YELLOW}○${NC} SMTP 服务: 未配置"
    fi
    
    if [ "$PVE_AVAILABLE" = true ]; then
        PVE_USER_EMAIL=$(pveum user list --output-format json 2>/dev/null | grep -A 5 '"userid":"root@pam"' | grep '"email"' | cut -d'"' -f4 || echo "")
        if [ -n "$PVE_USER_EMAIL" ]; then
            echo -e "  ${GREEN}✓${NC} root@pam 邮箱: $PVE_USER_EMAIL"
        else
            echo -e "  ${YELLOW}○${NC} root@pam 邮箱: 未配置"
        fi
        
        if [ -f /etc/pve/datacenter.cfg ]; then
            DC_EMAIL=$(grep -E "^email:" /etc/pve/datacenter.cfg 2>/dev/null | cut -d' ' -f2 || echo "")
            if [ -n "$DC_EMAIL" ]; then
                echo -e "  ${GREEN}✓${NC} Datacenter 邮箱: $DC_EMAIL"
            else
                echo -e "  ${YELLOW}○${NC} Datacenter 邮箱: 未配置"
            fi
        fi
    fi
    
    echo ""
    read -p "是否发送测试邮件? [Y/n]: " send_test
    if [[ ! "$send_test" =~ ^[Nn]$ ]]; then
        if [ "$PVE_AVAILABLE" = true ]; then
            TEST_EMAIL=$(pveum user list --output-format json 2>/dev/null | grep -A 5 '"userid":"root@pam"' | grep '"email"' | cut -d'"' -f4 || echo "")
            if [ -z "$TEST_EMAIL" ] && [ -f /etc/pve/datacenter.cfg ]; then
                TEST_EMAIL=$(grep -E "^email:" /etc/pve/datacenter.cfg 2>/dev/null | cut -d' ' -f2 || echo "")
            fi
        fi
        
        if [ -n "$TEST_EMAIL" ]; then
            echo ""
            echo "正在发送测试邮件到: $TEST_EMAIL"
            HOSTNAME=$(hostname)
            TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
            
            if echo -e "这是一封来自 $HOSTNAME 的测试邮件。\n\n发送时间: $TIMESTAMP\n\n如果您收到这封邮件，说明邮件配置成功！" | \
               mail -s "[测试] PVE 邮件配置测试 - $HOSTNAME" "$TEST_EMAIL" 2>&1; then
                echo -e "${GREEN}✓ 测试邮件已发送${NC}"
                echo "请检查您的邮箱（包括垃圾邮件文件夹）"
            else
                echo -e "${RED}✗ 测试邮件发送失败${NC}"
                echo "请检查邮件日志: tail -f /var/log/mail.log"
            fi
        else
            echo -e "${YELLOW}⚠ 未找到配置的邮箱地址，无法发送测试邮件${NC}"
        fi
    fi
    echo ""
}

# 配置SMTP中继服务器
configure_relayhost() {
    echo ""
    echo -e "${CYAN}配置 SMTP 中继服务器${NC}"
    echo "----------------------------------------"
    echo "常用SMTP服务器示例:"
    echo "  - Gmail: [smtp.gmail.com]:587"
    echo "  - Outlook: [smtp-mail.outlook.com]:587"
    echo "  - QQ邮箱: [smtp.qq.com]:587"
    echo "  - 163邮箱: [smtp.163.com]:587"
    echo ""
    
    CURRENT_RELAYHOST=$(postconf -h relayhost 2>/dev/null || echo "")
    if [ -n "$CURRENT_RELAYHOST" ]; then
        echo -e "${YELLOW}当前 relayhost: $CURRENT_RELAYHOST${NC}"
        read -p "是否修改? [y/N]: " modify
        if [[ ! "$modify" =~ ^[Yy]$ ]]; then
            return
        fi
    fi
    
    read -p "请输入 SMTP 服务器地址 (格式: [smtp.example.com]:587): " relayhost
    
    if [ -z "$relayhost" ]; then
        echo -e "${RED}✗ 未输入服务器地址${NC}"
        return
    fi
    
    # 备份配置文件
    if [ -f "$POSTFIX_MAIN_CF" ]; then
        cp "$POSTFIX_MAIN_CF" "${POSTFIX_MAIN_CF}.bak.$(date +%Y%m%d_%H%M%S)"
    fi
    
    # 配置relayhost
    if grep -q "^relayhost" "$POSTFIX_MAIN_CF" 2>/dev/null; then
        sed -i "s|^relayhost.*|relayhost = $relayhost|" "$POSTFIX_MAIN_CF"
    else
        echo "relayhost = $relayhost" >> "$POSTFIX_MAIN_CF"
    fi
    
    # 配置TLS支持
    if ! grep -q "^smtp_use_tls" "$POSTFIX_MAIN_CF" 2>/dev/null; then
        echo "smtp_use_tls = yes" >> "$POSTFIX_MAIN_CF"
    fi
    
    if ! grep -q "^smtp_tls_security_level" "$POSTFIX_MAIN_CF" 2>/dev/null; then
        echo "smtp_tls_security_level = encrypt" >> "$POSTFIX_MAIN_CF"
    fi
    
    # 重新加载Postfix
    postfix check
    if [ $? -eq 0 ]; then
        systemctl reload postfix
        echo -e "${GREEN}✓ SMTP 中继服务器配置成功${NC}"
        echo -e "${GREEN}✓ relayhost = $relayhost${NC}"
    else
        echo -e "${RED}✗ Postfix 配置检查失败，请检查配置${NC}"
        return 1
    fi
}

# 配置SMTP认证
configure_smtp_auth() {
    echo ""
    echo -e "${CYAN}配置 SMTP 认证${NC}"
    echo "----------------------------------------"
    echo "注意: 某些邮件服务商需要使用应用专用密码"
    echo "  - Gmail: 需要在Google账号中生成应用专用密码"
    echo "  - QQ邮箱: 需要使用授权码而非登录密码"
    echo ""
    
    if [ ! -f "$POSTFIX_MAIN_CF" ]; then
        echo -e "${RED}✗ Postfix 配置文件不存在，请先配置 relayhost${NC}"
        return
    fi
    
    CURRENT_RELAYHOST=$(postconf -h relayhost 2>/dev/null || echo "")
    if [ -z "$CURRENT_RELAYHOST" ]; then
        echo -e "${RED}✗ 请先配置 relayhost${NC}"
        return
    fi
    
    # 提取SMTP服务器地址（去掉端口）
    SMTP_SERVER=$(echo "$CURRENT_RELAYHOST" | sed 's/\[\(.*\)\]:.*/\1/')
    
    read -p "请输入 SMTP 用户名/邮箱: " smtp_user
    if [ -z "$smtp_user" ]; then
        echo -e "${RED}✗ 未输入用户名${NC}"
        return
    fi
    
    read -sp "请输入 SMTP 密码/授权码: " smtp_pass
    echo ""
    if [ -z "$smtp_pass" ]; then
        echo -e "${RED}✗ 未输入密码${NC}"
        return
    fi
    
    # 创建sasl_passwd文件
    echo "$CURRENT_RELAYHOST $smtp_user:$smtp_pass" > "$POSTFIX_SASL_PASSWD"
    chmod 600 "$POSTFIX_SASL_PASSWD"
    
    # 生成数据库文件
    postmap "$POSTFIX_SASL_PASSWD"
    chmod 600 "$POSTFIX_SASL_PASSWD_DB"
    
    # 备份并更新main.cf
    cp "$POSTFIX_MAIN_CF" "${POSTFIX_MAIN_CF}.bak.$(date +%Y%m%d_%H%M%S)"
    
    # 配置SASL认证
    if ! grep -q "^smtp_sasl_auth_enable" "$POSTFIX_MAIN_CF" 2>/dev/null; then
        echo "smtp_sasl_auth_enable = yes" >> "$POSTFIX_MAIN_CF"
    else
        sed -i 's/^smtp_sasl_auth_enable.*/smtp_sasl_auth_enable = yes/' "$POSTFIX_MAIN_CF"
    fi
    
    if ! grep -q "^smtp_sasl_password_maps" "$POSTFIX_MAIN_CF" 2>/dev/null; then
        echo "smtp_sasl_password_maps = hash:$POSTFIX_SASL_PASSWD" >> "$POSTFIX_MAIN_CF"
    else
        sed -i "s|^smtp_sasl_password_maps.*|smtp_sasl_password_maps = hash:$POSTFIX_SASL_PASSWD|" "$POSTFIX_MAIN_CF"
    fi
    
    if ! grep -q "^smtp_sasl_security_options" "$POSTFIX_MAIN_CF" 2>/dev/null; then
        echo "smtp_sasl_security_options = noanonymous" >> "$POSTFIX_MAIN_CF"
    fi
    
    if ! grep -q "^smtp_sasl_tls_security_options" "$POSTFIX_MAIN_CF" 2>/dev/null; then
        echo "smtp_sasl_tls_security_options = noanonymous" >> "$POSTFIX_MAIN_CF"
    fi
    
    # 重新加载Postfix
    postfix check
    if [ $? -eq 0 ]; then
        systemctl reload postfix
        echo -e "${GREEN}✓ SMTP 认证配置成功${NC}"
        echo -e "${GREEN}✓ 用户名: $smtp_user${NC}"
    else
        echo -e "${RED}✗ Postfix 配置检查失败，请检查配置${NC}"
        return 1
    fi
}

# 配置PVE用户邮箱
configure_pve_user_email() {
    if [ "$PVE_AVAILABLE" != true ]; then
        echo -e "${RED}✗ PVE 环境不可用${NC}"
        return
    fi
    
    echo ""
    echo -e "${CYAN}配置 PVE root@pam 用户邮箱${NC}"
    echo "----------------------------------------"
    
    CURRENT_EMAIL=$(pveum user list --output-format json 2>/dev/null | grep -A 5 '"userid":"root@pam"' | grep '"email"' | cut -d'"' -f4 || echo "")
    if [ -n "$CURRENT_EMAIL" ]; then
        echo -e "${YELLOW}当前邮箱: $CURRENT_EMAIL${NC}"
        read -p "是否修改? [y/N]: " modify
        if [[ ! "$modify" =~ ^[Yy]$ ]]; then
            return
        fi
    fi
    
    read -p "请输入邮箱地址: " email
    
    if [ -z "$email" ]; then
        echo -e "${RED}✗ 未输入邮箱地址${NC}"
        return
    fi
    
    # 验证邮箱格式
    if [[ ! "$email" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
        echo -e "${YELLOW}⚠ 邮箱格式可能不正确，但将继续配置${NC}"
    fi
    
    if pveum user modify root@pam -email "$email" 2>/dev/null; then
        echo -e "${GREEN}✓ PVE root@pam 用户邮箱配置成功: $email${NC}"
    else
        echo -e "${RED}✗ 配置失败，请检查权限和邮箱格式${NC}"
        return 1
    fi
}

# 配置PVE Datacenter邮箱
configure_pve_datacenter_email() {
    if [ "$PVE_AVAILABLE" != true ]; then
        echo -e "${RED}✗ PVE 环境不可用${NC}"
        return
    fi
    
    echo ""
    echo -e "${CYAN}配置 PVE Datacenter 邮箱${NC}"
    echo "----------------------------------------"
    
    DC_CFG="/etc/pve/datacenter.cfg"
    
    if [ -f "$DC_CFG" ]; then
        CURRENT_EMAIL=$(grep -E "^email:" "$DC_CFG" 2>/dev/null | cut -d' ' -f2 || echo "")
        if [ -n "$CURRENT_EMAIL" ]; then
            echo -e "${YELLOW}当前邮箱: $CURRENT_EMAIL${NC}"
            read -p "是否修改? [y/N]: " modify
            if [[ ! "$modify" =~ ^[Yy]$ ]]; then
                return
            fi
        fi
    fi
    
    read -p "请输入邮箱地址: " email
    
    if [ -z "$email" ]; then
        echo -e "${RED}✗ 未输入邮箱地址${NC}"
        return
    fi
    
    # 验证邮箱格式
    if [[ ! "$email" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
        echo -e "${YELLOW}⚠ 邮箱格式可能不正确，但将继续配置${NC}"
    fi
    
    # 备份配置文件
    if [ -f "$DC_CFG" ]; then
        cp "$DC_CFG" "${DC_CFG}.bak.$(date +%Y%m%d_%H%M%S)"
    fi
    
    # 更新或添加邮箱配置
    if grep -q "^email:" "$DC_CFG" 2>/dev/null; then
        sed -i "s|^email:.*|email: $email|" "$DC_CFG"
    else
        echo "email: $email" >> "$DC_CFG"
    fi
    
    echo -e "${GREEN}✓ PVE Datacenter 邮箱配置成功: $email${NC}"
}

# 查看当前配置
show_current_config() {
    echo ""
    echo -e "${CYAN}当前配置详情:${NC}"
    echo "========================================"
    
    if [ -f "$POSTFIX_MAIN_CF" ]; then
        echo -e "${BLUE}Postfix 配置:${NC}"
        echo "  relayhost: $(postconf -h relayhost 2>/dev/null || echo '未配置')"
        echo "  myhostname: $(postconf -h myhostname 2>/dev/null || echo '未配置')"
        echo "  smtp_use_tls: $(postconf -h smtp_use_tls 2>/dev/null || echo '未配置')"
        echo "  smtp_sasl_auth_enable: $(postconf -h smtp_sasl_auth_enable 2>/dev/null || echo '未配置')"
        echo "  smtputf8_enable: $(postconf -h smtputf8_enable 2>/dev/null || echo '未配置')"
        
        if [ -f "$POSTFIX_SASL_PASSWD" ]; then
            echo "  SMTP认证: 已配置"
            SMTP_USER=$(cut -d' ' -f2 "$POSTFIX_SASL_PASSWD" | cut -d':' -f1)
            echo "  SMTP用户名: $SMTP_USER"
        else
            echo "  SMTP认证: 未配置"
        fi
    else
        echo -e "${RED}Postfix 配置文件不存在${NC}"
    fi
    
    echo ""
    
    if [ "$PVE_AVAILABLE" = true ]; then
        echo -e "${BLUE}PVE 配置:${NC}"
        PVE_USER_EMAIL=$(pveum user list --output-format json 2>/dev/null | grep -A 5 '"userid":"root@pam"' | grep '"email"' | cut -d'"' -f4 || echo "")
        if [ -n "$PVE_USER_EMAIL" ]; then
            echo "  root@pam 邮箱: $PVE_USER_EMAIL"
        else
            echo "  root@pam 邮箱: 未配置"
        fi
        
        if [ -f /etc/pve/datacenter.cfg ]; then
            DC_EMAIL=$(grep -E "^email:" /etc/pve/datacenter.cfg 2>/dev/null | cut -d' ' -f2 || echo "")
            if [ -n "$DC_EMAIL" ]; then
                echo "  Datacenter 邮箱: $DC_EMAIL"
            else
                echo "  Datacenter 邮箱: 未配置"
            fi
        fi
    fi
    
    echo ""
    echo -e "${BLUE}Postfix 服务状态:${NC}"
    if systemctl is-active --quiet postfix; then
        echo -e "  ${GREEN}✓ 运行中${NC}"
    else
        echo -e "  ${RED}✗ 未运行${NC}"
    fi
    echo ""
}

# 测试邮件发送
test_email() {
    echo ""
    echo -e "${CYAN}测试邮件发送${NC}"
    echo "----------------------------------------"
    
    # 获取测试邮箱
    if [ "$PVE_AVAILABLE" = true ]; then
        PVE_USER_EMAIL=$(pveum user list --output-format json 2>/dev/null | grep -A 5 '"userid":"root@pam"' | grep '"email"' | cut -d'"' -f4 || echo "")
        if [ -n "$PVE_USER_EMAIL" ]; then
            read -p "使用 PVE 配置的邮箱 ($PVE_USER_EMAIL) 进行测试? [Y/n]: " use_pve_email
            if [[ ! "$use_pve_email" =~ ^[Nn]$ ]]; then
                TEST_EMAIL="$PVE_USER_EMAIL"
            else
                read -p "请输入测试邮箱地址: " TEST_EMAIL
            fi
        else
            read -p "请输入测试邮箱地址: " TEST_EMAIL
        fi
    else
        read -p "请输入测试邮箱地址: " TEST_EMAIL
    fi
    
    if [ -z "$TEST_EMAIL" ]; then
        echo -e "${RED}✗ 未输入测试邮箱${NC}"
        return
    fi
    
    echo ""
    echo "正在发送测试邮件..."
    
    HOSTNAME=$(hostname)
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    
    if echo -e "这是一封来自 $HOSTNAME 的测试邮件。\n\n发送时间: $TIMESTAMP\n\n如果您收到这封邮件，说明邮件配置成功！" | \
       mail -s "[测试] PVE 邮件配置测试 - $HOSTNAME" "$TEST_EMAIL" 2>&1; then
        echo -e "${GREEN}✓ 测试邮件已发送到: $TEST_EMAIL${NC}"
        echo ""
        echo "请检查您的邮箱 (包括垃圾邮件文件夹)"
        echo ""
        echo "查看邮件日志: tail -f /var/log/mail.log"
    else
        echo -e "${RED}✗ 邮件发送失败${NC}"
        echo ""
        echo "故障排查:"
        echo "  1. 检查 Postfix 状态: systemctl status postfix"
        echo "  2. 查看邮件日志: tail -f /var/log/mail.log"
        echo "  3. 检查配置: postconf -n"
    fi
    echo ""
}

# 移除SMTP中继配置
remove_relayhost() {
    echo ""
    echo -e "${YELLOW}警告: 此操作将移除 SMTP 中继配置${NC}"
    read -p "确认继续? [y/N]: " confirm
    
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "已取消"
        return
    fi
    
    if [ -f "$POSTFIX_MAIN_CF" ]; then
        # 备份配置文件
        cp "$POSTFIX_MAIN_CF" "${POSTFIX_MAIN_CF}.bak.$(date +%Y%m%d_%H%M%S)"
        
        # 移除relayhost相关配置
        sed -i '/^relayhost/d' "$POSTFIX_MAIN_CF"
        sed -i '/^smtp_use_tls/d' "$POSTFIX_MAIN_CF"
        sed -i '/^smtp_tls_security_level/d' "$POSTFIX_MAIN_CF"
        sed -i '/^smtp_sasl_auth_enable/d' "$POSTFIX_MAIN_CF"
        sed -i '/^smtp_sasl_password_maps/d' "$POSTFIX_MAIN_CF"
        sed -i '/^smtp_sasl_security_options/d' "$POSTFIX_MAIN_CF"
        sed -i '/^smtp_sasl_tls_security_options/d' "$POSTFIX_MAIN_CF"
        
        # 删除认证文件
        rm -f "$POSTFIX_SASL_PASSWD" "$POSTFIX_SASL_PASSWD_DB"
        
        # 重新加载Postfix
        postfix check
        systemctl reload postfix
        
        echo -e "${GREEN}✓ SMTP 中继配置已移除${NC}"
    else
        echo -e "${YELLOW}⚠ Postfix 配置文件不存在${NC}"
    fi
    echo ""
}

# 主循环
while true; do
    show_menu
    
    case $choice in
        1)
            configure_email_wizard
            ;;
        2)
            configure_relayhost
            ;;
        3)
            configure_smtp_auth
            ;;
        4)
            configure_pve_user_email
            ;;
        5)
            configure_pve_datacenter_email
            ;;
        6)
            show_current_config
            ;;
        7)
            test_email
            ;;
        8)
            remove_relayhost
            ;;
        9)
            echo "退出配置工具"
            exit 0
            ;;
        *)
            echo -e "${RED}无效选项，请重新选择${NC}"
            ;;
    esac
    
    echo ""
    read -p "按 Enter 继续..."
    echo ""
done

