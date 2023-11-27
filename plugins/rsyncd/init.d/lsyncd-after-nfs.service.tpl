[Unit]
Description=Start lsyncd after NFS is ready
After=nfs-client.target
Wants=nfs-client.target

[Service]
Type=oneshot
ExecStartPre=/bin/sleep 30 
ExecStart=/usr/bin/systemctl start lsyncd

[Install]
WantedBy=multi-user.target
