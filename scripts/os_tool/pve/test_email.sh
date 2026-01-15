#!/bin/bash
#
# PVE 邮件发送功能测试脚本
# 用于诊断和测试邮件发送配置
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}================================${NC}"
echo -e "${CYAN}PVE 邮件发送功能测试${NC}"
echo -e "${CYAN}================================${NC}"
echo ""

# 1. 检查邮件工具
echo -e "${CYAN}[1/7] 检查邮件发送工具...${NC}"
MAIL_TOOL=""

if command -v sendmail &> /dev/null; then
    echo -e "${GREEN}✓ sendmail 已安装: $(which sendmail)${NC}"
    MAIL_TOOL="sendmail"
elif command -v mail &> /dev/null; then
    echo -e "${GREEN}✓ mail 已安装: $(which mail)${NC}"
    MAIL_TOOL="mail"
else
    echo -e "${RED}✗ 未安装邮件工具${NC}"
    echo -e "${YELLOW}请安装邮件工具:${NC}"
    echo "  apt-get install -y mailutils"
    echo "  或"
    echo "  apt-get install -y sendmail"
    exit 1
fi
echo ""

# 2. 检查 Postfix 服务
echo -e "${CYAN}[2/7] 检查 Postfix 邮件服务...${NC}"
if systemctl is-active --quiet postfix; then
    echo -e "${GREEN}✓ Postfix 服务运行中${NC}"
else
    echo -e "${YELLOW}⚠ Postfix 服务未运行${NC}"
    echo "尝试启动 Postfix..."
    if systemctl start postfix 2>/dev/null; then
        echo -e "${GREEN}✓ Postfix 已启动${NC}"
    else
        echo -e "${RED}✗ 无法启动 Postfix${NC}"
        echo "请检查 Postfix 配置"
    fi
fi
echo ""

# 3. 检查 Postfix 配置
echo -e "${CYAN}[3/7] 检查 Postfix 配置...${NC}"
if [ -f /etc/postfix/main.cf ]; then
    echo "关键配置项:"
    echo "  myhostname: $(postconf -h myhostname)"
    echo "  relayhost: $(postconf -h relayhost)"
    echo "  inet_interfaces: $(postconf -h inet_interfaces)"
    
    RELAYHOST=$(postconf -h relayhost)
    if [ -z "$RELAYHOST" ]; then
        echo -e "${YELLOW}⚠ 未配置 relayhost (将使用本地发送)${NC}"
    else
        echo -e "${GREEN}✓ 已配置 relayhost: $RELAYHOST${NC}"
    fi
else
    echo -e "${RED}✗ Postfix 配置文件不存在${NC}"
fi
echo ""

# 4. 检查 PVE 邮箱配置
echo -e "${CYAN}[4/7] 检查 PVE 邮箱配置...${NC}"
PVE_EMAIL=""

# 尝试从 root@pam 用户读取
if command -v pveum &> /dev/null; then
    PVE_EMAIL=$(pveum user list --output-format json 2>/dev/null | grep -A 5 '"userid":"root@pam"' | grep '"email"' | cut -d'"' -f4 || echo "")
    
    if [ -n "$PVE_EMAIL" ]; then
        echo -e "${GREEN}✓ root@pam 邮箱: $PVE_EMAIL${NC}"
    else
        echo -e "${YELLOW}⚠ root@pam 未配置邮箱${NC}"
        echo "配置方法: pveum user modify root@pam -email your@email.com"
    fi
else
    echo -e "${YELLOW}⚠ pveum 命令不可用 (可能不是 PVE 系统)${NC}"
fi

# 检查 datacenter 配置
if [ -f /etc/pve/datacenter.cfg ]; then
    DC_EMAIL=$(grep -E "^email:" /etc/pve/datacenter.cfg 2>/dev/null | cut -d' ' -f2 || echo "")
    if [ -n "$DC_EMAIL" ]; then
        echo -e "${GREEN}✓ Datacenter 邮箱: $DC_EMAIL${NC}"
        [ -z "$PVE_EMAIL" ] && PVE_EMAIL="$DC_EMAIL"
    fi
fi
echo ""

# 5. 获取测试邮箱
echo -e "${CYAN}[5/7] 准备测试邮件...${NC}"
if [ -n "$1" ]; then
    TEST_EMAIL="$1"
    echo "使用命令行参数指定的邮箱: $TEST_EMAIL"
elif [ -n "$PVE_EMAIL" ]; then
    TEST_EMAIL="$PVE_EMAIL"
    echo "使用 PVE 配置的邮箱: $TEST_EMAIL"
else
    echo -e "${YELLOW}请输入测试邮箱地址:${NC}"
    read -p "邮箱: " TEST_EMAIL
fi

if [ -z "$TEST_EMAIL" ]; then
    echo -e "${RED}✗ 未提供邮箱地址${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 测试邮箱: $TEST_EMAIL${NC}"
echo ""

# 6. 发送测试邮件
echo -e "${CYAN}[6/7] 发送测试邮件...${NC}"
HOSTNAME=$(hostname)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# 创建 HTML 测试邮件
HTML_CONTENT="<!DOCTYPE html>
<html>
<head>
    <meta charset='utf-8'>
    <title>PVE 邮件测试</title>
