

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
    createRadioSwitch: function (value = false, change) {
      const uuid = 'radio_switch_' + getRandomString();
      let html = '';
      if(value){
        html = `<input class='radio-switch btswitch btswitch-ios'  id='${uuid}' type='checkbox' checked><label class='btswitch-btn' for='${uuid}' ></label>`;
      } else {
        html = `<input class='radio-switch btswitch btswitch-ios'  id='${uuid}' type='checkbox'><label class='btswitch-btn' for='${uuid}'></label>`;
      }
      $(this).html(html)
      $(this).find('.btswitch').click(function() {
        let checked = $(this).prop('checked');
        change && change(checked);
      });
      return this;
    },
    getRadioSwitchValue: function() {
      return $(this).find('.btswitch').prop('checked');
    }
  })
})()

