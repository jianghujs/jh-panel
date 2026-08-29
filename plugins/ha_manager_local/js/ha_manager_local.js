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
        '<button class="btn btn-success btn-sm" onclick="hmlOpenSwitchDialog()">切换角色</button>' +
        '<button class="btn btn-danger btn-sm" onclick="hmlCloseExternalService()">关闭对外服务</button>' +
        '<button class="btn btn-default btn-sm" onclick="hmlRunHealthCheck()">重新自检</button>' +
      '</div></div></div>';
  $('.soft-man-con').html(html);
}

function hmlOpenSwitchDialog() {
  var defaultRole = hmlState.role === 'master' ? 'standby' : 'master';
  var state = {
    role: hmlState.role,
    desired_role: defaultRole,
    target_role: defaultRole,
    external_closed: hmlState.external_closed,
    active_step: -1,
    focus_step: 0,
    auto_running: false,
    running: false,
    flow_timer: null,
    log: []
  };
  state.steps = hmlBuildFlowSteps(defaultRole);
  state.role_selected = false;
  window.hmlFlowState = state;
  var dialog = layer.open({
    type: 1,
    area: ['900px', '620px'],
    title: '切换流程',
    closeBtn: 1,
    shadeClose: false,
    content: '<div id="hmlFlowDialog" class="hml-flow-wrap" style="height:552px; min-height: 552px;"></div>',
    success: function(layero) {
      hmlRenderFlowDialog(layero.find('#hmlFlowDialog'), state, state.steps);
    }
  });
  state.layer_id = dialog;
  hmlLog('打开切换流程弹框：目标=' + hmlRoleText(defaultRole));
  return dialog;
}

function hmlFlowNextText(role) {
  if (role === 'standby') return '备机下线完成，请回到主机执行正式上线流程。';
  return '主机正式上线完成。';
}

function hmlBuildFlowStages(state) {
  if (!state || state.target_role === 'standby') {
    return [{key: 'standby_offline', text: '备机下线'}];
  }
  return [
    {key: 'master_prepare', text: '主机预上线'},
    {key: 'standby_offline', text: '备机下线'},
    {key: 'master_online', text: '主机正式上线'}
  ];
}

function hmlFlowStageKey(step) {
  if (!step) return '';
  if (step.key === 'wait_standby_offline') return 'standby_offline';
  if (step.stage === '主机预上线') return 'master_prepare';
  if (step.stage === '备机下线' || step.stage === '准备下线' || step.stage === '备机流程') return 'standby_offline';
  return 'master_online';
}

function hmlBuildFlowStageBar(state, steps, activeStep) {
  var stages = hmlBuildFlowStages(state);
  return '<div class="hml-flow-stages">' + stages.map(function(stage) {
    var indices = [];
    steps.forEach(function(step, index) {
      if (state.target_role === 'standby' || hmlFlowStageKey(step) === stage.key) indices.push(index);
    });
    var done = hmlIsFlowStageReadyForNext(state, stage.key);
    var active = indices.indexOf(activeStep) !== -1;
    var cls = done ? 'done' : active ? 'active' : '';
    return '<div class="hml-flow-stage-step ' + cls + '" onclick="hmlJumpFlowStage(\'' + stage.key + '\')"><span class="hml-flow-stage-num">' + (done ? '✓' : '') + '</span>' + hmlHtml(stage.text) + '</div>';
  }).join('') + '</div>';
}

function hmlMasterPrepareSteps() {
  return hmlWithPhase([
    {key: 'close_external', title: '关闭对外服务', desc: '先停 OpenResty，确保上线准备期间入口收敛。', stage: '主机预上线', state: 'pending', required: true},
    {key: 'mysql_prepare', title: '确保 MySQL 服务正常', desc: '对应旧脚本：预上线检查前确保 MySQL 正常。', stage: '主机预上线', state: 'pending', required: true},
    {key: 'xtrabackup_restore', title: '执行 xtrabackup 增量恢复', desc: '可选项：run_xtrabackup_inc_restore。', stage: '主机预上线', state: 'pending', required: false},
    {key: 'async_dryrun_check', title: '检查文件一致性', desc: '参考 rsyncd 预检查只检查 /www/wwwstorage 相关同步任务。', stage: '主机预上线', state: 'pending', required: true},
    {key: 'checksum_check', title: '检查主备 checksum', desc: '可选项：run_checksum，发现差异后需要人工确认。', stage: '主机预上线', state: 'pending', required: false},
    {key: 'sync_files', title: '同步文件目录', desc: '可选项：sync_files，同步 /www/wwwroot、/www/wwwstorage 等目录。', stage: '主机预上线', state: 'pending', required: false},
    {key: 'restore_site_setting', title: '恢复网站配置', desc: '可选项：restore_site_setting，导入站点和 Web 配置。', stage: '主机预上线', state: 'pending', required: false},
    {key: 'restore_plugin_setting', title: '恢复插件配置', desc: '可选项：restore_plugin_setting，恢复插件运行配置。', stage: '主机预上线', state: 'pending', required: false}
  ], 'master_prepare');
}

