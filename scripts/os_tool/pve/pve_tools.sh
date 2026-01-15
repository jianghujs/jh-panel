#!/bin/bash
#
# PVE 工具脚本
# 提供常用的 PVE 系统工具函数
#
# 作者: PVE Admin
# 版本: 1.0
#

set -e

# ========================= 配置区域 =========================

# 默认邮件配置
DEFAULT_FROM="root@$(hostname -f)"
DEFAULT_CHARSET="utf-8"

# ========================= 邮件发送函数 =========================

#
# 发送邮件
#
# 用法:
#   send_email --to <收件人> --subject <主题> --body <内容> [选项]
#
# 参数:
#   --to <email>          收件人邮箱（必需）
#   --subject <text>      邮件主题（必需）
#   --body <text>         邮件正文（必需，可以是文本或HTML）
#   --body-file <path>    邮件正文文件（与 --body 二选一）
#   --html                邮件正文为HTML格式（默认为纯文本）
#   --from <email>        发件人邮箱（默认: root@hostname）
#   --cc <email>          抄送邮箱（可选）
#   --bcc <email>         密送邮箱（可选）
#   --attachment <path>   附件文件路径（可选）
#
# 返回值:
#   0 - 发送成功
#   1 - 参数错误
#   2 - 邮件工具未安装
#   3 - 发送失败
#
# 示例:
#   # 发送纯文本邮件
#   send_email --to user@example.com --subject "测试邮件" --body "这是测试内容"
#
#   # 发送HTML邮件
#   send_email --to user@example.com --subject "HTML邮件" --body-file report.html --html
#
#   # 发送带附件的邮件
#   send_email --to user@example.com --subject "报告" --body "请查收附件" --attachment report.pdf
#
send_email() {
    local to=""
    local subject=""
    local body=""
    local body_file=""
    local html=false
    local from="$DEFAULT_FROM"
    local cc=""
    local bcc=""
    local attachment=""
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --to)
                to="$2"
                shift 2
                ;;
            --subject)
                subject="$2"
                shift 2
                ;;
            --body)
                body="$2"
                shift 2
                ;;
            --body-file)
                body_file="$2"
                shift 2
                ;;
            --html)
                html=true
                shift
                ;;
            --from)
                from="$2"
                shift 2
                ;;
            --cc)
                cc="$2"
                shift 2
                ;;
            --bcc)
                bcc="$2"
                shift 2
                ;;
            --attachment)
                attachment="$2"
                shift 2
                ;;
            *)
                echo "错误: 未知参数 $1" >&2
                return 1
                ;;
        esac
    done
    
    # 验证必需参数
    if [[ -z "$to" ]]; then
        echo "错误: 缺少收件人 (--to)" >&2
        return 1
    fi
    
    if [[ -z "$subject" ]]; then
        echo "错误: 缺少邮件主题 (--subject)" >&2
        return 1
    fi
    
    if [[ -z "$body" && -z "$body_file" ]]; then
        echo "错误: 缺少邮件正文 (--body 或 --body-file)" >&2
        return 1
    fi
    
    # 如果指定了 body-file，读取文件内容
    if [[ -n "$body_file" ]]; then
        if [[ ! -f "$body_file" ]]; then
            echo "错误: 文件不存在: $body_file" >&2
            return 1
        fi
        body=$(cat "$body_file")
    fi
    
    # 检查 sendmail 是否可用
    if ! command -v sendmail &> /dev/null; then
        echo "错误: sendmail 未安装" >&2
        echo "请安装邮件工具: apt-get install postfix" >&2
        return 2
    fi
    
    # 创建临时邮件文件
    local tmp_mail=$(mktemp /tmp/pve_mail.XXXXXX)
    
    # 构建邮件头
    {
        echo "From: $from"
        echo "To: $to"
        [[ -n "$cc" ]] && echo "Cc: $cc"
        [[ -n "$bcc" ]] && echo "Bcc: $bcc"
        echo "Subject: $subject"
        echo "MIME-Version: 1.0"
        
        if [[ "$html" == true ]]; then
            echo "Content-Type: text/html; charset=$DEFAULT_CHARSET"
        else
            echo "Content-Type: text/plain; charset=$DEFAULT_CHARSET"
        fi
        
        echo ""
        echo "$body"
    } > "$tmp_mail"
    
    # 发送邮件
    if sendmail -t < "$tmp_mail" 2>&1; then
        rm -f "$tmp_mail"
        echo "✓ 邮件已发送至: $to"
        return 0
    else
        local exit_code=$?
        rm -f "$tmp_mail"
        echo "✗ 邮件发送失败 (退出码: $exit_code)" >&2
        return 3
    fi
}

