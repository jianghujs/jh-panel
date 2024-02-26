function rsPost(method,args,callback, title){
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
        $.post('/plugins/run', {name:'rsyncd', func:method, args:_args}, function(data) {
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

///////////////// ----------------- 发送配置 ---------------- //////////////

function createSendTask(name = ''){
    var args = {};
    args["name"] = name;
    rsPost('lsyncd_get', args, function(rdata){
        var rdata = $.parseJSON(rdata.data);
        var data = rdata.data;
        console.log(data);

        var layerName = '创建';
        if (name!=''){
            layerName = '编辑';
        }

        var compress_true = "";
        var compress_false = "";
        if (data['rsync']['compress'] == 'true'){
            compress_true = "selected";
            compress_false = "";
        } else {
            compress_true = "";
            compress_false = "selected";
        }


        var delete_true = "";
        var delete_false = "";
        if (data['delete'] == 'false'){
            delete_true = "selected";
            delete_false = "";
        } else {
            delete_true = "";
            delete_false = "selected";
        }


        var realtime_true = "";
        var realtime_false = "";
        if (data['realtime'] == 'true'){
            realtime_true = "selected";
            realtime_false = "";
        } else {
            realtime_true = "";
            realtime_false = "selected";
        }


        var period_day = "";
        var period_minute_n = "";
        if (data['period'] == 'day'){
            period_day = "selected";
            period_minute_n = "";
        } else {
            period_day = "";
            period_minute_n = "selected";
        }

        // 连接方式选中
        var conn_type_key = "";
        var conn_type_user = "";
        var conn_type_ssh = "";
        if(data['conn_type'] == 'key') {
            conn_type_key = "selected";
            conn_type_user = "";
            conn_type_ssh = "";
        } else if(data['conn_type'] == 'user') {
            conn_type_key = "";
            conn_type_user = "selected";
            conn_type_ssh = "";
        } else {
            conn_type_key = "";
            conn_type_user = "";
            conn_type_ssh = "selected";
        }

        var layerID = layer.open({
            type: 1,
            area: ['600px','500px'],
            title: layerName+"发送任务",
            closeBtn: 1,
            shift: 0,
            shadeClose: false,
            btn: ['提交','取消'], 
            content:"<form class='bt-form pd20' id='fromServerPath' accept-charset='utf-8'>\
                <div class='line'>\
                    <span class='tname'>服务器IP</span>\
                    <div class='info-r c4'>\
                        <input class='bt-input-text' type='text' name='ip' placeholder='请输入接收服务器IP' value='"+data["ip"]+"' style='width:310px' />\
                    </div>\
                </div>\
                <div class='line'>\
                    <span class='tname'>同步目录</span>\
                    <div class='info-r c4'>\
                        <input id='inputPath' class='bt-input-text mr5' type='text' name='path' value='"+data["path"]+"' placeholder='请选择同步目录（一般以/结尾）' style='width:310px' /><span class='glyphicon glyphicon-folder-open cursor' onclick='changePath(\"inputPath\", {\"endSlash\": true})'></span>\
                        <span data-toggle='tooltip' data-placement='top' title='【同步目录】若不以/结尾，则表示将数据同步到二级目录，一般情况下目录路径请以/结尾' class='bt-ico-ask' style='cursor: pointer;'>?</span>\
                    </div>\
                </div>\
                <div class='line'>\
                    <span class='tname'>同步方式</span>\
                    <div class='info-r c4'>\
                        <select class='bt-input-text' name='delete' style='width:100px'>\
                            <option value='false' "+delete_true+">增量</option>\
                            <option value='true' "+delete_false+">完全</option>\
                        </select>\
                        <span data-toggle='tooltip' data-placement='top' title='【同步方式】增量： 数据更改/增加时同步，且只追加和替换文件\n【同步方式】完全： 保持两端的数据与目录结构的一致性，会同步删除、追加和替换文件和目录' class='bt-ico-ask' style='cursor: pointer;'>?</span>\
                        <span style='margin-left: 20px;margin-right: 10px;'>同步周期</span>\
                        <select class='bt-input-text synchronization' name='realtime' style='width:100px'>\
                            <option value='true' "+realtime_true+">实时同步</option>\
                            <option value='false' "+realtime_false+">定时同步</option>\
                        </select>\
                    </div>\
                </div>\
                <div class='line' id='period' style='height:45px;display:none;'>\
                    <span class='tname'>定时周期</span>\
                    <div class='info-r c4'>\
                        <select class='bt-input-text pull-left mr20' name='period' style='width:100px;'>\
                            <option value='day' "+period_day+">每天</option>\
                            <option value='minute-n' "+period_minute_n+">N分钟</option>\
                        </select>\
                        <div class='plan_hms pull-left mr20 bt-input-text hour'>\
                            <span><input class='bt-input-text' type='number' name='hour' value='"+data["hour"]+"' maxlength='2' max='23' min='0'></span>\
                            <span class='name'>小时</span>\
                        </div>\
                        <div class='plan_hms pull-left mr20 bt-input-text minute'>\
                            <span><input class='bt-input-text' type='number' name='minute' value='"+data["minute"]+"' maxlength='2' max='59' min='0'></span>\
                            <span class='name'>分钟</span>\
                        </div>\
                        <div class='plan_hms pull-left mr20 bt-input-text minute-n' style='display:none;'>\
                            <span><input class='bt-input-text' type='number' name='minute-n' value='"+data["minute-n"]+"' maxlength='2' max='59' min='0'></span>\
                            <span class='name'>分钟</span>\
                        </div>\
                    </div>\
                </div>\
                <div class='line'>\
                    <span class='tname'>限速</span>\
                    <div class='info-r c4'>\
                        <input class='bt-input-text' type='number' name='bwlimit' min='0'  value='"+(data.rsync ? data.rsync['bwlimit']: 1024)+"' style='width:100px' /> KB\
                        <span data-toggle='tooltip' data-placement='top' title='【限速】限制数据同步任务的速度，防止因同步数据导致带宽跑高' class='bt-ico-ask' style='cursor: pointer;'>?</span>\
                        <span style='margin-left: 29px;margin-right: 10px;'>延迟</span><input class='bt-input-text' min='0' type='number' name='delay'  value='3' style='width:100px' /> 秒\
                        <span data-toggle='tooltip' data-placement='top' title='【延迟】在延迟时间周期内仅记录不同步，到达周期后一次性同步数据，以节省开销' class='bt-ico-ask' style='cursor: pointer;'>?</span>\
                    </div>\
                </div>\
                <div class='line'>\
                    <span class='tname'>连接方式</span>\
                    <div class='info-r c4'>\
                        <select class='bt-input-text' name='conn_type' style='width:100px'>\
                            <option value='key' " + conn_type_key +  ">密钥</option>\
                            <option value='user' " + conn_type_user + ">帐号</option>\
                            <option value='ssh' " + conn_type_ssh + ">SSH</option>\
                        </select>\
                        <span data-toggle='tooltip' data-placement='top' title='密钥和账号的方式，需要目标服务器添加接收配置获取。SSH不需要目标服务器添加配置。SSH方式以root账号连接，常用于同步需要高权限的数据。' class='bt-ico-ask' style='cursor: pointer;'>?</span>\
                        <span style='margin-left: 45px;margin-right: 10px;'>压缩传输</span>\
                        <select class='bt-input-text' name='compress' style='width:100px'>\
                            <option value='true' "+compress_true+">开启</option>\
                            <option value='false' "+compress_false+">关闭</option>\
                        </select>\
                        <span data-toggle='tooltip' data-placement='top' title='【压缩传输】开启后可减少带宽开销，但会增加CPU开销，如带宽充足，建议关闭此选项' class='bt-ico-ask' style='cursor: pointer;'>?</span>\
                    </div>\
                </div>\
                <div class='line conn-key'>\
                    <span class='tname'>接收密钥</span>\
                    <div class='info-r c4'>\
                        <textarea id='mainDomain' class='bt-input-text' name='secret_key' style='width:310px;height:75px;line-height:22px' placeholder='此密钥为 接收配置[接收账号] 的密钥'>"+data['secret_key']+"</textarea>\
                    </div>\
                </div>\
                <div class='line conn-user'>\
                    <span class='tname'>用户名</span>\
                    <div class='info-r c4'>\
                        <input class='bt-input-text' type='text' name='u_user' min='0'  value='"+(data["name"]||'')+"' style='width:310px' />\
                    </div>\
                </div>\
                <div class='line conn-user'>\
                    <span class='tname'>密码</span>\
                    <div class='info-r c4'>\
                        <input class='bt-input-text' type='text' name='u_pass' min='0'  value='"+(data["password"]||'')+"' style='width:310px' />\
                    </div>\
                </div>\
                <div class='line conn-user'>\
                    <span class='tname'>端口</span>\
                    <div class='info-r c4'>\
                        <input class='bt-input-text' type='number' name='u_port' min='0'  value='"+data["rsync"]["port"]+"' style='width:310px' />\
                    </div>\
                </div>\
                <div class='line conn-ssh'>\
                    <span class='tname'>SSH端口</span>\
                    <div class='info-r c4'>\
                        <input class='bt-input-text' type='number' name='ssh_port' min='0'  value='"+(data["ssh_port"] || 22)+"' style='width:310px' />\
                    </div>\
                </div>\
                <div class='line conn-ssh'>\
                    <span class='tname'>密钥文件</span>\
                    <div class='info-r c4'>\
                        <input class='bt-input-text' name='key_path' value='"+(data["key_path"] || '/root/.ssh/id_rsa')+"' placeholder='密钥文件位置（如：/root/.ssh/id_rsa.pub）' style='width:310px' />\
                    </div>\
                </div>\
                <div class='line conn-ssh'>\
                    <span class='tname'>目标目录</span>\
                    <div class='info-r c4'>\
                        <input class='bt-input-text' name='target_path' value='"+(data["target_path"] || '')+"' style='width:310px' />\
                    </div>\
                </div>\
                <ul class=\"help-info-text c7\">\
                </ul>\
              </form>",
            success:function(){
                $('[data-toggle="tooltip"]').tooltip();
                function handleConnTypeChange(conn_type) {
                    if(conn_type == 'key'){
                        $(".conn-key").show();
                        $(".conn-user").hide();
                        $(".conn-ssh").hide();
                    }else if(conn_type == 'user'){
                        $(".conn-key").hide();
                        $(".conn-user").show();
                        $(".conn-ssh").hide();
                    } else {
                        $(".conn-key").hide();
                        $(".conn-user").hide();
                        $(".conn-ssh").show();
                    }
                }
                
                handleConnTypeChange(data['conn_type'] || 'ssh')
                $("select[name='conn_type']").change(function(){
                    handleConnTypeChange($(this).val());
                });


                var selVal = $('.synchronization option:selected').val();
                if (selVal == "false"){
                    $('#period').show();
                }else{
                    $('#period').hide();
                    $('.hour input,.minute input').val('0');
                    $('.minute-n input').val('1');
                }   

                $('.synchronization').change(function(event) {
                    var selVal = $('.synchronization option:selected').val();
                    if (selVal == "false"){
                        $('#period').show();
                    }else{
                        $('#period').hide();
                        $('.hour input,.minute input').val('0');
                        $('.minute-n input').val('1');
                    }
                });

                $("select[name='delete']").change(function(){
                    if($(this).val() == 'true'){
                        var mpath = $('input[name="path"]').val();
                        var msg = '<div><span style="color:orangered;">警告：您选择了完全同步，将会使本机同步与目标机器指定目录的文件保持一致，'
                            +'<br />请确认目录设置是否有误，一但设置错误，可能导致目标机器的目录文件被删除!</span>'
                            +'<br /><br /> <span style="color:red;">注意： 同步程序将本机目录：'
                            +mpath+'的所有数据同步到目标服务器，若目标服务器的同步目录存在其它文件将被删除!</span> <br /><br /> 已了解风险，请按确定继续</div>';

                        layer.confirm(msg,{title:'数据安全风险警告',icon:2,closeBtn: 1,shift: 5,
                        btn2:function(){
                            setTimeout(function(){$($("select[name='delete']").children("option")[0]).prop('selected',true);},100);
                        }
                        });
                    }
                });

                $("input[name='path']").change(function(event) {
                    let val = $(this).val();
                    if (val) {
                        $("input[name='target_path']").val(val);
                    }
                });
                
                var selVal = $('#period select option:selected').val();
                if (selVal == 'day'){
                    $('.hour,.minute').show();
                    if ($('.hour input').val() == ''){
                        $('.hour input,.minute input').val('0');
                    }
                    $('.minute-n').hide();
                }else{
                    $('.hour,.minute').hide();
                    $('.minute-n').show();
                    if ($('.minute-n input').val() == ''){
                        $('.minute-n input').val('1');
                    }
                }
                $('#period').change(function(event) {
                    var selVal = $('#period select option:selected').val();
                    if (selVal == 'day'){
                        $('.hour,.minute').show();
                        if ($('.hour input').val() == ''){
                            $('.hour input,.minute input').val('0');
                        }
                        $('.minute-n').hide();
                    }else{
                        $('.hour,.minute').hide();
                        $('.minute-n').show();
                        if ($('.minute-n input').val() == ''){
                            $('.minute-n input').val('1');
                        }
                    }
                });
            },
            yes:async function(index){
                var args = {};
                var conn_type = $("select[name='conn_type']").val();
        
                if(conn_type == 'key'){
                    if ( $('textarea[name="secret_key"]').val() != ''){
                        args['secret_key'] = $('textarea[name="secret_key"]').val();
                    } else {
                        layer.msg('请输入接收密钥！');
                        return false;
                    }
                } else if (conn_type == 'user') {
                    args['sname'] = $("input[name='u_user']").val();
                    args['password'] = $("input[name='u_pass']").val();
                    var port = Number($("input[name='u_port']").val());
                    args['port'] = port;
                    if (!args['sname'] || !args['password'] || !args['port']){
                        layer.msg('请输入帐号、密码、端口信息');
                        return false;
                    }
                } else {
                    args['ssh_port'] = $("input[name='ssh_port']").val();
                    args['key_path'] = $("input[name='key_path']").val();
                    args['target_path'] = $("input[name='target_path']").val();
                    if (!args['ssh_port'] || !args['key_path'] || !args['target_path']){
                        layer.msg('请输入SSH端口、密钥文件、目标目录信息');
                        return false;
                    }
                }

                if ($('input[name="ip"]').val() == ''){
                    layer.msg('请输入服务器IP地址！');
                    return false;
                }

                args['sname'] = $("input[name='u_user']").val();
                args['password'] = $("input[name='u_pass']").val();
                var port = Number($("input[name='u_port']").val());
                args['port'] = port;
                args['ssh_port'] = $("input[name='ssh_port']").val();
                args['key_path'] = $("input[name='key_path']").val();
                args['target_path'] = $("input[name='target_path']").val();

                
                args['ip'] = $('input[name="ip"]').val();
                args['path'] = $('input[name="path"]').val();
                args['delete'] = $('select[name="delete"]').val();
                args['realtime'] = $('select[name="realtime"]').val();
                args['delay'] = $('input[name="delay"]').val();

                args['bwlimit'] = $('input[name="bwlimit"]').val();
                args['conn_type'] = $('select[name="conn_type"]').val();
                args['compress'] = $('select[name="compress"]').val();

                args['period'] = $('select[name="period"]').val(); 
                args['hour'] = $('input[name="hour"]').val();
                args['minute'] = $('input[name="minute"]').val();
                args['minute-n'] = $('input[name="minute-n"]').val();
                args['edit'] = (name!='')

                if(args['conn_type'] == 'ssh') {
                    let testResult = JSON.parse((await rsPost('test_ssh', args)).data)
                    if (!testResult.status) {
                        console.log(testResult)
                        layer.msg("使用密钥文件连接服务器失败!<br/>请检查对应的公钥内容是否添加到目标服务器的/root/.ssh/authorized_keys中",{icon:2,time:8000,shade: [0.3, '#000']});
                        return 
                    }
                }

                rsPost('lsyncd_add', args, async function(rdata){
                    var rdata = $.parseJSON(rdata.data);
                    layer.msg(rdata.msg,{icon:rdata.status?1:2,time:2000,shade: [0.3, '#000']});

                    if (rdata.status){
                        
                        // let addKnownHostsScriptData = await rsPost('get_add_known_hosts_script', args);
                        // if (addKnownHostsScriptData.data) {
                        //     await execScriptAndShowLog('正在添加可信地址...', addKnownHostsScriptData.data, {logWindowSuccessTimeout: -1});    
                        // }

                        setTimeout(function(){
                            layer.close(index);
                            lsyncdSend();
                        },500);
                        return;
                    }
                });
                return true;
            }
        });
    });
}

function lsyncdDelete(name){
    safeMessage('删除['+name+']', '您真的要删除['+name+']吗？', function(){
        var args = {};
        args['name'] = name;
        rsPost('lsyncd_delete', args, function(rdata){
            var rdata = $.parseJSON(rdata.data);
            layer.msg(rdata.msg,{icon:rdata.status?1:2,time:2000,shade: [0.3, '#000']});
            setTimeout(function(){lsyncdSend();},2000);
        });
    });
}

function lsyncdStatus(name, status){
  var confirm = layer.confirm(status == 'disabled'?'暂停后将无法自动运行，您真的要停用吗？':'该任务已停用，是否要启用这个任务', {title:'提示',icon:3,closeBtn:1},function(index) {
		if (index > 0) {
			var loadT = layer.msg('正在设置状态，请稍后...',{icon:16,time:0,shade: [0.3, '#000']});
      var args = {};
      args['name'] = name;
      args['status'] = status;
      rsPost('lsyncd_status', args, function(rdata){
          var rdata = $.parseJSON(rdata.data);
					layer.close(loadT);
					layer.close(confirm);
          layer.msg(rdata.msg,{icon:rdata.status?1:2,time:2000,shade: [0.3, '#000']});
          setTimeout(function(){lsyncdSend();},1000);
      });
		}
	});
  
}

function lsyncdRun(name){
    var args = {};
    args["name"] = name;
    rsPost('lsyncd_run', args, function(data) {
      let rdata = $.parseJSON(data.data);
      layer.msg(rdata.msg,{icon:rdata.status?1:2});
      messageBox({timeout: 300, autoClose: true, toLogAfterComplete: true});
      // doTaskWithLock('rsyncd 同步', rdata.data)
    });
}

function lsyncdLog(name, realtime){
    // var args = {};
    // args["name"] = name;
    // pluginStandAloneLogs("rsyncd", '', "lsyncd_log", JSON.stringify(args));
    // let logDir = realtime == 'true'? `/www/server/rsyncd/logs/` : `/www/server/rsyncd/send/${name}/logs/`;
    openNewWindowPath(`/www/server/rsyncd/send/${name}/logs/`)
}


function lsyncdExclude(name){
    layer.open({
        type:1,
        title:'过滤器',
        area: '400px', 
        shadeClose:false,
        closeBtn:2,
        content:'<div class="lsyncd_exclude">\
                <div style="overflow:hidden;">\
                    <fieldset>\
                        <legend>排除的文件和目录</legend>\
                        <input type="text" class="bt-input-text mr5" data-type="exclude" title="例如：/home/www/" placeholder="例如：*.log" style="width:305px;">\
                        <button data-type="exclude" class=" addList btn btn-default btn-sm">添加</button>\
                        <div class="table-overflow">\
                            <table class="table table-hover BlockList"><tbody></tbody></table>\
                        </div>\
                    </fieldset>\
                </div>\
                <div>\
                    <ul class="help-info-text c7" style="list-style-type:decimal;">\
                        <li>排除的文件和目录是指当前目录下不需要同步的目录或者文件</li>\
                        <li>如果规则以斜线 <code>/</code>开头，则从头开始要匹配全部</li>\
                        <li>如果规则以 <code>/</code>结尾，则要匹配监控路径的末尾</li>\
                        <li><code>?</code> 匹配任何字符，但不包括<code>/</code></li>\
                        <li><code>*</code> 匹配0或多个字符，但不包括<code>/</code></li>\
                        <li><code>**</code> 匹配0或多个字符，可以是<code>/</code></li>\
                    </ul>\
                </div>\
            </div>'
    });

    function getIncludeExclude(mName){
        loadT = layer.msg('正在获取数据...',{icon:16,time:0,shade: [0.3, '#000']});
        rsPost('lsyncd_get_exclude',{"name":mName}, function(rdata) {
            layer.close(loadT);

            var rdata = $.parseJSON(rdata.data);
            var res = rdata.data;

            var list=''
            for (var i = 0; i < res.length; i++) {
                list += '<tr><td>'+ res[i] +'</td><td><a href="javascript:;" data-type='+ mName +' class="delList">删除</a></td></tr>';
            }
            $('.lsyncd_exclude .BlockList tbody').empty().append(list);
        });
    }
    getIncludeExclude(name);


    function addArgs(name,exclude){
        loadT = layer.msg('正在添加...',{icon:16,time:0,shade: [0.3, '#000']});
        rsPost('lsyncd_add_exclude', {name:name,exclude:exclude}, function(res){
            layer.close(loadT);

            console.log('addArgs:',res);

            if (res.status){
                getIncludeExclude(name);
                $('.lsyncd_exclude input').val('');
                layer.msg(res.msg);
            }else{
                layer.msg(res.msg);
            }
        });
    }
    $('.addList').click(function(event) {
        var val = $(this).prev().val();
        if(val == ''){
            layer.msg('当前输入内容为空,请输入');
            return false;
        }
        addArgs(name,val);
    });
    $('.lsyncd_exclude input').keyup(function(event){
        if (event.which == 13){
            var val = $(this).val();
            if(val == ''){
                layer.msg('当前输入内容为空,请输入');
                return false;
            }
            addArgs(name,val);
        }
    });


    $('.lsyncd_exclude').on('click', '.delList', function(event) {
        loadT = layer.msg('正在删除...',{icon:16,time:0,shade: [0.3, '#000']});
        var val = $(this).parent().prev().text();
        rsPost('lsyncd_remove_exclude',{"name":name,exclude:val}, function(rdata) {
            layer.close(loadT);

            console.log(rdata)
            var rdata = $.parseJSON(rdata.data);
            var res = rdata.data;

            var list=''
            for (var i = 0; i < res.length; i++) {
                list += '<tr><td>'+ res[i] +'</td><td><a href="javascript:;" data-type='+ name +' class="delList">删除</a></td></tr>';
            }
            $('.lsyncd_exclude .BlockList tbody').empty().append(list);
        });
    });
}

function lsyncdConfLog(){
    // pluginStandAloneLogs("rsyncd","","lsyncd_conf_log");;
    openNewWindowPath(`/www/server/rsyncd/logs/`)
}

function lsyncdStatusLog(){
  execScriptAndShowLog('正在获取同步状态...', 'head -n 10 /www/server/rsyncd/logs/lsyncd.status', {doLogWindowsSuccess: false});
}


function lsyncdServiceLog(){
  execScriptAndShowLog('正在获取lsyncd日志...', 'journalctl -f -u lsyncd');
}

function lsyncdServiceStatus() {
  rsPost('lsyncd_service_status', '', function(data){
    let status = data.data
    $('.lsyncd-status').text(status == 'ok'?'运行中':'已停止');
    $('.lsyncd-status').css('color', status == 'ok'?'green':'red');
    visibleDom('.lsyncd-service-start-btn', status != 'ok');
    visibleDom('.lsyncd-service-stop-btn', status == 'ok');
  });

}

function lsyncdServiceOpt(opt) {
  rsPost('lsyncd_service_opt', {opt}, function(data){
    var rdata = $.parseJSON(data.data);
    layer.msg(rdata.msg,{icon:rdata.status?1:2,time:2000,shade: [0.3, '#000']});
    lsyncdServiceStatus();
  });
}


function lsyncdRealtime(){
  var con = `\
  
  <div class="safe container-fluid mt10" style="overflow: hidden;">
      <div class="flex align-center">
          lsyncd服务状态：
          <span class="lsyncd-status">获取中...</span>
      </div>
      <div class="mt15 flex align-center">
          <button class="btn btn-success btn-sm mr5 lsyncd-service-start-btn" onclick="lsyncdServiceOpt('start')" >启用</button>\    
          <button class="btn btn-danger btn-sm mr5 lsyncd-service-stop-btn" onclick="lsyncdServiceOpt('stop')" >停用</button>\
          <button class="btn btn-success btn-sm mr5" onclick="lsyncdServiceOpt('restart')" >重启</button>\
          <button class="btn btn-default btn-sm mr5" onclick="lsyncdServiceLog()" >服务日志</button>\
          <button class="btn btn-default btn-sm mr5" onclick="lsyncdStatusLog()" >同步状态</button>\
          <button class="btn btn-default btn-sm mr5" onclick="lsyncdConfLog()" >同步日志</button>\
      </div>
  </div>
  <hr/>\
  <div class="safe container-fluid mt10" style="overflow: hidden;">
      <div class="flex align-center">任务设置：</div>
      <div class="mt15">\

        <div class="card mb10" id="lsyncd-log-cut-cron">\
          <span class="flex align-center mb10">定时切割实时日志：</span>\
          
          <div>\
              <span>每天</span>\
              <span>\
                  <input type="hidden" name="id" value="">\
                  <input type="number" name="hour" value="20" maxlength="2" max="23" min="0">\
                  <span class="name">:</span>\
                  <input type="number" name="minute" value="30" maxlength="2" max="59" min="0">\
              </span>\
              <span>定时执行切割</span>\
          </div>\
          <div class="flex align-center mtb10">\
              <div class="mr5">保留规则</div>\
              <div class="plan_hms pull-left mr20 bt-input-text">\
                  <span><input type="number" name="saveAllDay" maxlength="4" max="100" min="1"></span>\
                  <span class="name" style="width: 160px;">天内全部保留，其余只保留</span>\
                  <span><input type="number" name="saveOther" maxlength="4" max="100" min="1"></span>\
                  <span class="name" style="width: 90px;">份，最长保留</span>\
                  <span><input type="number" name="saveMaxDay" maxlength="4" max="100" min="1"></span>\
                  <span class="name">天</span>\
              </div>\
          </div>\
          <button id="lsyncd-log-cut-cron-add" style="display: none;"\
              class="btn btn-success btn-sm" onclick="addLsyncdLogCutCron();">创建</button>\
          <button id="lsyncd-log-cut-cron-update" style="display: none;"\
              class="btn btn-success btn-sm" onclick="updateLsyncdLogCutCron();">修改</button>\
          <button id="lsyncd-log-cut-cron-delete" style="display: none;"\
              class="btn btn-danger btn-sm" onclick="deleteLsyncdLogCutCron();">删除</button>\
        </div>\
        <div class="card" id="lsyncd-all-sync-cron">\
          <span class="flex align-center mb10">定时同步全部实时任务：</span>\
          <div class="mb10">\
              <span>每天</span>\
              <span>\
                  <input type="hidden" name="id" value="">\
                  <input type="number" name="hour" value="20" maxlength="2" max="23" min="0">\
                  <span class="name">:</span>\
                  <input type="number" name="minute" value="30" maxlength="2" max="59" min="0">\
              </span>\
              <span>定时执行</span>\
          </div>\
          <button id="lsyncd-all-sync-add" style="display: none;"\
              class="btn btn-success btn-sm" onclick="addLsyncdAllSyncCron();">创建</button>\
          <button id="lsyncd-all-sync-update" style="display: none;"\
              class="btn btn-success btn-sm" onclick="updateLsyncdAllSyncCron();">修改</button>\
          <button id="lsyncd-all-sync-delete" style="display: none;"\
              class="btn btn-danger btn-sm" onclick="deleteLsyncdAllSyncCron();">删除</button>\
        </div>\

      </div>\
    </div>\
  </div>
  `;

  $(".soft-man-con").html(con);
  
  getLsyncdLogCutCron();
  getLsyncdAllSyncCron();
  lsyncdServiceStatus();
}

function lsyncdSend(){
    rsPost('lsyncd_list', '', function(data){
        var rdata = $.parseJSON(data.data);
        console.log(rdata);
        if (!rdata.status){
            layer.msg(rdata.msg,{icon:rdata.status?1:2,time:2000,shade: [0.3, '#000']});
            return;
        }
        var list = rdata.data.list;
        var con = '';

        con += '<div style="padding-top:1px;">\
                <button class="btn btn-success btn-sm" onclick="createSendTask();">创建发送任务</button>\
            </div>';

        con += '<div class="lsyncd-send-table divtable" style="margin-top:5px;"><table class="table table-hover" width="100%" cellspacing="0" cellpadding="0" border="0">';
        con += '<thead><tr>';
        con += '<th>名称(标识)</th>';
        con += '<th>启动状态</th>';
        con += '<th>连接状态</th>';
        con += '<th>源目录</th>';
        con += '<th>同步到</th>';
        con += '<th>模式</th>';
        con += '<th>周期</th>';
        con += '<th>操作</th>';
        con += '</tr></thead>';

        con += '<tbody>';

        

        for (var i = 0; i < list.length; i++) {
            var mode = '增量';
            if (list[i]['delete'] == 'true'){
                mode = '完全';
            } else {
                mode = '增量';
            }

            var period = "实时";
            if (list[i]['realtime'] == 'true'){ 
                period = '实时';
            } else {
                period = '定时';
            }

            let target_path = list[i]['conn_type'] == 'ssh'? (list[i]['ip']+":"+list[i]['target_path']) : list[i]['ip']+":"+list[i]['name']

            let status = list[i]['status'] != 'disabled' ?
            '<td><span class="btOpen" onclick="lsyncdStatus(\'' + list[i]['name'] + '\',\'disabled\')" style="color:rgb(92, 184, 92);cursor:pointer" title="停用任务">正常<span class="glyphicon glyphicon-play"></span></span></td>' 
            :'<td><span onclick="lsyncdStatus(\''+ list[i]['name'] +'\',\'enabled\')" class="btClose" style="color:red;cursor:pointer" title="启用任务">停用<span style="color:rgb(255, 0, 0);" class="glyphicon glyphicon-pause"></span></span></td>';

            let connect_status = `<td class="conn-status-${i}"><span class="tag disabled">测试中...<span></td>`;
            // let connect_status = `<td class="conn-status-${i}">
            //   <span class="tag ${list[i]['connect_status'] = true? 'normal': 'error' }">${ list[i]['connect_status'] = true? '正常': '异常' }<span>
            // </td>`;
                

            con += '<tr>'+
                '<td><div class="overflow_hide" style="width: 120px;" title="' + list[i]['name'] + '">' + list[i]['name']+'</div></td>' +
                status +
                connect_status +
                '<td><a class="btlink overflow_hide" style="width:80px;" onclick="openNewWindowPath(\''+list[i]['path']+'\')" title="' + list[i]['path'] + '">' + list[i]['path']+'</a></td>' +
                '<td><div class="overflow_hide" style="width: 120px;" title="' + target_path + '">' + target_path+'</div></td>' +
                '<td>' + mode+'</td>' +
                '<td>' + period +'</td>' +
                '<td>\
                    <a class="btlink" onclick="lsyncdRun(\''+list[i]['name']+'\')">同步</a>\
                    | <a class="btlink" onclick="lsyncdLog(\''+list[i]['name']+'\', \''+list[i]['realtime']+'\')">日志</a>\
                    | <a class="btlink" onclick="lsyncdExclude(\''+list[i]['name']+'\')">过滤器</a>\
                    | <a class="btlink" onclick="createSendTask(\''+list[i]['name']+'\')">编辑</a>\
                    | <a class="btlink" onclick="lsyncdDelete(\''+list[i]['name']+'\')">删除</a>\
                </td>\
                </tr>';
        }

        con += '</tbody>';
        con += '</table></div>';

        $(".soft-man-con").html(con);
        // syncdListTest(list);
    });
}

function syncdListTest(list) {
  for (index in list) {
    let item = list[index];
    let itemStatusClass = '.conn-status-' + index;
    rsPost('lsyncd_test', {name: item.name}, function(rdata){
      let data = JSON.parse(rdata['data']);
      $('.lsyncd-send-table '+ itemStatusClass).html(data['status']?'<span class="tag normal">正常</span>':`<span class="tag error" title="${data.msg}">异常</span>`);        
    });
  }
}



///////////////// ----------------- 接收配置 ---------------- //////////////
function rsyncdConf(){
    rsPost('conf', {}, function(rdata){
        rpath = rdata['data'];
        if (rdata['status']){
            onlineEditFile(0, rpath);
        } else {
            layer.msg(rdata.msg,{icon:1,time:2000,shade: [0.3, '#000']});
        }        
    });
}

function rsyncdLog(name){
    // openNewWindowPath(`/www/server/rsyncd/receive/${name}/logs/`)
    pluginStandAloneLogs("rsyncd","","run_log");
}


function rsyncdReceive(){
	rsPost('rec_list', '', function(data){
		var rdata = $.parseJSON(data.data);
		if (!rdata.status){
			layer.msg(rdata.msg,{icon:rdata.status?1:2,time:2000,shade: [0.3, '#000']});
			return;
		}
		// console.log(rdata);
		var list = rdata.data;
		var con = '';

        con += '<div style="padding-top:1px;">\
                <button class="btn btn-success btn-sm" onclick="addReceive();">创建接收任务</button>\
                <button class="btn btn-success btn-sm" onclick="rsyncdConf();">配置</button>\
                <button class="btn btn-success btn-sm" onclick="rsyncdLog();">日志</button>\
            </div>';

        con += '<div class="divtable" style="margin-top:5px;"><table class="table table-hover" width="100%" cellspacing="0" cellpadding="0" border="0">';
        con += '<thead><tr>';
        con += '<th>服务名</th>';
        con += '<th>路径</th>';
        con += '<th>备注</th>';
        con += '<th>操作</th>';
        con += '</tr></thead>';

        con += '<tbody>';

        //<a class="btlink" onclick="modReceive(\''+list[i]['name']+'\')">编辑</a>
        for (var i = 0; i < list.length; i++) {
            con += '<tr>'+
                '<td>' + list[i]['name']+'</td>' +
                '<td><a class="btlink overflow_hide" onclick="openNewWindowPath(\''+list[i]['path']+'\')">' + list[i]['path']+'</a></td>' +
                '<td>' + list[i]['comment']+'</td>' +
                '<td>\
                    <a class="btlink" onclick="cmdRecCmd(\''+list[i]['name']+'\')">命令</a>\
                	| <a class="btlink" onclick="cmdRecSecretKey(\''+list[i]['name']+'\')">密钥</a>\
                    | <a class="btlink" onclick="addReceive(\''+list[i]['name']+'\')">编辑</a>\
                	| <a class="btlink" onclick="delReceive(\''+list[i]['name']+'\')">删除</a></td>\
                </tr>';
        }

        con += '</tbody>';
        con += '</table></div>';

        $(".soft-man-con").html(con);
	});
}


function addReceive(name = ""){
    rsPost('get_rec',{"name":name},function(rdata) {
        var rdata = $.parseJSON(rdata.data);
        var data = rdata.data;

        var readonly = "";
        if (name !=""){
            readonly = 'readonly="readonly"'
        }

        var loadOpen = layer.open({
            type: 1,
            title: '创建接收',
            area: '400px',
            btn:['确认','取消'],
            content:"<div class='bt-form pd20 c6'>\
                <div class='line'>\
                    <span class='tname'>项目名</span>\
                    <div class='info-r c4'>\
                        <input id='name' value='"+data["name"]+"' class='bt-input-text' type='text' name='name' placeholder='项目名' style='width:200px' "+readonly+"/>\
                    </div>\
                </div>\
                <div class='line'>\
                    <span class='tname'>密钥</span>\
                    <div class='info-r c4'>\
                        <input id='MyPassword' value='"+data["pwd"]+"' class='bt-input-text' type='text' name='pwd' placeholder='密钥' style='width:200px'/>\
                        <span title='随机密码' class='glyphicon glyphicon-repeat cursor' onclick='repeatPwd(16)'></span>\
                    </div>\
                </div>\
                <div class='line'>\
                    <span class='tname'>同步到</span>\
                    <div class='info-r c4'>\
                        <input id='inputPath' value='"+data["path"]+"' class='bt-input-text' type='text' name='path' placeholder='/' style='width:200px'/>\
                        <span class='glyphicon glyphicon-folder-open cursor' onclick=\"changePath('inputPath', {'endSlash': true})\"></span>\
                    </div>\
                </div>\
                <div class='line'>\
                    <span class='tname'>备注</span>\
                    <div class='info-r c4'>\
                        <input id='ps' class='bt-input-text' type='text' name='ps' value='"+data["comment"]+"' placeholder='备注' style='width:200px'/>\
                    </div>\
                </div>\
            </div>",
            success:function(layero, index){},
            yes:function(){
                var args = {};
                args['name'] = $('#name').val();
                args['pwd'] = $('#MyPassword').val();
                args['path'] = $('#inputPath').val();
                args['ps'] = $('#ps').val();
                var loadT = layer.msg('正在获取...', { icon: 16, time: 0 });
                rsPost('add_rec', args, function(data){
                    var rdata = $.parseJSON(data.data);
                    layer.close(loadOpen);
                    layer.msg(rdata.msg,{icon:rdata.status?1:2,time:2000,shade: [0.3, '#000']});
                    setTimeout(function(){rsyncdReceive();},2000);
                });
            }
        });
    })
}


function delReceive(name){
	safeMessage('删除['+name+']', '您真的要删除['+name+']吗？', function(){
		var _data = {};
		_data['name'] = name;
		rsPost('del_rec', _data, function(data){
            var rdata = $.parseJSON(data.data);
            layer.msg(rdata.msg,{icon:rdata.status?1:2,time:2000,shade: [0.3, '#000']});
            setTimeout(function(){rsyncdReceive();},2000);
        });
	});
}

function cmdRecSecretKey(name){
	var _data = {};
	_data['name'] = name;
	rsPost('cmd_rec_secret_key', _data, function(data){
        var rdata = $.parseJSON(data.data);
	    layer.open({
	        type: 1,
	        title: '接收密钥',
	        area: '400px',
	        content:"<div class='bt-form pd20 pb70 c6'><textarea class='form-control' rows='6' readonly='readonly'>"+rdata.data+"</textarea></div>"
    	});
    });
}

function cmdRecCmd(name){
    var _data = {};
    _data['name'] = name;
    rsPost('cmd_rec_cmd', _data, function(data){
        var rdata = $.parseJSON(data.data);
        layer.open({
            type: 1,
            title: '接收命令例子',
            area: '400px',
            content:"<div class='bt-form pd20 pb70 c6'>"+rdata.data+"</div>"
        });
    });
}


function rsRead(){
	var readme = '<ul class="help-info-text c7">';
    readme += '<li>如需将其他服务器数据同步到本地服务器，请在接受配置中 "创建接收任务" </li>';
    readme += '<li>如果开启防火墙,需要放行873端口</li>';
    readme += '</ul>';

    $('.soft-man-con').html(readme);   
}




var defaultLsyncdLogCutCron = {      
  name: '[勿删]lsyncd实时日志切割',
  type: 'day',
  where1: '',
  week: '',
  sType: 'toShell',
  stype: 'toShell',
  sName: '',
  sBody: `
#!/bin/bash
timestamp=$(date +%Y%m%d_%H%M%S)
cp /www/server/rsyncd/logs/lsyncd.log /www/server/rsyncd/logs/lsyncd_\${timestamp}.log
  `,
  backupTo: 'localhost' };
var lsyncdLogCutCron = {...defaultLsyncdLogCutCron}

var defaultLsyncdAllSyncCron = {      
  name: '[勿删]lsyncd实时任务定时同步',
  type: 'day',
  where1: '',
  week: '',
  sType: 'toShell',
  stype: 'toShell',
  sName: '',
  sBody: `
#!/bin/bash
pushd /www/server/jh-panel > /dev/null  
python3 /www/server/jh-panel/plugins/rsyncd/index.py lsyncd_realtime_all_run
popd > /dev/null
  `,
  backupTo: 'localhost' };
var lsyncdAllSyncCron = {...defaultLsyncdAllSyncCron}


function getLsyncdLogCutCron() {
  $.post('/crontab/get', { name: lsyncdLogCutCron.name },function(rdata){
    const { status } = rdata;
    if (status) {
      const { id,name,type,where_hour: hour,where_minute: minute,saveAllDay,saveOther,saveMaxDay} = rdata.data;
      $("#lsyncd-log-cut-cron #lsyncd-log-cut-cron-add").css("display", "none");
      $("#lsyncd-log-cut-cron #lsyncd-log-cut-cron-update").css("display", "inline-block");
      $("#lsyncd-log-cut-cron #lsyncd-log-cut-cron-delete").css("display", "inline-block");
      $("#lsyncd-log-cut-cron input[name='id']").val(id);
      $("#lsyncd-log-cut-cron input[name='hour']").val(hour);
      $("#lsyncd-log-cut-cron input[name='minute']").val(minute);
      $("#lsyncd-log-cut-cron input[name='saveAllDay']").val(saveAllDay);
      $("#lsyncd-log-cut-cron input[name='saveOther']").val(saveOther);
      $("#lsyncd-log-cut-cron input[name='saveMaxDay']").val(saveMaxDay);
      // lsyncdLogCutCron = rdata.data;
    }else {
      $("#lsyncd-log-cut-cron #lsyncd-log-cut-cron-add").css("display", "inline-block");
      $("#lsyncd-log-cut-cron #lsyncd-log-cut-cron-update").css("display", "none");
      $("#lsyncd-log-cut-cron #lsyncd-log-cut-cron-delete").css("display", "none");
      $("#lsyncd-log-cut-cron input[name='id']").val("");
      $("#lsyncd-log-cut-cron input[name='hour']").val(0);
      $("#lsyncd-log-cut-cron input[name='minute']").val(0);
      $("#lsyncd-log-cut-cron input[name='saveAllDay']").val(3);
      $("#lsyncd-log-cut-cron input[name='saveOther']").val(1);
      $("#lsyncd-log-cut-cron input[name='saveMaxDay']").val(30);
      // lsyncdLogCutCron = {...defaultLsyncdLogCutCron};
    }
  },'json');
}


function getLsyncdAllSyncCron() {
  $.post('/crontab/get', { name: lsyncdAllSyncCron.name },function(rdata){
    const { status } = rdata;
    if (status) {
      const { id,name,type,where_hour: hour,where_minute: minute} = rdata.data;
      $("#lsyncd-all-sync-cron #lsyncd-all-sync-add").css("display", "none");
      $("#lsyncd-all-sync-cron #lsyncd-all-sync-update").css("display", "inline-block");
      $("#lsyncd-all-sync-cron #lsyncd-all-sync-delete").css("display", "inline-block");
      $("#lsyncd-all-sync-cron input[name='id']").val(id);
      $("#lsyncd-all-sync-cron input[name='hour']").val(hour);
      $("#lsyncd-all-sync-cron input[name='minute']").val(minute);
      // lsyncdAllSyncCron = rdata.data;
    }else {
      $("#lsyncd-all-sync-cron #lsyncd-all-sync-add").css("display", "inline-block");
      $("#lsyncd-all-sync-cron #lsyncd-all-sync-update").css("display", "none");
      $("#lsyncd-all-sync-cron #lsyncd-all-sync-delete").css("display", "none");
      $("#lsyncd-all-sync-cron input[name='id']").val("");
      $("#lsyncd-all-sync-cron input[name='hour']").val(0);
      $("#lsyncd-all-sync-cron input[name='minute']").val(0);
      // lsyncdAllSyncCron = {...defaultLsyncdLogCutCron};
    }
  },'json');
}


function deleteLsyncdLogCutCron(e) {
  var id = $("#lsyncd-log-cut-cron input[name='id']").val();
  if (id) {
    safeMessage('确认删除', '确定删除定时任务吗', function(){
        $.post('/crontab/del', { id },function(rdata){
            getLsyncdLogCutCron();
            layer.msg(rdata.msg,{icon:rdata.status?1:2}, 5000);
        },'json');
    })
  }
}

function deleteLsyncdAllSyncCron(e) {
  var id = $("#lsyncd-all-sync-cron input[name='id']").val();
  if (id) {
    safeMessage('确认删除', '确定删除定时任务吗', function(){
        $.post('/crontab/del', { id },function(rdata){
            getLsyncdAllSyncCron();
            layer.msg(rdata.msg,{icon:rdata.status?1:2}, 5000);
        },'json');
    })
  }
}
function addLsyncdLogCutCron() {
  var hour =  $("#lsyncd-log-cut-cron input[name='hour']").val();
  var minute =  $("#lsyncd-log-cut-cron input[name='minute']").val();
  var saveAllDay =  $("#lsyncd-log-cut-cron input[name='saveAllDay']").val();
  var saveOther =  $("#lsyncd-log-cut-cron input[name='saveOther']").val();
  var saveMaxDay =  $("#lsyncd-log-cut-cron input[name='saveMaxDay']").val();
  
  // 添加清理脚本
  let cleanScript = `python3 /www/server/jh-panel/scripts/clean.py /www/server/rsyncd/logs/ '{"saveAllDay": "${saveAllDay}", "saveOther": "${saveOther}", "saveMaxDay": "${saveMaxDay}"}'`
  lsyncdLogCutCron.sBody = lsyncdLogCutCron.sbody = lsyncdLogCutCron.sBody + "\n" + cleanScript;
  
  $.post('/crontab/add', { ...lsyncdLogCutCron, hour, minute, saveAllDay, saveOther, saveMaxDay },function(rdata){
      getLsyncdLogCutCron();
      layer.msg(rdata.msg,{icon:rdata.status?1:2}, 5000);
  },'json');
}
function addLsyncdAllSyncCron() {
  var hour =  $("#lsyncd-all-sync-cron input[name='hour']").val();
  var minute =  $("#lsyncd-all-sync-cron input[name='minute']").val();
  
  $.post('/crontab/add', { ...lsyncdAllSyncCron, hour, minute },function(rdata){
    getLsyncdAllSyncCron();
      layer.msg(rdata.msg,{icon:rdata.status?1:2}, 5000);
  },'json');
}

function updateLsyncdLogCutCron() {
  var id = $("#lsyncd-log-cut-cron input[name='id']").val();
  var hour =  $("#lsyncd-log-cut-cron input[name='hour']").val();
  var minute =  $("#lsyncd-log-cut-cron input[name='minute']").val();
  var saveAllDay =  $("#lsyncd-log-cut-cron input[name='saveAllDay']").val();
  var saveOther =  $("#lsyncd-log-cut-cron input[name='saveOther']").val();
  var saveMaxDay =  $("#lsyncd-log-cut-cron input[name='saveMaxDay']").val();
  if (id) {
      $.post('/crontab/modify_crond', { ...lsyncdLogCutCron, id, hour, minute, saveAllDay, saveOther, saveMaxDay },function(rdata){
          getLsyncdLogCutCron();
          layer.msg(rdata.msg,{icon:rdata.status?1:2}, 5000);
      },'json');
  }
}

function updateLsyncdAllSyncCron() {
  var id = $("#lsyncd-all-sync-cron input[name='id']").val();
  var hour =  $("#lsyncd-all-sync-cron input[name='hour']").val();
  var minute =  $("#lsyncd-all-sync-cron input[name='minute']").val();
  if (id) {
      $.post('/crontab/modify_crond', { ...lsyncdAllSyncCron, id, hour, minute },function(rdata){
          getLsyncdAllSyncCron();
          layer.msg(rdata.msg,{icon:rdata.status?1:2}, 5000);
      },'json');
  }
}
