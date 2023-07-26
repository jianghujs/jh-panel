var tableData = []; // 表格数据
var addLayer = null; // 添加弹框
var editLayer = null; // 编辑弹框
var logLayer = null; // 日志弹框
var deployLayer = null; // 部署弹框
var editItem = null; // 编辑项


function projectPanel() {
	refreshTable();
}

function refreshTable() {
    let firstLoad = $('.nfs-util-panel').length == 0;
	var con = '\
    <div class="divtable nfs-util-panel">\
    <button class="btn btn-default btn-sm va0" onclick="openCreateItem();">添加挂载目录</button>\
        <table class="table table-hover" style="margin-top: 10px; max-height: 380px; overflow: auto;">\
            <thead>\
                <th>名称</th>\
                <th>NFS服务器</th>\
                <th>挂载路径</th>\
                <th>开机自动挂载</th>\
                <th>状态</th>\
                <th>创建时间</th>\
                <th style="text-align: right;" width="150">操作</th></tr>\
            </thead>\
            <tbody class="plugin-table-body"></tbody>\
        </table>\
    </div>';
    
    if(firstLoad) {
	    $(".soft-man-con").html(con);
    }

	requestApi('mount_list',{showLoading: firstLoad}, function(data){
		let rdata = $.parseJSON(data.data);
		// console.log(rdata);
		if (!rdata['status']){
            layer.msg(rdata['msg'],{icon:2,time:2000,shade: [0.3, '#000']});
            return;
        }

        var tbody = '';
        var tmp = rdata['data'];
        tableData = tmp;
        for(var i=0;i<tmp.length;i++){
            var opt = '';
            if(tmp[i].status != 'start'){
                opt += '<a href="javascript:doMount(\''+tmp[i].id+'\')" class="btlink">挂载</a> | ';
            }else{
                opt += '<a href="javascript:doUnMount(\''+tmp[i].id+'\')" class="btlink">卸载</a> | ';
            }

            const mountPath = tmp[i].mountPath.replace('//','')
            tmp[i].mountPath = mountPath
            tmp[i].temMountPath = '<a class="jhlink" href="javascript:openNewWindowPath(\'' + mountPath + '\')">' + mountPath + '</a>';
            
            var status = '';
            if(tmp[i].status != 'start'){
                status = '<span style="color:rgb(255, 0, 0);" class="glyphicon glyphicon-pause"></span>';
            } else {
                status = '<span style="color:rgb(92, 184, 92)" class="glyphicon glyphicon-play"></span>';
            }
            

            var autostart = '';
            var autostartChecked = tmp[i].autostartStatus == 'start'? 'checked' : '';
            autostart = '<div class="autostart-item">\
                <input class="btswitch btswitch-ios" id="autostart_' + tmp[i].id + '" type="checkbox" ' + autostartChecked + '>\
                <label class="btswitch-btn" for="autostart_' + tmp[i].id + '" onclick="toggleAutostart(\'' + tmp[i].id + '\')"></label></div>';
            
            tbody += '<tr>\
                        <td style="width: 180px;">'+tmp[i].name+'</td>\
                        <td style="width: 160px;"><div style=" width:160px; overflow: hidden; text-overflow: ellipsis;" title="'+tmp[i].serverIP+':'+tmp[i].mountServerPath+'">'+tmp[i].serverIP+':'+tmp[i].mountServerPath+'</div></td>\
                        <td style="width: 160px;"><div style=" width:160px; overflow: hidden; text-overflow: ellipsis;" title="'+tmp[i].mountPath+'">'+tmp[i].temMountPath+'</div></td>' +
                        '<td style="width: 220px;">'+autostart+'</td>' +
                        '<td style="width: 100px;">'+status+'</td>' +
                        '<td style="width: 180px;">'+tmp[i].createTime+'</td>' +
                        '<td style="text-align: right;width: 280px;">\
                            '+opt+
                            '<a href="javascript:openEditItem(\''+tmp[i].id+'\')" class="btlink">编辑</a> | ' + 
                            '<a href="javascript:deleteItem(\''+tmp[i].id+'\', \''+tmp[i].name+'\')" class="btlink">删除</a>\
                        </td>\
                    </tr>';
        }
        $(".plugin-table-body").html(tbody);
	});
}

