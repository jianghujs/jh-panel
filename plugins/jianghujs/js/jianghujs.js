var tableData = []; // 表格数据
var addLayer = null; // 添加弹框
var editLayer = null; // 编辑弹框
var logLayer = null; // 日志弹框
var editItem = null; // 编辑项
var refreshTableTask = null;

function refreshTable() {
    let firstLoad = $('.soft-man-con').html() == '';
	var con = '\
    <div class="divtable" style="width:620px;">\
        <button class="btn btn-default btn-sm va0" onclick="openCreateItem();">添加项目</button>\
        <table class="table table-hover" style="margin-top: 10px; max-height: 380px; overflow: auto;">\
            <thead>\
                <th>目录</th>\
                <th>名称</th>\
                <th>状态</th>\
                <th style="text-align: right;" width="150">操作</th></tr>\
            </thead>\
            <tbody class="plugin-table-body"></tbody>\
        </table>\
    </div>';
    
    if(firstLoad) {
	    $(".soft-man-con").html(con);
    }

	requestApi('project_list',{showLoading: firstLoad}, function(data){
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
                opt += '<a href="javascript:projectScriptExcute(\'start\', \''+tmp[i].id+'\')" class="btlink">启动</a> | ';
            }else{
                opt += '<a href="javascript:projectScriptExcute(\'stop\', \''+tmp[i].id+'\')" class="btlink">停止</a> | ';
                opt += '<a href="javascript:projectScriptExcute(\'reload\', \''+tmp[i].id+'\')" class="btlink">重启</a> | ';
            }
            tmp[i].path = tmp[i].path.replace('//','');
            
            var status = '<span style="color:rgb(92, 184, 92)" class="glyphicon glyphicon-play"></span>';
            if(tmp[i].status != 'start'){
                status = '<span style="color:rgb(255, 0, 0);" class="glyphicon glyphicon-pause"></span>';
            }
            
            tbody += '<tr>\
                        <td style="width: 180px;">'+tmp[i].path+'</td>\
                        <td style="width: 150px;">'+tmp[i].name+'</td>\
                        <td style="width: 60px;">'+status+'</td>\
                        <td style="text-align: right;width: 260px;">\
                            '+opt+
                            '<a href="javascript:projectUpdate(\''+tmp[i].path+'\')" class="btlink">git pull</a> | ' + 
                            '<a href="javascript:openProjectLogs(\''+tmp[i].id+'\')" class="btlink">日志</a> | ' + 
                            '<a href="javascript:openEditItem(\''+tmp[i].id+'\')" class="btlink">编辑</a> | ' + 
                            '<a href="javascript:deleteItem(\''+tmp[i].id+'\', \''+tmp[i].name+'\')" class="btlink">删除</a>\
                        </td>\
                    </tr>';
        }
        $(".plugin-table-body").html(tbody);
	});
}

function clearRefreshTableTask() {
    if(refreshTableTask != null) {
        clearInterval(refreshTableTask);
        refreshTableTask = null;
    }
}

function startRefreshTableTask() {
    clearRefreshTableTask();
    refreshTableTask = setInterval(function(){
        refreshTable();
    }, 5000);
}

// 绑定关闭事件
$(document).on('jianghujsPluginClose', function(e){
    clearRefreshTableTask();
});

