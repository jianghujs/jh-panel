
function myPost(method,args,callback, title){
    return new Promise((resolve, reject) => {   

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
      $.post('/plugins/run', {name:'mysql-apt', func:method, args:_args}, function(data) {
          layer.close(loadT);
          if (!data.status){
              layer.msg(data.msg,{icon:0,time:2000,shade: [0.3, '#000']});
              return;
          }

          if(typeof(callback) == 'function'){
              callback(data);
          }
          resolve(data)
      },'json'); 
    })
}

function myPostN(method,args,callback, title){

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
    $.post('/plugins/run', {name:'mysql-apt', func:method, args:_args}, function(data) {
        if(typeof(callback) == 'function'){
            callback(data);
        }
    },'json'); 
}

function myAsyncPost(method,args){
    var _args = null; 
    if (typeof(args) == 'string'){
        _args = JSON.stringify(toArrayObject(args));
    } else {
        _args = JSON.stringify(args);
    }

    var loadT = layer.msg('正在获取...', { icon: 16, time: 0 });
    return syncPost('/plugins/run', {name:'mysql-apt', func:method, args:_args}); 
}

function vaildPhpmyadmin(url,username,password){
    // console.log("Authorization: Basic " + btoa(username + ":" + password));
    $.ajax({
        type: "GET",
        url: url,
        dataType: 'json',
        async: false,
        username:username,
        password:password,
        headers: {
            "Authorization": "Basic " + btoa(username + ":" + password)
        },
        data: 'vaild',
        success: function (){
            alert('Thanks for your comment!');
        }
    });
}

function runInfo(){
    myPost('run_info','',function(data){
        var rdata = $.parseJSON(data.data);
        if (typeof(rdata['status']) != 'undefined'){
            layer.msg(rdata['msg'],{icon:0,time:2000,shade: [0.3, '#000']});
            return;
        }

        // Com_select , Qcache_inserts
        var cache_size = ((parseInt(rdata.Qcache_hits) / (parseInt(rdata.Qcache_hits) + parseInt(rdata.Qcache_inserts))) * 100).toFixed(2) + '%';
        if (cache_size == 'NaN%') cache_size = 'OFF';
        var Con = '<div class="divtable"><table class="table table-hover table-bordered" style="margin-bottom:10px;background-color:#fafafa">\
                    <tbody>\
                        <tr><th>启动时间</th><td>' + getLocalTime(rdata.Run) + '</td><th>每秒查询</th><td>' + parseInt(rdata.Questions / rdata.Uptime) + '</td></tr>\
                        <tr><th>总连接次数</th><td>' + rdata.Connections + '</td><th>每秒事务</th><td>' + parseInt((parseInt(rdata.Com_commit) + parseInt(rdata.Com_rollback)) / rdata.Uptime) + '</td></tr>\
                        <tr><th>发送</th><td>' + toSize(rdata.Bytes_sent) + '</td><th>File</th><td>' + rdata.File + '</td></tr>\
                        <tr><th>接收</th><td>' + toSize(rdata.Bytes_received) + '</td><th>Position</th><td>' + rdata.Position + '</td></tr>\
                    </tbody>\
                    </table>\
                    <table class="table table-hover table-bordered">\
                    <thead style="display:none;"><th></th><th></th><th></th><th></th></thead>\
                    <tbody>\
                        <tr><th>活动/峰值连接数</th><td>' + rdata.Threads_running + '/' + rdata.Max_used_connections + '</td><td colspan="2">若值过大,增加max_connections</td></tr>\
                        <tr><th>线程缓存命中率</th><td>' + ((1 - rdata.Threads_created / rdata.Connections) * 100).toFixed(2) + '%</td><td colspan="2">若过低,增加thread_cache_size</td></tr>\
                        <tr><th>索引命中率</th><td>' + ((1 - rdata.Key_reads / rdata.Key_read_requests) * 100).toFixed(2) + '%</td><td colspan="2">若过低,增加key_buffer_size</td></tr>\
                        <tr><th>Innodb索引命中率</th><td>' + ((1 - rdata.Innodb_buffer_pool_reads / rdata.Innodb_buffer_pool_read_requests) * 100).toFixed(2) + '%</td><td colspan="2">若过低,增加innodb_buffer_pool_size</td></tr>\
                        <tr><th>查询缓存命中率</th><td>' + cache_size + '</td><td colspan="2">' + lan.soft.mysql_status_ps5 + '</td></tr>\
                        <tr><th>创建临时表到磁盘</th><td>' + ((rdata.Created_tmp_disk_tables / rdata.Created_tmp_tables) * 100).toFixed(2) + '%</td><td colspan="2">若过大,尝试增加tmp_table_size</td></tr>\
                        <tr><th>已打开的表</th><td>' + rdata.Open_tables + '</td><td colspan="2">若过大,增加table_cache_size</td></tr>\
                        <tr><th>没有使用索引的量</th><td>' + rdata.Select_full_join + '</td><td colspan="2">若不为0,请检查数据表的索引是否合理</td></tr>\
                        <tr><th>没有索引的JOIN量</th><td>' + rdata.Select_range_check + '</td><td colspan="2">若不为0,请检查数据表的索引是否合理</td></tr>\
                        <tr><th>排序后的合并次数</th><td>' + rdata.Sort_merge_passes + '</td><td colspan="2">若值过大,增加sort_buffer_size</td></tr>\
                        <tr><th>锁表次数</th><td>' + rdata.Table_locks_waited + '</td><td colspan="2">若值过大,请考虑增加您的数据库性能</td></tr>\
                    <tbody>\
            </table></div>';
        $(".soft-man-con").html(Con);
    });
}


function myDbPos(){
    myPost('my_db_pos','',function(data){
        var con = '<div class="line ">\
            <div class="info-r  ml0">\
            <input id="datadir" name="datadir" class="bt-input-text mr5 port" type="text" style="width:330px" value="'+data.data+'">\
            <span class="glyphicon cursor mr5 glyphicon-folder-open icon_datadir" onclick="changePath(\'datadir\')"></span>\
            <button id="btn_change_path" name="btn_change_path" class="btn btn-success btn-sm mr5 ml5 btn_change_port">迁移</button>\
            </div></div>';
        $(".soft-man-con").html(con);

        $('#btn_change_path').click(function(){
            var datadir = $("input[name='datadir']").val();
            myPost('set_db_pos','datadir='+datadir,function(data){
                var rdata = $.parseJSON(data.data);
                layer.msg(rdata.msg,{icon:rdata.status ? 1 : 5,time:2000,shade: [0.3, '#000']});
            });
        });
    });
}

function myPort(){
    myPost('my_port','',function(data){
        var con = '<div class="line ">\
            <div class="info-r  ml0">\
            <input name="port" class="bt-input-text mr5 port" type="text" style="width:100px" value="'+data.data+'">\
            <button id="btn_change_port" name="btn_change_port" class="btn btn-success btn-sm mr5 ml5 btn_change_port">修改</button>\
            </div></div>';
        $(".soft-man-con").html(con);

        $('#btn_change_port').click(function(){
            var port = $("input[name='port']").val();
            myPost('set_my_port','port='+port,function(data){
                var rdata = $.parseJSON(data.data);
                if (rdata.status){
                    layer.msg('修改成功!',{icon:1,time:2000,shade: [0.3, '#000']});
                } else {
                    layer.msg(rdata.msg,{icon:1,time:2000,shade: [0.3, '#000']});
                }
            });
        });
    });
}

async function openMysqlTerminal(){
    if (typeof WebShell == 'undefined') {
        layer.msg('当前面板终端组件不可用', {icon: 2});
        return;
    }

    var webShell = WebShell.getInstance().setCloseCommand('exit\n');
    var socket = await webShell.open();
    myPost('get_mysql_terminal_cmd', '', function(data){
        var rdata = $.parseJSON(data.data);
        if (!rdata.status) {
            layer.msg(rdata.msg, {icon: 2});
            return;
        }

        socket.emit('webssh', 'clear && ' + rdata.data + '\n');
    }, '正在打开MySQL终端...');
}


//数据库存储信置
function changeMySQLDataPath(act) {
    if (act != undefined) {
        layer.confirm(lan.soft.mysql_to_msg, { closeBtn: 2, icon: 3 }, function() {
            var datadir = $("#datadir").val();
            var data = 'datadir=' + datadir;
            var loadT = layer.msg(lan.soft.mysql_to_msg1, { icon: 16, time: 0, shade: [0.3, '#000'] });
            $.post('/database?action=SetDataDir', data, function(rdata) {
                layer.close(loadT)
                layer.msg(rdata.msg, { icon: rdata.status ? 1 : 5 });
            });
        });
        return;
    }

    $.post('/database?action=GetMySQLInfo', '', function(rdata) {
        var LimitCon = '<p class="conf_p">\
                            <input id="datadir" class="phpUploadLimit bt-input-text mr5" style="width:350px;" type="text" value="' + rdata.datadir + '" name="datadir">\
                            <span onclick="ChangePath(\'datadir\')" class="glyphicon glyphicon-folder-open cursor mr20" style="width:auto"></span><button class="btn btn-success btn-sm" onclick="changeMySQLDataPath(1)">' + lan.soft.mysql_to + '</button>\
                        </p>';
        $(".soft-man-con").html(LimitCon);
    });
}




