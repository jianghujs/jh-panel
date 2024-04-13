#!/bin/bash

# 定位到脚本所在目录
cd "$(dirname "$0")"

# 获取当前版本号
current_version=$(grep -oP "__version\s*=\s*'\K[^']+" ./class/core/config_api.py)
echo "当前版本号: $current_version"

# 分割版本号并递增
IFS='.' read -ra ADDR <<< "$current_version"
minor=${ADDR[2]}
minor=$((minor+1))
new_version="${ADDR[0]}.${ADDR[1]}.$minor"
echo "建议的新版本号: $new_version"

# 询问新版本号
read -p "请输入新的版本号 [默认为 $new_version]: " input_version
if [ -z "$input_version" ]; then
  input_version=$new_version
fi
echo "新版本号: $input_version"

# 替换新版本号到config_api.py
sed -i "s/__version = '$current_version'/__version = '$input_version'/g" ./class/core/config_api.py

# 提交代码
git add ./class/core/config_api.py
git commit -m "$input_version"
git push

# 创建版本号的标签并提交
git tag -a "$input_version" -m "$input_version"
git push --tags

echo "版本升级并提交完成。"