var msState = {
  monitor_url: '',
  pair_name: '',
  pair_id: '',
  host_id: '',
  host_name: '',
  peer_host_id: '',
  peer_state: null,
  peer_collect_status: '',
  peer_collect_msg: '',
  peer_public_ip: '',
  peer_ssh_port: '22',
  peer_ssh_user: 'root',
  peer_public_key: '',
  bind_test_status: 'untested',
  role: 'standby',
  desired_role: 'standby',
  poll_interval: 10,
  report_interval: 30,
  last_report_at: '',
  switch_run_id: '',
  switch_status: 'idle',
  health_status: 'normal',
  health_text: '正常',
  log_path: '',
  health: {
    mysql: {status: 'unknown', text: '等待自检'},
    rsync: {status: 'unknown', text: '等待自检'},
    openresty: {status: 'unknown', text: '等待自检'}
  },
  options: {
    local_ip: '',
    remote_ip: '',
    remote_ssh_port: '22',
    run_checksum: true,
    sync_files: true,
    sync_file_dirs: '/www/wwwroot,/www/wwwstorage',
    sync_ignore_dirs: '.git,node_modules,logs,run',
    restore_site_setting: false,
    restore_plugin_setting: false,
    run_xtrabackup_inc_restore: false,
    promote_mysql: true
  },
  log: ''
};

var msKeyInfo = {public_key: '', has_private: false, has_public: false, public_key_path: '/root/.ssh/id_rsa.pub'};
var msSwitchLogTimer = null;
var msSwitchLogLayerIndex = null;
var msSwitchDialogIndex = null;
var msSwitchWizard = {step: 1, targetRole: '', options: null, prepared: false, prepareRunId: '', prepareLog: ''};

function msPost(method, args, callback, options) {
  options = options || {};
  var loadT = options.quiet ? null : layer.msg('正在处理...', {icon: 16, time: 0});
  $.post('/plugins/run', {name: 'ha_manager', func: method, args: encodeURIComponent(JSON.stringify(args || {}))}, function(res) {
    if (loadT) layer.close(loadT);
    if (typeof res === 'string') {
      try { res = JSON.parse(res); } catch (e) { res = {status: false, msg: res}; }
    }
    if (!res || !res.status) {
      if (!options.quiet) layer.msg((res && res.msg) || '插件接口请求失败', {icon: 2});
      if (callback) callback(null, res || {});
      return;
    }
    var data = res.data;
    if (typeof data === 'string') {
      try { data = JSON.parse(data); } catch (e2) {}
    }
    if (data && typeof data === 'object' && data.hasOwnProperty('status') && data.hasOwnProperty('msg')) {
      if (!data.status) {
        if (!options.quiet) layer.msg(data.msg || '插件接口请求失败', {icon: 2});
        if (callback) callback(null, data);
        return;
      }
      data = data.data || {};
    }
    if (callback) callback(data, res);
  }, 'json').fail(function() {
    if (loadT) layer.close(loadT);
    if (!options.quiet) layer.msg('插件接口连接失败', {icon: 2});
    if (callback) callback(null, {status: false});
  });
}

function msLoadState(callback) {
  msPost('get_state', {}, function(data) {
    if (data) {
      msState = $.extend(true, msState, data);
      if (data.health) msState.health = data.health;
      if (data.log) msState.log = data.log;
    }
    if (callback) callback();
  });
}

function msSetActive(index) {
  $('.bt-w-menu p').removeClass('bgw');
  $('.bt-w-menu p').eq(index).addClass('bgw');
}

