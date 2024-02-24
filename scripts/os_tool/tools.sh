
prompt()
{
  tip=$1
  local _resultvar=$2
  local default_choice=$3
  echo -ne "\033[1;32m?\033[0m \033[1m${tip}\033[0m"
  read choice
  choice=${choice:-$default_choice}
  eval $_resultvar="'$choice'"
}

# prompt "确认要执行吗？" choice "y"
# echo "$choice"
# exit 0


show_error()
{
  tip=$1
  echo -e "\033[1;31m× ${tip}\033[0m"
}

# show_error "error"

show_info()
{
  echo -e "\033[1;32m$1\033[0m"
}

# show_info "info"