//数据库配置状态
function myPerfOpt() {
    //获取MySQL配置
    myPost('db_status','',function(data){
        var rdata = $.parseJSON(data.data);
        if ( typeof(rdata.status) != 'undefined' && !rdata.status){
            layer.msg(rdata.msg, {icon:2});
            return; 
        }


        // console.log(rdata);
        var key_buffer_size = toSizeM(rdata.mem.key_buffer_size);
        var query_cache_size = toSizeM(rdata.mem.query_cache_size);
        var tmp_table_size = toSizeM(rdata.mem.tmp_table_size);
        var innodb_buffer_pool_size = toSizeM(rdata.mem.innodb_buffer_pool_size);
        var innodb_additional_mem_pool_size = toSizeM(rdata.mem.innodb_additional_mem_pool_size);
        var innodb_log_buffer_size = toSizeM(rdata.mem.innodb_log_buffer_size);

        var sort_buffer_size = toSizeM(rdata.mem.sort_buffer_size);
        var read_buffer_size = toSizeM(rdata.mem.read_buffer_size);
        var read_rnd_buffer_size = toSizeM(rdata.mem.read_rnd_buffer_size);
        var join_buffer_size = toSizeM(rdata.mem.join_buffer_size);
        var thread_stack = toSizeM(rdata.mem.thread_stack);
        var binlog_cache_size = toSizeM(rdata.mem.binlog_cache_size);

        var a = key_buffer_size + query_cache_size + tmp_table_size + innodb_buffer_pool_size + innodb_additional_mem_pool_size + innodb_log_buffer_size;
        var b = sort_buffer_size + read_buffer_size + read_rnd_buffer_size + join_buffer_size + thread_stack + binlog_cache_size;
        var memSize = a + rdata.mem.max_connections * b;


        var memCon = '<div class="conf_p" style="margin-bottom:0">\
                        <div style="border-bottom:#ccc 1px solid;padding-bottom:10px;margin-bottom:10px"><span><b>最大使用内存: </b></span>\
                        <select class="bt-input-text" name="mysql_set" style="margin-left:-4px">\
                            <option value="0">请选择</option>\
                            <option value="1">1-2GB</option>\
                            <option value="2">2-4GB</option>\
                            <option value="3">4-8GB</option>\
                            <option value="4">8-16GB</option>\
                            <option value="5">16-32GB</option>\
                        </select>\
                        <span>' + lan.soft.mysql_set_maxmem + ': </span><input style="width:70px;background-color:#eee;" class="bt-input-text mr5" name="memSize" type="text" value="' + memSize.toFixed(2) + '" readonly>MB\
                        </div>\
                        <p><span>key_buffer_size</span><input style="width: 70px;" class="bt-input-text mr5" name="key_buffer_size" value="' + key_buffer_size + '" type="number" >MB, <font>' + lan.soft.mysql_set_key_buffer_size + '</font></p>\
                        <p><span>query_cache_size</span><input style="width: 70px;" class="bt-input-text mr5" name="query_cache_size" value="' + query_cache_size + '" type="number" >MB, <font>' + lan.soft.mysql_set_query_cache_size + '</font></p>\
                        <p><span>tmp_table_size</span><input style="width: 70px;" class="bt-input-text mr5" name="tmp_table_size" value="' + tmp_table_size + '" type="number" >MB, <font>' + lan.soft.mysql_set_tmp_table_size + '</font></p>\
                        <p><span>innodb_buffer_pool_size</span><input style="width: 70px;" class="bt-input-text mr5" name="innodb_buffer_pool_size" value="' + innodb_buffer_pool_size + '" type="number" >MB, <font>' + lan.soft.mysql_set_innodb_buffer_pool_size + '</font></p>\
                        <p><span>innodb_log_buffer_size</span><input style="width: 70px;" class="bt-input-text mr5" name="innodb_log_buffer_size" value="' + innodb_log_buffer_size + '" type="number">MB, <font>' + lan.soft.mysql_set_innodb_log_buffer_size + '</font></p>\
                        <p style="display:none;"><span>innodb_additional_mem_pool_size</span><input style="width: 70px;" class="bt-input-text mr5" name="innodb_additional_mem_pool_size" value="' + innodb_additional_mem_pool_size + '" type="number" >MB</p>\
                        <p><span>sort_buffer_size</span><input style="width: 70px;" class="bt-input-text mr5" name="sort_buffer_size" value="' + (sort_buffer_size * 1024) + '" type="number" >KB * ' + lan.soft.mysql_set_conn + ', <font>' + lan.soft.mysql_set_sort_buffer_size + '</font></p>\
                        <p><span>read_buffer_size</span><input style="width: 70px;" class="bt-input-text mr5" name="read_buffer_size" value="' + (read_buffer_size * 1024) + '" type="number" >KB * ' + lan.soft.mysql_set_conn + ', <font>' + lan.soft.mysql_set_read_buffer_size + ' </font></p>\
                        <p><span>read_rnd_buffer_size</span><input style="width: 70px;" class="bt-input-text mr5" name="read_rnd_buffer_size" value="' + (read_rnd_buffer_size * 1024) + '" type="number" >KB * ' + lan.soft.mysql_set_conn + ', <font>' + lan.soft.mysql_set_read_rnd_buffer_size + ' </font></p>\
                        <p><span>join_buffer_size</span><input style="width: 70px;" class="bt-input-text mr5" name="join_buffer_size" value="' + (join_buffer_size * 1024) + '" type="number" >KB * ' + lan.soft.mysql_set_conn + ', <font>' + lan.soft.mysql_set_join_buffer_size + '</font></p>\
                        <p><span>thread_stack</span><input style="width: 70px;" class="bt-input-text mr5" name="thread_stack" value="' + (thread_stack * 1024) + '" type="number" >KB * ' + lan.soft.mysql_set_conn + ', <font>' + lan.soft.mysql_set_thread_stack + '</font></p>\
                        <p><span>binlog_cache_size</span><input style="width: 70px;" class="bt-input-text mr5" name="binlog_cache_size" value="' + (binlog_cache_size * 1024) + '" type="number" >KB * ' + lan.soft.mysql_set_conn + ', <font>' + lan.soft.mysql_set_binlog_cache_size + '</font></p>\
                        <p><span>thread_cache_size</span><input style="width: 70px;" class="bt-input-text mr5" name="thread_cache_size" value="' + rdata.mem.thread_cache_size + '" type="number" ><font> ' + lan.soft.mysql_set_thread_cache_size + '</font></p>\
                        <p><span>table_open_cache</span><input style="width: 70px;" class="bt-input-text mr5" name="table_open_cache" value="' + rdata.mem.table_open_cache + '" type="number" > <font>' + lan.soft.mysql_set_table_open_cache + '</font></p>\
                        <p><span>max_connections</span><input style="width: 70px;" class="bt-input-text mr5" name="max_connections" value="' + rdata.mem.max_connections + '" type="number" ><font> ' + lan.soft.mysql_set_max_connections + '</font></p>\
                        <div style="margin-top:10px; padding-right:15px" class="text-right"><button class="btn btn-success btn-sm mr5" onclick="reBootMySqld()">重启数据库</button><button class="btn btn-success btn-sm" onclick="setMySQLConf()">保存</button></div>\
                    </div>'

        $(".soft-man-con").html(memCon);

        $(".conf_p input[name*='size'],.conf_p input[name='max_connections'],.conf_p input[name='thread_stack']").change(function() {
            comMySqlMem();
        });

        $(".conf_p select[name='mysql_set']").change(function() {
            mySQLMemOpt($(this).val());
            comMySqlMem();
        });
    });
}

function reBootMySqld(){
    pluginOpService('mysql-apt','restart','');
}


//设置MySQL配置参数
function setMySQLConf() {
    $.post('/system/system_total', '', function(memInfo) {
        var memSize = memInfo['memTotal'];
        var setSize = parseInt($("input[name='memSize']").val());
        
        if(memSize < setSize){
            var errMsg = "错误,内存分配过高!<p style='color:red;'>物理内存: {1}MB<br>最大使用内存: {2}MB<br>可能造成的后果: 导致数据库不稳定,甚至无法启动MySQLd服务!";
            var msg = errMsg.replace('{1}',memSize).replace('{2}',setSize);
            layer.msg(msg,{icon:2,time:5000});
            return;
        }

        var query_cache_size = parseInt($("input[name='query_cache_size']").val());
        var query_cache_type = 0;
        if (query_cache_size > 0) {
            query_cache_type = 1;
        }
        var data = {
            key_buffer_size: parseInt($("input[name='key_buffer_size']").val()),
            query_cache_size: query_cache_size,
            query_cache_type: query_cache_type,
            tmp_table_size: parseInt($("input[name='tmp_table_size']").val()),
            max_heap_table_size: parseInt($("input[name='tmp_table_size']").val()),
            innodb_buffer_pool_size: parseInt($("input[name='innodb_buffer_pool_size']").val()),
            innodb_log_buffer_size: parseInt($("input[name='innodb_log_buffer_size']").val()),
            sort_buffer_size: parseInt($("input[name='sort_buffer_size']").val()),
            read_buffer_size: parseInt($("input[name='read_buffer_size']").val()),
            read_rnd_buffer_size: parseInt($("input[name='read_rnd_buffer_size']").val()),
            join_buffer_size: parseInt($("input[name='join_buffer_size']").val()),
            thread_stack: parseInt($("input[name='thread_stack']").val()),
            binlog_cache_size: parseInt($("input[name='binlog_cache_size']").val()),
            thread_cache_size: parseInt($("input[name='thread_cache_size']").val()),
            table_open_cache: parseInt($("input[name='table_open_cache']").val()),
            max_connections: parseInt($("input[name='max_connections']").val())
        };

        myPost('set_db_status', data, function(data){
            var rdata = $.parseJSON(data.data);
            showMsg(rdata.msg,function(){
                reBootMySqld();
            },{ icon: rdata.status ? 1 : 2 });
        });
    },'json');
}


//MySQL内存优化方案
function mySQLMemOpt(opt) {
    var query_size = parseInt($("input[name='query_cache_size']").val());
    switch (opt) {
        case '0':
            $("input[name='key_buffer_size']").val(8);
            if (query_size) $("input[name='query_cache_size']").val(4);
            $("input[name='tmp_table_size']").val(8);
            $("input[name='innodb_buffer_pool_size']").val(16);
            $("input[name='innodb_log_buffer_size']").val(32);
            $("input[name='sort_buffer_size']").val(256);
            $("input[name='read_buffer_size']").val(256);
            $("input[name='read_rnd_buffer_size']").val(128);
            $("input[name='join_buffer_size']").val(128);
            $("input[name='thread_stack']").val(256);
            $("input[name='binlog_cache_size']").val(32);
            $("input[name='thread_cache_size']").val(4);
            $("input[name='table_open_cache']").val(32);
            $("input[name='max_connections']").val(500);
            break;
        case '1':
            $("input[name='key_buffer_size']").val(128);
            if (query_size) $("input[name='query_cache_size']").val(64);
            $("input[name='tmp_table_size']").val(64);
            $("input[name='innodb_buffer_pool_size']").val(256);
            $("input[name='innodb_log_buffer_size']").val(32);
            $("input[name='sort_buffer_size']").val(768);
            $("input[name='read_buffer_size']").val(768);
            $("input[name='read_rnd_buffer_size']").val(512);
            $("input[name='join_buffer_size']").val(1024);
            $("input[name='thread_stack']").val(256);
            $("input[name='binlog_cache_size']").val(64);
            $("input[name='thread_cache_size']").val(64);
            $("input[name='table_open_cache']").val(128);
            $("input[name='max_connections']").val(100);
            break;
        case '2':
            $("input[name='key_buffer_size']").val(256);
            if (query_size) $("input[name='query_cache_size']").val(128);
            $("input[name='tmp_table_size']").val(384);
            $("input[name='innodb_buffer_pool_size']").val(384);
            $("input[name='innodb_log_buffer_size']").val(32);
            $("input[name='sort_buffer_size']").val(768);
            $("input[name='read_buffer_size']").val(768);
            $("input[name='read_rnd_buffer_size']").val(512);
            $("input[name='join_buffer_size']").val(2048);
            $("input[name='thread_stack']").val(256);
            $("input[name='binlog_cache_size']").val(64);
            $("input[name='thread_cache_size']").val(96);
            $("input[name='table_open_cache']").val(192);
            $("input[name='max_connections']").val(200);
            break;
        case '3':
            $("input[name='key_buffer_size']").val(384);
            if (query_size) $("input[name='query_cache_size']").val(192);
            $("input[name='tmp_table_size']").val(512);
            $("input[name='innodb_buffer_pool_size']").val(512);
            $("input[name='innodb_log_buffer_size']").val(32);
            $("input[name='sort_buffer_size']").val(1024);
            $("input[name='read_buffer_size']").val(1024);
            $("input[name='read_rnd_buffer_size']").val(768);
            $("input[name='join_buffer_size']").val(2048);
            $("input[name='thread_stack']").val(256);
            $("input[name='binlog_cache_size']").val(128);
            $("input[name='thread_cache_size']").val(128);
            $("input[name='table_open_cache']").val(384);
            $("input[name='max_connections']").val(300);
            break;
        case '4':
            $("input[name='key_buffer_size']").val(512);
            if (query_size) $("input[name='query_cache_size']").val(256);
            $("input[name='tmp_table_size']").val(1024);
            $("input[name='innodb_buffer_pool_size']").val(1024);
            $("input[name='innodb_log_buffer_size']").val(32);
            $("input[name='sort_buffer_size']").val(2048);
            $("input[name='read_buffer_size']").val(2048);
            $("input[name='read_rnd_buffer_size']").val(1024);
            $("input[name='join_buffer_size']").val(4096);
            $("input[name='thread_stack']").val(384);
            $("input[name='binlog_cache_size']").val(192);
            $("input[name='thread_cache_size']").val(192);
            $("input[name='table_open_cache']").val(1024);
            $("input[name='max_connections']").val(400);
            break;
        case '5':
            $("input[name='key_buffer_size']").val(1024);
            if (query_size) $("input[name='query_cache_size']").val(384);
            $("input[name='tmp_table_size']").val(2048);
            $("input[name='innodb_buffer_pool_size']").val(4096);
            $("input[name='innodb_log_buffer_size']").val(32);
            $("input[name='sort_buffer_size']").val(4096);
            $("input[name='read_buffer_size']").val(4096);
            $("input[name='read_rnd_buffer_size']").val(2048);
            $("input[name='join_buffer_size']").val(8192);
            $("input[name='thread_stack']").val(512);
            $("input[name='binlog_cache_size']").val(256);
            $("input[name='thread_cache_size']").val(256);
            $("input[name='table_open_cache']").val(2048);
            $("input[name='max_connections']").val(500);
            break;
    }
}

//计算MySQL内存开销
function comMySqlMem() {
    var key_buffer_size = parseInt($("input[name='key_buffer_size']").val());
    var query_cache_size = parseInt($("input[name='query_cache_size']").val());
    var tmp_table_size = parseInt($("input[name='tmp_table_size']").val());
    var innodb_buffer_pool_size = parseInt($("input[name='innodb_buffer_pool_size']").val());
    var innodb_additional_mem_pool_size = parseInt($("input[name='innodb_additional_mem_pool_size']").val());
    var innodb_log_buffer_size = parseInt($("input[name='innodb_log_buffer_size']").val());

    var sort_buffer_size = $("input[name='sort_buffer_size']").val() / 1024;
    var read_buffer_size = $("input[name='read_buffer_size']").val() / 1024;
    var read_rnd_buffer_size = $("input[name='read_rnd_buffer_size']").val() / 1024;
    var join_buffer_size = $("input[name='join_buffer_size']").val() / 1024;
    var thread_stack = $("input[name='thread_stack']").val() / 1024;
    var binlog_cache_size = $("input[name='binlog_cache_size']").val() / 1024;
    var max_connections = $("input[name='max_connections']").val();

    var a = key_buffer_size + query_cache_size + tmp_table_size + innodb_buffer_pool_size + innodb_additional_mem_pool_size + innodb_log_buffer_size
    var b = sort_buffer_size + read_buffer_size + read_rnd_buffer_size + join_buffer_size + thread_stack + binlog_cache_size
    var memSize = a + max_connections * b
    $("input[name='memSize']").val(memSize.toFixed(2));
}

