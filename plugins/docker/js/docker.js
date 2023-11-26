var composeFileListData = [];
var importProjectLayer = [];
let codeMirror = null;

function dPostOrgin(args, callback) {
    $.post('/plugins/run', args, function(data) {
        callback(data);
    }, 'json');
}

function dPost(method, version, args, callback) {
    return new Promise((resolve) => {
            
        var loadT = layer.msg('正在获取...', { icon: 16, time: 0, shade: 0.3 });

        var req_data = {};
        req_data['name'] = 'docker';
        req_data['func'] = method;
        req_data['version'] = version;

        if (typeof(args) == 'string') {
            req_data['args'] = JSON.stringify(toArrayObject(args));
        } else {
            req_data['args'] = JSON.stringify(args);
        }

        dPostOrgin(req_data, function(data) {
            layer.close(loadT);
            if (!data.status) {
                //错误展示10S
                layer.msg(data.msg, { icon: 0, time: 2000, shade: [10, '#000'] });
                return;
            }

            if (typeof(callback) == 'function') {
                callback(data);
            }
            resolve(data);
        });
    })
}

function dPostCallbak(method, version, args, callback) {
    var loadT = layer.msg('正在获取...', { icon: 16, time: 0, shade: 0.3 });

    var req_data = {};
    req_data['name'] = 'docker';
    req_data['func'] = method;
    args['version'] = version;

    if (typeof(args) == 'string') {
        req_data['args'] = JSON.stringify(toArrayObject(args));
    } else {
        req_data['args'] = JSON.stringify(args);
    }

    $.post('/plugins/callback', req_data, function(data) {
        layer.close(loadT);
        if (!data.status) {
            layer.msg(data.msg, { icon: 0, time: 2000, shade: [0.3, '#000'] });
            return;
        }

        if (typeof(callback) == 'function') {
            callback(data);
        }
    }, 'json');
}


function logsCon(id) {
    dPost('docker_con_log', '', { Hostname: id }, function(rdata) {
        var rdata = $.parseJSON(rdata.data);
        if (!rdata.status) {
            layer.msg(rdata.msg, { icon: 2 });
            return;
        };
        layer.open({
            type: 1,
            title: 'Docker日志',
            area: '600px',
            closeBtn: 2,
            content: '<div class="bt-form">' +
                '<pre class="crontab-log" style="overflow: auto; \
                    border: 0px none; line-height:23px;padding: 15px; \
                    margin: 0px; white-space: pre-wrap; height: 405px; \
                    background-color: rgb(51,51,51);color:#f1f1f1;\
                    border-radius:0px;">' + (rdata.msg == '' ? 'No logs' : rdata.msg) + '</pre>' +
                '</div>',
            success: function(index, layers) {
                $(".crontab-log").scrollTop(1000000);
            }
        });
    });
}

function deleteCon(Hostname) {
    // 删除容器
    safeMessage('删除容器 ', '删除容器 [' + Hostname + '], 确定?', function() {
        dPost('docker_remove_con', '', { Hostname: Hostname }, function(rdata) {
            var rdata = $.parseJSON(rdata.data);
            showMsg(rdata.msg, function() {
                if (rdata.status) {
                    dockerConListRender();
                }
            }, { icon: rdata.status ? 1 : 2 });
        });
    });
}


function startCon(Hostname) {
    dPost('docker_run_con', '', { Hostname: Hostname }, function(rdata) {
        var rdata = $.parseJSON(rdata.data);
        showMsg(rdata.msg, function() {
            if (rdata.status) {
                dockerConListRender();
            }
        }, { icon: rdata.status ? 1 : 2 });
    });
}

function stopCon(Hostname) {
    dPost('docker_stop_con', '', { Hostname: Hostname }, function(rdata) {
        var rdata = $.parseJSON(rdata.data);
        showMsg(rdata.msg, function() {
            if (rdata.status) {
                dockerConListRender();
            }
        }, { icon: rdata.status ? 1 : 2 });
    });
}

async function execCon(Hostname) {
    let socket = await WebShell.getInstance().open();
    var pdata_socket = {};
    var shell = setInterval(function() {
        if ($('.term-box').length == 0) {
            pdata_socket['data'] = 'exit\n';
            socket.emit('webssh', pdata_socket);
            setTimeout(function() { socket.emit('webssh', pdata_socket['data']); }, 1000);
            clearInterval(shell);
        }
    }, 500);
    setTimeout(function() {
        dPost('docker_exec', '', { Hostname: Hostname }, function(res) {
            var res = $.parseJSON(res.data);
            if (!res.status) {
                layer.msg(res.msg, { icon: res.status ? 1 : 2 });
            } else {
                pdata_socket['data'] = 'clear && ' + res.msg + '\n'
                socket.emit('webssh', pdata_socket);
                setTimeout(function() { socket.emit('webssh', pdata_socket['data']); }, 1000);
            }
        });
    });
}

// 选中的 id
let checkedIds = []
// 点击选中
function checkSelect() {
    setTimeout(function () {
        var selectList = $('#con_list tbody input[type="checkbox"].check:checked');
        
        const listCount = $('#con_list tbody tr').length
        checkedIds = selectList.toArray().map(o => o.value)
        var num = selectList.length
        // console.log(num);
        if (num == 1) {
            $('button[batch="true"]').hide();
            $('button[batch="false"]').show();
        }else if (num>1){
            $('button[batch="true"]').show();
            $('button[batch="false"]').show();
        }else{
            $('button[batch="true"]').hide();
            $('button[batch="false"]').hide();
        }
        if (num >= listCount) {
            // 全选
            $('#con_list thead input[type="checkbox"].check').prop('checked', true);
        } else {
            // 取消全选
            $('#con_list thead input[type="checkbox"].check').prop('checked', false);
        }
    },5)
}
// 点击全选
function checkSelectAll() {
    setTimeout(function () {
        var num = $('#con_list thead input[type="checkbox"].check:checked').length;
        const listCount = $('#con_list tbody tr').length
        if (listCount == 0) {
            return
        }
        if (num > 0 ) {
            // 全选
            $('#con_list tbody input[type="checkbox"].check').prop('checked', true);;
        } else {
            // 取消全选
            $('#con_list tbody input[type="checkbox"].check').prop('checked', false);;
        }
        checkSelect()
    },5)
}

function dockerConListRender() {
    dPost('con_list', '', {}, function(rdata) {
        var rdata = $.parseJSON(rdata.data);
        console.log(rdata);
        if (!rdata.status) {
            layer.msg(rdata.msg, { icon: 2, time: 2000 });
            return;
        }


        var list = '';
        var rlist = rdata.data;

        for (var i = 0; i < rlist.length; i++) {
            var docker_status = 'stop';
            var status = '<span class="glyphicon glyphicon-pause" style="color:red;font-size:12px"></span>';
            if (rlist[i]['State']['Status'] == 'running') {
                docker_status = 'start';
                status = '<span class="glyphicon glyphicon-play" style="color:#20a53a;font-size:12px"></span>';
            }

            var op = '';
            op += '<a href="javascript:;" onclick="execCon(\'' + rlist[i]['Config']['Hostname'] + '\')" class="btlink">终端</a> | ';
            op += '<a href="javascript:;" onclick="logsCon(\'' + rlist[i]['Id'] + '\')" class="btlink">日志</a> | ';
            op += '<a href="javascript:;" onclick="deleteCon(\'' + rlist[i]['Config']['Hostname'] + '\')" class="btlink">删除</a>';

            list += '<tr>';
            list += '<td>' + rlist[i]['Name'].substring(1) + '</td>';
            list += '<td>' + rlist[i]['Config']['Image'] + '</td>';
            list += '<td>' + getFormatTime(rlist[i]['Created']) + '</td>';


            if (docker_status == 'start') {
                list += '<td style="cursor:pointer;" align="center" onclick="stopCon(\'' + rlist[i]['Config']['Hostname'] + '\')">' + status + '</td>';
            } else {
                list += '<td style="cursor:pointer;" align="center" onclick="startCon(\'' + rlist[i]['Config']['Hostname'] + '\')">' + status + '</td>';
            }
            list += '<td class="text-right">' + op + '</td>';
            list += '</tr>';
        }

        $('#con_list tbody').html(list);
    });
}

