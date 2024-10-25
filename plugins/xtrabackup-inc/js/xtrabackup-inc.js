var mysqlBackupLayer = null; // 执行备份弹窗
function myPost(method,args,callback, title){
    return new Promise((resolve) => {    
        var _args = null; 
        if (typeof(args) == 'string'){
            _args = JSON.stringify(toArrayObject(args));
        } else {
            _args = JSON.stringify(args);
        }

        var _title = '正在获取...';
        if (typeof(title) != 'undefined'){
            _title = title;
        }

        var loadT = layer.msg(_title, { icon: 16, time: 0, });
        $.post('/plugins/run', {name:'xtrabackup-inc', func:method, args:_args}, function(data) {
            layer.close(loadT);
            if (!data.status){
                layer.msg(data.msg,{icon:0,time:2000,shade: [0.3, '#000']});
                return;
            }
            resolve(data)
            if(typeof(callback) == 'function'){
                callback(data);
            }
        },'json'); 
    })
}


function setting(){
    myPost('get_setting','',function(data){
        let result = JSON.parse(data.data)
        var con = '<div class="line setting">\
            <div class="info-r  m5">\
                <span class="tname">端口</span>\
                <input name="port" class="bt-input-text mr5 port" type="text" style="width:100px" value="'+result.data.port+'">\
            </div>\
            <div class="info-r  m5">\
                <span class="tname">用户名</span>\
                <input name="user" class="bt-input-text mr5" type="text" style="width:100px" value="'+result.data.user+'">\
            </div>\
            <div class="info-r  m5">\
                <span class="tname">密码</span>\
                <input name="password" class="bt-input-text mr5" type="password" style="width:100px" value="'+result.data.password+'">\
            </div>\
            <div class="info-r  m5 mt5">\
                <span class="tname"></span>\
                <button id="btn_change_setting" name="btn_change_setting" class="btn btn-success btn-sm btn_change_port">保存</button>\
                <button id="btn_test_setting" name="btn_test_setting" class="btn btn-sm btn_change_port">测试连接</button>\
            </div>\
        </div>';
        $(".soft-man-con").html(con);

        $('#btn_change_setting').click(function(){
            var port = $(".setting input[name='port']").val();
            var user = $(".setting input[name='user']").val();
            var password = $(".setting input[name='password']").val();
            myPost('change_setting','port='+port+'&user='+user+'&password='+password,function(data){
                var rdata = $.parseJSON(data.data);
                if (rdata.status){
                    layer.msg('修改成功!',{icon:1,time:2000,shade: [0.3, '#000']});
                } else {
                    layer.msg(rdata.msg,{icon:1,time:2000,shade: [0.3, '#000']});
                }
            });
        });
        $('#btn_test_setting').click(function(){
            var port = $(".setting input[name='port']").val();
            var user = $(".setting input[name='user']").val();
            var password = $(".setting input[name='password']").val();
            myPost('test_setting','port='+port+'&user='+user+'&password='+password,function(data){
                var rdata = $.parseJSON(data.data);
                if (rdata.status){
                    layer.msg('连接成功!',{icon:1,time:2000,shade: [0.3, '#000']});
                } else {
                    layer.msg(rdata.msg,{icon:2,time:2000,shade: [0.3, '#000']});
                }
            });
        });
    });
}

function backupPath(){
    myPost('get_backup_path','',function(data){
      data = JSON.parse(data.data);
        var con = '<div class="line ">\
                <div class="info-r  ml0">\
                    <input id="backupPath" name="backupPath" class="bt-input-text mr5 port" type="text" style="width:330px" value="'+(data.data || '/www/backup/xtrabackup_inc_data')+'">\
                    <span class="glyphicon cursor mr5 glyphicon-folder-open icon_datadir" onclick="changePath(\'backupPath\')"></span>\
                    <button id="btn_change_path" name="btn_change_path" class="btn btn-success btn-sm mr5 ml5 btn_change_port">保存</button>\
                </div>\
            </div>';
        $(".soft-man-con").html(con);

        $('#btn_change_path').click(function(){
            let backupPath = $("input[name='backupPath']").val();
            setXtrabackupConfig('backup', 'path', backupPath);
        });
    });
}

var defaultXtrabackupFullCron = {      
    name: '[勿删]xtrabackup-inc全量备份',
    type: 'day',
    where1: '',
    hour: 0,
    minute: 0,
    week: '',
    sType: 'toShell',
    stype: 'toShell',
    sName: '',
    backupCompress: false,
    backupZip: false,
    backupTo: 'localhost' };
var xtrabackupFullCron = {...defaultXtrabackupFullCron};

var defaultXtrabackupIncCron = {      
    name: '[勿删]xtrabackup-inc增量备份',
    type: 'minute-n',
    where1: 30,
    hour: 0,
    minute: 30,
    week: '',
    sType: 'toShell',
    stype: 'toShell',
    sName: '',
    backupCompress: false,
    backupZip: false,
    backupTo: 'localhost' };
