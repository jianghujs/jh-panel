
import json
import time

# 节流池文件
debounce_commands_pool_file = 'data/debounce_commands_pool.json'

# 读取节流池
def read_debounce_commands_pool():
    with open(debounce_commands_pool_file, 'r') as file:
        return json.load(file)

# 写入节流池
def write_debounce_commands_pool(debounce_commands_pool):
    with open(debounce_commands_pool_file, 'w') as file:
        json.dump(debounce_commands_pool, file)
 
# 添加节流命令
def set_debounce_command(command, debounce_time):
    debounce_commands_pool = read_debounce_commands_pool()
    # 查找是否存在相同命令
    exist_command = False
    for index, item in enumerate(debounce_commands_pool):
        if item['command'] == command:
            # 如果存在相同命令，则更新时间
            debounce_commands_pool[index]['time'] = time.time()
            exist_command = True
            return
    # 如果不存在相同命令，则添加
    if not exist_command:
      debounce_commands_pool.append({
          'command': command,
          'seconds_to_run': debounce_time,
          'time': time.time()
      })
    write_debounce_commands_pool(debounce_commands_pool)
    
# set_debounce_command('systemctl restart lsyncd', 3)