function syncGetDatabase(){
    myPost('sync_get_databases', null, function(data){
        var rdata = $.parseJSON(data.data);
        showMsg(rdata.msg,function(){
            dbList();
        },{ icon: rdata.status ? 1 : 2 });
    });
}

function syncToDatabase(type){
    var data = [];
    $('input[type="checkbox"].check:checked').each(function () {
        if (!isNaN($(this).val())) data.push($(this).val());
    });
    var postData = 'type='+type+'&ids='+JSON.stringify(data); 
    myPost('sync_to_databases', postData, function(data){
        var rdata = $.parseJSON(data.data);
        // console.log(rdata);
        showMsg(rdata.msg,function(){
            dbList();
        },{ icon: rdata.status ? 1 : 2 });
    });
}

function setRootPwd(type, pwd){
    if (type==1){
        var password = $("#MyPassword").val();
        myPost('set_root_pwd', {password:password}, function(data){
            var rdata = $.parseJSON(data.data);
            showMsg(rdata.msg,function(){
                dbList();
                $('.layui-layer-close1').click();
            },{icon: rdata.status ? 1 : 2});   
        });
        return;
    }

    var index = layer.open({
        type: 1,
        area: '500px',
        title: '修改数据库密码',
        closeBtn: 1,
        shift: 5,
        btn:["提交","关闭"],
        shadeClose: true,
        content: "<form class='bt-form pd20' id='mod_pwd'>\
                    <div class='line'>\
                        <span class='tname'>root密码</span>\
                        <div class='info-r'><input class='bt-input-text mr5' type='text' name='password' id='MyPassword' style='width:330px' value='"+pwd+"' />\
                            <span title='随机密码' class='glyphicon glyphicon-repeat cursor' onclick='repeatPwd(16)'></span>\
                        </div>\
                    </div>\
                  </form>",
        yes:function(){
            setRootPwd(1);
        }
    });
}

function fixRootPwd(type){
    if (type==1){
        var password = $("#FixPassword").val();
        myPost('fix_root_pwd', {password:password}, function(data){
            var rdata = $.parseJSON(data.data);
            showMsg(rdata.msg,function(){
                dbList();
                $('.layui-layer-close1').click();
            },{icon: rdata.status ? 1 : 2});   
        });
        return;
    }

    var index = layer.open({
        type: 1,
        area: '500px',
        title: '修复ROOT密码',
        closeBtn: 1,
        shift: 5,
        btn:["提交","关闭"],
        shadeClose: true,
        content: "<form class='bt-form pd20' id='mod_pwd'>\
                    <div class='line'>\
                        <span class='tname'>root密码</span>\
                        <div class='info-r'><input class='bt-input-text mr5' placeholder='更新真实ROOT密码到江湖面板' type='text' name='password' id='FixPassword' style='width:330px' value='' /></div>\
                    </div>\
                  </form>",
        yes:function(){
            fixRootPwd(1);
        }
    });
}

function showHidePass(obj){
    var a = "glyphicon-eye-open";
    var b = "glyphicon-eye-close";
    
    if($(obj).hasClass(a)){
        $(obj).removeClass(a).addClass(b);
        $(obj).prev().text($(obj).prev().attr('data-pw'))
    }
    else{
        $(obj).removeClass(b).addClass(a);
        $(obj).prev().text('***');
    }
}

function copyPass(password){
    var clipboard = new ClipboardJS('#bt_copys');
    clipboard.on('success', function (e) {
        layer.msg('复制成功',{icon:1,time:2000});
    });

    clipboard.on('error', function (e) {
        layer.msg('复制失败，浏览器不兼容!',{icon:2,time:2000});
    });
    $("#bt_copys").attr('data-clipboard-text',password);
    $("#bt_copys").click();
}

function checkSelect(){
    $('#DataBody').find('tr').each(function(i,obj){
        var fin = $(this).find('td')[0];
        checked = $(fin).find('input').prop('checked');
        $(fin).find('input').prop('checked',!checked);
    });
}

function setDbRw(id,username,val){
    myPost('set_db_rw',{id:id,username:username,rw:val}, function(data){
        var rdata = $.parseJSON(data.data);
        // layer.msg(rdata.msg,{icon:rdata.status ? 1 : 5,shade: [0.3, '#000']});
        showMsg(rdata.msg, function(){
            dbList();
        },{icon:rdata.status ? 1 : 5,shade: [0.3, '#000']}, 2000);

    });
}

function setDbAccess(username){
    myPost('get_db_access','username='+username, function(data){
        var rdata = $.parseJSON(data.data);
        if (!rdata.status){
            layer.msg(rdata.msg,{icon:2,shade: [0.3, '#000']});
            return;
        }
        
        var index = layer.open({
            type: 1,
            area: '500px',
            title: '设置数据库权限',
            closeBtn: 1,
            shift: 5,
            btn:["提交","取消"],
            shadeClose: true,
            content: "<form class='bt-form pd20' id='set_db_access'>\
                        <div class='line'>\
                            <span class='tname'>访问权限</span>\
                            <div class='info-r '>\
                                <select class='bt-input-text mr5' name='dataAccess' style='width:100px'>\
                                <option value='127.0.0.1'>本地服务器</option>\
                                <option value=\"%\">所有人</option>\
                                <option value='ip'>指定IP</option>\
                                </select>\
                            </div>\
                        </div>\
                      </form>",
            success:function(){
                if (rdata.msg == '127.0.0.1'){
                    $('select[name="dataAccess"]').find("option[value='127.0.0.1']").attr("selected",true);
                } else if (rdata.msg == '%'){
                    $('select[name="dataAccess"]').find('option[value="%"]').attr("selected",true);
                } else if ( rdata.msg == 'ip' ){
                    $('select[name="dataAccess"]').find('option[value="ip"]').attr("selected",true);
                    $('select[name="dataAccess"]').after("<input id='dataAccess_subid' class='bt-input-text mr5' type='text' name='address' placeholder='多个IP使用逗号(,)分隔' style='width: 230px; display: inline-block;'>");
                } else {
                    $('select[name="dataAccess"]').find('option[value="ip"]').attr("selected",true);
                    $('select[name="dataAccess"]').after("<input value='"+rdata.msg+"' id='dataAccess_subid' class='bt-input-text mr5' type='text' name='address' placeholder='多个IP使用逗号(,)分隔' style='width: 230px; display: inline-block;'>");
                }

                 $('select[name="dataAccess"]').change(function(){
                    var v = $(this).val();
                    if (v == 'ip'){
                        $(this).after("<input id='dataAccess_subid' class='bt-input-text mr5' type='text' name='address' placeholder='多个IP使用逗号(,)分隔' style='width: 230px; display: inline-block;'>");
                    } else {
                        $('#dataAccess_subid').remove();
                    }
                });
            },
            yes:function(index){
                var data = $("#set_db_access").serialize();
                data = decodeURIComponent(data);
                var dataObj = toArrayObject(data);
                if(!dataObj['access']){
                    dataObj['access'] = dataObj['dataAccess'];
                    if ( dataObj['dataAccess'] == 'ip'){
                        if (dataObj['address']==''){
                            layer.msg('IP地址不能空!',{icon:2,shade: [0.3, '#000']});
                            return;
                        }
                        dataObj['access'] = dataObj['address'];
                    }
                }
                dataObj['username'] = username;
                myPost('set_db_access', dataObj, function(data){
                    var rdata = $.parseJSON(data.data);
                    showMsg(rdata.msg,function(){
                        layer.close(index);
                        dbList();
                    },{icon: rdata.status ? 1 : 2});   
                });
            }
        });

    });
}

async function getChecksumReport() {
    showLogWindow('正在计算checksum...', { logPath: '/logs/mysql_checksum_opt.log', autoClearLog: false }, function({layerIndex}){
		myPost('get_checksum_report', '', function(rdata){
            var rdata = $.parseJSON(rdata.data);
            showMsg(rdata.msg,function(){
                layer.close(layerIndex);
                
                openEditCodeFile({
                    title: 'MySQL Checksum报告',
                    path: '/www/server/jh-panel/tmp/mysql_checksum_report.txt',
                    width: '640px',
                    height: '500px',
                    showBtnPanel: false
                })
                
            },{icon: rdata.status ? 1 : 2}); 
        });
	});	
  
}

function fixDbAccess(username){
    myPost('fix_db_access', '', function(rdata){
        var rdata = $.parseJSON(rdata.data);
        showMsg(rdata.msg,function(){
            dbList();
        },{icon: rdata.status ? 1 : 2}); 
    });
}

function setDbPass(id, username, password){
    layer.open({
        type: 1,
        area: '500px',
        title: '修改数据库密码',
        closeBtn: 1,
        shift: 5,
        shadeClose: true,
        btn:["提交","关闭"],
        content: "<form class='bt-form pd20' id='mod_pwd'>\
                    <div class='line'>\
                        <span class='tname'>用户名</span>\
                        <div class='info-r'><input readonly='readonly' name=\"name\" class='bt-input-text mr5' type='text' style='width:330px;outline:none;' value='"+username+"' /></div>\
                    </div>\
                    <div class='line'>\
                    <span class='tname'>密码</span>\
                    <div class='info-r'>\
                        <input class='bt-input-text mr5' type='text' name='password' id='MyPassword' style='width:330px' value='"+password+"' />\
                        <span title='随机密码' class='glyphicon glyphicon-repeat cursor' onclick='repeatPwd(16)'></span></div>\
                    </div>\
                    <input type='hidden' name='id' value='"+id+"'>\
                  </form>",
        yes:function(index){
            // var data = $("#mod_pwd").serialize();
            var data = {};
            data['name'] = $('input[name=name]').val();
            data['password'] = $('#MyPassword').val();
            data['id'] = $('#mod_pwd input[name=id]').val();
            myPost('set_user_pwd', data, function(data){
                var rdata = $.parseJSON(data.data);
                showMsg(rdata.msg,function(){
                    layer.close(index);
                    dbList();
                },{icon: rdata.status ? 1 : 2});   
            });
        }
    });
}

function addDatabase(type){
    layer.open({
        type: 1,
        area: '500px',
        title: '添加数据库',
        closeBtn: 1,
        shift: 5,
        shadeClose: true,
        btn:["提交","关闭"],
        content: "<form class='bt-form pd20' id='add_db'>\
                    <div class='line'>\
                        <span class='tname'>数据库名</span>\
                        <div class='info-r'><input name='name' class='bt-input-text mr5' placeholder='新的数据库名称' type='text' style='width:65%' value=''>\
                        <select class='bt-input-text mr5 codeing_a5nGsm' name='codeing' style='width:27%'>\
                            <option value='utf8mb4'>utf8mb4</option>\
                            <option value='utf8'>utf-8</option>\
                            <option value='gbk'>gbk</option>\
                            <option value='big5'>big5</option>\
                        </select>\
                        </div>\
                    </div>\
                    <div class='line'><span class='tname'>用户名</span><div class='info-r'><input name='db_user' class='bt-input-text mr5' placeholder='数据库用户' type='text' style='width:65%' value=''></div></div>\
                    <div class='line'>\
                    <span class='tname'>密码</span>\
                    <div class='info-r'><input class='bt-input-text mr5' type='text' name='password' id='MyPassword' style='width:330px' value='"+(randomStrPwd(16))+"' /><span title='随机密码' class='glyphicon glyphicon-repeat cursor' onclick='repeatPwd(16)'></span></div>\
                    </div>\
                    <div class='line'>\
                        <span class='tname'>访问权限</span>\
                        <div class='info-r '>\
                            <select class='bt-input-text mr5' name='dataAccess' style='width:100px'>\
                            <option value='127.0.0.1'>本地服务器</option>\
                            <option value=\"%\">所有人</option>\
                            <option value='ip'>指定IP</option>\
                            </select>\
                        </div>\
                    </div>\
                    <input type='hidden' name='ps' value='' />\
                  </form>",
        success:function(){
            $("input[name='name']").keyup(function(){
                var v = $(this).val();
                $("input[name='db_user']").val(v);
                $("input[name='ps']").val(v);
            });

            $('select[name="dataAccess"]').change(function(){
                var v = $(this).val();
                if (v == 'ip'){
                    $(this).after("<input id='dataAccess_subid' class='bt-input-text mr5' type='text' name='address' placeholder='多个IP使用逗号(,)分隔' style='width: 230px; display: inline-block;'>");
                } else {
                    $('#dataAccess_subid').remove();
                }
            });
        },
        yes:function(index) {
            var data = $("#add_db").serialize();
            data = decodeURIComponent(data);
            var dataObj = toArrayObject(data);
            if(!dataObj['address']){
                dataObj['address'] = dataObj['dataAccess'];
            }
            myPost('add_db', dataObj, function(data){
                var rdata = $.parseJSON(data.data);
                showMsg(rdata.msg,function(){
                    if (rdata.status){
                        layer.close(index);
                        dbList();
                    }
                },{icon: rdata.status ? 1 : 2},600);
            });
        }
    });
}

