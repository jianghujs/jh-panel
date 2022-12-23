var tableData = []; // 表格数据
var addLayer = null; // 添加弹框
var editLayer = null; // 编辑弹框
var logLayer = null; // 日志弹框
var editItem = null; // 编辑项

function refreshTable() {
	var con = '\
    <div class="divtable" style="width:620px;">\
        <button class="btn btn-default btn-sm va0" onclick="openCreateItem();">添加Host</button>\
        <table class="table table-hover" style="margin-top: 10px; max-height: 380px; overflow: auto;">\
            <thead>\
                <th>IP</th>\
                <th>域名</th>\
                <th style="text-align: right;" width="150">操作</th></tr>\
            </thead>\
            <tbody class="plugin-table-body"></tbody>\
        </table>\
    </div>';
    
    $(".soft-man-con").html(con);

	requestApi('host_list',{}, function(data){
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
            tbody += '<tr>\
                        <td style="width: 180px;">'+tmp[i].ip+'</td>\
                        <td style="width: 150px;">'+tmp[i].domain+'</td>\
                        <td style="text-align: right;width: 260px;">' +
                            '<a href="javascript:openEditItem(\''+tmp[i].original+'\')" class="btlink">编辑</a> | ' + 
                            '<a href="javascript:deleteItem(\''+tmp[i].original+'\', \''+tmp[i].ip+'\')" class="btlink">删除</a>\
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
        title: '添加Host',
        closeBtn: 1,
        shift: 0,
        shadeClose: false,
        content: "\
        <form class='bt-form pd20 pb70' id='addForm'>\
            <div class='line'>\
                <span class='tname'>IP</span>\
                <div class='info-r c4'>\
                    <input id='ipInput' class='bt-input-text' type='text' name='ip' placeholder='IP' style='width:458px' />\
                </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>域名</span>\
                <div class='info-r c4'>\
                    <input id='domainInput' class='bt-input-text' type='text' name='domain' placeholder='域名' style='width:458px' />\
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

    requestApi('host_add', data, function(data){
    	var rdata = $.parseJSON(data.data);
        if(rdata.status) {
            layer.close(addLayer);
            refreshTable();
        }
        layer.msg(rdata.msg, { icon: rdata.status ? 1 : 2 });
    });
}

function openEditItem(original) {
    editItem = tableData.find(item => item.original == original) || {};
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
                <span class='tname'>IP</span>\
                <div class='info-r c4'>\
                    <input id='ipInput' class='bt-input-text' type='text' name='ip' placeholder='IP' style='width:458px' />\
                </div>\
            </div>\
            <div class='line'>\
                <span class='tname'>域名</span>\
                <div class='info-r c4'>\
                    <input id='domainInput' class='bt-input-text' type='text' name='domain' placeholder='域名' style='width:458px' />\
                </div>\
            </div>\
            <div class='bt-form-submit-btn'>\
                <button type='button' class='btn btn-danger btn-sm btn-title' onclick='layer.close(editLayer)'>取消</button>\
                <button type='button' class='btn btn-success btn-sm btn-title' onclick=\"submitEditItem()\">提交</button>\
            </div>\
        </form>",
    });
    
    $('#ipInput').val(editItem.ip);
    $('#domainInput').val(editItem.domain);
}

function submitEditItem(){
    var data = $("#editForm").serialize() + '&original=' + editItem.original;

    requestApi('host_edit', data, function(data){
    	var rdata = $.parseJSON(data.data);
        if(rdata.status) {
            layer.close(editLayer);
            refreshTable();
        }
        layer.msg(rdata.msg, { icon: rdata.status ? 1 : 2 });
    });
}

function deleteItem(original, ip) {
    safeMessage('确认删除host', '删除[' + original + ']后不可恢复，请谨慎操作！', function(){
        var data = "original="+original;
        requestApi('host_delete', data, function(data){
        	var rdata = $.parseJSON(data.data);
	        layer.msg(rdata.msg,{icon:rdata.status?1:2});
	        refreshTable();
        });
    });
}

function editHostFile() {
	var con = '\
    <H3>Hosts编辑</H3>\
    <br><br>\
    <textarea id="hostEditTextbox" class="txtsjs bt-input-text"\
    placeholder="127.0.0.1 localhost" name="sBody"\
    style="line-height:20px; width: 755px; height:310px;"></textarea>\
    <br><br>\
    <button class="btn btn-success btn-sm" id="saveHostsFileBTN" \
    onclick="saveHostFile()">保存</button><br>';
    $(".soft-man-con").html(con);
    
	getHostFile();
}

function getHostFile() {
    requestApi('get_host_file',{}, function(data){
		let rdata = $.parseJSON(data.data);
		// console.log(rdata);
		if (!rdata['status']){
            layer.msg(rdata['msg'],{icon:2,time:2000,shade: [0.3, '#000']});
            return;
        }

        $("#hostEditTextbox").val(rdata.data)
	});
}

function saveHostFile() {
	requestApi('save_host_file',{content: $("#hostEditTextbox").val()}, function(data){
		let rdata = $.parseJSON(data.data);
		// console.log(rdata);
		if (!rdata['status']){
            layer.msg(rdata['msg'],{icon:2,time:2000,shade: [0.3, '#000']});
            return;
        }

        getHostFile();
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
        $.post('/plugins/run', {name:'host', func:method, args:_args}, function(data) {
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