function openCreateItem() {
    addLayer = layer.open({
        type: 1,
        skin: 'demo-class',
        area: '640px',
        title: '添加挂载目录配置',
        closeBtn: 1,
        shift: 0,
        shadeClose: false,
        content: "\
        <form class='bt-form pd20 pb70' id='addForm'>\
            <div class='line'>\
                <span class='tname'>NFS服务器IP</span>\
                <div class='info-r c4'>\
                    <input id='serverIP' class='bt-input-text' type='text' name='serverIP' placeholder='请输入NFS服务器IP，并点击获取共享目录' style='width: 336px' />\
                    <button type='button' class='btn btn-success btn-sm btn-title' onclick=\"getNfsSharePath()\">点击获取共享目录</button>\
                </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>共享目录</span>\
                <div class='info-r c4'>\
                <select id='mountServerPath' class='bt-input-text c5 mr5' name='mountServerPath' placeholder='请选择共享目录' style='width:458px' onchange='handleMountServerPathChange()'>\
                    <option>无数据</option>\
                </select>\
                </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>挂载名称</span>\
                <div class='info-r c4'>\
                    <input id='mountName' class='bt-input-text' type='text' name='name' placeholder='挂载名称' style='width:458px' />\
                </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>挂载路径</span>\
                <div class='info-r c4'>\
                    <input onchange='handlePathChange()' id='mountPath' class='bt-input-text mr5' type='text' name='mountPath' value='' placeholder='请输入挂载路径' style='width:458px' />\
                    <span class='glyphicon glyphicon-folder-open cursor' onclick='changePath(\"mountPath\")'></span>\
                </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>备注</span>\
                <div class='info-r c4'>\
                    <textarea id='mountRemark' class='bt-input-text' name='remark' style='width:458px;height:100px;line-height:22px'/></textarea>\
                </div>\
            </div>" +
            "<div class='bt-form-submit-btn'>\
                <button type='button' class='btn btn-danger btn-sm btn-title' onclick='layer.close(addLayer)'>取消</button>\
                <button type='button' class='btn btn-success btn-sm btn-title' onclick=\"submitCreateItem()\">提交</button>\
            </div>\
        </form>",
    });
}

function submitCreateItem(){
    var data = $("#addForm").serialize();
    requestApi('mount_add', data, function(data){
    	var rdata = $.parseJSON(data.data);
        if(rdata.status) {
            layer.close(addLayer);
            refreshTable();
        }
        layer.msg(rdata.msg, { icon: rdata.status ? 1 : 2 });
    });
}

async function openEditItem(id) {
    editItem = tableData.find(item => item.id == id) || {};
    if(editItem.status == 'start' || editItem.autostartStatus == 'start') {
        layer.msg('请先卸载挂载目录并关闭开机自动挂载后再进行编辑', { icon: 2 });
        return;
    }
    editLayer = layer.open({
        type: 1,
        skin: 'demo-class',
        area: '640px',
        title: '编辑挂载目录配置',
        closeBtn: 1,
        shift: 0,
        shadeClose: false,
        content: "\
        <form class='bt-form pd20 pb70' id='editForm'>\
            <div class='line'>\
                <span class='tname'>NFS服务器IP</span>\
                <div class='info-r c4'>\
                    <input id='serverIP' class='bt-input-text' type='text' name='serverIP' placeholder='请输入NFS服务器IP，并点击获取共享目录' value='"+editItem.serverIP+"' style='width: 336px' />\
                    <button type='button' class='btn btn-success btn-sm btn-title' onclick=\"getNfsSharePath()\">点击获取共享目录</button>\
                </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>共享目录</span>\
                <div class='info-r c4'>\
                <select id='mountServerPath' class='bt-input-text c5 mr5' name='mountServerPath' placeholder='请选择共享目录' style='width:458px' value='"+editItem.mountServerPath+"' onchange='handleMountServerPathChange'>\
                    <option>无数据</option>\
                </select>\
                </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>挂载名称</span>\
                <div class='info-r c4'>\
                    <input id='mountName' class='bt-input-text' type='text' name='name' placeholder='挂载名称' style='width:458px' value='"+editItem.name+"' />\
                </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>挂载路径</span>\
                <div class='info-r c4'>\
                    <input onchange='handlePathChange()' id='mountPath' class='bt-input-text mr5' type='text' name='mountPath' value='"+editItem.mountPath+"'  placeholder='请输入挂载路径' style='width:458px' />\
                    <span class='glyphicon glyphicon-folder-open cursor' onclick='changePath(\"mountPath\")'></span>\
                </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>备注</span>\
                <div class='info-r c4'>\
                    <textarea id='mountRemark' class='bt-input-text' name='remark' style='width:458px;height:100px;line-height:22px' value='"+editItem.remark+"' /></textarea>\
                </div>\
            </div>" +
            "<div class='bt-form-submit-btn'>\
                <button type='button' class='btn btn-danger btn-sm btn-title' onclick='layer.close(editLayer)'>取消</button>\
                <button type='button' class='btn btn-success btn-sm btn-title' onclick=\"submitEditItem()\">提交</button>\
            </div>\
        </form>",
    });
    await getNfsSharePath();
    $('#mountServerPath').val(editItem.mountServerPath);
    $('#mountName').val(editItem.name);
    $('#mountPath').val(editItem.mountPath);
    $('#mountRemark').val(editItem.remark);
}

