function frpOpenMenu(el, cb){
    $('.bt-w-menu p').removeClass('bgw');
    $(el).addClass('bgw');
    if(typeof cb === 'function'){
        cb();
    }
}

function frpEscapeHtml(value){
    if(value === undefined || value === null) return '';
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function frpParsePayload(payload){
    if(typeof payload === 'string'){
        try{
            return JSON.parse(payload);
        }catch(e){
            return null;
        }
    }
    return payload || null;
}

function frpPost(method, args, callback, silent){
    var reqData = {name: 'frp', func: method};
    if(typeof args !== 'undefined' && args !== null){
        reqData.args = JSON.stringify(args);
    }
    var loadT = null;
    if(!silent){
        loadT = layer.msg('正在获取...', {icon:16, time:0, shade:0.3});
    }
    $.post('/plugins/run', reqData, function(res){
        if(loadT){ layer.close(loadT); }
        if(!res.status){
            layer.msg(res.msg || '请求失败', {icon:2});
            return;
        }
        if(typeof callback === 'function'){
            callback(res);
        }
    }, 'json').error(function(){
        if(loadT){ layer.close(loadT); }
        layer.msg('系统异常!', {icon:2});
    });
}

var frpState = {
    activeRole: '',
    currentMode: '',
    modes: null,
    templates: {
        server: [],
        client: []
    },
    editor: null,
    currentFile: '',
    currentName: '',
    currentRole: '',
    list: []
};

function frpRoleTitle(role){
    return role === 'server' ? '服务端' : '客户端';
}

function frpTplFunc(role){
    return role === 'server' ? 'frp_server_tpl' : 'frp_client_tpl';
}

function frpPathFunc(role){
    return role === 'server' ? 'frp_server' : 'frp_client';
}

function frpCurrentTemplate(role, value){
    var list = frpState.templates[role] || [];
    var html = '<option value="">请选择模板</option>';
    for(var i = 0; i < list.length; i++){
        var path = list[i];
        var selected = value === path ? ' selected' : '';
        var name = path.split('/').pop();
        html += '<option value="' + frpEscapeHtml(path) + '"' + selected + '>' + frpEscapeHtml(name) + '</option>';
    }
    return html;
}

function frpEnsureEditor(content){
    $('#frp_text_body').val(content || '');
    $('.CodeMirror').remove();
    frpState.editor = CodeMirror.fromTextArea(document.getElementById('frp_text_body'), {
        extraKeys: {
            'Ctrl-Space': 'autocomplete',
            'Ctrl-F': 'findPersistent',
            'Ctrl-H': 'replaceAll',
            'Ctrl-S': function() {
                frpSaveCurrent();
            }
        },
        lineNumbers: true,
        matchBrackets: true
    });
    frpState.editor.focus();
    $('.CodeMirror-scroll').css({'height':'340px','margin':0,'padding':0});
}

function frpRenderPanel(role){
    frpState.activeRole = role;
    var mode = frpState.modes[role + '_mode'];
    frpState.currentRole = role;
    frpState.currentMode = mode;
    var title = frpRoleTitle(role);
    var modeTips = mode === 'single'
        ? '当前为单配置文件模式，继续使用固定主配置文件。'
        : '当前为多配置文件模式，可维护多个 .ini 配置文件并按文件分别启动。';

    var html = '<div class="frp-config-wrap">\
        <div class="mb15">\
            <div style="font-size:16px;color:#333;font-weight:600;">' + title + '配置</div>\
            <div class="c9" style="margin-top:6px;">' + modeTips + '</div>\
        </div>\
        <div class="mb15">\
            <button class="btn btn-sm ' + (mode === 'single' ? 'btn-success' : 'btn-default') + '" onclick="frpSwitchMode(\'' + role + '\',\'single\')">单配置文件</button>\
            <button class="btn btn-sm ' + (mode === 'multi' ? 'btn-success' : 'btn-default') + '" style="margin-left:8px" onclick="frpSwitchMode(\'' + role + '\',\'multi\')">多配置文件</button>\
            <span class="c9" style="margin-left:12px;">单文件路径或多文件目录会保留，切换模式不会自动删除另一套文件。</span>\
        </div>\
        <div id="frp_config_content"></div>\
    </div>';
    $('.soft-man-con').html(html);
    frpLoadTemplates(role, function(){
        frpLoadConfigList(role, true);
    });
}

function frpRenderEditorArea(role, payload, selectedName, selectedContent){
    var mode = payload.mode;
    var pathText = mode === 'single' ? payload.single_path : payload.multi_dir;
    var listHtml = '';
    if(mode === 'multi'){
        listHtml += '<div style="width:220px;float:left;border:1px solid #e6e6e6;border-radius:4px;padding:12px;min-height:450px;">\
            <div style="font-weight:600;margin-bottom:10px;">配置文件列表</div>\
            <div class="mb10">\
                <button class="btn btn-default btn-sm" onclick="frpCreateConfig(\'' + role + '\')">新建</button>\
                <button class="btn btn-default btn-sm" style="margin-left:6px" onclick="frpLoadConfigList(\'' + role + '\', true)">刷新</button>\
            </div>\
            <div id="frp_file_list">';
        if(payload.items.length === 0){
            listHtml += '<div class="c9">当前没有配置文件</div>';
        } else {
            for(var i = 0; i < payload.items.length; i++){
                var item = payload.items[i];
                var active = selectedName === item.name ? 'background:#f0f9eb;border-color:#b7eb8f;' : '';
                listHtml += '<div style="padding:8px 10px;border:1px solid #eee;border-radius:4px;margin-bottom:8px;' + active + '">\
                    <div style="font-weight:600;word-break:break-all;">' + frpEscapeHtml(item.name) + '</div>\
                    <div style="margin-top:8px;">\
                        <button class="btn btn-default btn-xs" onclick="frpLoadConfigFile(\'' + role + '\',\'' + item.name + '\')">编辑</button>\
                        <button class="btn btn-danger btn-xs" style="margin-left:6px" onclick="frpDeleteConfig(\'' + role + '\',\'' + item.name + '\')">删除</button>\
                    </div>\
                </div>';
            }
        }
        listHtml += '</div></div>';
    }

    var editorWidth = mode === 'multi' ? 'calc(100% - 240px)' : '100%';
    var currentName = selectedName || (mode === 'single' ? payload.items[0].name : '');
    var editorHtml = '<div style="float:right;width:' + editorWidth + ';">\
        <div class="mb10">\
            <span class="c9">生效位置：</span><span style="word-break:break-all;">' + frpEscapeHtml(pathText) + '</span>\
        </div>\
        <div class="mb10">\
            <select id="frp_tpl_select" class="bt-input-text" style="width:220px;">' + frpCurrentTemplate(role, '') + '</select>\
            <button class="btn btn-default btn-sm" style="margin-left:8px" onclick="frpApplyTemplate(\'' + role + '\')">载入模板</button>\
            ' + (mode === 'multi' ? '<input id="frp_current_name" class="bt-input-text" style="width:180px;margin-left:8px;" value="' + frpEscapeHtml(currentName) + '" placeholder="配置文件名，例如 demo.ini" />' : '') + '\
        </div>\
        <textarea id="frp_text_body" class="bt-input-text" style="height:360px;line-height:18px;"></textarea>\
        <div class="mtb10">\
            <button id="frp_save_btn" class="btn btn-success btn-sm" onclick="frpSaveCurrent()">保存</button>\
            <button class="btn btn-default btn-sm" style="margin-left:8px" onclick="frpLoadConfigList(\'' + role + '\', true)">刷新内容</button>\
        </div>\
        <ul class="help-info-text c7 ptb15">\
            <li>单配置文件模式直接编辑固定主配置；多配置模式可维护多个 `*.ini` 文件。</li>\
            <li>模板仅用于快速填充，不会自动写入，点击保存后才会生效。</li>\
            <li>多配置模式下目录内每个配置文件都会被作为独立实例启动，请注意端口和代理名称冲突。</li>\
        </ul>\
    </div>\
    <div style="clear:both;"></div>';

    $('#frp_config_content').html(listHtml + editorHtml);
    frpEnsureEditor(selectedContent || '');
}

function frpLoadTemplates(role, callback){
    frpPost(frpTplFunc(role), {}, function(res){
        var payload = frpParsePayload(res.data) || [];
        frpState.templates[role] = payload;
        if(typeof callback === 'function'){
            callback();
        }
    }, true);
}

function frpLoadConfigPanelData(role){
    frpPost('get_config_modes', {}, function(res){
        var payload = frpParsePayload(res.data);
        if(!payload || !payload.data){
            layer.msg('未能获取模式信息', {icon:2});
            return;
        }
        frpState.modes = payload.data;
        frpRenderPanel(role);
    });
}

function frpConfigPanel(role){
    frpLoadConfigPanelData(role);
}

function frpSwitchMode(role, mode){
    frpPost('set_config_mode', {role: role, mode: mode}, function(res){
        var payload = frpParsePayload(res.data);
        if(!payload || !payload.status){
            layer.msg(payload ? payload.msg : '切换失败', {icon:2});
            return;
        }
        layer.msg(payload.msg || '切换成功', {icon:1});
        frpLoadConfigPanelData(role);
    });
}

function frpLoadConfigList(role, autoOpen, selectedName, selectedContent){
    frpPost('list_config_files', {role: role}, function(res){
        var payload = frpParsePayload(res.data);
        if(!payload || !payload.status){
            layer.msg(payload ? payload.msg : '读取失败', {icon:2});
            return;
        }
        frpState.list = payload.data.items || [];
        var targetName = selectedName || '';
        if(payload.data.mode === 'multi' && targetName === '' && payload.data.items.length > 0){
            targetName = payload.data.items[0].name;
        }
        frpRenderEditorArea(role, payload.data, targetName, selectedContent || '');
        if(payload.data.mode === 'single'){
            frpLoadConfigFile(role, '');
            return;
        }
        if(autoOpen){
            if(targetName){
                frpLoadConfigFile(role, targetName);
            } else {
                frpState.currentFile = '';
                frpState.currentName = '';
            }
        }
    });
}

function frpLoadConfigFile(role, name){
    frpPost('get_config_file', {role: role, name: name}, function(res){
        var payload = frpParsePayload(res.data);
        if(!payload || !payload.status){
            layer.msg(payload ? payload.msg : '读取失败', {icon:2});
            return;
        }
        frpState.currentRole = role;
        frpState.currentName = payload.data.name;
        frpState.currentFile = payload.data.path;
        if(payload.data.mode === 'multi'){
            frpLoadConfigList(role, false, payload.data.name, payload.data.content || '');
            return;
        }
        if($('#frp_current_name').length){
            $('#frp_current_name').val(payload.data.name);
        }
        frpEnsureEditor(payload.data.content || '');
    }, true);
}

function frpApplyTemplate(role){
    var templateFile = $('#frp_tpl_select').val();
    if(!templateFile){
        layer.msg('请选择模板', {icon:0});
        return;
    }
    frpPost('read_config_tpl', {file: templateFile}, function(res){
        var payload = frpParsePayload(res.data);
        if(!payload || !payload.status){
            layer.msg(payload ? payload.msg : '模板读取失败', {icon:2});
            return;
        }
        if(frpState.editor){
            frpState.editor.setValue(payload.data || '');
        } else {
            frpEnsureEditor(payload.data || '');
        }
    }, true);
}

function frpSaveCurrent(){
    var role = frpState.currentRole || frpState.activeRole;
    if(!role){
        layer.msg('未选择配置角色', {icon:2});
        return;
    }
    var content = frpState.editor ? frpState.editor.getValue() : $('#frp_text_body').val();
    var req = {role: role, content: content};
    if(frpState.modes[role + '_mode'] === 'multi'){
        var name = $('#frp_current_name').val();
        if(!name){
            layer.msg('请填写配置文件名', {icon:2});
            return;
        }
        req.name = name;
    }
    frpPost('save_config_file', req, function(res){
        var payload = frpParsePayload(res.data);
        if(!payload || !payload.status){
            layer.msg(payload ? payload.msg : '保存失败', {icon:2});
            return;
        }
        frpState.currentFile = payload.data.path;
        frpState.currentName = payload.data.name;
        layer.msg(payload.msg || '保存成功', {icon:1});
        if(frpState.modes[role + '_mode'] === 'multi'){
            frpLoadConfigList(role, false, payload.data.name, content);
        }
    });
}

function frpCreateConfig(role){
    var templateFile = $('#frp_tpl_select').val() || '';
    layer.prompt({
        title: '请输入新的配置文件名',
        value: 'demo.ini',
        formType: 0
    }, function(value, index){
        layer.close(index);
        frpPost('create_config_file', {role: role, name: value, template: templateFile}, function(res){
            var payload = frpParsePayload(res.data);
            if(!payload || !payload.status){
                layer.msg(payload ? payload.msg : '创建失败', {icon:2});
                return;
            }
            layer.msg(payload.msg || '创建成功', {icon:1});
            frpLoadConfigList(role, true);
            setTimeout(function(){
                frpLoadConfigFile(role, payload.data.name);
            }, 80);
        });
    });
}

function frpDeleteConfig(role, name){
    safeMessage('删除配置', '确定删除配置文件 [' + name + '] 吗？', function(){
        frpPost('delete_config_file', {role: role, name: name}, function(res){
            var payload = frpParsePayload(res.data);
            if(!payload || !payload.status){
                layer.msg(payload ? payload.msg : '删除失败', {icon:2});
                return;
            }
            layer.msg(payload.msg || '删除成功', {icon:1});
            frpLoadConfigList(role, true);
        });
    });
}

function readme(){
    var readme = '<ul class="help-info-text c7">';
    readme += '<li>支持两种模式：单配置文件模式继续使用 `frps.ini` / `frpc.ini`，多配置文件模式使用 `frps.d/*.ini` / `frpc.d/*.ini`。</li>';
    readme += '<li>服务端和客户端模式互相独立，可以单独切换，不要求保持一致。</li>';
    readme += '<li>切换模式不会自动删除另一套文件；实际启动时只按当前模式读取对应配置。</li>';
    readme += '<li>多配置模式下目录内每个 `.ini` 都会启动为独立实例，请自行检查端口、代理名和日志冲突。</li>';
    readme += '<li>请注意端口需要在防火墙自行开启或关闭。</li>';
    readme += '<li>参考文档：https://www.cnblogs.com/hahaha111122222/p/8508741.html</li>';
    readme += '</ul>';
    $('.soft-man-con').html(readme);
}
