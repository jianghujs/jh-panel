var tableData = []; // 表格数据
var addLayer = null; // 添加弹框
var editLayer = null; // 编辑弹框
var logLayer = null; // 日志弹框
var editItem = null; // 编辑项
var refreshTableTask = null;

function refreshTable() {
    let firstLoad = $('.soft-man-con').html() == '';
	var con = '\
    <div class="divtable">\
        <button class="btn btn-default btn-sm va0" onclick="openCreateItem();">添加脚本</button>\
        <table class="table table-hover" style="margin-top: 10px; max-height: 380px; overflow: auto;">\
            <thead>\
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

	requestApi('script_list',{showLoading: firstLoad}, function(data){
		let rdata = $.parseJSON(data.data);
		if (!rdata['status']){
            layer.msg(rdata['msg'],{icon:2,time:2000,shade: [0.3, '#000']});
            return;
        }

        var tbody = '';
        var tmp = rdata['data'];
        tableData = tmp;
        for(var i=0;i<tmp.length;i++){
            var opt = '';
            
            var statusHtml = '';
            var loadingStatus = tmp[i].loadingStatus || '';
            var loadingStatusColor = {'执行成功': 'green', '执行失败': 'red'}[loadingStatus.trim()]
            
            statusHtml = '<span style="color:' + (loadingStatusColor || '#cecece') + ';">' + (loadingStatus || '未执行') + '</span>';

            if(!loadingStatus || loadingStatus != '执行中...') {
                opt += '<a href="javascript:scriptExcute(\''+tmp[i].id+'\')" class="btlink">执行</a> | ';    
            }

            tbody += '<tr>\
                        <td style="width: 180px;">'+tmp[i].name+'</td>\
                        <td style="width: 100px;">'+statusHtml+'</td>\
                        <td style="text-align: right;width: 280px;">\
                            '+opt+
                            '<a href="javascript:openScriptLogs(\''+tmp[i].id+'\')" class="btlink">日志</a> | ' + 
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
$(document).on('dockerPluginClose', function(e){
    clearRefreshTableTask();
});

function openCreateItem() {
    addLayer = layer.open({
        type: 1,
        skin: 'demo-class',
        area: '640px',
        title: '添加脚本',
        closeBtn: 1,
        shift: 0,
        shadeClose: false,
        content: "\
        <form class='bt-form pd20 pb70' id='addForm'>\
            <div class='line'>\
                <span class='tname'>脚本名称</span>\
                <div class='info-r c4'>\
                    <input id='scriptName' class='bt-input-text' type='text' name='name' placeholder='脚本名称' style='width:458px' />\
                </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>脚本内容</span>\
                <div class='info-r c4'>\
                    <textarea id='scriptContent' class='bt-input-text' name='script' style='width:458px;height:100px;line-height:22px' /></textarea>\
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
    requestApi('script_add', {
        name: $('#addForm #scriptName').val(),
        script: $('#addForm #scriptContent').val()
    }, function(data){
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
                <span class='tname'>脚本名称</span>\
                <div class='info-r c4'>\
                    <input id='scriptName' class='bt-input-text' type='text' name='scriptName' placeholder='脚本名称' style='width:458px' value='" + editItem.name + "'/>\
                </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>脚本内容</span>\
                <div class='info-r c4'>\
                    <textarea id='scriptContent' class='bt-input-text' name='scriptContent' style='width:458px;height:100px;line-height:22px'/></textarea>\
                </div>\
            </div>\
            <div class='bt-form-submit-btn'>\
                <button type='button' class='btn btn-danger btn-sm btn-title' onclick='layer.close(editLayer)'>取消</button>\
                <button type='button' class='btn btn-success btn-sm btn-title' onclick=\"submitEditItem()\">提交</button>\
            </div>\
        </form>",
    });
    
    $('#scriptName').val(editItem.name);
    $('#scriptContent').val(editItem.script);
}

function submitEditItem(){
    requestApi('script_edit', {
        id: editItem.id,
        name: $('#editForm #scriptName').val(),
        script: $('#editForm #scriptContent').val()
    }, function(data){
    	var rdata = $.parseJSON(data.data);
        if(rdata.status) {
            layer.close(editLayer);
            refreshTable();
        }
        layer.msg(rdata.msg, { icon: rdata.status ? 1 : 2 });
    });
}

function deleteItem(id, name) {
    safeMessage('确认删除脚本[' + name + ']', '确认删除后不可恢复，请谨慎操作', function(){
        var data = "id="+id;
        requestApi('script_delete', data, function(data){
        	var rdata = $.parseJSON(data.data);
	        layer.msg(rdata.msg,{icon:rdata.status?1:2});
	        refreshTable();
        });
    });
}

function scriptExcute(id) {
    setTimeout(function() {
        refreshTable()
    }, 100)
    requestApi('script_excute', {
        id: id,
    }, function(data){
        var rdata = $.parseJSON(data.data);
        layer.msg(rdata.msg,{icon:rdata.status?1:2});
        refreshTable();
    });
}

function openScriptLogs(id){
	layer.msg('正在获取,请稍候...',{icon:16,time:0,shade: [0.3, '#000']});
	requestApi('script_logs', {
        id: id
    }, function(data){
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
				+'<button type="button" class="btn btn-success btn-sm" onclick="scriptLogsClear('+id+')">清空</button>'
				+'<button type="button" class="btn btn-danger btn-sm" onclick="layer.close(logLayer)">关闭</button>'
			    +'</div>'
			+'</div>'
		});

		setTimeout(function(){
			$("#project-log").html(rdata.msg);
		},200);
    });
}

function scriptLogsClear(id) {
    var data = "id="+id;
    requestApi('script_logs_clear', data, function(data){
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

function encodeObjValue(obj){
    var data = {};
    for(i in obj){
        data[i] = encodeURIComponent(obj[i]);
    }
    return data;
}

function requestApi(method,args,callback){
    return new Promise(function(resolve, reject) {
        var _args = args; 
        if (typeof(args) == 'string'){
            _args = query2Obj(args);
        }
        _args = JSON.stringify(encodeObjValue(_args));
        if(args.showLoading != false) {
            var loadT = layer.msg('正在获取中...', { icon: 16, time: 0});
        }
        $.post('/plugins/run', {name:'docker', func:method, args:_args}, function(data) {
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