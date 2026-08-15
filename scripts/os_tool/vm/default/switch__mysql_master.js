
const fs = require("fs");
const readline = require('readline');
const util = require('util');
const exec = util.promisify(require('child_process').exec);

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

async function prompt(question, defaultValue) {
  if (process.env.HA_MANAGER_AUTO_CONFIRM === '1') {
    console.log(`${question} y`);
    return 'y';
  }
  return new Promise((resolve) => {
      rl.question(question, (answer) => {
          resolve(answer || defaultValue);
      });
  });
}

const Logger = {
  success: (content) => {
    console.log(`\x1b[32m${content}\x1b[0m`);
  },
  error: (content) => {
    console.log(`\x1b[31m${content}\x1b[0m`);
  },
  info: (content) => {
    console.log(content);
  }
};


function parsePluginJson(raw, step) {
  const text = String(raw || '').trim();
  if (!text) {
    throw new Error(`${step} 返回为空，无法解析插件结果`);
  }
  const lines = text.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
  const jsonLine = lines.reverse().find(line => line.startsWith('{') || line.startsWith('['));
  if (!jsonLine) {
    throw new Error(`${step} 未返回JSON结果: ${text.slice(-800)}`);
  }
  try {
    return JSON.parse(jsonLine);
  } catch (error) {
    throw new Error(`${step} JSON解析失败: ${error.message}; 原始输出: ${text.slice(-800)}`);
  }
}




let MASTER_HOST = '';
let MASTER_SSH_PORT = null;
let MASTER_ID_RSA = '';
let MASTER_SSH_PRIVATE_KEY = '';
let MASTER_SSH_COMMAND = null;

let MASTER_OPT_FLAG = true;

// let SLAVE_HOST = '127.0.0.1';
// let SLAVE_SSH_PORT = null;

// let SLAVE_MYSQL_PORT = '';
// let SLAVE_MYSQL_USER = 'root';
// let SLAVE_MYSQL_PASS = '';

// let slaveConnection = null;
// let slaveQuery = null;

async function _switchMasterSlave() {
  console.log("|- 开始切换主从服务器...");
  // 主备服务器加上只读锁
  console.log("|- 正在为主备服务器添加只读锁...");

  let masterSetDbReadOnlyResult = parsePluginJson(await execMasterSync('python3 /www/server/jh-panel/plugins/mysql-apt/index.py set_db_read_only'), '主库加只读锁')
  if(!masterSetDbReadOnlyResult.status) {
    throw new Error("执行主库加锁异常❌");
  }
  let slaveSetDbReadOnlyResult = parsePluginJson(await execLocalSync('python3 /www/server/jh-panel/plugins/mysql-apt/index.py set_db_read_only'), '从库加只读锁')
  if(!slaveSetDbReadOnlyResult.status) {
    throw new Error("执行从库加锁异常❌");
  }
  Logger.success("|- 主备服务器添加只读锁完成✅");


  let slaveDeleteSlaveResult = parsePluginJson(await execLocalSync('python3 /www/server/jh-panel/plugins/mysql-apt/index.py delete_slave'), '删除从库')
  if (!slaveDeleteSlaveResult.status) {
    throw new Error('删除从库失败❌')
  }
  Logger.success("|- 删除从库完成✅");
  // 设置新主的从库信息
  console.log("|- 正在设置新主的从库信息...");
  let masterAddSlaveResult = parsePluginJson(await execMasterSync('python3 /www/server/jh-panel/plugins/mysql-apt/index.py init_slave_status'), '设置新主的从库信息')
  if(!masterAddSlaveResult.status) {
    throw new Error("添加从库失败❌");
  }
  Logger.success("|- 新主的从库信息设置完成✅");

  // 取消新主的只读锁
  console.log("|- 正在取消新主的只读锁...");
  let slaveSetDbReadWriteResult = parsePluginJson(await execLocalSync('python3 /www/server/jh-panel/plugins/mysql-apt/index.py set_db_read_write'), '取消新主只读锁')
  if(!slaveSetDbReadWriteResult.status) {
    throw new Error("取消新主的只读锁异常❌");
  }
  Logger.success("|- 取消新主的只读锁完成✅");

  Logger.success("主从切换完毕✅");
}

async function _switchSlave() {
  
  console.log("|- 开始将当前服务器提升为主...");
  
  let slaveDeleteSlaveResult = parsePluginJson(await execLocalSync('python3 /www/server/jh-panel/plugins/mysql-apt/index.py delete_slave'), '删除从库')
  if (!slaveDeleteSlaveResult.status) {
    throw new Error('删除从库失败❌')
  }
  Logger.success("|- 删除从库完成✅");
  
  Logger.success("将当前服务器提升为主完毕✅");
}