function createConTemplate() {

    dPost('get_docker_create_info', '', {}, function(rdata) {
        var rdata = $.parseJSON(rdata.data);
        // console.log(rdata);
        var rdata = rdata.data;
        var imageOpt = '';
        for (var i = 0; i < rdata.images.length; i++) {
            var imageName = rdata.images[i].RepoTags.indexOf('panel') == -1 ? rdata.images[i].RepoTags : 'aaPanel:' + rdata.images[i].RepoTags.split(':')[1];
            imageOpt += '<option value="' + rdata.images[i].RepoTags + '">' + imageName + '</option>';
        }
        var iplistOpt = '';
        for (var i = 0; i < rdata.iplist.length; i++) {
            iplistOpt += '<option value="' + rdata.iplist[i].address + '">' + rdata.iplist[i].address + '</option>';
        }

        var layer_index = layer.open({
            type: 1,
            title: "创建容器",
            area: '556',
            closeBtn: 2,
            shadeClose: false,
            btn: ['确定', '取消'],
            content: '<div class="bt-form pd20 pb70 ceart-docker new_tname">\
                        <div class="line">\
                            <span class="tname">镜像</span>\
                            <div class="info-r c4"><select class="bt-input-text docker-image" style="width:330px">' + imageOpt + '</select></div>\
                        </div>\
                        <div class="line">\
                            <span class="tname">绑定IP</span>\
                            <div class="info-r c4"><select class="bt-input-text docker-address" style="width:330px"><option value="0.0.0.0">0.0.0.0</optin>' + iplistOpt + '</select></div>\
                        </div>\
                        <div class="line">\
                            <span class="tname">端口映射</span>\
                            <div class="info-r c4">\
                                <div class="type-port">\
                                    <input class="bt-input-text" name="name1" type="number" placeholder="容器端口" style="width:110px;margin-right:15px">\
                                    <select class="bt-input-text" style="width:90px;margin-right:15px"><option value="TCP">TCP</optin><option value="UDP">UDP</optin></select>\
                                    <input class="bt-input-text" name="name2" type="number" placeholder="服务器端口" style="width:90px">\
                                    <span class="plus glyphicon glyphicon-plus" style="color: #20a53a;font-size: 11px;"></span>\
                                </div>\
                                <div class="divtable" style="max-height:100px;overflow:auto; margin-top:15px;width:330px;padding-left: 0px;">\
                                    <table class="table table-hover">\
                                        <tbody id="portabletr"><tr class="more1"><td>当前未添加端口映射</td></tr></tbody>\
                                    </table>\
                                </div>\
                            </div>\
                        </div>\
                        <div class="line">\
                            <span class="tname">目录映射</span>\
                            <div class="info-r c4">\
                                <div class="type-volumes">\
                                    <input class="bt-input-text" name="path1" type="text" placeholder="容器目录" style="width:110px;margin-right:15px">\
                                    <select class="bt-input-text" style="width:90px;margin-right:15px"><option value="rw">read-write</optin><option value="ro">read only</optin></select>\
                                    <input class="bt-input-text" name="path2" type="text" placeholder="服务器目录" style="width:90px">\
                                    <span class="plus2 glyphicon glyphicon-plus" style="color: #20a53a;font-size: 11px;"></span>\
                                </div>\
                                <div class="divtable" style="max-height:100px;overflow:auto; margin-top:15px;width:330px;padding-left: 0px;">\
                                    <table class="table table-hover">\
                                        <tbody id="portabletr2"><tr class="more2"><td>当前未添加目录映射</td></tr></tbody>\
                                    </table>\
                                </div>\
                            </div>\
                        </div>\
                        <div class="line">\
                            <span class="tname" style="height: auto;line-height: 20px;">环境变量<br>(每行一个)</span>\
                            <div class="info-r c4" style="margin-bottom: 0;">\
                                <div class="type-volumes">\
                                    <textarea placeholder="Add variables format as following, one per line:\nJAVA_HOME=/usr/local/java8&#10;HOSTNAME=master" name="environments" class="docker-environments"></textarea>\
                                </div>\
                            </div>\
                        </div>\
                        <div class="line">\
                            <span class="tname">内存配额</span>\
                            <div class="info-r c4"><input class="bt-input-text mr5 docker-mem" type="number" style="width:100px" value="' + parseInt(rdata.memSize / 2) + '">\
                            <span class="dc-un">MB</span><i class="help">不超过， ' + rdata.memSize + 'MB</i></div>\
                        </div>\
                        <div class="line">\
                            <span class="tname">CPU配额</span>\
                            <div class="info-r c4">\
                            <input class="bt-input-text mr5 docker-cpu" type="number" max="100" min="1" style="width:100px" value="100">\
                            <span class="dc-un"></span><i class="help">越大，占用的CPU越多</i></div>\
                        </div>\
                        <div class="line">\
                            <span class="tname">执行命令</span>\
                            <div class="info-r c4"><input class="bt-input-text docker-command" type="text" style="width:330px" value="" placeholder="/bin/bash"></div>\
                        </div>\
                        <div class="line" style="display:none">\
                            <span class="tname">entrypoint</span>\
                            <div class="info-r c4"><input class="bt-input-text docker-entrypoint" type="text" style="width:300px" value=""></div>\
                        </div>\
                    </div>',
            success: function() {

                $(".plus").click(function() {
                    var name1 = $(".type-port input[name='name1']").val();
                    var name2 = $(".type-port input[name='name2']").val();
                    if (name1 < 1 || name1 > 65535 || name2 < 1 || name2 > 65535 || isNaN(name1) || isNaN(name2)) {
                        layer.msg('端口设置值范围无效，范围 [1-65535]', { icon: 2 });
                        return;
                    }

                    var portval = $('#portabletr')[0].childNodes;
                    for (var i = 0; i < portval.length; i++) {
                        if (portval[i].childNodes[0].innerText == '当前未添加端口映射') continue;
                        var sport = portval[i].childNodes[2].innerText;
                        if (name2 == sport) {
                            layer.msg('端口 [' + name2 + '] 已在映射列表中!', { icon: 2 });
                            return;
                        }
                    }
                    var address = $('.docker-address').val();
                    if (address == '0.0.0.0') {
                        address = '*';
                    }
                    var port = address + ':' + name2;
                    var loadT = layer.msg('正在检测中... <img src="/static/img/ing.gif">', { icon: 16, time: 0, shade: [0.3, "#000"] });
                    dPost('docker_port_check', '',{port:port}, function(rdata){
                        layer.close(loadT);
                        var rdata = $.parseJSON(rdata.data);
                        if (rdata.status){
                            layer.msg('端口 [' + name2 + ']已在映射列表中！', { icon: 2 });
                            return;
                        }
                
                        var selecttype = $(".type-port select").val();
                        var portable = '<tr>\
                            <td>' + name1 + '</td>\
                            <td>' + selecttype + '</td>\
                            <td>' + name2 + '</td>\
                            <td class="text-right" width="60"><a href="javascript:;" class="btlink minus">删除</a></td>\
                        </tr>';
                        $("#portabletr").append(portable);
                        $(".more1").remove();
                        $(".minus").click(function() {
                            $(this).parents("tr").remove();
                        });
                    });
                });

                $(".plus2").click(function() {
                    var path1 = $(".type-volumes input[name='path1']").val();
                    var path2 = $(".type-volumes input[name='path2']").val();

                    var notPath = ['/boot', '/bin', '/sbin', '/etc', '/usr/bin', '/usr/sbin', '/dev']
                    if ($.inArray(path2, notPath) != -1) {
                        layer.msg('Cannot map' + path2, { icon: 2 });
                        return;
                    }
                    var portval = $('#portabletr2')[0].childNodes;
                    for (var i = 0; i < portval.length; i++) {
                        if (portval[i].childNodes[0].innerText == '当前未添加端口映射') continue;
                        var sport = portval[i].childNodes[2].innerText;
                        if (path2 == sport) {
                            layer.msg('目录 [' + path2 + '] 已在映射列表中!', { icon: 2 });
                            return;
                        }
                    }
                    var selecttype = $(".type-volumes select").val();
                    var portable = '<tr>\
                        <td class="td_width_1" title="' + path1 + '">' + path1 + '</td>\
                        <td>' + selecttype + '</td><td title="' + path2 + '" class="td_width_1" style="max-width: 138px;">' + path2 + '</td>\
                        <td class="text-right" width="50"><a href="javascript:;" class="btlink minus2">删除</a></td>\
                    </tr>';
                    $("#portabletr2").append(portable);
                    $(".more2").remove();
                    $(".minus2").click(function() {
                        $(this).parents("tr").remove();
                    });
                });
            },
            yes: function(layero, layer_id) {
                var ports = {};
                var volumes = {};
                var portval = $('#portabletr')[0].childNodes;
                var address = $('.docker-address').val();
                var portval2 = $('#portabletr2')[0].childNodes;
                var command = $('.docker-command').val()
                var entrypoint = $('.docker-entrypoint').val()
                var accept = [];

                //遍历端口映射
                for (var i = 0; i < portval.length; i++) {

                    if (portval[i].childNodes[0].innerText == '当前未添加端口映射') {
                        continue;
                    }

                    // console.log(i,portval[i].children[0].innerText);
                    // console.log(i,portval[i].childNodes[0].innerText);

                    var port = portval[i].children[0].innerText.replace(/\s/g, '');
                    var dport = port + '/' + portval[i].children[1].innerText.toLowerCase().replace(/\s/g, '');
                    var sport = [address, parseInt(portval[i].children[2].innerText.replace(/\s/g, ''))];
                    ports[dport] = sport
                    accept.push(port);
                }

                //遍历目录映射
                volumes['/sys/fs/cgroup'] = {
                    'bind': '/sys/fs/cgroup',
                    'mode': 'rw'
                };
                for (var i = 0; i < portval2.length; i++) {
                    if (portval2[i].childNodes[0].innerText.replace(/\s/g, ' ') == '当前未添加目录映射') {
                        continue;
                    }
                    var dpath = portval2[i].childNodes[2].innerText.replace(/\s/g, '');
                    var spath = {
                        'bind': portval2[i].childNodes[0].innerText.replace(/\s/g, ''),
                        'mode': portval2[i].childNodes[1].innerText.toLowerCase().replace(/\s/g, '')
                    };
                    volumes[dpath] = spath;
                }

                var data = {
                    image: $('.docker-image').val(),
                    ports: JSON.stringify(ports),
                    accept: JSON.stringify(accept),
                    volumes: JSON.stringify(volumes),
                    environments: $('.docker-environments').val(),
                    mem_limit: $('.docker-mem').val(),
                    cpu_shares: $('.docker-cpu').val(),
                    command: command,
                    entrypoint: entrypoint
                }

                if (data.mem_limit > rdata.memSize) {
                    layer.msg('内存配额不能大于物理内存 [' + rdata.memSize + ']!', { icon: 2 });
                    return;
                }

                if (data.cpu_shares > 100 || data.cpu_shares < 1) {
                    layer.msg('CPU配额设置值范围应为 [1-100]!', { icon: 2 });
                    return;
                }

                // console.log(data);
                dPost('docker_create_con','', data, function(rdata){
                    var rdata = $.parseJSON(rdata.data);
                    showMsg(rdata.msg,function(){
                        if(rdata.status) {
                            layer.close(layer_index);
                            dockerConListRender();
                        }
                    },{ icon: rdata.status ? 1 : 2 });
                });
            }
        });
    });

}

