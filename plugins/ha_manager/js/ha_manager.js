function haPost(method, version, args, callback){
    var loadT = layer.msg('正在获取...', { icon: 16, time: 0, shade: 0.3 });
    var req_data = {};
    req_data['name'] = 'ha_manager';
    req_data['func'] = method;
    req_data['version'] = version;
    if (typeof(args) === 'string'){
        req_data['args'] = JSON.stringify(toArrayObject(args));
    } else {
        req_data['args'] = JSON.stringify(args || {});
    }
    $.post('/plugins/run', req_data, function(data){
        layer.close(loadT);
        if (!data.status){
            layer.msg(data.msg,{icon:0,time:2000,shade:[0.3,'#000']});
            return;
        }
        if (typeof(callback) === 'function'){
            callback(data);
        }
    }, 'json');
}

function haParsePayload(payload){
    if(typeof payload === 'string'){
        try{
            return JSON.parse(payload);
        }catch(e){
            return null;
        }
    }
    return payload || null;
}

function haEscapeHtml(value){
    if(value === undefined || value === null) return '';
    return String(value)
        .replace(/&/g,'&amp;')
        .replace(/</g,'&lt;')
        .replace(/>/g,'&gt;')
        .replace(/"/g,'&quot;')
        .replace(/'/g,'&#39;');
}

function haBadge(status, text){
    return '<span class="ha-badge ' + status + '">' + text + '</span>';
}

function haManagerConfigPanel(version){
    haPost('get_config', version, {}, function(res){
        var payload = haParsePayload(res.data) || {};
        var data = payload.data || {};
        var html = '<div class="bt-form ha-form">\
            <div class="line">\
                <span class="tname">关系 ID</span>\
                <div class="info-r"><input class="bt-input-text" name="relation_id" value="' + haEscapeHtml(data.relation_id || '') + '" placeholder="例如：prod-db-ha-001" /></div>\
            </div>\
            <div class="line">\
                <span class="tname">对端 IP</span>\
                <div class="info-r"><input class="bt-input-text" name="peer_ip" value="' + haEscapeHtml(data.peer_ip || '') + '" placeholder="例如：1.2.3.4" /></div>\
            </div>\
            <div class="line">\
                <span class="tname">SSH 用户</span>\
                <div class="info-r"><input class="bt-input-text" name="ssh_user" value="' + haEscapeHtml(data.ssh_user || 'root') + '" placeholder="root" /></div>\
            </div>\
            <div class="line">\
                <span class="tname">SSH 端口</span>\
                <div class="info-r"><input class="bt-input-text" name="ssh_port" value="' + haEscapeHtml(data.ssh_port || 22) + '" placeholder="22" /></div>\
            </div>\
            <div class="line">\
                <span class="tname">配置角色</span>\
                <div class="info-r"><select class="bt-input-text" name="configured_role"><option value="">请选择</option><option value="primary" ' + (data.configured_role === 'primary' ? 'selected' : '') + '>primary</option><option value="standby" ' + (data.configured_role === 'standby' ? 'selected' : '') + '>standby</option></select></div>\
            </div>\
            <div class="line">\
                <span class="tname">本机公钥</span>\
                <div class="info-r"><textarea readonly name="public_key" class="ha-pre" placeholder="尚未生成"></textarea></div>\
            </div>\
            <div class="line">\
                <span class="tname">对端公钥</span>\
                <div class="info-r"><textarea class="bt-input-text" name="peer_ssh_public_key" style="width:420px;height:110px;" placeholder="粘贴对端公钥">' + haEscapeHtml(data.peer_ssh_public_key || '') + '</textarea></div>\
            </div>\
            <div class="line ha-actions">\
                <span class="tname"></span>\
                <div class="info-r">\
                    <button class="btn btn-default btn-sm" onclick="haManagerConfigPanel(\'' + version + '\')">刷新</button>\
                    <button class="btn btn-success btn-sm" onclick="haManagerSaveConfig(\'' + version + '\')">保存配置</button>\
                    <button class="btn btn-default btn-sm" onclick="haManagerLoadPublicKey(\'' + version + '\')">刷新公钥</button>\
                    <button class="btn btn-default btn-sm" onclick="haManagerTestPeer(\'' + version + '\')">测试连接</button>\
                </div>\
            </div>\
        </div>';
        $('.soft-man-con').html(html);
        haManagerLoadPublicKey(version);
    });
}

function haManagerLoadPublicKey(version){
    haPost('get_local_public_key', version, {}, function(res){
        var payload = haParsePayload(res.data) || {};
        var data = payload.data || {};
        $('textarea[name="public_key"]').val(data.public_key || '');
    });
}

function haManagerSaveConfig(version){
    var data = {
        relation_id: $.trim($('input[name="relation_id"]').val()),
        peer_ip: $.trim($('input[name="peer_ip"]').val()),
        ssh_user: $.trim($('input[name="ssh_user"]').val()),
        ssh_port: $.trim($('input[name="ssh_port"]').val()),
        configured_role: $('select[name="configured_role"]').val(),
        peer_ssh_public_key: $.trim($('textarea[name="peer_ssh_public_key"]').val())
    };
    haPost('save_config', version, data, function(res){
        layer.msg(res.msg || '保存成功', {icon:1});
        haManagerConfigPanel(version);
    });
}

function haManagerTestPeer(version){
    haPost('test_peer', version, {}, function(res){
        var payload = haParsePayload(res.data) || {};
        layer.msg(payload.msg || '测试完成', {icon:1});
        haManagerStatusPanel(version);
    });
}

function haManagerStatusPanel(version){
    haPost('get_status', version, {}, function(res){
        var payload = haParsePayload(res.data) || {};
        var data = payload.data || {};
        var peer = data.peer || {};
        var checks = data.checks || {};
        var html = '<div class="ha-status-card">\
            <div class="item"><span class="label">关系 ID</span>' + haEscapeHtml(data.relation_id || '-') + '</div>\
            <div class="item"><span class="label">本机 IP</span>' + haEscapeHtml(data.local_ip || '-') + '</div>\
            <div class="item"><span class="label">配置角色</span>' + haEscapeHtml(data.configured_role || '-') + '</div>\
            <div class="item"><span class="label">实际角色</span>' + haEscapeHtml(data.actual_role || '-') + '</div>\
            <div class="item"><span class="label">切换状态</span>' + haEscapeHtml(data.switch_state || '-') + '</div>\
            <div class="item"><span class="label">汇总状态</span>' + haBadge(data.summary_status || 'warning', data.summary_status || 'warning') + '</div>\
            <div class="item"><span class="label">汇总说明</span>' + haEscapeHtml(data.summary_msg || '-') + '</div>\
            <div class="item"><span class="label">连接状态</span>' + haBadge(data.connection_status || 'pending', data.connection_status || 'pending') + '</div>\
            <div class="item"><span class="label">对端结果</span>' + haEscapeHtml(peer.reason || peer.status || '-') + '</div>\
            <div class="item"><span class="label">对端详情</span>' + haEscapeHtml(peer.detail || '-') + '</div>\
            <div class="item"><span class="label">MySQL</span>' + haEscapeHtml((checks.mysql && checks.mysql.reason) || (checks.mysql && checks.mysql.detail) || '-') + '</div>\
            <div class="ha-actions">\
                <button class="btn btn-default btn-sm" onclick="haManagerStatusPanel(\'' + version + '\')">刷新</button>\
                <button class="btn btn-default btn-sm" onclick="haManagerSelfCheckPanel(\'' + version + '\')">查看自检</button>\
            </div>\
        </div>';
        $('.soft-man-con').html(html);
    });
}

function haManagerSelfCheckPanel(version){
    haPost('self_check', version, {}, function(res){
        var payload = haParsePayload(res.data) || {};
        var data = payload.data || {};
        var checks = data.checks || {};
        var html = '<div class="ha-status-card">\
            <div class="item"><span class="label">汇总状态</span>' + haBadge(data.summary_status || 'warning', data.summary_status || 'warning') + '</div>\
            <div class="item"><span class="label">汇总说明</span>' + haEscapeHtml(data.summary_msg || '-') + '</div>\
            <div class="item"><span class="label">角色检查</span>' + haEscapeHtml((checks.role && checks.role.reason) || (checks.role && checks.role.detail) || '-') + '</div>\
            <div class="item"><span class="label">MySQL 检查</span>' + haEscapeHtml((checks.mysql && checks.mysql.reason) || (checks.mysql && checks.mysql.detail) || '-') + '</div>\
            <div class="item"><span class="label">配置检查</span>' + haEscapeHtml((checks.config && checks.config.reason) || (checks.config && checks.config.detail) || '-') + '</div>\
            <div class="item"><span class="label">切换检查</span>' + haEscapeHtml((checks.switching && checks.switching.reason) || (checks.switching && checks.switching.detail) || '-') + '</div>\
            <div class="ha-actions">\
                <button class="btn btn-default btn-sm" onclick="haManagerSelfCheckPanel(\'' + version + '\')">刷新</button>\
                <button class="btn btn-default btn-sm" onclick="haManagerStatusPanel(\'' + version + '\')">查看连接状态</button>\
            </div>\
        </div>';
        $('.soft-man-con').html(html);
    });
}
