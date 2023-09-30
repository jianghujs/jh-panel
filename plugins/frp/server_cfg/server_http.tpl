[common]
bind_port = 7000
vhost_http_port = 8080

# frp管理后台端口，请按自己需求更改
dashboard_port = 7500
# frp管理后台用户名和密码，请改成自己的
dashboard_user = admin
dashboard_pwd = admin
enable_prometheus = false

log_file = {$SERVER_APP}/frps.log
log_level = info
log_max_days = 3