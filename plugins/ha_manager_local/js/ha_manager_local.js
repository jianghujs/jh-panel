var hmlState = {
  view: 'overview',
  role: 'standby',
  desired_role: 'standby',
  switch_status: 'idle',
  external_closed: false,
  target_role: 'master',
  last_action: '等待操作',
  log: [
    '[21:00:00] UI-only 预览已加载，当前未连接真实后端。',
    '[21:00:02] 本地版只展示本机操作流程，不执行对端 SSH 联动。'
  ],
  steps: [
    {key: 'close_external', name: '关闭对外服务', desc: '停止 OpenResty，阻断主要入口流量。', state: 'pending', action: '关闭 OpenResty', repair: '重新停止 OpenResty'},
    {key: 'task_policy_offline', name: '下线任务调整', desc: '关闭主机外放相关任务，打开恢复/备份类任务。', state: 'pending', action: '调整下线任务', repair: '重试任务调整'},
    {key: 'role_mark_standby', name: '标记为备机', desc: '将当前机器角色改成备机。', state: 'pending', action: '标记备机', repair: '重新写入角色'},
    {key: 'service_policy_standby', name: '应用备机策略', desc: '保持入口关闭，进入备机运行状态。', state: 'pending', action: '应用备机策略', repair: '重试服务策略'},
    {key: 'task_policy_online', name: '上线任务调整', desc: '切到主机后启用网站备份、插件备份和证书任务。', state: 'pending', action: '调整上线任务', repair: '重试任务调整'},
    {key: 'role_mark_master', name: '标记为主机', desc: '将当前机器角色改成主机。', state: 'pending', action: '标记主机', repair: '重新写入角色'},
    {key: 'service_policy_master', name: '应用主机策略', desc: '启动入口服务并恢复对外承载。', state: 'pending', action: '应用主机策略', repair: '重试服务策略'},
    {key: 'quality_check', name: '执行自检', desc: '检查 OpenResty、rsync、计划任务和角色一致性。', state: 'pending', action: '开始自检', repair: '重新自检'}
  ],
  checks: [
    {group: 'Web 服务', name: 'OpenResty', expected: '备机应停止', actual: '运行中', status: 'fail'},
    {group: '计划任务', name: '备份数据库', expected: '备机应启用', actual: '已启用', status: 'pass'},
    {group: '计划任务', name: '备份网站配置', expected: '备机应停用', actual: '已停用', status: 'pass'},
    {group: 'rsync', name: 'rsyncd 任务', expected: '备机应停止', actual: '已停止', status: 'pass'},
    {group: '角色状态', name: '本机角色标记', expected: 'standby', actual: 'standby', status: 'pass'}
  ]
};

function hmlBoot() {
  hmlRender();
}

function hmlCloneSteps() {
  return hmlState.steps.map(function(item) { return $.extend(true, {}, item); });
}