function dockerConList() {

    var con = '<div class="safe bgw">\
            <button onclick="createConTemplate();" class="btn btn-success btn-sm" type="button" style="margin-right: 5px;">创建容器</button>\
            <div class="divtable mtb10">\
                <div class="tablescroll">\
                    <table id="con_list" class="table table-hover" width="100%" cellspacing="0" cellpadding="0" border="0" style="border: 0 none;">\
                    <thead><tr>\
                    <th style="max-width: 110px">名称</th>\
                    <th style="max-width: 260px">镜像</th>\
                    <th style="min-width: 130px">创建时间</th>\
                    <th style="min-width: 50px" class="text-center">状态</th>\
                    <th style="text-align:right; min-width: 110px">操作</th></tr></thead>\
                    <tbody></tbody></table>\
                </div>\
            </div>\
        </div>';

    $(".soft-man-con").html(con);
    dockerConListRender();
}

function deleteImages(tag, id) {
    safeMessage('删除镜像', '删除镜像[' + tag + '],确定？', function() {
        dPost('docker_remove_image', '', { imageId: id, repoTags: tag }, function(rdata) {
            var rdata = $.parseJSON(rdata.data);
            showMsg(rdata.msg, function() {
                if (rdata.status) {
                    dockerImageListRender();
                }
            }, { icon: rdata.status ? 1 : 2 });
        });
    });
}

function pullImages(tag, id) {
    console.log(tag, id);
    layer.msg('开发中!', { icon: 2 });
}

function dockerImageListRender() {
    dPost('image_list', '', {}, function(rdata) {
        var rdata = $.parseJSON(rdata.data);
        // console.log(rdata);
        if (!rdata.status) {
            layer.msg(rdata.msg, { icon: 2, time: 2000 });
            return;
        }

        var list = '';
        var rlist = rdata.data;

        for (var i = 0; i < rlist.length; i++) {

            var tag = rlist[i]['RepoTags'].split(":")[1];

            var license = 'null';
            var desc = 'null';
            if (rlist[i]['Labels'] == null) {
                license = 'free';
            }

            var op = '';
            op += '<a href="javascript:;" onclick="pullImages(\'' + rlist[i]['RepoTags'] + '\',\'' + rlist[i]['Id'] + '\')" class="btlink">拉取</a> | ';
            op += '<a href="javascript:;" onclick="deleteImages(\'' + rlist[i]['RepoTags'] + '\',\'' + rlist[i]['Id'] + '\')" class="btlink">删除</a>';

            list += '<tr>';
            list += '<td>' + rlist[i]['RepoTags'] + '</td>';
            list += '<td>' + tag + '</td>';
            list += '<td>' + toSize(rlist[i]['Size']) + '</td>';
            list += '<td>' + license + '</td>';
            list += '<td>' + desc + '</td>';
            list += '<td class="text-right">' + op + '</td>';
            list += '</tr>';
        }

        $('#con_list tbody').html(list);
    });
}

