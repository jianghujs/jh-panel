var msState = {
  monitor_url: '',
  pair_name: '',
  pair_id: '',
  host_id: '',
  peer_host_id: '',
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
    allow_checksum_diff: false,
    sync_files: true,
    sync_file_dirs: '/www/wwwroot,/www/wwwstorage',
    sync_ignore_dirs: 'node_modules,logs,run',
    restore_site_setting: false,
    restore_plugin_setting: false,
    run_xtrabackup_inc_restore: false
  },
  log: ''
};

var msKeyInfo = {public_key: '', has_private: false, has_public: false, public_key_path: '/root/.ssh/id_rsa.pub'};

function msPost(method, args, callback) {
  var loadT = layer.msg('正在处理...', {icon: 16, time: 0});
  $.post('/plugins/run', {name: 'ha_manager', func: method, args: JSON.stringify(args || {})}, function(res) {
    layer.close(loadT);
    if (typeof res === 'string') {
      try { res = JSON.parse(res); } catch (e) { res = {status: false, msg: res}; }
    }
    if (!res || !res.status) {
      layer.msg((res && res.msg) || '插件接口请求失败', {icon: 2});
      if (callback) callback(null, res || {});
      return;
    }
    var data = res.data;
    if (typeof data === 'string') {
      try { data = JSON.parse(data); } catch (e2) {}
    }
    if (data && typeof data === 'object' && data.hasOwnProperty('status') && data.hasOwnProperty('msg')) {
      if (!data.status) {
        layer.msg(data.msg || '插件接口请求失败', {icon: 2});
        if (callback) callback(null, data);
        return;
      }
      data = data.data || {};
    }
    if (callback) callback(data, res);
  }, 'json').fail(function() {
    layer.close(loadT);
    layer.msg('插件接口连接失败', {icon: 2});
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
  {group: '计划任务', name: '备份数据库', master: '已启用', standby: '已启用'},
  {group: '计划任务', name: 'xtrabackup', master: '已启用', standby: '已启用'},
  {group: '计划任务', name: 'xtrabackup-inc 全量备份', master: '已启用', standby: '已启用'},
  {group: '计划任务', name: '恢复网站配置', master: '已关闭', standby: '已启用'},
  {group: '计划任务', name: '恢复插件配置', master: '已关闭', standby: '已启用'},
  {group: '计划任务', name: 'lsyncd 实时同步', master: '运行中', standby: '已停止'},
  {group: '计划任务', name: '证书续签任务', master: '已启用', standby: '已关闭'},
  {group: '监控提醒', name: '主从同步异常提醒', master: '已关闭', standby: '已启用'},
  {group: '监控提醒', name: 'Rsync 状态异常提醒', master: '已关闭', standby: '已启用'},
  {group: 'SSH 同步', name: 'authorized_keys 同步公钥', master: '对端公钥已授权', standby: '对端公钥已授权'},
  {group: 'SSH 同步', name: '对端 SSH 连接', master: '连接正常', standby: '连接正常'},
  {group: 'rsync', name: 'rsyncd 任务', master: '运行中', standby: '已停止'},
  {group: 'rsync', name: '残留 rsync 进程', master: '无残留', standby: '无残留'},
  {group: 'Web 服务', name: 'OpenResty', master: '运行中', standby: '已停止'},
  {group: '数据库', name: 'MySQL 主从状态', master: '无主从配置（作为主）', standby: '作为从库（复制链路正常）'}
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
  return [
    {name: '本机 ' + msState.host_id, role: localRole, current: true, online: true, switching: msState.switch_status === 'waiting_online', switch_step: '等待上线流程', health: msState.health},
    {name: '对端 ' + msState.peer_host_id, role: peerRole, current: false, online: peerBound, unbound: !peerBound, switching: false, switch_step: '', health: {mysql: {status: 'normal'}, rsync: {status: 'normal'}, openresty: {status: 'normal'}}}
  ];
}

function msBuildHostChecks(host) {
  var isMaster = host.role === 'master';
  var result = {};
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
    result[item.name] = {expected: expected, actual: actual, status: status};
  });
  return result;
}

