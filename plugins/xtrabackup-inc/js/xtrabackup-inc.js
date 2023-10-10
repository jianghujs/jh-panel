var mysqlBackupLayer = null; // 执行备份弹窗
function myPost(method,args,callback, title){

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

        if(typeof(callback) == 'function'){
            callback(data);
        }
    },'json'); 
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
        data = JSON.parse(data.data)
        var con = '<div class="line ">\
                <div class="info-r  ml0">\
                    <input id="basedir" name="basedir" class="bt-input-text mr5 port" type="text" style="width:330px" value="'+(data.data.base || '/www/backup/xtrabackup_data_base')+'">\
                    <span class="glyphicon cursor mr5 glyphicon-folder-open icon_datadir" onclick="changePath(\'basedir\')"></span>\
                </div>\
                <div class="info-r  ml0">\
                    <input id="incdir" name="incdir" class="bt-input-text mr5 port" type="text" style="width:330px" value="'+(data.data.inc || '/www/backup/xtrabackup_data_incremental')+'">\
                    <span class="glyphicon cursor mr5 glyphicon-folder-open icon_datadir" onclick="changePath(\'incdir\')"></span>\
                </div>\
                <div class="info-r  ml0">\
                    <button id="btn_change_path" name="btn_change_path" class="btn btn-success btn-sm mr5 ml5 btn_change_port">保存</button>\
                </div>\
            </div>';
        $(".soft-man-con").html(con);

        $('#btn_change_path').click(function(){
            var basedir = $("input[name='basedir']").val();
            var incdir = $("input[name='incdir']").val();
            myPost('set_backup_path','base='+basedir+'&inc='+incdir,function(data){
                var rdata = $.parseJSON(data.data);
                layer.msg(rdata.msg,{icon:rdata.status ? 1 : 5,time:2000,shade: [0.3, '#000']});
            });
        });
    });
}
var xtrabackupCron = {      
    name: '[勿删]xtrabackup-inc-cron_full',
    type: 'day',
    where1: '',
    week: '',
    sType: 'toShell',
    stype: 'toShell',
    sName: '',
    backupTo: 'localhost' };

myPost('full_backup_cron_script','', function(data) {
    let rdata = $.parseJSON(data.data);
    xtrabackupCron = {  
        ...xtrabackupCron,
        
        hour: $("#xtrabackup-cron input[name='hour']").val(),
        minute: $("#xtrabackup-cron input[name='minute']").val(),
        sBody: rdata.data,
        sbody: rdata.data,
    }
});

function doMysqlBackup(content) {
    myPost('do_mysql_backup', {content: encodeURIComponent(content)}, function(data){
        var rdata = $.parseJSON(data.data);
        if(!rdata.status) {
            backupIncHtml();
            setTimeout(() => {
                layer.msg(rdata.msg,{icon:2, time:2000});
            }, 500)
            return;
        };
        backupIncHtml();
        layer.msg(rdata.msg,{icon:1,time:2000,shade: [0.3, '#000']});
        setTimeout(() => {
            $("#openEditCodeCloseBtn").click();
            messageBox({timeout: 300, autoClose: true, toLogAfterComplete: true});
            
        }, 1000)
        
    });
}




function doDeleteBackup(filename) {
    myPost('do_delete_backup', {filename}, function(data){
        var rdata = $.parseJSON(data.data);
        if(!rdata.status) {
            layer.msg(rdata.msg,{icon:2, time:2000});
            return;
        };
        backupIncHtml();
        layer.msg(rdata.msg,{icon:1,time:2000,shade: [0.3, '#000']});
    });
    // safeMessage('确认删除备份文件', '确认后[' + filename + ']文件不可恢复，请谨慎操作！', function(){
    //     myPost('do_delete_backup', {filename}, function(data){
    //         var rdata = $.parseJSON(data.data);
    //         if(!rdata.status) {
    //             layer.msg(rdata.msg,{icon:2, time:2000});
    //             return;
    //         };
    //         backupIncHtml();
    //         layer.msg(rdata.msg,{icon:1,time:2000,shade: [0.3, '#000']});
    //     });
    // });
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
    backupTo: 'localhost' };
var xtrabackupFullCron = {...defaultXtrabackupFullCron};

var defaultXtrabackupIncCron = {      
    name: '[勿删]xtrabackup-inc增量备份',
    type: 'minute-n',
    where1: 3,
    hour: 0,
    minute: 3,
    week: '',
    sType: 'toShell',
    stype: 'toShell',
    sName: '',
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
        </div>
    </div>
    `;

    $(".soft-man-con").html(con);
    getXtrabackupFullCron();
    getXtrabackupIncCron();
    
    $("#xtrabackupFullCronDetail .open-cron-selecter-layer").click(() => {
        openCronSelectorLayer(xtrabackupFullCron, {yes: addOrUpdateXtrabackupFullCron});
    });
    
    $("#xtrabackupIncCronDetail .open-cron-selecter-layer").click(() => {
        openCronSelectorLayer(xtrabackupIncCron, {yes: addOrUpdateXtrabackupIncCron});
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

function addOrUpdateXtrabackupFullCron(cronSelectorData) {
    $.post(xtrabackupFullCron.id? '/crontab/modify_crond': '/crontab/add', {...xtrabackupFullCron, ...cronSelectorData},function(rdata){
        getXtrabackupFullCron();
        layer.msg(rdata.msg,{icon:rdata.status?1:2}, 5000);
    },'json');
}

function addOrUpdateXtrabackupIncCron(cronSelectorData) {
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
    myPost('full_backup_script','', function(data) {
		let rdata = $.parseJSON(data.data);
        openEditCodeAndExcute({
            title: '执行全量备份',
            name: '执行Xtrabackup增量版命令[全量备份]',
            content: rdata.data
        })
    });
}

function openXtrabackupInc() {
    myPost('inc_backup_script','', function(data) {
		let rdata = $.parseJSON(data.data);
        openEditCodeAndExcute({
            title: '执行增量备份',
            name: '执行Xtrabackup增量版命令[增量备份]',
            content: rdata.data
        })
    });
}



function recoveryIncHtml(){
    var con = `\
    <button class="btn btn-success btn-sm va0" onclick="openRecoveryBackup();">增量恢复</button>`;
    $(".soft-man-con").html(con);
}


function openRecoveryBackup() {
    myPost('get_recovery_backup_script','', function(data) {
		let rdata = $.parseJSON(data.data);
        openEditCode({
            title: '执行增量恢复',
            content: rdata.data,
            width: '640px',
            height: '400px',
            submitBtn: '执行',
            onSubmit: (content) => {
                doRecoveryBackup(content)
            }
        })
    });
}

function doRecoveryBackup(content) {
    myPost('do_recovery_backup', {content: encodeURIComponent(content)}, function(data){
        var rdata = $.parseJSON(data.data);
        if(!rdata.status) {
            setTimeout(() => {
                layer.msg(rdata.msg,{icon:2, time:2000});
            }, 500)
            return;
        };
        layer.open({
            area: ['500px', '300px'],
            title: '添加恢复任务成功',
            content: rdata.msg,
            btn: [],
            // cancel: function(index, layero){ 
            //     layer.close(index);
            //     mysqlBackupHtml();
            // } 
        });    
        $("#openEditCodeCloseBtn").click();
        messageBox({timeout: 300, autoClose: true, toLogAfterComplete: true});
    });
}