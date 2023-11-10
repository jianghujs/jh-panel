'use strict';

const Knex = require('knex');

const connection1 = {
    host: '192.168.3.63',
    port: 33067,
    user: 'root',
    password: 'DBLyykCtksMdAcf4'
};

const connection2 = {
    host: '192.168.3.73',
    port: 33067,
    user: 'root',
    password: 'DBLyykCtksMdAcf4'
};

let ignoreDb = [
  'information_schema',
  'mysql',
  'performance_schema',
  'sys',
  'test',
'baofeng_teacher',
'student_learning_record'
]

async function getTableChecksum(connection) {
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

    for (let database of databases) {
      
    if (ignoreDb.includes(database)) {
      continue;
    }
        const tables = (await knex("TABLES").select("*")).filter((o) => o.TABLE_SCHEMA === database && o.TABLE_COMMENT !== "VIEW")
        .map((o) => o.TABLE_NAME);

        checksums[database] = {};

        for (let table of tables.filter((o) => o.indexOf('view') == -1)) {
            const checksumRaw = await knex.raw(`CHECKSUM TABLE \`${database}\`.\`${table}\``);
            const checksum = checksumRaw[0][0].Checksum;

            checksums[database][table] = checksum;
        }
    }

    await knex.destroy();

    return checksums;
}

async function compareChecksums(checksums1, checksums2) {
    for (let database in checksums1) {
        if (!(database in checksums2)) {
            console.log(`Database ${database} is missing in the second connection.`);
            continue;
        }

        for (let table in checksums1[database]) {
            if (!(table in checksums2[database])) {
                console.log(`Table ${database}.${table} is missing in the second connection.`);
                continue;
            }

            if (checksums1[database][table] !== checksums2[database][table]) {
                console.log(`Checksum mismatch for table ${database}.${table}: ${checksums1[database][table]} vs ${checksums2[database][table]}`);
            }
        }
    }
}

(async () => {
    const checksums1 = await getTableChecksum(connection1);
    const checksums2 = await getTableChecksum(connection2);

    compareChecksums(checksums1, checksums2);
})();