function hmlMasterOnlineSteps() {
  return hmlWithPhase([
    {key: 'mysql_online', title: '正式上线前确认 MySQL', desc: '对应旧脚本：正式上线前确保 MySQL 正常。', stage: '主机正式上线', state: 'pending'},
    {key: 'promote_mysql', title: '将数据库提升为主', desc: '执行 switch__mysql_master.js。', stage: '主机正式上线', state: 'pending'},
    {key: 'authorized_key_off', title: '移除同步公钥授权', desc: '从 authorized_keys 中移除 standby_sync 公钥。', stage: '主机正式上线', state: 'pending'},
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
  ], 'master_online');
}

function hmlBuildFlowSteps(role) {
  if (role === 'master') {
    return hmlMasterPrepareSteps().concat([
      {key: 'wait_standby_offline', title: '等待备机下线', desc: '主机预上线完成，请到备用机执行下线流程；备用机下线完成后，再回到这里执行主机正式上线。', stage: '备机下线', state: 'pending', guide: true, phase: 'standby_offline'}
    ], hmlMasterOnlineSteps());
  }
  if (role === 'standby') {
    return hmlWithPhase([
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
    ], 'standby_offline');
  }
  return hmlMasterPrepareSteps();
}

function hmlWithPhase(list, phase) {
  return list.map(function(item) {
    return $.extend(true, {}, item, {phase: phase});
  });
}

function hmlGetVisibleFlowSteps(state, steps) {
  steps = steps || [];
  if (!state || !steps.length) return steps;
  var phase = hmlGetFlowPhase(state);
  if (!phase) return steps;
  var visible = steps.filter(function(step) {
    return (step.phase || '') === phase;
  });
  return visible.length ? visible : steps;
}

function hmlStepRequiredLabel(step) {
  if (!step || step.phase !== 'master_prepare') return '';
  return step.required === false ? '可选' : '必选';
}

function hmlStepBadgeHtml(step) {
  var label = hmlStepRequiredLabel(step);
  if (!label) return '';
  var cls = label === '必选' ? 'hml-step-flag-required' : 'hml-step-flag-optional';
  return '<span class="hml-step-flag ' + cls + '">' + label + '</span>';
}

