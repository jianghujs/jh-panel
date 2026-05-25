[Unit]
Description=frp client wrapper
After=network.target remote-fs.target nss-lookup.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart={$WRAPPER_PATH} client start
ExecStop={$WRAPPER_PATH} client stop
ExecReload={$WRAPPER_PATH} client restart

[Install]
WantedBy=multi-user.target
