# docker

## 执行脚本
1. 仓库列表
```
python3 /www/server/mdserver-web/plugins/docker/index.py repository_list 
```
2. 添加仓库
```
python3 /www/server/mdserver-web/plugins/docker/index.py repository_add {"user_name":"","user_pass":"","registry":"","hub_name":"test","namespace":"","repository_name":"DockerHub2"}
```
3. 删除
```
python3 /www/server/mdserver-web/plugins/docker/index.py repository_delete {id:1}
```
4. 启动
```
python3 /www/server/mdserver-web/plugins/docker/index.py service_ctl {"s_type":"start"}
```
5. 停止
```
python3 /www/server/mdserver-web/plugins/docker/index.py service_ctl {"s_type":"stop"}
```
6. 重启
```
python3 /www/server/mdserver-web/plugins/docker/index.py service_ctl {"s_type":"restart"}
```
