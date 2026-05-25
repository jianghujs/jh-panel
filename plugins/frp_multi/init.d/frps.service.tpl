[Unit]
Description=frp server wrapper
After=network.target remote-fs.target nss-lookup.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart={$WRAPPER_PATH} server start
ExecStop={$WRAPPER_PATH} server stop
ExecReload={$WRAPPER_PATH} server restart

[Install]
WantedBy=multi-user.target