async function startSwitch() {
  try {

    // 检查从库状态
    console.log("|- 正在检查从库状态 ...");
    let slaveStatusResult = parsePluginJson(await execLocalSync('python3 /www/server/jh-panel/plugins/mysql-apt/index.py get_slave_list {page:1,page_size:5}'), '检查从库状态')
    if (!slaveStatusResult || slaveStatusResult.status === false) {
      console.log(`获取从库状态失败：${slaveStatusResult && slaveStatusResult.msg ? slaveStatusResult.msg : '未知错误'}❌`);
      let ignore_error_choise = await prompt("继续提升当前库为主库吗？(默认n）[y/n]:", 'n');
      if (ignore_error_choise.toLowerCase() !== 'y') {
        throw new Error('获取从库状态失败，操作已取消❌')
      }
      MASTER_OPT_FLAG = false;
    } else if (!slaveStatusResult.data || !slaveStatusResult.data.length) {
      console.log("未检测到从库状态，可能当前库已经不是从库或复制未配置❌");
      let ignore_error_choise = await prompt("继续提升当前库为主库吗？(默认n）[y/n]:", 'n');
      if (ignore_error_choise.toLowerCase() !== 'y') {
        throw new Error('未检测到从库状态，操作已取消❌')
      }
      MASTER_OPT_FLAG = false;
    }

    if (MASTER_OPT_FLAG) {
      let slaveStatus = slaveStatusResult.data[0]
      const { Slave_IO_Running, Slave_SQL_Running, Seconds_Behind_Master } = slaveStatus;

      if (Slave_IO_Running !== 'Yes' || Slave_SQL_Running !== 'Yes') {
        console.log("检查异常，从库未运行或同步异常❌");
        let ignore_error_choise = await prompt("继续提升当前库为主库吗？(默认n）[y/n]:", 'n');
        if (ignore_error_choise.toLowerCase() !== 'y') {
          throw new Error('从库未运行或同步异常，操作已取消❌')
        }
        MASTER_OPT_FLAG = false;
      } else {
        Logger.success("|- 从库状态正常✅");
        // 检查数据同步延迟
        console.log("|- 正在检查数据同步延迟...");
        if (Seconds_Behind_Master !== 0) {
          throw new Error(`数据尚未完全同步，从库延迟了 ${Seconds_Behind_Master} 秒❌`);
        } 
        Logger.success("|- 数据无延迟✅");
      }
    }

    switch(MASTER_OPT_FLAG) {
      case true:
        await _switchMasterSlave();
        break;
      case false:
        await _switchSlave();
        break;
      default:
        throw new Error("MASTER_OPT_FLAG 未知状态");
    }

  } catch (error) {
    console.error(error.message);
    process.exit(1);
  } 
}

async function execMasterSync(cmd) {
  cmd = `
pushd /www/server/jh-panel > /dev/null
${cmd}
popd > /dev/null
  `
  cmd = cmd.replace(';', '\n')
  return new Promise((resolve) => {
    exec(`${MASTER_SSH_COMMAND} "${cmd}"`, (error, stdout, stderr) => {
      if (stderr) {
        console.error(`脚本警告: ${stderr}`);
      }
      if (error) {
        console.error(`执行出错: ${error}`);
        resolve(stdout || '');
        return;
      }
      resolve(stdout)
    });
  })
}

async function execLocalSync(cmd) {
  return new Promise((resolve) => {
    exec(`
pushd /www/server/jh-panel > /dev/null\n
${cmd}\n
popd > /dev/null
    `, (error, stdout, stderr) => {
      if (stderr) {
        console.error(`脚本警告: ${stderr}`);
      }
      if (error) {
        console.error(`执行出错: ${error}`);
        resolve(stdout || '');
        return;
      }
      resolve(stdout)
    });
  });
}



(async () => {
  // 获取主SSH信息
  try {
    let masterSSHResult = parsePluginJson(await execLocalSync('python3 /www/server/jh-panel/plugins/mysql-apt/index.py get_slave_ssh_list {page:1,page_size:5,tojs:getSlaveSSHPage}'), '获取主库SSH信息')
    if (masterSSHResult && masterSSHResult.status && masterSSHResult.data && masterSSHResult.data.length) {
      let masterConfig = masterSSHResult.data[0]
      MASTER_HOST = masterConfig.ip
      MASTER_SSH_PORT = masterConfig.port
      MASTER_ID_RSA = masterConfig.id_rsa
      MASTER_SSH_PRIVATE_KEY = "/root/.ssh/id_rsa"
      if (MASTER_ID_RSA && MASTER_ID_RSA.indexOf('BEGIN OPENSSH PRIVATE KEY') > -1) {
        MASTER_SSH_PRIVATE_KEY = "/tmp/t_ssh.txt"
        fs.writeFileSync(MASTER_SSH_PRIVATE_KEY, MASTER_ID_RSA.replace(/\\n/g, '\n'))
        await execLocalSync(`chmod 600 ${MASTER_SSH_PRIVATE_KEY}`)
      }
    } else {
      console.log("|- 未获取到主库SSH信息，按无旧主场景处理，仅将当前库提升为主");
      MASTER_OPT_FLAG = false;
    }
  } catch (error) {
    console.log(`|- 获取主SSH信息失败，按无旧主场景处理，仅将当前库提升为主: ${error.message}`);
    MASTER_OPT_FLAG = false;
  }

  // // 获取数据库密码
  // try {
  //   let mysql_info = await execLocalSync('python3 /www/server/jh-panel/plugins/mysql-apt/index.py get_db_list_page') 
  //   SLAVE_MYSQL_PASS =  JSON.parse(mysql_info).info.root_pwd
  //   let myport = (await execLocalSync('python3 /www/server/jh-panel/plugins/mysql-apt/index.py my_port')).trim()
  //   SLAVE_MYSQL_PORT = myport

  // } catch (error) {
  //   throw new Error(`获取数据库信息失败❌`);
  // }
  
  // 设置 MASTER_SSH 命令
  if (MASTER_OPT_FLAG) {
    MASTER_SSH_COMMAND = `ssh root@${MASTER_HOST} -p ${MASTER_SSH_PORT} -i ${MASTER_SSH_PRIVATE_KEY} -o StrictHostKeyChecking=no`;
  }
  
  // slaveConnection = mysql.createConnection({
  //   host: '127.0.0.1',
  //   port: SLAVE_MYSQL_PORT,
  //   user: SLAVE_MYSQL_USER,
  //   password: SLAVE_MYSQL_PASS,
  //   multipleStatements: true
  // });
  
  // slaveQuery = util.promisify(slaveConnection.query).bind(slaveConnection);

  await startSwitch();
  rl.close();
})();