function dockerPullImagesFileTemplate() {
    // 拉取镜像文件模板
    var layer_index = layer.open({
        type: 1,
        title: "获取镜像",
        area: '500px',
        closeBtn: 2,
        shadeClose: false,
        content: '<div class="bt-docker pd20">' +
            '<div class="docker-sub">' +
            '<span class="on">官方库</span>' +
            '<span>公共库</span>' +
            '<span>私有库</span>' +
            '</div>' +
            '<div class="bt-form bt-docker-con">' +
            '<div class="conter official_pull pd15"><div class="line">' +
            '<span class="tname">镜像名:</span>\
                            <div class="info-r c4">\
                                <input class="bt-input-text mr5" type="text" name="official_pull_name" style="width:218px" value="" placeholder="memcached:latest">\
                                <button type="button" class="btn btn-sm btn-success official_pull_btn">获取</button>\
                            </div>' +
            '</div></div>' +
            '<div class="conter public_pull pd15" style="display: none;"><div class="line">' +
            '<span class="tname">镜像名:</span>\
                            <div class="info-r c4">\
                                <input class="bt-input-text mr5" type="text" name="public_pull_path" style="width:218px" value="" placeholder="memcached:latest">\
                                <button type="button" class="btn btn-sm btn-success public_pull_btn">获取</button>\
                            </div>' +
            '</div></div>' +
            '<div class="conter private_pull pd15" style="display: none;">' +
            '<div class="line"><span class="tname">镜像地址:</span>\
                                <div class="info-r c4">\
                                    <input class="bt-input-text mr5" type="text" name="private_pull_path" style="width:218px" value="">\
                                    <button type="button" class="btn btn-sm btn-success private_pull_btn">获取</button>\
                                </div>\
                            </div>\
                        </div>\
                    </div>\
                </div>',
        success: function(layero, layer_id) {

            $('.docker-sub span').click(function() {
                var index = $(this).index();
                $(this).addClass('on').siblings().removeClass('on');
                $(this).parent().next().find('.conter').eq(index).show().siblings().hide();
            });

            $('.official_pull_btn').click(function() {
                var name = $('[name="official_pull_name"]').val();
                if (name == '') {
                    layer.msg('镜像名不能为空!');
                    return;
                }
                dPost('docker_pull', '', { images: name }, function(rdata) {
                    var rdata = $.parseJSON(rdata.data);
                    showMsg(rdata.msg, function() {
                        if (rdata.status) {
                            layer.close(layer_index);
                            dockerImageListRender();

                        }
                    }, { icon: rdata.status ? 1 : 2 });
                });
            });

            $('.public_pull_btn').click(function() {
                var path = $('[name="public_pull_path"]').val();
                if (path == '') {
                    layer.msg('公共网络镜像地址不能为空。');
                    return;
                }

                dPost('docker_pull_reg', '', { path: path }, function(rdata) {
                    var rdata = $.parseJSON(rdata.data);
                    showMsg(rdata.msg, function() {
                        if (rdata.status) {
                            layer.close(layer_index);
                            dockerImageListRender();
                        }
                    }, { icon: rdata.status ? 1 : 2 });
                });
            });
            $('.private_pull_btn').click(function() {
                var path = $('[name="private_pull_path"]').val();
                if (path == '') {
                    layer.msg('专用镜像地址不能为空!');
                    return
                }

                dPost('docker_pull_private_new', '', { path: path }, function(rdata) {
                    var rdata = $.parseJSON(rdata.data);
                    showMsg(rdata.msg, function() {
                        if (rdata.status) {
                            layer.close(layer_index);
                            dockerImageListRender();
                        }
                    }, { icon: rdata.status ? 1 : 2 });
                });
            });
        }

    });
}

function dockerImageList() {

    var con = '<div class="safe bgw">\
            <button onclick="dockerPullImagesFileTemplate()" class="btn btn-success btn-sm" type="button" style="margin-right: 5px;">获取镜像</button>\
            <div class="divtable mtb10">\
                <div class="tablescroll">\
                    <table id="con_list" class="table table-hover" width="100%" cellspacing="0" cellpadding="0" border="0" style="border: 0 none;">\
                    <thead><tr>\
                    <th>名称</th>\
                    <th>版本</th>\
                    <th>大小</th>\
                    <th>证书</th>\
                    <th>描述</th>\
                    <th style="text-align:right;">操作</th></tr></thead>\
                    <tbody></tbody></table>\
                </div>\
                <div id="databasePage" class="dataTables_paginate paging_bootstrap page"></div>\
            </div>\
        </div>';

    $(".soft-man-con").html(con);

    dockerImageListRender();
}

function projectBatchOperation(method) {
  var list = $('#con_list tbody input[type="checkbox"].check:checked');
  checkedIds = list.toArray().map(o => o.value)
  projectScriptExcute(method, checkedIds)
}

//获取文件数据
function dockerGetFileBytes(fileName) {
    window.open('/files/download?filename=' + encodeURIComponent(fileName));
}

//删除文件
function dockerDeleteFile(fileName) {
    layer.confirm(lan.get('recycle_bin_confirm', [fileName]), { title: '删除文件', closeBtn: 2, icon: 3 }, function() {
        layer.msg('正在处理,请稍候...', { icon: 16, time: 0, shade: [0.3, '#000'] });
        $.post('/files/delete', 'path=' + encodeURIComponent(fileName), function(rdata) {
            showMsg(rdata.msg, function() {
                dockerImageOutputRender();
            }, { icon: rdata.status ? 1 : 2 });
        }, 'json');
    });
}

function dockerLoadFile(fileName) {
    dPost('image_pick_load', '', { file: fileName }, function(rdata) {
        var rdata = $.parseJSON(rdata.data);
        showMsg(rdata.msg, function() {
            dockerImageOutputRender();
        }, { icon: rdata.status ? 1 : 2 });
    });
}

function dockerImageOutputRender() {
    dPost('image_pick_list', '', {}, function(rdata) {
        var rdata = $.parseJSON(rdata.data);
        if (!rdata.status) {
            layer.msg(rdata.msg, { icon: 2, time: 10000 });
            return;
        }

        var list = '';
        var rlist = rdata.data;

        for (var i = 0; i < rlist.length; i++) {

            var op = '';
            op += '<a href="javascript:;" onclick="dockerGetFileBytes(\'' + rlist[i]['file'] + '\')" class="btlink">下载</a> | ';
            op += '<a href="javascript:;" onclick="dockerLoadFile(\'' + rlist[i]['file'] + '\')" class="btlink">导入</a> | ';
            op += '<a href="javascript:;" onclick="dockerDeleteFile(\'' + rlist[i]['file'] + '\')" class="btlink">删除</a>';

            list += '<tr>';
            list += '<td>' + rlist[i]['name'] + '</td>';
            list += '<td>' + rlist[i]['size'] + '</td>';
            list += '<td>' + rlist[i]['time'] + '</td>';
            list += '<td class="text-right">' + op + '</td>';
            list += '</tr>';
        }

        $('#con_list tbody').html(list);
    });
}

//上传文件
function uploadImageFiles(upload_dir) {
    var image_layer = layer.open({
        type: 1,
        closeBtn: 1,
        title: "上传导入文件[" + upload_dir + ']',
        area: ['500px', '300px'],
        shadeClose: false,
        content: '<div class="fileUploadDiv">\
                <input type="hidden" id="input-val" value="' + upload_dir + '" />\
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
        success: function() {
            $('#filesClose').click(function() {
                layer.close(image_layer);
            });
        }

    });
    uploadStart(function() {
        showMsg('上传成功!', function() {
            dockerImageOutputRender();
            layer.close(image_layer);
        }, { icon: 1, time: 2000 });
    });
}

function dockerImagePick() {

    dPost('image_list', '', {}, function(rdata) {
        var rdata = $.parseJSON(rdata.data);
        var imageList = rdata.data;
        // console.log(imageList);
        var _tbody = '';
        for (var i = 0; i < imageList.length; i++) {
            if (imageList[i] == null) {
                _tbody = '<tr><td colspan="5" align="center">当前无镜像</td></tr>';
                continue;
            }
            var versionData = imageList[i].RepoTags,
                version, reg = new RegExp('((?<=:)[0-9A-z/.-]*)$');
            version = versionData.match(reg);
            _tbody += "<tr><td><input data-name='" + imageList[i].RepoTags + "' type='checkbox' name='images'></td>\
                    <td><span class='max_span' title='" + imageList[i].RepoTags + "'>" + imageList[i].RepoTags + "</span></td>\
                    <td>" + version[0] + "</td>\
                    <td>" + toSize(imageList[i].Size) + "</td></tr>";
        }


        var layerS = layer.open({
            type: 1,
            title: "选择镜像",
            area: '500px',
            closeBtn: 2,
            btn: ['打包', '取消'],
            shadeClose: false,
            content: '<div class="divtable images_pull" style="padding:10px;">\
                        <table class="table" id="images_table">\
                        <thead><tr>\
                            <th style="padding:8px 10px;"><input type="checkbox" name="images_all"></th>\
                            <th>名称</th>\
                            <th>版本</th>\
                            <th>大小</th>\
                        </tr></thead>\
                        <tbody>' + _tbody + '</tbody>\
                        </table>\
                    </div>',
            success: function() {
                readerTableChecked();
                tableFixed('images_table');
            },
            yes: function(layers, index) {
                var data = '',
                    tit = '\xa0',
                    choose_num = $(".images_pull tbody [name=images]:checked").length;
                for (var i = 0; i < choose_num; i++) {
                    if (choose_num == 0) {
                        layer.msg('Please choose the images which need to pack', { icon: 2 });
                        return false;
                    }
                    data += $(".images_pull tbody [name=images]:checked").eq(i).attr('data-name');
                    if (i != (choose_num - 1)) data += ' ';
                }

                dPost('image_pick_save', '', { images: data }, function(rdata) {
                    var rdata = $.parseJSON(rdata['data']);
                    showMsg(rdata.msg, function() {
                        dockerImageOutputRender();
                        layer.close(layerS);
                    }, { icon: rdata.status ? 1 : 2, time: 2000 });
                });
            }
        });
    });
}

