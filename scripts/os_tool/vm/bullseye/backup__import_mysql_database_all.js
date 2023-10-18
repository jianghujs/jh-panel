// 引入所需模块

const mysql = require('mysql');
const Importer = require('mysql-import');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

const MAX_RETRY = 10; // 最大重试次数

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

const connectionConfig = {
  host: '127.0.0.1',
  port: '33067',
  user: 'root',
  password: ''
};

// 文件路径列表
const defaultSqlFileDir = path.join(__dirname, './sql')
var sqlFileDir = defaultSqlFileDir;

// 初始化非视图SQL和视图SQL
let sqlNonViewList = [];
let sqlViewList = [];

async function prompt(question, defaultValue) {
  return new Promise((resolve) => {
      rl.question(question, (answer) => {
          resolve(answer || defaultValue);
      });
  });
}

async function confirmTip(tip) {
  return new Promise((resolve) => {
      rl.question(tip, (answer) => {
          if (answer.toLowerCase() === 'yes' || answer.toLowerCase() === 'y') {
              resolve();
          } else {
            process.exit(0);
          }
      });
  });
}

// 切分sql文件
async function splitSqlFileDirFile(filePaths) {


  for( let i = 0; i < filePaths.length; i++ ) {
      const filePath = filePaths[i];
      let fileName =  /(?:\d+\.)?(.+)\.sql/.exec(filePath)[1];
      // 读取SQL文件
      const fullPath = path.join(sqlFileDir, filePath);
      const sqlContent = fs.readFileSync(fullPath, 'utf8');

      // 从SQL文件中提取视图
      const viewRegex = /CREATE\s+OR\s+REPLACE\s+VIEW\s+.*?;\s*$/gims;
      const fileViews = sqlContent.match(viewRegex);
      sqlViewList = sqlViewList.concat((fileViews || []).map(view => {
        let viewName = view.match(/VIEW `(.+?)`/)[1];
        return {
          database: fileName, 
          viewName,
          sql: view,
        };
      }));

      // 获取非视图SQL
      const nonViewSql = sqlContent.replace(viewRegex, '').trim();
      sqlNonViewList.push({
        database: fileName,
        sql: nonViewSql
      });

  }
  
  return {
    sqlNonViewList,
    sqlViewList
  }
}


async function initDatabase({database}) {
  const mysqlConnection = mysql.createConnection(connectionConfig);
  await new Promise((resolve, reject) => {
      mysqlConnection.query(`CREATE DATABASE IF NOT EXISTS \`${database}\` default character set utf8mb4 collate utf8mb4_bin`, function (error, results, fields) {
          if (error) {
              reject(error);
          }
          console.log(`创建${database}成功`)
          resolve(results);
      });
  });
}

async function importSql({ database, sqlFile }) {
  const importer = new Importer({...connectionConfig, database});
  const startTime = new Date().getTime();
  importer.onProgress(progress => {
      const percent = Math.floor(progress.bytes_processed / progress.total_bytes * 10000) / 100;
      console.log(`导入${database}进行中, 进度: ${percent}%, sqlFile: ${sqlFile}`);
  });

  await new Promise((resolve, reject) => {
      importer.import(sqlFile).then(() => {
          const files_imported = importer.getImported();
          resolve(files_imported);
          const endTime = new Date().getTime();
          console.log(`导入${database}成功, useTime: ${(endTime - startTime)/1000.00}/s, sqlFile: ${sqlFile}`);
      }).catch(err => {
          console.error(`导入${database}!!!!异常!!!!!, sqlFile: ${sqlFile}`, err);
          reject(err);
      });
  });
}


async function importSqlNonViewList() {
  const tmpDir = path.join(sqlFileDir, 'tmp');
  if (!fs.existsSync(tmpDir)) {
    fs.mkdirSync(tmpDir);
    console.log("已自动创建目录" + tmpDir)
  } 
  for( let i = 0; i < sqlNonViewList.length; i++ ) {
    const { database, sql } = sqlNonViewList[i];
    // 写入临时文件
    const tempFilePath = path.join(tmpDir, `nonViewTemp-${database}.sql`);
    fs.writeFileSync(tempFilePath, sql, 'utf8');
    await initDatabase({database});
    await importSql({ database, sqlFile: tempFilePath });
    fs.unlinkSync(tempFilePath);
  }
  fs.rmdirSync(tmpDir);
}

      
// 处理视图的函数
async function importSqlViewList() {
  return new Promise(async (resolve) => {
    if (sqlViewList.length === 0) {
      console.log("全部数据库文件导入成功！")
      process.exit(0);
    }
    const view = sqlViewList.shift();
    // 添加重试机制
    view.retryCount = view.retryCount || 0; // 初始化重试计数器
    // 创建数据库连接
    const connection = await mysql.createConnection({...connectionConfig, database: view.database});
    await connection.query(view.sql, async function (error, results, fields) {
      view.retryCount++;
      if (error) {
        console.log(`\x1b[33mView ${view.database}.${view.viewName} creat failed. ==> ${error.message}, will retry again later(${view.retryCount}).\x1b[0m`);
        if(view.retryCount < MAX_RETRY) {
          sqlViewList.push(view);
        } else {
          console.log(`\x1b[31mView ${view.database}.${view.viewName} retry ${view.retryCount} times failed. ==> ${error.message}\x1b[0m`);
          process.exit(0);
        }
      } else {      
        console.log(`View ${view.database}.${view.viewName} created successfully.`);
      }
      connection.end();
      await importSqlViewList();
    });
  });
};

(async () => {
  console.log(`---------数据库批量导入工具-----------`);

  sqlFileDir = await prompt(`请输入数据库文件位置（默认为：${defaultSqlFileDir}）：`, defaultSqlFileDir);
  if (!fs.existsSync(sqlFileDir)) {
    console.log("目录不存在");
    process.exit(0);
  } 
  const filePaths = fs.readdirSync(sqlFileDir).filter(file => file.endsWith('.sql') && !file.startsWith('nonViewTemp-'));
  
  connectionConfig.host = await prompt(`请输入数据库IP地址（默认为：${connectionConfig.host}）：`, connectionConfig.host);
  connectionConfig.port = await prompt(`请输入数据库端口（默认为：${connectionConfig.port}）：`, connectionConfig.port);
  connectionConfig.user = await prompt(`请输入数据库用户名（默认为：${connectionConfig.user}）：`, connectionConfig.user);
  connectionConfig.password = await prompt(`请输入数据库密码${connectionConfig.password? '默认为：' + connectionConfig.password: ''}：`, connectionConfig.password);

  await confirmTip(`数据库文件列表：\x1b[31m\n${filePaths.join('\n')}\x1b[0m\n数据库URL：\n\x1b[31m${connectionConfig.host}:${connectionConfig.port}${connectionConfig.port != '3306'? '（检测到非本地数据库，请谨慎操作！！！）': ''}\x1b[0m\n确定要创建并导入到数据库吗？[y/n] `);
  if(connectionConfig.port != '3306') {
    await confirmTip(`请再次确定要导入到\x1b[31m${connectionConfig.host}:${connectionConfig.port}\x1b[0m吗？确认后将覆盖数据，请做好数据备份！[y/n] `);
  }

  await splitSqlFileDirFile(filePaths);
  await importSqlNonViewList();
  await importSqlViewList();
  
})();