function openCreateItem() {
    addLayer = layer.open({
        type: 1,
        skin: 'demo-class',
        area: '640px',
        title: '添加项目',
        closeBtn: 1,
        shift: 0,
        shadeClose: false,
        content: "\
        <form class='bt-form pd20 pb70' id='addForm'>\
            <div class='line'>\
                <span class='tname'>项目根目录</span>\
                <div class='info-r c4'>\
                    <input onchange='handlePathChange()' id='projectPath' class='bt-input-text mr5' type='text' name='path' value='"+'/www/wwwroot'+"/' placeholder='"+'/www/wwwroot'+"' style='width:458px' />\
                    <span class='glyphicon glyphicon-folder-open cursor' onclick='changePath(\"projectPath\")'></span>\
                </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>项目名称</span>\
                <div class='info-r c4'>\
                    <input id='projectName' class='bt-input-text' type='text' name='name' placeholder='项目名称' style='width:458px' />\
                </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>启动脚本</span>\
                <div class='info-r c4'>\
                    <textarea id='projectStartScript' class='bt-input-text' name='startScript' style='width:458px;height:100px;line-height:22px' /></textarea>\
                </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>重启脚本</span>\
                <div class='info-r c4'>\
                    <textarea id='projectReloadScript' class='bt-input-text' name='reloadScript' style='width:458px;height:100px;line-height:22px' /></textarea>\
                </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>停止脚本</span>\
                <div class='info-r c4'>\
                    <textarea id='projectStopScript' class='bt-input-text' name='stopScript' style='width:458px;height:100px;line-height:22px' /></textarea>\
                </div>\
            </div>\
            <div class='bt-form-submit-btn'>\
                <button type='button' class='btn btn-danger btn-sm btn-title' onclick='layer.close(addLayer)'>取消</button>\
                <button type='button' class='btn btn-success btn-sm btn-title' onclick=\"submitCreateItem()\">提交</button>\
            </div>\
        </form>",
    });
}

function submitCreateItem(){
    var data = $("#addForm").serialize();

    requestApi('project_add', data, function(data){
    	var rdata = $.parseJSON(data.data);
        if(rdata.status) {
            layer.close(addLayer);
            refreshTable();
        }
        layer.msg(rdata.msg, { icon: rdata.status ? 1 : 2 });
    });
}

function openEditItem(id) {
    editItem = tableData.find(item => item.id == id) || {};

    editLayer = layer.open({
        type: 1,
        skin: 'demo-class',
        area: '640px',
        title: '编辑项目',
        closeBtn: 1,
        shift: 0,
        shadeClose: false,
        content: "\
        <form class='bt-form pd20 pb70' id='editForm'>\
            <div class='line'>\
                <span class='tname'>项目根目录</span>\
                <div class='info-r c4'>\
                    <input onchange='handlePathChange()' id='projectPath' class='bt-input-text mr5' type='text' name='path' value='"+editItem.path+"' placeholder='"+editItem.path+"' style='width:458px' />\
                    <span class='glyphicon glyphicon-folder-open cursor' onclick='changePath(\"projectPath\")'></span>\
                </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>项目名称</span>\
                <div class='info-r c4'>\
                    <input id='projectName' class='bt-input-text' type='text' name='name' placeholder='项目名称' style='width:458px' value='" + editItem.name + "'/>\
                </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>启动脚本</span>\
                <div class='info-r c4'>\
                    <textarea id='projectStartScript' class='bt-input-text' name='startScript' style='width:458px;height:100px;line-height:22px'/></textarea>\
                </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>重启脚本</span>\
                <div class='info-r c4'>\
                    <textarea id='projectReloadScript' class='bt-input-text' name='reloadScript' style='width:458px;height:100px;line-height:22px'/></textarea>\
                </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>停止脚本</span>\
                <div class='info-r c4'>\
                    <textarea id='projectStopScript' class='bt-input-text' name='stopScript' style='width:458px;height:100px;line-height:22px'/></textarea>\
                </div>\
            </div>\
            <div class='bt-form-submit-btn'>\
                <button type='button' class='btn btn-danger btn-sm btn-title' onclick='layer.close(editLayer)'>取消</button>\
                <button type='button' class='btn btn-success btn-sm btn-title' onclick=\"submitEditItem()\">提交</button>\
            </div>\
        </form>",
    });
    
    $('#projectStartScript').val(editItem.start_script);
    $('#projectReloadScript').val(editItem.reload_script);
    $('#projectStopScript').val(editItem.stop_script);
}

function submitEditItem(){
    var data = $("#editForm").serialize() + '&id=' + editItem.id;

    requestApi('project_edit', data, function(data){
    	var rdata = $.parseJSON(data.data);
        if(rdata.status) {
            layer.close(editLayer);
            refreshTable();
        }
        layer.msg(rdata.msg, { icon: rdata.status ? 1 : 2 });
    });
}

