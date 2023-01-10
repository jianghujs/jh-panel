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
    $.post('/plugins/run', {name:'xtrabackup', func:method, args:_args}, function(data) {
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

const xtrabackupCron = {        
    name: '[勿删]xtrabackup-cron',
    type: 'day',
    where1: '',
    hour: $("#xtrabackup-cron input[name='hour']").val(),
    minute: $("#xtrabackup-cron input[name='minute']").val(),
    week: '',
    sType: 'toShell',
    stype: 'toShell',
    sBody: 'bash /www/server/xtrabackup/xtrabackup.sh \necho "xtrabackup定时执行成功" \necho $(date "+%Y-%m-%d_%H-%M-%S")',
    sbody: 'bash /www/server/xtrabackup/xtrabackup.sh \necho "xtrabackup定时执行成功" \necho $(date "+%Y-%m-%d_%H-%M-%S")',
    sName: '',
    backupTo: 'localhost' 
}
function getXtrabackupCron() {
    myPost('get_xtrabackup_cron', { xtrabackupCronName: xtrabackupCron.name }, function(data){
        var rdata = $.parseJSON(data.data);
        // 定时任务不存在
        if(!rdata.status) {
            $("#xtrabackup-cron #xtrabackup-cron-add").css("display", "inline-block");
            $("#xtrabackup-cron #xtrabackup-cron-update").css("display", "none");
            $("#xtrabackup-cron #xtrabackup-cron-delete").css("display", "none");
            $("#xtrabackup-cron input[name='id']").val("");
            $("#xtrabackup-cron input[name='hour']").val(20);
            $("#xtrabackup-cron input[name='minute']").val(30);
            return;
        };

        // 定时任务存在
        if(rdata.status) {
            const { id,name,type,hour,minute } = rdata.data;
            $("#xtrabackup-cron #xtrabackup-cron-add").css("display", "none");
            $("#xtrabackup-cron #xtrabackup-cron-update").css("display", "inline-block");
            $("#xtrabackup-cron #xtrabackup-cron-delete").css("display", "inline-block");
            $("#xtrabackup-cron input[name='id']").val(id);
            $("#xtrabackup-cron input[name='hour']").val(hour);
            $("#xtrabackup-cron input[name='minute']").val(minute);
            return;
        };
    });
}

function deleteXtrabackupCron() {
    var id = $("#xtrabackup-cron input[name='id']").val();
    if (id) {
        safeMessage('确认删除', '确定删除 xtrabackup 定时任务吗', function(){
            $.post('/crontab/del', { id },function(rdata){
                getXtrabackupCron();
                layer.msg(rdata.msg,{icon:rdata.status?1:2}, 5000);
            },'json');
        })
    }
}
function addXtrabackupCron() {
    var hour =  $("#xtrabackup-cron input[name='hour']").val();
    var minute =  $("#xtrabackup-cron input[name='minute']").val();
    $.post('/crontab/add', { ...xtrabackupCron, hour, minute },function(rdata){
        getXtrabackupCron();
        layer.msg(rdata.msg,{icon:rdata.status?1:2}, 5000);
    },'json');
}

function updateXtrabackupCron() {
    var id = $("#xtrabackup-cron input[name='id']").val();
    var hour =  $("#xtrabackup-cron input[name='hour']").val();
    var minute =  $("#xtrabackup-cron input[name='minute']").val();
    if (id) {
        $.post('/crontab/modify_crond', { ...xtrabackupCron, id, hour, minute },function(rdata){
            getXtrabackupCron();
            layer.msg(rdata.msg,{icon:rdata.status?1:2}, 5000);
        },'json');
    }
}


function doMysqlBackup() {
    myPost('do_mysql_backup', {}, function(data){
        var rdata = $.parseJSON(data.data);
        if(!rdata.status) {
            layer.msg(rdata.msg,{icon:2, time:2000});
            return;
        };
        layer.msg(rdata.msg,{icon:1,time:2000,shade: [0.3, '#000']});
        mysqlBackupHtml();
    });
}

function doRecoveryBackup(filename) {
    safeMessage('确认恢复备份', '确认后[' + filename + ']内容将会覆盖mysql目录下的data内容，请谨慎操作！', function(){
        myPost('do_recovery_backup', {filename}, function(data){
            var rdata = $.parseJSON(data.data);
            if(!rdata.status) {
                layer.msg(rdata.msg,{icon:2, time: 6000});
                return;
            };
            layer.open({
                area: ['500px', '300px'],
                title: '恢复成功',
                content: rdata.msg,
                btn: [],
                // cancel: function(index, layero){ 
                //     layer.close(index);
                //     mysqlBackupHtml();
                // } 
            });    
            // layer.msg(rdata.msg,{icon:1,time: 9000,shade: [0.3, '#000']});
        });
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
            mysqlBackupHtml();
            layer.msg(rdata.msg,{icon:1,time:2000,shade: [0.3, '#000']});
        });
    });
}

function mysqlBackupHtml(){
    var con = `\
    <div id="xtrabackup-cron">
        <span>每天</span>
        <span>
            <input type="hidden" name="id" value="">
            <input type="number" name="hour" value="20" maxlength="2" max="23" min="0">
            <span class="name">:</span>
            <input type="number" name="minute" value="30" maxlength="2" max="59" min="0">
        </span>
        <span>定时执行备份</span>
        <button id="xtrabackup-cron-add" style="display: none;"
            class="btn btn-success btn-sm va0" onclick="addXtrabackupCron();">创建</button>
        <button id="xtrabackup-cron-update" style="display: none;"
            class="btn btn-success btn-sm va0" onclick="updateXtrabackupCron();">修改</button>
        <button id="xtrabackup-cron-delete" style="display: none;"
            class="btn btn-danger btn-sm va0" onclick="deleteXtrabackupCron();">删除</button>
    </div>
    <div class="divtable">\
        \
        <div style="padding-top:5px;">存放目录: /www/backup/xtrabackup_data_history</div>\
        <table class="table table-hover" style="margin-top: 10px; max-height: 380px; overflow: auto;">\
            <thead>\
                <th>
                    备份文件
                    <button class="btn btn-default btn-sm va0" onclick="doMysqlBackup();">备份</button>
                </th>\
                <th> 文件大小</th>\
                <th> 创建时间</th>\
                <th style="text-align: right;" width="150">操作</th></tr>\
            </thead>\
            <tbody class="plugin-table-body"></tbody>\
        </table>\
    </div>`;
    $(".soft-man-con").html(con);
    setTimeout(() => {
        getXtrabackupCron();
    }, 300)
    
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
                            '<a href="javascript:doRecoveryBackup(\''+tmp[i].filename+'\')" class="btlink">恢复</a> | ' +
                            '<a href="javascript:doDeleteBackup(\''+tmp[i].filename+'\')" class="btlink">删除</a>' +
                        '</td>\
                    </tr>';
        }
        $(".plugin-table-body").html(tbody);
	});
}
