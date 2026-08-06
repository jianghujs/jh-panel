var msState = {
  monitor_url: '',
  pair_name: '生产面板主备',
  pair_id: 'HA_PANEL_CORE',
  host_id: 'H_PANEL_B',
  peer_host_id: 'H_PANEL_A',
  peer_public_ip: '203.0.113.12',
  peer_ssh_port: '10022',
  peer_ssh_user: 'root',
  peer_public_key: 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDmockPeerPublicKey standby-sync@jh-panel-prod-a',
  bind_test_status: 'untested',
  role: 'standby',
  desired_role: 'master',
  poll_interval: 10,
  report_interval: 30,
  last_report_at: '2026-08-05 16:12:08',
  switch_run_id: 'HSR_20260805161000_3f9a',
  switch_status: 'waiting_online',
  log_path: '/www/server/jh-monitor/logs/ha_switch/2026-08/HSR_20260805161000_3f9a.log',
  health: {
    mysql: {status: 'warning', text: '可提升为主，复制延迟 12s'},
    rsync: {status: 'normal', text: 'lsyncd 已停止，rsyncd 待启用'},
    openresty: {status: 'normal', text: '备用机待启动'}
  },
  options: {
    local_ip: '10.0.8.12',
    remote_ip: '10.0.8.11',
    remote_ssh_port: '10022',
    run_checksum: true,
    allow_checksum_diff: false,
    sync_files: true,
    sync_file_dirs: '/www/wwwroot,/www/wwwstorage',
    sync_ignore_dirs: 'node_modules,logs,run',
    restore_site_setting: false,
    restore_plugin_setting: false,
    run_xtrabackup_inc_restore: false
  },
  log: [
    '[2026-08-05 16:10:00] [system] [pending] 云监控创建切换任务 HSR_20260805161000_3f9a',
    '[2026-08-05 16:10:12] [H_PANEL_A] [offline] [success] 旧主机下线流程完成',
    '[2026-08-05 16:11:01] [H_PANEL_B] [online] [waiting] 等待本机插件领取上线阶段'
  ].join('\n')
};

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

