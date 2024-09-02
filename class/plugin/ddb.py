# coding: utf-8

# https://github.com/mkrd/DictDataBase
import re
import os
import sys

import dictdatabase 


class DDB:
    __DB_DIR = '/www/server/ddb/'
    __DB_CONN = None
    __DB_ERR = None

    def __init__(self, db_dir = None):
        if db_dir is not None:
            self.__DB_DIR = db_dir

    def __Conn(self):
        try:
            dictdatabase.config.storage_directory = self.__DB_DIR
            return True
        except Exception as e:
            self.__DB_ERR = e
            return False

    def setDbDir(self, db_dir):
        if db_dir is None:
            return
        if not os.path.exists(db_dir):
            os.mkdir(db_dir)
            
        dictdatabase.config.storage_directory = db_dir
        self.__DB_DIR = db_dir

    def getDB(self, table):
        if not self.__Conn():
            return self.__DB_ERR
        if not dictdatabase.at(table).exists():
            dictdatabase.at(table).create({})
        return dictdatabase.at(table)

    def getAll(self, table):
        if not self.__Conn():
            return self.__DB_ERR
        try:
          result = self.getDB(table).read()
        except Exception as e:  
          raise Exception("DictDataBase文件读取错误")
        
        if result:
            return list(result.values())
        return []

    def getOne(self, table, id):
        if not self.__Conn():
            return self.__DB_ERR
        if type(id) is not str:
            id = str(id)
        for item in self.getAll(table):
            if item['id'] == id:
                return item
        return None

    def saveOne(self, table, id, data):
        if not self.__Conn():
            return self.__DB_ERR
        if type(id) is not str:
            id = str(id)
        exist = self.getOne(table, id)
        if exist:
            data = {'id': id, **exist, **data}
        else:
            data = {'id': id, **data}
        with self.getDB(table).session() as (session, db):
            db[id] = data
            session.write()
        
    def deleteOne(self, table, id):
        if not self.__Conn():
            return self.__DB_ERR
        if type(id) is not str:
            id = str(id)
        with self.getDB(table).session() as (session, db):
            if db.get(id, None) is not None:
                del db[id]
            session.write()

