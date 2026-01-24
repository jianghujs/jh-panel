#!/bin/bash
set -e

netEnvCn="$1"
DEST_DIR="/www/server/os_tool"
BIN_PATH="/usr/local/bin/jht"
PANEL_DIR="/www/server/jh-panel"
LOCAL_SOURCE="${PANEL_DIR}/scripts/os_tool"

if [ -z "$netEnvCn" ]; then
  if [ -f "/www/server/jh-panel/data/net_env_cn.pl" ]; then
    netEnvCn="cn"
  fi
fi

download_file() {
  local url="$1"
  local dest="$2"
  if command -v wget >/dev/null 2>&1; then
    wget -nv -O "$dest" "$url"
    return $?
  fi
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL -o "$dest" "$url"
    return $?
  fi
  echo "未检测到 wget 或 curl，无法下载文件。"
  return 1
}

copy_source=""
if [ -d "$LOCAL_SOURCE" ]; then
  echo "检测到本地面板目录，使用本地脚本安装: ${LOCAL_SOURCE}"
  copy_source="$LOCAL_SOURCE"
else
  archive_url=""
  if [ "$netEnvCn" == "cn" ]; then
    archive_url="https://gitee.com/jianghujs/jh-panel/repository/archive/master.tar.gz"
  else
    archive_url="https://github.com/jianghujs/jh-panel/archive/refs/heads/master.tar.gz"
  fi

  tmp_dir=$(mktemp -d)
  archive_file="${tmp_dir}/jh-panel.tar.gz"
  trap 'rm -rf "$tmp_dir"' EXIT

  echo "开始下载安装包: ${archive_url}"
  if ! download_file "$archive_url" "$archive_file"; then
    echo "下载失败，请检查网络或镜像设置。"
    exit 1
  fi

  if ! tar -xzf "$archive_file" -C "$tmp_dir"; then
    echo "解压失败，请检查压缩包内容。"
    exit 1
  fi

  src_dir=$(find "$tmp_dir" -maxdepth 2 -type d -name "jh-panel*" | head -n 1)
  if [ -z "$src_dir" ] || [ ! -d "$src_dir/scripts/os_tool" ]; then
    echo "未找到 scripts/os_tool 目录，无法安装。"
    exit 1
  fi
  copy_source="$src_dir/scripts/os_tool"
fi

if [ -z "$copy_source" ] || [ ! -d "$copy_source" ]; then
  echo "未找到可用的 os_tool 源目录，无法安装。"
  exit 1
fi

mkdir -p "$DEST_DIR"
if command -v rsync >/dev/null 2>&1; then
  rsync -a "$copy_source/" "$DEST_DIR/"
else
  cp -a "$copy_source/." "$DEST_DIR/"
fi

find "$DEST_DIR" -type f -name "*.sh" -exec chmod +x {} \;

cat > "$BIN_PATH" << 'EOT'
#!/bin/bash
bash /www/server/os_tool/index.sh "$@"
EOT
chmod +x "$BIN_PATH"

echo "安装完成: $DEST_DIR"
echo "命令入口: $BIN_PATH"