function hmlRenderFlowDialog(root, state, steps) {
  root = root && root.length ? root : $('#hmlFlowDialog');
  if (!root.length) return;
  var activeStep = state.active_step < 0 ? 0 : state.active_step;
  var current = steps[activeStep] || steps[steps.length - 1];
  var previousScrollTop = state.list_scroll_top || 0;
  var currentIsGuide = current && current.guide;
  var visibleSteps = hmlGetVisibleFlowSteps(state, steps);
  var list = visibleSteps.map(function(step, index) {
    var stepIndex = steps.indexOf(step);
    if (stepIndex < 0) stepIndex = index;
    var cls = step.state === 'done' ? 'done' : stepIndex === activeStep ? 'active' : '';
    var undo = step.state === 'done' ? '<button class="btn btn-default btn-xs hml-flow-undo" onclick="hmlUndoFlowStep(' + stepIndex + ', event)">撤销</button>' : '';
    return '<div class="hml-flow-item ' + cls + '" data-step-index="' + stepIndex + '" onclick="hmlJumpFlowStep(' + stepIndex + ')"><span class="hml-flow-index">' + (step.state === 'done' ? '✓' : (index + 1)) + '</span><div class="hml-flow-item-main"><div class="hml-flow-item-title">' + hmlHtml(step.title) + hmlStepBadgeHtml(step) + '</div><div class="hml-flow-item-desc">' + hmlHtml(step.stage) + '</div></div>' + undo + '</div>';
  }).join('');
  if (!state.role_selected) {
    var role = state.target_role || 'master';
    var html = '<div class="hml-flow-head"><div><div class="hml-flow-title">选择角色</div><div class="hml-flow-sub">先选择切换后的角色，再进入后续流程。</div></div></div>' +
      '<div class="hml-role-select">' +
        '<div class="hml-role-option ' + (role === 'master' ? 'active' : '') + '" onclick="hmlPickFlowRole(\'master\')"><div class="hml-role-option-title">主机</div><div class="hml-role-option-desc">把当前机器切到主机流程。</div></div>' +
        '<div class="hml-role-option ' + (role === 'standby' ? 'active' : '') + '" onclick="hmlPickFlowRole(\'standby\')"><div class="hml-role-option-title">备机</div><div class="hml-role-option-desc">把当前机器切到备机流程。</div></div>' +
      '</div>' +
      '<div class="hml-step-actions" style="margin-top:12px;">' +
        '<button class="btn btn-success btn-sm" onclick="hmlConfirmFlowRole()">继续</button>' +
      '</div>';
    root.html(html);
    return;
  }
  if (currentIsGuide) {
    var guideHtml = hmlBuildFlowStageBar(state, steps, activeStep) +
      '<div class="hml-flow-guide"><div class="hml-flow-guide-text">' + hmlHtml(current.desc) + '</div></div>' +
      '<div class="hml-flow-footer"><button class="btn btn-default btn-sm" onclick="hmlCancelFlowDialog()">取消</button><button class="btn btn-default btn-sm" onclick="hmlStepBack()"' + (hmlCanGoPrevFlowPhase(state) ? '' : ' disabled') + '>上一步</button><button class="btn btn-success btn-sm" onclick="hmlToggleFlowAuto()">' + hmlFlowNextButtonText(state) + '</button></div>';
    root.html(guideHtml);
    return;
  }
  var html = hmlBuildFlowStageBar(state, steps, activeStep) + '<div class="hml-flow-head"><div><div class="hml-flow-title">' + hmlHtml(current.title) + '</div><div class="hml-flow-sub">' + hmlHtml(current.desc) + '</div></div></div>' +
    '<div class="hml-flow-body"><div class="hml-flow-list">' + list + '</div><div class="hml-flow-detail"><div class="hml-flow-detail-title">' + hmlHtml(current.title) + '</div><div class="hml-flow-detail-desc">' + hmlHtml(current.desc) + '</div><div class="hml-flow-stage">阶段：' + hmlHtml(current.stage) + '</div>' +
      (hmlStepRequiredLabel(current) ? '<div class="hml-flow-stage">类型：' + hmlStepRequiredLabel(current) + '</div>' : '') +
      (current.state === 'failed' ? '<div class="hml-flow-error"><div class="hml-flow-error-title">异常处理指引</div><div class="hml-flow-error-text">当前步骤执行失败，请先查看日志输出，再按提示处理后重新进入该步骤。\n如果是依赖项异常，先恢复依赖服务；如果是配置异常，先修正配置再重试。</div></div>' : '') +
      '<div class="hml-step-actions">' +
        '<button class="btn btn-success btn-sm" onclick="hmlRunFlowStepWithCode()">执行当前操作</button>' +
      '</div>' +
    '</div></div>' +
    '<div class="hml-flow-footer"><button class="btn btn-default btn-sm" onclick="hmlCancelFlowDialog()">取消</button><button class="btn btn-default btn-sm" onclick="hmlStepBack()"' + (hmlCanGoPrevFlowPhase(state) ? '' : ' disabled') + '>上一步</button><button class="btn btn-success btn-sm" onclick="hmlToggleFlowAuto()">' + hmlFlowNextButtonText(state) + '</button></div>';
  root.html(html);
  var listEl = $('#hmlFlowDialog .hml-flow-list')[0];
  if (listEl) listEl.scrollTop = previousScrollTop;
  if (state.auto_running || state.running || state.just_stepped) {
    setTimeout(function() {
      hmlCenterFlowStep(typeof state.focus_step === 'number' ? state.focus_step : activeStep);
    }, 0);
  }
  state.just_stepped = false;
}

function hmlPickFlowRole(role) {
  var state = window.hmlFlowState;
  if (!state) return;
  state.target_role = role;
  state.desired_role = role;
  state.steps = hmlBuildFlowSteps(role);
  state.active_step = -1;
  state.focus_step = 0;
  state.auto_running = false;
  hmlRenderFlowDialog($('#hmlFlowDialog'), state, state.steps);
}

function hmlConfirmFlowRole() {
  var state = window.hmlFlowState;
  if (!state) return;
  state.steps = hmlBuildFlowSteps(state.target_role || 'master');
  state.active_step = 0;
  state.focus_step = 0;
  state.role_selected = true;
  state.completed = false;
  state.prompted_next = false;
  hmlRenderFlowDialog($('#hmlFlowDialog'), state, state.steps);
}

function hmlJumpFlowStep(index) {
  var state = window.hmlFlowState;
  if (!state) return;
  var listEl = $('#hmlFlowDialog .hml-flow-list')[0];
  state.list_scroll_top = listEl ? listEl.scrollTop : 0;
  state.active_step = index;
  state.focus_step = index;
  hmlRenderFlowDialog($('#hmlFlowDialog'), state, state.steps);
}

function hmlCenterFlowStep(index) {
  var list = $('#hmlFlowDialog .hml-flow-list')[0];
  var item = $('#hmlFlowDialog .hml-flow-item[data-step-index="' + index + '"]')[0];
  if (!list || !item) return;
  list.scrollTop = item.offsetTop - (list.clientHeight / 2) + (item.offsetHeight / 2);
}

function hmlFindNextFlowStep(state) {
  if (!state || !state.steps) return -1;
  var start = Math.max(0, state.active_step || 0);
  for (var i = start; i < state.steps.length; i++) {
    if (state.steps[i].state !== 'done') return i;
  }
  for (var j = 0; j < start; j++) {
    if (state.steps[j].state !== 'done') return j;
  }
  return -1;
}