function hmlHtml(value) {
  value = value == null ? '' : String(value);
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function hmlNow() {
  var d = new Date();
  return [d.getHours(), d.getMinutes(), d.getSeconds()].map(function(n) { return n < 10 ? '0' + n : '' + n; }).join(':');
}

function hmlLog(text) {
  hmlState.log.push('[' + hmlNow() + '] ' + text);
  hmlState.last_action = text;
}

function hmlSetView(view) {
  hmlState.view = view;
  hmlRender();
}

function hmlPill(status, text) {
  var cls = status === 'ok' ? 'hml-pill-ok' : status === 'warn' ? 'hml-pill-warn' : status === 'bad' ? 'hml-pill-bad' : 'hml-pill-info';
  return '<span class="hml-pill ' + cls + '">' + hmlHtml(text) + '</span>';
}

function hmlRoleText(role) {
  return role === 'master' ? '主机' : '备机';
}

function hmlStepText(state) {
  if (state === 'done') return hmlPill('ok', '已完成');
  if (state === 'running') return hmlPill('info', '执行中');
  if (state === 'failed') return hmlPill('bad', '失败');
  return hmlPill('warn', '待执行');
}

function hmlCheckStatusIcon(status) {
  if (status === 'pass') return '<span class="hml-check-icon hml-check-pass" title="正常">✓</span>';
  if (status === 'unknown') return '<span class="hml-check-icon hml-check-unknown" title="未知">?</span>';
  return '<span class="hml-check-icon hml-check-fail" title="异常">✗</span>';
}

function hmlRender() {
  $('.bt-w-menu p').removeClass('bgw');
  $('.bt-w-menu p[data-view="' + hmlState.view + '"]').addClass('bgw');
  if (hmlState.view === 'overview') return hmlRenderOverview();
  if (hmlState.view === 'health') return hmlRenderHealth();
  if (hmlState.view === 'log') return hmlRenderLog();
  hmlRenderReadme();
}

function hmlRenderOverview() {
  var failedChecks = hmlState.checks.filter(function(item) { return item.status !== 'pass'; }).length;
  var html = '' +
    '<div class="hml-grid">' +
      '<div class="hml-card"><div class="hml-card-label">当前角色</div><div class="hml-card-value">' + hmlRoleText(hmlState.role) + '</div><div class="hml-card-note">只代表本机状态</div></div>' +
      '<div class="hml-card"><div class="hml-card-label">目标角色</div><div class="hml-card-value">' + hmlRoleText(hmlState.desired_role) + '</div><div class="hml-card-note">可手动切到主或备</div></div>' +
      '<div class="hml-card"><div class="hml-card-label">对外服务</div><div class="hml-card-value">' + (hmlState.external_closed ? '已关闭' : '开放中') + '</div><div class="hml-card-note">OpenResty ' + (hmlState.external_closed ? '已停止' : '运行中') + '</div></div>' +
      '<div class="hml-card"><div class="hml-card-label">自检状态</div><div class="hml-card-value">' + (failedChecks ? '有异常' : '正常') + '</div><div class="hml-card-note">异常项 ' + failedChecks + ' 个</div></div>' +
    '</div>' +
    '<div class="hml-section"><div class="hml-section-body"><div class="hml-step-actions hml-overview-actions" style="margin-top:0;">' +
        '<button class="btn btn-success btn-sm" onclick="hmlOpenSwitchDialog(\'master\')">切为主机</button>' +
        '<button class="btn btn-primary btn-sm" onclick="hmlOpenSwitchDialog(\'standby\')">切为备机</button>' +
        '<button class="btn btn-danger btn-sm" onclick="hmlCloseExternalService()">关闭对外服务</button>' +
        '<button class="btn btn-default btn-sm" onclick="hmlRunHealthCheck()">重新自检</button>' +
      '</div></div></div>';
  $('.soft-man-con').html(html);
}

function hmlOpenSwitchDialog(role) {
  var steps = hmlBuildFlowSteps(role);
  var state = {
    role: hmlState.role,
    desired_role: role,
    target_role: role,
    external_closed: hmlState.external_closed,
    active_step: 0,
    log: []
  };
  state.steps = steps;
  steps[0].state = 'active';
  window.hmlFlowState = state;
  var dialog = layer.open({
    type: 1,
    area: ['900px', '620px'],
    title: '切换流程 - 切到' + hmlRoleText(role),
    closeBtn: 1,
    shadeClose: false,
    content: '<div id="hmlFlowDialog" class="hml-flow-wrap"></div>',
    success: function(layero) {
      hmlRenderFlowDialog(layero.find('#hmlFlowDialog'), state, steps);
    }
  });
  hmlLog('打开切换流程弹框：目标=' + hmlRoleText(role));
  return dialog;
}

function hmlBuildFlowSteps(targetRole) {
  if (targetRole === 'standby') {
    return [
      {key: 'close_external', title: '关闭对外服务', desc: '停止 OpenResty，先阻断主要入口流量。', stage: '准备下线', state: 'pending'},
      {key: 'mysql_running_standby', title: '确保 MySQL 服务正常', desc: '对应旧脚本：恢复为备机前确保 MySQL 正常。', stage: '备机流程', state: 'pending'},
      {key: 'close_mysql_notify', title: '关闭主从同步异常提醒', desc: '对应旧脚本：closeMysqlSlaveNotify。', stage: '备机流程', state: 'pending'},
      {key: 'authorized_key_on', title: '授权同步公钥', desc: '把 standby_sync 公钥加入 authorized_keys。', stage: '备机流程', state: 'pending'},
      {key: 'open_backup_db', title: '开启数据库备份任务', desc: '开启 备份数据库[backupAll]。', stage: '计划任务', state: 'pending'},
      {key: 'open_xtrabackup', title: '开启 xtrabackup 任务', desc: '开启 [勿删]xtrabackup-cron。', stage: '计划任务', state: 'pending'},
      {key: 'open_xtrabackup_full', title: '开启 xtrabackup-inc 全量备份', desc: '开启 [勿删]xtrabackup-inc全量备份。', stage: '计划任务', state: 'pending'},
      {key: 'open_xtrabackup_inc', title: '开启 xtrabackup-inc 增量备份', desc: '开启 [勿删]xtrabackup-inc增量备份。', stage: '计划任务', state: 'pending'},
      {key: 'close_site_backup', title: '关闭网站配置备份', desc: '关闭 备份网站配置[backupAll]。', stage: '计划任务', state: 'pending'},
      {key: 'close_plugin_backup_all', title: '关闭插件配置备份（所有）', desc: '关闭 备份插件配置[所有]。', stage: '计划任务', state: 'pending'},
      {key: 'close_plugin_backup_batch', title: '关闭插件配置备份（backupAll）', desc: '关闭 备份插件配置[backupAll]。', stage: '计划任务', state: 'pending'},
      {key: 'close_lsyncd_cron', title: '关闭 lsyncd 定时同步', desc: '关闭 [勿删]lsyncd实时任务定时同步。', stage: '计划任务', state: 'pending'},
      {key: 'close_cert_cron', title: '关闭证书续签任务', desc: '关闭 [勿删]续签Let\'s Encrypt证书。', stage: '计划任务', state: 'pending'},
      {key: 'open_site_restore', title: '开启网站配置恢复', desc: '开启 恢复网站配置[所有]。', stage: '计划任务', state: 'pending'},
      {key: 'open_plugin_restore', title: '开启插件配置恢复', desc: '开启 恢复插件配置[所有]。', stage: '计划任务', state: 'pending'},
      {key: 'close_ssl_notify', title: '关闭 SSL 到期提醒', desc: '对应旧脚本：setNotifyValue {ssl_cert:-1}。', stage: '通知策略', state: 'pending'},
      {key: 'close_rsync_notify', title: '关闭 Rsync 状态异常提醒', desc: '对应旧脚本：closeRsyncStatusNotify。', stage: '通知策略', state: 'pending'},
      {key: 'disable_rsyncd_tasks', title: '停用 rsyncd 同步任务', desc: '批量调整 rsyncd 任务为 disabled。', stage: '同步服务', state: 'pending'},
      {key: 'stop_lsyncd', title: '停止 lsyncd 服务', desc: '执行 systemctl stop lsyncd。', stage: '同步服务', state: 'pending'},
      {key: 'kill_rsync', title: '清理 rsync 进程', desc: '清理残留 /bin/rsync 进程。', stage: '同步服务', state: 'pending'},
      {key: 'standby_openresty', title: '停止并锁定 OpenResty', desc: '停止 OpenResty，disable 并 mask，必要时停止系统 nginx。', stage: 'Web 服务', state: 'pending'},
      {key: 'role_standby', title: '标记为备机', desc: '把当前机器角色标记成备机。', stage: '角色切换', state: 'pending'},
      {key: 'standby_check', title: '执行备机自检', desc: '确认 OpenResty、rsync 和任务状态符合备机预期。', stage: '状态确认', state: 'pending'}
    ];
  }
  return [
    {key: 'close_external', title: '关闭对外服务', desc: '先停 OpenResty，确保上线准备期间入口收敛。', stage: '准备上线', state: 'pending'},
    {key: 'mysql_prepare', title: '确保 MySQL 服务正常', desc: '对应旧脚本：预上线检查前确保 MySQL 正常。', stage: '预上线', state: 'pending'},
    {key: 'xtrabackup_restore', title: '执行 xtrabackup 增量恢复', desc: '可选项：run_xtrabackup_inc_restore。', stage: '预上线', state: 'pending'},
    {key: 'checksum_check', title: '检查主备 checksum', desc: '可选项：run_checksum，发现差异后需要人工确认。', stage: '预上线', state: 'pending'},
    {key: 'sync_files', title: '同步文件目录', desc: '可选项：sync_files，同步 /www/wwwroot、/www/wwwstorage 等目录。', stage: '预上线', state: 'pending'},
    {key: 'restore_site_setting', title: '恢复网站配置', desc: '可选项：restore_site_setting，导入站点和 Web 配置。', stage: '预上线', state: 'pending'},
    {key: 'restore_plugin_setting', title: '恢复插件配置', desc: '可选项：restore_plugin_setting，恢复插件运行配置。', stage: '预上线', state: 'pending'},
    {key: 'mysql_online', title: '正式上线前确认 MySQL', desc: '对应旧脚本：正式上线前确保 MySQL 正常。', stage: '正式上线', state: 'pending'},
    {key: 'promote_mysql', title: '将数据库提升为主', desc: '执行 switch__mysql_master.js。', stage: '正式上线', state: 'pending'},
    {key: 'authorized_key_off', title: '移除同步公钥授权', desc: '从 authorized_keys 中移除 standby_sync 公钥。', stage: '正式上线', state: 'pending'},
    {key: 'close_backup_db', title: '关闭数据库备份任务', desc: '关闭 备份数据库[backupAll]。', stage: '计划任务', state: 'pending'},
    {key: 'close_xtrabackup', title: '关闭 xtrabackup 任务', desc: '关闭 [勿删]xtrabackup-cron。', stage: '计划任务', state: 'pending'},
    {key: 'close_xtrabackup_full', title: '关闭 xtrabackup-inc 全量备份', desc: '关闭 [勿删]xtrabackup-inc全量备份。', stage: '计划任务', state: 'pending'},
    {key: 'close_xtrabackup_inc', title: '关闭 xtrabackup-inc 增量备份', desc: '关闭 [勿删]xtrabackup-inc增量备份。', stage: '计划任务', state: 'pending'},
    {key: 'open_site_backup', title: '开启网站配置备份', desc: '开启 备份网站配置[backupAll]。', stage: '计划任务', state: 'pending'},
    {key: 'open_plugin_backup_all', title: '开启插件配置备份（所有）', desc: '开启 备份插件配置[所有]。', stage: '计划任务', state: 'pending'},
    {key: 'open_plugin_backup_batch', title: '开启插件配置备份（backupAll）', desc: '开启 备份插件配置[backupAll]。', stage: '计划任务', state: 'pending'},
    {key: 'open_lsyncd_cron', title: '开启 lsyncd 定时同步', desc: '开启 [勿删]lsyncd实时任务定时同步。', stage: '计划任务', state: 'pending'},
    {key: 'open_cert_cron', title: '开启证书续签任务', desc: '开启 [勿删]续签Let\'s Encrypt证书。', stage: '计划任务', state: 'pending'},
    {key: 'close_site_restore', title: '关闭网站配置恢复', desc: '关闭 恢复网站配置[所有]。', stage: '计划任务', state: 'pending'},
    {key: 'close_plugin_restore', title: '关闭插件配置恢复', desc: '关闭 恢复插件配置[所有]。', stage: '计划任务', state: 'pending'},
    {key: 'open_ssl_notify', title: '开启 SSL 到期提醒', desc: '对应旧脚本：setNotifyValue {ssl_cert:14}。', stage: '通知策略', state: 'pending'},
    {key: 'enable_rsyncd_tasks', title: '启用 rsyncd 同步任务', desc: '批量调整 rsyncd 任务为 enabled。', stage: '同步服务', state: 'pending'},
    {key: 'restart_lsyncd', title: '启动 lsyncd 服务', desc: '执行 systemctl restart lsyncd。', stage: '同步服务', state: 'pending'},
    {key: 'master_openresty', title: '启动 OpenResty', desc: '解除 mask、启用自启动、启动 OpenResty，并停止系统 nginx 冲突。', stage: 'Web 服务', state: 'pending'},
    {key: 'open_email_notify', title: '开启邮件通知', desc: '对应旧脚本：openEmailNotify。', stage: '通知策略', state: 'pending'},
    {key: 'open_mysql_notify', title: '开启主从同步异常提醒', desc: '对应旧脚本：openMysqlSlaveNotify。', stage: '通知策略', state: 'pending'},
    {key: 'open_rsync_notify', title: '开启 Rsync 状态异常提醒', desc: '对应旧脚本：openRsyncStatusNotify。', stage: '通知策略', state: 'pending'},
    {key: 'role_master', title: '标记为主机', desc: '把当前机器角色标记成主机。', stage: '角色切换', state: 'pending'},
    {key: 'master_check', title: '执行主机自检', desc: '确认 OpenResty、rsync 和任务状态符合主机预期。', stage: '状态确认', state: 'pending'}
  ];
}

function hmlRenderFlowDialog(root, state, steps) {
  root = root && root.length ? root : $('#hmlFlowDialog');
  if (!root.length) return;
  var activeStep = state.active_step || 0;
  var current = steps[activeStep] || steps[steps.length - 1];
  var list = steps.map(function(step, index) {
    var cls = step.state === 'done' ? 'done' : index === activeStep ? 'active' : '';
    return '<div class="hml-flow-item ' + cls + '" onclick="hmlJumpFlowStep(' + index + ')"><span class="hml-flow-index">' + (step.state === 'done' ? '✓' : (index + 1)) + '</span><div><div class="hml-flow-item-title">' + hmlHtml(step.title) + '</div><div class="hml-flow-item-desc">' + hmlHtml(step.stage) + '</div></div></div>';
  }).join('');
  var html = '<div class="hml-flow-head"><div><div class="hml-flow-title">' + hmlHtml(current.title) + '</div><div class="hml-flow-sub">' + hmlHtml(current.desc) + '</div></div><div>' + hmlPill('info', '弹框流程') + '</div></div>' +
    '<div class="hml-flow-body"><div class="hml-flow-list">' + list + '</div><div class="hml-flow-detail"><div class="hml-flow-detail-title">' + hmlHtml(current.title) + '</div><div class="hml-flow-detail-desc">' + hmlHtml(current.desc) + '</div><div class="hml-flow-stage">阶段：' + hmlHtml(current.stage) + '</div>' +
      '<div class="hml-step-actions">' +
        '<button class="btn btn-success btn-sm" onclick="hmlRunFlowStep()">执行当前步骤</button>' +
        '<button class="btn btn-default btn-sm" onclick="hmlRetryFlowStep()">重试</button>' +
        '<button class="btn btn-warning btn-sm" onclick="hmlRepairFlowStep()">修复</button>' +
        '<button class="btn btn-default btn-sm" onclick="hmlRunFlowAll()">按顺序执行</button>' +
      '</div>' +
      '<div class="hml-tip" style="margin-top:12px;">' +
        '这一步的内容会在后续接入真实执行逻辑；当前先按旧版脚本顺序把流程完整列出来。' +
      '</div>' +
    '</div></div>';
  root.html(html);
}

function hmlJumpFlowStep(index) {
  var state = window.hmlFlowState;
  if (!state) return;
  state.active_step = index;
  hmlRenderFlowDialog($('#hmlFlowDialog'), state, state.steps);
}

function hmlMarkCurrentFlowStep(state, steps, status) {
  var step = steps[state.active_step];
  if (!step) return;
  if (status === 'done') {
    step.state = 'done';
    if (step.key === 'close_external') hmlApplyExternalClosed();
    if (step.key === 'role_standby') hmlApplyRole('standby');
    if (step.key === 'role_master') hmlApplyRole('master');
    if (step.key === 'master_service') hmlState.external_closed = false;
  } else if (status === 'failed') {
    step.state = 'failed';
  } else {
    step.state = 'running';
  }
  if (status === 'done' && state.active_step < steps.length - 1) state.active_step += 1;
  if (status === 'done' && steps.every(function(item) { return item.state === 'done'; })) {
    state.completed = true;
    hmlState.switch_status = 'idle';
  }
}

function hmlRunFlowStep() {
  var state = window.hmlFlowState;
  if (!state) return;
  var steps = state.steps;
  var step = steps[state.active_step];
  if (!step) return;
  hmlMarkCurrentFlowStep(state, steps, 'running');
  hmlRenderFlowDialog($('#hmlFlowDialog'), state, steps);
  setTimeout(function() {
    if (step.key === 'standby_check' || step.key === 'master_check') {
      var failCount = hmlState.checks.filter(function(item) { return item.status !== 'pass'; }).length;
      if (failCount > 0) {
        hmlMarkCurrentFlowStep(state, steps, 'failed');
        hmlLog(step.title + '失败，发现 ' + failCount + ' 个异常项');
      } else {
        hmlMarkCurrentFlowStep(state, steps, 'done');
        hmlLog(step.title + '完成');
      }
    } else {
      hmlMarkCurrentFlowStep(state, steps, 'done');
      if (step.key === 'close_external') hmlCloseExternalService();
      if (step.key === 'offline_task') hmlLog('已按备机流程调整计划任务');
      if (step.key === 'online_task') hmlLog('已按主机流程调整计划任务');
      if (step.key === 'standby_service') hmlLog('已切入备机策略');
      if (step.key === 'master_service') hmlLog('已切入主机策略');
      if (step.key === 'role_standby' || step.key === 'role_master') hmlLog('本机角色已更新');
    }
    hmlRenderFlowDialog($('#hmlFlowDialog'), state, steps);
  }, 450);
}

function hmlRetryFlowStep() {
  var state = window.hmlFlowState;
  if (!state) return;
  hmlLog('重试当前步骤：' + (state.steps[state.active_step] ? state.steps[state.active_step].title : '--'));
  hmlRunFlowStep();
}

function hmlRepairFlowStep() {
  var state = window.hmlFlowState;
  if (!state) return;
  var step = state.steps[state.active_step];
  if (!step) return;
  if (step.key === 'master_check' || step.key === 'standby_check') {
    hmlRunHealthCheck(true);
  }
  if (step.key === 'close_external') {
    hmlApplyExternalClosed();
  }
  step.state = 'pending';
  hmlLog('执行修复：' + step.title);
  hmlRenderFlowDialog($('#hmlFlowDialog'), state, state.steps);
}

function hmlRunFlowAll() {
  var state = window.hmlFlowState;
  if (!state) return;
  function next() {
    if (state.completed || state.active_step >= state.steps.length) return;
    hmlRunFlowStep();
    setTimeout(function() {
      if (!state.completed && state.steps[state.active_step] && state.steps[state.active_step].state !== 'failed') next();
    }, 650);
  }
  next();
}

function hmlCloseExternalService() {
  hmlApplyExternalClosed();
  hmlLog('关闭对外服务完成：OpenResty 已停止');
  layer.msg('已模拟关闭 OpenResty', {icon: 1});
  hmlRender();
}

function hmlApplyExternalClosed() {
  hmlState.external_closed = true;
  hmlState.checks.forEach(function(item) {
    if (item.name === 'OpenResty') {
      item.actual = '已停止';
      item.status = hmlState.role === 'master' ? 'fail' : 'pass';
    }
  });
}

function hmlApplyRole(role) {
  hmlState.role = role;
  hmlState.desired_role = role;
  hmlState.checks.forEach(function(item) {
    if (item.name === '本机角色标记') {
      item.expected = role;
      item.actual = role;
      item.status = 'pass';
    }
    if (item.name === 'OpenResty') {
      item.expected = role === 'master' ? '主机应运行' : '备机应停止';
      item.status = (role === 'master' && !hmlState.external_closed) || (role === 'standby' && hmlState.external_closed) ? 'pass' : 'fail';
    }
  });
}

function hmlRunHealthCheck(fix) {
  if (fix) {
    hmlState.checks.forEach(function(item) { item.status = 'pass'; });
    hmlState.checks.forEach(function(item) { if (item.name === 'OpenResty') item.actual = hmlState.role === 'master' ? '运行中' : '已停止'; });
    hmlLog('修复并重新自检完成');
  } else {
    hmlLog('重新自检完成，发现 ' + hmlState.checks.filter(function(item) { return item.status !== 'pass'; }).length + ' 个异常项');
  }
  layer.msg('自检已刷新（模拟）', {icon: 1});
  hmlSetView('health');
}

function hmlRenderHealth() {
  var hostName = hmlState.role === 'master' ? '本机主机' : '本机备机';
  var hostRole = hmlRoleText(hmlState.role);
  var rows = '';
  var currentGroup = '';
  hmlState.checks.forEach(function(item) {
    if (item.group !== currentGroup) {
      currentGroup = item.group;
      rows += '<tr class="hml-check-group-row"><td colspan="2">' + hmlHtml(item.group) + '</td></tr>';
    }
    var matched = item.status === 'pass';
    var actualCls = matched ? 'hml-check-actual-pass' : 'hml-check-actual-fail';
    var title = '当前状态: ' + item.actual + '\n期望状态: ' + item.expected;
    rows += '<tr>' +
      '<td class="hml-check-name">' + hmlHtml(item.name) + '</td>' +
      '<td class="hml-check-actual ' + actualCls + '" title="' + hmlHtml(title) + '">' + hmlCheckStatusIcon(matched ? 'pass' : item.status) + hmlHtml(item.actual) + '</td>' +
    '</tr>';
  });
  var html = '<div class="hml-section"><div class="hml-section-head"><div><div class="hml-section-title">自检状态</div><div class="hml-section-sub">按本机当前角色计算期望状态。</div></div><button class="btn btn-default btn-sm" onclick="hmlRunHealthCheck()">刷新自检</button></div><div class="hml-section-body"><div class="hml-check-card">' +
    '<div class="hml-check-host-head"><span class="hml-host-dot"></span><span class="hml-role-mark hml-role-' + (hmlState.role === 'master' ? 'master' : 'standby') + '">' + (hmlState.role === 'master' ? '主' : '备') + '</span><span class="hml-check-name">' + hmlHtml(hostName) + '</span><span class="hml-current-site-tag">当前</span><span class="hml-check-state">' + hmlPill(hmlState.checks.some(function(item) { return item.status !== 'pass'; }) ? 'bad' : 'ok', hmlState.checks.some(function(item) { return item.status !== 'pass'; }) ? '存在异常' : '正常') + '</span></div>' +
    '<table class="table table-hover hml-check-table"><colgroup><col><col class="hml-check-status-col"></colgroup><thead><tr><th>检查项</th><th>状态</th></tr></thead><tbody>' + rows + '</tbody></table>' +
  '</div></div></div>';
  $('.soft-man-con').html(html);
}

function hmlRenderLog() {
  $('.soft-man-con').html('<div class="hml-section"><div class="hml-section-head"><div><div class="hml-section-title">操作日志</div><div class="hml-section-sub">UI-only 阶段只记录前端模拟操作。</div></div><button class="btn btn-default btn-sm" onclick="hmlState.log=[];hmlRenderLog()">清空</button></div><div class="hml-section-body"><pre class="hml-log">' + hmlHtml(hmlState.log.join('\n')) + '</pre></div></div>');
}

function hmlRenderReadme() {
  var html = '<div class="hml-section"><div class="hml-section-head"><div><div class="hml-section-title">本地版说明</div><div class="hml-section-sub">用于确认操作体验，后续再接真实后端。</div></div></div><div class="hml-section-body">' +
    '<ul class="hml-muted" style="line-height:28px;margin:0;padding-left:18px;">' +
      '<li>本地版只控制当前机器，不主动连接对端。</li>' +
      '<li>切换主备允许两台机器状态短暂不一致，由操作员自行分开执行。</li>' +
      '<li>关闭对外服务按钮后续会至少停止 OpenResty。</li>' +
      '<li>每个步骤后续都会接真实执行结果、失败指引和修复按钮。</li>' +
    '</ul></div></div>';
  $('.soft-man-con').html(html);
}
