
const fs = require("fs");
const mysql = require('mysql');
const readline = require('readline');
const util = require('util');
const exec = util.promisify(require('child_process').exec);

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

async function prompt(question, defaultValue) {
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




let MASTER_HOST = '';
let MASTER_SSH_PORT = null;
let MASTER_ID_RSA = '';
let MASTER_SSH_PRIVATE_KEY = '';
let MASTER_SSH_COMMAND = null;

// let SLAVE_HOST = '127.0.0.1';
// let SLAVE_SSH_PORT = null;

// let SLAVE_MYSQL_PORT = '';
// let SLAVE_MYSQL_USER = 'root';
// let SLAVE_MYSQL_PASS = '';

// let slaveConnection = null;
// let slaveQuery = null;

async function switchMasterSlave() {
  try {
    // 主备服务器加上只读锁
    console.log("|- 正在为主备服务器添加只读锁...");

    // let masterSetDbReadOnlyResult = JSON.parse(await execMasterSync('python3 /www/server/jh-panel/plugins/mysql-apt/index.py set_db_read_only'))
    // if(!masterSetDbReadOnlyResult.status) {
    //   throw new Error("执行主库加锁异常❌");
    // }
    let slaveSetDbReadOnlyResult = JSON.parse(await execLocalSync('python3 /www/server/jh-panel/plugins/mysql-apt/index.py set_db_read_only'))
    if(!slaveSetDbReadOnlyResult.status) {
      throw new Error("执行从库加锁异常❌");
    }
    Logger.success("|- 主备服务器添加只读锁完成✅");

    // 检查从库状态
    console.log("|- 正在检查从库状态 ...");
    let slaveStatusResult = JSON.parse(await execLocalSync('python3 /www/server/jh-panel/plugins/mysql-apt/index.py get_slave_list {page:1,page_size:5}'))
    if (!slaveStatusResult) {
      throw new Error('获取从库状态失败❌')
    }
    let slaveStatus = slaveStatusResult.data[0]
    const { Slave_IO_Running, Slave_SQL_Running, Seconds_Behind_Master } = slaveStatus;

    if (Slave_IO_Running !== 'Yes' || Slave_SQL_Running !== 'Yes') {
      throw new Error("检查异常，从库未运行或同步异常❌");
    }
    Logger.success("|- 从库状态正常✅");

    // 检查数据同步延迟
    console.log("|- 正在检查数据同步延迟...");
    if (Seconds_Behind_Master !== 0) {
      throw new Error(`数据尚未完全同步，从库延迟了 ${Seconds_Behind_Master} 秒❌`);
    } 
    Logger.success("|- 数据无延迟✅");

    let slaveDeleteSlaveResult = JSON.parse(await execLocalSync('python3 /www/server/jh-panel/plugins/mysql-apt/index.py delete_slave'))
    if (!slaveDeleteSlaveResult.status) {
      throw new Error('删除从库失败❌')
    }
    // 设置新主的从库信息
    console.log("|- 正在设置新主的从库信息...");
    let masterAddSlaveResult = JSON.parse(await execMasterSync('python3 /www/server/jh-panel/plugins/mysql-apt/index.py init_slave_status'))
    if(!masterAddSlaveResult.status) {
      throw new Error("添加从库失败❌");
    }
    Logger.success("|- 新主的从库信息设置完成✅");

    // 取消新主的只读锁
    console.log("|- 正在取消新主的只读锁...");
    let slaveSetDbReadWriteResult = JSON.parse(await execLocalSync('python3 /www/server/jh-panel/plugins/mysql-apt/index.py set_db_read_write'))
    if(!slaveSetDbReadWriteResult.status) {
      throw new Error("取消新主的只读锁异常❌");
    }
    Logger.success("|- 取消新主的只读锁完成✅");

    Logger.success("主从切换完毕✅");

  } catch (error) {
    console.error(error.message);
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
      if (error) {
        console.error(`执行出错: ${error}`);
        return;
      }
      if (stderr) {
        console.error(`脚本错误: ${stderr}`);
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
      if (error) {
        console.error(`执行出错: ${error}`);
        return;
      }
      if (stderr) {
        console.error(`脚本错误: ${stderr}`);
        return;
      }
      resolve(stdout)
    });
  });
}



(async () => {
  // 获取主SSH信息
  try {
    let masterSSHResult = JSON.parse(await execLocalSync('python3 /www/server/jh-panel/plugins/mysql-apt/index.py get_slave_ssh_list {page:1,page_size:5,tojs:getSlaveSSHPage}'))
    let masterConfig = masterSSHResult.data[0] 
    MASTER_HOST = masterConfig.ip
    MASTER_SSH_PORT = masterConfig.port
    MASTER_ID_RSA = masterConfig.id_rsa
    MASTER_SSH_PRIVATE_KEY = "/root/.ssh/id_rsa"
    if (MASTER_ID_RSA && MASTER_ID_RSA.indexOf('BEGIN OPENSSH PRIVATE KEY') > -1) {
      MASTER_SSH_PRIVATE_KEY = "/tmp/t_ssh.txt"
      fs.writeFileSync(MASTER_SSH_PRIVATE_KEY, MASTER_ID_RSA.replace('\\n', '\n'))
    }
  } catch (error) {
    throw new Error(`获取主SSH信息失败❌`);
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
  MASTER_SSH_COMMAND = `ssh root@${MASTER_HOST} -p ${MASTER_SSH_PORT} -i ${MASTER_SSH_PRIVATE_KEY} -o StrictHostKeyChecking=no`;
  
  // slaveConnection = mysql.createConnection({
  //   host: '127.0.0.1',
  //   port: SLAVE_MYSQL_PORT,
  //   user: SLAVE_MYSQL_USER,
  //   password: SLAVE_MYSQL_PASS,
  //   multipleStatements: true
  // });
  
  // slaveQuery = util.promisify(slaveConnection.query).bind(slaveConnection);

  await switchMasterSlave();
  rl.close();
})();