#
# 发送 PVE 系统通知 (使用 PVE::Notify)
#
# 用法:
#   send_pve_notify --subject <主题> --body-file <文件路径> [--severity <级别>]
#
# 参数:
#   --severity    通知级别 (info, notice, warning, error, unknown). 默认: info
#
# 返回值:
#   0 - 发送成功
#   1 - 参数错误
#   2 - PVE::Notify 模块不可用
#   3 - 发送失败
#
send_pve_notify() {
    local subject=""
    local body_file=""
    local severity="info"
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --subject)
                subject="$2"
                shift 2
                ;;
            --body-file)
                body_file="$2"
                shift 2
                ;;
            --severity)
                severity="$2"
                shift 2
                ;;
            *)
                echo "错误: 未知参数 $1" >&2
                return 1
                ;;
        esac
    done
    
    if [[ -z "$subject" || -z "$body_file" ]]; then
        echo "错误: 缺少必需参数 (--subject, --body-file)" >&2
        return 1
    fi
    
    if [[ ! -f "$body_file" ]]; then
        echo "错误: 文件不存在: $body_file" >&2
        return 1
    fi
    
    # 检查 PVE::Notify 模块是否存在
    if ! perl -e 'use PVE::Notify' 2>/dev/null; then
        echo "错误: PVE::Notify 模块不可用 (仅支持 PVE 8.1+)" >&2
        return 2
    fi
    
    # 使用 Perl 发送通知
    if perl -e '
        use strict;
        use warnings;
        use PVE::Notify;
        
        my $severity = $ARGV[0];
        my $subject = $ARGV[1];
        my $body_file = $ARGV[2];
        
        open(my $fh, "<", $body_file) or die "Cannot open file: $!";
        local $/;
        my $content = <$fh>;
        close($fh);
        
        # notify($severity, $title, $message, $template_data, $fields, $config)
        PVE::Notify::notify($severity, $subject, $content);
    ' "$severity" "$subject" "$body_file"; then
        echo "✓ PVE 通知已发送 ($severity)"
        return 0
    else
        echo "✗ PVE 通知发送失败" >&2
        return 3
    fi
}

# ========================= 其他工具函数 =========================

#
# 获取 PVE 配置的邮箱地址
#
# 返回值:
#   成功: 输出邮箱地址
#   失败: 返回空字符串
#
get_pve_email() {
    local email=""
    
    # 1. 尝试从 PVE 通知配置读取 (优先级最高，因为这是 PVE 面板专门的通知配置)
    if [[ -f /etc/pve/notifications.cfg ]]; then
        # 查找 mailto 配置，排除 mailto-user
        email=$(grep "^\s*mailto\s" /etc/pve/notifications.cfg | head -1 | awk '{print $2}')
    fi

    # 2. 尝试从 pveum 读取 root@pam 邮箱
    if [[ -z "$email" ]] && command -v pveum &> /dev/null; then
        email=$(pveum user list --output-format json 2>/dev/null | \
                grep -A 5 '"userid":"root@pam"' | \
                grep '"email"' | \
                cut -d'"' -f4)
    fi

    # 3. 尝试从 Datacenter 配置读取
    if [[ -z "$email" && -f /etc/pve/datacenter.cfg ]]; then
        email=$(grep "^email:" /etc/pve/datacenter.cfg | head -1 | awk '{print $2}')
    fi
    
    # 4. 尝试从 /etc/aliases 读取 root 的转发地址 (最后尝试)
    if [[ -z "$email" && -f /etc/aliases ]]; then
        email=$(grep "^root:" /etc/aliases | head -1 | cut -d: -f2 | tr -d ' ')
    fi
    
    echo "$email"
}

