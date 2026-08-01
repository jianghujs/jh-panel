var pfState = {
    config: null,
    editIndex: null,
    editLayer: null,
    interfaces: [],
    panelIp: '',
    dirty: false
};

function pfAppliedKey(){
    return 'jh_panel_port_forward_applied_at';
}

function pfAppliedAt(){
    return parseInt(localStorage.getItem(pfAppliedKey()) || '0', 10) || 0;
}

function pfSetAppliedAt(value){
    localStorage.setItem(pfAppliedKey(), String(value || 0));
}

function pfRefreshDirtyState(config){
    pfState.dirty = !!(config && config.updated_at && config.updated_at > pfAppliedAt());
}

function pfApplyButtonHtml(version){
    var dot = pfState.dirty ? '<span class="pf-dirty-dot"></span>' : '';
    var text = pfState.dirty ? '<span class="pf-dirty-text">有修改未应用</span>' : '';
    return '<span class="pf-apply-wrap"><button class="btn btn-success btn-sm" onclick="pfApplyRules(\'' + version + '\')">应用规则</button>' + dot + '</span>' + text;
}

function pfPost(method, version, args, callback){
    var loadT = layer.msg('正在获取...', { icon: 16, time: 0, shade: 0.3 });
    var reqData = {name: 'port_forward', func: method, version: version};
    reqData.args = JSON.stringify(pfEncodeObject(args || {}));
    $.post('/plugins/run', reqData, function(data){
        layer.close(loadT);
        if(!data.status){
            layer.msg(data.msg, {icon:0,time:2000,shade:[0.3,'#000']});
            return;
        }
        if(typeof callback === 'function') callback(data);
    }, 'json');
}

function pfEncodeObject(obj){
    var data = {};
    for(var key in obj){
        if(!obj.hasOwnProperty(key)) continue;
        data[key] = encodeURIComponent(obj[key]);
    }
    return data;
}

function pfPayload(payload){
    if(typeof payload === 'string'){
        try{return JSON.parse(payload);}catch(e){return null;}
    }
    return payload || null;
}