var xtrabackupIncCron = {...defaultXtrabackupIncCron};


function backupIncHtml(){
    var con = `\
    <div class="safe container-fluid mt10" style="overflow: hidden;">
        <div class="flex align-center">
            全量备份：
        </div>
        <div class="mtb15 flex align-center">
            <button class="btn btn-success btn-sm va0 mr20" onclick="openXtrabackupFull();">执行全量备份</button>
            <div class="mr20 ss-text pull-left">
                <em>定时执行</em>
                <div class='ssh-item' id="openXtrabackupFullCronSwitch"></div>
            </div>
            <div id="xtrabackupFullCronDetail">
                <div></div>
                <button class="open-cron-selecter-layer btn btn-default btn-sm mr20" type="button">配置频率</button>
            </div>
            <div class="mr20 ss-text pull-left">
                <em>Compress 压缩</em>
                <div class='ssh-item' id="openXtrabackupFullCompressSwitch"></div>
            </div>
        </div>
    </div>
    <div class="safe container-fluid mt10" style="overflow: hidden;">
        <div class="flex align-center">
            增量备份：
        </div>
        <div class="mtb15 flex align-center">
            <button class="btn btn-success btn-sm va0 mr20" onclick="openXtrabackupInc();">执行增量备份</button>
            <div class="mr20 ss-text pull-left">
                <em>定时执行</em>
                <div class='ssh-item' id="openXtrabackupIncCronSwitch"></div>
            </div>
            <div id="xtrabackupIncCronDetail">
                <div></div>
                <button class="open-cron-selecter-layer btn btn-default btn-sm mr20" type="button">配置频率</button>
            </div>
            <div class="mr20 ss-text pull-left">
                <em>Compress 压缩</em>
                <div class='ssh-item' id="openXtrabackupIncCompressSwitch"></div>
            </div>
            <div class="mr20 ss-text pull-left">
                <em>Zip 压缩</em>
                <div class='ssh-item' id="openXtrabackupIncZipSwitch"></div>
            </div>
        </div>
    </div>

    <div class="retention-rules safe container-fluid mt10" style="overflow: hidden;">
        <div class="flex align-center">
            保留规则：
        </div>
        <div class="flex align-center mtb15">
            <div class="plan_hms pull-left mr20 bt-input-text">
                <span><input id="saveAllDayInput" type="number" name="saveAllDay" maxlength="4" max="100" min="1"></span>
                <span class="name" style="width: 160px;">天内全部保留，其余只保留</span>
                <span><input id="saveOtherInput" type="number" name="saveOther" maxlength="4" max="100" min="1"></span>
                <span class="name" style="width: 90px;">份，最长保留</span>
                <span><input id="saveMaxDayInput" type="number" name="saveMaxDay" maxlength="4" max="100" min="1"></span>
                <span class="name">天</span>
            </div>
        </div>
    </div>
    `;

    $(".soft-man-con").html(con);
    getXtrabackupFullCron();
    getXtrabackupIncCron();
    getXtrabackupConfig();
    
    $("#xtrabackupFullCronDetail .open-cron-selecter-layer").click(() => {
        openCronSelectorLayer(xtrabackupFullCron, {yes: addOrUpdateXtrabackupFullCron});
    });
    
    $("#xtrabackupIncCronDetail .open-cron-selecter-layer").click(() => {
        openCronSelectorLayer(xtrabackupIncCron, {yes: addOrUpdateXtrabackupIncCron});
    });

    $(".retention-rules input").on('input', function() {
        const saveAllDay = $(".retention-rules input[name='saveAllDay']").val();
        const saveOther = $(".retention-rules input[name='saveOther']").val();
        const saveMaxDay = $(".retention-rules input[name='saveMaxDay']").val();
        setXtrabackupConfig('backup', 'save_all_day', saveAllDay);
        setXtrabackupConfig('backup', 'save_other', saveOther);
        setXtrabackupConfig('backup', 'save_max_day', saveMaxDay);
    });
}

function getXtrabackupFullCron() {
    $.post('/crontab/get', { name: xtrabackupFullCron.name },function(rdata){
        const { status: openXtrabackupFullCron } = rdata;
        if (openXtrabackupFullCron) {
            xtrabackupFullCron = rdata.data;
        } else {
            xtrabackupFullCron = {...defaultXtrabackupFullCron};
        }
        visibleDom('#xtrabackupFullCronDetail', openXtrabackupFullCron);
        $("#openXtrabackupFullCronSwitch").createRadioSwitch(openXtrabackupFullCron, (checked) => {
            visibleDom('#xtrabackupFullCronDetail', checked);
            if(checked) {
                addOrUpdateXtrabackupFullCron();
            } else {
                deleteCron(xtrabackupFullCron.id);
            }
        });
    },'json');
}