function msHtml(value) {
  value = value == null ? '' : String(value);
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function msPill(status, text) {
  var cls = status === 'normal' ? 'ms-pill-normal' : status === 'warning' ? 'ms-pill-warn' : status === 'danger' ? 'ms-pill-danger' : 'ms-pill-info';
  return '<span class="ms-status-pill ' + cls + '">' + msHtml(text) + '</span>';
}

function msStatusText(status) {
  if (status === 'normal') return '正常';
  if (status === 'warning') return '提醒';
  if (status === 'danger') return '异常';
  return '处理中';
}

var msCheckTemplate = [
  {group: '计划任务', name: '备份数据库', master: '应停用', standby: '应启用'},
  {group: '计划任务', name: 'xtrabackup', master: '应停用', standby: '应启用'},
  {group: '计划任务', name: 'xtrabackup-inc 全量备份', master: '应停用', standby: '应启用'},
  {group: '计划任务', name: 'xtrabackup-inc 增量备份', master: '应停用', standby: '应启用'},
  {group: '计划任务', name: '备份网站配置', master: '应启用', standby: '应停用'},
  {group: '计划任务', name: '备份插件配置', master: '应启用', standby: '应停用'},
  {group: '计划任务', name: '证书续签任务', master: '应启用', standby: '应停用'},
  {group: '计划任务', name: '恢复网站配置', master: '应停用', standby: '应启用'},
  {group: '计划任务', name: '恢复插件配置', master: '应停用', standby: '应启用'},
  {group: 'SSH 同步', name: 'authorized_keys 同步公钥', master: '应未授权', standby: '应授权'},
  {group: 'rsync', name: 'rsyncd 任务', master: '应运行', standby: '应停止'},
  {group: 'rsync', name: '残留 rsync 进程', master: '应停止', standby: '应停止'},
  {group: 'Web 服务', name: 'OpenResty', master: '应运行', standby: '应停止'},
  {group: '监控提醒', name: '主从同步异常提醒', master: '应启用', standby: '应停用'},
  {group: '监控提醒', name: 'Rsync 状态异常提醒', master: '应启用', standby: '应停用'}
];

function msCheckStatusIcon(status) {
  if (status === 'pass') return '<span class="ms-check-icon ms-check-pass" title="正常">✓</span>';
  if (status === 'unknown') return '<span class="ms-check-icon ms-check-unknown" title="未知">?</span>';
  return '<span class="ms-check-icon ms-check-fail" title="异常">✗</span>';
}

function msRoleMark(role, disabled) {
  if (disabled) return '<span class="ms-role-mark ms-role-disabled">未绑定</span>';
  var cls = role === 'master' ? 'ms-role-master' : 'ms-role-standby';
  var text = role === 'master' ? '主' : '备';
  return '<span class="ms-role-mark ' + cls + '">' + text + '</span>';
}

function msHostDot(host) {
  if (host.unbound) return '<span class="ms-host-dot ms-host-dot-unbound" title="未配置主备绑定"></span>';
  if (host.switching) return '<span class="ms-host-dot ms-host-dot-switching" title="正在切换中：' + msHtml(host.switch_step || '等待执行') + '"></span>';
  if (host.online === false) return '<span class="ms-host-dot ms-host-dot-offline" title="插件离线或采集失败"></span>';
  return '<span class="ms-host-dot" title="插件在线"></span>';
}

function msHealthHosts() {
  var localRole = msState.role;
  var peerRole = localRole === 'master' ? 'standby' : 'master';
  var peerBound = msState.bind_test_status === 'success';
  var localName = msState.host_name || msState.host_id || '本机';
  var peerState = msState.peer_state || {};
  var peerName = peerState.host_name || msState.peer_host_name || msState.peer_public_ip || msState.peer_host_id || '对端';
  return [
    {name: localName, role: localRole, current: true, online: true, switching: msState.switch_status === 'waiting_online', switch_step: '等待上线流程', health: msState.health},
    {name: peerName, role: peerState.role || peerRole, current: false, online: peerBound && msState.peer_collect_status !== 'failed', unbound: !peerBound, switching: false, switch_step: '', health: peerState.health_detail || {mysql: {status: 'normal'}, rsync: {status: 'normal'}, openresty: {status: 'normal'}}}
  ];
}

function msBuildHostChecks(host) {
  if (host.health && $.isArray(host.health.script_checks)) {
    return host.health.script_checks;
  }
  var isMaster = host.role === 'master';
  var result = [];
  msCheckTemplate.forEach(function(item) {
    var expected = isMaster ? item.master : item.standby;
    var actual = expected;
    var status = 'pass';
    if (host.unbound) {
      actual = '未配置主备绑定';
      status = 'unknown';
    } else if (host.online === false) {
      actual = '未知（插件离线或采集失败）';
      status = 'unknown';
    } else if (item.name.indexOf('MySQL') !== -1 && host.health.mysql && host.health.mysql.status === 'warning') {
      actual = host.health.mysql.text;
      status = 'fail';
    } else if (item.name.indexOf('OpenResty') !== -1 && host.health.openresty && host.health.openresty.status === 'warning') {
      actual = host.health.openresty.text;
      status = 'fail';
    } else if (item.name.indexOf('rsync') !== -1 && host.health.rsync && host.health.rsync.status === 'warning') {
      actual = host.health.rsync.text;
      status = 'fail';
    }
    result.push({group: item.group, name: item.name, expected: expected, actual: actual, status: status});
  });
  return result;
}

function msCheckHostCard(host) {
  var checks = msBuildHostChecks(host);
  var rows = '';
  var currentGroup = '';
  checks.forEach(function(item) {
    if (item.group !== currentGroup) {
      currentGroup = item.group;
      rows += '<tr class="ms-check-group-row"><td colspan="2">' + msHtml(item.group) + '</td></tr>';
    }
    var matched = item.status === 'pass';
    var actualCls = matched ? 'ms-check-actual-pass' : 'ms-check-actual-fail';
    if (host.unbound) actualCls = '';
    var title = '当前状态: ' + item.actual + '\n期望状态: ' + item.expected;
    rows += '<tr>' +
      '<td class="ms-check-name">' + msHtml(item.name) + '</td>' +
      '<td class="ms-check-actual ' + actualCls + '" title="' + msHtml(title) + '">' + msCheckStatusIcon(matched ? 'pass' : item.status) + msHtml(item.actual) + '</td>' +
    '</tr>';
  });
  var nameCls = host.online === false || host.unbound ? 'ms-host-name ms-host-name-offline' : 'ms-host-name';
  var cardCls = host.unbound ? 'ms-check-card ms-check-card-disabled' : 'ms-check-card';
  var switchingMark = host.switching ? '<span class="ms-loading-state" title="' + msHtml(host.switch_step || '正在切换中') + '"><span class="ms-loading-icon"></span>切换中</span>' : '';
  return '<div class="' + cardCls + '">' +
    '<div class="ms-check-head">' + msHostDot(host) + msRoleMark(host.role, host.unbound) + '<span class="' + nameCls + '">' + msHtml(host.name) + '</span>' + (host.current ? '<span class="ms-current-site-tag">当前</span>' : '') + switchingMark + '</div>' +
    '<table class="table table-hover ms-check-table"><colgroup><col><col class="ms-check-status-col"></colgroup><thead><tr><th>检查项</th><th class="ms-check-status-head">状态</th></tr></thead><tbody>' + rows + '</tbody></table>' +
  '</div>';
}

function msOverview() {
  msSetActive(0);
  var monitorConfigured = !!msState.monitor_url;
  var bindConfigured = msState.bind_test_status === 'success';
  var pluginStatus = 'normal';
  var pluginStatusText = '正常';
  var isSwitching = msState.switch_status === 'waiting_online';
  var roleTitle = '当前角色: ' + msState.role + '\n期望角色: ' + msState.desired_role;
  var switchingTip = '正在切换中\n' + roleTitle;
  var loading = '<span class="ms-loading-state" title="' + msHtml(switchingTip) + '"><span class="ms-loading-icon"></span>切换中</span>';
  var roleCell = '<span title="' + msHtml(roleTitle) + '">' + msRoleMark(msState.role) + '</span>' + (isSwitching ? ' ' + loading : '');
  var html = '<div class="ms-topbar"><div><div class="ms-title">主备管理插件</div><div class="ms-sub">查看本机主备状态，必要时手动发起切换。</div></div><div class="ms-actions"><button class="btn btn-default btn-sm" onclick="msPollMonitor()">轮询云监控</button><button class="btn btn-success btn-sm" onclick="msOpenLocalSwitchDialog()">切换主备</button></div></div>' +
    '<div class="ms-panel"><div class="ms-panel-head"><div class="ms-title">当前状态</div>' + msPill(pluginStatus, pluginStatusText) + '</div><div class="ms-panel-body">' +
      '<table class="table table-hover ms-overview-table"><tbody>' +
        '<tr><th>本机角色</th><td>' + roleCell + '</td><td class="ms-overview-actions" rowspan="4"><button class="btn btn-default btn-sm" onclick="msHealthPanel()">查看自检</button><button class="btn btn-default btn-sm" onclick="msLogPanel()">查看日志</button></td></tr>' +
        '<tr><th>主备关系</th><td>' + msHtml(msState.pair_name) + ' <span class="c7">' + msHtml(msState.pair_id) + '</span></td></tr>' +
        '<tr><th>对端绑定</th><td>' + (bindConfigured ? msPill('normal', '已绑定') + ' <span class="c7">' + msHtml(msState.peer_ssh_user) + '@' + msHtml(msState.peer_public_ip) + ':' + msHtml(msState.peer_ssh_port) + '</span>' : msPill('warning', '未验证') + ' <a class="btlink" href="javascript:;" onclick="msConfigPanel()">去绑定</a>') + '</td></tr>' +
        '<tr><th>云监控</th><td>' + (monitorConfigured ? msPill('normal', '已开启') + ' <span class="c7">最近上报: ' + msHtml(msState.last_report_at) + '</span>' : msPill('warning', '未配置') + ' <a class="btlink" href="javascript:;" onclick="msMonitorPanel()">去配置</a>') + '</td></tr>' +
      '</tbody></table>' +
    '</div></div>';
  $('.soft-man-con').html(html);
}

function msHealthBox(label, item) {
  return '<div class="ms-health"><div class="ms-health-label">' + msHtml(label) + ' ' + msPill(item.status, msStatusText(item.status)) + '</div><div class="ms-health-value" title="' + msHtml(item.text) + '">' + msHtml(item.text) + '</div></div>';
}

function msKeyPanel() {
  msSetActive(1);
  var html = '<div class="bt-form">' +
    '<div class="line"><span class="tname">公钥</span><div class="info-r c4"><textarea class="bt-input-text" readonly name="local_public_key" style="width:520px;height:82px;line-height:22px;background:#f7f8fa;" placeholder="尚未生成"></textarea></div></div>' +
    '<div class="line"><span class="tname">私钥</span><div class="info-r c4"><textarea class="bt-input-text" readonly name="local_private_key" style="width:520px;height:82px;line-height:22px;background:#f7f8fa;" placeholder="尚未生成"></textarea></div></div>' +
    '<div class="line"><span class="tname"></span><div class="info-r">' +
      '<button type="button" class="btn btn-success btn-sm" id="msKeyActionBtn" onclick="return msGenerateLocalKey()">生成密钥</button>' +
      '<button type="button" class="btn btn-default btn-sm ml5" onclick="return msLoadLocalKey()">刷新</button>' +
      '<button type="button" class="btn btn-default btn-sm ml5" onclick="return msCopyLocalPublicKey()">复制公钥</button>' +
      '<span id="msKeyPathTip" style="margin-left:8px;color:#888;font-size:12px;"></span>' +
    '</div></div>' +
  '</div>';
  $('.soft-man-con').html(html);
  msLoadLocalKey();
}

function msConfigPanel() {
  msSetActive(2);
  var testPill = msState.bind_test_status === 'success' ? msPill('normal', 'SSH已通过') : msState.bind_test_status === 'failed' ? msPill('danger', 'SSH失败') : msPill('warning', '未测试');
  var html = '<div class="ms-panel"><div class="ms-panel-head"><div><div class="ms-title">绑定对端江湖面板</div><div class="ms-sub">输入对方机器 IP 和 SSH 信息，测试连接后保存主备关系。</div></div>' + testPill + '</div><div class="ms-panel-body"><form class="bt-form ms-form" id="msConfigForm">' +
    msInput('对方IP', 'peer_public_ip', msState.peer_public_ip, 'width:260px') +
    msInput('SSH端口', 'peer_ssh_port', msState.peer_ssh_port, 'width:120px', 'number') +
    msInput('SSH用户', 'peer_ssh_user', msState.peer_ssh_user, 'width:160px') +
    '<div class="line"><span class="tname">对方公钥</span><div class="info-r">' +
      '<textarea class="bt-input-text" name="peer_public_key" style="width:360px;height:70px" placeholder="粘贴对方机器用于主备同步的 SSH 公钥">' + msHtml(msState.peer_public_key) + '</textarea>' +
      '<div style="margin-top:6px;margin-left: 130px;">' +
        '<button type="button" class="btn btn-default btn-xs" onclick="return msCopyLocalPublicKey()">复制本机公钥</button>' +
        '<span style="margin-left:8px;color:#888;font-size:12px;">把本机公钥复制到对方机器，用于对方回连采集。</span>' +
      '</div>' +
    '</div></div>' +
    '<div class="line"><span class="tname"></span><div class="info-r"><button type="button" class="btn btn-default btn-sm" onclick="msTestPeerSsh()">测试SSH连接</button><button type="button" class="btn btn-success btn-sm ml5" onclick="msSaveConfig()">保存绑定</button></div></div>' +
    '<ul class="help-info-text c7"><li>保存绑定前先确认双方都已交换 SSH 公钥，并通过 SSH 测试对端可达性。</li><li>主备关系ID由插件保存绑定时自动生成，不需要手动填写。</li><li>云监控地址在单独页签配置，默认留空时不会上传主备状态。</li></ul>' +
    '</form></div></div>';
  $('.soft-man-con').html(html);
}

function msInput(label, name, value, style, type) {
  return '<div class="line"><span class="tname">' + msHtml(label) + '</span><div class="info-r c4"><input class="bt-input-text" type="' + (type || 'text') + '" name="' + name + '" value="' + msHtml(value) + '" style="' + style + '" /></div></div>';
}

function msMonitorPanel() {
  msSetActive(3);
  var configured = !!msState.monitor_url;
  var html = '<div class="ms-panel"><div class="ms-panel-head"><div><div class="ms-title">绑定云监控上报配置</div><div class="ms-sub">填写主备关系名称和云监控地址后，插件会把本机和对端状态注册并上报到云监控。</div></div>' + (configured ? msPill('normal', '已开启') : msPill('warning', '未配置')) + '</div><div class="ms-panel-body"><form class="bt-form ms-form" id="msMonitorForm">' +
    msInput('主备关系名称', 'pair_name', msState.pair_name, 'width:260px') +
    msInput('云监控地址', 'monitor_url', msState.monitor_url, 'width:420px') +
    '<div class="line"><span class="tname">轮询/上报</span><div class="info-r c4"><input class="bt-input-text" type="number" name="poll_interval" value="' + msHtml(msState.poll_interval) + '" style="width:80px" /> 秒轮询 <input class="bt-input-text ml10" type="number" name="report_interval" value="' + msHtml(msState.report_interval) + '" style="width:80px" /> 秒上报</div></div>' +
    '<div class="line"><span class="tname">状态</span><div class="info-r c4">' + (configured ? '已配置云监控地址，将按主备关系名称注册并周期上传状态。' : '未配置云监控地址，不上传状态。') + '</div></div>' +
    '<div class="line"><span class="tname"></span><div class="info-r"><button type="button" class="btn btn-default btn-sm" onclick="msTestMonitor()">测试云监控</button><button type="button" class="btn btn-success btn-sm ml5" onclick="msSaveMonitor()">保存并注册</button><button type="button" class="btn btn-warning btn-sm ml5" onclick="msClearMonitor()">清空地址</button></div></div>' +
    '</form></div></div>';
  $('.soft-man-con').html(html);
}

function msCheck(name, label, checked) {
  return '<label class="ms-option-check"><input type="checkbox" name="' + name + '" ' + (checked ? 'checked' : '') + '><span>' + msHtml(label) + '</span></label>';
}

function msHealthPanel() {
  msSetActive(4);
  var cards = msHealthHosts().map(msCheckHostCard).join('');
  var html = '<div class="ms-topbar"><div><div class="ms-title">自检状态</div><div class="ms-sub">基于上下线脚本的每个步骤，检查本机和对端在当前角色下的期望状态是否满足。</div></div><button class="btn btn-default btn-sm" onclick="msRefreshHealth()">重新自检</button></div>' +
    '<div class="ms-check-grid">' + cards + '</div>';
  $('.soft-man-con').html(html);
}

function msLogPanel() {
  msSetActive(5);
  var html = '<div class="ms-topbar"><div><div class="ms-title">切换日志</div><div class="ms-sub">云监控日志文件: ' + msHtml(msState.log_path) + '</div></div><div class="ms-actions"><button class="btn btn-default btn-sm" onclick="msRefreshLog()">刷新日志</button><button class="btn btn-default btn-sm" onclick="msCopyLogPath()">复制路径</button></div></div>' +
    '<div class="ms-log-box" id="msLogBox">' + msHtml(msState.log) + '</div>';
  $('.soft-man-con').html(html);
}

function msReadmePanel() {
  msSetActive(6);
  var html = '<div class="ms-panel"><div class="ms-panel-head"><div class="ms-title">插件说明</div></div><div class="ms-panel-body"><ul class="ms-tip-list">' +
    '<li>本插件第一版只做手动切换，不做自动故障切换。</li>' +
    '<li>绑定时先输入对方机器 IP、SSH 端口、SSH 用户和对方公钥，测试连接后保存主备关系。</li>' +
    '<li>云监控地址在“云监控”页签单独配置，默认留空；留空时不上传主备状态和切换日志。</li>' +
    '<li>插件周期轮询云监控期望状态，领取 offline 或 online 阶段任务。</li>' +
    '<li>切换状态和日志通过 API 上报云监控，日志最终写入 <code>/www/server/jh-monitor/logs/ha_switch/</code>。</li>' +
    '<li>插件首页可以直接发起本机切换：当前为主时切换为备，当前为备时切换为主。</li>' +
    '<li>确认执行前会弹出流程选项框，确认后进入切换日志视图。</li>' +
    '<li>页面数据来自插件本地配置、状态快照和云监控 API。</li>' +
    '</ul></div></div>';
  $('.soft-man-con').html(html);
}

function msPollMonitor() {
  if (!msState.monitor_url) {
    layer.msg('云监控地址为空，当前不会上传状态', {icon: 0});
    return;
  }
  msPost('poll_monitor', {}, function(data) {
    if (data) msState = $.extend(true, msState, data);
    layer.msg('云监控轮询完成', {icon: 1});
    msOverview();
  });
}

function msReadMonitorForm() {
  var data = {};
  $('#msMonitorForm').serializeArray().forEach(function(item) {
    data[item.name] = item.value;
  });
  return data;
}

function msOpenLocalSwitchDialog() {
  msSwitchWizard = {step: 1, targetRole: '', options: $.extend(true, {}, msState.options), prepared: false, prepareRunId: '', prepareLog: ''};
  msSwitchDialogIndex = layer.open({
    type: 1,
    area: ['780px', '560px'],
    title: '切换主备',
    closeBtn: 1,
    shadeClose: false,
    content: '<div id="msSwitchWizardBox" class="ms-switch-wizard"></div>',
    success: function(layero) {
      msRenderSwitchWizard(layero.find('#msSwitchWizardBox'));
    },
    end: function() {
      msSwitchDialogIndex = null;
    }
  });
}

function msConfirmPrepareOnline(targetRole, callback) {
  var targetText = targetRole === 'master' ? '本机' : '对端';
  layer.confirm('确认在目标主机（' + targetText + '）执行预备上线？<br>将按预上线选项执行同步文件、checksum 检查、增量恢复等操作。', {
    icon: 3,
    title: '确认预备上线',
    btn: ['确认执行', '取消']
  }, function(confirmIndex) {
    layer.close(confirmIndex);
    if (callback) callback();
  });
}

function msConfirmFinalizeSwitch(targetRole, callback) {
  var targetText = targetRole === 'master' ? '本机' : '对端';
  layer.confirm('确认执行正式上线并切换主备？<br>将执行目标备用机下线和目标主机（' + targetText + '）正式上线脚本流程', {
    icon: 3,
    title: '确认正式上线',
    btn: ['确认执行', '取消']
  }, function(confirmIndex) {
    layer.close(confirmIndex);
    if (callback) callback();
  });
}

function msSwitchWizardRoot() {
  return msSwitchDialogIndex ? $('#layui-layer' + msSwitchDialogIndex).find('#msSwitchWizardBox') : $('#msSwitchWizardBox');
}

function msBuildWizardSteps() {
  var items = [
    {num: 1, text: '选择主机'},
    {num: 2, text: '预备上线'},
    {num: 3, text: '正式上线'}
  ];
  return '<div class="ms-wizard-steps">' + items.map(function(item) {
    var cls = item.num === msSwitchWizard.step ? 'active' : item.num < msSwitchWizard.step ? 'done' : '';
    return '<div class="ms-wizard-step ' + cls + '"><span class="ms-wizard-step-num">' + item.num + '</span>' + item.text + '</div>';
  }).join('') + '</div>';
}

function msRenderSwitchWizard(root) {
  root = root && root.length ? root : msSwitchWizardRoot();
  if (!root.length) return;
  var body = '';
  var actions = '';
  if (msSwitchWizard.step === 1) {
    body = '<div class="c6 mb10">选择切换完成后作为主机的机器。</div>' + msBuildSwitchHostSelect();
    actions = '<button type="button" class="btn btn-success btn-sm" onclick="msWizardGoOptions()">下一步</button>';
  } else if (msSwitchWizard.step === 2) {
    body = '<div class="c6 mb10">选择预上线要执行的检查和同步动作。</div>' + msBuildSwitchOptionsForm(msSwitchWizard.options || msState.options);
    actions = '<button type="button" class="btn btn-default btn-sm" onclick="msWizardBackHost()">上一步</button><button type="button" class="btn btn-success btn-sm" onclick="msWizardRunPrepare()">开始预上线</button>';
  } else {
    body = msBuildPrepareResultContent(msSwitchWizard.prepareRunId, msSwitchWizard.prepareLog, msSwitchWizard.prepared);
    actions = '<button type="button" class="btn btn-default btn-sm" onclick="msWizardBackOptions()">返回预上线选项</button>' + (msSwitchWizard.prepared ? '<button type="button" class="btn btn-success btn-sm" onclick="msStartFinalizeFromCurrentSwitchDialog()">正式切换</button>' : '');
  }
  root.html(msBuildWizardSteps() + '<div class="ms-wizard-body">' + body + '</div><div class="ms-wizard-actions">' + actions + '</div>');
  msToggleSyncOptions(root);
}

function msWizardGoOptions() {
  var root = msSwitchWizardRoot();
  var targetRole = msSelectedMasterTargetRole(root);
  if (!targetRole) return;
  if (targetRole === msState.role) {
    layer.msg('当前主备关系已符合选择，无需切换', {icon: 0});
    return;
  }
  msSwitchWizard.targetRole = targetRole;
  msSwitchWizard.step = 2;
  msRenderSwitchWizard(root);
}

function msWizardBackHost() {
  msSwitchWizard.step = 1;
  msRenderSwitchWizard();
}

function msWizardBackOptions() {
  msSwitchWizard.step = 2;
  msRenderSwitchWizard();
}

function msWizardRunPrepare() {
  var root = msSwitchWizardRoot();
  var options = msReadLocalSwitchOptions(root);
  msSwitchWizard.options = options;
  msConfirmPrepareOnline(msSwitchWizard.targetRole, function() {
    msPrepareRunLocalSwitch(msSwitchWizard.targetRole, options, 'prepare');
  });
}

function msConfirmPeerTakeover(callback) {
  var peerState = msState.peer_state || {};
  var peerName = peerState.host_name || msState.peer_public_ip || msState.peer_host_id || '对端';
  var content = msSwitchRiskTip() + '<div>确认对端 ' + msHtml(peerName) + ' 已经可以接管业务？<br>确认后会继续执行本机下线并切为备用机。</div>';
  layer.confirm(content, {
    icon: 3,
    title: '确认对端可接管业务',
    btn: ['确认可接管', '取消']
  }, function(confirmIndex) {
    layer.close(confirmIndex);
    if (callback) callback();
  });
}

function msSwitchRiskTip() {
  return '<div class="ms-switch-risk-tip"><span>提示：</span>为减少服务中断时间，请确保程序（JianghuJS、Docker）和配置正确后执行上线操作。</div>';
}

function msSelectedMasterTargetRole(scope) {
  var root = scope && scope.length ? scope : $(document);
  var masterHost = root.find('[name=switch_master_host]:checked').val();
  if (!masterHost) {
    layer.msg('请选择切换后的主机', {icon: 2});
    return '';
  }
  return masterHost === 'local' ? 'master' : 'standby';
}

function msBuildLocalSwitchForm() {
  return '<div class="pd15"><div class="c6 mb10">选择切换完成后作为主机的机器。插件会按选择自动编排两台机器的上线、下线流程。</div>' +
    msBuildSwitchHostSelect() +
    msBuildSwitchOptionsForm(msState.options) +
    '</div>';
}

function msBuildSwitchHostSelect() {
  var localName = msState.host_name || msState.host_id || '本机';
  var peerState = msState.peer_state || {};
  var peerName = peerState.host_name || msState.peer_public_ip || msState.peer_host_id || '对端';
  var defaultMaster = msSwitchWizard.targetRole ? (msSwitchWizard.targetRole === 'master' ? 'local' : 'peer') : (msState.role === 'master' ? 'local' : 'peer');
  return '<div class="ms-switch-hosts">' +
    '<label class="ms-switch-host"><input type="radio" name="switch_master_host" value="local" ' + (defaultMaster === 'local' ? 'checked' : '') + '><span class="ms-switch-host-name">' + msHtml(localName) + '</span><div class="ms-switch-host-meta">设为主机 / 当前角色: ' + msHtml(msState.role) + ' / IP: ' + msHtml(msState.options.local_ip) + '</div></label>' +
    '<label class="ms-switch-host"><input type="radio" name="switch_master_host" value="peer" ' + (defaultMaster === 'peer' ? 'checked' : '') + '><span class="ms-switch-host-name">' + msHtml(peerName) + '</span><div class="ms-switch-host-meta">设为主机 / SSH: ' + msHtml(msState.peer_ssh_user) + '@' + msHtml(msState.peer_public_ip) + ':' + msHtml(msState.peer_ssh_port) + '</div></label>' +
  '</div>';
}

function msBuildSwitchOptionsForm(o) {
  o = o || {};
  return '<form class="bt-form ms-form" id="msLocalSwitchForm">' +
    '<div class="ms-switch-options"><div class="ms-switch-options-title">预上线选项</div>' +
      '<div class="ms-option-grid">' +
      '<label class="ms-option-check"><input type="checkbox" name="sync_files" onchange="msToggleSyncOptions()" ' + (o.sync_files ? 'checked' : '') + '><span>同步文件</span></label>' +
      msCheck('run_checksum', '检查 checksum', o.run_checksum) +
      msCheck('restore_site_setting', '恢复网站配置', o.restore_site_setting) +
      msCheck('restore_plugin_setting', '面板插件配置', o.restore_plugin_setting) +
      msCheck('run_xtrabackup_inc_restore', '执行增量恢复', o.run_xtrabackup_inc_restore) +
      '</div>' +
      '<div class="ms-sync-options ms-sync-group">' +
        '<div class="ms-sync-field"><span>同步目录</span><input class="bt-input-text" type="text" name="sync_file_dirs" value="' + msHtml(o.sync_file_dirs) + '" /></div>' +
        '<div class="ms-sync-field"><span>忽略目录</span><input class="bt-input-text" type="text" name="sync_ignore_dirs" value="' + msHtml(o.sync_ignore_dirs) + '" /></div>' +
      '</div>' +
    '</div>' +
    '</form>';
}

function msReadLocalSwitchOptions(scope) {
  var root = scope && scope.length ? scope : $(document);
  var form = root.find('#msLocalSwitchForm').last();
  var data = $.extend(true, {}, msState.options);
  if (!form.length) return data;
  form.serializeArray().forEach(function(item) { data[item.name] = item.value; });
  ['run_checksum','sync_files','restore_site_setting','restore_plugin_setting','run_xtrabackup_inc_restore'].forEach(function(key) {
    data[key] = form.find('input[type="checkbox"][name="' + key + '"]').prop('checked') === true;
  });
  data.promote_mysql = true;
  msState.options = $.extend(true, {}, msState.options, data);
  return data;
}

function msToggleSyncOptions(scope) {
  var root = scope && scope.length ? scope : $(document);
  var form = root.find('#msLocalSwitchForm').last();
  var checked = form.find('input[type="checkbox"][name="sync_files"]').prop('checked') === true;
  root.find('.ms-sync-options').toggle(checked);
}

function msCreateSwitchRunId() {
  var now = new Date();
  var pad = function(num) { return num < 10 ? '0' + num : String(num); };
  return 'LOCAL_' + now.getFullYear() + pad(now.getMonth() + 1) + pad(now.getDate()) + pad(now.getHours()) + pad(now.getMinutes()) + pad(now.getSeconds());
}

function msStopSwitchLogPolling() {
  if (msSwitchLogTimer) {
    clearInterval(msSwitchLogTimer);
    msSwitchLogTimer = null;
  }
}

function msCloseSwitchLogWindow() {
  if (msSwitchLogLayerIndex !== null) {
    var index = msSwitchLogLayerIndex;
    msSwitchLogLayerIndex = null;
    layer.close(index);
  }
}

function msUpdateSwitchLogWindow(logText, stateText, stateClass) {
  $('#msSwitchLiveLog').text(logText || '正在准备切换任务...');
  $('#msSwitchLiveState').removeClass('ms-live-state-running ms-live-state-success ms-live-state-failed').addClass(stateClass || 'ms-live-state-running').text(stateText || '执行中');
  var box = document.getElementById('msSwitchLiveLog');
  if (box) box.scrollTop = box.scrollHeight;
}

function msRefreshSwitchLogWindow(switchRunId, callback) {
  msPost('read_log', {switch_run_id: switchRunId}, function(data) {
    if (data) {
      msState.log = data.log || '';
      msState.switch_status = data.switch_status || msState.switch_status;
      msUpdateSwitchLogWindow(msState.log, '执行中', 'ms-live-state-running');
      if ($('#msLogBox').length) $('#msLogBox').text(msState.log || '暂无切换日志');
    }
    if (callback) callback(data);
  }, {quiet: true});
}

function msShowSwitchLogWindow(title, switchRunId) {
  msStopSwitchLogPolling();
  var html = '<div class="ms-live-log-wrap">' +
    '<div class="ms-live-log-head"><span id="msSwitchLiveState" class="ms-live-state ms-live-state-running">执行中</span><span class="ms-live-run-id">' + msHtml(switchRunId) + '</span></div>' +
    '<pre id="msSwitchLiveLog" class="ms-live-log-box">正在准备切换任务...</pre>' +
    '<div class="ms-live-log-tip">执行期间请勿重复发起切换；窗口关闭后仍可在“切换日志”页签查看。</div>' +
    '</div>';
  msSwitchLogLayerIndex = layer.open({
    title: title,
    type: 1,
    closeBtn: 2,
    shade: 0.3,
    shadeClose: false,
    area: '760px',
    offset: '20%',
    content: html,
    end: function() {
      msStopSwitchLogPolling();
      msSwitchLogLayerIndex = null;
    }
  });
  msRefreshSwitchLogWindow(switchRunId);
  msSwitchLogTimer = setInterval(function() {
    msRefreshSwitchLogWindow(switchRunId);
  }, 1000);
}

function msFinishSwitchLogWindow(success, msg, switchRunId, keepOpen) {
  msStopSwitchLogPolling();
  msRefreshSwitchLogWindow(switchRunId, function() {
    var text = msg || (success ? '切换执行完成' : '切换执行失败');
    if (keepOpen && success && (msState.log || '').indexOf('checksum 存在差异') !== -1) {
      text = '预备上线完成，checksum 有差异';
    }
    msUpdateSwitchLogWindow(msState.log, text, success ? 'ms-live-state-success' : 'ms-live-state-failed');
    msCloseSwitchLogWindow();
    if (keepOpen) {
      msSwitchWizard.prepared = success;
      msSwitchWizard.prepareRunId = switchRunId;
      msSwitchWizard.prepareLog = msState.log || '';
      msSwitchWizard.step = 3;
      msRenderSwitchWizard();
    }
    layer.msg(text, {icon: success ? 1 : 2, time: success ? 2000 : 0, shade: success ? 0 : 0.3, shadeClose: !success});
  });
}

function msPrepareResultStatusMeta(status) {
  if (status === 'ok') return {text: '完成', cls: 'normal'};
  if (status === 'warning') return {text: '提醒', cls: 'warning'};
  if (status === 'failed') return {text: '失败', cls: 'danger'};
  return {text: '未执行', cls: 'info'};
}

function msParsePrepareResults(logText, success) {
  var names = {
    xtrabackup: '增量恢复',
    checksum: 'checksum 检查',
    sync: 'rsync 同步',
    site_setting: '恢复网站配置',
    plugin_setting: '面板插件配置'
  };
  var order = ['xtrabackup', 'checksum', 'sync', 'site_setting', 'plugin_setting'];
  var rank = {failed: 3, warning: 2, ok: 1, skipped: 0};
  var resultMap = {};
  order.forEach(function(key) { resultMap[key] = {key: key, name: names[key], status: 'skipped', detail: '未执行'}; });
  (logText || '').split('\n').forEach(function(line) {
    var idx = line.indexOf('PREPARE_RESULT ');
    if (idx === -1) return;
    var payload = line.substring(idx + 'PREPARE_RESULT '.length).trim();
    var parts = payload.split(' ');
    var key = parts.shift();
    var status = parts.shift();
    if (!resultMap[key]) return;
    var detail = parts.join(' ') || resultMap[key].detail;
    if (key === 'sync') {
      var current = resultMap[key];
      var details = current.detail && current.detail !== '未执行' ? current.detail.split('<br>') : [];
      details.push(detail);
      resultMap[key] = {key: key, name: names[key], status: (rank[status] > rank[current.status] ? status : current.status), detail: details.join('<br>')};
      return;
    }
    if ((rank[status] || 0) >= (rank[resultMap[key].status] || 0)) {
      resultMap[key] = {key: key, name: names[key], status: status, detail: detail};
    }
  });
  if (!success) {
    resultMap.prepare = {key: 'prepare', name: '预备上线', status: 'failed', detail: '执行失败，请查看切换日志'};
    return [resultMap.prepare].concat(order.map(function(key) { return resultMap[key]; }));
  }
  return order.map(function(key) { return resultMap[key]; });
}

function msBuildPrepareResultContent(switchRunId, logText, success) {
  var resultItems = msParsePrepareResults(logText, success).filter(function(item) {
    return item.status !== 'skipped';
  });
  if (!resultItems.length) {
    resultItems = [{key: 'prepare', name: '预备上线', status: success ? 'ok' : 'failed', detail: success ? '执行完成' : '执行失败，请查看切换日志'}];
  }
  var rows = resultItems.map(function(item) {
    var meta = msPrepareResultStatusMeta(item.status);
    var detailHtml = msHtml(item.detail).replace(/&lt;br&gt;/g, '<br>');
    return '<tr><td>' + msHtml(item.name) + '</td><td>' + msPill(meta.cls, meta.text) + '</td><td>' + detailHtml + '</td></tr>';
  }).join('');
  return '<div><div class="ms-sub mb10">Run ID: ' + msHtml(switchRunId || '') + '</div>' +
    '<table class="table table-hover ms-overview-table"><thead><tr><th>流程</th><th style="width:90px">结果</th><th>说明</th></tr></thead><tbody>' + rows + '</tbody></table>' +
    '<div class="mt10"><a class="btlink" href="javascript:;" onclick="msLogPanel()">查看完整切换日志</a></div></div>';
}

function msShowPrepareResultReport(success, title, switchRunId, logText) {
  var html = '<div class="pd15">' + msBuildPrepareResultContent(switchRunId, logText, success) + '</div>';
  var reportIndex = layer.open({
    type: 1,
    title: '预备上线完成',
    area: '760px',
    closeBtn: 2,
    shadeClose: true,
    btn: success ? ['正式切换', '关闭'] : ['关闭'],
    content: html,
    yes: function(index) {
      if (!success) {
        layer.close(index);
        return;
      }
      layer.close(index);
      msStartFinalizeFromCurrentSwitchDialog();
    },
    success: function() {}
  });
}

function msStartFinalizeFromCurrentSwitchDialog() {
  var scope = msSwitchDialogIndex ? $('#layui-layer' + msSwitchDialogIndex) : $(document);
  var targetRole = msSwitchWizard.targetRole || msSelectedMasterTargetRole(scope);
  if (!targetRole) return;
  var switchOptions = msSwitchWizard.options || msReadLocalSwitchOptions(scope);
  if (targetRole === msState.role) {
    layer.msg('当前主备关系已符合选择，无需切换', {icon: 0});
    return;
  }
  var runFinalize = function() {
    if (msSwitchDialogIndex) {
      layer.close(msSwitchDialogIndex);
      msSwitchDialogIndex = null;
    }
    msPrepareRunLocalSwitch(targetRole, switchOptions, 'finalize');
  };
  if (targetRole === 'standby') {
    msConfirmPeerTakeover(runFinalize);
    return;
  }
  msConfirmFinalizeSwitch(targetRole, runFinalize);
}

function msPrepareRunLocalSwitch(targetRole, options, action) {
  action = action || 'finalize';
  msPost('switch_lock_status', {}, function(lock) {
    if (!lock || !lock.locked) {
      msRunLocalSwitch(targetRole, options, action);
      return;
    }
    var pidText = lock.pid ? ('PID: ' + lock.pid) : '未记录 PID';
    var processText = lock.alive ? '检测到已有切换任务仍在执行。' : '检测到上次切换锁未清理，进程已不存在。';
    layer.confirm(processText + '<br>' + pidText + '<br>是否强制结束并重新执行本次操作？', {icon: 3, title: '已有切换任务正在执行', btn: ['强制结束并执行', '取消']}, function(confirmIndex) {
      layer.close(confirmIndex);
      msPost('force_stop_switch', {}, function(result, res) {
        if (!result) {
          layer.msg((res && res.msg) || '强制结束失败', {icon: 2, time: 0, shade: 0.3, shadeClose: true});
          return;
        }
        layer.msg('已结束旧切换任务，准备重新执行', {icon: 1, time: 1200});
        msRunLocalSwitch(targetRole, options, action);
      });
    });
  });
}

function msRunLocalSwitch(targetRole, options, action) {
  options = $.extend(true, {}, options || msState.options);
  options.promote_mysql = true;
  msDoRunLocalSwitch(targetRole, options, action || 'finalize');
}

function msDoRunLocalSwitch(targetRole, options, action) {
  action = action || 'finalize';
  var switchRunId = msCreateSwitchRunId();
  msState.switch_run_id = switchRunId;
  msState.switch_status = 'running';
  msState.log = '';
  var title = action === 'prepare' ? '正在执行预备上线...' : (targetRole === 'master' ? '正在正式上线为主...' : '正在正式上线为备...');
  var method = action === 'prepare' ? 'prepare_switch' : 'finalize_switch';
  msShowSwitchLogWindow(title, switchRunId);
  msPost(method, {target_role: targetRole, switch_run_id: switchRunId, options: options}, function(data, res) {
    var success = !!data;
    if (data) msState = $.extend(true, msState, data);
    var responseMsg = (res && res.msg) || '';
    if (action !== 'prepare' && !success && (responseMsg.indexOf('CHECKSUM_DIFF_CONFIRM_REQUIRED') !== -1 || (msState.log || '').indexOf('CHECKSUM_DIFF_CONFIRM_REQUIRED') !== -1)) {
      msStopSwitchLogPolling();
      msUpdateSwitchLogWindow(msState.log, '等待确认 checksum 差异', 'ms-live-state-failed');
      msConfirmChecksumDiff(function() {
        msCloseSwitchLogWindow();
        var retryOptions = $.extend(true, {}, options, {checksum_confirmed: true});
        msDoRunLocalSwitch(targetRole, retryOptions, action);
      });
      return;
    }
    var successMsg = action === 'prepare' ? '预备上线完成' : '正式上线完成';
    var failMsg = action === 'prepare' ? '预备上线失败' : '正式上线失败';
    msFinishSwitchLogWindow(success, success ? successMsg : ((res && res.msg) || failMsg), switchRunId, action === 'prepare');
    if (action !== 'prepare') msLogPanel();
  }, {quiet: true});
}

function msConfirmChecksumDiff(callback) {
  layer.confirm('checksum 检查发现差异，是否确认忽略差异并继续本次切换？', {
    icon: 3,
    title: '确认 checksum 差异',
    btn: ['忽略差异并继续', '取消']
  }, function(index) {
    layer.close(index);
    if (callback) callback();
  });
}

function msTestMonitor() {
  var data = msReadMonitorForm();
  if (!data.monitor_url) return layer.msg('云监控地址为空，不测试也不上传', {icon: 0});
  msPost('save_monitor', data, function(result) {
    if (result) msState = $.extend(true, msState, result);
    layer.msg('云监控配置测试完成', {icon: 1});
    msMonitorPanel();
  });
}

function msSaveMonitor() {
  var data = msReadMonitorForm();
  msPost('save_monitor', data, function(result) {
    if (result) msState = $.extend(true, msState, result);
    layer.msg(msState.monitor_url ? '已按主备关系名称注册到云监控' : '地址为空，不上传状态', {icon: msState.monitor_url ? 1 : 0});
    msMonitorPanel();
  });
}

function msClearMonitor() {
  msPost('clear_monitor', {}, function(result) {
    if (result) msState = $.extend(true, msState, result);
    layer.msg('已清空云监控地址，不上传状态', {icon: 0});
    msMonitorPanel();
  });
}

function msTestPeerSsh() {
  var data = msReadConfigForm();
  if (!data.peer_public_ip) return layer.msg('请先填写对方IP', {icon: 2});
  if (!data.peer_public_key) return layer.msg('请先粘贴对方公钥', {icon: 2});
  msPost('test_peer_ssh', data, function(result) {
    if (result) msState = $.extend(true, msState, result);
    layer.msg('SSH连接测试通过', {icon: 1});
    msConfigPanel();
  });
}

function msReadConfigForm() {
  var data = {};
  $('#msConfigForm').serializeArray().forEach(function(item) {
    data[item.name] = item.value;
  });
  return data;
}

function msOpenSwitchConfirm() {
  msOpenLocalSwitchDialog();
}

function msSaveConfig() {
  var data = msReadConfigForm();
  if (!data.peer_public_ip || !data.peer_public_key) {
    return layer.msg('请填写对方IP和对方公钥', {icon: 2});
  }
  msPost('save_binding', data, function(result) {
    if (result) msState = $.extend(true, msState, result);
    layer.msg(msState.bind_test_status === 'success' ? '主备关系已绑定' : '已保存，建议先测试SSH连接', {icon: msState.bind_test_status === 'success' ? 1 : 0});
    msConfigPanel();
  });
}

function msLoadLocalKey() {
  msPost('get_key_info', {}, function(data) {
    msKeyInfo = $.extend(msKeyInfo, data || {});
    $('textarea[name="local_public_key"]').val(msKeyInfo.public_key || '');
    $('textarea[name="local_private_key"]').val(msKeyInfo.private_key || '');
    $('#msKeyActionBtn').text(msKeyInfo.has_private || msKeyInfo.has_public ? '重新生成密钥' : '生成密钥');
    $('#msKeyPathTip').text(msKeyInfo.public_key ? ('公钥路径: ' + (msKeyInfo.public_key_path || '/root/.ssh/id_rsa.pub')) : '未检测到密钥');
  });
  return false;
}

function msGenerateLocalKey() {
  var force = msKeyInfo.has_private || msKeyInfo.has_public;
  var doGenerate = function() {
    msPost('generate_keypair', {force: force ? 1 : 0}, function(data) {
      if (data) {
        msKeyInfo = $.extend(msKeyInfo, data);
        $('textarea[name="local_public_key"]').val(msKeyInfo.public_key || '');
        $('textarea[name="local_private_key"]').val(msKeyInfo.private_key || '');
        $('#msKeyActionBtn').text('重新生成密钥');
        $('#msKeyPathTip').text('公钥路径: ' + (msKeyInfo.public_key_path || '/root/.ssh/id_rsa.pub'));
      }
      layer.msg('密钥已生成', {icon: 1});
    });
  };
  if (force) {
    layer.confirm('重新生成会覆盖 /root/.ssh/id_rsa 和 id_rsa.pub，可能影响已有 SSH 互信，是否继续？', {icon: 3, title: '确认重新生成'}, function(index) {
      layer.close(index);
      doGenerate();
    });
    return false;
  }
  doGenerate();
  return false;
}

function msCopyLocalPublicKey() {
  msPost('get_local_public_key', {}, function(data) {
    var key = data && data.public_key ? data.public_key : '';
    if (!key) {
      layer.msg('本机公钥为空，请先生成本机公钥', {icon: 2});
      return;
    }
    var $temp = $('<textarea>');
    $('body').append($temp);
    $temp.val(key).select();
    try {
      document.execCommand('copy');
      layer.msg('已复制本机公钥', {icon: 1});
    } catch (e) {
      layer.msg('复制失败，请手动复制', {icon: 2});
    }
    $temp.remove();
  });
  return false;
}

function msBuildPairId(peerIp) {
  var source = (msState.host_id || 'local') + '_' + (peerIp || 'peer');
  var hash = 0;
  for (var i = 0; i < source.length; i++) {
    hash = ((hash << 5) - hash) + source.charCodeAt(i);
    hash = hash & hash;
  }
  return 'HA_' + Math.abs(hash).toString(16);
}

function msRefreshHealth() {
  msLoadState(function() {
    layer.msg('自检状态已刷新', {icon: 1});
    msHealthPanel();
  });
}

function msRefreshLog() {
  msPost('read_log', {}, function(data) {
    msState.log = (data && data.log) || '';
    $('#msLogBox').text(msState.log || '暂无切换日志');
    var box = document.getElementById('msLogBox');
    if (box) box.scrollTop = box.scrollHeight;
  });
}

function msCopyLogPath() {
  if (typeof bt !== 'undefined' && bt.copy_pass) {
    bt.copy_pass(msState.log_path);
  } else {
    layer.msg(msState.log_path, {time: 3000});
  }
}