function pfEscape(value){
    if(value === undefined || value === null) return '';
    return String(value)
        .replace(/&/g,'&amp;')
        .replace(/</g,'&lt;')
        .replace(/>/g,'&gt;')
        .replace(/"/g,'&quot;')
        .replace(/'/g,'&#39;');
}

function pfBadge(enabled){
    return enabled ? '<span class="pf-badge on">启用</span>' : '<span class="pf-badge off">停用</span>';
}

function pfSwitchHtml(checked, onchange){
    return '<label class="pf-switch"><input type="checkbox" ' + (checked ? 'checked' : '') + ' onchange="' + onchange + '" /><span class="pf-switch-slider"></span></label>';
}

function pfLoadConfig(version, callback){
    pfPost('get_config', version, {}, function(res){
        var payload = pfPayload(res.data) || {};
        pfState.config = payload.data || {};
        if(!pfState.config.rules) pfState.config.rules = [];
        pfRefreshDirtyState(pfState.config);
        if(typeof callback === 'function') callback(pfState.config);
    });
}

function pfLoadInterfaces(version, callback){
    pfPost('get_interfaces', version, {}, function(res){
        var payload = pfPayload(res.data) || {};
        var data = payload.data || {};
        pfState.interfaces = data.items || [];
        pfState.panelIp = data.panel_ip || '';
        if(typeof callback === 'function') callback(pfState.interfaces);
    });
}

function pfSaveConfig(version, callback){
    pfPost('save_config', version, {config: JSON.stringify(pfState.config)}, function(res){
        var payload = pfPayload(res.data) || {};
        if(payload.status && payload.data){
            pfState.config = payload.data;
            pfRefreshDirtyState(pfState.config);
        }
        if(typeof callback === 'function') callback(payload);
    });
}

function pfRulesPanel(version){
    pfLoadConfig(version, function(config){
        var rows = '';
        for(var i=0;i<config.rules.length;i++){
            var item = config.rules[i];
            rows += '<tr>\
                <td>' + pfEscape(item.listen_ip) + ':' + pfEscape(item.listen_port) + '<br><span class="c9">' + pfEscape(item.listen_iface) + '</span></td>\
                <td>' + pfEscape(item.target_ip) + ':' + pfEscape(item.target_port) + '<br><span class="c9">' + pfEscape(item.target_iface) + '</span></td>\
                <td>' + pfEscape(item.remark || item.id) + '</td>\
                <td style="text-align:center;width:90px;">' + pfSwitchHtml(item.enabled, 'pfToggleRule(\'' + version + '\',' + i + ')') + '<div>' + pfBadge(item.enabled) + '</div></td>\
                <td style="text-align:right;width:190px;">\
                    <a href="javascript:pfEditRule(\'' + version + '\',' + i + ')" class="btlink">编辑</a> | \
                    <a href="javascript:pfDeleteRule(\'' + version + '\',' + i + ')" class="btlink">删除</a>\
                </td>\
            </tr>';
        }
        if(rows === '') rows = '<tr><td colspan="5" class="c9">暂无转发规则</td></tr>';
        var html = '<div class="pf-toolbar">\
                <button class="btn btn-default btn-sm" onclick="pfRulesPanel(\'' + version + '\')">刷新</button>\
                <button class="btn btn-default btn-sm" onclick="pfEditRule(\'' + version + '\', -1)">添加规则</button>\
                ' + pfApplyButtonHtml(version) + '\
            </div>\
            <div class="divtable">\
                <table class="table table-hover pf-table">\
                    <thead><tr><th>监听</th><th>目标</th><th>备注</th><th width="90">状态</th><th style="text-align:right">操作</th></tr></thead>\
                    <tbody>' + rows + '</tbody>\
                </table>\
            </div>';
        $('.soft-man-con').html(html);
    });
}

function pfBlankRule(){
    return {id:'', enabled:true, listen_ip:'', listen_iface:'', listen_port:'', target_ip:'', target_iface:'', target_port:'', remark:''};
}

function pfFirstIface(){
    for(var i=0;i<pfState.interfaces.length;i++){
        if(pfState.interfaces[i].iface !== 'lo') return pfState.interfaces[i].iface;
    }
    return pfState.interfaces.length > 0 ? pfState.interfaces[0].iface : '';
}

function pfApplyCreateDefaults(item){
    var firstIface = pfFirstIface();
    item.listen_ip = pfState.panelIp || (pfState.interfaces.length > 0 ? pfState.interfaces[0].ip : '');
    item.listen_iface = firstIface;
    item.target_iface = firstIface;
    item.enabled = true;
    return item;
}

function pfIsLoopbackIp(value){
    return /^127\./.test(String(value || ''));
}

function pfSlug(value){
    return String(value || '')
        .replace(/[^A-Za-z0-9_.-]+/g, '-')
        .replace(/^-+|-+$/g, '');
}

function pfBuildRuleId(){
    var listenPort = $.trim($('input[name="pf_listen_port"]').val());
    var targetIp = $.trim($('input[name="pf_target_ip"]').val());
    var targetPort = $.trim($('input[name="pf_target_port"]').val());
    var parts = ['pf'];
    if(listenPort) parts.push(listenPort);
    if(targetIp) parts.push('to-' + targetIp.replace(/[.:]/g, '-'));
    if(targetPort) parts.push(targetPort);
    return pfSlug(parts.join('-'));
}

function pfSyncRuleId(){
    var idInput = $('input[name="pf_id"]');
    if(idInput.attr('data-manual') === '1') return;
    idInput.val(pfBuildRuleId());
}

function pfInterfaceOptions(currentIface){
    var seen = {};
    var html = '<option value="">请选择网卡</option>';
    for(var i=0;i<pfState.interfaces.length;i++){
        var item = pfState.interfaces[i];
        if(seen[item.iface]) continue;
        seen[item.iface] = true;
        html += '<option value="' + pfEscape(item.iface) + '" ' + (item.iface === currentIface ? 'selected' : '') + '>' + pfEscape(item.iface + ' (' + item.cidr + ')') + '</option>';
    }
    if(currentIface && !seen[currentIface]){
        html += '<option value="' + pfEscape(currentIface) + '" selected>' + pfEscape(currentIface + ' (当前配置)') + '</option>';
    }
    return html;
}

function pfIpOptions(currentIp){
    var seen = {};
    var html = '<option value="">请选择IP</option>';
    html += '<option value="0.0.0.0" ' + (currentIp === '0.0.0.0' ? 'selected' : '') + '>0.0.0.0（所有IPv4）</option>';
    seen['0.0.0.0'] = true;
    for(var i=0;i<pfState.interfaces.length;i++){
        var item = pfState.interfaces[i];
        if(seen[item.ip]) continue;
        seen[item.ip] = true;
        html += '<option value="' + pfEscape(item.ip) + '" data-iface="' + pfEscape(item.iface) + '" ' + (item.ip === currentIp ? 'selected' : '') + '>' + pfEscape(item.ip + ' / ' + item.iface) + '</option>';
    }
    if(currentIp && !seen[currentIp]){
        html += '<option value="' + pfEscape(currentIp) + '" selected>' + pfEscape(currentIp + ' (当前配置)') + '</option>';
    }
    return html;
}

function pfEditRule(version, index){
    pfState.editIndex = index;
    var item = index >= 0 ? $.extend({}, pfState.config.rules[index]) : pfBlankRule();
    pfLoadInterfaces(version, function(){
        if(index < 0){
            item = pfApplyCreateDefaults(item);
        }
        var checked = item.enabled !== false ? 'checked' : '';
        pfState.editLayer = layer.open({
            type: 1,
            area: '720px',
            title: index >= 0 ? '编辑转发规则' : '添加转发规则',
            closeBtn: 1,
            shadeClose: false,
            content: '<form class="bt-form pd20 pb70 pf-form">\
                <div class="line"><span class="tname">规则ID</span><div class="info-r"><input class="bt-input-text" name="pf_id" value="' + pfEscape(item.id) + '" placeholder="自动计算，可修改" /></div></div>\
                <div class="line"><span class="tname">监听IP</span><div class="info-r"><select class="bt-input-text" name="pf_listen_ip" onchange="pfSyncListenIface()">' + pfIpOptions(item.listen_ip) + '</select></div></div>\
                <div class="line"><span class="tname">入口网卡</span><div class="info-r"><select class="bt-input-text" name="pf_listen_iface">' + pfInterfaceOptions(item.listen_iface) + '</select></div></div>\
                <div class="line"><span class="tname">监听端口</span><div class="info-r"><input class="bt-input-text" name="pf_listen_port" value="' + pfEscape(item.listen_port) + '" placeholder="2443" oninput="pfSyncRuleId()" /></div></div>\
                <div class="line"><span class="tname">目标IP</span><div class="info-r"><input class="bt-input-text" name="pf_target_ip" value="' + pfEscape(item.target_ip) + '" placeholder="192.168.222.1" oninput="pfSyncRuleId()" /></div></div>\
                <div class="line"><span class="tname">出口网卡</span><div class="info-r"><select class="bt-input-text" name="pf_target_iface">' + pfInterfaceOptions(item.target_iface) + '</select></div></div>\
                <div class="line"><span class="tname">目标端口</span><div class="info-r"><input class="bt-input-text" name="pf_target_port" value="' + pfEscape(item.target_port) + '" placeholder="443" oninput="pfSyncRuleId()" /></div></div>\
                <div class="line"><span class="tname">启用</span><div class="info-r">' + pfSwitchHtml(item.enabled !== false, '') + '<span style="margin-left:8px">启用此规则</span></div></div>\
                <div class="line"><span class="tname">备注</span><div class="info-r"><textarea class="bt-input-text" name="pf_remark" placeholder="用途说明">' + pfEscape(item.remark) + '</textarea></div></div>\
                <div class="bt-form-submit-btn">\
                    <button type="button" class="btn btn-danger btn-sm btn-title" onclick="layer.close(pfState.editLayer)">取消</button>\
                    <button type="button" class="btn btn-success btn-sm btn-title" onclick="pfSubmitRule(\'' + version + '\')">保存</button>\
                </div>\
            </form>'
        });
        var idInput = $('input[name="pf_id"]');
        idInput.attr('data-original', item.id || '');
        idInput.attr('data-manual', '0');
        idInput.on('input', function(){
            $(this).attr('data-manual', '1');
        });
        pfSyncRuleId();
    });
}

function pfSyncListenIface(){
    var iface = $('select[name="pf_listen_ip"] option:selected').attr('data-iface');
    if(iface){
        $('select[name="pf_listen_iface"]').val(iface);
    }
}

function pfSubmitRule(version){
    var item = {
        id: $.trim($('input[name="pf_id"]').val()),
        enabled: $('.pf-form .pf-switch input').is(':checked'),
        listen_ip: $.trim($('select[name="pf_listen_ip"]').val()),
        listen_iface: $.trim($('select[name="pf_listen_iface"]').val()),
        listen_port: $.trim($('input[name="pf_listen_port"]').val()),
        target_ip: $.trim($('input[name="pf_target_ip"]').val()),
        target_iface: $.trim($('select[name="pf_target_iface"]').val()),
        target_port: $.trim($('input[name="pf_target_port"]').val()),
        remark: $.trim($('textarea[name="pf_remark"]').val())
    };
    if(item.id === '') item.id = 'rule-' + (new Date().getTime());
    var oldItem = pfState.editIndex >= 0 ? $.extend({}, pfState.config.rules[pfState.editIndex]) : null;
    var saveItem = function(){
        if(pfState.editIndex >= 0){
            pfState.config.rules[pfState.editIndex] = item;
        }else{
            pfState.config.rules.push(item);
        }
        pfSaveConfig(version, function(payload){
            layer.msg(payload.msg || '保存成功', {icon: payload.status ? 1 : 2});
            if(payload.status){
                layer.close(pfState.editLayer);
                pfRulesPanel(version);
            }
        });
    };
    if(oldItem){
        pfPost('delete_rule', version, {rule: JSON.stringify(oldItem)}, function(){
            saveItem();
        });
        return;
    }
    saveItem();
}

function pfToggleRule(version, index){
    var item = pfState.config.rules[index];
    var nextEnabled = !item.enabled;
    if(!nextEnabled){
        pfPost('delete_rule', version, {rule: JSON.stringify(item)}, function(){
            pfState.config.rules[index].enabled = false;
            pfSaveConfig(version, function(payload){
                layer.msg(payload.msg || '已停用并清理运行规则', {icon: payload.status ? 1 : 2});
                pfRulesPanel(version);
            });
        });
        return;
    }
    pfState.config.rules[index].enabled = true;
    pfSaveConfig(version, function(payload){
        layer.msg('已启用配置，请点击“应用规则”使其生效', {icon: payload.status ? 1 : 2, time: 2500});
        pfRulesPanel(version);
    });
}

function pfDeleteRule(version, index){
    var item = pfState.config.rules[index];
    safeMessage('确认删除转发规则', '删除后会同步清理对应的运行规则。确认删除 [' + pfEscape(item.id) + ']？', function(){
        pfPost('delete_rule', version, {rule: JSON.stringify(item)}, function(){
            pfState.config.rules.splice(index, 1);
            pfSaveConfig(version, function(payload){
                layer.msg(payload.msg || '删除成功', {icon: payload.status ? 1 : 2});
                pfRulesPanel(version);
            });
        });
    });
}

function pfApplyRules(version){
    safeMessage('确认应用端口转发', '将开启IPv4转发并写入iptables NAT/FORWARD规则，请确认当前规则配置无误。', function(){
        pfPost('apply_rules', version, {}, function(res){
            var payload = pfPayload(res.data) || {};
            var data = payload.data || {};
            var persist = data.persistence || {};
            if(payload.status && pfState.config && pfState.config.updated_at){
                pfSetAppliedAt(pfState.config.updated_at);
                pfState.dirty = false;
            }
            layer.msg((payload.msg || '应用成功') + '，持久化：' + (persist.method || '-') + ' ' + (persist.msg || ''), {icon: payload.status ? 1 : 2, time: 3500});
            pfRulesPanel(version);
        });
    });
}

function pfLogsPanel(version){
    pfPost('get_logs', version, {}, function(res){
        var payload = pfPayload(res.data) || {};
        $('.soft-man-con').html('<div class="pf-toolbar"><button class="btn btn-default btn-sm" onclick="pfLogsPanel(\'' + version + '\')">刷新</button></div><pre class="pf-pre">' + pfEscape(payload.data || '') + '</pre>');
    });
}