function getXtrabackupConfig() {
  myPost('conf','',function(data){
      const config = JSON.parse(data.data);
      $("#openXtrabackupFullCompressSwitch").createRadioSwitch(config.backup_full.backup_compress == 1, (checked) => {
          setXtrabackupConfig('backup_full', 'backup_compress', checked ? 1 : 0);
      });
      $("#openXtrabackupIncZipSwitch").createRadioSwitch(config.backup_inc.backup_zip == 1, (checked) => {
          setXtrabackupConfig('backup_inc', 'backup_zip', checked ? 1 : 0);
      });
      $("#openXtrabackupIncCompressSwitch").createRadioSwitch(config.backup_inc.backup_compress == 1, (checked) => {
          setXtrabackupConfig('backup_inc', 'backup_compress', checked ? 1 : 0);
      });
      
      $(".retention-rules input[name='saveAllDay']").val((config.backup || {}).save_all_day || 1);
      $(".retention-rules input[name='saveOther']").val((config.backup || {}).save_other || 1);
      $(".retention-rules input[name='saveMaxDay']").val((config.backup || {}).save_max_day || 3);
  });
}

function setXtrabackupConfig(section, key, value) {
    myPost('set_conf', {section, key, value},function(data){
        const rdata = JSON.parse(data.data);
        layer.msg(rdata.msg,{icon:rdata.status?1:2}, 5000);
    });
}

function getXtrabackupIncCron() {
    $.post('/crontab/get', { name: xtrabackupIncCron.name },function(rdata){
        const { status: openXtrabackupIncCron } = rdata;
        if (openXtrabackupIncCron) {
            xtrabackupIncCron = rdata.data;
        }else {
            xtrabackupIncCron = {...defaultXtrabackupIncCron};
        }
        visibleDom('#xtrabackupIncCronDetail', openXtrabackupIncCron);
        $("#openXtrabackupIncCronSwitch").createRadioSwitch(openXtrabackupIncCron, (checked) => {
            visibleDom('#xtrabackupIncCronDetail', checked);
            if(checked) {
                addOrUpdateXtrabackupIncCron();
            } else {
                deleteCron(xtrabackupIncCron.id);
            }
        });
    },'json');
}

async function addOrUpdateXtrabackupFullCron(cronSelectorData) {
    if(!xtrabackupFullCron.id) {
        let scriptData = await myPost('full_backup_cron_script','');
        let scriptRData = $.parseJSON(scriptData.data);
        xtrabackupFullCron.sBody = xtrabackupFullCron.sbody = scriptRData.data
    }
    $.post(xtrabackupFullCron.id? '/crontab/modify_crond': '/crontab/add', {...xtrabackupFullCron, ...cronSelectorData},function(rdata){
        getXtrabackupFullCron();
        layer.msg(rdata.msg,{icon:rdata.status?1:2}, 5000);
    },'json');
}

async function addOrUpdateXtrabackupIncCron(cronSelectorData) {
    if(!xtrabackupIncCron.id) {
        let scriptData = await myPost('inc_backup_cron_script','');
        let scriptRData = $.parseJSON(scriptData.data);
        xtrabackupIncCron.sBody = xtrabackupIncCron.sbody = scriptRData.data
    }
    $.post(xtrabackupIncCron.id? '/crontab/modify_crond': '/crontab/add', {...xtrabackupIncCron, ...cronSelectorData},function(rdata){
        getXtrabackupIncCron();
        layer.msg(rdata.msg,{icon:rdata.status?1:2}, 5000);
    },'json');
}


function deleteCron(id) {
    if (id) {
        $.post('/crontab/del', { id },function(rdata){
            getXtrabackupFullCron();
            getXtrabackupIncCron();
            layer.msg(rdata.msg,{icon:rdata.status?1:2}, 5000);
        },'json');
    }
}

function openXtrabackupFull() {
    const backupCompress = $("#openXtrabackupFullCompressSwitch").getRadioSwitchValue();
    myPost('full_backup_script', { backupCompress }, function(data) {
		let rdata = $.parseJSON(data.data);
        openEditCode({
            title: '执行全量备份',
            content: rdata.data,
            width: '640px',
            height: '400px',
            submitBtn: '执行',
            onSubmit: (content) => {
                doTaskWithLock('全量备份', content)
            }
        })
    });
}

function openXtrabackupInc() {
    const backupZip = $("#openXtrabackupIncZipSwitch").getRadioSwitchValue();
    const backupCompress = $("#openXtrabackupIncCompressSwitch").getRadioSwitchValue();
    myPost('inc_backup_script',{ backupZip, backupCompress }, function(data) {
		let rdata = $.parseJSON(data.data);
        openEditCode({
            title: '执行增量备份',
            content: rdata.data,
            width: '640px',
            height: '400px',
            submitBtn: '执行',
            onSubmit: (content) => {
                doTaskWithLock('增量备份', content)
            }
        })
    });
}



