
check_and_install()
{
  package=$1
  # 检查是否安装
  if ! command -v $package &> /dev/null; then
      echo "${package}未安装，正在尝试自动安装..."
      apt-get update
      apt-get install $package -y
      if ! command -v $package &> /dev/null; then
          echo "安装${package}失败，请手动安装后再运行脚本。"
          exit 1
      fi
  fi
}

# check_and_install "mydumper"