function delDb(id, name){
    safeMessage('删除['+name+']','您真的要删除['+name+']吗？',function(){
        var data='id='+id+'&name='+name
        myPost('del_db', data, function(data){
            var rdata = $.parseJSON(data.data);
            showMsg(rdata.msg,function(){
                dbList();
            },{icon: rdata.status ? 1 : 2}, 600);
        });
    });
}

function delDbBatch(){
    var arr = [];
    $('input[type="checkbox"].check:checked').each(function () {
        var _val = $(this).val();
        var _name = $(this).parent().next().text();
        if (!isNaN(_val)) {
            arr.push({'id':_val,'name':_name});
        }
    });

    safeMessage('批量删除数据库','<a style="color:red;">您共选择了[2]个数据库,删除后将无法恢复,真的要删除吗?</a>',function(){
        var i = 0;
        $(arr).each(function(){
            var data  = myAsyncPost('del_db', this);
            var rdata = $.parseJSON(data.data);
            if (!rdata.status){
                layer.msg(rdata.msg,{icon:2,time:2000,shade: [0.3, '#000']});
            }
            i++;
        });
        
        var msg = '成功删除['+i+']个数据库!';
        showMsg(msg,function(){
            dbList();
        },{icon: 1}, 600);
    });
}


function setDbPs(id, name, obj) {
    var _span = $(obj);
    var _input = $("<input class='baktext' value=\""+_span.text()+"\" type='text' placeholder='备注信息' />");
    _span.hide().after(_input);
    _input.focus();
    _input.blur(function(){
        $(this).remove();
        var ps = _input.val();
        _span.text(ps).show();
        var data = {name:name,id:id,ps:ps};
        myPost('set_db_ps', data, function(data){
            var rdata = $.parseJSON(data.data);
            layer.msg(rdata.msg, { icon: rdata.status ? 1 : 2 });
        });
    });
    _input.keyup(function(){
        if(event.keyCode == 13){
            _input.trigger('blur');
        }
    });
}

function openPhpmyadmin(name,username,password){

    data = syncPost('/plugins/check',{'name':'phpmyadmin'});


    if (!data.status){
        layer.msg(data.msg,{icon:2,shade: [0.3, '#000']});
        return;
    }

    data = syncPost('/plugins/run',{'name':'phpmyadmin','func':'status'});
    if (data.data != 'start'){
        layer.msg('phpMyAdmin未启动',{icon:2,shade: [0.3, '#000']});
        return;
    }

    data = syncPost('/plugins/run',{'name':'phpmyadmin','func':'get_cfg'});
    var rdata = $.parseJSON(data.data);
    if (rdata.choose != 'mysql-apt'){
        layer.msg('当前为['+rdata.choose+']模式,若要使用请切换模式.',{icon:2,shade: [0.3, '#000']});
        return;
    }

    var phpmyadmin_cfg = rdata;
    data = syncPost('/plugins/run',{'name':'phpmyadmin','func':'get_home_page'});
    var rdata = $.parseJSON(data.data);
    if (!rdata.status){
        layer.msg(rdata.msg,{icon:2,shade: [0.3, '#000']});
        return;
    }
    var home_page = rdata.data;

    home_page = home_page.replace("http://","http://"+phpmyadmin_cfg['username']+":"+phpmyadmin_cfg['password']+"@")

    $("#toPHPMyAdmin").attr('action',home_page);
    if($("#toPHPMyAdmin").attr('action').indexOf('phpmyadmin') == -1){
        layer.msg('请先安装phpMyAdmin',{icon:2,shade: [0.3, '#000']});
        setTimeout(function(){ window.location.href = '/soft'; },3000);
        return;
    }

    //检查版本
    data = syncPost('/plugins/run',{'name':'phpmyadmin','func':'version'});
    bigVer = data.data.split('.')[0];
    if (bigVer>=4.5){

        setTimeout(function(){
            $("#toPHPMyAdmin").submit();
        },3000);
        layer.msg('phpMyAdmin['+data.data+']需要手动登录😭',{icon:16,shade: [0.3, '#000'],time:4000});
        
    } else{
        var murl = $("#toPHPMyAdmin").attr('action');
        $("#pma_username").val(username);
        $("#pma_password").val(password);
        $("#db").val(name);

        layer.msg('正在打开phpMyAdmin',{icon:16,shade: [0.3, '#000'],time:2000});

        setTimeout(function(){
            $("#toPHPMyAdmin").submit();
        },3000);
    }    
}

function delBackup(filename, name, path){
    if(typeof(path) == "undefined"){
        path = "";
    }
    myPost('delete_db_backup',{filename:filename,path:path},function(){
        layer.msg('执行成功!');
        setTimeout(function(){
            setBackupReq(name);
        },2000);
    });
}

function downloadBackup(file){
    window.open('/files/download?filename='+encodeURIComponent(file));
}

function importBackup(file,name){
    // myPost('import_db_backup',{file:file,name:name}, function(data){
    //     layer.msg('执行成功!');
    // });
    myPost('get_import_db_backup_script',{file:file,name:name}, function(data){
        let rdata = $.parseJSON(data.data);
        openEditCodeAndExcute({
            title: '执行恢复',
            name: '执行mysql插件操作[恢复]',
            content: rdata.data
        })
    });
    
}


function importDbExternal(file,name){
    myPost('import_db_external',{file:file,name:name}, function(data){
        layer.msg('执行成功!');
    });
}

function setLocalImport(db_name){

    //上传文件
    function uploadDbFiles(upload_dir){
        var up_db = layer.open({
            type:1,
            closeBtn: 1,
            title:"上传导入文件["+upload_dir+']',
            area: ['500px','300px'],
            shadeClose:false,
            content:'<div class="fileUploadDiv">\
                    <input type="hidden" id="input-val" value="'+upload_dir+'" />\
                    <input type="file" id="file_input"  multiple="true" autocomplete="off" />\
                    <button type="button"  id="opt" autocomplete="off">添加文件</button>\
                    <button type="button" id="up" autocomplete="off" >开始上传</button>\
                    <span id="totalProgress" style="position: absolute;top: 7px;right: 147px;"></span>\
                    <span style="float:right;margin-top: 9px;">\
                    <font>文件编码:</font>\
                    <select id="fileCodeing" >\
                        <option value="byte">二进制</option>\
                        <option value="utf-8">UTF-8</option>\
                        <option value="gb18030">GB2312</option>\
                    </select>\
                    </span>\
                    <button type="button" id="filesClose" autocomplete="off">关闭</button>\
                    <ul id="up_box"></ul>\
                </div>',
            success:function(){
                $('#filesClose').click(function(){
                    layer.close(up_db);
                });
            }

        });
        uploadStart(function(){
            getList();
            layer.close(up_db);
        });
    }

    function getList(){
        myPost('get_db_backup_import_list',{}, function(data){
            var rdata = $.parseJSON(data.data);

            var file_list = rdata.data.list;
            var upload_dir = rdata.data.upload_dir;

            var tbody = '';
            for (var i = 0; i < file_list.length; i++) {
                tbody += '<tr>\
                        <td><span> ' + file_list[i]['name'] + '</span></td>\
                        <td><span> ' + file_list[i]['size'] + '</span></td>\
                        <td><span> ' + file_list[i]['time'] + '</span></td>\
                        <td style="text-align: right;">\
                            <a class="btlink" onclick="importDbExternal(\'' + file_list[i]['name'] + '\',\'' +db_name+ '\')">恢复</a> | \
                            <a class="btlink del" index="'+i+'">删除</a>\
                        </td>\
                    </tr>';
            }

            $('#import_db_file_list').html(tbody);
            $('input[name="upload_dir"]').val(upload_dir);

            $("#import_db_file_list .del").on('click',function(){
                var index = $(this).attr('index');
                var filename = file_list[index]["name"];
                myPost('delete_db_backup',{filename:filename,path:upload_dir},function(){
                    showMsg('执行成功!', function(){
                        getList();
                    },{icon:1},2000);
                });
            });
        });
    }

    var layerIndex = layer.open({
        type: 1,
        title: "从文件导入数据",
        area: ['600px', '380px'],
        closeBtn: 1,
        shadeClose: false,
        content: '<div class="pd15">\
                    <div class="db_list">\
                        <button id="btn_file_upload" class="btn btn-success btn-sm" type="button">从本地上传</button>\
                    </div >\
                    <div class="divtable">\
                    <input type="hidden" name="upload_dir" value=""> \
                    <div id="database_fix"  style="height:150px;overflow:auto;border:#ddd 1px solid">\
                    <table class="table table-hover "style="border:none">\
                        <thead>\
                            <tr>\
                                <th>文件名称</th>\
                                <th>文件大小</th>\
                                <th>备份时间</th>\
                                <th style="text-align: right;">操作</th>\
                            </tr>\
                        </thead>\
                        <tbody  id="import_db_file_list" class="gztr"></tbody>\
                    </table>\
                    </div>\
                    <ul class="help-info-text c7">\
                        <li>仅支持sql、zip、sql.gz、(tar.gz|gz|tgz|zst)</li>\
                        <li>zip、tar.gz压缩包结构：test.zip或test.tar.gz压缩包内，必需包含test.sql</li>\
                        <li>若文件过大，您还可以使用SFTP工具，将数据库文件上传到/www/backup/import</li>\
                    </ul>\
                </div>\
        </div>',
        success:function(index){
            $('#btn_file_upload').click(function(){
                var upload_dir = $('input[name="upload_dir"]').val();
                uploadDbFiles(upload_dir);
            });

            getList();
        },
    });

    
}

function setBackup(db_name){
    var layerIndex = layer.open({
        type: 1,
        title: "数据库备份详情",
        area: ['750px', '300px'],
        closeBtn: 1,
        shadeClose: false,
        content: '<div class="pd15">\
                    <div class="db_list">\
                        <button id="btn_backup" class="btn btn-success btn-sm" type="button">备份（mydumper,快）</button>\
                        <button id="btn_backup_old" class="btn btn-success btn-sm" type="button">备份（mysqldump,小）</button>\
                        <button id="btn_local_import" class="btn btn-success btn-sm" type="button">外部导入</button>\
                    </div >\
                    <div class="divtable">\
                    <div  id="database_fix"  style="height:180px;overflow:auto;border:#ddd 1px solid">\
                    <table id="database_table" class="table table-hover "style="border:none">\
                        <thead>\
                            <tr>\
                                <th>文件名称</th>\
                                <th>文件大小</th>\
                                <th>备份时间</th>\
                                <th style="text-align: right;width: 110px;">操作</th>\
                            </tr>\
                        </thead>\
                        <tbody class="list"></tbody>\
                    </table>\
                    </div>\
                </div>\
        </div>',
        success:function(index){
            $('#btn_backup').click(function(){
                myPost('set_db_backup',{name:db_name, exec_type: 'mydumper'}, function(data){
                    showMsg('执行成功!', function(){
                        setBackupReq(db_name);
                    }, {icon:1}, 2000);
                });
            });

            $('#btn_backup_old').click(function(){
                myPost('set_db_backup',{name:db_name, exec_type: 'mysqldump'}, function(data){
                    showMsg('执行成功!', function(){
                        setBackupReq(db_name);
                    }, {icon:1}, 2000);
                });
            });

            $('#btn_local_import').click(function(){
                setLocalImport(db_name);
            });

            setBackupReq(db_name);
        },
    });
}


function setBackupReq(db_name, obj){
     myPost('get_db_backup_list', {name:db_name}, function(data){
        var rdata = $.parseJSON(data.data);
        var tbody = '';
        for (var i = 0; i < rdata.data.length; i++) {
            tbody += '<tr>\
                    <td><span> ' + rdata.data[i]['name'] + '</span></td>\
                    <td><span> ' + rdata.data[i]['size'] + '</span></td>\
                    <td><span> ' + rdata.data[i]['time'] + '</span></td>\
                    <td style="text-align: right;">\
                        <a class="btlink" onclick="importBackup(\'' + rdata.data[i]['name'] + '\',\'' +db_name+ '\')">恢复</a> | \
                        <a class="btlink" onclick="downloadBackup(\'' + rdata.data[i]['file'] + '\')">下载</a> | \
                        <a class="btlink" onclick="delBackup(\'' + rdata.data[i]['name'] + '\',\'' +db_name+ '\')">删除</a>\
                    </td>\
                </tr> ';
        }
        $('#database_table tbody').html(tbody);
    });
}