function recoveryIncHtml(){
    var con = `\
    <div class="safe container-fluid mt10" style="overflow: hidden;">
        <div class="flex align-center">
            增量恢复：
        </div>
        <div class="mtb15 flex align-center">
            <button class="btn btn-success btn-sm va0 mr20" onclick="openRecoveryLatestBackup();">执行增量恢复</button>
        </div>
    </div>`;
    $(".soft-man-con").html(con);
}


function openRecoveryLatestBackup() {
    myPost('get_recovery_backup_script','', function(data) {
		let rdata = $.parseJSON(data.data);
        openEditCode({
            title: '执行增量恢复',
            content: rdata.data,
            width: '640px',
            height: '400px',
            submitBtn: '执行',
            onSubmit: (content) => {
              safeMessage('<b style="color: red">【' + document.title + '】增量恢复警告！ </b>', '确定恢复当前系统数据库吗？确认后将清空当前数据库，请谨慎操作!', function() {
                doTaskWithLock('增量恢复', content)
              })
            }
        })
    });
}

function doTaskWithLock(name, content) {
    myPost('do_task_with_lock', {name, content: encodeURIComponent(content)}, function(data){
        var rdata = $.parseJSON(data.data);
        if(!rdata.status) {
            setTimeout(() => {
                layer.msg(rdata.msg,{icon:2, time:2000});
            }, 500)
            return;
        };
        $("#openEditCodeCloseBtn").click();
        messageBox({timeout: 300, autoClose: true, toLogAfterComplete: true});
    });
}


function backupListHtml(){
  var con = `\
  <div class="divtable">\
      \
      <div style="padding-top:5px;">存放目录: /www/backup/xtrabackup_inc_data_history</div>\
      <table class="table table-hover" style="margin-top: 10px; max-height: 380px; overflow: auto;">\
          <thead>\
              <th>
                  备份文件
              </th>\
              <th> 文件大小</th>\
              <th> 创建时间</th>\
              <th style="text-align: right;" width="150">操作</th></tr>\
          </thead>\
          <tbody class="plugin-table-body"></tbody>\
      </table>\
  </div>`;
  $(".soft-man-con").html(con);
  
  myPost('backup_list',{}, function(data){
    let rdata = $.parseJSON(data.data);
    console.log(rdata);
    if (!rdata['status']){
            layer.msg(rdata['msg'],{icon:2,time:2000,shade: [0.3, '#000']});
            return;
        }

        var tbody = '';
        var tmp = rdata['data'].sort((a, b) => b.createTime - a.createTime);
        tableData = tmp;
        for(var i=0;i<tmp.length;i++){
            tbody += '<tr>\
                        <td style="width: 120px;">'+tmp[i].filename+'</td>\
                        <td style="width: 240px;' + (tmp[i].size < 1024? 'color: red;': '') + '">'+tmp[i].sizeTxt+(tmp[i].size < 1024? '（无效的备份文件）': '')+'</td>\
                        <td style="width: 180px;">'+getFormatTime(tmp[i].createTime)+'</td>\
                        <td style="text-align: right;width: 60px;">' + 
                            '<a href="javascript:openRecoveryBackup(\''+tmp[i].filename+'\')" class="btlink">恢复</a> | ' +
                            '<a href="javascript:doDeleteBackup(\''+tmp[i].filename+'\')" class="btlink">删除</a>' +
                        '</td>\
                    </tr>';
        }
        $(".plugin-table-body").html(tbody);
  });
}


function openRecoveryBackup(filename) {
  myPost('get_recovery_backup_script',{filename}, function(data) {
    let rdata = $.parseJSON(data.data);
        openEditCode({
            title: '执行恢复',
            content: rdata.data,
            width: '640px',
            height: '400px',
            submitBtn: '执行',
            onSubmit: (content) => {
              safeMessage('<b style="color: red">【' + document.title + '】恢复确认警告！ </b>', '确定恢复当前系统数据库吗？确认后将清空当前数据库，请谨慎操作!', function() {
                doTaskWithLock('增量恢复', content)
              });
            }
        })
    });
}


function doDeleteBackup(filename) {
  safeMessage('确认删除备份文件', '确认后[' + filename + ']文件不可恢复，请谨慎操作！', function(){
    myPost('do_delete_backup', {filename}, function(data){
        var rdata = $.parseJSON(data.data);
        if(!rdata.status) {
            layer.msg(rdata.msg,{icon:2, time:2000});
            return;
        };
        backupListHtml();
        layer.msg(rdata.msg,{icon:1,time:2000,shade: [0.3, '#000']});
    });
  });
}