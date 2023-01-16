var rsa = '';
function renderMain() {
    var con = '\
    <div class="pd15">\
        <button id="createRsaBtn" class="btn btn-default btn-sm va0 " onclick="createRsa();">生成SSH公钥</button>\
        <textarea id="rsaTextbox" class="txtsjs bt-input-text mt10"\
        style="line-height:20px; width: 100%; height:310px;"></textarea>\
    </div>';
    
    $(".soft-man-con").html(con);
    requestApi('get_rsa', {}, function(data){
        var rdata = $.parseJSON(data.data);
        rsa = rdata.data;
        if(rsa) {
            $("#createRsaBtn").html('重新生成SSH公钥');
        }
        $("#rsaTextbox").val(rsa);
    });
}
async function confirmRecreateRsa() {
    return new Promise(function(resolve, reject) {
        safeMessage('确认重新生成SSH密钥', '重新生成SSH密钥可能会影响Git等服务的连接，是否继续？', function(){
            resolve(true);
        });
    })
}
async function createRsa() {
    if(rsa) {
        console.log("rsa is not empty")
        await confirmRecreateRsa();
    }
    requestApi('create_rsa', {}, function(data){
        var rdata = $.parseJSON(data.data);
        renderMain();
        setTimeout(function() {
            layer.msg(rdata.msg,{icon:rdata.status?1:2});
        }, 100);
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
        $.post('/plugins/run', {name:'ssh', func:method, args:_args}, function(data) {
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