#
# 检查邮件系统是否配置正确
#
# 返回值:
#   0 - 配置正确
#   1 - 配置有问题
#
check_mail_system() {
    local has_error=false
    
    echo "=== 检查邮件系统配置 ==="
    echo ""
    
    # 检查 sendmail
    if command -v sendmail &> /dev/null; then
        echo "✓ sendmail 已安装: $(which sendmail)"
    else
        echo "✗ sendmail 未安装"
        has_error=true
    fi
    
    # 检查 Postfix
    if command -v postfix &> /dev/null; then
        echo "✓ Postfix 已安装: $(postfix version 2>&1 | head -1)"
        
        # 检查 Postfix 状态
        if systemctl is-active --quiet postfix; then
            echo "✓ Postfix 服务运行中"
        else
            echo "✗ Postfix 服务未运行"
            has_error=true
        fi
    else
        echo "✗ Postfix 未安装"
        has_error=true
    fi
    
    # 检查 /etc/aliases
    if [[ -f /etc/aliases ]]; then
        echo "✓ /etc/aliases 存在"
        local root_alias=$(grep "^root:" /etc/aliases | head -1)
        if [[ -n "$root_alias" ]]; then
            echo "  $root_alias"
        else
            echo "  警告: 未配置 root 邮件转发"
        fi
    else
        echo "✗ /etc/aliases 不存在"
    fi
    
    # 检查邮件队列
    if command -v mailq &> /dev/null; then
        local queue_output=$(mailq 2>&1)
        if echo "$queue_output" | grep -q "Mail queue is empty"; then
            echo "✓ 邮件队列为空"
        else
            local queue_count=$(echo "$queue_output" | grep -c "^[A-F0-9]" || echo "0")
            if [[ "$queue_count" -eq 0 ]]; then
                echo "✓ 邮件队列为空"
            else
                echo "⚠ 邮件队列有 $queue_count 封待发邮件"
            fi
        fi
    fi
    
    # 检查 PVE 邮箱配置
    local pve_email=$(get_pve_email)
    if [[ -n "$pve_email" ]]; then
        echo "✓ PVE 邮箱已配置: $pve_email"
    else
        echo "⚠ PVE 邮箱未配置"
    fi
    
    echo ""
    
    if [[ "$has_error" == true ]]; then
        echo "❌ 邮件系统配置有问题"
        return 1
    else
        echo "✅ 邮件系统配置正常"
        return 0
    fi
}

#
# 发送测试邮件
#
# 用法:
#   send_test_email [收件人邮箱]
#
# 参数:
#   收件人邮箱（可选，默认使用 PVE 配置的邮箱）
#
send_test_email() {
    local to="$1"
    
    # 如果没有指定收件人，使用 PVE 配置的邮箱
    if [[ -z "$to" ]]; then
        to=$(get_pve_email)
        if [[ -z "$to" ]]; then
            echo "错误: 未指定收件人，且 PVE 邮箱未配置" >&2
            return 1
        fi
    fi
    
    local subject="[$(hostname)] PVE 邮件系统测试"
    local body="这是一封测试邮件。

发送时间: $(date '+%Y-%m-%d %H:%M:%S')
主机名: $(hostname)
系统: $(uname -a)

如果您收到这封邮件，说明 PVE 邮件系统工作正常。"
    
    echo "正在发送测试邮件到: $to"
    send_email --to "$to" --subject "$subject" --body "$body"
}

# ========================= 主程序 =========================

#
# 显示帮助信息
#
show_help() {
    cat << EOF
PVE 工具脚本 v1.0

用法:
  $0 <命令> [参数]

命令:
  send-email          发送邮件
  get-pve-email       获取 PVE 配置的邮箱地址
      check-mail-system   检查邮件系统配置
    send-test-email     发送测试邮件
    send-pve-notify     发送 PVE 系统通知 (PVE 8.1+)
    help                显示帮助信息
  
  示例:
    # 发送纯文本邮件
    $0 send-email --to user@example.com --subject "测试" --body "内容"
    
    # 发送 PVE 通知
    $0 send-pve-notify --subject "警告" --body-file /tmp/msg.txt
  
detailed documentation:
  Please check the function comments in the script source code

EOF
}
  
  # 主程序入口
  if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
      # 脚本被直接执行
      if [[ $# -eq 0 ]]; then
          show_help
          exit 0
      fi
      
      command="$1"
      shift
      
      case "$command" in
          send-email)
              send_email "$@"
              ;;
          get-pve-email)
              get_pve_email
              ;;
          check-mail-system)
              check_mail_system
              ;;
          send-test-email)
              send_test_email "$@"
              ;;
          send-pve-notify)
              send_pve_notify "$@"
              ;;
          help|--help|-h)
              show_help
              ;;
          *)
              echo "错误: 未知命令 '$command'" >&2
              echo "使用 '$0 help' 查看帮助信息" >&2
              exit 1
              ;;
      esac
  else    # 脚本被 source 引入
    :
fi

