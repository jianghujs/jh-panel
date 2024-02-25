

CONFIG_FILE="/www/server/mysql-apt/etc/my.cnf"
# 检查文件是否存在
if [ ! -f "$CONFIG_FILE" ]; then
    echo "配置文件不存在: $CONFIG_FILE"
    exit 1
fi

# 开启只读
enable_readonly()
{
  TEMP_FILE=$(mktemp)
  awk '
  BEGIN {found_mysqld=0; already_added=0;}
  /^\[mysqld\]/ {
      found_mysqld=1;
      print;
      next;
  }
  found_mysqld && /^\[/ {
      if (!already_added) {
          print "read_only=on";
          print "super_read_only=on";
          already_added=1;
      }
      found_mysqld=0;
  }
  found_mysqld && /read_only=on/ {already_added=1;}
  found_mysqld && /super_read_only=on/ {already_added=1;}
  {print;}
  END {
      if (found_mysqld && !already_added) {
          print "read_only=on";
          print "super_read_only=on";
      }
  }' $CONFIG_FILE > $TEMP_FILE
  mv $TEMP_FILE $CONFIG_FILE
  echo "ok"
}

# enable_readonly


# 关闭只读
disable_readonly()
{
  TEMP_FILE=$(mktemp)
  awk '!/^\s*(read_only|super_read_only)\s*=/' $CONFIG_FILE > $TEMP_FILE
  mv $TEMP_FILE $CONFIG_FILE
  echo "ok"
}

# disable_readonly