function deleteItem(id, name) {
    safeMessage('确认删除项目[' + name + ']', '删除[' + name + ']项目只会在管理页面移除项目，不会影响项目的运行', function(){
        var data = "id="+id;
        requestApi('project_delete', data, function(data){
        	var rdata = $.parseJSON(data.data);
	        layer.msg(rdata.msg,{icon:rdata.status?1:2});
	        refreshTable();
        });
    });
}

function projectScriptExcute(scriptKey, id) {
    var data = "id="+id+"&scriptKey="+scriptKey;
    requestApi('project_script_excute', data, function(data){
        var rdata = $.parseJSON(data.data);
        layer.msg(rdata.msg,{icon:rdata.status?1:2});
        refreshTable();
    });
}

function projectStart(path) {
    var data = "path="+path;
    requestApi('project_start', data, function(data){
        var rdata = $.parseJSON(data.data);
        layer.msg(rdata.msg,{icon:rdata.status?1:2});
        refreshTable();
    });
}

function projectStop(path) {
    var data = "path="+path;
    requestApi('project_stop', data, function(data){
        var rdata = $.parseJSON(data.data);
        layer.msg(rdata.msg,{icon:rdata.status?1:2});
        refreshTable();
    });
}

function projectUpdate(path) {
    var data = "path="+path;
    requestApi('project_update', data, function(data){
        var rdata = $.parseJSON(data.data);
        layer.msg(rdata.msg,{icon:rdata.status?1:2});
        refreshTable();
    });
}

function handlePathChange() {
    let path = document.getElementById('projectPath').value;
    let name = (path || '').split('/').pop();
    let startScript = 'cd ' + path + '\nnpm i\nnpm start';
    let reloadScript = 'cd ' + path + '\nnpm stop\nnpm start';
    let stopScript = 'cd ' + path + '\nnpm stop';
    $('#projectName').val(name);
    $('#projectStartScript').val(startScript);
    $('#projectReloadScript').val(reloadScript);
    $('#projectStopScript').val(stopScript);
}

function openProjectLogs(id){
	layer.msg('正在获取,请稍候...',{icon:16,time:0,shade: [0.3, '#000']});
	var data='&id='+id;
    requestApi('project_logs', data, function(data){
        var rdata = $.parseJSON(data.data);
        if(!rdata.status) {
			layer.msg(rdata.msg,{icon:2, time:2000});
			return;
		};
		logLayer = layer.open({
			type:1,
			title:lan.crontab.task_log_title,
			area: ['60%','500px'], 
			shadeClose:false,
			closeBtn:1,
			content:'<div class="setchmod bt-form pd20 pb70">'
				+'<pre id="project-log" style="overflow: auto; border: 0px none; line-height:23px;padding: 15px; margin: 0px; white-space: pre-wrap; height: 405px; background-color: rgb(51,51,51);color:#f1f1f1;border-radius:0px;font-family:"></pre>'
				+'<div class="bt-form-submit-btn" style="margin-top: 0px;">'
				+'<button type="button" class="btn btn-success btn-sm" onclick="projectLogsClear('+id+')">清空</button>'
				+'<button type="button" class="btn btn-danger btn-sm" onclick="layer.close(logLayer)">关闭</button>'
			    +'</div>'
			+'</div>'
		});

		setTimeout(function(){
			$("#project-log").html(rdata.msg);
		},200);
    });
}

function projectLogsClear(id) {
    var data = "id="+id;
    requestApi('project_logs_clear', data, function(data){
        var rdata = $.parseJSON(data.data);
        layer.msg(rdata.msg,{icon:rdata.status?1:2});
        layer.close(logLayer);
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

function requestApi(method,args,callback){
    return new Promise(function(resolve, reject) {
        var _args = null; 
        if (typeof(args) == 'string'){
            _args = JSON.stringify(query2Obj(args));
        } else {
            _args = JSON.stringify(args);
        }
        if(args.showLoading != false) {
            var loadT = layer.msg('正在获取中...', { icon: 16, time: 0});
        }
        $.post('/plugins/run', {name:'jianghujs', func:method, args:_args}, function(data) {
            layer.close(loadT);
            if (!data.status){
                layer.msg(data.msg,{icon:0,time:2000,shade: [0.3, '#000']});
                return;
            }
            resolve(data);
            if(typeof(callback) == 'function'){
                callback(data);
            }
        },'json'); 
    });
}