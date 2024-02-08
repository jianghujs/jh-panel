const mysql = require('mysql');
const util = require('util');
const exec = util.promisify(require('child_process').exec);


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


const MASTER_HOST = '192.168.3.63';
const MASTER_PORT = 33067;
const SLAVE_HOST = '192.168.3.73';
const SLAVE_PORT = 33067;

const SLAVE_USER = 'BwciBS';
const SLAVE_PASS = 'cBcSheKeBBLrbCtW';
const MYSQL_USER = 'root';
const MYSQL_PASS = 'deuuKtRfdCPWA9X4';

const MYSQLADMIN_COMMAND = `/www/server/mysql-apt/bin/usr/bin/mysqladmin -u${MYSQL_USER} -p${MYSQL_PASS}`;

// 创建 MySQL 连接
const masterConnection = mysql.createConnection({
  host: MASTER_HOST,
  port: MASTER_PORT,
  user: MYSQL_USER,
  password: MYSQL_PASS,
  multipleStatements: true
});

const slaveConnection = mysql.createConnection({
  host: SLAVE_HOST,
  port: SLAVE_PORT,
  user: MYSQL_USER,
  password: MYSQL_PASS,
  multipleStatements: true
});

// 将 callback-based 方法转换为 Promise-based
const masterQuery = util.promisify(masterConnection.query).bind(masterConnection);
const slaveQuery = util.promisify(slaveConnection.query).bind(slaveConnection);

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
    Logger.success("|- 停止从库完成✅");

    // 获取从库日志文件位置
    console.log(`|- 正在获取从库信息...`);
    const logFilePos = await slaveQuery("SHOW SLAVE STATUS;");
    const { Master_Log_File, Read_Master_Log_Pos } = logFilePos[0];
    console.log(`|-- SLAVE LOG_FILE: ${Master_Log_File}`);
    console.log(`|-- SLAVE LOG_POS: ${Read_Master_Log_Pos}`);

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

switchMasterSlave();