function hmlMarkCurrentFlowStep(state, steps, status) {
  var step = steps[state.active_step];
  if (!step) return;
  var listEl = $('#hmlFlowDialog .hml-flow-list')[0];
  state.list_scroll_top = listEl ? listEl.scrollTop : state.list_scroll_top || 0;
  state.focus_step = state.active_step;
  if (status === 'done') {
    step.state = 'done';
    if (step.key === 'close_external') hmlApplyExternalClosed();
    if (step.key === 'role_standby') hmlApplyRole('standby');
    if (step.key === 'role_master') hmlApplyRole('master');
    if (step.key === 'master_openresty') hmlApplyExternalOpen();
  } else if (status === 'failed') {
    step.state = 'failed';
    state.auto_running = false;
    state.running = false;
  } else {
    step.state = 'running';
    state.running = true;
  }
  if (status === 'done') {
    state.running = false;
    state.just_stepped = true;
  }
  if (status === 'done' && steps.every(function(item) { return item.state === 'done'; })) {
    state.completed = true;
    state.auto_running = false;
    hmlState.switch_status = 'idle';
    if (!state.prompted_next) {
      state.prompted_next = true;
      hmlPromptNextFlow(state.target_role);
    }
  }
}

function hmlGetFlowStepCode(step) {
  var codeMap = {
    close_external: 'systemctl stop openresty\nsystemctl stop nginx || true',
    mysql_running_standby: 'systemctl start mysqld\nsystemctl status mysqld --no-pager',
    close_mysql_notify: 'node /www/server/jh-panel/plugins/ha_manager_local/scripts/closeMysqlSlaveNotify.js',
    authorized_key_on: 'mkdir -p /root/.ssh\ngrep -qxF "$STANDBY_SYNC_PUBLIC_KEY" /root/.ssh/authorized_keys || echo "$STANDBY_SYNC_PUBLIC_KEY" >> /root/.ssh/authorized_keys',
    open_backup_db: 'btpython /www/server/jh-panel/plugins/ha_manager_local/scripts/set_cron_status.py "备份数据库[backupAll]" enabled',
    open_xtrabackup: 'btpython /www/server/jh-panel/plugins/ha_manager_local/scripts/set_cron_status.py "[勿删]xtrabackup-cron" enabled',
    open_xtrabackup_full: 'btpython /www/server/jh-panel/plugins/ha_manager_local/scripts/set_cron_status.py "[勿删]xtrabackup-inc全量备份" enabled',
    open_xtrabackup_inc: 'btpython /www/server/jh-panel/plugins/ha_manager_local/scripts/set_cron_status.py "[勿删]xtrabackup-inc增量备份" enabled',
    close_site_backup: 'btpython /www/server/jh-panel/plugins/ha_manager_local/scripts/set_cron_status.py "备份网站配置[backupAll]" disabled',
    close_plugin_backup_all: 'btpython /www/server/jh-panel/plugins/ha_manager_local/scripts/set_cron_status.py "备份插件配置[所有]" disabled',
    close_plugin_backup_batch: 'btpython /www/server/jh-panel/plugins/ha_manager_local/scripts/set_cron_status.py "备份插件配置[backupAll]" disabled',
    close_lsyncd_cron: 'btpython /www/server/jh-panel/plugins/ha_manager_local/scripts/set_cron_status.py "[勿删]lsyncd实时任务定时同步" disabled',
    close_cert_cron: 'btpython /www/server/jh-panel/plugins/ha_manager_local/scripts/set_cron_status.py "[勿删]续签Let\'s Encrypt证书" disabled',
    open_site_restore: 'btpython /www/server/jh-panel/plugins/ha_manager_local/scripts/set_cron_status.py "恢复网站配置[所有]" enabled',
    open_plugin_restore: 'btpython /www/server/jh-panel/plugins/ha_manager_local/scripts/set_cron_status.py "恢复插件配置[所有]" enabled',
    close_ssl_notify: 'node /www/server/jh-panel/plugins/ha_manager_local/scripts/setNotifyValue.js ssl_cert -1',
    close_rsync_notify: 'node /www/server/jh-panel/plugins/ha_manager_local/scripts/closeRsyncStatusNotify.js',
    disable_rsyncd_tasks: 'btpython /www/server/jh-panel/plugins/ha_manager_local/scripts/set_rsyncd_tasks.py disabled',
    stop_lsyncd: 'systemctl stop lsyncd',
    kill_rsync: 'pkill -f /bin/rsync || true',
    standby_openresty: 'systemctl stop openresty\nsystemctl disable openresty\nsystemctl mask openresty\nsystemctl stop nginx || true',
    role_standby: 'echo standby > /www/server/ha_manager_local/role',
    standby_check: 'btpython /www/server/jh-panel/plugins/ha_manager_local/index.py health_check \"{}\"',
    mysql_prepare: 'systemctl start mysqld\nsystemctl status mysqld --no-pager',
    xtrabackup_restore: 'bash /www/server/jh-panel/plugins/ha_manager_local/scripts/run_xtrabackup_inc_restore.sh',
    checksum_check: 'bash /www/server/jh-panel/plugins/ha_manager_local/scripts/run_checksum.sh',
    sync_files: 'bash /www/server/jh-panel/plugins/ha_manager_local/scripts/sync_files.sh',
    async_dryrun_check: 'python3 - <<\'PY\'\nimport json\nimport os\nimport subprocess\nimport sys\n\ncfg_path = \'/www/server/rsyncd/config.json\'\nif not os.path.exists(cfg_path):\n    print(\'未找到 rsyncd 配置，跳过预检\')\n    sys.exit(0)\n\nwith open(cfg_path, \'r\', encoding=\'utf-8\') as fp:\n    cfg = json.load(fp)\n\nitems = cfg.get(\'send\', {}).get(\'list\', [])\nselected = []\nfor item in items:\n    name = item.get(\'name\') or \'\'\n    path = item.get(\'path\') or \'\'\n    target_path = item.get(\'target_path\') or \'\'\n    if \'/www/wwwstorage\' in path or \'/www/wwwstorage\' in target_path or \'wwwstorage\' in name:\n        selected.append(name)\n\nif not selected:\n    print(\'未找到 /www/wwwstorage 相关 rsyncd 任务，跳过预检\')\n    sys.exit(0)\n\nfor name in selected:\n    print(\'==> rsyncd 预检查:\', name)\n    subprocess.check_call([\'python3\', \'/www/server/jh-panel/plugins/rsyncd/tool_run.py\', \'preflight\', name])\nPY',
    restore_site_setting: 'bash /www/server/jh-panel/plugins/ha_manager_local/scripts/restore_site_setting.sh',
    restore_plugin_setting: 'bash /www/server/jh-panel/plugins/ha_manager_local/scripts/restore_plugin_setting.sh',
    mysql_online: 'systemctl start mysqld\nsystemctl status mysqld --no-pager',
    promote_mysql: 'node /www/server/jh-panel/plugins/ha_manager_local/scripts/switch__mysql_master.js',
    authorized_key_off: 'sed -i \"/standby_sync/d\" /root/.ssh/authorized_keys',
    close_backup_db: 'btpython /www/server/jh-panel/plugins/ha_manager_local/scripts/set_cron_status.py "备份数据库[backupAll]" disabled',
    close_xtrabackup: 'btpython /www/server/jh-panel/plugins/ha_manager_local/scripts/set_cron_status.py "[勿删]xtrabackup-cron" disabled',
    close_xtrabackup_full: 'btpython /www/server/jh-panel/plugins/ha_manager_local/scripts/set_cron_status.py "[勿删]xtrabackup-inc全量备份" disabled',
    close_xtrabackup_inc: 'btpython /www/server/jh-panel/plugins/ha_manager_local/scripts/set_cron_status.py "[勿删]xtrabackup-inc增量备份" disabled',
    open_site_backup: 'btpython /www/server/jh-panel/plugins/ha_manager_local/scripts/set_cron_status.py "备份网站配置[backupAll]" enabled',
    open_plugin_backup_all: 'btpython /www/server/jh-panel/plugins/ha_manager_local/scripts/set_cron_status.py "备份插件配置[所有]" enabled',
    open_plugin_backup_batch: 'btpython /www/server/jh-panel/plugins/ha_manager_local/scripts/set_cron_status.py "备份插件配置[backupAll]" enabled',
    open_lsyncd_cron: 'btpython /www/server/jh-panel/plugins/ha_manager_local/scripts/set_cron_status.py "[勿删]lsyncd实时任务定时同步" enabled',
    open_cert_cron: 'btpython /www/server/jh-panel/plugins/ha_manager_local/scripts/set_cron_status.py "[勿删]续签Let\'s Encrypt证书" enabled',
    close_site_restore: 'btpython /www/server/jh-panel/plugins/ha_manager_local/scripts/set_cron_status.py "恢复网站配置[所有]" disabled',
    close_plugin_restore: 'btpython /www/server/jh-panel/plugins/ha_manager_local/scripts/set_cron_status.py "恢复插件配置[所有]" disabled',
    open_ssl_notify: 'node /www/server/jh-panel/plugins/ha_manager_local/scripts/setNotifyValue.js ssl_cert 14',
    enable_rsyncd_tasks: 'btpython /www/server/jh-panel/plugins/ha_manager_local/scripts/set_rsyncd_tasks.py enabled',
    restart_lsyncd: 'systemctl restart lsyncd',
    master_openresty: 'systemctl unmask openresty\nsystemctl enable openresty\nsystemctl start openresty\nsystemctl stop nginx || true',
    open_email_notify: 'node /www/server/jh-panel/plugins/ha_manager_local/scripts/openEmailNotify.js',
    open_mysql_notify: 'node /www/server/jh-panel/plugins/ha_manager_local/scripts/openMysqlSlaveNotify.js',
    open_rsync_notify: 'node /www/server/jh-panel/plugins/ha_manager_local/scripts/openRsyncStatusNotify.js',
    role_master: 'echo master > /www/server/ha_manager_local/role',
    master_check: 'btpython /www/server/jh-panel/plugins/ha_manager_local/index.py health_check \"{}\"'
  };
  return codeMap[step.key] || ('# ' + step.title + '\n# 待接入真实执行脚本');
}