</head>
<body style='font-family: Arial, sans-serif; margin: 20px;'>
    <h2 style='color: #2196F3;'>PVE 邮件发送测试</h2>
    <p>这是一封来自 <strong>$HOSTNAME</strong> 的测试邮件。</p>
    <table style='border-collapse: collapse; margin: 20px 0;'>
        <tr>
            <td style='padding: 8px; border: 1px solid #ddd; background: #f5f5f5;'><strong>主机名:</strong></td>
            <td style='padding: 8px; border: 1px solid #ddd;'>$HOSTNAME</td>
        </tr>
        <tr>
            <td style='padding: 8px; border: 1px solid #ddd; background: #f5f5f5;'><strong>发送时间:</strong></td>
            <td style='padding: 8px; border: 1px solid #ddd;'>$TIMESTAMP</td>
        </tr>
        <tr>
            <td style='padding: 8px; border: 1px solid #ddd; background: #f5f5f5;'><strong>邮件工具:</strong></td>
            <td style='padding: 8px; border: 1px solid #ddd;'>$MAIL_TOOL</td>
        </tr>
    </table>
    <p style='color: green;'>✓ 如果您收到这封邮件，说明邮件发送功能正常！</p>
    <hr style='margin: 20px 0;'>
    <p style='color: #666; font-size: 12px;'>PVE 硬件监控系统 - 邮件测试</p>
</body>
</html>"

# 创建临时文件
TMP_HTML=$(mktemp /tmp/test_email_XXXXXX.html)
echo "$HTML_CONTENT" > "$TMP_HTML"

# 根据可用工具发送邮件
SEND_SUCCESS=false

if [ "$MAIL_TOOL" = "sendmail" ]; then
    echo "使用 sendmail 发送..."
    TMP_EML=$(mktemp /tmp/test_email_XXXXXX.eml)
    cat > "$TMP_EML" << EOF
To: $TEST_EMAIL
Subject: [测试] PVE 邮件发送测试 - $HOSTNAME
MIME-Version: 1.0
Content-Type: text/html; charset=utf-8

$HTML_CONTENT
EOF
    
    if sendmail -t < "$TMP_EML" 2>&1; then
        SEND_SUCCESS=true
    fi
    rm -f "$TMP_EML"
    
elif [ "$MAIL_TOOL" = "mail" ]; then
    echo "使用 mail 命令发送..."
    if echo "$HTML_CONTENT" | mail -s "[测试] PVE 邮件发送测试 - $HOSTNAME" -a "Content-Type: text/html; charset=utf-8" "$TEST_EMAIL" 2>&1; then
        SEND_SUCCESS=true
    fi
fi

rm -f "$TMP_HTML"

if [ "$SEND_SUCCESS" = true ]; then
    echo -e "${GREEN}✓ 邮件已发送${NC}"
else
    echo -e "${RED}✗ 邮件发送失败${NC}"
fi
echo ""

# 7. 检查邮件日志
echo -e "${CYAN}[7/7] 检查邮件日志...${NC}"
if [ -f /var/log/mail.log ]; then
    echo "最近的邮件日志 (最后10行):"
    tail -10 /var/log/mail.log | sed 's/^/  /'
elif [ -f /var/log/maillog ]; then
    echo "最近的邮件日志 (最后10行):"
    tail -10 /var/log/maillog | sed 's/^/  /'
else
    echo -e "${YELLOW}⚠ 未找到邮件日志文件${NC}"
fi
echo ""

# 总结
echo -e "${CYAN}================================${NC}"
echo -e "${CYAN}测试总结${NC}"
echo -e "${CYAN}================================${NC}"
echo ""

if [ "$SEND_SUCCESS" = true ]; then
    echo -e "${GREEN}✓ 测试邮件已发送到: $TEST_EMAIL${NC}"
    echo ""
    echo "请检查您的邮箱 (包括垃圾邮件文件夹)"
    echo ""
    echo "如果未收到邮件，请检查:"
    echo "  1. 查看邮件日志: tail -f /var/log/mail.log"
    echo "  2. 检查 Postfix 配置: postconf -n"
    echo "  3. 测试 Postfix: echo 'test' | mail -s 'test' $TEST_EMAIL"
    echo "  4. 检查防火墙规则: iptables -L -n | grep 25"
else
    echo -e "${RED}✗ 邮件发送失败${NC}"
    echo ""
    echo "故障排查建议:"
    echo "  1. 检查 Postfix 状态: systemctl status postfix"
    echo "  2. 查看错误日志: tail -f /var/log/mail.log"
    echo "  3. 测试 Postfix: postfix check"
    echo "  4. 重启 Postfix: systemctl restart postfix"
fi
echo ""

# 提供配置建议
if [ -z "$(postconf -h relayhost)" ]; then
    echo -e "${YELLOW}提示: 未配置 SMTP 中继服务器${NC}"
    echo ""
    echo "如果需要使用外部 SMTP 服务器 (如 Gmail)，请配置:"
    echo ""
    echo "1. 编辑 /etc/postfix/main.cf，添加:"
    echo "   relayhost = [smtp.gmail.com]:587"
    echo "   smtp_use_tls = yes"
    echo "   smtp_sasl_auth_enable = yes"
    echo "   smtp_sasl_password_maps = hash:/etc/postfix/sasl_passwd"
    echo "   smtp_sasl_security_options = noanonymous"
    echo ""
    echo "2. 创建 /etc/postfix/sasl_passwd:"
    echo "   [smtp.gmail.com]:587 your@gmail.com:your_app_password"
    echo ""
    echo "3. 更新数据库并重启:"
    echo "   postmap /etc/postfix/sasl_passwd"
    echo "   chmod 600 /etc/postfix/sasl_passwd*"
    echo "   systemctl restart postfix"
    echo ""
fi

exit 0

