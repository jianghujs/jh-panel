# frp

frp内网穿透服务

## 配置模式

- 单配置文件模式：继续使用 `server/frp/frps.ini` 和 `server/frp/frpc.ini`
- 多配置文件模式：分别使用 `server/frp/frps.d/*.ini` 和 `server/frp/frpc.d/*.ini`
- 服务端与客户端可分别切换模式，互不影响
- 切换模式不会删除另一套文件，实际启动时仅加载当前模式对应的文件

## 运行说明

- 多配置文件模式下，每个 `.ini` 文件会启动为一个独立的 frp 进程
- 请自行检查多个配置之间的端口、代理名和日志输出是否冲突
- 升级旧版本插件时，如未发现模式文件，默认按单配置文件模式兼容
- Linux 安装时会优先使用 `plugins/frp/source/frp_0.44.0_linux_amd64.tar.gz` 本地离线包，只有本地包缺失时才回退到外网下载

# 安装命令
```
cd /www/server/mdserver-web/plugins && rm -rf frp && git clone https://github.com/mw-plugin/frp && cd frp && rm -rf .git && cd /www/server/mdserver-web/plugins/frp && bash install.sh install 1.0
```

