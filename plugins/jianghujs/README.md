# jianghujs


## 脚本
1. 启动
```
git pull
npm i
npm start
```
2. 重启
```
npm stop
npm start
```
3. 停止
```
npm stop
```
4. 获取运行状态
```
ps -ef| grep jianghujs-1table-crud | grep -v grep | awk '{print $2}'
```



## 执行脚本
1. 查看状态
```
python3 /www/server/mdserver-web/plugins/jianghujs/index.py project_status {name:jianghujs-1table-crud}
```
2. 启动
```
python3 /www/server/mdserver-web/plugins/jianghujs/index.py project_start {name:jianghujs-1table-crud}

python3 /www/server/mdserver-web/plugins/jianghujs/index.py project_script_excute {id:6,scriptKey:start_script}
```
3. 停止
```
python3 /www/server/mdserver-web/plugins/jianghujs/index.py project_stop {name:jianghujs-1table-crud}
```
4. 重启
```
python3 /www/server/mdserver-web/plugins/jianghujs/index.py project_restart {name:jianghujs-1table-crud}
```
5. 更新
```
python3 /www/server/mdserver-web/plugins/jianghujs/index.py project_update {name:jianghujs-1table-crud}
```
6. 列表
```
python3 /www/server/mdserver-web/plugins/jianghujs/index.py project_list
```
7. 新增
```
python3 /www/server/mdserver-web/plugins/jianghujs/index.py project_add {name:jianghujs-1table-crud}

python3 /www/server/mdserver-web/plugins/jianghujs/index.py project_add  {"name":"jianghujs-1table-crud","path":"%2Fwww%2Fwwwroot%2Fjianghujs-1table-crud","startScript":"cd+%2Fwww%2Fwwwroot%2Fjianghujs-1table-crud%0D%0Anpm+i%0D%0Anpm+start","reloadScript":"cd+%2Fwww%2Fwwwroot%2Fjianghujs-1table-crud%0D%0Anpm+stop%0D%0Anpm+start","stopScript":"cd+%2Fwww%2Fwwwroot%2Fjianghujs-1table-crud%0D%0Anpm+stop"}
```
8. 编辑
```
python3 /www/server/mdserver-web/plugins/jianghujs/index.py project_edit {name:jianghujs-1table-crud}
```
9. 删除
```
python3 /www/server/mdserver-web/plugins/jianghujs/index.py project_delete{name:jianghujs-1table-crud}
```
10. 日志

```
python3 /www/server/mdserver-web/plugins/jianghujs/index.py project_logs {id:14}
```