function dockerImageOutput() {
    var con = '<div class="safe bgw">\
            <button onclick="dockerImagePick()" class="btn btn-success btn-sm" type="button" style="margin-right: 5px;">镜像打包</button>\
            <button id="btn_image_upload" class="btn btn-default btn-sm" type="button" style="margin-right: 5px;">上传镜像</button>\
            <div class="divtable mtb10">\
                <div class="tablescroll">\
                    <table id="con_list" class="table table-hover" width="100%" cellspacing="0" cellpadding="0" border="0" style="border: 0 none;">\
                    <thead><tr>\
                    <th>名称</th>\
                    <th>大小</th>\
                    <th>时间</th>\
                    <th style="text-align:right;">操作</th></tr></thead>\
                    <tbody></tbody></table>\
                </div>\
                <div id="databasePage" class="dataTables_paginate paging_bootstrap page"></div>\
            </div>\
        </div>';

    $(".soft-man-con").html(con);


    $('#btn_image_upload').click(function() {
        dPostOrgin({
            name: 'docker',
            func: 'image_pick_dir',
            version: '',
        }, function(rdata) {
            var rdata = $.parseJSON(rdata['data']);
            var upload_dir = rdata['data'];
            uploadImageFiles(upload_dir);
        });
    });

    dockerImageOutputRender();
}

function deleteIpList(address) {
    safeMessage('删除IP', '你将删除从IP地址池[' + address + '],确定？', function() {
        dPost('docker_del_ip', '', { address: address }, function(rdata) {
            var rdata = $.parseJSON(rdata.data);
            showMsg(rdata.msg, function() {
                if (rdata.status) {
                    dockerIpListRender();
                }
            }, { icon: rdata.status ? 1 : 2 });
        });
    });
}

function dockerIpListRender() {
    dPost('docker_get_iplist', '', {}, function(rdata) {
        var rdata = $.parseJSON(rdata.data);
        // console.log(rdata);
        if (!rdata.status) {
            layer.msg(rdata.msg, { icon: 2, time: 2000 });
            return;
        }

        var list = '';
        var rlist = rdata.data;

        for (var i = 0; i < rlist.length; i++) {

            var op = '';
            op += '<a href="javascript:;" onclick="deleteIpList(\'' + rlist[i]['address'] + '\')" class="btlink">删除</a>';

            list += '<tr>';
            list += '<td>' + rlist[i]['address'] + '</td>';
            list += '<td>' + rlist[i]['netmask'] + '</td>';
            list += '<td>' + rlist[i]['gateway'] + '</td>';
            list += '<td class="text-right">' + op + '</td>';
            list += '</tr>';
        }

        $('#ip_list tbody').html(list);
    });
}

function dockerAddIpPool() {
    var address = $('input[name="address"]').val();
    var netmask = $('input[name="netmask"]').val();
    var gateway = $('input[name="gateway"]').val();
    dPost('docker_add_ip', '', { address: address, netmask: netmask, gateway: gateway }, function(rdata) {
        var rdata = $.parseJSON(rdata.data);
        showMsg(rdata.msg, function() {
            dockerIpListRender();
        }, { icon: rdata.status ? 1 : 2 })
    });
}

function dockerIpList() {
    var con = '<div class="safe bgw">\
            <div class="search_input">\
                <input class="bt-input-text mr5" type="text" style="width:150px" name="address" placeholder="IP地址">\
                <input class="bt-input-text mr5" name="netmask" type="text" style="width:150px" placeholder="子网掩码">\
                <input name="gateway" class="bt-input-text mr5" type="text" style="width:150px" placeholder="网关">\
                <button class="btn btn-success btn-sm va0" onclick="dockerAddIpPool()">添加</button>\
            </div>\
            <div class="divtable mtb10">\
                <div class="tablescroll">\
                    <table id="ip_list" class="table table-hover" width="100%" cellspacing="0" cellpadding="0" border="0" style="border: 0 none;">\
                    <thead><tr>\
                    <th>IP地址</th>\
                    <th>子网掩码</th>\
                    <th>网关</th>\
                    <th style="text-align:right;">操作</th></tr></thead>\
                    <tbody></tbody></table>\
                </div>\
                <div id="databasePage" class="dataTables_paginate paging_bootstrap page"></div>\
            </div>\
        </div>';

    $(".soft-man-con").html(con);

    dockerIpListRender();
}

// login
function repoLogin() {
    var _option1 = "";
    var obj = { hub_name: "", namespace: "", name: "", registry: "", user_pass: "", user_name: "", arry: ['Docker Repository', 'Other Repository'] };
    for (var i = 0; i < obj.arry.length; i++) {
        _option1 += '<option value="' + obj.arry[i] + '">' + obj.arry[i] + '</option>';
    }
    var layer_index = layer.open({
        type: 1,
        title: "登录到存储库",
        area: '450px',
        closeBtn: 2,
        shadeClose: false,
        content: '<div class="bt-docker-con docker_content">' +
            '<style>.line .tname{width:120px;}</style>' +
            '<div class="soft-man-con pd20 pb70 private_pull">' +
            '<div class="line"><span class="tname">仓库类型：</span><div class="info-r c4"><select class="bt-input-text mr5 project_version" name="dtype" style="width:250px">' + _option1 + '</select></div></div>' +
            '<div class="line"><span class="tname">名称:</span><div class="info-r"><input class="bt-input-text" type="text" name="ctm_name" style="width:250px" value="' + obj.name + '"></div></div>' +
            '<div class="line"><span class="tname">用户名:</span><div class="info-r"><input class="bt-input-text" type="text" name="user" style="width:250px" value="' + obj.user_name + '"></div></div>' +
            '<div class="line"><span class="tname">密码:</span><div class="info-r"><input class="bt-input-text" type="password" name="passwd" style="width:250px" value="' + obj.user_pass + '"></div></div>' +
            '<div class="line"><span class="tname">仓库名称:</span><div class="info-r"><input class="bt-input-text" type="text" name="hub_name" style="width:250px" value="' + obj.hub_name + '"></div></div>' +
            '<div class="line"><span class="tname">命名空间:</span><div class="info-r"><input class="bt-input-text" type="text" name="namespace" style="width:250px" value="' + obj.namespace + '"></div></div>' +
            '<div class="line" style="display:none"><span class="tname">地址:</span><div class="info-r"><input class="bt-input-text" type="text" name="registry" style="width:250px" value="' + obj.registry + '"></div></div>' +
            '<div class="bt-form-submit-btn"><button type="button" class="btn btn-sm btn-success login_aliyun">登录</button></div>' +
            '</div>' +
            '</div>',
        success: function() {
            $('[name="dtype"]').change(function(e) {
                var docker_type = $(this).val();
                if (docker_type == 'Other Repository') {
                    $('.docker_content .line').show();
                } else {
                    $('.docker_content .line').filter(":lt(3)").show().end().filter(":gt(4)").hide();
                }
            });
            $('.login_aliyun').click(function() {
                var user = $('[name="user"]').val(),
                    passwd = $('[name="passwd"]').val(),
                    registry = $('[name="registry"]').val(),
                    name = $('[name="ctm_name"]').val(),
                    hub_name = $('[name="hub_name"]').val(),
                    namespace = $('[name="namespace"]').val();

                var args = {
                    user: user,
                    passwd: passwd,
                    registry: '',
                    repository_name: name,
                    hub_name: hub_name,
                    namespace: namespace
                };
                if ($('[name="dtype"]').val() == 'Docker Repository') {
                    args.registry = '';
                } else {
                    args.registry = registry;
                }

                console.log(obj);
                dPost('docker_login', '', args, function(rdata) {
                    var rdata = $.parseJSON(rdata.data);
                    console.log(rdata);
                    layer.msg(rdata.msg, { icon: rdata.status ? 1 : 2 });
                    if (res.status) {
                        repoListRender();
                        layer.close(layer_index);
                    }
                });
            });
        }
    });

}