function submitEditItem(){
    var data = $("#editForm").serialize() + '&id=' + editItem.id;

    requestApi('mount_edit', data, function(data){
    	var rdata = $.parseJSON(data.data);
        if(rdata.status) {
            layer.close(editLayer);
            refreshTable();
        }
        layer.msg(rdata.msg, { icon: rdata.status ? 1 : 2 });
    });
}

function deleteItem(id, name) {
    safeMessage('确认删除挂载[' + name + ']', '删除[' + name + ']挂载只会在挂载列表移除，不会影响挂载的运行！<span style="color: red">如果需要卸载和取消自启动，请先完成对应操作后再删除！<span>', function(){
        var data = "id="+id;
        requestApi('mount_delete', data, function(data){
        	var rdata = $.parseJSON(data.data);
	        layer.msg(rdata.msg,{icon:rdata.status?1:2});
	        refreshTable();
        });
    });
}

async function getNfsSharePath() {
    let serverIP = document.getElementById('serverIP').value;
    let data = await requestApi('get_nfs_share_path', {serverIP});
    let rdata = $.parseJSON(data.data);
    if(rdata.status) {
        let list = rdata.data || [];
        let options = list.map(item => '<option value="' + item.path + '">' + item.path + '</option>').join('');
        $('#mountServerPath').html(options);
        handleMountServerPathChange();
    } else {
        layer.msg(rdata.msg, { icon: rdata.status ? 1 : 2 });
    }
}

function handleMountServerPathChange() {
    let mountServerPath = document.getElementById('mountServerPath').value;
    document.getElementById('mountName').value = mountServerPath.split('/').pop();;
    document.getElementById('mountPath').value = mountServerPath;
}


async function doMount(id) {
    var mountScriptData = await requestApi('get_mount_script', "id="+id);
    if (!mountScriptData.status){
        layer.msg(mountScriptData.msg,{icon:0,time:2000,shade: [0.3, '#000']});
        return;
    }
    await execScriptAndShowLog('正在挂载...', mountScriptData.data);
    refreshTable();
}

async function doUnMount(id) {
    var unMountScriptData = await requestApi('get_unmount_script', "id="+id);
    if (!unMountScriptData.status){
        layer.msg(unMountScriptData.msg,{icon:0,time:2000,shade: [0.3, '#000']});
        return;
    }
    await execScriptAndShowLog('正在卸载...', unMountScriptData.data);
    refreshTable();
}

function toggleAutostart(id) {
    requestApi('mount_toggle_autostart', {id}, function(data){
    	var rdata = $.parseJSON(data.data);
        if(rdata.status) {
            layer.close(addLayer);
        }
        layer.msg(rdata.msg, { icon: rdata.status ? 1 : 2 });
        refreshTable();
    });
}

function query2Obj(str){
    var data = {};
    kv = str.split('&');
    for(i in kv){
        v = kv[i].split('=');
        data[v[0]] = v[1];
    }
    return data;
}

async function requestApi(method,args,callback){
    return new Promise(function(resolve, reject) {
        
        var argsObj = null;
        if (typeof(args) == 'string'){
            argsObj = query2Obj(args);
        } else {
            argsObj = args;
        }
        if(argsObj.showLoading != false && argsObj.showLoading != 'false') {
            var loadT = layer.msg('正在获取中...', { icon: 16, time: 0});
        }
        $.post('/plugins/run', {name:'nfs-util', func:method, args:JSON.stringify(argsObj)}, function(data) {
            layer.close(loadT);
            if (!data.status){
                layer.msg(data.msg,{icon:0,time:2000,shade: [0.3, '#000']});
                return;
            }
            resolve(data);
            callback && callback(data);
        },'json'); 
    });
}