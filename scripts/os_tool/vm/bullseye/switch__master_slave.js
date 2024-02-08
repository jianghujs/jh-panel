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


let MASTER_HOST = process.env.REMOTE_IP || '';
let MASTER_PORT = 33067;
let SLAVE_HOST =  process.env.LOCAL_IP || '';
let SLAVE_PORT = 33067;
let SLAVE_USER = 'BwciBS';
let SLAVE_PASS = 'cBcSheKeBBLrbCtW';
let MYSQL_USER = 'root';
let MYSQL_PASS = '';

let MYSQLADMIN_COMMAND = null;

let masterConnection = null;
let slaveConnection = null;
let masterQuery = null;
let slaveQuery = null;

async function switchMasterSlave() {
  try {
    // 主备服务器加上只读锁
    console.log("|- 正在为主备服务器添加只读锁...");
    await masterQuery("FLUSH TABLES WITH READ LOCK; SET GLOBAL read_only = ON; FLUSH PRIVILEGES;");
    await slaveQuery("FLUSH TABLES WITH READ LOCK; SET GLOBAL read_only = ON; FLUSH PRIVILEGES;");

    // 检查从库状态
    console.log("|- 正在检查从库状态 ...");
    const slaveStatus = await slaveQuery("SHOW SLAVE STATUS;");
    const { Slave_IO_Running, Slave_SQL_Running, Seconds_Behind_Master } = slaveStatus[0];

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

    // 停止从库
    console.log("|- 正在停止从库...");
    await exec(`${MYSQLADMIN_COMMAND} -h ${SLAVE_HOST} stop-slave`);
    // 获取从库日志文件位置
    console.log(`|- 正在获取从库信息...`);
    const logFilePos = await slaveQuery("SHOW SLAVE STATUS;");
    const { Master_Log_File, Read_Master_Log_Pos } = logFilePos[0];
    console.log(`|-- SLAVE LOG_FILE: ${Master_Log_File}`);
    console.log(`|-- SLAVE LOG_POS: ${Read_Master_Log_Pos}`);
    await slaveQuery("RESET SLAVE ALL;");
    Logger.success("|- 停止从库完成✅");

    // 原主库修改为从
    console.log("|- 正在将原主库修改为从...");
    await exec(`${MYSQLADMIN_COMMAND} -h ${MASTER_HOST} stop-slave`);
    await masterQuery("RESET SLAVE ALL;");
    Logger.success("|- 原主库修改为从完成✅");

    // 获取新主库的日志文件和位置
    console.log("|- 正在获取新主库信息...");
    const newMasterStatus = await slaveQuery("SHOW MASTER STATUS;");
    const { File: newMasterLogFile, Position: newMasterLogPos } = newMasterStatus[0];
    console.log(`|-- SLAVE MASTER_LOG_FILE: ${newMasterLogFile}`);
    console.log(`|-- SLAVE MASTER_LOG_POS: ${newMasterLogPos}`);

    // 在原主库上设置新的从库信息
    console.log("|- 正在设置原主库新的从库信息...");
    await masterQuery(`CHANGE MASTER TO MASTER_HOST='${SLAVE_HOST}', MASTER_PORT=${SLAVE_PORT}, MASTER_USER='${SLAVE_USER}', MASTER_PASSWORD='${SLAVE_PASS}', MASTER_LOG_FILE='${newMasterLogFile}', MASTER_LOG_POS=${newMasterLogPos};`);
    await exec(`${MYSQLADMIN_COMMAND} -h ${MASTER_HOST} start-slave`);
    console.log("|- 设置原主库新的从库信息完成✅");

    // 取消新主的只读锁
    console.log("|- 正在取消新主的只读锁...");
    await slaveQuery("UNLOCK TABLES; SET GLOBAL read_only = OFF; FLUSH PRIVILEGES;");
    Logger.success("|- 取消新主的只读锁完成✅");

    Logger.success("主从切换完毕✅");

  } catch (error) {
    console.error(error.message);
  } finally {
    // 关闭数据库连接
    masterConnection.end();
    slaveConnection.end();
  }
}

async function execSync(cmd) {
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
  // 获取数据库密码
  try {
    let mysql_info = await execSync('python3 /www/server/jh-panel/plugins/mysql-apt/index.py get_db_list_page') 
    MYSQL_PASS =  JSON.parse(mysql_info).info.root_pwd
  } catch (error) {
    console.error('获取数据库信息失败')
  }

  // 获取主从密码
  try {
    let slave_user_info_result = await execSync('python3 /www/server/jh-panel/plugins/mysql-apt/index.py get_master_rep_slave_list') 
    let slave_user_info = JSON.parse(slave_user_info_result).data[0]
    SLAVE_USER = slave_user_info.username
    SLAVE_PASS = slave_user_info.password
  } catch (error) {
    console.error('获取数据库信息失败')
  }

  if (!MASTER_HOST || !SLAVE_HOST) {
    // 从数据库信息
    SLAVE_HOST = await prompt(`请输入从数据库IP地址：`, SLAVE_HOST);
    if (!SLAVE_HOST) {
      console.error("|- 从数据库IP地址不能为空");
      process.exit(1);
    }
    SLAVE_PORT = await prompt(`请输入从数据库端口（默认为：${SLAVE_PORT}）：`, SLAVE_PORT);
    
    // 主数据库信息
    MASTER_HOST = await prompt(`请输入主数据库IP地址${MASTER_HOST? ('（默认为：' + MASTER_HOST + '）'): ''}：`, MASTER_HOST);
    if (!MASTER_HOST) {
      console.error("|- 主数据库IP地址不能为空");
      process.exit(1);
    }
    MASTER_PORT = await prompt(`请输入主数据库端口（默认为：${MASTER_PORT}）：`, MASTER_PORT);
    
    // 数据库用户
    MYSQL_USER = await prompt(`请输入数据库用户名（默认为：${MYSQL_USER}）：`, MYSQL_USER);
    MYSQL_PASS = await prompt(`请输入数据库密码${MYSQL_PASS? ('（默认为：' + (MYSQL_PASS? '当前mysql密码': '空') + '）'): ''}：`, MYSQL_PASS);
    
    // 主从同步用户
    SLAVE_USER = await prompt(`请输入主从同步用户名（默认为：${SLAVE_USER}）：`, SLAVE_USER);
    SLAVE_PASS = await prompt(`请输入主从同步用户密码${SLAVE_PASS? ('（默认为：' + (SLAVE_PASS? '当前主从同步密码': '空') + '）'): ''}：`, SLAVE_PASS);
  } 

  // 设置 MySQLADMIN 命令
  MYSQLADMIN_COMMAND = `/www/server/mysql-apt/bin/usr/bin/mysqladmin -u${MYSQL_USER} -p${MYSQL_PASS}`;
  
  // 创建 MySQL 连接
  masterConnection = mysql.createConnection({
    host: MASTER_HOST,
    port: MASTER_PORT,
    user: MYSQL_USER,
    password: MYSQL_PASS,
    multipleStatements: true
  });

  slaveConnection = mysql.createConnection({
    host: SLAVE_HOST,
    port: SLAVE_PORT,
    user: MYSQL_USER,
    password: MYSQL_PASS,
    multipleStatements: true
  });
  
  masterQuery = util.promisify(masterConnection.query).bind(masterConnection);
  slaveQuery = util.promisify(slaveConnection.query).bind(slaveConnection);

  switchMasterSlave();
  rl.close();
})();