function hmlOpenFlowCodeDialog(step, confirm) {
  openEditCode({
    title: step.title,
    content: hmlGetFlowStepCode(step),
    mode: 'shell',
    width: '640px',
    height: '400px',
    submitBtn: '执行',
    onSubmit: function(content) {
      $('#openEditCodeCloseBtn').click();
      messageBox({timeout: 300, autoClose: true, toLogAfterComplete: true});
      confirm(content);
    }
  });
}

function hmlRunFlowStepWithCode() {
  hmlRunFlowStep(null, false);
}

function hmlRunFlowStep(done, skipConfirm) {
  var state = window.hmlFlowState;
  if (!state || state.running) return;
  var listEl = $('#hmlFlowDialog .hml-flow-list')[0];
  state.list_scroll_top = listEl ? listEl.scrollTop : state.list_scroll_top || 0;
  var steps = state.steps;
  if (state.active_step < 0) state.active_step = 0;
  if (state.active_step >= steps.length) state.active_step = steps.length - 1;
  var step = steps[state.active_step];
  if (!step) return;
  if (step.state === 'done') {
    hmlGoNextFlowStep();
    if (done) done(true);
    return;
  }
  if (steps.every(function(item) { return item.state === 'done'; })) {
    state.completed = true;
    state.auto_running = false;
    hmlRenderFlowDialog($('#hmlFlowDialog'), state, steps);
    if (done) done(true);
    return;
  }
  state.focus_step = state.active_step;
  if (step.guide) {
    hmlPromptNextFlow('master_prepare');
    hmlMarkCurrentFlowStep(state, steps, 'done');
    hmlRenderFlowDialog($('#hmlFlowDialog'), state, steps);
    if (done) done(true);
    return;
  }
  if (!skipConfirm) {
    hmlOpenFlowCodeDialog(step, function() {
      hmlRunFlowStep(done, true);
    });
    return;
  }
  hmlMarkCurrentFlowStep(state, steps, 'running');
  hmlRenderFlowDialog($('#hmlFlowDialog'), state, steps);
  setTimeout(function() {
    if (!window.hmlFlowState || window.hmlFlowState !== state) return;
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
      if (step.key === 'close_external') hmlLog('关闭对外服务完成：OpenResty 已停止');
      if (step.key.indexOf('task') >= 0 || step.key.indexOf('backup') >= 0 || step.key.indexOf('restore') >= 0 || step.key.indexOf('cron') >= 0) hmlLog('计划任务调整完成');
      if (step.key === 'standby_openresty') hmlLog('已切入备机策略');
      if (step.key === 'master_openresty') hmlLog('已切入主机策略');
      if (step.key === 'role_standby' || step.key === 'role_master') hmlLog('本机角色已更新');
    }
    hmlRenderFlowDialog($('#hmlFlowDialog'), state, steps);
    if (state.auto_running) {
      if (step.state === 'done') {
        state.flow_timer = setTimeout(hmlContinueCurrentFlowPhase, 180);
      } else {
        hmlPauseFlowAuto(true);
      }
    }
    if (done) done(step.state === 'done');
  }, 450);
}

