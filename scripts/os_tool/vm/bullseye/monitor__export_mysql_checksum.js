'use strict';

const Knex = require('knex');
const readline = require('readline');
const fs = require("fs");
const path = require("path");

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

const connection = {
  host: '127.0.0.1',
  port: '33067',
  user: 'root',
  password: ''
};

// 不检查的库
let ignoreDatabases = [];

const logFile = path.join('/tmp', 'checksum.log');
let writeLog = true;

async function prompt(question, defaultValue) {
  return new Promise((resolve) => {
      rl.question(question, (answer) => {
          resolve(answer || defaultValue);
      });
  });
}


// 获取要用于计算 checksum 的字段
async function prepareColumns(knex, database, table) {
  const columnList = await knex('INFORMATION_SCHEMA.COLUMNS')
    .where({
      TABLE_SCHEMA: database,
      TABLE_NAME: table,
    })
    .select('COLUMN_NAME as columnName', 'DATA_TYPE as dataType');
  let releventColumns = columnList.filter(column =>
    column.columnName !== 'id'
  ).map(column => {
    if (column.dataType === 'varchar' || column.dataType.includes('text')) {
      return {
        name: column.columnName,
        // 处理 null 字段
        sql: `coalesce(\`${column.columnName}\`,'<null>')`,
      };
    }
    return {
      name: column.columnName,
      // 处理 null 字段
      // 处理非 char 字段
      sql: `coalesce(cast(\`${column.columnName}\` as char),'<null>')`,
    };
  });
  return releventColumns;
}

async function getDatabaseChecksum(connection) {
    const knex = Knex({
        client: 'mysql',
        connection: {
          ...connection,
          database: "information_schema",
        },
    });

    const databasesRaw = await knex.raw("SHOW DATABASES");
    const databases = databasesRaw[0].map(row => row.Database);

    let checksums = {};
    let checksumTotal = 0;

    for (let database of databases) {
      
      if (ignoreDatabases.includes(database)) {
        continue;
      }
      Logger.info('|------------------ 开始计算' + database + ' ---------------');
      let currentDatabaseChecksum = 0;
        const tables = (await knex("TABLES").select("*")).filter((o) => o.TABLE_SCHEMA === database && o.TABLE_COMMENT !== "VIEW")
        .map((o) => o.TABLE_NAME);

        checksums[database] = {};
        for (let table of tables.filter((o) => o.indexOf('view') == -1)) {
            // 计算checksum

            const checksumRaw = await knex.raw(`CHECKSUM TABLE \`${database}\`.\`${table}\``);
            const checksum = checksumRaw[0][0].Checksum;
            Logger.info('|- ' + database + '.' + table + ': ' + checksum + '');

            // let releventColumns = await prepareColumns(knex, database, table);
            // const [{ checksum }] = await knex(table)
            // .select(knex.raw('count(*) as count, sum(cast(conv(substring(md5(concat('
            //   + releventColumns.map(o => o.sql).join(',') +
            //   ')), 18), 16, 10) as unsigned)) as checksum'));
            // Logger.info('|- ' + database + '.' + table + ': ' + checksum + '');

            checksums[database][table] = checksum;
            currentDatabaseChecksum += checksum;
        }
        checksumTotal += currentDatabaseChecksum;
        Logger.info('|- ' + database + ': ' + currentDatabaseChecksum, true);   
    }
    Logger.info("|- All Database Total：" + checksumTotal, true);  

    await knex.destroy();

    return checksumTotal;
}


const Logger = {
  clear: () => {
    fs.writeFileSync(logFile, '');
  },
  info: (content, echo = false) => {
    if (!writeLog) {
      return; 
    }
    if (!fs.existsSync(logFile)) {
      fs.writeFileSync(logFile, '');
    }
    const log = fs.readFileSync(logFile, 'utf8');
    fs.writeFileSync(logFile, log + '\n' + content);
    if (echo) {
      console.log(content);
    }
  }
};

(async () => {
    console.log(`---------数据库checksum检查工具-----------`);

    connection.host = await prompt(`请输入数据库IP地址（默认为：${connection.host}）：`, connection.host);
    connection.port = await prompt(`请输入数据库端口（默认为：${connection.port}）：`, connection.port);
    connection.user = await prompt(`请输入数据库用户名（默认为：${connection.user}）：`, connection.user);
    connection.password = await prompt(`请输入数据库密码${connection.password? ('（默认为：' + connection.password + '）'): ''}：`, connection.password);

    const defaultIgnoreDeatabasesInput = "mysql,performance_schema,sys,information_schema,test";
    const ignoreDatabasesInput = await prompt(`请输入需要忽略的库，多个用英文逗号隔开（默认为${defaultIgnoreDeatabasesInput || '空'}）：`, defaultIgnoreDeatabasesInput);
    ignoreDatabases = ignoreDatabasesInput.split(",").map(database => database.trim());
    
    const writeLogInput = await prompt(`需要将checksum的结果写入到${logFile}吗（默认y）[y/n]？ `, 'y');
    if (writeLogInput.toLowerCase() == 'y') {
      writeLog = true;
      Logger.clear();
    } else {
      writeLog = false;
    }

    console.log("正在计算checksum...")
    const checksum = await getDatabaseChecksum(connection);

    console.log("")
    console.log("===========================Checksum计算完毕✅==========================")
    console.log(`- Total：${checksum}`)
    console.log("---------------------------后续操作指引❗❗----------------------------")
    console.log(`如果你要保证两个服务器的数据库是一致的，请先确保两个服务器执行此脚本得到的Total是一致的，如果不一致，请对比两边的${logFile}中每个表的checksum值`)
    console.log("=====================================================================")
    rl.close();
    setTimeout(() => {
      process.exit(0);
    }, 3000)
})();
