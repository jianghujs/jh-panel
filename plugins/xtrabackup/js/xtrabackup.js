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
            mysqlBackupHtml();
            layer.open({
                area: ['500px', '300px'],
                title: '恢复成功',
                content: rdata.msg,
                btn: []
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
    <div>
        <label><input class="mui-switch" type="checkbox" checked>定时备份</label>
    </div>
    <div class="divtable">\
        \
        <div style="padding-top:5px;">存放目录: /www/backup/xtrabackup_data_history</div>\
        <table class="table table-hover" style="margin-top: 10px; max-height: 380px; overflow: auto;">\
            <thead>\
<<<<<<< HEAD
                <th>
                    备份文件
                    <button class="btn btn-default btn-sm va0" onclick="doMysqlBackup();">备份</button>
                </th>\
=======
                <th>备份文件</th>\
                <th>文件大小</th>\
                <th>创建时间</th>\
>>>>>>> 80dd2d99129691cf8ddd3333f3404423ceb504aa
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
                        <td style="width: 120px;' + (tmp[i].size < 1024? 'color: red;': '') + '">'+tmp[i].sizeTxt+'</td>\
                        <td style="width: 180px;">'+getFormatTime(tmp[i].createTime)+'</td>\
                        <td style="text-align: right;width: 60px;">' + 
                            '<a href="javascript:doRecoveryBackup(\''+tmp[i]+'\')" class="btlink">恢复</a> | ' +
                            '<a href="javascript:doDeleteBackup(\''+tmp[i]+'\')" class="btlink">删除</a>' +
                        '</td>\
                    </tr>';
        }
        $(".plugin-table-body").html(tbody);
	});
}
