#!/bin/bash

# 添加确认提示
read -p "确定要配置seatable自启动服务吗？ (y/n) " -n 1 -r
echo    # (optional) move to a new line
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    exit 1
fi

# 创建脚本文件
echo "正在配置启动脚本文件..."
cat << EOF > /opt/seatable/seatable-autostart.sh
#!/bin/bash
case \$1 in
    start)
    docker exec -d seatable /shared/seatable/scripts/seatable.sh start
    ;;
    stop)
    docker exec -d seatable /shared/seatable/scripts/seatable.sh stop
    ;;
    restart)
    sleep 10
    docker exec -d seatable /shared/seatable/scripts/seatable.sh restart
    ;;
esac
EOF
echo "配置启动脚本文件成功✅"

systemctl daemon-reload

# 配置脚本可执行权限
chmod u+x /opt/seatable/seatable-autostart.sh

# 配置 systemd 单元文件
echo "正在配置systemd单元文件..."
cat << EOF > /etc/systemd/system/seatable.service
[Unit]
Description=SeaTable
After=network.target

[Service]
ExecStart=/opt/seatable/seatable-autostart.sh start
ExecStop=/opt/seatable/seatable-autostart.sh stop
User=root
Type=forking
TimeoutSec=0
RemainAfterExit=yes
GuessMainPID=no

[Install]
WantedBy=multi-user.target
EOF
echo "配置systemd单元文件成功✅"

systemctl daemon-reload
# 开启并自启动服务
systemctl start seatable
echo "服务启动成功✅"
systemctl enable seatable
echo "服务自启动配置成功✅"
systemctl status seatable