function delRepo(address) {
    safeMessage('退出', '你将退出 [' + address + '],确定?', function() {
        dPost('docker_logout', '', { registry: address },
            function(rdata) {
                var rdata = $.parseJSON(rdata.data);
                layer.msg(rdata.msg, { icon: rdata.status ? 1 : 2 });
                if (rdata.status) {
                    repoListRender();
                }
            }
        );
    });
}


function repoListRender() {
    dPost('repo_list', '', {}, function(rdata) {
        var rdata = $.parseJSON(rdata.data);
        console.log(rdata);
        if (!rdata.status) {
            layer.msg(rdata.msg, { icon: 2, time: 2000 });
            return;
        }

        var list = '';
        var rlist = rdata.data;

        for (var i = 0; i < rlist.length; i++) {

            list += '<tr>';
            list += '<td>' + rlist[i]['hub_name'] + '</td>';
            list += '<td>' + rlist[i]['repository_name'] + '</td>';
            list += '<td>' + rlist[i]['namespace'] + '</td>';
            list += '<td>' + rlist[i]['registry'] + '</td>';
            list += '<td class="text-right"><a href="javascript:;" onclick="delRepo(\'' + rlist[i]['registry'] + '\')" class="btlink">删除</a></td>';
            list += '</tr>';
        }

        $('#con_list tbody').html(list);
    });
}

function repoList() {

    var con = '<div class="safe bgw">\
            <button id="docker_login" title="" class="btn btn-success btn-sm" type="button" style="margin-right: 5px;">登录</button>\
            <div class="divtable mtb10">\
                <div class="tablescroll">\
                    <table id="con_list" class="table table-hover" width="100%" cellspacing="0" cellpadding="0" border="0" style="border: 0 none;">\
                    <thead><tr>\
                    <th>名称</th>\
                    <th>仓库名称</th>\
                    <th>命名空间</th>\
                    <th>地址</th>\
                    <th style="text-align:right;">操作</th></tr></thead>\
                    <tbody>\
                    ' + '</tbody></table>\
                </div>\
                <div id="databasePage" class="dataTables_paginate paging_bootstrap page"></div>\
            </div>\
        </div>';

    $(".soft-man-con").html(con);

    //login
    $('#docker_login').click(function() {
        repoLogin();
    });

    repoListRender();
}





function projectList() {

    var con = '<div class="safe bgw">\
            <button title="" class="btn btn-success btn-sm" type="button" style="margin-right: 5px;" onclick="openCreateProject();">新建项目</button>\
            <button title="" class="btn btn-default btn-sm" type="button" style="margin-right: 5px;" onclick="openImportProject();">导入项目</button>\
            <button class="btn btn-default btn-sm va0" batch="false" style="display: none;" onclick="projectBatchOperation(\'start\');">批量启动</button>\
            <button class="btn btn-default btn-sm va0" batch="false" style="display: none;" onclick="projectBatchOperation(\'stop\');">批量停止</button>\
            <button class="btn btn-default btn-sm va0" batch="false" style="display: none;" onclick="projectBatchOperation(\'reload\');">批量重启</button>\
            <div class="divtable mtb10">\
                <div class="tablescroll">\
                    <table id="con_list" class="table table-hover" width="100%" cellspacing="0" cellpadding="0" border="0" style="border: 0 none;">\
                    <thead><tr>\
                    <th width="30"><input class="check" onclick="checkSelectAll();" type="checkbox"></th>\
                    <th>目录</th>\
                    <th>名称</th>' +
                    '<th>状态</th>\
                    <th style="text-align:right;">操作</th></tr></thead>\
                    <tbody>\
                    ' + '</tbody></table>\
                </div>\
                <div id="projectList" class="dataTables_paginate paging_bootstrap page"></div>\
            </div>\
        </div>';

    $(".soft-man-con").html(con);


    projectListRender();
}



function projectListRender() {
    dPost('project_list', '', {}, function(rdata) {
        var rdata = $.parseJSON(rdata.data);
        console.log(rdata);
        if (!rdata.status) {
            layer.msg(rdata.msg, { icon: 2, time: 2000 });
            return;
        }

        var list = '';
        var rlist = rdata.data;
        composeFileListData = rlist;
        for (var i = 0; i < rlist.length; i++) {
            var opt = '';
            if(!rlist[i].loadingStatus) {
                if(rlist[i].status != 'start'){
                    opt += '<a href="javascript:projectScriptExcute(\'start\', [\'' + rlist[i].id + '\'])" class="btlink">启动</a> | ';
                }else{
                    opt += '<a href="javascript:projectScriptExcute(\'stop\', [\'' + rlist[i].id + '\'])" class="btlink">停止</a> | ';
                    opt += '<a href="javascript:projectScriptExcute(\'reload\', [\'' + rlist[i].id + '\'])" class="btlink">重启</a> | ';
                }
            }

            const path = rlist[i].path.replace('//','')
            rlist[i].path = path
            rlist[i].temPath = '<a class="jhlink" href="javascript:openNewWindowPath(\'' + path + '\')">' + path + '</a>';
            
            var status = '';
            if(rlist[i].loadingStatus) {
                status = '<span style="color:#cecece;">' + rlist[i].loadingStatus + '</span>';
            } else {
                if(rlist[i].status != 'start'){
                    status = '<span style="color:rgb(255, 0, 0);" class="glyphicon glyphicon-pause"></span>';
                } else {
                    status = '<span style="color:rgb(92, 184, 92)" class="glyphicon glyphicon-play"></span>';
                }
            }

            var checked = ''
            if (checkedIds.includes(rlist[i]['id'])) {
                checked = 'checked'
            }

            list += '<tr>';
            list += '<td><input value="' + rlist[i]['id'] + '" class="check" onclick="checkSelect();" ' + checked +' type="checkbox"></td>';
            list += '<td><a class="jhlink" href="javascript:openNewWindowPath(\'' + rlist[i].path + '\')">' + rlist[i]['path'] + '</a></td>'
            list += '<td>' + rlist[i]['name'] + '</td>'
            list += '<td>' + status + '</td>';
            list += '<td class="text-right">\
                    ' + opt + '\
                    <a href="javascript:;" onclick="openEditProject(\'' + rlist[i]['id'] + '\')" class="btlink">编辑</a> | \
                    <a href="javascript:;" onclick="projectDelete(\'' + rlist[i]['id'] + '\', \'' + rlist[i]['name'] + '\')" class="btlink">删除</a>\
                    </td>';
            list += '</tr>';
        }

        $('#con_list tbody').html(list);
    });
}


function checkProjectNameExist(projectName) {
    return new Promise(function(resolve, reject) {
        dPost('check_project_name_exist', {}, { name: projectName }, function(data){
            var rdata = $.parseJSON(data.data);
            let isExist = rdata.data;
            if(isExist) {
                layer.msg('项目名称已存在',{icon:2, time:2000});
                return;
            }
            resolve();
        });
    });
}


