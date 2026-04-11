#!/bin/bash

set -e

LOGROTATE_CONFIG="/etc/logrotate.d/large-log-limit"

echo "开始初始化日志轮转配置..."

if ! command -v logrotate >/dev/null 2>&1; then
    echo "未检测到logrotate，正在安装..."
    apt-get update
    apt-get install -y logrotate
fi

cat > "${LOGROTATE_CONFIG}" <<'EOF'
/var/log/syslog
/var/log/daemon.log
/var/log/filebeat/filebeat
/var/log/filebeat/*.log
{
    size 1G
    rotate 4
    missingok
    notifempty
    compress
    delaycompress
    copytruncate
}
EOF

echo "logrotate配置已写入: ${LOGROTATE_CONFIG}"

if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files logrotate.timer >/dev/null 2>&1; then
    systemctl enable --now logrotate.timer >/dev/null 2>&1 || true
fi

echo "初始化日志轮转配置完成."