function dbList(page, search){
    var _data = {};
    if (typeof(page) =='undefined'){
        var page = 1;
    }
    
    _data['page'] = page;
    // _data['page_size'] = 10;
    _data['page_size'] = 1000;
    if(typeof(search) != 'undefined'){
        _data['search'] = search;
    }
    myPost('get_db_list_page', _data, function(data){
        var rdata = $.parseJSON(data.data);
        var list = '';
        for(i in rdata.data){
            list += '<tr>';
            list +='<td><input value="'+rdata.data[i]['id']+'" class="check" type="checkbox"></td>';
            list += '<td>' + rdata.data[i]['name'] +'</td>';
            list += '<td>' + rdata.data[i]['username'] +'</td>';
            list += '<td>' + 
                        '<span class="password" data-pw="'+rdata.data[i]['password']+`">${rdata.data[i]['password'] ? '***' : '<font color="red">密码未记录</font>'}</span>` +
                        '<span onclick="showHidePass(this)" class="glyphicon glyphicon-eye-open cursor pw-ico" style="margin-left:10px"></span>'+
                        '<span class="ico-copy cursor btcopy" style="margin-left:10px" title="复制密码" onclick="copyPass(\''+rdata.data[i]['password']+'\')"></span>'+
                    '</td>';
        

            list += '<td><span class="c9 input-edit" onclick="setDbPs(\''+rdata.data[i]['id']+'\',\''+rdata.data[i]['name']+'\',this)" style="display: inline-block;">'+rdata.data[i]['ps']+'</span></td>';
            list += '<td style="text-align:right;">';

            list += '<a href="javascript:;" class="btlink" class="btlink" onclick="setBackup(\''+rdata.data[i]['name']+'\',this)" title="数据库备份">'+(rdata.data[i]['is_backup']?'备份':'未备份') +'</a> | ';

            var rw = '';
            var rw_change = 'all';
            if (typeof(rdata.data[i]['rw'])!='undefined'){
                var rw_val = '读写';
                if (rdata.data[i]['rw'] == 'all'){
                    rw_val = "所有";
                    rw_change = 'rw';
                } else if (rdata.data[i]['rw'] == 'rw'){
                    rw_val = "读写";
                    rw_change = 'r';
                } else if (rdata.data[i]['rw'] == 'r'){
                    rw_val = "只读";
                    rw_change = 'all';
                }
                rw = '<a href="javascript:;" class="btlink" onclick="setDbRw(\''+rdata.data[i]['id']+'\',\''+rdata.data[i]['name']+'\',\''+rw_change+'\')" title="设置读写">'+rw_val+'</a> | ';
            }


            list += '<a href="javascript:;" class="btlink" onclick="openPhpmyadmin(\''+rdata.data[i]['name']+'\',\''+rdata.data[i]['username']+'\',\''+rdata.data[i]['password']+'\')" title="数据库管理">管理</a> | ' +
                        '<a href="javascript:;" class="btlink" onclick="repTools(\''+rdata.data[i]['name']+'\')" title="MySQL优化修复工具">工具</a> | ' +
                        '<a href="javascript:;" class="btlink" onclick="setDbAccess(\''+rdata.data[i]['username']+'\')" title="设置数据库权限">权限</a> | ' +
                        rw +
                        '<a href="javascript:;" class="btlink" onclick="setDbPass('+rdata.data[i]['id']+',\''+ rdata.data[i]['username'] +'\',\'' + rdata.data[i]['password'] + '\')">改密</a> | ' +
                        '<a href="javascript:;" class="btlink" onclick="delDb(\''+rdata.data[i]['id']+'\',\''+rdata.data[i]['name']+'\')" title="删除数据库">删除</a>' +
                    '</td>';
            list += '</tr>';
        }

        //<button onclick="" id="dataRecycle" title="删除选中项" class="btn btn-default btn-sm" style="margin-left: 5px;"><span class="glyphicon glyphicon-trash" style="margin-right: 5px;"></span>回收站</button>
        //<button onclick="fixDbAccess(\'root\')" title="修复" class="btn btn-default btn-sm" type="button" style="margin-right: 5px;">修复</button>\
        var con = '<div class="safe bgw">\
            <button onclick="addDatabase()" title="添加数据库" class="btn btn-success btn-sm" type="button" style="margin-right: 5px;">添加数据库</button>\
            <button onclick="setRootPwd(0,\''+rdata.info['root_pwd']+'\')" title="设置MySQL管理员密码" class="btn btn-default btn-sm" type="button" style="margin-right: 5px;">root密码</button>\
            <button onclick="fixRootPwd(0)" title="更新真实ROOT密码到江湖面板" class="btn btn-default btn-sm" type="button" style="margin-right: 5px;">修复ROOT密码</button>\
            <button onclick="setDbAccess(\'root\')" title="ROOT权限" class="btn btn-default btn-sm" type="button" style="margin-right: 5px;">ROOT权限</button>\
            <button onclick="openMysqlTerminal()" title="打开MySQL终端" class="btn btn-default btn-sm" type="button" style="margin-right: 5px;">打开终端</button>\
            <button onclick="getChecksumReport()" title="获取Checksum报告" class="btn btn-default btn-sm" type="button" style="margin-right: 5px;">获取Checksum报告</button>\
            <span style="float:right">              \
                <button batch="true" style="float: right;display: none;margin-left:10px;" onclick="delDbBatch();" title="删除选中项" class="btn btn-default btn-sm">删除选中</button>\
            </span>\
            <div class="divtable mtb10">\
                <div class="tablescroll">\
                    <table id="DataBody" class="table table-hover" width="100%" cellspacing="0" cellpadding="0" border="0" style="border: 0 none;">\
                    <tr><th width="30"><input class="check" onclick="checkSelect();" type="checkbox"></th>\
                    <th>数据库名</th>\
                    <th>用户名</th>\
                    <th style="min-width: 180px;">密码</th>\
                    '+
                    // '<th>备份</th>'+
                    '<th>备注</th>\
                    <th style="text-align:right; min-width: 154px;" width="154px" fixed="true">操作</th></tr>\
                    <tbody>\
                    '+ list +'\
                    </tbody></table>\
                    <tfoot>\
                    <span>共 <b class="databases-count">' + rdata.data.length + '</b> 个数据库</span>\
                  </tfoot>\
                </div>\
                <div id="databasePage" class="dataTables_paginate paging_bootstrap page"></div>\
                <div class="table_toolbar" style="left:0px;">\
                    <span class="sync btn btn-default btn-sm" style="margin-right:5px" onclick="syncToDatabase(1)" title="将选中数据库信息同步到服务器">同步选中</span>\
                    <span class="sync btn btn-default btn-sm" style="margin-right:5px" onclick="syncToDatabase(0)" title="将所有数据库信息同步到服务器">同步所有</span>\
                    <span class="sync btn btn-default btn-sm" onclick="syncGetDatabase()" title="从服务器获取数据库列表">从服务器获取</span>\
                </div>\
            </div>\
        </div>';

        con += '<form id="toPHPMyAdmin" action="" method="post" style="display: none;" target="_blank">\
            <input type="text" name="pma_username" id="pma_username" value="">\
            <input type="password" name="pma_password" id="pma_password" value="">\
            <input type="text" name="server" value="1">\
            <input type="text" name="target" value="index.php">\
            <input type="text" name="db" id="db" value="">\
        </form>';

        $(".soft-man-con").html(con); 
        // $('#databasePage').html(rdata.page);

        readerTableChecked();
    });
}


function myLogs(){
    
    myPost('bin_log', {status:1}, function(data){
        var rdata = $.parseJSON(data.data);

        var line_status = ""
        if (rdata.status){
            line_status = '<button class="btn btn-success btn-xs btn-bin va0">关闭</button>\
                        <button class="btn btn-success btn-xs clean-btn-bin va0">清理BINLOG日志</button>';
        } else {
            line_status = '<button class="btn btn-success btn-xs btn-bin va0">开启</button>';
        }

        var limitCon = '<p class="conf_p">\
                        <span class="f14 c6 mr20">二进制日志 </span><span class="f14 c6 mr20">' + toSize(rdata.msg) + '</span>\
                        '+line_status+'\
                        <p class="f14 c6 mtb10" style="border-top:#ddd 1px solid; padding:10px 0">错误日志<button class="btn btn-default btn-clear btn-xs" style="float:right;" >清理日志</button></p>\
                        <textarea readonly style="margin: 0px;width: 100%;height: 440px;background-color: #333;color:#fff; padding:0 5px" id="error_log"></textarea>\
                    </p>';
        $(".soft-man-con").html(limitCon);

        //设置二进制日志
        $(".btn-bin").click(function () {
            myPost('bin_log', 'close=change', function(data){
                var rdata = $.parseJSON(data.data);
                layer.msg(rdata.msg, { icon: rdata.status ? 1 : 5 });
                setTimeout(function(){myLogs();}, 2000);
            });
        });

        $(".clean-btn-bin").click(function () {
            myPost('clean_bin_log', '', function(data){
                var rdata = $.parseJSON(data.data);
                layer.msg(rdata.msg, { icon: rdata.status ? 1 : 5 });
                setTimeout(function(){myLogs();}, 2000);
            });
        });

         //清空日志
        $(".btn-clear").click(function () {
            myPost('error_log', 'close=1', function(data){
                var rdata = $.parseJSON(data.data);
                layer.msg(rdata.msg, { icon: rdata.status ? 1 : 5 });
                setTimeout(function(){myLogs();}, 2000);
            });
        })

        myPost('error_log', 'p=1', function(data){
            var rdata = $.parseJSON(data.data);
            var error_body = '';
            if (rdata.status){
                error_body = rdata.data;
            } else {
                error_body = rdata.msg;
            }
            $("#error_log").html(error_body);
            var ob = document.getElementById('error_log');
            ob.scrollTop = ob.scrollHeight;
        });
    });
}


function repCheckeds(tables) {
    var dbs = []
    if (tables) {
        dbs.push(tables)
    } else {
        var db_tools = $("input[value^='dbtools_']");
        for (var i = 0; i < db_tools.length; i++) {
            if (db_tools[i].checked) dbs.push(db_tools[i].value.replace('dbtools_', ''));
        }
    }

    if (dbs.length < 1) {
        layer.msg('请至少选择一张表!', { icon: 2 });
        return false;
    }
    return dbs;
}

function repDatabase(db_name, tables) {
    dbs = repCheckeds(tables);
    
    myPost('repair_table', { db_name: db_name, tables: JSON.stringify(dbs) }, function(data){
        var rdata = $.parseJSON(data.data);
        layer.msg(rdata.msg, { icon: rdata.status ? 1 : 2 });
        repTools(db_name, true);
    },'已送修复指令,请稍候...');
}


function optDatabase(db_name, tables) {
    dbs = repCheckeds(tables);
    
    myPost('opt_table', { db_name: db_name, tables: JSON.stringify(dbs) }, function(data){
        var rdata = $.parseJSON(data.data);
        layer.msg(rdata.msg, { icon: rdata.status ? 1 : 2 });
        repTools(db_name, true);
    },'已送优化指令,请稍候...');
}

function toDatabaseType(db_name, tables, type){
    dbs = repCheckeds(tables);
    myPost('alter_table', { db_name: db_name, tables: JSON.stringify(dbs),table_type: type }, function(data){
        var rdata = $.parseJSON(data.data);
        layer.msg(rdata.msg, { icon: rdata.status ? 1 : 2 });
        repTools(db_name, true);
    }, '已送引擎转换指令,请稍候...');
}


function selectedTools(my_obj, db_name) {
    var is_checked = false

    if (my_obj) is_checked = my_obj.checked;
    var db_tools = $("input[value^='dbtools_']");
    var n = 0;
    for (var i = 0; i < db_tools.length; i++) {
        if (my_obj) db_tools[i].checked = is_checked;
        if (db_tools[i].checked) n++;
    }
    if (n > 0) {
        var my_btns = '<button class="btn btn-default btn-sm" onclick="repDatabase(\'' + db_name + '\',null)">修复</button>\
            <button class="btn btn-default btn-sm" onclick="optDatabase(\'' + db_name + '\',null)">优化</button>\
            <button class="btn btn-default btn-sm" onclick="toDatabaseType(\'' + db_name + '\',null,\'InnoDB\')">转为InnoDB</button></button>\
            <button class="btn btn-default btn-sm" onclick="toDatabaseType(\'' + db_name + '\',null,\'MyISAM\')">转为MyISAM</button>'
        $("#db_tools").html(my_btns);
    } else {
        $("#db_tools").html('');
    }
}

