

/**
 * 用法：
 * 
 * HTML：
 * <div id="testRadio"></div>
 * 
 * 初始化：$("#testRadio").createRadio(value);
 */

;(function () {
  $.fn.extend({
    createTextSwitch: function (value = false, change) {
      const uuid = 'text_switch_' + getRandomString();
      let html = '';
      if(value){
        html = `<span class="btswitch" style="color:rgb(92, 184, 92);cursor:pointer" title="点击停用">正常<span class="glyphicon glyphicon-play"></span></span>`
      } else {
        html = `<span class="btswitch" style="color:red;cursor:pointer" title="点击启用">停用<span style="color:rgb(255, 0, 0);" class="glyphicon glyphicon-pause"></span></span>`
      }
      html += `<input type="hidden" class="val" name="${uuid}" value="${value}" />`;
      $(this).html(html)
      $(this).find('.btswitch').click(function() {
        change && change(!value);
      });
      return this;
    },
    getRadioSwitchValue: function() {
      return $(this).find('.btswitch').prop('checked');
    }
  })
})()

