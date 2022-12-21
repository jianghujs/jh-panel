function myPost(method,args,callback, title){

    var _args = null; 
    if (typeof(args) == 'string'){
        _args = JSON.stringify(toArrayObject(args));
    } else {
        _args = JSON.stringify(args);
    }

    var _title = '正在获取...';
    if (typeof(title) != 'undefined'){
        _title = title;
    }

    var loadT = layer.msg(_title, { icon: 16, time: 0, shade: 0.3 });
    $.post('/plugins/run', {name:'xtrabackup', func:method, args:_args}, function(data) {
        layer.close(loadT);
        if (!data.status){
            layer.msg(data.msg,{icon:0,time:2000,shade: [0.3, '#000']});
            return;
        }

        if(typeof(callback) == 'function'){
            callback(data);
        }
    },'json'); 
}


function mysqlBackupHtml(){
    var con = `<div class="line ">
                    <div class="info-r  ml0">
                        <button id="btn_mysql_backup" name="btn_mysql_backup" class="btn btn-success btn-sm mr5 ml5 btn_change_port">备份</button>
                    </div>
               </div>`;
    $(".soft-man-con").html(con);
    $('#btn_mysql_backup').click(function(){
        myPost('do_mysql_backup', {}, function(data){
            var rdata = $.parseJSON(data.data);
            if(!rdata.status) {
                layer.msg(rdata.msg,{icon:2, time:2000});
                return;
            };
            layer.msg(rdata.msg,{icon:1,time:2000,shade: [0.3, '#000']});
        });
    })
}
