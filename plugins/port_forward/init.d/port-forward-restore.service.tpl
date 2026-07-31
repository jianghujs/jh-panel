[Unit]
Description=JH Panel Port Forward Restore
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory={$ROOT_PATH}
ExecStart=/usr/bin/env python3 {$ROOT_PATH}/plugins/port_forward/index.py restore_rules
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
