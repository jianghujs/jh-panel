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
        console.log('66666666');
        myPost('do_mysql_backup', {}, function(data){
            var rdata = $.parseJSON(data.data);
            layer.msg(rdata.msg,{icon:1,time:2000,shade: [0.3, '#000']});
        });
    })
    // myPost('my_port','',function(data){
    //     var con = '<div class="line ">\
    //         <div class="info-r  ml0">\
    //         <input name="port" class="bt-input-text mr5 port" type="text" style="width:100px" value="'+data.data+'">\
    //         <button id="btn_change_port" name="btn_change_port" class="btn btn-success btn-sm mr5 ml5 btn_change_port">修改</button>\
    //         </div></div>';
    //     $(".soft-man-con").html(con);

    //     $('#btn_change_port').click(function(){
    //         var port = $("input[name='port']").val();
    //         myPost('set_my_port','port='+port,function(data){
    //             var rdata = $.parseJSON(data.data);
    //             if (rdata.status){
    //                 layer.msg('修改成功!',{icon:1,time:2000,shade: [0.3, '#000']});
    //             } else {
    //                 layer.msg(rdata.msg,{icon:1,time:2000,shade: [0.3, '#000']});
    //             }
    //         });
    //     });
    // });
}
