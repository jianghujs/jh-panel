function kpPost(method, version, args,callback){
    var loadT = layer.msg('正在获取...', { icon: 16, time: 0, shade: 0.3 });

    var req_data = {};
    req_data['name'] = 'keepalived';
    req_data['func'] = method;
    req_data['version'] = version;
 
    if (typeof(args) == 'string'){
        req_data['args'] = JSON.stringify(toArrayObject(args));
    } else {
        req_data['args'] = JSON.stringify(args);
    }

    $.post('/plugins/run', req_data, function(data) {
        layer.close(loadT);
        if (!data.status){
            //错误展示10S
            layer.msg(data.msg,{icon:0,time:2000,shade: [10, '#000']});
            return;
        }

        if(typeof(callback) == 'function'){
            callback(data);
        }
    },'json'); 
}

function kpPostCallbak(method, version, args,callback){
    var loadT = layer.msg('正在获取...', { icon: 16, time: 0, shade: 0.3 });

    var req_data = {};
    req_data['name'] = 'keepalived';
    req_data['func'] = method;
    args['version'] = version;
 
    if (typeof(args) == 'string'){
        req_data['args'] = JSON.stringify(toArrayObject(args));
    } else {
        req_data['args'] = JSON.stringify(args);
    }

    $.post('/plugins/callback', req_data, function(data) {
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

//redis负载状态  start
function redisStatus(version) {

    redisPost('run_info',version, {},function(data){
        var rdata = $.parseJSON(data.data);
        // if (!rdata.status){
        //     layer.msg(data.msg,{icon:0,time:2000,shade: [0.3, '#000']});
        //     return;
        // }

        hit = (parseInt(rdata.keyspace_hits) / (parseInt(rdata.keyspace_hits) + parseInt(rdata.keyspace_misses)) * 100).toFixed(2);
        var con = '<div class="divtable">\
                        <table class="table table-hover table-bordered" style="width: 490px;">\
                        <thead><th>字段</th><th>当前值</th><th>说明</th></thead>\
                        <tbody>\
                            <tr><th>uptime_in_days</th><td>' + rdata.uptime_in_days + '</td><td>已运行天数</td></tr>\
                            <tr><th>tcp_port</th><td>' + rdata.tcp_port + '</td><td>当前监听端口</td></tr>\
                            <tr><th>connected_clients</th><td>' + rdata.connected_clients + '</td><td>连接的客户端数量</td></tr>\
                            <tr><th>used_memory_rss</th><td>' + toSize(rdata.used_memory_rss) + '</td><td>Redis当前占用的系统内存总量</td></tr>\
                            <tr><th>used_memory</th><td>' + toSize(rdata.used_memory) + '</td><td>Redis当前已分配的内存总量</td></tr>\
                            <tr><th>used_memory_peak</th><td>' + toSize(rdata.used_memory_peak) + '</td><td>Redis历史分配内存的峰值</td></tr>\
                            <tr><th>mem_fragmentation_ratio</th><td>' + rdata.mem_fragmentation_ratio + '%</td><td>内存碎片比率</td></tr>\
                            <tr><th>total_connections_received</th><td>' + rdata.total_connections_received + '</td><td>运行以来连接过的客户端的总数量</td></tr>\
                            <tr><th>total_commands_processed</th><td>' + rdata.total_commands_processed + '</td><td>运行以来执行过的命令的总数量</td></tr>\
                            <tr><th>instantaneous_ops_per_sec</th><td>' + rdata.instantaneous_ops_per_sec + '</td><td>服务器每秒钟执行的命令数量</td></tr>\
                            <tr><th>keyspace_hits</th><td>' + rdata.keyspace_hits + '</td><td>查找数据库键成功的次数</td></tr>\
                            <tr><th>keyspace_misses</th><td>' + rdata.keyspace_misses + '</td><td>查找数据库键失败的次数</td></tr>\
                            <tr><th>hit</th><td>' + hit + '%</td><td>查找数据库键命中率</td></tr>\
                            <tr><th>latest_fork_usec</th><td>' + rdata.latest_fork_usec + '</td><td>最近一次 fork() 操作耗费的微秒数</td></tr>\
                        <tbody>\
                </table></div>';
        $(".soft-man-con").html(con);
    });
}
//redis负载状态 end

//配置修改
function getRedisConfig(version) {
    redisPost('get_redis_conf', version,'',function(data){
        // console.log(data);
        var rdata = $.parseJSON(data.data);
        // console.log(rdata);
        var mlist = '';
        for (var i = 0; i < rdata.length; i++) {
            var w = '70'
            if (rdata[i].name == 'error_reporting') w = '250';
            var ibody = '<input style="width: ' + w + 'px;" class="bt-input-text mr5" name="' + rdata[i].name + '" value="' + rdata[i].value + '" type="text" >';
            switch (rdata[i].type) {
                case 0:
                    var selected_1 = (rdata[i].value == 1) ? 'selected' : '';
                    var selected_0 = (rdata[i].value == 0) ? 'selected' : '';
                    ibody = '<select class="bt-input-text mr5" name="' + rdata[i].name + '" style="width: ' + w + 'px;"><option value="1" ' + selected_1 + '>开启</option><option value="0" ' + selected_0 + '>关闭</option></select>'
                    break;
                case 1:
                    var selected_1 = (rdata[i].value == 'On') ? 'selected' : '';
                    var selected_0 = (rdata[i].value == 'Off') ? 'selected' : '';
                    ibody = '<select class="bt-input-text mr5" name="' + rdata[i].name + '" style="width: ' + w + 'px;"><option value="On" ' + selected_1 + '>开启</option><option value="Off" ' + selected_0 + '>关闭</option></select>'
                    break;
            }
            mlist += '<p><span>' + rdata[i].name + '</span>' + ibody + ', <font>' + rdata[i].ps + '</font></p>'
        }
        var con = '<style>.conf_p p{margin-bottom: 2px}</style><div class="conf_p" style="margin-bottom:0">' + mlist + '\
                        <div style="margin-top:10px; padding-right:15px" class="text-right"><button class="btn btn-success btn-sm mr5" onclick="getRedisConfig(\'' + version + '\')">刷新</button>\
                        <button class="btn btn-success btn-sm" onclick="submitConf(\'' + version + '\')">保存</button></div>\
                    </div>'
        $(".soft-man-con").html(con);
    });
}

//提交配置
function submitConf(version) {
    var data = {
        version: version,
        bind: $("input[name='bind']").val(),
        'port': $("input[name='port']").val(),
        'timeout': $("input[name='timeout']").val(),
        maxclients: $("input[name='maxclients']").val(),
        databases: $("input[name='databases']").val(),
        requirepass: $("input[name='requirepass']").val(),
        maxmemory: $("input[name='maxmemory']").val(),
    };

    redisPost('submit_redis_conf', version, data, function(ret_data){
        var rdata = $.parseJSON(ret_data.data);
        layer.msg(rdata.msg, { icon: rdata.status ? 1 : 2 });
    });
}

function keepalivedEscapeHtml(value){
    if(value === undefined || value === null) return '';
    return String(value)
        .replace(/&/g,'&amp;')
        .replace(/</g,'&lt;')
        .replace(/>/g,'&gt;')
        .replace(/"/g,'&quot;')
        .replace(/'/g,'&#39;');
}

function keepalivedParsePayload(payload){
    if(typeof payload === 'string'){
        try{
            return JSON.parse(payload);
        }catch(e){
            return null;
        }
    }
    return payload || null;
}

function keepalivedVrrpPanel(version){
    kpPost('get_vrrp_form', version, {}, function(res){
        var resData = keepalivedParsePayload(res.data);
        var formData = resData.data;
        if(!formData){
            layer.msg('解析配置失败，请稍后重试。', {icon:2});
            return;
        }
        var checked = formData.unicast_enabled ? 'checked' : '';
        var html = '<div class="bt-form">\
            <div class="line">\
                <span class="tname">网络接口</span>\
                <div class="info-r"><input class="bt-input-text" name="kp_interface" style="width:270px" value="' + keepalivedEscapeHtml(formData.interface) + '" placeholder="示例：eth0" /></div>\
            </div>\
            <div class="line">\
                <span class="tname">目标虚拟IP</span>\
                <div class="info-r"><input class="bt-input-text" name="kp_virtual_ip" style="width:270px" value="' + keepalivedEscapeHtml(formData.virtual_ipaddress) + '" placeholder="示例：192.168.1.10/24" /></div>\
            </div>\
            <div class="line">\
                <span class="tname">单播模式</span>\
                <div class="info-r">\
                    <label class="mr10"><input type="checkbox" class="keepalived-unicast-toggle" ' + checked + ' /> 启用</label>\
                </div>\
            </div>\
            <div class="line keepalived-unicast-group">\
                <span class="tname">本地IP</span>\
                <div class="info-r"><input class="bt-input-text" name="kp_unicast_src" style="width:270px" value="' + keepalivedEscapeHtml(formData.unicast_src_ip) + '" placeholder="单播源IP，示例：192.168.1.110" /></div>\
            </div>\
            <div class="line keepalived-unicast-group">\
                <span class="tname">对端IP</span>\
                <div class="info-r"><textarea name="kp_unicast_peer_list" class="bt-input-text" style="width:270px;height:96px" placeholder="每行一个对端IP，示例：192.168.1.210">' + keepalivedEscapeHtml(formData.unicast_peer_list) + '</textarea>\
                    <div class="c9" style="margin-top:5px">支持多个IP，使用换行分隔。</div>\
                </div>\
            </div>\
            <div class="line">\
                <span class="tname">优先级</span>\
                <div class="info-r"><input class="bt-input-text" name="kp_priority" style="width:270px" value="' + keepalivedEscapeHtml(formData.priority) + '" placeholder="示例：100" /></div>\
            </div>\
            <div class="line">\
                <span class="tname">连接验证码</span>\
                <div class="info-r"><input class="bt-input-text" name="kp_auth_pass" style="width:270px" value="' + keepalivedEscapeHtml(formData.auth_pass) + '" placeholder="示例：1111" /></div>\
            </div>\
            <div class="line">\
                <span class="tname"></span>\
                <div class="info-r">\
                    <button class="btn btn-sm mr10" onclick="keepalivedVrrpPanel(\'' + version + '\')">刷新</button>\
                    <button class="btn btn-success btn-sm" onclick="keepalivedSaveVrrp(\'' + version + '\')">保存</button>\
                </div>\
            </div>\
        </div>';
        $(".soft-man-con").html(html);
        keepalivedSyncUnicastState();
        $('.keepalived-unicast-toggle').change(function(){
            keepalivedSyncUnicastState();
        });
    });
}

function keepalivedSyncUnicastState(){
    var enabled = $('.keepalived-unicast-toggle').is(':checked');
    var group = $('.keepalived-unicast-group');
    group.find('input,textarea').prop('disabled', !enabled);
    if(enabled){
        group.removeClass('disabled');
    }else{
        group.addClass('disabled');
    }
}

function keepalivedSaveVrrp(version){
    var iface = $.trim($("input[name='kp_interface']").val());
    var vip = $.trim($("input[name='kp_virtual_ip']").val());
    var priority = $.trim($("input[name='kp_priority']").val());
    var authPass = $.trim($("input[name='kp_auth_pass']").val());
    var unicastEnabled = $('.keepalived-unicast-toggle').is(':checked');
    var srcIp = $.trim($("input[name='kp_unicast_src']").val());
    var peerList = $.trim($("textarea[name='kp_unicast_peer_list']").val());

    if(iface === ''){
        layer.msg('请填写网络接口名称', {icon:2});
        return;
    }
    if(vip === ''){
        layer.msg('请填写目标虚拟IP', {icon:2});
        return;
    }
    if(priority === '' || !/^[0-9]+$/.test(priority)){
        layer.msg('优先级必须为正整数', {icon:2});
        return;
    }
    if(authPass === ''){
        layer.msg('请填写连接验证码', {icon:2});
        return;
    }
    if(unicastEnabled){
        if(srcIp === ''){
            layer.msg('启用单播时需要填写本地IP', {icon:2});
            return;
        }
        if(peerList === ''){
            layer.msg('启用单播时需要至少一个对端IP', {icon:2});
            return;
        }
    }
    var postData = {
        interface: iface,
        virtual_ipaddress: vip,
        priority: priority,
        auth_pass: authPass,
        unicast_enabled: unicastEnabled ? '1' : '0',
        unicast_src_ip: srcIp,
        unicast_peer_list: peerList
    };
    kpPost('save_vrrp_form', version, postData, function(res){
        layer.msg(res.msg, {icon:1});
        setTimeout(function(){
            keepalivedVrrpPanel(version);
        }, 500);
    });
}

function keepalivedStatusPanel(version){
    kpPost('get_status_panel', version, {}, function(res){
        var resData = keepalivedParsePayload(res.data);
        var data = resData.data;
        if(!data){
            layer.msg('未能获取状态数据，请稍后重试。', {icon:2});
            return;
        }

        var serviceBadge = data.service_status === 'start'
            ? '<span class="keepalived-status-badge success">运行中</span>'
            : '<span class="keepalived-status-badge danger">未运行</span>';
        var vipBadge = data.vip_owned
            ? '<span class="keepalived-status-badge success">是</span>'
            : '<span class="keepalived-status-badge danger">否</span>';

        var vipText = data.vip ? '（' + keepalivedEscapeHtml(data.vip) + '）' : '';
        var startStopClass = data.service_status === 'start' ? 'btn-danger' : 'btn-success';
        var startStopStyle = data.service_status === 'start' ? 'background-color:#d9534f;color:#fff;' : 'background-color:#5cb85c;color:#fff;';

        var html = '<div class="keepalived-status-simple">\
            <div class="item"><span class="label-text">Keepalived 服务状态：</span>' + serviceBadge + '</div>\
            <div class="item"><span class="label-text">是否持有 VIP：</span>' + vipBadge + vipText + '</div>\
            <div class="keepalived-status-buttons">\
                <button class="btn btn-sm ' + startStopClass + '" style="' + startStopStyle + '" onclick="keepalivedServiceControl(\'' + (data.service_status === 'start' ? 'stop' : 'start') + '\', \'' + version + '\')">' + (data.service_status === 'start' ? '停止' : '启动') + '</button>\
                <button class="btn btn-default btn-sm" onclick="keepalivedServiceControl(\'restart\', \'' + version + '\')">重启</button>\
                <button class="btn btn-default btn-sm" onclick="keepalivedServiceLog()">服务日志</button>\
                <button class="btn btn-default btn-sm" onclick="keepalivedShowVipStatus(\'' + version + '\')">VIP 状态</button>\
            </div>\
        </div>';
        $(".soft-man-con").html(html);
    });
}

function keepalivedServiceControl(action, version){
    var alias = action === 'restart' ? '重启' : (action === 'stop' ? '停止' : '启动');
    var perform = function(){
        kpPost(action, version, {}, function(res){
            layer.msg(res.msg || (alias + '成功'), {icon:1});
            setTimeout(function(){
                keepalivedStatusPanel(version);
            }, 800);
        });
    };
    if(action === 'stop'){
        layer.confirm('确认要停止 Keepalived 服务吗？', {title:'确认操作',icon:0}, function(index){
            layer.close(index);
            perform();
        });
    } else {
        perform();
    }
}

function keepalivedServiceLog(){
    var logPath = '/www/server/keepalived/keepalived.log';
    var cmd = 'tail -f ' + logPath;
    execScriptAndShowLog('正在获取 Keepalived 日志...', cmd);
}

function keepalivedShowVipStatus(version){
    kpPost('get_status_panel', version, {}, function(res){
        var resData = keepalivedParsePayload(res.data);
        var data = resData.data;
        if(!data){
            layer.msg('未能获取 VIP 状态', {icon:2});
            return;
        }
        var vipBadge = data.vip_owned
            ? '<span class="keepalived-status-badge success">是</span>'
            : '<span class="keepalived-status-badge danger">否</span>';
        var content = '<div class="pd15">\
            <p>VIP：' + keepalivedEscapeHtml(data.vip || '未配置') + '</p>\
            <p>接口：' + keepalivedEscapeHtml(data.vip_interface || '-') + '</p>\
            <p>当前是否持有：' + vipBadge + '</p>\
            <p style="margin-top:10px;">检查输出：</p>\
            <pre class="status-pre" style="height:160px;overflow:auto;">' + keepalivedEscapeHtml(data.vip_check_output || '') + '</pre>\
        </div>';
        layer.open({
            type: 1,
            title: 'VIP 状态',
            area: ['460px','360px'],
            content: content
        });
    });
}