function msMockHostChecks(host) {
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
  var checks = msMockHostChecks(host);
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
  return '<div class="' + cardCls + '">' +
    '<div class="ms-check-head">' + msHostDot(host) + msRoleMark(host.role, host.unbound) + '<span class="' + nameCls + '">' + msHtml(host.name) + '</span>' + (host.current ? '<span class="ms-current-site-tag">当前</span>' : '') + '</div>' +
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
  var html = '<div class="ms-topbar"><div><div class="ms-title">主备管理插件</div><div class="ms-sub">查看本机主备状态，必要时手动发起切换。</div></div><div class="ms-actions"><button class="btn btn-default btn-sm" onclick="msMockPoll()">轮询云监控</button><button class="btn btn-success btn-sm" onclick="msOpenLocalSwitchDialog()">切换主备</button></div></div>' +
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

function msConfigPanel() {
  msSetActive(1);
  var testPill = msState.bind_test_status === 'success' ? msPill('normal', 'SSH已通过') : msState.bind_test_status === 'failed' ? msPill('danger', 'SSH失败') : msPill('warning', '未测试');
  var html = '<div class="ms-panel"><div class="ms-panel-head"><div><div class="ms-title">绑定对端江湖面板</div><div class="ms-sub">输入对方机器公网 IP 和 SSH 信息，测试连接后保存主备关系。</div></div>' + testPill + '</div><div class="ms-panel-body"><form class="bt-form ms-form" id="msConfigForm">' +
    msInput('对方公网IP', 'peer_public_ip', msState.peer_public_ip, 'width:260px') +
    msInput('SSH端口', 'peer_ssh_port', msState.peer_ssh_port, 'width:120px', 'number') +
    msInput('SSH用户', 'peer_ssh_user', msState.peer_ssh_user, 'width:160px') +
    '<div class="line"><span class="tname">对方公钥</span><div class="info-r c4"><textarea class="bt-input-text" name="peer_public_key" style="width:520px;height:92px;line-height:22px" placeholder="粘贴对方机器用于主备同步的 SSH 公钥">' + msHtml(msState.peer_public_key) + '</textarea></div></div>' +
    '<div class="line"><span class="tname"></span><div class="info-r"><button type="button" class="btn btn-default btn-sm" onclick="msTestPeerSshMock()">测试SSH连接</button><button type="button" class="btn btn-success btn-sm ml5" onclick="msSaveConfigMock()">保存绑定</button></div></div>' +
    '<ul class="help-info-text c7"><li>真实实现时会把对方公钥写入本机授权配置，并通过 SSH 测试对端可达性。</li><li>主备关系ID由插件保存绑定时自动生成，不需要手动填写。</li><li>云监控地址在单独页签配置，默认留空时不会上传主备状态。</li></ul>' +
    '</form></div></div>';
  $('.soft-man-con').html(html);
}

function msInput(label, name, value, style, type) {
  return '<div class="line"><span class="tname">' + msHtml(label) + '</span><div class="info-r c4"><input class="bt-input-text" type="' + (type || 'text') + '" name="' + name + '" value="' + msHtml(value) + '" style="' + style + '" /></div></div>';
}

function msMonitorPanel() {
  msSetActive(2);
  var configured = !!msState.monitor_url;
  var html = '<div class="ms-panel"><div class="ms-panel-head"><div><div class="ms-title">绑定云监控上报配置</div><div class="ms-sub">填写主备关系名称和云监控地址后，插件会把本机和对端状态注册并上报到云监控。</div></div>' + (configured ? msPill('normal', '已开启') : msPill('warning', '未配置')) + '</div><div class="ms-panel-body"><form class="bt-form ms-form" id="msMonitorForm">' +
    msInput('主备关系名称', 'pair_name', msState.pair_name, 'width:260px') +
    msInput('云监控地址', 'monitor_url', msState.monitor_url, 'width:420px') +
    '<div class="line"><span class="tname">轮询/上报</span><div class="info-r c4"><input class="bt-input-text" type="number" name="poll_interval" value="' + msHtml(msState.poll_interval) + '" style="width:80px" /> 秒轮询 <input class="bt-input-text ml10" type="number" name="report_interval" value="' + msHtml(msState.report_interval) + '" style="width:80px" /> 秒上报</div></div>' +
    '<div class="line"><span class="tname">状态</span><div class="info-r c4">' + (configured ? '已配置云监控地址，将按主备关系名称注册并周期上传状态。' : '未配置云监控地址，不上传状态。') + '</div></div>' +
    '<div class="line"><span class="tname"></span><div class="info-r"><button type="button" class="btn btn-default btn-sm" onclick="msTestMonitorMock()">测试云监控</button><button type="button" class="btn btn-success btn-sm ml5" onclick="msSaveMonitorMock()">保存并注册</button><button type="button" class="btn btn-warning btn-sm ml5" onclick="msClearMonitorMock()">清空地址</button></div></div>' +
    '</form></div></div>';
  $('.soft-man-con').html(html);
}

function msCheck(name, label, checked) {
  return '<label class="ms-option-check"><input type="checkbox" name="' + name + '" ' + (checked ? 'checked' : '') + '><span>' + msHtml(label) + '</span></label>';
}

function msHealthPanel() {
  msSetActive(3);
  var cards = msHealthHosts().map(msCheckHostCard).join('');
  var html = '<div class="ms-topbar"><div><div class="ms-title">自检状态</div><div class="ms-sub">基于上下线脚本的每个步骤，检查本机和对端在当前角色下的期望状态是否满足。</div></div><button class="btn btn-default btn-sm" onclick="msRefreshHealthMock()">重新自检</button></div>' +
    '<div class="ms-check-grid">' + cards + '</div>';
  $('.soft-man-con').html(html);
}

function msLogPanel() {
  msSetActive(4);
  var html = '<div class="ms-topbar"><div><div class="ms-title">切换日志</div><div class="ms-sub">云监控日志文件: ' + msHtml(msState.log_path) + '</div></div><div class="ms-actions"><button class="btn btn-default btn-sm" onclick="msAppendLogMock()">模拟追加</button><button class="btn btn-default btn-sm" onclick="msCopyLogPath()">复制路径</button></div></div>' +
    '<div class="ms-log-box" id="msLogBox">' + msHtml(msState.log) + '</div>';
  $('.soft-man-con').html(html);
}

function msReadmePanel() {
  msSetActive(5);
  var html = '<div class="ms-panel"><div class="ms-panel-head"><div class="ms-title">插件说明</div></div><div class="ms-panel-body"><ul class="ms-tip-list">' +
    '<li>本插件第一版只做手动切换，不做自动故障切换。</li>' +
    '<li>绑定时先输入对方机器公网 IP、SSH 端口、SSH 用户和对方公钥，测试连接后保存主备关系。</li>' +
    '<li>云监控地址在“云监控”页签单独配置，默认留空；留空时不上传主备状态和切换日志。</li>' +
    '<li>插件周期轮询云监控期望状态，领取 offline 或 online 阶段任务。</li>' +
    '<li>切换状态和日志通过 API 上报云监控，日志最终写入 <code>/www/server/jh-monitor/logs/ha_switch/</code>。</li>' +
    '<li>插件首页可以直接发起本机切换：当前为主时切换为备，当前为备时切换为主。</li>' +
    '<li>确认执行前会弹出流程选项框，确认后进入切换日志视图。</li>' +
    '<li>当前页面为 UI-only 预览，后续由后端实现真实配置保存、签名、轮询和执行器。</li>' +
    '</ul></div></div>';
  $('.soft-man-con').html(html);
}

function msMockPoll() {
  if (!msState.monitor_url) {
    layer.msg('云监控地址为空，当前不会上传状态', {icon: 0});
    return;
  }
  msState.last_report_at = '2026-08-05 16:15:00';
  layer.msg('UI 预览：云监控连接正常，发现待执行上线阶段', {icon: 1});
  msOverview();
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
      msRunLocalSwitchMock(targetRole);
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
  return '<div class="pd15"><div class="c6 mb10">选择要执行上线流程的主机，将其切换为主机。以下选项仅为 UI 预览。</div>' +
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

function msRunLocalSwitchMock(targetRole) {
  if (targetRole === 'master') {
    msSaveLocalSwitchOptionsMock();
    msState.role = 'master';
    msState.desired_role = 'master';
    msState.switch_status = 'online_done';
    msState.log += '\n[2026-08-05 16:18:00] [local] [online] [running] 本机发起切换为主';
    msState.log += '\n[2026-08-05 16:18:03] [local] [online] [running] 执行 checksum / 同步文件 / 提升数据库为主';
    msState.log += '\n[2026-08-05 16:18:15] [local] [online] [success] UI 预览：本机已切换为主';
    layer.msg('UI 预览：已执行切换为主', {icon: 1});
    return;
  }
  msState.role = 'standby';
  msState.desired_role = 'standby';
  msState.switch_status = 'offline_done';
  msState.log += '\n[2026-08-05 16:18:00] [local] [offline] [running] 本机发起切换为备';
  msState.log += '\n[2026-08-05 16:18:06] [local] [offline] [running] 调整计划任务、关闭 rsyncd、关闭 OpenResty';
  msState.log += '\n[2026-08-05 16:18:12] [local] [offline] [success] UI 预览：本机已切换为备';
  layer.msg('UI 预览：已执行切换为备', {icon: 1});
}

function msSaveLocalSwitchOptionsMock() {
  var form = $('#msLocalSwitchForm');
  if (!form.length) return;
  var data = {};
  form.serializeArray().forEach(function(item) { data[item.name] = item.value; });
  ['run_checksum','allow_checksum_diff','sync_files','restore_site_setting','restore_plugin_setting','run_xtrabackup_inc_restore'].forEach(function(key) {
    data[key] = form.find('[name=' + key + ']').is(':checked');
  });
  msState.options = $.extend(msState.options, data);
}

function msTestMonitorMock() {
  var data = msReadMonitorForm();
  if (!data.monitor_url) return layer.msg('云监控地址为空，不测试也不上传', {icon: 0});
  layer.msg('UI 预览：云监控连接测试通过', {icon: 1});
}

function msSaveMonitorMock() {
  var data = msReadMonitorForm();
  msState.pair_name = data.pair_name || msState.pair_name;
  msState.monitor_url = data.monitor_url || '';
  msState.poll_interval = data.poll_interval || msState.poll_interval;
  msState.report_interval = data.report_interval || msState.report_interval;
  layer.msg(msState.monitor_url ? 'UI 预览：已按主备关系名称注册到云监控' : 'UI 预览：地址为空，不上传状态', {icon: msState.monitor_url ? 1 : 0});
  msMonitorPanel();
}

function msClearMonitorMock() {
  msState.monitor_url = '';
  layer.msg('UI 预览：已清空云监控地址，不上传状态', {icon: 0});
  msMonitorPanel();
}

function msTestPeerSshMock() {
  var data = msReadConfigForm();
  if (!data.peer_public_ip) return layer.msg('请先填写对方公网IP', {icon: 2});
  if (!data.peer_public_key) return layer.msg('请先粘贴对方公钥', {icon: 2});
  msState.bind_test_status = 'success';
  msState.peer_public_ip = data.peer_public_ip;
  msState.peer_ssh_port = data.peer_ssh_port || '22';
  msState.peer_ssh_user = data.peer_ssh_user || 'root';
  msState.peer_public_key = data.peer_public_key;
  msState.log += '\n[2026-08-05 16:16:00] [bind] [success] UI 预览：SSH连接测试通过 ' + msState.peer_ssh_user + '@' + msState.peer_public_ip + ':' + msState.peer_ssh_port;
  layer.msg('UI 预览：SSH连接测试通过', {icon: 1});
  msConfigPanel();
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

function msSaveConfigMock() {
  var data = msReadConfigForm();
  if (!data.peer_public_ip || !data.peer_public_key) {
    return layer.msg('请填写对方公网IP和对方公钥', {icon: 2});
  }
  msState = $.extend(msState, data);
  msState.pair_id = msState.pair_id || msBuildPairId(msState.peer_public_ip);
  if (msState.bind_test_status !== 'success') {
    msState.bind_test_status = 'untested';
    layer.msg('UI 预览：已保存，建议先测试SSH连接', {icon: 0});
  } else {
    layer.msg('UI 预览：主备关系已绑定', {icon: 1});
  }
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

function msRefreshHealthMock() {
  layer.msg('UI 预览：自检完成，mysql 仍为提醒状态', {icon: 1});
  msHealthPanel();
}

function msAppendLogMock() {
  msState.log += '\n[2026-08-05 16:15:30] [H_PANEL_B] [online] [running] UI 预览：追加一条切换日志';
  $('#msLogBox').text(msState.log);
  var box = document.getElementById('msLogBox');
  if (box) box.scrollTop = box.scrollHeight;
}

function msCopyLogPath() {
  if (typeof bt !== 'undefined' && bt.copy_pass) {
    bt.copy_pass(msState.log_path);
  } else {
    layer.msg(msState.log_path, {time: 3000});
  }
}