function hmlFlowNextButtonText(state) {
  if (!state) return '继续执行';
  var step = state.steps && state.steps[state.active_step];
  if (!step) return '继续执行';
  if (state.auto_running) return '暂停执行';
  if (step.guide) return '下一步';
  if (hmlIsFlowPhaseReadyForNext(state)) return '下一步';
  return '继续执行';
}

function hmlGetFlowPhase(state) {
  if (!state || !state.steps || state.active_step < 0) return '';
  var step = state.steps[state.active_step];
  return step ? (step.phase || '') : '';
}

function hmlIsFlowPhaseDone(state) {
  var phase = hmlGetFlowPhase(state);
  if (!phase) return false;
  var items = (state.steps || []).filter(function(step) { return (step.phase || '') === phase; });
  return items.length > 0 && items.every(function(item) { return item.state === 'done'; });
}

function hmlIsAutoRequiredFlowStep(step, phase) {
  if (!step) return false;
  if ((step.phase || '') !== phase) return false;
  return phase !== 'master_prepare' || step.required !== false;
}

function hmlIsFlowPhaseReadyForNext(state) {
  var phase = hmlGetFlowPhase(state);
  if (!phase) return false;
  var items = (state.steps || []).filter(function(step) {
    return hmlIsAutoRequiredFlowStep(step, phase);
  });
  return items.length > 0 && items.every(function(item) { return item.state === 'done'; });
}

