function wgPost(method, version, args, callback){
    var loadT = layer.msg('正在获取...', { icon: 16, time: 0, shade: 0.3 });
    var req_data = {};
    req_data['name'] = 'wireguard';
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
            layer.msg(data.msg, {icon:0,time:2000,shade:[0.3,'#000']});
            return;
        }
        if (typeof(callback) === 'function'){
            callback(data);
        }
    }, 'json');
}

function wireguardParsePayload(payload){
    if (typeof payload === 'string'){
        try{
            return JSON.parse(payload);
        }catch(e){
            return null;
        }
    }
    return payload || null;
}

function wireguardEscapeHtml(value){
    if(value === undefined || value === null) return '';
    return String(value)
        .replace(/&/g,'&amp;')
        .replace(/</g,'&lt;')
        .replace(/>/g,'&gt;')
        .replace(/"/g,'&quot;')
        .replace(/'/g,'&#39;');
}

function wireguardStatusPanel(version){
    wgPost('get_status_info', version, {}, function(res){
        var payload = wireguardParsePayload(res.data) || {};
        var data = payload.data || {};
        var installed = data.installed;
        var badge = installed ? '<span class="wg-status-badge success">已安装</span>' : '<span class="wg-status-badge danger">未安装</span>';
        var svc = data.service_active ? '<span class="wg-status-badge success">运行中</span>' : '<span class="wg-status-badge danger">未运行</span>';
        var iface = data.interface || 'wg0';
        var ifaceBadge = data.interface_up ? '<span class="wg-status-badge success">已启用</span>' : '<span class="wg-status-badge danger">未启用</span>';

        var html = '<div class="wg-status-card">\
            <div class="item"><span class="label">安装状态</span>' + badge + '</div>\
            <div class="item"><span class="label">wg 版本</span>' + wireguardEscapeHtml(data.wg_version || '-') + '</div>\
            <div class="item"><span class="label">接口</span>' + wireguardEscapeHtml(iface) + ifaceBadge + '</div>\
            <div class="item"><span class="label">服务状态</span>' + svc + '</div>\
            <div class="item"><span class="label">配置文件</span>' + wireguardEscapeHtml(data.config_path || '-') + '</div>\
            <div class="wg-status-actions">';
        if (!installed){
            html += '<button class="btn btn-success btn-sm" onclick="wireguardInstall(\'' + version + '\')">一键安装</button>';
        } else {
            html += '<button class="btn btn-danger btn-sm" onclick="wireguardUninstall(\'' + version + '\')">卸载标记</button>';
        }
        html += '<button class="btn btn-default btn-sm" onclick="wireguardStatusPanel(\'' + version + '\')">刷新</button></div>\
            <ul class="help-info-text c7" style="margin-top:10px;">\
                <li>安装完成后请在“密钥初始化”中生成密钥。</li>\
                <li>点对点向导可自动生成 wg0 配置并应用。</li>\
            </ul>\
        </div>';
        $('.soft-man-con').html(html);
    });
}

function wireguardInstall(version){
    layer.confirm('确认安装 WireGuard 组件？', {icon:3, title:'安装确认'}, function(index){
        layer.close(index);
        wgPost('install_wireguard', version, {}, function(res){
            var payload = wireguardParsePayload(res.data) || {};
            var ok = payload.status !== false;
            var msg = payload.msg || res.msg || '完成';
            layer.msg(msg, {icon: ok ? 1 : 2});
            wireguardStatusPanel(version);
        });
    });
}

function wireguardUninstall(version){
    layer.confirm('确认卸载插件标记？系统 WireGuard 组件将保留。', {icon:3, title:'卸载确认'}, function(index){
        layer.close(index);
        wgPost('uninstall_wireguard', version, {}, function(res){
            var payload = wireguardParsePayload(res.data) || {};
            var ok = payload.status !== false;
            var msg = payload.msg || res.msg || '完成';
            layer.msg(msg, {icon: ok ? 1 : 2});
            wireguardStatusPanel(version);
        });
    });
}

var wgHasPrivateKey = false;

function wireguardKeyPanel(version){
    var html = '<div class="bt-form">\
        <div class="line">\
            <span class="tname">公钥</span>\
            <div class="info-r wg-key-area"><textarea readonly name="wg_public_key" placeholder="尚未生成"></textarea></div>\
        </div>\
        <div class="line">\
            <span class="tname">私钥</span>\
            <div class="info-r wg-key-area"><textarea readonly name="wg_private_key" placeholder="尚未生成"></textarea></div>\
        </div>\
        <div class="line">\
            <span class="tname">操作</span>\
            <div class="info-r">\
                <button class="btn btn-success btn-sm" id="wg_key_action" onclick="wireguardGenerateKey(\'' + version + '\')">生成密钥</button>\
                <button class="btn btn-default btn-sm" onclick="wireguardLoadKey(\'' + version + '\')">刷新</button>\
            </div>\
        </div>\
    </div>';
    $('.soft-man-con').html(html);
    wireguardLoadKey(version);
}

function wireguardLoadKey(version){
    wgPost('get_key_info', version, {}, function(res){
        var payload = wireguardParsePayload(res.data) || {};
        var data = payload.data || {};
        $('textarea[name="wg_public_key"]').val(data.public_key || '');
        $('textarea[name="wg_private_key"]').val(data.private_key || '');
        wgHasPrivateKey = !!data.has_private;
        $('#wg_key_action').text(wgHasPrivateKey ? '重新生成' : '生成密钥');
    });
}

function wireguardGenerateKey(version){
    if (wgHasPrivateKey){
        layer.confirm('重新生成将覆盖现有私钥，可能导致现有配置失效，是否继续？', {icon:3, title:'确认重新生成'}, function(index){
            layer.close(index);
            wireguardDoGenerateKey(version);
        });
        return;
    }
    wireguardDoGenerateKey(version);
}

function wireguardDoGenerateKey(version){
    wgPost('generate_keypair', version, {}, function(res){
        var payload = wireguardParsePayload(res.data) || {};
        layer.msg(payload.msg || '生成完成', {icon: payload.status ? 1 : 2});
        wireguardLoadKey(version);
    });
}

function wireguardConfigPanel(version){
    var header = '<div class="mb15">\
        <button class="btn btn-success btn-sm" onclick="wireguardNewConfigModal(\'' + version + '\')">新增配置</button>\
        <button class="btn btn-warning btn-sm" onclick="wireguardP2PWizardModal(\'' + version + '\')">点对点配置向导</button>\
        <button class="btn btn-default btn-sm" onclick="wireguardConfigPanel(\'' + version + '\')">刷新</button>\
    </div>';
    wgPost('list_configs', version, {}, function(res){
        var payload = wireguardParsePayload(res.data) || {};
        var list = payload.data || [];
        var table = '<div class="divtable wg-config-table"><table class="table table-hover table-bordered">\
            <thead><tr><th>接口</th><th>地址</th><th>端口</th><th>Peer数</th><th>握手</th><th>状态</th><th width="210">操作</th></tr></thead><tbody>';
        if (!list.length){
            table += '<tr><td colspan="7" style="text-align:center;">暂无配置</td></tr>';
        } else {
            for (var i=0;i<list.length;i++){
                var item = list[i];
                var state = item.interface_up ? '<span class="wg-status-badge success">已启用</span>' : '<span class="wg-status-badge danger">未启用</span>';
                table += '<tr>\
                    <td>' + wireguardEscapeHtml(item.name) + '</td>\
                    <td>' + wireguardEscapeHtml(item.address || '-') + '</td>\
                    <td>' + wireguardEscapeHtml(item.listen_port || '-') + '</td>\
                    <td>' + wireguardEscapeHtml(item.peer_count || 0) + '</td>\
                    <td>' + wireguardEscapeHtml(item.last_handshake || '-') + '</td>\
                    <td>' + state + '</td>\
                    <td>\
                        <button class="btn btn-default btn-xs" onclick="wireguardEditConfig(\'' + version + '\',\'' + item.name + '\')">编辑</button>\
                        <button class="btn btn-default btn-xs" onclick="wireguardApplyConfig(\'' + version + '\',\'' + item.name + '\')">应用</button>\
                        <button class="btn btn-danger btn-xs" onclick="wireguardDeleteConfig(\'' + version + '\',\'' + item.name + '\')">删除</button>\
                    </td>\
                </tr>';
            }
        }
        table += '</tbody></table></div>';
        $('.soft-man-con').html(header + table);
    });
}

function wireguardBuildTemplate(iface, defaults, keyInfo){
    var address = defaults.address || '10.0.0.1/24';
    var listenPort = defaults.listen_port || '51820';
    var privateKey = (keyInfo && keyInfo.private_key) ? keyInfo.private_key : '<PRIVATE_KEY>';
    var allowedIps = '10.0.0.1/32,10.0.0.2/32,10.0.0.100/32';
    var peerEndpoint = '<PEER_IP>:' + listenPort;
    var lines = [
        '[Interface]',
        'PrivateKey = ' + privateKey,
        'Address = ' + address,
        'ListenPort = ' + listenPort,
        '',
        'PostUp = sysctl -w net.ipv4.ip_forward=1',
        'PostUp = iptables -A FORWARD -i ' + iface + ' -j ACCEPT',
        'PostUp = iptables -A FORWARD -o ' + iface + ' -j ACCEPT',
        'PostDown = iptables -D FORWARD -i ' + iface + ' -j ACCEPT',
        'PostDown = iptables -D FORWARD -o ' + iface + ' -j ACCEPT',
        '',
        '[Peer]',
        'PublicKey = <PEER_PUBLIC_KEY>',
        'AllowedIPs = ' + allowedIps,
        'Endpoint = ' + peerEndpoint,
        'PersistentKeepalive = 25'
    ];
    return lines.join('\n') + '\n';
}

function wireguardNewConfigModal(version){
    wgPost('get_wizard_defaults', version, {}, function(res){
        var payload = wireguardParsePayload(res.data) || {};
        var defaults = payload.data || {};
        wgPost('get_key_info', version, {}, function(resKey){
            var keyPayload = wireguardParsePayload(resKey.data) || {};
            var keyInfo = keyPayload.data || {};
            var iface = defaults.interface || 'wg0';
            var template = wireguardBuildTemplate(iface, defaults, keyInfo);
            var html = '<div class="bt-form pd20">\
                <div class="line"><span class="tname">接口名</span><div class="info-r"><input class="bt-input-text" name="wg_tpl_iface" style="width:220px" value="' + wireguardEscapeHtml(iface) + '" /></div></div>\
                <div class="line"><span class="tname">配置内容</span><div class="info-r"><textarea class="bt-input-text" name="wg_tpl_content" style="width:100%;height:280px">' + wireguardEscapeHtml(template) + '</textarea></div></div>\
            </div>';
            layer.open({
                title: '新增 WireGuard 配置',
                area: ['760px','520px'],
                content: html,
                btn: ['保存','取消'],
                yes: function(index){
                    var name = $('input[name="wg_tpl_iface"]').val();
                    var content = $('textarea[name="wg_tpl_content"]').val();
                    if (!name){
                        layer.msg('接口名不能为空', {icon:2});
                        return;
                    }
                    wgPost('save_config', version, {name: name, content: content}, function(resSave){
                        var payloadSave = wireguardParsePayload(resSave.data) || {};
                        layer.msg(payloadSave.msg || '保存完成', {icon: payloadSave.status ? 1 : 2});
                        if (payloadSave.status){
                            layer.close(index);
                            wireguardConfigPanel(version);
                        }
                    });
                }
            });
        });
    });
}

function wireguardEditConfig(version, name){
    wgPost('get_config', version, {name: name}, function(res){
        var payload = wireguardParsePayload(res.data) || {};
        var content = payload.data || '';
        var html = '<div style="padding:10px;">\
            <textarea class="bt-input-text" name="wg_edit_content" style="width:100%;height:280px">' + wireguardEscapeHtml(content) + '</textarea>\
        </div>';
        layer.open({
            title: '编辑配置 - ' + name,
            area: ['720px','420px'],
            content: html,
            btn: ['保存','取消'],
            yes: function(index){
                var newContent = $('textarea[name="wg_edit_content"]').val();
                wgPost('save_config', version, {name: name, content: newContent}, function(res){
                    var payload = wireguardParsePayload(res.data) || {};
                    layer.msg(payload.msg || '保存完成', {icon: payload.status ? 1 : 2});
                    if (payload.status){
                        layer.close(index);
                        wireguardConfigPanel(version);
                    }
                });
            }
        });
    });
}

function wireguardApplyConfig(version, name){
    wgPost('apply_config', version, {name: name}, function(res){
        var payload = wireguardParsePayload(res.data) || {};
        layer.msg(payload.msg || '完成', {icon: payload.status ? 1 : 2});
        wireguardConfigPanel(version);
    });
}

function wireguardDeleteConfig(version, name){
    layer.confirm('确认删除配置 ' + name + ' ?', {icon:3, title:'删除确认'}, function(index){
        layer.close(index);
        wgPost('delete_config', version, {name: name}, function(res){
            var payload = wireguardParsePayload(res.data) || {};
            layer.msg(payload.msg || '删除完成', {icon: payload.status ? 1 : 2});
            wireguardConfigPanel(version);
        });
    });
}

function wireguardP2PWizardModal(version){
    var html = '<div class="bt-form pd20">\
        <div class="line"><span class="tname">接口名</span><div class="info-r"><input class="bt-input-text" name="wg_w_iface" style="width:220px" value="wg0" /></div></div>\
        <div class="line"><span class="tname">IP段</span><div class="info-r"><input class="bt-input-text" name="wg_w_address" style="width:220px" value="10.0.0.1/24" /></div></div>\
        <div class="line"><span class="tname">对端公网IP</span><div class="info-r"><input class="bt-input-text" name="wg_w_peer_host" style="width:220px" placeholder="必填" /></div></div>\
        <div class="line"><span class="tname">对端端口</span><div class="info-r"><input class="bt-input-text" name="wg_w_peer_port" style="width:220px" value="51820" /></div></div>\
        <div class="line"><span class="tname">对端公钥</span><div class="info-r">\
            <textarea class="bt-input-text" name="wg_w_peer_pub" style="width:360px;height:70px"></textarea>\
            <div style="margin-top:6px;">\
                <button type="button" class="btn btn-default btn-xs" onclick="return wireguardCopyLocalPublicKey(\'' + version + '\')">复制本机公钥</button>\
                <span style="margin-left:8px;color:#888;font-size:12px;">可在对端执行：wg show 或 cat /etc/wireguard/publickey 获取</span>\
            </div>\
        </div></div>\
        <div class="line"><span class="tname">AllowedIPs</span><div class="info-r"><input class="bt-input-text" name="wg_w_allowed" style="width:360px" value="10.0.0.1/32,10.0.0.2/32,10.0.0.100/32" /></div></div>\
        <div class="line"><span class="tname">Keepalive</span><div class="info-r"><input class="bt-input-text" name="wg_w_keepalive" style="width:220px" value="25" /></div></div>\
        <div class="line"><span class="tname">选项</span><div class="info-r">\
            <label class="mr10"><input type="checkbox" name="wg_w_forward" checked /> 启用转发规则</label>\
            <label><input type="checkbox" name="wg_w_autokey" checked /> 无私钥则自动生成</label>\
        </div></div>\
    </div>';
    layer.open({
        type: 1,
        title: '点对点配置向导',
        area: ['700px','520px'],
        content: html,
        btn: ['保存','取消'],
        yes: function(index){
            var iface = $('input[name="wg_w_iface"]').val();
            var address = $('input[name="wg_w_address"]').val();
            var peerHost = $('input[name="wg_w_peer_host"]').val();
            var peerPort = $.trim($('input[name="wg_w_peer_port"]').val());
            var peerPub = $('textarea[name="wg_w_peer_pub"]').val();
            var allowed = $('input[name="wg_w_allowed"]').val();
            var keepalive = $('input[name="wg_w_keepalive"]').val();
            if (!peerHost){
                layer.msg('对端公网IP不能为空', {icon:2});
                return;
            }
            if (!peerPort){
                layer.msg('对端端口不能为空', {icon:2});
                return;
            }
            if (!peerPub){
                layer.msg('对端公钥不能为空', {icon:2});
                return;
            }
            var endpoint = peerHost + ':' + peerPort;
            var data = {
                iface: iface,
                address: address,
                listen_port: peerPort,
                peer_public_key: peerPub,
                peer_allowed_ips: allowed,
                peer_endpoint: endpoint,
                peer_keepalive: keepalive,
                enable_forward: $('input[name="wg_w_forward"]').prop('checked') ? 1 : 0,
                auto_gen_key: $('input[name="wg_w_autokey"]').prop('checked') ? 1 : 0
            };
            wgPost('create_config', version, data, function(res){
                var payload = wireguardParsePayload(res.data) || {};
                showMsg(payload.msg || '完成', null, {icon: payload.status ? 1 : 2});
                if (payload.status){
                    layer.close(index);
                    wireguardConfigPanel(version);
                }
            });
        }
    });
}

function wireguardCopyLocalPublicKey(version){
    wgPost('get_key_info', version, {}, function(res){
        var payload = wireguardParsePayload(res.data) || {};
        var data = payload.data || {};
        var key = data.public_key || '';
        if (!key){
            layer.msg('本机公钥为空，请先生成密钥', {icon:2});
            return;
        }
        var $temp = $('<textarea>');
        $('body').append($temp);
        $temp.val(key).select();
        try{
            document.execCommand('copy');
            layer.msg('已复制本机公钥', {icon:1});
        }catch(e){
            layer.msg('复制失败，请手动复制', {icon:2});
        }
        $temp.remove();
    });
    return false;
}