async function checkPathExist(path) {
    return new Promise(function(resolve, reject) {
        $.post('/files/check_exist_path',{path},function(rdata){
            if(rdata.data) {
                safeMessage('目录已存在','<a style="color:red;">目录['+path+']已存在，要删除目录重新部署吗？</a>删除后将无法恢复,请谨慎操作。<br/>确认请输入结果:',function(){
                    resolve(true);
                });
            } else {
                resolve(false);
            }
        },'json');
    });
}


function handlePathChange() {
    let path = document.getElementById('projectPath').value;
    let name = (path || '').split('/').pop();
    let composeFileName = 'docker-compose.yml';
    let composeFileContent = `\
version: '3'\n\
services:\n\
    demo:\n\
        image: demo:latest\n\
        ports:\n\
            - "1234:80"\n\
        volumes:\n\
            - ./data/:/usr/data # 数据文件建议挂载到项目文件夹下./data/下\n\
            - ./conf/:/usr/conf # 配置文件建议挂载到./conf/下\n\
    `;
    let startScript = `docker-compose -f ${path}/${composeFileName} up -d`;
    let reloadScript = `docker-compose -f ${path}/${composeFileName} restart`;
    let stopScript = `docker-compose -f ${path}/${composeFileName} down`;
    

    $('#projectName').val(name);
    $('#composeFileName').val(composeFileName);
    if(codeMirror && !$('#composeFileContent').text()) {
        $("#composeFileContent").text(composeFileContent);
        codeMirror.setValue(composeFileContent);
    }
    $('#projectStartScript').val(startScript);
    $('#projectReloadScript').val(reloadScript);
    $('#projectStopScript').val(stopScript);
}

function handleProjectNameChange() {
    let name = $("#projectName").val();
    let path = '/www/wwwroot/' + name 
    
    $("#projectPath").val(path);
    handlePathChange();
}


function openCreateProject() {
    var addLayer = layer.open({
        type: 1,
        skin: 'demo-class',
		area: ['900px', "80%"],
        title: '新建项目',
        closeBtn: 2,
        btn: ['提交', '取消'],
        shift: 0,
        shadeClose: false,
        content: "\
        <form class='docker-add-project-form bt-form pd20 pb70' id='addForm'>\
            <div class='line' style='display: none;'>\
                <span class='tname'>项目根目录</span>\
                <div class='info-r c4'>\
                    <input onchange='handlePathChange()' id='projectPath' class='bt-input-text mr5' type='text' name='path' value='"+'/www/wwwroot'+"/' placeholder='"+'/www/wwwroot'+"' style='width:670px' />\
                    <span class='glyphicon glyphicon-folder-open cursor' onclick='changePath(\"projectPath\")'></span>\
                </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>项目名称</span>\
                <div class='info-r c4'>\
                    <input oninput='handleProjectNameChange()' id='projectName' class='bt-input-text' type='text' name='name' value='demo' placeholder='项目名称' style='width:670px' />\
                </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>Compose文件名</span>\
                <div class='info-r c4'>\
                    <input id='composeFileName' class='bt-input-text' type='text' name='composeFileName' value='docker-compose.yml' placeholder='Compose文件名' style='width:670px'/>\
                </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>Compose文件内容</span>\
                <div class='info-r c4'>\
				    <textarea class='mCustomScrollbar bt-input-text' id='composeFileContent' name='composeFileContent' style='width:650px;margin:0 auto;line-height: 1.8;position: relative;top: 10px;' value='' />\
			    </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>启动脚本</span>\
                <div class='info-r c4'>\
                    <textarea id='projectStartScript' class='bt-input-text' name='startScript' style='width:670px;height:50px;line-height:22px' /></textarea>\
                </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>重启脚本</span>\
                <div class='info-r c4'>\
                    <textarea id='projectReloadScript' class='bt-input-text' name='reloadScript' style='width:670px;height:50px;line-height:22px' /></textarea>\
                </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>停止脚本</span>\
                <div class='info-r c4'>\
                    <textarea id='projectStopScript' class='bt-input-text' name='stopScript' style='width:670px;height:50px;line-height:22px' /></textarea>\
                </div>\
            </div>\
        </form>",
        success: function(layero, layer_id) {
            $("#composeFileContent").text('');
            let height = $(window).height() * 0.8;
            $("#composeFileContent").height(height - 200);
            codeMirror = CodeMirror.fromTextArea(document.getElementById("composeFileContent"), {
                extraKeys: {
                    "Ctrl-F": "findPersistent",
                    "Ctrl-H": "replaceAll",
                    "Ctrl-S": function() {
                        $("#composeFileContent").text(codeMirror.getValue());
                    }
                },
                mode: 'yaml',
                lineNumbers: true,
                matchBrackets: true,
                matchtags: true,
                autoMatchParens: true
            });
            codeMirror.focus();
            codeMirror.setSize("670px", height - 250);
            handleProjectNameChange();
        },
        yes: async function(layers, index) {
            $("#composeFileContent").text(codeMirror.getValue());

            var form = $("#addForm").serialize();

            let name = $('#projectName').val();
            let path = $('#projectPath').val();
            let composeFileName = $('#composeFileName').val();
            if (!name) {
                layer.msg("项目名称不能为空", { icon: 2 });
                return
            }
            if (!composeFileName) {
                layer.msg("Compose文件名不能为空", { icon: 2 });
                return
            }
            await checkProjectNameExist(name);
            await checkPathExist(path);

            layer.msg('正在添加,请稍候...',{icon:16,time:0,shade: [0.3, '#000']});
            let data = await dPost('project_add', {}, form);
            let rdata = $.parseJSON(data.data);
            if(!rdata.status) {
                layer.msg(rdata.msg, { icon: rdata.status ? 1 : 2 });
            }
            layer.close(layers);
            projectListRender();
        }
    });
}


function openEditProject(id) {
    editItem = composeFileListData.find(item => item.id == id) || {};
    
    var editLayer = layer.open({
        type: 1,
        skin: 'demo-class',
		area: ['900px', "80%"],
        title: '编辑项目',
        closeBtn: 2,
        btn: ['保存', '取消'],
        shift: 0,
        shadeClose: false,
        content: "\
        <form class='docker-edit-project-form bt-form pd20 pb70' id='editForm'>\
            <div class='line'>\
                <span class='tname'>项目根目录</span>\
                <div class='info-r c4'>\
                    <input onchange='handlePathChange()' id='projectPath' class='bt-input-text mr5' type='text' name='path' value='" + editItem['path'] + "' placeholder='"+'/www/wwwroot'+"' style='width:670px' />\
                    <span class='glyphicon glyphicon-folder-open cursor' onclick='changePath(\"projectPath\")'></span>\
                </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>项目名称</span>\
                <div class='info-r c4'>\
                    <input oninput='handleProjectNameChange()' id='projectName' class='bt-input-text' type='text' name='name' value='" + editItem['name'] + "' placeholder='项目名称' style='width:670px' />\
                </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>Compose文件名</span>\
                <div class='info-r c4'>\
                    <input id='composeFileName' class='bt-input-text' type='text' name='composeFileName' value='" + editItem['compose_file_name'] + "' placeholder='Compose文件名' style='width:670px'/>\
                </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>Compose文件内容</span>\
                <div class='info-r c4'>\
				    <textarea class='mCustomScrollbar bt-input-text' id='composeFileContent' name='composeFileContent' style='width:650px;margin:0 auto;line-height: 1.8;position: relative;top: 10px;' value='' />\
			    </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>启动脚本</span>\
                <div class='info-r c4'>\
                    <textarea id='projectStartScript' class='bt-input-text' name='startScript' style='width:670px;height:50px;line-height:22px' /></textarea>\
                </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>重启脚本</span>\
                <div class='info-r c4'>\
                    <textarea id='projectReloadScript' class='bt-input-text' name='reloadScript' style='width:670px;height:50px;line-height:22px' /></textarea>\
                </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>停止脚本</span>\
                <div class='info-r c4'>\
                    <textarea id='projectStopScript' class='bt-input-text' name='stopScript' style='width:670px;height:50px;line-height:22px' /></textarea>\
                </div>\
            </div>\
        </form>",
        success: function(layero, layer_id) {
            
            $('#composeFileName').val(editItem.compose_file_name);
            $("#composeFileContent").text(editItem.compose_file_content);
            $('#projectStartScript').val(editItem.start_script);
            $('#projectReloadScript').val(editItem.reload_script);
            $('#projectStopScript').val(editItem.stop_script);

            let height = $(window).height() * 0.8;
            $("#composeFileContent").height(height - 200);
            codeMirror = CodeMirror.fromTextArea(document.getElementById("composeFileContent"), {
                extraKeys: {
                    "Ctrl-F": "findPersistent",
                    "Ctrl-H": "replaceAll",
                    "Ctrl-S": function() {
                        $("#composeFileContent").text(codeMirror.getValue());
                    }
                },
                mode: 'yaml',
                lineNumbers: true,
                matchBrackets: true,
                matchtags: true,
                autoMatchParens: true
            });
            codeMirror.focus();
            codeMirror.setSize("670px", height - 250);
            handleProjectNameChange();
        },
        yes: async function(layers, index) {
            $("#composeFileContent").text(codeMirror.getValue());

            var form = $("#editForm").serialize() + '&id=' + editItem.id;

            layer.msg('正在保存,请稍候...',{icon:16,time:0,shade: [0.3, '#000']});
            let data = await dPost('project_edit', {}, form);
            let rdata = $.parseJSON(data.data);
            if(!rdata.status) {
                layer.msg(rdata.msg, { icon: rdata.status ? 1 : 2 });
            }
            layer.close(layers);
            projectListRender();
        }
    });
}



