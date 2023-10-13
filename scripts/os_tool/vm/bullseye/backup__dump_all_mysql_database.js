'use strict';

/**
 * - 如果使用code runner 运行, 则将env配置到 '../.env'
 * - 如果使用node xxx.js 运行, 则将env配置到 './jianghujs-script-util/.env'
 */
const mysqldump = require('mysqldump');
const Knex = require('knex');
const fs = require("fs");
const path = require("path");
const readline = require('readline');

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

/**
 * 导出 sql
 * @param database 数据库
 * @param ignoreTables 不导出的表
 * @param withDataTables 导出数据的表，如 _page 相关表
 * @param clearFields 导出前清除的表的字段
 * @param sqlFile 导出文件
 * @param replace 关键字替换
 * @returns {Promise<void>}
 */
async function dumpSql({ database, tables, ignoreTables, withDataTables, clearFields, sqlFile, replace }) {
    console.log(`|- 开始导出${database}...`);
    connection.database = database;
    const knex = Knex({
        client: 'mysql',
        connection,
    });
    const startTime = new Date().getTime();

    // clear fields
    // for (const tableField of clearFields) {
    //     try {
    //         await knex(tableField.table).update(tableField.field, '');
    //         console.log(`|-- clear ${tableField.table}.${tableField.field} success!`);
    //     } catch (e) {
    //     }
    // }

    const res = await mysqldump({
        connection,
        dump: {
            data: {
                format: false
            },
            schema: {
                table: {
                    dropIfExist: true,
                },
            },
            trigger: {
                dropIfExist: false,
            },
        },
        ignoreTables
    });

    let content = `CREATE DATABASE IF NOT EXISTS \`${database}\` default character set utf8mb4 collate utf8mb4_bin;\nUSE \`${database}\`;\n`;

    const allTable = res.tables.filter((item) => !item.isView);
    let allView = res.tables.filter((item) => item.isView);

    const resTables = [...allTable, ...allView];

    resTables.forEach(tableData => {
        if (tables.length !== 0 && !tables.includes(tableData.name)) {
            return;
        }
        if (ignoreTables.includes(tableData.name)) {
            return;
        }
        if (withDataTables.includes(tableData.name)) {
            content += tableData.schema + '\n' + (tableData.data || '') + '\n' + (tableData.triggers && tableData.triggers.join('\n') || '') + '\n\n\n';
        } else {
            content += tableData.schema + '\n' + (tableData.triggers && tableData.triggers.join('\n') || '') + '\n\n\n';
        }
    });

    replace.forEach((item) => {
        content = content.replace(new RegExp(/DROP TRIGGER IF EXISTS (\w*);/, 'g'), 'DROP TRIGGER IF EXISTS `$1`;');
        content = content.replace(new RegExp(item.key, 'g'), item.value);
    });

    // 干掉init.sql trigger的注释
    content = content.replace(new RegExp(/# ------------------------------------------------------------\n# TRIGGER DUMP FOR: .*?\n# ------------------------------------------------------------\n/, 'g'), "");
    content = content.replace(new RegExp(/# ------------------------------------------------------------\n# DATA DUMP FOR TABLE: .*?\n# ------------------------------------------------------------\n/, 'g'), "");
    fs.writeFileSync(sqlFile, content);
    const endTime = new Date().getTime();
    console.log(`|- 导出${database}完成✅, useTime: ${(endTime - startTime) / 1000.00}/s, sqlFile: ${sqlFile}`);
    await knex.destroy();
}

// 不导出的库
let ignoreDatabases = [];

// 不导出的表
let ignoreTables = [];

// 带数据的表
let withDataTables = [];

// 导出前清理表中的无用字段
let clearFields = [
    { table: '_resource', field: 'requestDemo' }
];
let replace = [
    { key: ' COLLATE utf8mb4_bin', value: '' }
];

// 项目
(async () => {
    console.log(`---------数据库批量导出工具-----------`);

    connection.host = await prompt(`请输入数据库IP地址（默认为：${connection.host}）：`, connection.host);
    connection.port = await prompt(`请输入数据库端口（默认为：${connection.port}）：`, connection.port);
    connection.user = await prompt(`请输入数据库用户名（默认为：${connection.user}）：`, connection.user);
    connection.password = await prompt(`请输入数据库密码${connection.password? '默认为：' + connection.password: ''}：`, connection.password);

    const defaultIgnoreDeatabasesInput = "mysql,performance_schema,sys,information_schema";
    const ignoreDatabasesInput = await prompt(`请输入需要忽略的库，多个用英文逗号隔开（默认为${defaultIgnoreDeatabasesInput || '空'}）：`, defaultIgnoreDeatabasesInput);
    ignoreDatabases = ignoreDatabasesInput.split(",").map(database => database.trim());
    
    const defaultIgnoreTablesInput = "";
    const ignoreTablesInput = await prompt(`请输入需要忽略的表，多个用英文逗号隔开（默认为${defaultIgnoreTablesInput || '空'}）：`, defaultIgnoreTablesInput);
    ignoreTables = ignoreTablesInput.split(",").map(table => table.trim());

    const defaultWithDataTablesInput = "_page,_resource,_constant,_constant_ui,_group,_role,_user_group_role,_user_group_role_page,_user_group_role_resource";
    const withDataTablesInput = await prompt(`请输入需要导出数据的表，多个用英文逗号隔开（默认为：${defaultWithDataTablesInput}）：`, defaultWithDataTablesInput);
    withDataTables = withDataTablesInput.split(",").map(table => table.trim());
    
    const knex = Knex({
        client: 'mysql',
        connection,
    });
    const databasesRaw = await knex.raw("SHOW DATABASES");
    const databaseList = databasesRaw[0].filter(row => ignoreDatabases.indexOf(row.Database) == -1).map((row) => ({ database: row.Database}));
    await confirmTip(`数据库列表：\x1b[31m\n${databaseList.map(database => database.database).join('\n')}\x1b[0m\n数据库URL：\n\x1b[31m${connection.host}:${connection.port}\x1b[0m\n确定要导出数据库文件吗？[y/n] `);

    const defaultSqlFileDir = path.join(__dirname, './sql')
    const sqlFileDir = await prompt(`请输入导出数据库的文件位置（默认为：${defaultSqlFileDir}）：`, defaultSqlFileDir);
    if (!fs.existsSync(sqlFileDir)) {
        fs.mkdirSync(sqlFileDir);
        console.log("已自动创建目录" + sqlFileDir)
    } 

    for (let i = 0; i < databaseList.length; i++) {
        const database = databaseList[i];
        const databaseTables = database.databaseTables || [];
        const databaseIgnoreTables = database.databaseIgnoreTables || [];
        const databaseWithDataTables = database.databaseWithDataTables || [];
        await dumpSql({
            database: database.database,
            sqlFile: path.join(sqlFileDir, `${database.database}.sql`),
            tables: databaseTables,
            ignoreTables: [...ignoreTables, ...databaseIgnoreTables],
            withDataTables: [...withDataTables, ...databaseWithDataTables],
            clearFields,
            replace
        });
    }
    
    console.log("")
    console.log("===========================导出程序执行完毕✅==========================")
    console.log(`- 数据库连接：${connection.host + ':' + connection.port}`)
    console.log(`- 导出数据库：\n${databaseList.map(database => "  " + database.database).join('\n')}`)
    console.log(`- 忽略库：${ignoreDatabasesInput}`)
    console.log(`- 忽略表：${ignoreTablesInput}`)
    console.log(`- 带数据表：${withDataTablesInput}`)
    console.log(`- 导出目录：${sqlFileDir}`)
    console.log("---------------------------后续操作指引❗❗----------------------------")
    console.log(`请在${sqlFileDir}复制到目标服务器并执行批量导入工具进行批量导入：`)
    console.log("=====================================================================")
    rl.close();
    process.exit(0);
})();