function repTools(db_name, res){
    myPost('get_db_info', {name:db_name}, function(data){
        var rdata = $.parseJSON(data.data);
        var types = { InnoDB: "MyISAM", MyISAM: "InnoDB" };
        var tbody = '';
        for (var i = 0; i < rdata.tables.length; i++) {
            if (!types[rdata.tables[i].type]) continue;
            tbody += '<tr>\
                    <td><input value="dbtools_' + rdata.tables[i].table_name + '" class="check" onclick="selectedTools(null,\'' + db_name + '\');" type="checkbox"></td>\
                    <td><span style="width:220px;"> ' + rdata.tables[i].table_name + '</span></td>\
                    <td>' + rdata.tables[i].type + '</td>\
                    <td><span style="width:90px;"> ' + rdata.tables[i].collation + '</span></td>\
                    <td>' + rdata.tables[i].rows_count + '</td>\
                    <td>' + rdata.tables[i].data_size + '</td>\
                    <td style="text-align: right;">\
                        <a class="btlink" onclick="repDatabase(\''+ db_name + '\',\'' + rdata.tables[i].table_name + '\')">修复</a> |\
                        <a class="btlink" onclick="optDatabase(\''+ db_name + '\',\'' + rdata.tables[i].table_name + '\')">优化</a> |\
                        <a class="btlink" onclick="toDatabaseType(\''+ db_name + '\',\'' + rdata.tables[i].table_name + '\',\'' + types[rdata.tables[i].type] + '\')">转为' + types[rdata.tables[i].type] + '</a>\
                    </td>\
                </tr> '
        }

        if (res) {
            $(".gztr").html(tbody);
            $("#db_tools").html('');
            $("input[type='checkbox']").attr("checked", false);
            $(".tools_size").html('大小：' + rdata.data_size);
            return;
        }

        layer.open({
            type: 1,
            title: "MySQL工具箱【" + db_name + "】",
            area: ['780px', '580px'],
            closeBtn: 1,
            shadeClose: false,
            content: '<div class="pd15">\
                            <div class="db_list">\
                                <span><a>数据库名称：'+ db_name + '</a>\
                                <a class="tools_size">大小：'+ rdata.data_size + '</a></span>\
                                <span id="db_tools" style="float: right;"></span>\
                            </div >\
                            <div class="divtable">\
                            <div  id="database_fix"  style="height:360px;overflow:auto;border:#ddd 1px solid">\
                            <table class="table table-hover "style="border:none">\
                                <thead>\
                                    <tr>\
                                        <th><input class="check" onclick="selectedTools(this,\''+ db_name + '\');" type="checkbox"></th>\
                                        <th>表名</th>\
                                        <th>引擎</th>\
                                        <th>字符集</th>\
                                        <th>行数</th>\
                                        <th>大小</th>\
                                        <th style="text-align: right;">操作</th>\
                                    </tr>\
                                </thead>\
                                <tbody class="gztr">' + tbody + '</tbody>\
                            </table>\
                            </div>\
                        </div>\
                        <ul class="help-info-text c7">\
                            <li>【修复】尝试使用REPAIR命令修复损坏的表，仅能做简单修复，若修复不成功请考虑使用myisamchk工具</li>\
                            <li>【优化】执行OPTIMIZE命令，可回收未释放的磁盘空间，建议每月执行一次</li>\
                            <li>【转为InnoDB/MyISAM】转换数据表引擎，建议将所有表转为InnoDB</li>\
                        </ul></div>'
        });
        tableFixed('database_fix');
    });
}


function setDbMaster(name){
    myPost('set_db_master', {name:name}, function(data){
        var rdata = $.parseJSON(data.data);
        layer.msg(rdata.msg, { icon: rdata.status ? 1 : 5 });
        setTimeout(function(){
            masterOrSlaveConf();
        }, 2000);
    });
}


function setDbSlave(name){
    myPost('set_db_slave', {name:name}, function(data){
        var rdata = $.parseJSON(data.data);
        layer.msg(rdata.msg, { icon: rdata.status ? 1 : 5 });
        setTimeout(function(){
            masterOrSlaveConf();
        }, 2000);
    });
}


function addMasterRepSlaveUser(){
    layer.open({
        type: 1,
        area: '500px',
        title: '添加同步账户',
        closeBtn: 1,
        shift: 5,
        shadeClose: true,
        btn:["提交","取消"],
        content: "<form class='bt-form pd20' id='add_master'>\
            <div class='line'><span class='tname'>用户名</span><div class='info-r'><input name='username' class='bt-input-text mr5' placeholder='用户名' type='text' style='width:330px;' value='"+(randomStrPwd(6))+"'></div></div>\
            <div class='line'>\
            <span class='tname'>密码</span>\
            <div class='info-r'><input class='bt-input-text mr5' type='text' name='password' id='MyPassword' style='width:330px' value='"+(randomStrPwd(16))+"' /><span title='随机密码' class='glyphicon glyphicon-repeat cursor' onclick='repeatPwd(16)'></span></div>\
            </div>\
            <input type='hidden' name='ps' value='' />\
          </form>",
        success:function(){
            $("input[name='name']").keyup(function(){
                var v = $(this).val();
                $("input[name='db_user']").val(v);
                $("input[name='ps']").val(v);
            });

            $('select[name="dataAccess"]').change(function(){
                var v = $(this).val();
                if (v == 'ip'){
                    $(this).after("<input id='dataAccess_subid' class='bt-input-text mr5' type='text' name='address' placeholder='多个IP使用逗号(,)分隔' style='width: 230px; display: inline-block;'>");
                } else {
                    $('#dataAccess_subid').remove();
                }
            });
        },
        yes:function(index){
            var data = $("#add_master").serialize();
            data = decodeURIComponent(data);
            var dataObj = toArrayObject(data);
            if(!dataObj['address']){
                dataObj['address'] = dataObj['dataAccess'];
            }

            myPost('add_master_rep_slave_user', dataObj, function(data){
                var rdata = $.parseJSON(data.data);
                showMsg(rdata.msg,function(){
                    layer.close(index);
                    if (rdata.status){
                        getMasterRepSlaveList();
                    }
                },{icon: rdata.status ? 1 : 2},600);
            });
        }
    });
}



function updateMasterRepSlaveUser(username){
  
    var index = layer.open({
        type: 1,
        area: '500px',
        title: '更新账户',
        closeBtn: 1,
        shift: 5,
        shadeClose: true,
        content: "<form class='bt-form pd20 pb70' id='update_master'>\
            <div class='line'><span class='tname'>用户名</span><div class='info-r'><input name='username' readonly='readonly' class='bt-input-text mr5' placeholder='用户名' type='text' style='width:330px;' value='"+username+"'></div></div>\
            <div class='line'>\
            <span class='tname'>密码</span>\
            <div class='info-r'><input class='bt-input-text mr5' type='text' name='password' id='MyPassword' style='width:330px' value='"+(randomStrPwd(16))+"' /><span title='随机密码' class='glyphicon glyphicon-repeat cursor' onclick='repeatPwd(16)'></span></div>\
            </div>\
            <input type='hidden' name='ps' value='' />\
            <div class='bt-form-submit-btn'>\
                <button type='button' class='btn btn-success btn-sm btn-title' id='submit_update_master' >提交</button>\
            </div>\
          </form>",
    });

    $('#submit_update_master').click(function(){
        var data = $("#update_master").serialize();
        data = decodeURIComponent(data);
        var dataObj = toArrayObject(data);
        myPost('update_master_rep_slave_user', data, function(data){
            var rdata = $.parseJSON(data.data);
            showMsg(rdata.msg,function(){
                if (rdata.status){
                    getMasterRepSlaveList();
                }
                $('.layui-layer-close1').click();
            },{icon: rdata.status ? 1 : 2},600);
        });
    });
}

function getMasterRepSlaveUserCmd(username, db=''){
    myPost('get_master_rep_slave_user_cmd', {username:username,db:db}, function(data){
        var rdata = $.parseJSON(data.data);

        if (!rdata['status']){
            layer.msg(rdata['msg']);
            return;
        }

        var cmd = rdata.data['cmd'];
        
        var loadOpen = layer.open({
            type: 1,
            title: '同步命令',
            area: '500px',
            content:"<form class='bt-form pd20 pb70' id='add_master'>\
            <div class='line'>"+cmd+"</div>\
            <div class='bt-form-submit-btn'>\
                <button type='button' class='btn btn-success btn-sm btn-title class-copy-cmd'>复制</button>\
            </div>\
          </form>",
        });

       
        copyPass(cmd);
        $('.class-copy-cmd').click(function(){
            copyPass(cmd);
        });
    });
}

function delMasterRepSlaveUser(username){
    myPost('del_master_rep_slave_user', {username:username}, function(data){
        var rdata = $.parseJSON(data.data);
        layer.msg(rdata.msg);

        $('.layui-layer-close1').click();

        setTimeout(function(){
            getMasterRepSlaveList();
        },1000);
    });
}


function setDbMasterAccess(username){
    myPost('get_db_access','username='+username, function(data){
        var rdata = $.parseJSON(data.data);
        if (!rdata.status){
            layer.msg(rdata.msg,{icon:2,shade: [0.3, '#000']});
            return;
        }
        
        var index = layer.open({
            type: 1,
            area: '500px',
            title: '设置数据库权限',
            closeBtn: 1,
            shift: 5,
            btn:["提交","取消"],
            shadeClose: true,
            content: "<form class='bt-form pd20' id='set_db_access'>\
                        <div class='line'>\
                            <span class='tname'>访问权限</span>\
                            <div class='info-r '>\
                                <select class='bt-input-text mr5' name='dataAccess' style='width:100px'>\
                                <option value='127.0.0.1'>本地服务器</option>\
                                <option value=\"%\">所有人</option>\
                                <option value='ip'>指定IP</option>\
                                </select>\
                            </div>\
                        </div>\
                      </form>",
            success:function(){
                if (rdata.msg == '127.0.0.1'){
                    $('select[name="dataAccess"]').find("option[value='127.0.0.1']").attr("selected",true);
                } else if (rdata.msg == '%'){
                    $('select[name="dataAccess"]').find('option[value="%"]').attr("selected",true);
                } else if ( rdata.msg == 'ip' ){
                    $('select[name="dataAccess"]').find('option[value="ip"]').attr("selected",true);
                    $('select[name="dataAccess"]').after("<input id='dataAccess_subid' class='bt-input-text mr5' type='text' name='address' placeholder='多个IP使用逗号(,)分隔' style='width: 230px; display: inline-block;'>");
                } else {
                    $('select[name="dataAccess"]').find('option[value="ip"]').attr("selected",true);
                    $('select[name="dataAccess"]').after("<input value='"+rdata.msg+"' id='dataAccess_subid' class='bt-input-text mr5' type='text' name='address' placeholder='多个IP使用逗号(,)分隔' style='width: 230px; display: inline-block;'>");
                }

                 $('select[name="dataAccess"]').change(function(){
                    var v = $(this).val();
                    if (v == 'ip'){
                        $(this).after("<input id='dataAccess_subid' class='bt-input-text mr5' type='text' name='address' placeholder='多个IP使用逗号(,)分隔' style='width: 230px; display: inline-block;'>");
                    } else {
                        $('#dataAccess_subid').remove();
                    }
                });
            },
            yes:function(index){
                var data = $("#set_db_access").serialize();
                data = decodeURIComponent(data);
                var dataObj = toArrayObject(data);
                if(!dataObj['access']){
                    dataObj['access'] = dataObj['dataAccess'];
                    if ( dataObj['dataAccess'] == 'ip'){
                        if (dataObj['address']==''){
                            layer.msg('IP地址不能空!',{icon:2,shade: [0.3, '#000']});
                            return;
                        }
                        dataObj['access'] = dataObj['address'];
                    }
                }
                dataObj['username'] = username;
                myPost('set_dbmaster_access', dataObj, function(data){
                    var rdata = $.parseJSON(data.data);
                    showMsg(rdata.msg,function(){
                        layer.close(index);
                    },{icon: rdata.status ? 1 : 2});   
                });
            }
        });

    });
}

function getMasterRepSlaveList(){
    var _data = {};
    if (typeof(page) =='undefined'){
        var page = 1;
    }
    
    _data['page'] = page;
    _data['page_size'] = 10;
    myPost('get_master_rep_slave_list', _data, function(data){
        // console.log(data);
        var rdata = [];
        try {
            rdata = $.parseJSON(data.data);
        } catch(e){
            console.log(e);
        }
        var list = '';
        // console.log(rdata['data']);
        var user_list = rdata['data'];
        for (i in user_list) {
            // console.log(i);
            var name = user_list[i]['username'];
            list += '<tr><td>'+name+'</td>\
                <td>'+user_list[i]['password']+'</td>\
                <td>\
                    <a class="btlink" onclick="updateMasterRepSlaveUser(\''+name+'\');">修改</a> | \
                    <a class="btlink" onclick="delMasterRepSlaveUser(\''+name+'\');">删除</a> | \
                    <a class="btlink" onclick="setDbMasterAccess(\''+name+'\');">权限</a> | \
                    <a class="btlink" onclick="getMasterRepSlaveUserCmd(\''+name+'\');">从库同步命令</a>\
                </td>\
            </tr>';
        }

        $('#get_master_rep_slave_list_page tbody').html(list);
        $('.dataTables_paginate_4').html(rdata['page']);
    });
}