function projectDelete(id, name) {
    safeMessage('确认删除项目[' + name + ']', '删除[' + name + ']项目只会在管理页面移除项目，不会影响项目的运行', function(){
        var data = "id="+id;
        dPost('project_delete', {}, data, function(data){
        	var rdata = $.parseJSON(data.data);
	        layer.msg(rdata.msg,{icon:rdata.status?1:2});
	        projectListRender();
        });
    });
}



async function openImportProject() {
    importProjectLayer = layer.open({
        type: 1,
        skin: 'demo-class',
		area: '900px',
        title: '导入项目',
        closeBtn: 1,
        shift: 0,
        shadeClose: false,
        content: "\
        <form class='docker-import-project-form bt-form pd20 pb70' id='importForm'>\
            <div class='step1'>\
                <div class='line'>\
                    <span class='tname'>项目根目录</span>\
                    <div class='info-r c4'>\
                        <input onchange='handlePathChange()' id='projectPath' class='bt-input-text mr5' type='text' name='path' value='"+'/www/wwwroot'+"/' placeholder='"+'/www/wwwroot'+"' style='width:670px' />\
                        <span class='glyphicon glyphicon-folder-open cursor' onclick='changePath(\"projectPath\")'></span>\
                    </div>\
                </div>\
                <div class='line'>\
                    <span class='tname'>项目名称</span>\
                    <div class='info-r c4'>\
                        <input id='projectName' class='bt-input-text' type='text' name='name' placeholder='项目名称' style='width:670px' />\
                    </div>\
                </div>\
                <div class='line'>\
                    <span class='tname'>Compose文件名</span>\
                    <div class='info-r c4'>\
                        <input id='composeFileName' class='bt-input-text' type='text' name='composeFileName' placeholder='Compose文件名' style='width:670px'/>\
                    </div>\
                </div>\
            </div>\
            <div class='step2'>\
                <div class='line'>\
                    <span class='tname'>Compose文件内容</span>\
                    <div class='info-r c4'>\
                        <textarea class='mCustomScrollbar bt-input-text' id='composeFileContent' name='composeFileContent' style='width:650px;margin:0 auto;line-height: 1.8;position: relative;top: 10px;' value='' />\
                    </div>\
                </div>\
                <div class='line'>\
                    <span class='tname'>启动脚本</span>\
                    <div class='info-r c4'>\
                        <textarea id='projectStartScript' class='bt-input-text' name='startScript' style='width:670px;height:50px;line-height:22px' /></textarea>\
                    </div>\
                </div>\
                <div class='line'>\
                    <span class='tname'>重启脚本</span>\
                    <div class='info-r c4'>\
                        <textarea id='projectReloadScript' class='bt-input-text' name='reloadScript' style='width:670px;height:50px;line-height:22px' /></textarea>\
                    </div>\
                </div>\
                <div class='line'>\
                    <span class='tname'>停止脚本</span>\
                    <div class='info-r c4'>\
                        <textarea id='projectStopScript' class='bt-input-text' name='stopScript' style='width:670px;height:50px;line-height:22px' /></textarea>\
                    </div>\
                </div>\
            </div>\
            <div class='bt-form-submit-btn'>\
                <button type='button' class='btn btn-danger btn-sm btn-title' onclick='layer.close(importProjectLayer)'>取消</button>\
                <button type='button' class='step1-btn btn btn-success btn-sm btn-title' onclick=\"submitImportItemStep1(importProjectLayer)\">解析&下一步</button>\
                <button type='button' class='step2-back-btn btn btn-success btn-sm btn-title' onclick=\"importItemBackStep1()\">上一步</button>\
                <button type='button' class='step2-btn btn btn-success btn-sm btn-title' onclick=\"submitImportItem()\">保存</button>\
            </div>\
        </form>",
        success: function() {
            codeMirror = null;
            $("#importForm .step2, #importForm .step2-btn, #importForm .step2-back-btn").hide();
        }
    });
}


async function submitImportItemStep1(importProjectLayer) {
    const form = $("#importForm").serialize() + '&showLoading=false';
    const path = $("#projectPath").val();
    const name = $("#projectName").val();
    const composeFileName = $("#composeFileName").val();

    if (!path) {
        layer.msg('路径不能为空',{icon:2, time:2000});
        return;
    }
    if (!name) {
        layer.msg("项目名称不能为空", { icon: 2 });
        return
    }
    if (!composeFileName) {
        layer.msg("Compose文件名不能为空", { icon: 2 });
        return
    }

    await checkProjectNameExist(name);

    dPost('get_project_compose_file_content', {}, form, function(rdata) {
        composeFileContent = rdata.data;
        $('#composeFileContent').val(composeFileContent);
        let height = $(window).height() * 0.8;
        $("#composeFileContent").height(height - 200);
        codeMirror = CodeMirror.fromTextArea(document.getElementById("composeFileContent"), {
            extraKeys: {
                "Ctrl-F": "findPersistent",
                "Ctrl-H": "replaceAll",
                "Ctrl-S": function() {
                    $("#composeFileContent").text(codeMirror.getValue());
                }
            },
            mode: 'yaml',
            lineNumbers: true,
            matchBrackets: true,
            matchtags: true,
            autoMatchParens: true
        });
        codeMirror.focus();
        codeMirror.setSize("670px", height - 250);
        refreshLayerCenter(importProjectLayer);
    })
    handlePathChange()

    $("#importForm .step1, #importForm .step1-btn").hide();
    $("#importForm .step2, #importForm .step2-btn").show();
}

async function submitImportItem() {
    var importForm = $("#importForm").serialize();
    let data = await dPost('project_add', {}, importForm);
    
    let rdata = $.parseJSON(data.data);
    if(rdata.status) {
        layer.close(importProjectLayer);
        projectListRender();
        return
    }
    layer.msg(rdata.msg, { icon: rdata.status ? 1 : 2 });
    
}

function projectScriptExcute(opt, ids) {
    editItemList = composeFileListData.filter(item => ids.includes(item.id)) || [];
    layer.msg('执行成功',{icon:1});
    editItemList.forEach(editItem => 
      excuteScriptTask(`docker插件[${editItem.name}:${opt}]`, editItem[opt + '_script'])
      )
}

// 绑定执行完毕事件
$(document).on('messageBoxLayerClose', function(e){
    projectListRender();
});









