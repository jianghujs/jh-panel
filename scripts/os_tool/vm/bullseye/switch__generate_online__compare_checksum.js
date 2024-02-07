'use strict';

const Knex = require('knex');
const readline = require('readline');
const fs = require("fs");
const path = require("path");
const { exec } = require('child_process');
const { rejects } = require('assert');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

const connectionA = {
  host: '127.0.0.1',
  port: '33067',
  user: 'root',
  password: ''
};

const connectionB = {
  host: process.env.REMOTE_IP || '',
  port: '33067',
  user: 'root',
  password: ''
};

// 不检查的库
let ignoreDatabases = [];

const logFile = path.join('/tmp', 'checksum.log');

async function prompt(question, defaultValue) {
  return new Promise((resolve) => {
      rl.question(question, (answer) => {
          resolve(answer || defaultValue);
      });
  });
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

    console.log("")
    console.log(`|- 开始计算${connection.host}...`)
    for (let database of databases) {
      
      if (ignoreDatabases.includes(database)) {
        continue;
      }
      console.log('|------------------ ' + database + ' ---------------');
      let currentDatabaseChecksum = 0;
        const tables = (await knex("TABLES").select("*")).filter((o) => o.TABLE_SCHEMA === database && o.TABLE_COMMENT !== "VIEW")
        .map((o) => o.TABLE_NAME);

        checksums[database] = {};
        for (let table of tables.filter((o) => o.indexOf('view') == -1)) {
            const checksumRaw = await knex.raw(`CHECKSUM TABLE \`${database}\`.\`${table}\``);
            const checksum = checksumRaw[0][0].Checksum;
            console.log('|- ' + database + '.' + table + ': ' + checksum + '');

            checksums[database][table] = checksum;
            currentDatabaseChecksum += checksum;
        }
        checksumTotal += currentDatabaseChecksum;
        console.log('|- Total : ' + currentDatabaseChecksum);   
    }
    console.log("----------------------------------------------------------")
    console.log(`- IP：${connection.host}`)
    console.log(`- All Database Total：${checksumTotal}`)
    console.log("----------------------------------------------------------")
    console.log("")

    await knex.destroy();

    return checksums;
}

function findDifferences(obj1, obj2, prefix = '') {
  const diffs = [];
  const keys = new Set([...Object.keys(obj1), ...Object.keys(obj2)]);

  keys.forEach(key => {
    const path = prefix ? `${prefix}.${key}` : key;

    if (typeof obj1[key] === 'object' && typeof obj2[key] === 'object') {
      diffs.push(...findDifferences(obj1[key], obj2[key], path));
    } else if (obj1[key] !== obj2[key]) {
      diffs.push(path);
    }
  });

  return diffs;
}


(async () => {
  try {
    let mysql_info = await execSync('python3 /www/server/jh-panel/plugins/mysql-apt/index.py get_db_list_page') 
    let password =  JSON.parse(mysql_info).info.root_pwd
    connectionA.password = password
    connectionB.password = password

  } catch (error) {
    console.error('获取数据库信息失败')
  }

    // 本地数据库信息
    // connectionA.host = await prompt(`请输入当前数据库IP地址（默认为：${connectionA.host}）：`, connectionA.host);
    // connectionA.port = await prompt(`请输入当前数据库端口（默认为：${connectionA.port}）：`, connectionA.port);
    // connectionA.user = await prompt(`请输入当前数据库用户名（默认为：${connectionA.user}）：`, connectionA.user);
    // connectionA.password = await prompt(`请输入当前数据库密码${connectionA.password? ('（默认为：' + (connectionA.password? '当前mysql密码': '空') + '）'): ''}：`, connectionA.password);

    // 目标数据库信息
    // connectionB.host = await prompt(`请输入目标数据库IP地址（默认为：${connectionB.host}）：`, connectionB.host);
    // connectionB.port = await prompt(`请输入目标数据库端口（默认为：${connectionB.port}）：`, connectionB.port);
    // connectionB.user = await prompt(`请输入目标数据库用户名（默认为：${connectionB.user}）：`, connectionB.user);
    // connectionB.password = await prompt(`请输入目标数据库密码${connectionB.password? ('（默认为：' + (connectionB.password? '当前mysql密码': '空') + '）'): ''}：`, connectionB.password);

    const defaultIgnoreDeatabasesInput = "mysql,performance_schema,sys,information_schema,test";
    // const ignoreDatabasesInput = await prompt(`请输入需要忽略的库，多个用英文逗号隔开（默认为${defaultIgnoreDeatabasesInput || '空'}）：`, defaultIgnoreDeatabasesInput);
    const ignoreDatabasesInput = defaultIgnoreDeatabasesInput;
    ignoreDatabases = ignoreDatabasesInput.split(",").map(database => database.trim());

    const checksumA = await getDatabaseChecksum(connectionA);
    const checksumB = await getDatabaseChecksum(connectionB);
    const checksumDiff = findDifferences(checksumA, checksumB).sort();

    fs.writeFileSync('/tmp/compare_checksum_diff', `checksum_diff=${checksumDiff.join(',')}`);
    rl.close();
})();
