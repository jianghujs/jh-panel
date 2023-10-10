

/**
 * 用法：
 * 
 * HTML：
 * <div id="testCronSelector"></div>
 * 
 * 初始化：$("#testCronSelector").createCronSelector(value);
 * 获取当前配置：$("#testCronSelector").getCronData();
 */

var cycleArray = { 'day': '每天', 'day-n': 'N天', 'hour': '每小时', 'hour-n': 'N小时', 'minute-n': 'N分钟', 'week': '每星期', 'month': '每月' }
var weekArray = { 1: '周一', 2: '周二', 3: '周三', 4: '周四', 5: '周五', 6: '周六', 0: '周日' }

;(function () {
  $.fn.extend({
    cronSelectorValue: {},
    createCronSelector: function (value = {}) {
      const getselectname = () => {
        $(this).find(".dropdown ul li a").click(function(){
          var txt = $(this).text();
          var type = $(this).attr("value");
          $(this).parents(".dropdown").find("button b").text(txt).attr("val",type);
        });
      }
      
      //清理
      const closeOpt = () => {
        $(this).find(".ptime").html('');
      }
  
      //星期
      const toWeek = () => {
        var mBody = '<div class="dropdown planweek pull-left mr20">\
                <button class="excode_week btn btn-default dropdown-toggle" type="button" data-toggle="dropdown">\
                <b val="0">' + weekArray[parseInt(this.cronSelectorValue.week || '0')] + '</b> <span class="caret"></span>\
                </button>\
                <ul class="dropdown-menu" role="menu" aria-labelledby="excode_week">\
                <li><a role="menuitem" tabindex="-1" href="javascript:;" value="1">周一</a></li>\
                <li><a role="menuitem" tabindex="-1" href="javascript:;" value="2">周二</a></li>\
                <li><a role="menuitem" tabindex="-1" href="javascript:;" value="3">周三</a></li>\
                <li><a role="menuitem" tabindex="-1" href="javascript:;" value="4">周四</a></li>\
                <li><a role="menuitem" tabindex="-1" href="javascript:;" value="5">周五</a></li>\
                <li><a role="menuitem" tabindex="-1" href="javascript:;" value="6">周六</a></li>\
                <li><a role="menuitem" tabindex="-1" href="javascript:;" value="0">周日</a></li>\
                </ul>\
              </div>';
        $(this).find(".ptime").html(mBody);
        getselectname();
      }
  
      //指定1
      const toWhere1 = (ix) => {
        var mBody ='<div class="plan_hms pull-left mr20 bt-input-text">\
                <span><input type="number" name="where1" value="' + (this.cronSelectorValue.where1 || 3) + '" maxlength="2" max="31" min="0"></span>\
                <span class="name">'+ix+'</span>\
              </div>';
        $(this).find(".ptime").append(mBody);
      }
  
      //小时
      const toHour = () => {
        var mBody = '<div class="plan_hms pull-left mr20 bt-input-text">\
                <span><input type="number" name="hour" value="' + (this.cronSelectorValue.hour || 0) + '" maxlength="2" max="23" min="0"></span>\
                <span class="name">小时</span>\
                </div>';
        $(this).find(".ptime").append(mBody);
      }
  
      //分钟
      const toMinute = () => {
        var mBody = '<div class="plan_hms pull-left mr20 bt-input-text">\
                <span><input type="number" name="minute" value="' + (this.cronSelectorValue.minute || 0) + '" maxlength="2" max="59" min="0"></span>\
                <span class="name">分钟</span>\
                </div>';
        $(this).find(".ptime").append(mBody);	
      }
  
      const handleStypeChange = (type) => {
        switch(type){
          case 'day':
            closeOpt();
            toHour();
            toMinute();
            break;
          case 'day-n':
            closeOpt();
            toWhere1('天');
            toHour();
            toMinute();
            break;
          case 'hour':
            closeOpt();
            toMinute();
            break;
          case 'hour-n':
            closeOpt();
            toWhere1('小时');
            toMinute();
            break;
          case 'minute-n':
            closeOpt();
            toWhere1('分钟');
            break;
          case 'week':
            closeOpt();
            toWeek();
            toHour();
            toMinute();
            break;
          case 'month':
            closeOpt();
            toWhere1('日');
            toHour();
            toMinute();
            break;
        }
      }
      this.cronSelectorValue = value;
      var html = "<div class='cron-selector-main pd20' style='height: 100px; overflow: visible;'>\
        <div class='clearfix plan'>\
          <div class='dropdown plancycle pull-left mr20'>\
            <button class='btn btn-default dropdown-toggle' type='button' id='cycle' data-toggle='dropdown' style='width:94px'>\
                              <b val='" + (value.type || 'week') + "'>" + cycleArray[value.type || 'week'] + "</b>\
                              <span class='caret'></span>\
                          </button>\
            <ul class='dropdown-menu' role='menu' aria-labelledby='cycle'>\
              <li><a role='menuitem' tabindex='-1' href='javascript:;' value='day'>每天</a></li>\
              <li><a role='menuitem' tabindex='-1' href='javascript:;' value='day-n'>N天</a></li>\
              <li><a role='menuitem' tabindex='-1' href='javascript:;' value='hour'>每小时</a></li>\
              <li><a role='menuitem' tabindex='-1' href='javascript:;' value='hour-n'>N小时</a></li>\
              <li><a role='menuitem' tabindex='-1' href='javascript:;' value='minute-n'>N分钟</a></li>\
              <li><a role='menuitem' tabindex='-1' href='javascript:;' value='week'>每星期</a></li>\
              <li><a role='menuitem' tabindex='-1' href='javascript:;' value='month'>每月</a></li>\
            </ul>\
          </div>\
          <div class='ptime pull-left'>\
            <div class='dropdown planweek pull-left mr20'>\
              <button class='btn btn-default dropdown-toggle' type='button' id='excode' data-toggle='dropdown'>\
                <b val='0'>" + weekArray[parseInt(value.week || '0')] + "</b>\
                <span class='caret'></span>\
              </button>\
              <ul class='dropdown-menu' role='menu' aria-labelledby='excode'>\
                <li><a role='menuitem' tabindex='-1' href='javascript:;' value='1'>周一</a></li>\
                <li><a role='menuitem' tabindex='-1' href='javascript:;' value='2'>周二</a></li>\
                <li><a role='menuitem' tabindex='-1' href='javascript:;' value='3'>周三</a></li>\
                <li><a role='menuitem' tabindex='-1' href='javascript:;' value='4'>周四</a></li>\
                <li><a role='menuitem' tabindex='-1' href='javascript:;' value='5'>周五</a></li>\
                <li><a role='menuitem' tabindex='-1' href='javascript:;' value='6'>周六</a></li>\
                <li><a role='menuitem' tabindex='-1' href='javascript:;' value='0'>周日</a></li>\
              </ul>\
            </div>\
            <div class='plan_hms pull-left mr20 bt-input-text'>\
              <span><input type='number' name='hour' value='" + (value.hour || 0) + "' maxlength='2' max='23' min='0'></span>\
              <span class='name'>小时</span>\
            </div>\
            <div class='plan_hms pull-left mr20 bt-input-text'>\
              <span><input type='number' name='minute' value='" + (value.minute || 0) + "' maxlength='2' max='59' min='0'></span>\
              <span class='name'>分钟</span>\
            </div>\
          </div>\
        </div>\
        <form class='set-Config' action='/crontab/add' enctype='multipart/form-data' method='post' style='display: none;'>\
          <input type='text' name='type' value='' />\
          <input type='number' name='where1' value='' />\
          <input type='number' name='hour' value='' />\
          <input type='number' name='minute' value='' />\
          <input type='text' name='week' value='' />\
          <input type='submit' />\
        </form>\
      </div>" 
      $(this).append(html)
      $(this).find(".dropdown ul li a").click(function() {
        var txt = $(this).text();
        var type = $(this).attr("value");
        $(this).parents(".dropdown").find("button b").text(txt).attr("val",type);
        handleStypeChange(type);
      });
      if(this.cronSelectorValue.type) {
        handleStypeChange(this.cronSelectorValue.type);
      }
      return this;
    },

    getCronSelectorData: function() {
      var type = $(this).find(".plancycle").find("b").attr("val");
      $(this).find(".set-Config input[name='type']").val(type);

      var is1;
      var is2 = 1;
      switch(type){
        case 'day-n':
          is1=31;
          break;
        case 'hour-n':
          is1=23;
          break;
        case 'minute-n':
          is1=59;
          break;
        case 'month':
          is1=31;
          break;
      }
      
      var where1 = $(this).find('.excode_week b').attr('val');
      $(this).find(".set-Config input[name='where1']").val(where1);

      // if(where1 > is1 || where1 < is2){
      // 	$(this).find(".ptime input[name='where1']").focus();
      // 	layer.msg('表单不合法,请重新输入!',{icon:2});
      // 	return;
      // }
      
      var hour = $(this).find(".ptime input[name='hour']").val();
      if(hour > 23 || hour < 0){
        $(this).find(".ptime input[name='hour']").focus();
        layer.msg('小时值不合法!',{icon:2});
        return;
      }
      $(this).find(".set-Config input[name='hour']").val(hour);
      var minute = $(this).find(".ptime input[name='minute']").val();
      if(minute > 59 || minute < 0){
        $(this).find(".ptime input[name='minute']").focus();
        layer.msg('分钟值不合法!',{icon:2});
        return;
      }
      $(this).find(".set-Config input[name='minute']").val(minute);
      
      if (type == 'minute-n'){
        var where1 = $(this).find(".ptime input[name='where1']").val();
        $(this).find(".set-Config input[name='where1']").val(where1);
      }

      if (type == 'day-n'){
        var where1 = $(this).find(".ptime input[name='where1']").val();
        $(this).find(".set-Config input[name='where1']").val(where1);
      }

      if (type == 'hour-n'){
        var where1 = $(this).find(".ptime input[name='where1']").val();
        $(this).find(".set-Config input[name='where1']").val(where1);
      }

      if (type == 'week'){
        // TODO 星期暂时写死0，待完善逻辑
        // var where1 = $("#ptime input[name='where1']").val();
        var where1 = 0;
        $(this).find(".set-Config input[name='where1']").val(where1);
      }
      let data = $(this).find(".set-Config").serialize();
      return data;
    }
  })
})()

