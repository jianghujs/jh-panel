[Unit]
Description=Redis In-Memory Data Store

After=network-online.target syslog.target 
# 当需要等待wg0启动时，可改为以下配置
# After=network-online.target syslog.target wg-quick@wg0.service
# Requires=wg-quick@wg0.service
ExecStartPre=/bin/sleep 3

[Service]
Type=forking
ExecStart={$SERVER_PATH}/keepalived/sbin/keepalived -D
ExecReload=/bin/kill -USR1 $MAINPID
Restart=on-failure
StandardOutput={$SERVER_PATH}/keepalived/keepalived.log

[Install]
WantedBy=multi-user.target