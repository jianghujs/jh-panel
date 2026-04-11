#!/bin/bash

set -e

LOGROTATE_CONFIG="/etc/logrotate.d/large-log-limit"
LOGROTATE_SERVICE="/etc/systemd/system/large-log-limit.service"
LOGROTATE_TIMER="/etc/systemd/system/large-log-limit.timer"
LOGROTATE_STATE="/var/lib/logrotate/large-log-limit.status"

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

mkdir -p "$(dirname "${LOGROTATE_STATE}")"
touch "${LOGROTATE_STATE}"

cat > "${LOGROTATE_SERVICE}" <<EOF
[Unit]
Description=Run logrotate for large-log-limit only

[Service]
Type=oneshot
ExecStart=$(command -v logrotate) -s ${LOGROTATE_STATE} ${LOGROTATE_CONFIG}
EOF

cat > "${LOGROTATE_TIMER}" <<'EOF'
[Unit]
Description=Run large-log-limit logrotate every 5 minutes

[Timer]
OnCalendar=*:0/5
AccuracySec=1m
Persistent=true

[Install]
WantedBy=timers.target
EOF

if command -v systemctl >/dev/null 2>&1; then
    systemctl daemon-reload
    systemctl enable --now large-log-limit.timer >/dev/null 2>&1
fi

echo "初始化日志轮转配置完成."