function hmlIsFlowStageReadyForNext(state, stageKey) {
  if (!state || !state.steps || !stageKey) return false;
  var items = state.steps.filter(function(step) {
    if ((step.phase || '') !== stageKey) return false;
    return stageKey !== 'master_prepare' || step.required !== false;
  });
  return items.length > 0 && items.every(function(item) { return item.state === 'done'; });
}

function hmlFindNextPendingStepInPhase(state) {
  var phase = hmlGetFlowPhase(state);
  if (!phase) return -1;
  var phaseStart = (state.steps || []).findIndex(function(step) { return (step.phase || '') === phase; });
  if (phaseStart < 0) return -1;
  for (var i = phaseStart; i < (state.steps || []).length; i++) {
    if (hmlIsAutoRequiredFlowStep(state.steps[i], phase) && state.steps[i].state !== 'done') return i;
  }
  return -1;
}

function hmlCurrentPhaseStepCount(state) {
  var phase = hmlGetFlowPhase(state);
  if (!phase) return 0;
  return (state.steps || []).filter(function(step) { return (step.phase || '') === phase; }).length;
}

function hmlCurrentPhaseDoneCount(state) {
  var phase = hmlGetFlowPhase(state);
  if (!phase) return 0;
  return (state.steps || []).filter(function(step) { return (step.phase || '') === phase && step.state === 'done'; }).length;
}

function hmlContinueCurrentFlowPhase() {
  var state = window.hmlFlowState;
  if (!state || !state.auto_running) return;
  if (state.running) return;
  if (state.steps && state.steps[state.active_step] && state.steps[state.active_step].guide) {
    state.auto_running = false;
    hmlRenderFlowDialog($('#hmlFlowDialog'), state, state.steps);
    return;
  }
  if (hmlIsFlowPhaseReadyForNext(state)) {
    state.auto_running = false;
    hmlRenderFlowDialog($('#hmlFlowDialog'), state, state.steps);
    return;
  }
  var nextPending = hmlFindNextPendingStepInPhase(state);
  if (nextPending < 0) {
    state.auto_running = false;
    hmlRenderFlowDialog($('#hmlFlowDialog'), state, state.steps);
    return;
  }
  state.active_step = nextPending;
  state.focus_step = nextPending;
  hmlRenderFlowDialog($('#hmlFlowDialog'), state, state.steps);
  hmlRunFlowStep(null, true);
}

function hmlGoNextFlowStep() {
  var state = window.hmlFlowState;
  if (!state || !state.steps) return;
  var current = state.steps[state.active_step];
  if (current && current.guide) {
    current.state = 'done';
    var nextAfterGuide = state.active_step + 1;
    if (nextAfterGuide < state.steps.length) {
      state.active_step = nextAfterGuide;
      state.focus_step = nextAfterGuide;
    }
    state.just_stepped = true;
    hmlRenderFlowDialog($('#hmlFlowDialog'), state, state.steps);
    return;
  }
  var phase = hmlGetFlowPhase(state);
  if (!phase) return;
  var currentPhaseSteps = state.steps.filter(function(step) { return (step.phase || '') === phase; });
  var allDone = hmlIsFlowPhaseReadyForNext(state);
  if (!allDone) return;
  if (phase === 'master_prepare') {
    var waitIndex = state.steps.findIndex(function(step) { return step.key === 'wait_standby_offline'; });
    if (waitIndex >= 0) {
      hmlPromptNextFlow('master_prepare');
      state.active_step = waitIndex;
      state.focus_step = waitIndex;
      state.just_stepped = true;
      hmlRenderFlowDialog($('#hmlFlowDialog'), state, state.steps);
      return;
    }
  }
  if (phase === 'master_online') {
    state.completed = true;
    hmlPromptNextFlow(state.target_role);
    hmlRenderFlowDialog($('#hmlFlowDialog'), state, state.steps);
    return;
  }
  var stages = hmlBuildFlowStages(state);
  var currentStageIndex = stages.findIndex(function(item) { return item.key === phase; });
  if (currentStageIndex < 0) return;
  var nextStage = stages[currentStageIndex + 1];
  if (!nextStage) return;
  var nextIndex = state.steps.findIndex(function(step) { return (step.phase || '') === nextStage.key; });
  if (nextIndex < 0) return;
  state.active_step = nextIndex;
  state.focus_step = nextIndex;
  state.just_stepped = true;
  hmlRenderFlowDialog($('#hmlFlowDialog'), state, state.steps);
}

function hmlPromptNextFlow(flow) {
  var text = flow === 'master_prepare' ? '请到备用机执行下线流程；备用机下线完成后，再回到主机执行正式上线流程。' : hmlFlowNextText(flow);
  hmlState.last_action = text;
  hmlLog(text);
  layer.msg(text, {icon: 1, time: 2500});
}

