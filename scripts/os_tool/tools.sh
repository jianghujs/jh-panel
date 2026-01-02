
# 下载并执行脚本的函数
download_and_run() {
    local script_name=$1
    if [ "$USE_PANEL_SCRIPT" == "true" ]; then 
      # echo "|- 正在运行  $SCRIPT_BASE/${script_name}..."
      bash $SCRIPT_BASE/${script_name} ${@:2}
    else
      # echo "|- 正在下载并运行  ${URLBase}/${script_name}..."
      wget -nv -O /tmp/vm_${script_name} ${URLBase}/${script_name}
      bash /tmp/vm_${script_name} ${@:2}
    fi    
}

download_and_run_node() {
    local script_name=$1
    local script_path=""
    if [ "$USE_PANEL_SCRIPT" == "true" ]; then 
      pushd $SCRIPT_BASE > /dev/null
      script_path=$SCRIPT_BASE/${script_name}
    else
      wget -nv -O /tmp/package.json ${URLBase}/package.json
      pushd /tmp/ > /dev/null
      script_path=/tmp/vm_${script_name}
      wget -nv -O $script_path ${URLBase}/${script_name}
    fi    
    
    # echo "|- 正在运行  $script_path..."
    source /root/.bashrc

    # 检查依赖是否安装
    package_json_current_checksum=$(md5sum "package.json" | awk '{print $1}')
    package_json_old_checksum=""
    if [ -f "package.json.checksum" ]; then
      package_json_old_checksum=$(cat "package.json.checksum")
    fi

    if [ ! -d "node_modules" ] || [ "$package_json_current_checksum" != "$package_json_old_checksum" ]; then
      echo "正在运行 npm install..."
      npm install
      echo $package_json_current_checksum > "package.json.checksum"
    else
      echo "跳过 npm install。"
    fi

    node ${script_path} ${@:2}
    popd > /dev/null
}

download_and_run_py() {
    local script_name=$1
    local script_path=""
    local requirements_path=""
    local python_bin=${PYTHON_BIN:-python3}

    if ! command -v "$python_bin" > /dev/null 2>&1; then
        echo "未检测到 ${python_bin}，请先安装 Python 环境。"
        return 1
    fi

    if [ "$USE_PANEL_SCRIPT" == "true" ]; then 
      pushd $SCRIPT_BASE > /dev/null
      script_path=$SCRIPT_BASE/${script_name}
      requirements_path=$SCRIPT_BASE/requirements.txt
    else
      pushd /tmp/ > /dev/null
      script_path=/tmp/vm_${script_name}
      wget -nv -O $script_path ${URLBase}/${script_name}
      if wget -q --spider ${URLBase}/requirements.txt 2>/dev/null; then
        requirements_path=/tmp/vm_requirements.txt
        wget -nv -O $requirements_path ${URLBase}/requirements.txt
      fi
    fi

    if [ -n "$requirements_path" ] && [ -f "$requirements_path" ]; then
      echo "正在运行 pip install -r requirements.txt..."
      $python_bin -m pip install -r "$requirements_path"
    fi

    $python_bin "$script_path" ${@:2}
    popd > /dev/null
}

ensure_jq_installed() {
    if command -v jq >/dev/null 2>&1; then
        return 0
    fi
    echo "jq 未安装，正在尝试自动安装..."
    if command -v apt-get >/dev/null 2>&1; then
        apt-get update
        apt-get install -y jq
    else
        echo "当前环境不支持自动安装 jq，请手动安装后重试。"
        return 1
    fi
    if ! command -v jq >/dev/null 2>&1; then
        echo "安装 jq 失败，请手动安装后再运行脚本。"
        return 1
    fi
    return 0
}

panel_python_call() {
    local label="$1"
    shift
    local panel_dir="${PANEL_DIR:-/www/server/jh-panel}"
    local python_bin="${PYTHON_BIN:-python3}"
    local output
    if ! output=$(cd "$panel_dir" && "$python_bin" "$@" 2>&1); then
        echo "[$label] 执行失败：$output" >&2
        return 1
    fi
    printf '%s\n' "$output"
}
