[Unit]
Description=Lightweight inotify based sync daemon
ConditionPathExists={$SERVER_PATH}/rsyncd/lsyncd.conf

[Service]
Type=simple
ExecStart={$LSYNCD_BIN} -nodaemon -log all {$SERVER_PATH}/rsyncd/lsyncd.conf
StandardOutput=null

[Install]
WantedBy=multi-user.target
