var hmlState = {
  view: 'overview',
  role: 'standby',
  desired_role: 'standby',
  switch_status: 'idle',
  external_closed: false,
  target_role: 'master',
  host_id: '',
  host_name: '',
  host_ip: '',
  pair_id: '',
  pair_name: '',
  monitor_url: '',
  monitor_enabled: false,
  report_interval: 30,
  last_report_at: '',
  last_action: '等待操作',
  log: [
    '[21:00:00] 本地版已加载，等待实际操作。',
    '[21:00:02] 本地版只执行当前主机动作。'
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

var hmlFlowConfig = null;
var hmlFlowConfigLoaded = false;

function hmlEnsureFlowConfig(callback) {
  if (hmlFlowConfigLoaded) {
    if (callback) callback();
    return;
  }
  $.getJSON('/plugins/file?name=ha_manager_local&f=flow_config.json&v=202609030200', function(data) {
    hmlFlowConfig = data || {};
    hmlFlowConfigLoaded = true;
    if (callback) callback();
  }).fail(function() {
    hmlFlowConfig = {roles: {}, guides: {}};
    hmlFlowConfigLoaded = true;
    if (callback) callback();
  });
}

function hmlFlowRoleConfig(role) {
  var roles = (hmlFlowConfig && hmlFlowConfig.roles) || {};
  return roles[role] || roles.master || {stages: [], steps: []};
}

function hmlFlowGuideConfig(step) {
  if (!step) return null;
  if (step.repair && step.repair.text) return step.repair;
  if (step.repair_data && step.repair_data.text) return step.repair_data;
  return null;
}

function hmlMonitorEnabled() {
  return !!hmlState.monitor_url && !!hmlState.monitor_enabled;
}

function hmlBoot() {
  hmlLoadState(function() {
    hmlEnsureFlowConfig(function() {
      hmlRender();
    });
  });
}

function hmlPost(method, args, callback, failCallback) {
  function encodePluginArgs(value) {
    return encodeURIComponent(JSON.stringify(value || {})).replace(/[!'()*]/g, function(ch) {
      return '%' + ch.charCodeAt(0).toString(16).toUpperCase();
    });
  }
  return $.post('/plugins/run', {
    name: 'ha_manager_local',
    func: method,
    args: encodePluginArgs(args || {})
  }, function(res) {
    var data = null;
    try {
      data = typeof res === 'string' ? JSON.parse(res) : res;
    } catch (e) {
      data = null;
    }
    if (!data || !data.status) {
      if (failCallback) {
        failCallback(data || {status: false, msg: '操作失败', data: {}});
        return;
      }
      layer.msg((data && data.msg) || '操作失败', {icon: 2});
      return;
    }
    var payload = data.data;
    if (typeof payload === 'string') {
      try { payload = JSON.parse(payload); } catch (e2) {}
    }
    if (payload && typeof payload === 'object' && payload.hasOwnProperty('status') && payload.hasOwnProperty('msg')) {
      if (!payload.status) {
        if (failCallback) {
          failCallback(payload);
          return;
        }
        layer.msg(payload.msg || '操作失败', {icon: 2});
        return;
      }
      payload = payload.data || {};
    }
    if (callback) callback(payload || {});
  }, 'json').fail(function(xhr) {
    var msg = '插件接口连接失败';
    if (xhr && xhr.responseText) msg += ': ' + String(xhr.responseText).slice(0, 500);
    if (failCallback) {
      failCallback({status: false, msg: msg, data: {}});
      return;
    }
    layer.msg(msg, {icon: 2});
  });
}

function hmlBackendLogs(data, state, step) {
  data = data || {};
  if ($.isArray(data.logs) && data.logs.length) return data.logs;
  if (typeof data.logs === 'string' && data.logs) return data.logs.split('\n');
  if (typeof data.log === 'string' && data.log) return data.log.replace(/\r\n/g, '\n').split('\n');
  var targetRole = state && state.target_role;
  var backendStep = data.state_snapshot && data.state_snapshot.step_list && data.state_snapshot.step_list[targetRole] && data.state_snapshot.step_list[targetRole][step.key];
  if (backendStep && $.isArray(backendStep.logs) && backendStep.logs.length) return backendStep.logs;
  return [];
}

function hmlCreateRunId() {
  var now = new Date();
  var pad = function(n) { return n < 10 ? '0' + n : '' + n; };
  return 'LOCAL_' + now.getFullYear() + pad(now.getMonth() + 1) + pad(now.getDate()) + pad(now.getHours()) + pad(now.getMinutes()) + pad(now.getSeconds()) + '_' + Math.floor(Math.random() * 1000);
}

function hmlCreateFlowRunId() {
  return 'FLOW_' + hmlCreateRunId();
}

function hmlStopStepLogPolling() {
  if (window.hmlStepLogTimer) {
    clearInterval(window.hmlStepLogTimer);
    window.hmlStepLogTimer = null;
  }
}

function hmlReadStepLog(runId, callback, logPath) {
  if (!runId && !logPath) return;
  hmlPost('read_step_log', {run_id: runId || '', log_path: logPath || ''}, function(data) {
    if (callback) callback(data || {});
  }, function() {
    if (callback) callback({log: ''});
  });
}

function hmlEnsureStepLogLoaded(step) {
  if (!step || (step.logs && step.logs.length) || (!step.run_id && !step.log_path)) return;
  hmlReadStepLog(step.run_id || '', function(logData) {
    hmlSetStepLogFromFile(step, logData);
  }, step.log_path || '');
}

function hmlApplyStepLogFromResponse(step, data) {
  if (data && data.warning_msg) step.warning_msg = data.warning_msg;
  var logs = hmlBackendLogs(data, window.hmlFlowState, step);
  if (!logs.length) return false;
  var prefix = $.isArray(step.active_run_log_prefix) ? step.active_run_log_prefix : [];
  step.logs = prefix.concat(logs);
  hmlUpdateVisibleStepLog(step);
  return true;
}

function hmlSetStepLogFromFile(step, logData) {
  if (!step || !logData || !logData.log) return false;
  var prefix = $.isArray(step.active_run_log_prefix) ? step.active_run_log_prefix : [];
  var fileLogs = String(logData.log).replace(/\r\n/g, '\n').split('\n');
  step.logs = prefix.concat(fileLogs);
  hmlUpdateVisibleStepLog(step);
  return true;
}

function hmlUpdateVisibleStepLog(step) {
  var box = $('#hmlFlowDialog .hml-flow-step-log-box');
  if (!box.length) return;
  box.text((step && step.logs ? step.logs : []).join('\n') || '暂无日志');
  hmlScrollStepLogToBottom();
  hmlScrollStepLogToBottomLater();
}

function hmlScrollStepLogToBottom() {
  var el = $('#hmlFlowDialog .hml-flow-step-log-box')[0];
  if (!el) return;
  el.scrollTop = el.scrollHeight;
}

function hmlScrollStepLogToBottomLater() {
  setTimeout(hmlScrollStepLogToBottom, 0);
}

function hmlLoadState(callback) {
  hmlPost('get_state', {}, function(data) {
    hmlState = $.extend(true, hmlState, data);
    hmlRefreshBrowserTitle();
    if (callback) callback();
  });
}

function hmlRefreshBrowserTitle() {
  var titleState = {role: hmlState.role};
  if (typeof applyHaManagerBrowserTitle === 'function') {
    applyHaManagerBrowserTitle(titleState);
  } else if (typeof applyHaManagerSshBrowserTitle === 'function') {
    applyHaManagerSshBrowserTitle(titleState);
  }
}

function hmlCloneSteps() {
  return hmlState.steps.map(function(item) { return $.extend(true, {}, item); });
}

function hmlHtml(value) {
  value = value == null ? '' : String(value);
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function hmlTipHtml(value) {
  var lines = String(value || '').replace(/\r\n/g, '\n').split('\n').filter(function(line) { return $.trim(line); });
  return lines.map(function(line) {
    var index = line.indexOf('：');
    if (index < 0) index = line.indexOf(': ');
    if (index <= 0) return '<div class="hml-tip-line hml-tip-plain">' + hmlHtml(line) + '</div>';
    var label = line.slice(0, index);
    var valueText = line.slice(index + (line.charAt(index) === ':' ? 2 : 1));
    var valueClass = label === '异常原因' ? 'hml-tip-value hml-tip-value-error' : 'hml-tip-value';
    return '<div class="hml-tip-line"><span class="hml-tip-label">' + hmlHtml(label) + '</span><span class="' + valueClass + '">' + hmlHtml(valueText) + '</span></div>';
  }).join('');
}

function hmlNow() {
  var d = new Date();
  return [d.getHours(), d.getMinutes(), d.getSeconds()].map(function(n) { return n < 10 ? '0' + n : '' + n; }).join(':');
}

function hmlEnsureStepLog(step) {
  if (!step) return [];
  if (!step.logs) step.logs = [];
  return step.logs;
}

function hmlStepLogsText(step) {
  return hmlHtml((step && step.logs ? step.logs : []).join('\n') || '暂无日志');
}

function hmlAppendStepLog(step, text) {
  if (!step || !text) return;
  hmlEnsureStepLog(step).push('[' + hmlNow() + '] ' + text);
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

function hmlRoleShortText(role) {
  return role === 'master' ? '主' : '备';
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
  if (hmlState.view === 'monitor') return hmlRenderMonitor();
  if (hmlState.view === 'health') return hmlRenderHealth();
  if (hmlState.view === 'log') return hmlRenderLog();
  hmlRenderReadme();
}

function hmlExternalServiceButtonText() {
  return hmlState.external_closed ? '打开对外服务' : '关闭对外服务';
}

function hmlExternalServiceNormal(externalClosed) {
  if (hmlState.role === 'master') return !externalClosed;
  return !!externalClosed;
}

function hmlExternalServiceButtonClass() {
  var nextExternalClosed = !hmlState.external_closed;
  return hmlExternalServiceNormal(nextExternalClosed) ? 'btn-success' : 'btn-danger';
}

function hmlRenderOverview() {
  var failedChecks = hmlState.checks.filter(function(item) { return item.status !== 'pass'; }).length;
  var externalNormal = hmlExternalServiceNormal(hmlState.external_closed);
  var monitorConfigured = !!hmlState.monitor_url;
  var monitorEnabled = hmlMonitorEnabled();
  var promoteDisabled = hmlState.role === 'master';
  var demoteDisabled = hmlState.role === 'standby';
  var promoteTitle = promoteDisabled ? '当前已是主' : '将当前机器从备切换为主';
  var demoteTitle = demoteDisabled ? '当前已是备' : '将当前机器从主切换为备';
  var promoteBtn = '<button class="btn ' + (promoteDisabled ? 'btn-default' : 'btn-success') + ' btn-sm" onclick="hmlOpenSwitchDialog(\'master\')" title="' + promoteTitle + '"' + (promoteDisabled ? ' disabled' : '') + '>备-&gt;主</button>';
  var demoteBtn = '<button class="btn ' + (demoteDisabled ? 'btn-default' : 'btn-success') + ' btn-sm" onclick="hmlOpenSwitchDialog(\'standby\')" title="' + demoteTitle + '"' + (demoteDisabled ? ' disabled' : '') + '>主-&gt;备</button>';
  var html = '<div class="hml-topbar"><div><div class="hml-title">主备管理</div><div class="hml-sub">查看本机主备状态，必要时执行升主、降从与对外服务控制。</div></div><div class="hml-actions">' + promoteBtn + demoteBtn + '<button class="btn ' + hmlExternalServiceButtonClass() + ' btn-sm" onclick="hmlToggleExternalService()">' + hmlHtml(hmlExternalServiceButtonText()) + '</button><button class="btn btn-default btn-sm" onclick="hmlRunHealthCheck()">重新自检</button></div></div>' +
    '<div class="hml-panel"><div class="hml-panel-body">' +
      '<table class="table table-hover hml-overview-table"><tbody>' +
        '<tr><th>当前主备状态</th><td>' + hmlPill(hmlState.role === 'master' ? 'ok' : 'info', hmlRoleShortText(hmlState.role)) + '</td></tr>' +
        '<tr><th>对外服务</th><td>' + hmlPill(externalNormal ? 'ok' : 'bad', hmlState.external_closed ? '已关闭' : '开放中') + '<span class="hml-overview-note">' + hmlHtml(hmlState.external_closed ? 'OpenResty 已停止' : 'OpenResty 运行中') + '</span></td></tr>' +
        '<tr><th>自检状态</th><td>' + hmlPill(failedChecks ? 'bad' : 'ok', failedChecks ? '有异常' : '正常') + '<span class="hml-overview-note">异常项 ' + failedChecks + ' 个</span></td></tr>' +
        '<tr><th>云监控</th><td>' + (monitorConfigured ? hmlPill(monitorEnabled ? 'ok' : 'warn', monitorEnabled ? '已启用' : '未启用') : hmlPill('warn', '未配置')) + '<span class="hml-overview-note">' + hmlHtml(monitorEnabled ? '最近上报：' + (hmlState.last_report_at || '未上报') : (monitorConfigured ? '已配置地址，但云监控相关功能已关闭' : '未启用云监控相关功能')) + '</span></td></tr>' +
      '</tbody></table>' +
    '</div></div>';
  $('.soft-man-con').html(html);
}

function hmlInput(label, name, value, style, type, placeholder) {
  return '<div class="line"><span class="tname">' + hmlHtml(label) + '</span><div class="info-r"><input class="bt-input-text" type="' + (type || 'text') + '" name="' + hmlHtml(name) + '" value="' + hmlHtml(value) + '" style="' + hmlHtml(style) + '" placeholder="' + hmlHtml(placeholder || '') + '" /></div></div>';
}

function hmlRenderMonitor() {
  var configured = !!hmlState.monitor_url;
  var enabled = hmlMonitorEnabled();
  var html = '<div class="hml-section"><div class="hml-section-head"><div><div class="hml-section-title">绑定云监控配置</div><div class="hml-section-sub">配置本机 ID、主备关系 ID、云监控地址和总开关。关闭后不上报状态，也不启用云监控相关能力。</div></div>' + (configured ? hmlPill(enabled ? 'ok' : 'warn', enabled ? '已启用' : '未启用') : hmlPill('warn', '未配置')) + '</div><div class="hml-section-body"><form class="bt-form hml-form" id="hmlMonitorForm">' +
    '<div class="line"><span class="tname">本机ID</span><div class="info-r hml-inline-actions"><input class="bt-input-text" type="text" name="host_id" value="' + hmlHtml(hmlState.host_id) + '" style="width:360px" readonly /><button type="button" class="btn btn-default btn-sm" onclick="hmlRegenerateHostId()">重新生成</button></div></div>' +
    hmlInput('主备关系ID', 'pair_id', hmlState.pair_id, 'width:360px') +
    hmlInput('云监控地址', 'monitor_url', hmlState.monitor_url, 'width:420px', 'text', '例如：http://192.168.100.1:10844') +
    '<div class="line"><span class="tname">是否启用</span><div class="info-r c4"><label class="hml-monitor-switch"><input type="checkbox" name="monitor_enabled" value="1" ' + (hmlState.monitor_enabled ? 'checked' : '') + '><span class="hml-switch-slider"></span></label></div></div>' +
    '<div class="line"><span class="tname">状态</span><div class="info-r c4">' + hmlHtml(enabled ? '云监控已启用，本机状态允许上传到云监控。' : (configured ? '已配置云监控地址，但云监控开关已关闭，不会上报状态。' : '未配置云监控地址，云监控相关功能未启用。')) + '</div></div>' +
    '<div class="line"><span class="tname"></span><div class="info-r hml-inline-actions"><button type="button" class="btn btn-default btn-sm" onclick="hmlSaveMonitor()">测试并注册</button><button type="button" class="btn btn-success btn-sm" onclick="hmlSaveMonitor(true)">保存并注册</button><button type="button" class="btn btn-default btn-sm" onclick="hmlReportState()">立即上报</button><button type="button" class="btn btn-warning btn-sm" onclick="hmlClearMonitor()">清空地址</button></div></div>' +
  '</form></div></div>';
  $('.soft-man-con').html(html);
}

function hmlReadMonitorForm() {
  var data = {};
  $('#hmlMonitorForm').serializeArray().forEach(function(item) {
    data[item.name] = item.value;
  });
  data.monitor_enabled = $('#hmlMonitorForm input[name="monitor_enabled"]').is(':checked') ? '1' : '0';
  return data;
}

function hmlSaveMonitor(report) {
  var data = hmlReadMonitorForm();
  hmlPost('save_monitor', data, function(next) {
    hmlState = $.extend(true, hmlState, next);
    layer.msg(report === true ? '已保存配置' : '配置已保存', {icon: hmlMonitorEnabled() ? 1 : 0});
    hmlRenderMonitor();
  });
}

function hmlReportState() {
  if (!hmlState.monitor_url) return layer.msg('云监控地址为空，云监控相关功能未启用', {icon: 0});
  if (!hmlMonitorEnabled()) return layer.msg('云监控未启用，当前不会上传状态', {icon: 0});
  hmlPost('report_state', {}, function(next) {
    hmlState = $.extend(true, hmlState, next);
    layer.msg('本机状态已刷新', {icon: 1});
    hmlRenderMonitor();
  });
}

function hmlClearMonitor() {
  layer.confirm('确认清空云监控地址？清空后本机状态不再上报。', {icon: 3, title: '清空云监控', btn: ['确认', '取消']}, function(index) {
    layer.close(index);
    hmlPost('clear_monitor', {}, function(next) {
      hmlState = $.extend(true, hmlState, next);
      layer.msg('已清空云监控地址', {icon: 1});
      hmlRenderMonitor();
    });
  });
}

function hmlRegenerateHostId() {
  layer.confirm('确认重新生成本机ID？重新生成后需要重新注册云监控。', {icon: 3, title: '重新生成本机ID', btn: ['确认', '取消']}, function(index) {
    layer.close(index);
    hmlPost('regenerate_host_id', {}, function(next) {
      hmlState.host_id = next.host_id || hmlState.host_id;
      layer.msg('本机ID已重新生成', {icon: 1});
      hmlRenderMonitor();
    });
  });
}

function hmlCloneFlowStep(step) {
  return $.extend(true, {}, step);
}

function hmlOpenSwitchDialog(targetRole) {
  var defaultRole = targetRole || (hmlState.role === 'master' ? 'standby' : 'master');
  if (defaultRole === hmlState.role) return;
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
    log: [],
    flow_run_id: hmlCreateFlowRunId(),
    role_selected: true
  };
  state.steps = hmlBuildFlowSteps(defaultRole, true);
  state.active_step = 0;
  window.hmlFlowState = state;
  var flowTitle = defaultRole === 'master' ? '备->主' : '主->备';
  var dialog = layer.open({
    type: 1,
    area: ['900px', '620px'],
    title: flowTitle,
    closeBtn: 1,
    shadeClose: false,
    content: '<div id="hmlFlowDialog" class="hml-flow-wrap" style="height:552px; min-height: 552px;"></div>',
    success: function(layero) {
      hmlRenderFlowDialog(layero.find('#hmlFlowDialog'), state, state.steps);
    }
  });
  state.layer_id = dialog;
  hmlLog('打开' + flowTitle + '流程弹框');
  return dialog;
}

function hmlBuildFlowStages(state) {
  var role = state && state.target_role ? state.target_role : 'master';
  return (hmlFlowRoleConfig(role).stages || []).map(function(item) {
    return $.extend(true, {}, item);
  });
}

function hmlFlowStageKey(step) {
  if (!step) return '';
  return step.phase || '';
}

function hmlBuildFlowStageBar(state, steps, activeStep) {
  var stages = hmlBuildFlowStages(state);
  if (!stages.length || stages.length === 1 || state.target_role === 'standby') return '';
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

function hmlBuildFlowSteps(role, fresh) {
  return hmlCloneStepsFromConfig(role, fresh);
}

function hmlCloneStepsFromConfig(role, fresh) {
  var cfg = hmlFlowRoleConfig(role);
  return (cfg.steps || []).map(function(item) {
    var saved = fresh ? {} : (((hmlState.step_list || {})[role] || {})[item.key] || {});
    return $.extend(true, {}, item, {
      state: saved.state || item.state || 'pending',
      logs: saved.logs || item.logs || [],
      run_id: saved.run_id || item.run_id || '',
      log_path: saved.log_path || item.log_path || '',
      failure_msg: saved.msg || item.failure_msg || '',
      warning_msg: saved.warning_msg || item.warning_msg || ''
    });
  });
}

function hmlStepGroupTitle(step) {
  if (!step) return '其他操作';
  if (step.group) return step.group;
  if (step.stage) return step.stage;
  return '其他操作';
}

function hmlFlowGroups(steps) {
  var groups = [];
  var indexMap = {};
  (steps || []).forEach(function(step, index) {
    var title = hmlStepGroupTitle(step);
    if (indexMap[title] == null) {
      indexMap[title] = groups.length;
      groups.push({title: title, steps: []});
    }
    groups[indexMap[title]].steps.push({step: step, index: index});
  });
  return groups;
}

function hmlEnsureOpenGroups(state, steps) {
  if (!state) return;
  if (!state.open_groups) state.open_groups = {};
  var active = steps && steps[state.active_step];
  if (!active) return;
  var activeGroup = hmlStepGroupTitle(active);
  if (state.last_active_group !== activeGroup) {
    state.open_groups[activeGroup] = true;
    state.last_active_group = activeGroup;
  }
}

function hmlStepStatusText(state) {
  if (state === 'done') return '已完成';
  if (state === 'running') return '执行中';
  if (state === 'failed') return '失败';
  return '待执行';
}

function hmlIsFlowGroupDone(steps, groupTitle) {
  if (!groupTitle) return false;
  var items = (steps || []).filter(function(item) { return hmlStepGroupTitle(item) === groupTitle; });
  return items.length > 0 && items.every(function(item) { return item.state === 'done'; });
}

function hmlRenderFlowGroupList(state, steps, activeStep) {
  hmlEnsureOpenGroups(state, steps);
  return hmlFlowGroups(steps).map(function(group) {
    var active = group.steps.some(function(item) { return item.index === activeStep; });
    var doneCount = group.steps.filter(function(item) { return item.step.state === 'done'; }).length;
    var allDone = doneCount === group.steps.length;
    var open = !!(state.open_groups && state.open_groups[group.title]);
    var groupCls = (open ? 'open ' : '') + (active ? 'active ' : '') + (allDone ? 'done' : '');
    var body = group.steps.map(function(item) {
      var step = item.step;
      var cls = step.state === 'done' ? 'done' : item.index === activeStep ? 'active' : '';
      // 暂时隐藏撤销按钮
      // var undo = step.state === 'done' ? '<button class="btn btn-default btn-xs hml-flow-undo" onclick="hmlUndoFlowStep(' + item.index + ', event)">撤销</button>' : '';
      var undo = '';
      return '<div class="hml-flow-item ' + cls + '" data-step-index="' + item.index + '" onclick="hmlJumpFlowStep(' + item.index + ')"><span class="hml-flow-index">' + (step.state === 'done' ? '✓' : (item.index + 1)) + '</span><div class="hml-flow-item-main"><div class="hml-flow-item-title">' + hmlHtml(step.title) + hmlStepBadgeHtml(step) + '</div><div class="hml-flow-item-desc">' + hmlHtml(hmlStepStatusText(step.state)) + '</div></div>' + undo + '</div>';
    }).join('');
    return '<div class="hml-flow-group ' + groupCls + '" data-group-title="' + hmlHtml(group.title) + '"><div class="hml-flow-group-head" onclick="hmlToggleFlowGroup(\'' + hmlAttr(group.title) + '\')"><span class="hml-flow-group-toggle">' + (open ? '▾' : '▸') + '</span><span class="hml-flow-group-title">' + hmlHtml(group.title) + '</span><span class="hml-flow-group-count">' + doneCount + '/' + group.steps.length + '</span></div><div class="hml-flow-group-body">' + body + '</div></div>';
  }).join('');
}

function hmlAttr(value) {
  return hmlHtml(value).replace(/'/g, '&#39;');
}

function hmlToggleFlowGroup(title) {
  var state = window.hmlFlowState;
  if (!state) return;
  var listEl = $('#hmlFlowDialog .hml-flow-list')[0];
  state.list_scroll_top = listEl ? listEl.scrollTop : state.list_scroll_top || 0;
  if (!state.open_groups) state.open_groups = {};
  state.open_groups[title] = !state.open_groups[title];
  hmlRenderFlowDialog($('#hmlFlowDialog'), state, state.steps);
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
  return '';
}

function hmlStepBadgeHtml(step) {
  var label = hmlStepRequiredLabel(step);
  if (!label) return '';
  var cls = 'hml-step-flag-optional';
  return '<span class="hml-step-flag ' + cls + '">' + label + '</span>';
}

function hmlStepHintHtml(step) {
  if (!step) return '';
  if (!hmlFlowGuideConfig(step)) return '';
  return '<button type="button" class="hml-step-hint" title="异常处理指导" onclick="hmlOpenStepGuide()">!</button>';
}

function hmlStepRepairButton(step) {
  if (!step || step.state !== 'failed') return '';
  return '<button class="btn btn-warning btn-sm" onclick="hmlRunFlowStepWithCode()">重新执行当前步骤</button>';
}

function hmlStepFailureGuide(step) {
  var guide = hmlFlowGuideConfig(step);
  return (guide && guide.text) || '';
}

function hmlStepGuideCommands(step) {
  var guide = hmlFlowGuideConfig(step);
  return (guide && guide.commands) || [];
}

function hmlOpenStepGuide() {
  var state = window.hmlFlowState;
  if (!state || !state.steps) return;
  var step = state.steps[state.active_step] || state.steps[0];
  if (!step) return;
  var guide = hmlFlowGuideConfig(step) || {};
  if (!guide.text) return;
  var commands = guide.commands || [];
  window.hmlGuideCommands = commands;
  var commandHtml = commands.map(function(item, index) {
    return '<div class="hml-guide-command"><div class="hml-guide-command-desc">' + hmlHtml(item.desc) + '</div><div class="hml-guide-code-row"><pre>' + hmlHtml(item.cmd) + '</pre><button class="btn btn-default btn-xs hml-guide-copy" onclick="hmlCopyGuideCommand(' + index + ')">复制</button></div></div>';
  }).join('');
  var commandSection = commandHtml ? '<div class="hml-guide-section-title">常用命令</div>' + commandHtml : '';
  layer.open({
    type: 1,
    title: step.title + ' 处理指引',
    area: ['620px', '460px'],
    shadeClose: true,
    content: '<div class="hml-guide-layer"><div class="hml-guide-section-title">处理流程</div><div class="hml-guide-text">' + hmlHtml(guide.text || hmlStepFailureGuide(step)) + '</div>' + commandSection + '</div>'
  });
}

function hmlCopyGuideCommand(index) {
  var commands = window.hmlGuideCommands || [];
  var item = commands[index];
  var cmd = item && item.cmd;
  if (!cmd) return;
  function ok() { layer.msg('已复制', {icon: 1, time: 1000}); }
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(cmd).then(ok);
    return;
  }
  var input = $('<textarea>').val(cmd).appendTo('body').select();
  document.execCommand('copy');
  input.remove();
  ok();
}

function hmlRenderFlowDialog(root, state, steps) {
  root = root && root.length ? root : $('#hmlFlowDialog');
  if (!root.length) return;
  if (state.completed_view) {
    var completedTitle = state.target_role === 'master' ? '当前主机已切换为主' : '当前主机已切换为备';
    var completedText = state.target_role === 'master' ? '请到 Zenlayer 切换 DNS 或入口解析，将业务流量指向当前主机。' : '请确认对外服务已关闭并进入备机状态。';
    root.html('<div class="hml-flow-complete"><div class="hml-flow-complete-title">' + hmlHtml(completedTitle) + '</div><div class="hml-flow-complete-text">' + hmlHtml(completedText) + '</div></div><div class="hml-flow-footer"><button class="btn btn-success btn-sm" onclick="hmlCancelFlowDialog()">关闭窗口</button></div>');
    return;
  }
  var activeStep = state.active_step < 0 ? 0 : state.active_step;
  var current = steps[activeStep] || steps[steps.length - 1];
  hmlEnsureStepLogLoaded(current);
  var previousScrollTop = state.list_scroll_top || 0;
  var currentIsGuide = current && current.guide;
  var list = hmlRenderFlowGroupList(state, steps, activeStep);
  if (currentIsGuide) {
    var guideHtml = hmlBuildFlowStageBar(state, steps, activeStep) +
      '<div class="hml-flow-guide"><div class="hml-flow-guide-text">' + hmlHtml(current.desc) + '</div></div>' +
      '<div class="hml-flow-footer"><button class="btn btn-default btn-sm" onclick="hmlCancelFlowDialog()">取消</button><button class="btn btn-default btn-sm" onclick="hmlStepBack()"' + (hmlCanGoPrevFlowPhase(state) ? '' : ' disabled') + '>上一步</button><button class="btn btn-success btn-sm" onclick="hmlToggleFlowAuto()">' + hmlFlowNextButtonText(state) + '</button></div>';
    root.html(guideHtml);
    return;
  }
  var html = hmlBuildFlowStageBar(state, steps, activeStep) + '<div class="hml-flow-body"><div class="hml-flow-list">' + list + '</div><div class="hml-flow-detail"><div class="hml-flow-detail-title">' + hmlHtml(current.title) + hmlStepHintHtml(current) + '</div><div class="hml-flow-detail-desc">' + hmlHtml(current.desc) + '</div><div class="hml-flow-stage">阶段：' + hmlHtml(current.stage) + '</div>' +
      (hmlStepRequiredLabel(current) ? '<div class="hml-flow-stage">类型：' + hmlStepRequiredLabel(current) + '</div>' : '') +
      (current.state === 'failed' && current.failure_msg ? '<div class="hml-tip" style="margin-top:12px;">' + hmlTipHtml(current.failure_msg) + '</div>' : '') +
      (current.warning_msg ? '<div class="hml-tip" style="margin-top:12px;">' + hmlTipHtml(current.warning_msg) + '</div>' : '') +
      '<div class="hml-step-actions">' +
        '<button class="btn btn-success btn-sm" onclick="hmlRunFlowStepWithCode()">执行当前步骤</button>' +
        hmlStepRepairButton(current) +
      '</div>' +
      '<div class="hml-flow-step-log"><div class="hml-flow-step-log-title">当前步骤日志</div><pre class="hml-flow-step-log-box">' + hmlStepLogsText(current) + '</pre></div>' +
    '</div></div>' +
    '<div class="hml-flow-footer"><button class="btn btn-default btn-sm" onclick="hmlCancelFlowDialog()">取消</button><button class="btn btn-default btn-sm" onclick="hmlStepBack()"' + (hmlCanGoPrevFlowPhase(state) ? '' : ' disabled') + '>上一步</button><button class="btn btn-success btn-sm" onclick="hmlToggleFlowAuto()">' + hmlFlowNextButtonText(state) + '</button></div>';
  root.html(html);
  var listEl = $('#hmlFlowDialog .hml-flow-list')[0];
  if (listEl) listEl.scrollTop = previousScrollTop;
  hmlScrollStepLogToBottomLater();
  if (state.auto_running || state.running || state.just_stepped) {
    setTimeout(function() {
      hmlCenterFlowStep(typeof state.focus_step === 'number' ? state.focus_step : activeStep);
    }, 0);
  }
  state.just_stepped = false;
}

function hmlJumpFlowStep(index) {
  var state = window.hmlFlowState;
  if (!state) return;
  var listEl = $('#hmlFlowDialog .hml-flow-list')[0];
  state.list_scroll_top = listEl ? listEl.scrollTop : 0;
  state.active_step = index;
  state.focus_step = index;
  var step = state.steps && state.steps[index];
  if (step) {
    if (!state.open_groups) state.open_groups = {};
    state.open_groups[hmlStepGroupTitle(step)] = true;
  }
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
  hmlEnsureStepLog(step);
  if (status === 'done') {
    step.state = 'done';
    if (step.effect === 'external_closed') hmlApplyExternalClosed();
    if (step.effect === 'external_open') hmlApplyExternalOpen();
    if (step.effect === 'role_standby') hmlApplyRole('standby');
    if (step.effect === 'role_master') hmlApplyRole('master');
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
    if (!step.logs || !step.logs.length) hmlAppendStepLog(step, '步骤执行完成');
    var finishedGroup = hmlStepGroupTitle(step);
    if (hmlIsFlowGroupDone(steps, finishedGroup)) {
      if (!state.open_groups) state.open_groups = {};
      state.open_groups[finishedGroup] = false;
    }
  }
  if (status === 'done' && steps.every(function(item) { return item.state === 'done'; })) {
    state.completed = true;
    state.auto_running = false;
    hmlState.switch_status = 'idle';
  }
}

function hmlGetFlowStepCode(step) {
  if (!step) return '# 待接入真实执行脚本';
  return step.code || ('# ' + step.title + '\n# 待接入真实执行脚本');
}

function hmlOpenFlowCodeDialog(step, confirm) {
  function openDialog(data) {
    var script = (data && data.script) ? data.script : hmlGetFlowStepCode(step);
    openEditCode({
      title: '执行当前步骤 - ' + (data && data.title ? data.title : step.title),
      content: script,
      mode: 'shell',
      width: '640px',
      height: '400px',
      submitBtn: '执行',
      onSubmit: function(content) {
        confirm(content);
        $('#openEditCodeCloseBtn').click();
      }
    });
  }
  hmlPost('get_step_script', {step_key: step.key, target_role: window.hmlFlowState ? window.hmlFlowState.target_role : ''}, function(data) {
    openDialog(data);
  }, function(res) {
    hmlAppendStepLog(step, '获取后端脚本失败，已使用流程配置脚本兜底：' + ((res && res.msg) || '未知错误'));
    hmlRenderFlowDialog($('#hmlFlowDialog'), window.hmlFlowState, window.hmlFlowState ? window.hmlFlowState.steps : []);
    openDialog({title: step.title, script: hmlGetFlowStepCode(step)});
  });
}

function hmlRunFlowStepWithCode() {
  hmlRunFlowStep(null, false, true);
}

function hmlRunFlowStep(done, skipConfirm, forceRun) {
  var state = window.hmlFlowState;
  if (!state) return;
  var listEl = $('#hmlFlowDialog .hml-flow-list')[0];
  state.list_scroll_top = listEl ? listEl.scrollTop : state.list_scroll_top || 0;
  var steps = state.steps;
  if (state.active_step < 0) state.active_step = 0;
  if (state.active_step >= steps.length) state.active_step = steps.length - 1;
  var step = steps[state.active_step];
  if (!step) return;
  if (state.running) {
    hmlAppendStepLog(step, '点击执行被忽略：当前已有步骤正在执行');
    hmlRenderFlowDialog($('#hmlFlowDialog'), state, steps);
    layer.msg('当前已有步骤正在执行，请稍后再试', {icon: 0});
    return;
  }
  if (!forceRun && steps.every(function(item) { return item.state === 'done'; })) {
    state.completed = true;
    state.auto_running = false;
    hmlRenderFlowDialog($('#hmlFlowDialog'), state, steps);
    if (done) done(true);
    return;
  }
  state.focus_step = state.active_step;
  if (step.guide) {
    hmlAppendStepLog(step, '进入提示步骤');
    hmlPromptNextFlow(state.target_role);
    hmlMarkCurrentFlowStep(state, steps, 'done');
    hmlRenderFlowDialog($('#hmlFlowDialog'), state, steps);
    if (done) done(true);
    return;
  }
  if (!skipConfirm) {
    hmlAppendStepLog(step, '正在打开脚本编辑框');
    hmlRenderFlowDialog($('#hmlFlowDialog'), state, steps);
    hmlOpenFlowCodeDialog(step, function(content) {
      hmlAppendStepLog(step, '已确认执行脚本，准备提交后端');
      hmlExecuteFlowStep(done, forceRun, content);
    });
    return;
  }
  hmlExecuteFlowStep(done, forceRun, '');
}

function hmlExecuteFlowStep(done, forceRun, scriptContent) {
  var state = window.hmlFlowState;
  if (!state) return;
  var listEl = $('#hmlFlowDialog .hml-flow-list')[0];
  state.list_scroll_top = listEl ? listEl.scrollTop : state.list_scroll_top || 0;
  var steps = state.steps;
  if (state.active_step < 0) state.active_step = 0;
  if (state.active_step >= steps.length) state.active_step = steps.length - 1;
  var step = steps[state.active_step];
  if (!step) return;
  state.completed = false;
  state.completed_view = false;
  step.failure_msg = '';
  hmlEnsureStepLog(step);
  if (step.logs.length) hmlAppendStepLog(step, '---------------- 本次执行开始 ----------------');
  hmlAppendStepLog(step, '开始执行');
  hmlMarkCurrentFlowStep(state, steps, 'running');
  hmlRenderFlowDialog($('#hmlFlowDialog'), state, steps);
  var runId = (state.flow_run_id || hmlCreateFlowRunId()) + '_' + hmlCreateRunId();
  state.current_run_id = runId;
  hmlAppendStepLog(step, '执行请求已创建 run_id=' + runId);
  step.active_run_log_prefix = step.logs.slice();
  hmlUpdateVisibleStepLog(step);
  scriptContent = scriptContent || '';
  hmlStopStepLogPolling();
  window.hmlStepLogTimer = setInterval(function() {
    if (!window.hmlFlowState || window.hmlFlowState !== state || state.current_run_id !== runId) return;
    hmlReadStepLog(runId, function(logData) {
      if (!window.hmlFlowState || window.hmlFlowState !== state || state.current_run_id !== runId) return;
      if (logData && logData.log) {
        hmlSetStepLogFromFile(step, logData);
      }
    });
  }, 500);
  hmlPost('run_step', {step_key: step.key, target_role: state.target_role, run_id: runId, script_content: scriptContent}, function(data) {
    if (!window.hmlFlowState || window.hmlFlowState !== state) return;
    hmlStopStepLogPolling();
    hmlReadStepLog(runId, function(logData) {
      if (!window.hmlFlowState || window.hmlFlowState !== state) return;
      var hasFileLog = hmlSetStepLogFromFile(step, logData);
      if (!hasFileLog) {
        hmlApplyStepLogFromResponse(step, data);
      }
      if (data.state_snapshot) hmlState = $.extend(true, hmlState, data.state_snapshot);
      hmlRefreshBrowserTitle();
      if (data.warning_msg) step.warning_msg = data.warning_msg;
      hmlMarkCurrentFlowStep(state, steps, 'done');
      if (!hasFileLog) {
        hmlApplyStepLogFromResponse(step, data);
      }
      if (!step.logs || !step.logs.length) hmlAppendStepLog(step, '步骤执行完成，但未读取到日志文件内容');
      step.active_run_log_prefix = null;
      state.current_run_id = '';
      hmlUpdateVisibleStepLog(step);
      hmlRenderFlowDialog($('#hmlFlowDialog'), state, steps);
      if (state.auto_running) {
        if (step.state === 'done') {
          state.flow_timer = setTimeout(hmlContinueCurrentFlowPhase, 180);
        } else {
          hmlPauseFlowAuto(true);
        }
      }
      if (done) done(step.state === 'done');
    });
  }, function(res) {
    if (!window.hmlFlowState || window.hmlFlowState !== state) return;
    hmlStopStepLogPolling();
    var data = (res && res.data) || {};
    hmlAppendStepLog(step, '后端执行接口返回失败：' + ((res && res.msg) || '未知错误'));
    hmlReadStepLog(runId, function(logData) {
      if (!window.hmlFlowState || window.hmlFlowState !== state) return;
      var hasFileLog = hmlSetStepLogFromFile(step, logData);
      if (!hasFileLog) {
        hmlApplyStepLogFromResponse(step, data);
      }
      if (data.state_snapshot) hmlState = $.extend(true, hmlState, data.state_snapshot);
      hmlRefreshBrowserTitle();
      step.repair_data = data.repair || null;
      step.failure_msg = (res && res.msg) || '步骤执行失败';
      hmlMarkCurrentFlowStep(state, steps, 'failed');
      if (!hasFileLog) {
        hmlApplyStepLogFromResponse(step, data);
      }
      if (!step.logs || !step.logs.length) hmlAppendStepLog(step, '步骤执行失败，但未读取到日志文件内容');
      step.active_run_log_prefix = null;
      state.current_run_id = '';
      hmlUpdateVisibleStepLog(step);
      hmlRenderFlowDialog($('#hmlFlowDialog'), state, steps);
      if (state.auto_running) hmlPauseFlowAuto(true);
      if (done) done(false);
    });
  });
}

function hmlFlowNextButtonText(state) {
  if (!state) return '继续执行';
  if (state.completed) return '下一步';
  var step = state.steps && state.steps[state.active_step];
  if (!step) return '继续执行';
  if (state.auto_running) return '暂停执行';
  if (step.guide) return '下一步';
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
  return true;
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
  var items = state.steps.filter(function(step) { return (step.phase || '') === stageKey; });
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
  if (state.completed) {
    state.completed_view = true;
    hmlPromptNextFlow(state.target_role);
    hmlRenderFlowDialog($('#hmlFlowDialog'), state, state.steps);
    return;
  }
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
  var allDone = hmlIsFlowPhaseReadyForNext(state);
  if (!allDone) return;
  if (phase === 'master_online') {
    state.completed = true;
    state.completed_view = true;
    hmlPromptNextFlow(state.target_role);
    hmlRenderFlowDialog($('#hmlFlowDialog'), state, state.steps);
    return;
  }
  var stages = hmlBuildFlowStages(state);
  var currentStageIndex = stages.findIndex(function(item) { return item.key === phase; });
  if (currentStageIndex < 0) return;
  var nextStage = stages[currentStageIndex + 1];
  if (!nextStage) {
    state.completed = true;
    state.completed_view = true;
    hmlPromptNextFlow(state.target_role);
    hmlRenderFlowDialog($('#hmlFlowDialog'), state, state.steps);
    return;
  }
  var nextIndex = state.steps.findIndex(function(step) { return (step.phase || '') === nextStage.key; });
  if (nextIndex < 0) return;
  state.active_step = nextIndex;
  state.focus_step = nextIndex;
  state.just_stepped = true;
  hmlRenderFlowDialog($('#hmlFlowDialog'), state, state.steps);
}

function hmlPromptNextFlow(flow) {
  var text = '流程已完成。';
  if (flow === 'standby_offline' || flow === 'standby') text = '降从流程完成。';
  if (flow === 'master_online' || flow === 'master') text = '升主流程完成。';
  hmlState.last_action = text;
  hmlLog(text);
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
  if (currentStageIndex === 0) return;
  if (currentStageIndex < 0) {
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
  hmlPost('reset_step', {step_key: state.steps[index].key, target_role: state.target_role}, function() {
    state.steps[index].state = 'pending';
    state.steps[index].logs = [];
    state.completed = false;
    state.running = false;
    state.active_step = Math.max(0, index - 1);
    state.focus_step = state.active_step;
    hmlLog('重置步骤：' + state.steps[index].title);
    hmlRenderFlowDialog($('#hmlFlowDialog'), state, state.steps);
  });
}

function hmlCancelFlowDialog() {
  var state = window.hmlFlowState;
  if (state) hmlPauseFlowAuto(false);
  hmlStopStepLogPolling();
  if (state && state.layer_id) layer.close(state.layer_id);
  window.hmlFlowState = null;
  hmlLoadState(function() {
    hmlRender();
  });
}

function hmlToggleExternalService() {
  if (hmlState.external_closed) {
    hmlPost('open_external_service', {}, function(data) {
      if (data.state_snapshot) hmlState = $.extend(true, hmlState, data.state_snapshot);
      hmlRefreshBrowserTitle();
      hmlLog('打开对外服务完成：OpenResty 已启动');
      layer.msg('已打开 OpenResty', {icon: 1});
      hmlRender();
    });
  } else {
    hmlPost('close_external_service', {}, function(data) {
      if (data.state_snapshot) hmlState = $.extend(true, hmlState, data.state_snapshot);
      hmlRefreshBrowserTitle();
      hmlLog('关闭对外服务完成：OpenResty 已停止');
      layer.msg('已关闭 OpenResty', {icon: 1});
      hmlRender();
    });
  }
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
  hmlRefreshBrowserTitle();
}

function hmlRunHealthCheck(fix) {
  hmlPost('health_check', {}, function(data) {
    hmlState.checks = data.checks || hmlState.checks;
    hmlState.health_status = data.health_status || hmlState.health_status;
    hmlState.health_text = data.health_text || hmlState.health_text;
    hmlState.external_closed = data.external_closed;
    hmlLog('重新自检完成，发现 ' + hmlState.checks.filter(function(item) { return item.status !== 'pass'; }).length + ' 个异常项');
    layer.msg('自检已刷新', {icon: 1});
    hmlSetView('health');
  });
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