function getMasterRepSlaveListPage(){
    var page = '<div class="dataTables_paginate_4 dataTables_paginate paging_bootstrap page" style="margin-top:0px;"></div>';
        page += '<div class="table_toolbar" style="left:0px;"><span class="sync btn btn-default btn-sm" onclick="addMasterRepSlaveUser()" title="">添加同步账户</span></div>';

    var loadOpen = layer.open({
        type: 1,
        title: '同步账户列表',
        area: '500px',
        content:"<div class='bt-form pd20 c6'>\
                 <div class='divtable mtb10' id='get_master_rep_slave_list_page'>\
                    <div><table class='table table-hover'>\
                        <thead><tr><th>用户名</th><th>密码</th><th>操作</th></tr></thead>\
                        <tbody></tbody>\
                    </table></div>\
                    "+page +"\
                </div>\
            </div>",
        success:function(){
            getMasterRepSlaveList();
        }
    });
}


function deleteSlave(){
    myPost('delete_slave', {}, function(data){
        var rdata = $.parseJSON(data.data);
        showMsg(rdata['msg'], function(){
            masterOrSlaveConf();
        },{},3000);
    });
}


function getFullSyncStatus(db){
    var timeId = null;

    var btn = '<div class="table_toolbar" style="left:0px;"><span data-status="init" class="sync btn btn-default btn-sm" id="begin_full_sync" title="">开始</span></div>';
    var loadOpen = layer.open({
        type: 1,
        title: '全量同步['+db+']',
        area: '500px',
        content:"<div class='bt-form pd20 c6'>\
                 <div class='divtable mtb10'>\
                    <span id='full_msg'></span>\
                    <div class='progress'>\
                        <div class='progress-bar' role='progressbar' aria-valuenow='0' aria-valuemin='0' aria-valuemax='100' style='min-width: 2em;'>0%</div>\
                    </div>\
                </div>\
                "+btn+"\
            </div>",
        cancel: function(){ 
            clearInterval(timeId);
        }
    });

    function fullSync(db,begin){
       
        myPostN('full_sync', {db:db,begin:begin}, function(data){
            var rdata = $.parseJSON(data.data);
            $('#full_msg').text(rdata['msg']);
            $('.progress-bar').css('width',rdata['progress']+'%');
            $('.progress-bar').text(rdata['progress']+'%');

            if (rdata['code']==6 ||rdata['code']<0){
                layer.msg(rdata['msg']);
                clearInterval(timeId);
                $("#begin_full_sync").attr('data-status','init');
            }
        });
    }

    $('#begin_full_sync').click(function(){
        var val = $(this).attr('data-status');
        if (val == 'init'){
            fullSync(db,1);
            timeId = setInterval(function(){
                fullSync(db,0);
            }, 1000);
            $(this).attr('data-status','starting');
        } else {
            layer.msg("正在同步中..");
        }
    });
}

function addSlaveSSH(ip=''){

    myPost('get_slave_ssh_by_ip', {ip:ip}, function(rdata){
        
        var rdata = $.parseJSON(rdata.data);

        var ip = '127.0.0.1';
        var port = "10022";
        var id_rsa = '';
        var db_user ='';
        var id_rsa = '/root/.ssh/id_rsa'

        if (rdata.data.length>0){
            ip = rdata.data[0]['ip'];
            port = rdata.data[0]['port'];
            id_rsa = rdata.data[0]['id_rsa'];
            db_user = rdata.data[0]['db_user'];
        }

        var index = layer.open({
            type: 1,
            area: ['500px','480px'],
            title: '添加SSH',
            closeBtn: 1,
            shift: 5,
            shadeClose: true,
            btn:["确认","取消"],
            content: "<form class='add_slave_ssh_form bt-form pd20'>\
                <div class='line'><span class='tname'>IP</span><div class='info-r'><input name='ip' class='bt-input-text mr5' type='text' style='width:330px;' value='"+ip+"'></div></div>\
                <div class='line'><span class='tname'>端口</span><div class='info-r'><input name='port' class='bt-input-text mr5' type='number' style='width:330px;' value='"+port+"'></div></div>\
                <div class='line'><span class='tname'>同步账户[DB]</span><div class='info-r'><input name='db_user'  placeholder='为空则取第一个!' class='bt-input-text mr5' type='text' style='width:330px;' value='"+db_user+"'></div></div>\
                <div class='line'>\
                <span class='tname'>密钥文件</span>\
                <div class='info-r'><textarea class='bt-input-text mr5' row='20' cols='50' name='id_rsa'  style='width:330px;height:200px;'  value='"+id_rsa+"' placeholder='公钥文件位置或私钥内容（如：/root/.ssh/id_rsa.pub）' ></textarea></div>\
                </div>\
                <input type='hidden' name='ps' value='' />\
              </form>",
            success:function(){
                $('textarea[name="id_rsa"]').html(id_rsa);
            },
            yes:async function(index){
                var ip = $('.add_slave_ssh_form input[name="ip"]').val();
                var port = $('.add_slave_ssh_form input[name="port"]').val();
                var db_user = $('.add_slave_ssh_form input[name="db_user"]').val();
                var id_rsa = $('.add_slave_ssh_form textarea[name="id_rsa"]').val();

                var data = {ip:ip,port:port,id_rsa:id_rsa,db_user:db_user};
                let testResult = JSON.parse((await myPost('test_ssh', data)).data)
                if (!testResult.status) {
                    layer.msg("使用密钥文件连接服务器失败!<br/>请检查对应的公钥内容是否添加到目标服务器的/root/.ssh/authorized_keys中",{icon:2,time:8000,shade: [0.3, '#000']});
                    return 
                }

                myPost('add_slave_ssh', data, function(data){
                    layer.close(index);
                    var rdata = $.parseJSON(data.data);
                    showMsg(rdata.msg,function(){
                        if (rdata.status){
                            getSlaveSSHPage();
                        }
                    },{icon: rdata.status ? 1 : 2},600);
                });
            }
        });
    });
}


function delSlaveSSH(ip){
    myPost('del_slave_ssh', {ip:ip}, function(rdata){
        var rdata = $.parseJSON(rdata.data);
        layer.msg(rdata.msg, {icon: rdata.status ? 1 : 2});
        getSlaveSSHPage();
    });
}

function getSlaveSSHPage(page=1){
    var _data = {};    
    _data['page'] = page;
    _data['page_size'] = 5;
    _data['tojs'] ='getSlaveSSHPage';
    myPost('get_slave_ssh_list', _data, function(data){
        var layerId = null;
        var rdata = [];
        try {
            rdata = $.parseJSON(data.data);
        } catch(e) {
            console.log(e);
        }
        var list = '';
        var ssh_list = rdata['data'];
        for (i in ssh_list) {
            var ip = ssh_list[i]['ip'];
            var port = ssh_list[i]['port'];

            var id_rsa = '未设置';
            if ( ssh_list[i]['port'] != ''){
                id_rsa = '已设置';
            }

            var db_user = '未设置';
            if ( ssh_list[i]['db_user'] != ''){
                db_user = ssh_list[i]['db_user'];
            }

            list += '<tr><td>'+ip+'</td>\
                <td>'+port+'</td>\
                <td>'+db_user+'</td>\
                <td>'+id_rsa+'</td>\
                <td>\
                    <a class="btlink" onclick="addSlaveSSH(\''+ip+'\');">修改</a> | \
                    <a class="btlink" onclick="delSlaveSSH(\''+ip+'\');">删除</a>\
                </td>\
            </tr>';
        }

        $('.get-slave-ssh-list tbody').html(list);
        $('.dataTables_paginate_4').html(rdata['page']);
    });
}


function getSlaveSSHList(page=1){

    var page = '<div class="dataTables_paginate_4 dataTables_paginate paging_bootstrap page" style="margin-top:0px;"></div>';
    page += '<div class="table_toolbar" style="left:0px;"><span class="sync btn btn-default btn-sm" onclick="addSlaveSSH()" title="">添加SSH</span></div>';

    layerId = layer.open({
        type: 1,
        title: 'SSH列表',
        area: '500px',
        content:"<div class='bt-form pd20 c6'>\
                 <div class='divtable mtb10'>\
                    <div><table class='table table-hover get-slave-ssh-list'>\
                        <thead><tr><th>IP</th><th>PORT</th><th>同步账户</th><th>SSH</th><th>操作</th></tr></thead>\
                        <tbody></tbody>\
                    </table></div>\
                    "+page +"\
                </div>\
            </div>",
        success:function(){
            getSlaveSSHPage(1);
        }
    });
}

function handlerRun(){
    myPostN('get_slave_sync_cmd', {}, function(data){
        var rdata = $.parseJSON(data.data);
        var cmd = rdata['data'];
        var loadOpen = layer.open({
            type: 1,
            title: '手动执行',
            area: '500px',
            content:"<form class='bt-form pd20 pb70' id='add_master'>\
            <div class='line'>"+cmd+"</div>\
            <div class='bt-form-submit-btn'>\
                <button type='button' class='btn btn-success btn-sm btn-title class-copy-cmd'>复制</button>\
            </div>\
          </form>",
        });
        copyPass(cmd);
        $('.class-copy-cmd').click(function(){
            copyPass(cmd);
        });
    });
}

function initSlaveStatus(){
    myPost('init_slave_status', '', function(data){
        var rdata = $.parseJSON(data.data);
        showMsg(rdata.msg,function(){
            if (rdata.status){
                masterOrSlaveConf();
            }
        },{icon:rdata.status?1:2},2000);
    });
}

var defaultAutoSaveSlaveStatusToMasterCron = {      
  name: '[勿删]主从状态推送到[主]服务器',
  type: 'hour-n',
  where1: 2,
  hour: 0,
  minute: 0,
  week: '',
  sType: 'toShell',
  stype: 'toShell',
  sName: '',
  sBody: `
#!/bin/bash
pushd /www/server/jh-panel > /dev/null  
python3 /www/server/jh-panel/plugins/mysql-apt/index.py save_slave_status_to_master
popd > /dev/null
  `,
  backupCompress: false,
  backupZip: false,
  backupTo: 'localhost' };
var autoSaveSlaveStatusToMasterCron = {...defaultAutoSaveSlaveStatusToMasterCron};

