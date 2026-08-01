[Unit]
Description=JH Panel Port Forward Restore
After=network-online.target netfilter-persistent.service docker.service firewalld.service
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory={$ROOT_PATH}
ExecStartPre=/bin/sleep 15
ExecStart=/usr/bin/env python3 {$ROOT_PATH}/plugins/port_forward/index.py restore_rules
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
