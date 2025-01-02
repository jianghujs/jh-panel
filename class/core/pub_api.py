# coding: utf-8

# ---------------------------------------------------------------------------------
# 开放接口
# ---------------------------------------------------------------------------------


import psutil
import time
import os
import sys
import mw
import re
import json
import pwd

from flask import request

class pub_api:
    
    def getHostAddrApi(self):
        return jh.returnJson(True, 'ok', jh.getHostAddr())