function msCheckHostCard(host) {
  var checks = msBuildHostChecks(host);
  var rows = '';
  var currentGroup = '';
  msCheckTemplate.forEach(function(item) {
    if (item.group !== currentGroup) {
      currentGroup = item.group;
      rows += '<tr class="ms-check-group-row"><td colspan="2">' + msHtml(item.group) + '</td></tr>';
    }
    var check = checks[item.name];
    var matched = check.status === 'pass';
    var actualCls = matched ? 'ms-check-actual-pass' : 'ms-check-actual-fail';
    if (host.unbound) actualCls = '';
    var title = '当前状态: ' + check.actual + '\n期望状态: ' + check.expected;
    rows += '<tr>' +
      '<td class="ms-check-name">' + msHtml(item.name) + '</td>' +
      '<td class="ms-check-actual ' + actualCls + '" title="' + msHtml(title) + '">' + msCheckStatusIcon(matched ? 'pass' : check.status) + msHtml(check.actual) + '</td>' +
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
  var switchStatusText = msState.switch_status === 'waiting_online' ? '等待上线' : msState.switch_status === 'offline_done' ? '下线完成' : msState.switch_status === 'online_done' ? '上线完成' : '无执行中任务';
  var switchStatus = msState.switch_status === 'waiting_online' ? 'warning' : 'normal';
  var isSwitching = msState.switch_status === 'waiting_online';
  var roleTitle = '当前角色: ' + msState.role + '\n期望角色: ' + msState.desired_role;
  var switchingTip = '正在切换中\n' + roleTitle;
  var loading = '<span class="ms-loading-state" title="' + msHtml(switchingTip) + '"><span class="ms-loading-icon"></span>切换中</span>';
  var roleCell = '<span title="' + msHtml(roleTitle) + '">' + msRoleMark(msState.role) + '</span>' + (isSwitching ? ' ' + loading : '');
  var html = '<div class="ms-topbar"><div><div class="ms-title">主备管理插件</div><div class="ms-sub">查看本机主备状态，必要时手动发起切换。</div></div><div class="ms-actions"><button class="btn btn-default btn-sm" onclick="msPollMonitor()">轮询云监控</button><button class="btn btn-success btn-sm" onclick="msOpenLocalSwitchDialog()">切换主备</button></div></div>' +
    '<div class="ms-panel"><div class="ms-panel-head"><div class="ms-title">当前状态</div>' + msPill(switchStatus, switchStatusText) + '</div><div class="ms-panel-body">' +
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
  var targetRole = msState.role === 'master' ? 'standby' : 'master';
  var title = targetRole === 'master' ? '切换为主' : '切换为备';
  layer.open({
    type: 1,
    area: ['750px', targetRole === 'master' ? '560px' : '460px'],
    title: title,
    closeBtn: 1,
    shadeClose: false,
    btn: ['确认执行', '取消'],
    content: msBuildLocalSwitchForm(targetRole),
    success: function() {
      msToggleSyncOptions();
    },
    yes: function(index) {
      if (targetRole === 'standby' && !$('#msOfflineConfirm').is(':checked')) {
        layer.msg('请先确认对端可接管业务', {icon: 2});
        return;
      }
      msRunLocalSwitch(targetRole);
      layer.close(index);
      msLogPanel();
    }
  });
}

function msBuildLocalSwitchForm(targetRole) {
  var hostSelect = '<div class="ms-switch-hosts">' +
    '<label class="ms-switch-host"><input type="radio" name="switch_host" value="local" checked><span class="ms-switch-host-name">本机 ' + msHtml(msState.host_id) + '</span><div class="ms-switch-host-meta">当前: ' + msHtml(msState.role) + ' / IP: ' + msHtml(msState.options.local_ip) + '</div></label>' +
    '<label class="ms-switch-host"><input type="radio" name="switch_host" value="peer"><span class="ms-switch-host-name">对端 ' + msHtml(msState.peer_host_id) + '</span><div class="ms-switch-host-meta">SSH: ' + msHtml(msState.peer_ssh_user) + '@' + msHtml(msState.peer_public_ip) + ':' + msHtml(msState.peer_ssh_port) + '</div></label>' +
  '</div>';
  if (targetRole === 'standby') {
    return '<div class="pd15"><div class="c6 mb10">选择要执行下线流程的主机，将其切换为备用机。</div>' +
      hostSelect +
      '<div class="ms-panel"><div class="ms-panel-body"><ul class="ms-tip-list">' +
      '<li>开启数据库备份、xtrabackup、xtrabackup-inc 全量/增量备份。</li>' +
      '<li>关闭网站配置备份、插件配置备份、lsyncd 实时同步、证书续签任务。</li>' +
      '<li>关闭 rsyncd、清理 rsync 进程、关闭 OpenResty。</li>' +
      '<li>关闭主从同步异常提醒和 Rsync 状态异常提醒。</li>' +
      '</ul></div></div>' +
      '<div class="mtb10"><label><input type="checkbox" id="msOfflineConfirm" checked> 已确认对端可接管业务</label></div>' +
      '</div>';
  }
  var o = msState.options;
  return '<div class="pd15"><div class="c6 mb10">选择要执行上线流程的主机，将其切换为主机。</div>' +
    hostSelect +
    '<form class="bt-form ms-form" id="msLocalSwitchForm">' +
    '<div class="ms-switch-options"><div class="ms-switch-options-title">切换选项</div>' +
      '<div class="ms-option-grid">' +
      '<label class="ms-option-check"><input type="checkbox" name="sync_files" onchange="msToggleSyncOptions()" ' + (o.sync_files ? 'checked' : '') + '><span>同步文件</span></label>' +
      msCheck('run_checksum', '检查 checksum', o.run_checksum) +
      msCheck('allow_checksum_diff', '允许忽略 checksum 差异', o.allow_checksum_diff) +
      msCheck('restore_site_setting', '恢复网站配置', o.restore_site_setting) +
      msCheck('restore_plugin_setting', '面板插件配置', o.restore_plugin_setting) +
      msCheck('run_xtrabackup_inc_restore', '执行增量恢复', o.run_xtrabackup_inc_restore) +
      '</div>' +
      '<div class="ms-sync-options ms-sync-group">' +
        '<div class="ms-sync-field"><span>同步目录</span><input class="bt-input-text" type="text" name="sync_file_dirs" value="' + msHtml(o.sync_file_dirs) + '" /></div>' +
        '<div class="ms-sync-field"><span>忽略目录</span><input class="bt-input-text" type="text" name="sync_ignore_dirs" value="' + msHtml(o.sync_ignore_dirs) + '" /></div>' +
      '</div>' +
    '</div>' +
    '</form></div>';
}

function msToggleSyncOptions() {
  var checked = $('#msLocalSwitchForm [name=sync_files]').is(':checked');
  $('.ms-sync-options').toggle(checked);
}

function msRunLocalSwitch(targetRole) {
  var options = {};
  if (targetRole === 'master') {
    msSaveLocalSwitchOptions();
    options = msState.options;
  }
  msPost('local_switch', {target_role: targetRole, options: options}, function(data) {
    if (data) msState = $.extend(true, msState, data);
    layer.msg('切换执行完成', {icon: 1});
    msLogPanel();
  });
}

function msSaveLocalSwitchOptions() {
  var form = $('#msLocalSwitchForm');
  if (!form.length) return;
  var data = {};
  form.serializeArray().forEach(function(item) { data[item.name] = item.value; });
  ['run_checksum','allow_checksum_diff','sync_files','restore_site_setting','restore_plugin_setting','run_xtrabackup_inc_restore'].forEach(function(key) {
    data[key] = form.find('[name=' + key + ']').is(':checked');
  });
  msState.options = $.extend(msState.options, data);
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