function masterOrSlaveConf(version=''){

    function getAsyncMasterDbList(){
        var _data = {};
        if (typeof(page) =='undefined'){
            var page = 1;
        }
        
        _data['page'] = page;
        _data['page_size'] = 10;

        myPost('get_slave_list', _data, function(data){
            var rdata = $.parseJSON(data.data);
            var list = '';
            for(i in rdata.data){

                var v = rdata.data[i];
                var status = "异常";
                if (v['Slave_SQL_Running'] == 'Yes' && v['Slave_IO_Running'] == 'Yes'){
                    status = "正常";
                }

                let errorMsg = v['Last_Error'] || v['Last_IO_Error']

                list += '<tr>';
                list += '<td>' + rdata.data[i]['Master_Host'] +'</td>';
                list += '<td>' + rdata.data[i]['Master_Port'] +'</td>';
                list += '<td>' + rdata.data[i]['Master_User'] +'</td>';
                list += '<td>' + rdata.data[i]['Master_Log_File'] +'</td>';
                list += '<td style="color: ' + (rdata.data[i]['Slave_IO_Running'] == 'Yes'? 'green': 'red') + '">' + rdata.data[i]['Slave_IO_Running'] +'</td>';
                list += '<td style="color: ' + (rdata.data[i]['Slave_SQL_Running'] == 'Yes'? 'green': 'red') + '">' + rdata.data[i]['Slave_SQL_Running'] +'</td>';
                list += '<td style="color: ' + (rdata.data[i]['Seconds_Behind_Master'] == 0? 'green': 'red') + '">' + rdata.data[i]['Seconds_Behind_Master'] +'</td>';
                list += '<td style="color: ' + (status == '正常'? 'green': 'red') + `"><span title="${errorMsg}">` + status + '</span>' + (status == '正常'? '': ` <span data-toggle="tooltip" title="${errorMsg}" class='bt-ico-ask' style='cursor: pointer; margin-left: 0;'>?</span>`) + '</td>';
                list += '<td style="text-align:right">' + 
                    '<a href="javascript:;" class="btlink" onclick="deleteSlave()" title="删除">删除</a>' +
                '</td>';
                list += '</tr>';
            }

            var con = '<div class="divtable mtb10">\
                    <div class="tablescroll">\
                        <table id="DataBody" class="table table-hover" width="100%" cellspacing="0" cellpadding="0" border="0" style="border: 0 none;">\
                        <thead><tr>\
                        <th>主[服务]</th>\
                        <th>端口</th>\
                        <th>用户</th>\
                        <th>日志</th>\
                        <th>IO</th>\
                        <th>SQL</th>\
                        <th>延迟</th>\
                        <th>状态</th>\
                        <th style="text-align:right;">操作</th></tr></thead>\
                        <tbody>\
                        '+ list +'\
                        </tbody></table>\
                    </div>\
                </div>';

            // <div id="databasePage_slave" class="dataTables_paginate paging_bootstrap page"></div>\
            // <div class="table_toolbar">\
            //     <span class="sync btn btn-default btn-sm" onclick="getMasterRepSlaveList()" title="">添加</span>\
            // </div>
            $(".table_slave_status_list").html(con);
            $('[data-toggle="tooltip"]').tooltip();
        });
    }

    function getAsyncDataList(){
        var _data = {};
        if (typeof(page) =='undefined'){
            var page = 1;
        }
        
        _data['page'] = page;
        _data['page_size'] = 10;
        myPost('get_masterdb_list', _data, function(data){
            var rdata = $.parseJSON(data.data);
            var list = '';
            for(i in rdata.data){
                list += '<tr>';
                list += '<td>' + rdata.data[i]['name'] +'</td>';
                list += '<td style="text-align:right">' + 
                    '<a href="javascript:;" class="btlink" onclick="setDbSlave(\''+rdata.data[i]['name']+'\')"  title="加入|退出">'+(rdata.data[i]['slave']?'退出':'加入')+'</a> | ' +
                    '<a href="javascript:;" class="btlink" onclick="getFullSyncStatus(\''+rdata.data[i]['name']+'\')" title="同步">同步</a>' +
                '</td>';
                list += '</tr>';
            }

            var con = '<div class="divtable mtb10">\
                    <div class="tablescroll">\
                        <table id="DataBody" class="table table-hover" width="100%" cellspacing="0" cellpadding="0" border="0" style="border: 0 none;">\
                        <thead><tr>\
                        <th>本地库名</th>\
                        <th style="text-align:right;">操作</th></tr></thead>\
                        <tbody>\
                        '+ list +'\
                        </tbody></table>\
                    </div>\
                    <div id="databasePage" class="dataTables_paginate paging_bootstrap page"></div>\
                    <div class="table_toolbar" style="left:0px;">\
                        <span class="sync btn btn-default btn-sm" onclick="handlerRun()" title="免登录设置后,需要手动执行一下!">手动命令</span>\
                        <span class="sync btn btn-default btn-sm" onclick="getFullSyncStatus(\'ALL\')" title="全量同步">全量同步</span>\
                    </div>\
                </div>';

            $(".table_slave_list").html(con);
            $('#databasePage').html(rdata.page);
        });
    }

   

    function getMasterStatus(){
        myPost('get_master_status', '', function(rdata){
            var rdata = $.parseJSON(rdata.data);
            // console.log('mode:',rdata.data);
            if ( typeof(rdata.status) != 'undefined' && !rdata.status && rdata.data == 'pwd'){
                layer.msg(rdata.msg, {icon:2});
                return;
            }

            var rdata = rdata.data;
            var limitCon = '\
                <p class="conf_p">\
                    <span class="f14 c6 mr20">主从同步模式</span><span class="f14 c6 mr20"></span>\
                    <button class="btn '+(!(rdata.mode == "gtid") ? 'btn-danger' : 'btn-success')+' btn-xs db-mode btn-gtid">GTID</button>\
                </p>\
                <hr/>\
                <p class="conf_p master_box">\
                    <span class="f14 c6 mr20">Master[主]配置</span><span class="f14 c6 mr20"></span>\
                    <!-- <button class="btn '+(!rdata.status ? 'btn-danger' : 'btn-success')+' btn-xs btn-master">'+(!rdata.status ? '未开启' : '已开启') +'</button> -->\
                </p>\
                <hr/>\
                <div class="conf_p semi-sync-box flex" style="align-items: center;">\
                    <span class="f14 c6 mr20">半同步复制</span><span class="f14 c6 mr20"></span>\
                    <div id="semiSyncSwitch"></div>\
                    <div>\
                        <span class="f12 c9 semi-sync-runtime" style="cursor:pointer;margin-left: 15px;margin-right: 2px;width:250px;" title=""></span>\
                        <span class="semi-sync-runtime-tip bt-ico-ask" data-toggle="tooltip" title="" style="cursor:pointer; margin-left:0;width: 16px;height: 16px;text-align: center;">?</span>\
                    </div>\
                </div>\
                <hr/>\
                <!-- class="conf_p" -->\
                <p class="conf_p">\
                    <span class="f14 c6 mr20">Slave[从]配置</span><span class="f14 c6 mr20"></span>\
                    <button class="btn '+(!rdata.slave_status ? 'btn-danger' : 'btn-success')+' btn-xs btn-slave">'+(!rdata.slave_status ? '未启动' : '已启动') +'</button>\
                    <button class="btn btn-success btn-xs" onclick="getSlaveSSHList()" >[主]SSH配置</button>\
                    <button class="btn btn-success btn-xs" onclick="initSlaveStatus()" >初始化</button>\
                </p>\
                <div class="auto-save-slave-to-master-cron mt20 conf_p flex" style="align-items: center;">\
                    <span class="f14 c6 mr20">定时推送状态到[主]</span><span class="f14 c6 mr20"></span>\
                    <div  class="ssh-item" id="openAutoSaveSlaveStatusToMasterCronSwitch"></div>\
                    <div id="autoSaveSlaveStatusToMasterCronDetail">\
                        <div></div>\
                        <button class="open-cron-selecter-layer btn btn-default btn-sm mlr15" type="button">配置频率</button>\
                    </div>\
                </div>\
                <hr/>\
                <!-- slave status list -->\
                <div class="safe bgw table_slave_status_list"></div>\
                <!-- slave list -->\
                <div class="safe bgw table_slave_list"></div>\
                ';
            $(".soft-man-con").html(limitCon);

            var semiSyncInfo = rdata.semi_sync || {enabled:false, master_runtime:false, slave_runtime:false};
            var runtimeText = '运行状态：主' + (semiSyncInfo.master_runtime ? '开启' : '关闭') + ' / 从' + (semiSyncInfo.slave_runtime ? '开启' : '关闭');
            if (!semiSyncInfo.enabled){
                runtimeText += '（配置未启用）';
            }
            $('.semi-sync-runtime').text(runtimeText);
            var statusVars = semiSyncInfo.status_vars || {};
            var metricsText = [];
            Object.keys(statusVars).forEach(function(key){
                if (statusVars[key] !== ''){
                    metricsText.push(key + '=' + statusVars[key]);
                }
            });
            $('.semi-sync-runtime').attr('title', metricsText.join('\n'));
            $('.semi-sync-runtime-tip').attr('title', metricsText.join('\n'));
            $('[data-toggle="tooltip"]').tooltip();
            $("#semiSyncSwitch").createRadioSwitch(semiSyncInfo.enabled, function(checked){
                if (semiSyncInfo.enabled === checked) return;
                var tip = checked ? '确认启用半同步复制？该操作会写入配置并重启MySQL。' : '确认关闭半同步复制？该操作会写入配置并重启MySQL。';
                layer.confirm(tip, {title:'确认操作', icon:3}, function(index){
                    layer.close(index);
                    setSemiSyncStatus(checked);
                }, function(){
                    masterOrSlaveConf();
                });
            });
            getAutoSaveSlaveStatusToMasterCron();
            
            $("#autoSaveSlaveStatusToMasterCronDetail .open-cron-selecter-layer").click(() => {
              openCronSelectorLayer(autoSaveSlaveStatusToMasterCron, {yes: addOrUpdateAutoSaveSlaveStatusToMasterCron});
            });

            visibleDom('.auto-save-slave-to-master-cron', rdata.slave_status);


            //设置主服务器配置
            $(".btn-master").click(function () {
                myPost('set_master_status', 'close=change', function(data){
                    var rdata = $.parseJSON(data.data);
                    layer.msg(rdata.msg, { icon: rdata.status ? 1 : 5 });
                    setTimeout(function(){
                        getMasterStatus();
                    }, 3000);
                });
            });

            $(".btn-slave").click(function () {
                myPost('set_slave_status', 'close=change', function(data){
                    var rdata = $.parseJSON(data.data);
                    layer.msg(rdata.msg, { icon: rdata.status ? 1 : 5 });
                    setTimeout(function(){
                        getMasterStatus();
                    }, 3000);
                });
            });

            $('.db-mode').click(function(){
                if ($(this).hasClass('btn-success')){
                    //no action
                    return;
                }

                var mode = 'classic';
                if ($(this).hasClass('btn-gtid')){
                    mode = 'gtid';
                }

                layer.open({
                    type:1,
                    title:"MySQL主从模式切换",
                    shadeClose:false,
                    btnAlign: 'c',
                    btn: ['切换并重启', '切换不重启'],
                    yes: function(index, layero){
                        this.change(index,mode,"yes");

                    },
                    btn2: function(index, layero){
                        this.change(index,mode,"no");
                        return false;
                    },
                    change:function(index,mode,reload){
                        console.log(index,mode,reload);
                        myPost('set_dbrun_mode',{'mode':mode,'reload':reload},function(data){
                            layer.close(index);
                            var rdata = $.parseJSON(data.data);
                            showMsg(rdata.msg ,function(){
                                getMasterStatus();
                            },{ icon: rdata.status ? 1 : 5 });
                        });
                    }
                });
            });

            // if (rdata.status){
                var con = '<span class="sync btn btn-default btn-sm" style="width: auto" onclick="getMasterRepSlaveListPage()" title="">配置同步账户</span>';
                $(".master_box").append(con);
            // }
            
            if (rdata.slave_status){
                getAsyncMasterDbList();
                // getAsyncDataList()
            }
        });
    }
    getMasterStatus();
}

function getAutoSaveSlaveStatusToMasterCron() {
  $.post('/crontab/get', { name: autoSaveSlaveStatusToMasterCron.name },function(rdata){
      const { status: openAutoSaveSlaveStatusToMasterCron } = rdata;
      if (openAutoSaveSlaveStatusToMasterCron) {
          autoSaveSlaveStatusToMasterCron = rdata.data;
      }else {
          autoSaveSlaveStatusToMasterCron = {...defaultAutoSaveSlaveStatusToMasterCron};
      }
      visibleDom('#autoSaveSlaveStatusToMasterCronDetail', openAutoSaveSlaveStatusToMasterCron);
      $("#openAutoSaveSlaveStatusToMasterCronSwitch").createRadioSwitch(openAutoSaveSlaveStatusToMasterCron, (checked) => {
          visibleDom('#autoSaveSlaveStatusToMasterCronDetail', checked);
          if(checked) {
              addOrUpdateAutoSaveSlaveStatusToMasterCron();
          } else {
              deleteCron(autoSaveSlaveStatusToMasterCron.id);
          }
      });
  },'json');
}

async function addOrUpdateAutoSaveSlaveStatusToMasterCron(cronSelectorData) {
  autoSaveSlaveStatusToMasterCron.sbody = autoSaveSlaveStatusToMasterCron.sBody;
  // if(!autoSaveSlaveStatusToMasterCron.id) {
  //     let scriptData = await myPost('inc_backup_cron_script','');
  //     let scriptRData = $.parseJSON(scriptData.data);
  //     xtrabackupIncCron.sBody = xtrabackupIncCron.sbody = scriptRData.data
  // }
  $.post(autoSaveSlaveStatusToMasterCron.id? '/crontab/modify_crond': '/crontab/add', {...autoSaveSlaveStatusToMasterCron, ...cronSelectorData},function(rdata){
      getAutoSaveSlaveStatusToMasterCron();
      layer.msg(rdata.msg,{icon:rdata.status?1:2}, 5000);
  },'json');
}


function deleteCron(id) {
  if (id) {
      $.post('/crontab/del', { id },function(rdata){
          getAutoSaveSlaveStatusToMasterCron();
          layer.msg(rdata.msg,{icon:rdata.status?1:2}, 5000);
      },'json');
  }
}

function setSemiSyncStatus(enable){
    var title = enable ? '正在启用半同步...' : '正在关闭半同步...';
    myPost('set_semi_sync_status', { enable: enable ? 1 : 0 }, function(data){
        var rdata = $.parseJSON(data.data);
        layer.msg(rdata.msg, {icon: rdata.status ? 1 : 2});
        setTimeout(function(){
            masterOrSlaveConf();
        }, 1000);
    }, title);
}