function hmlToggleFlowAuto() {
  var state = window.hmlFlowState;
  if (!state) return;
  if (state.auto_running) {
    hmlPauseFlowAuto(true);
    return;
  }
  if (state.running) return;
  var step = state.steps && state.steps[state.active_step];
  if (step && step.guide) {
    hmlGoNextFlowStep();
    return;
  }
  if (hmlIsFlowPhaseReadyForNext(state)) {
    hmlGoNextFlowStep();
    return;
  }
  state.auto_running = true;
  hmlContinueCurrentFlowPhase();
}

function hmlCanGoPrevFlowPhase(state) {
  if (!state || !state.steps) return false;
  var phase = hmlGetFlowPhase(state);
  if (!phase) return false;
  var stages = hmlBuildFlowStages(state);
  var currentStageIndex = stages.findIndex(function(item) { return item.key === phase; });
  return currentStageIndex > 0;
}

function hmlStepBack() {
  var state = window.hmlFlowState;
  if (!state || !state.steps) return;
  var phase = hmlGetFlowPhase(state);
  if (!phase) return;
  hmlPauseFlowAuto(false);
  var stages = hmlBuildFlowStages(state);
  var currentStageIndex = stages.findIndex(function(item) { return item.key === phase; });
  if (currentStageIndex <= 0) {
    return;
  }
  var prevStage = stages[currentStageIndex - 1];
  var prevIndex = state.steps.findIndex(function(step) { return (step.phase || '') === prevStage.key; });
  if (prevIndex < 0) return;
  state.active_step = prevIndex;
  state.focus_step = state.active_step;
  hmlRenderFlowDialog($('#hmlFlowDialog'), state, state.steps);
}

function hmlJumpFlowStage(stageKey) {
  var state = window.hmlFlowState;
  if (!state || !state.steps) return;
  var currentPhase = hmlGetFlowPhase(state);
  var stageIndex = (hmlBuildFlowStages(state) || []).findIndex(function(item) { return item.key === stageKey; });
  if (stageIndex < 0) return;
  var stages = hmlBuildFlowStages(state);
  if (currentPhase) {
    var currentIndex = stages.findIndex(function(item) { return item.key === currentPhase; });
    if (stageIndex > currentIndex) return;
    if (stageIndex === currentIndex) return;
  }
  var targetIndex = state.steps.findIndex(function(step) { return (step.phase || '') === stageKey; });
  if (targetIndex < 0) return;
  if (stageKey !== currentPhase && !hmlIsFlowStageReadyForNext(state, stageKey)) return;
  hmlPauseFlowAuto(false);
  state.active_step = targetIndex;
  state.focus_step = targetIndex;
  hmlRenderFlowDialog($('#hmlFlowDialog'), state, state.steps);
}

function hmlPauseFlowAuto(render) {
  var state = window.hmlFlowState;
  if (!state) return;
  state.auto_running = false;
  if (state.flow_timer) {
    clearTimeout(state.flow_timer);
    state.flow_timer = null;
  }
  if (render) hmlRenderFlowDialog($('#hmlFlowDialog'), state, state.steps);
}

function hmlUndoFlowStep(index, event) {
  if (event) {
    event.stopPropagation();
    event.preventDefault();
  }
  var state = window.hmlFlowState;
  if (!state || !state.steps || !state.steps[index]) return;
  hmlPauseFlowAuto(false);
  var listEl = $('#hmlFlowDialog .hml-flow-list')[0];
  state.list_scroll_top = listEl ? listEl.scrollTop : state.list_scroll_top || 0;
  state.steps[index].state = 'pending';
  state.completed = false;
  state.running = false;
  state.active_step = Math.max(0, index - 1);
  state.focus_step = state.active_step;
  if (state.steps[index].key === 'role_master') hmlApplyRole('standby');
  if (state.steps[index].key === 'role_standby') hmlApplyRole('master');
  if (state.steps[index].key === 'master_openresty') hmlApplyExternalClosed();
  hmlLog('撤销步骤：' + state.steps[index].title);
  hmlRenderFlowDialog($('#hmlFlowDialog'), state, state.steps);
}

function hmlCancelFlowDialog() {
  var state = window.hmlFlowState;
  if (state) hmlPauseFlowAuto(false);
  if (state && state.layer_id) layer.close(state.layer_id);
  window.hmlFlowState = null;
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

function hmlApplyExternalOpen() {
  hmlState.external_closed = false;
  hmlState.checks.forEach(function(item) {
    if (item.name === 'OpenResty') {
      item.actual = '运行中';
      item.status = hmlState.role === 'master' ? 'pass' : 'fail';
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
  $('.soft-man-con').html('<div class="hml-section"><div class="hml-section-head"><div><div class="hml-section-title">操作日志</div></div><button class="btn btn-default btn-sm" onclick="hmlState.log=[];hmlRenderLog()">清空</button></div><div class="hml-section-body"><pre class="hml-log">' + hmlHtml(hmlState.log.join('\n')) + '</pre></div></div>');
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
