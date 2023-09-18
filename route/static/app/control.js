//默认显示7天周期图表
setTimeout(function(){
	Wday(0,'getload');
},500);
setTimeout(function(){
	Wday(0,'cpu');
},500);
setTimeout(function(){
	Wday(0,'mem');
},1000);
setTimeout(function(){
	Wday(0,'disk');
},1500);
setTimeout(function(){
	Wday(0,'network');
},2000);

$(".st").hover(function(){
	$(this).next().show();
},function(){
	$(this).next().hide();
	$(this).next().hover(function(){
		$(this).show();
	},function(){
		$(this).hide();
	})
})
$(".searcTime .gt").click(function(){
	$(this).addClass("on").siblings().removeClass("on");
})
$(".loadbtn").click(function(){
	$(this).parents(".searcTime").find("span").removeClass("on");
	$(this).parents(".searcTime").find(".st").addClass("on");
	var b = (new Date($(this).parent().find(".btime").val()).getTime())/1000;
	var e = (new Date($(this).parent().find(".etime").val()).getTime())/1000;
	b = Math.round(b);
	e = Math.round(e);
	getload(b,e)
})
$(".cpubtn").click(function(){
	$(this).parents(".searcTime").find("span").removeClass("on");
	$(this).parents(".searcTime").find(".st").addClass("on");
	var b = (new Date($(this).parent().find(".btime").val()).getTime())/1000;
	var e = (new Date($(this).parent().find(".etime").val()).getTime())/1000;
	b = Math.round(b);
	e = Math.round(e);
	cpu(b,e)
})
$(".membtn").click(function(){
	$(this).parents(".searcTime").find("span").removeClass("on");
	$(this).parents(".searcTime").find(".st").addClass("on");
	var b = (new Date($(this).parent().find(".btime").val()).getTime())/1000;
	var e = (new Date($(this).parent().find(".etime").val()).getTime())/1000;
	b = Math.round(b);
	e = Math.round(e);
	mem(b,e)
})
$(".diskbtn").click(function(){
	$(this).parents(".searcTime").find("span").removeClass("on");
	$(this).parents(".searcTime").find(".st").addClass("on");
	var b = (new Date($(this).parent().find(".btime").val()).getTime())/1000;
	var e = (new Date($(this).parent().find(".etime").val()).getTime())/1000;
	b = Math.round(b);
	e = Math.round(e);
	disk(b,e)
})
$(".networkbtn").click(function(){
	$(this).parents(".searcTime").find("span").removeClass("on");
	$(this).parents(".searcTime").find(".st").addClass("on");
	var b = (new Date($(this).parent().find(".btime").val()).getTime())/1000;
	var e = (new Date($(this).parent().find(".etime").val()).getTime())/1000;
	b = Math.round(b);
	e = Math.round(e);
	network(b,e)
})
//指定天数
function Wday(day,name){
	var now = (new Date().getTime())/1000;
	if(day==0){
		var b = (new Date(getToday() + " 00:00:01").getTime())/1000;
			b = Math.round(b);
		var e = Math.round(now);
	}
	if(day==1){
		var b = (new Date(getBeforeDate(day) + " 00:00:01").getTime())/1000;
		var e = (new Date(getBeforeDate(day) + " 23:59:59").getTime())/1000;
		b = Math.round(b);
		e = Math.round(e);
	}
	else{
		var b = (new Date(getBeforeDate(day) + " 00:00:01").getTime())/1000;
			b = Math.round(b);
		var e = Math.round(now);
	}
	switch (name){
		case "cpu":
			cpu(b,e);
			break;
		case "mem":
			mem(b,e);
			break;
		case "disk":
			disk(b,e);
			break;
		case "network":
			network(b,e);
			break;
		case "getload":
			getload(b,e);
			break;
	}
}

function getToday(){
   var mydate = new Date();
   var str = "" + mydate.getFullYear() + "/";
   str += (mydate.getMonth()+1) + "/";
   str += mydate.getDate();
   return str;
}

//取监控状态
function getStatus(){
	loadT = layer.msg('正在读取,请稍候...',{icon:16,time:0})
	$.post('/system/set_control','type=-1',function(rdata){
		layer.close(loadT);

		if(rdata.status){
			$("#openJK").html("<input class='btswitch btswitch-ios' id='ctswitch' type='checkbox' checked><label class='btswitch-btn' for='ctswitch' onclick='setControl(\"openjk\", true)'></label>");
			$("#notifySetting").show();
		} else {
			$("#openJK").html("<input class='btswitch btswitch-ios' id='ctswitch' type='checkbox'><label class='btswitch-btn' for='ctswitch' onclick='setControl(\"openjk\",false)'></label>");
			$("#notifySetting").hide();
		}

		if(rdata.notify_status){
			$("#openNotify").html("<input class='btswitch btswitch-ios' id='notify_switch' type='checkbox' checked><label class='btswitch-btn' for='notify_switch' onclick='setControl(\"opennotify\", true)'></label>");
		} else {
			$("#openNotify").html("<input class='btswitch btswitch-ios' id='notify_switch' type='checkbox'><label class='btswitch-btn' for='notify_switch' onclick='setControl(\"opennotify\",false)'></label>");
		}

		if(rdata.report_notify_status) {
			$("#openReport").html("<input class='btswitch btswitch-ios' id='report_notify_switch' type='checkbox' checked><label class='btswitch-btn' for='report_notify_switch' onclick='setControl(\"openReportNotify\", true)'></label>");
		} else {
			$("#openReport").html("<input class='btswitch btswitch-ios' id='report_notify_switch' type='checkbox'><label class='btswitch-btn' for='report_notify_switch' onclick='setControl(\"openReportNotify\",false)'></label>");
		}

		if(rdata.stat_all_status){
			$("#statAll").html("<input class='btswitch btswitch-ios' id='stat_witch' type='checkbox' checked><label class='btswitch-btn' for='stat_witch' onclick='setControl(\"stat\",true)'></label>");
		} else{
			$("#statAll").html("<input class='btswitch btswitch-ios' id='stat_witch' type='checkbox'><label class='btswitch-btn' for='stat_witch' onclick='setControl(\"stat\",false)'></label>");
		}

		$("#save_day").val(rdata.day);

	},'json');
}
getStatus();

//设置监控状态
function setControl(act, value=false){

	if (act == 'openjk'){
		var type = $("#ctswitch").prop('checked')?'0':'1';
		var day = $("#save_day").val();
		if(day < 1){
			layer.msg('保存天数不合法!',{icon:2});
			return;
		}
		if($("#ctswitch").prop('checked')) {
			$("#notifySetting").hide();
		} else {
			$("#notifySetting").show();
		}
	} else if (act == 'stat'){
		var type = $("#stat_witch").prop('checked')?'2':'3';
	} else if (act == 'save_day'){
		var type = $("#ctswitch").prop('checked')?'1':'0';
		var day = $("#save_day").val();

		if(type == 0){
			layer.msg('先开启监控!',{icon:2});
			return;
		}

		if(day < 1){
			layer.msg('保存天数不合法!',{icon:2});
			return;
		}
	} else if (act == 'opennotify'){
		var type = $("#notify_switch").prop('checked')?'4':'5';
	} else if (act == 'openReportNotify') {
		var type = $("#report_notify_switch").prop('checked')?'6':'7';
	}
	
	loadT = layer.msg('正在处理,请稍候...',{icon:16,time:0})
	$.post('/system/set_control','type='+type+'&day='+day,function(rdata){
		layer.close(loadT);
		layer.msg(rdata.msg,{icon:rdata.status?1:2});
	},'json');
}


//清理记录
function closeControl(){
	layer.confirm('您真的清空所有监控记录吗？',{title:'清空记录',icon:3,closeBtn:1}, function() {
		loadT = layer.msg('正在处理,请稍候...',{icon:16,time:0})
		$.post('/system/set_control','type=del',function(rdata){
			layer.close(loadT);
			layer.msg(rdata.msg,{icon:rdata.status?1:2});
		},'json');
	});
}


//定义周期时间
function getBeforeDate(n){
    var n = n;
    var d = new Date();
    var year = d.getFullYear();
    var mon=d.getMonth()+1;
    var day=d.getDate();
    if(day <= n){
		if(mon>1) {
		   mon=mon-1;
		}
		else {
		 year = year-1;
		 mon = 12;
		}
	}
	d.setDate(d.getDate()-n);
	year = d.getFullYear();
	mon=d.getMonth()+1;
	day=d.getDate();
    s = year+"/"+(mon<10?('0'+mon):mon)+"/"+(day<10?('0'+day):day);
    return s;
}
//cpu
function cpu(b,e){
	$.get('/system/get_cpu_io?start='+b+'&end='+e,function(rdata){
		var myChartCpu = echarts.init(document.getElementById('cupview'));
		var xData = [];
		var yData = [];
		//var zData = [];
		
		for(var i = 0; i < rdata.length; i++){
			xData.push(rdata[i].addtime);
			yData.push(rdata[i].pro);
			//zData.push(rdata[i].mem);
		}
		option = {
			tooltip: {
				trigger: 'axis',
				axisPointer: {
					type: 'cross'
				},
				formatter: '{b}<br />{a}: {c}%'
			},
			xAxis: {
				type: 'category',
				boundaryGap: false,
				data: xData,
				axisLine:{
					lineStyle:{
						color:"#666"
					}
				}
			},
			yAxis: {
				type: 'value',
				name: lan.public.pre,
				boundaryGap: [0, '100%'],
				min:0,
				max: 100,
				splitLine:{
					lineStyle:{
						color:"#ddd"
					}
				},
				axisLine:{
					lineStyle:{
						color:"#666"
					}
				}
			},
			dataZoom: [{
				type: 'inside',
				start: 0,
				end: 100,
				zoomLock:true
			}, {
				start: 0,
				end: 100,
				handleIcon: 'M10.7,11.9v-1.3H9.3v1.3c-4.9,0.3-8.8,4.4-8.8,9.4c0,5,3.9,9.1,8.8,9.4v1.3h1.3v-1.3c4.9-0.3,8.8-4.4,8.8-9.4C19.5,16.3,15.6,12.2,10.7,11.9z M13.3,24.4H6.7V23h6.6V24.4z M13.3,19.6H6.7v-1.4h6.6V19.6z',
				handleSize: '80%',
				handleStyle: {
					color: '#fff',
					shadowBlur: 3,
					shadowColor: 'rgba(0, 0, 0, 0.6)',
					shadowOffsetX: 2,
					shadowOffsetY: 2
				}
			}],
			series: [
				{
					name:'CPU',
					type:'line',
					smooth:true,
					symbol: 'none',
					sampling: 'average',
					itemStyle: {
						normal: {
							color: 'rgb(0, 153, 238)'
						}
					},
					data: yData
				}
			]
		};
		myChartCpu.setOption(option);
	    window.addEventListener("resize",function(){
			myChartCpu.resize();
		});
	},'json');
}

//内存
function mem(b,e){
	$.get('/system/get_cpu_io?start='+b+'&end='+e,function(rdata){
		var myChartMen = echarts.init(document.getElementById('memview'));
		var xData = [];
		//var yData = [];
		var zData = [];
		
		for(var i = 0; i < rdata.length; i++){
			xData.push(rdata[i].addtime);
			//yData.push(rdata[i].pro);
			zData.push(rdata[i].mem);
		}
		option = {
			tooltip: {
				trigger: 'axis',
				axisPointer: {
					type: 'cross'
				},
				formatter: '{b}<br />{a}: {c}%'
			},
			xAxis: {
				type: 'category',
				boundaryGap: false,
				data: xData,
				axisLine:{
					lineStyle:{
						color:"#666"
					}
				}
			},
			yAxis: {
				type: 'value',
				name: lan.public.pre,
				boundaryGap: [0, '100%'],
				min:0,
				max: 100,
				splitLine:{
					lineStyle:{
						color:"#ddd"
					}
				},
				axisLine:{
					lineStyle:{
						color:"#666"
					}
				}
			},
			dataZoom: [{
				type: 'inside',
				start: 0,
				end: 100,
				zoomLock:true
			}, {
				start: 0,
				end: 100,
				handleIcon: 'M10.7,11.9v-1.3H9.3v1.3c-4.9,0.3-8.8,4.4-8.8,9.4c0,5,3.9,9.1,8.8,9.4v1.3h1.3v-1.3c4.9-0.3,8.8-4.4,8.8-9.4C19.5,16.3,15.6,12.2,10.7,11.9z M13.3,24.4H6.7V23h6.6V24.4z M13.3,19.6H6.7v-1.4h6.6V19.6z',
				handleSize: '80%',
				handleStyle: {
					color: '#fff',
					shadowBlur: 3,
					shadowColor: 'rgba(0, 0, 0, 0.6)',
					shadowOffsetX: 2,
					shadowOffsetY: 2
				}
			}],
			series: [
				{
					name:lan.index.process_mem,
					type:'line',
					smooth:true,
					symbol: 'none',
					sampling: 'average',
					itemStyle: {
						normal: {
							color: 'rgb(0, 153, 238)'
						}
					},
					data: zData
				}
			]
		};
		myChartMen.setOption(option);
		window.addEventListener("resize",function(){
			myChartMen.resize();
		});
	},'json');
}

//磁盘io
function disk(b,e){
	$.get('/system/get_disk_io?start='+b+'&end='+e,function(rdata){
		var myChartDisk = echarts.init(document.getElementById('diskview'));
		var rData = [];
		var wData = [];
		var xData = [];
		//var yData = [];
		//var zData = [];
		
		for(var i = 0; i < rdata.length; i++){
			rData.push((rdata[i].read_bytes/1024/60).toFixed(3));
			wData.push((rdata[i].write_bytes/1024/60).toFixed(3));
			xData.push(rdata[i].addtime);
			//yData.push(rdata[i].read_count);
			//zData.push(rdata[i].write_count);
		}
		option = {
			tooltip: {
				trigger: 'axis',
				axisPointer: {
					type: 'cross'
				},
				formatter:"时间：{b0}<br />{a0}: {c0} Kb/s<br />{a1}: {c1} Kb/s", 
			},
			legend: {
				data:['读取字节数','写入字节数']
			},
			xAxis: {
				type: 'category',
				boundaryGap: false,
				data: xData,
				axisLine:{
					lineStyle:{
						color:"#666"
					}
				}
			},
			yAxis: {
				type: 'value',
				name: '单位:KB/s',
				boundaryGap: [0, '100%'],
				splitLine:{
					lineStyle:{
						color:"#ddd"
					}
				},
				axisLine:{
					lineStyle:{
						color:"#666"
					}
				}
			},
			dataZoom: [{
				type: 'inside',
				start: 0,
				end: 100,
				zoomLock:true
			}, {
				start: 0,
				end: 100,
				handleIcon: 'M10.7,11.9v-1.3H9.3v1.3c-4.9,0.3-8.8,4.4-8.8,9.4c0,5,3.9,9.1,8.8,9.4v1.3h1.3v-1.3c4.9-0.3,8.8-4.4,8.8-9.4C19.5,16.3,15.6,12.2,10.7,11.9z M13.3,24.4H6.7V23h6.6V24.4z M13.3,19.6H6.7v-1.4h6.6V19.6z',
				handleSize: '80%',
				handleStyle: {
					color: '#fff',
					shadowBlur: 3,
					shadowColor: 'rgba(0, 0, 0, 0.6)',
					shadowOffsetX: 2,
					shadowOffsetY: 2
				}
			}],
			series: [
				{
					name:'读取字节数',
					type:'line',
					smooth:true,
					symbol: 'none',
					sampling: 'average',
					itemStyle: {
						normal: {
							color: 'rgb(255, 70, 131)'
						}
					},
					data: rData
				},
				{
					name:'写入字节数',
					type:'line',
					smooth:true,
					symbol: 'none',
					sampling: 'average',
					itemStyle: {
						normal: {
							color: 'rgba(46, 165, 186, .7)'
						}
					},
					data: wData
				}
			]
		};
		myChartDisk.setOption(option);
		window.addEventListener("resize",function(){
			myChartDisk.resize();
		});
	},'json');
}

//网络Io
function network(b,e){
	$.get('/system/get_network_io?start='+b+'&end='+e,function(rdata){
		var myChartNetwork = echarts.init(document.getElementById('network'));
		var aData = [];
		var bData = [];
		var cData = [];
		var dData = [];
		var xData = [];
		var yData = [];
		var zData = [];
		
		for(var i = 0; i < rdata.length; i++){
			aData.push(rdata[i].total_up);
			bData.push(rdata[i].total_down);
			cData.push(rdata[i].down_packets);
			dData.push(rdata[i].up_packets);
			xData.push(rdata[i].addtime);
			yData.push(rdata[i].up);
			zData.push(rdata[i].down);
		}
		option = {
			tooltip: {
				trigger: 'axis',
				axisPointer: {
					type: 'cross'
				}
			},
			legend: {
				data:[lan.index.net_up,lan.index.net_down]
			},
			xAxis: {
				type: 'category',
				boundaryGap: false,
				data: xData,
				axisLine:{
					lineStyle:{
						color:"#666"
					}
				}
			},
			yAxis: {
				type: 'value',
				name: lan.index.unit+':KB/s',
				boundaryGap: [0, '100%'],
				splitLine:{
					lineStyle:{
						color:"#ddd"
					}
				},
				axisLine:{
					lineStyle:{
						color:"#666"
					}
				}
			},
			dataZoom: [{
				type: 'inside',
				start: 0,
				end: 100,
				zoomLock:true
			}, {
				start: 0,
				end: 100,
				handleIcon: 'M10.7,11.9v-1.3H9.3v1.3c-4.9,0.3-8.8,4.4-8.8,9.4c0,5,3.9,9.1,8.8,9.4v1.3h1.3v-1.3c4.9-0.3,8.8-4.4,8.8-9.4C19.5,16.3,15.6,12.2,10.7,11.9z M13.3,24.4H6.7V23h6.6V24.4z M13.3,19.6H6.7v-1.4h6.6V19.6z',
				handleSize: '80%',
				handleStyle: {
					color: '#fff',
					shadowBlur: 3,
					shadowColor: 'rgba(0, 0, 0, 0.6)',
					shadowOffsetX: 2,
					shadowOffsetY: 2
				}
			}],
			series: [
				{
					name:lan.index.net_up,
					type:'line',
					smooth:true,
					symbol: 'none',
					sampling: 'average',
					itemStyle: {
						normal: {
							color: 'rgb(255, 140, 0)'
						}
					},
					data: yData
				},
				{
					name:lan.index.net_down,
					type:'line',
					smooth:true,
					symbol: 'none',
					sampling: 'average',
					itemStyle: {
						normal: {
							color: 'rgb(30, 144, 255)'
						}
					},
					data: zData
				}
			]
		};
		myChartNetwork.setOption(option);
		window.addEventListener("resize",function(){
			myChartNetwork.resize();
		});
	},'json');
}
//负载
function getload_old(b,e){
	$.get('/system/get_load_average?start='+b+'&end='+e,function(rdata){
		var myChartgetload = echarts.init(document.getElementById('getloadview'));
		var aData = [];
		var bData = [];
		var xData = [];
		var yData = [];
		var zData = [];
		
		for(var i = 0; i < rdata.length; i++){
			xData.push(rdata[i].addtime);
			yData.push(rdata[i].pro);
			zData.push(rdata[i].one);
			aData.push(rdata[i].five);
			bData.push(rdata[i].fifteen);
		}
		option = {
			tooltip: {
				trigger: 'axis'
			},
			calculable: true,
			legend: {
				data:['系统资源使用率','1分钟','5分钟','15分钟'],
				selectedMode: 'single',
			},
			xAxis: {
				type: 'category',
				boundaryGap: false,
				data: xData,
				axisLine:{
					lineStyle:{
						color:"#666"
					}
				}
			},
			yAxis: {
				type: 'value',
				name: '',
				boundaryGap: [0, '100%'],
				splitLine:{
					lineStyle:{
						color:"#ddd"
					}
				},
				axisLine:{
					lineStyle:{
						color:"#666"
					}
				}
			},
			dataZoom: [{
				type: 'inside',
				start: 0,
				end: 100,
				zoomLock:true
			}, {
				start: 0,
				end: 100,
				handleIcon: 'M10.7,11.9v-1.3H9.3v1.3c-4.9,0.3-8.8,4.4-8.8,9.4c0,5,3.9,9.1,8.8,9.4v1.3h1.3v-1.3c4.9-0.3,8.8-4.4,8.8-9.4C19.5,16.3,15.6,12.2,10.7,11.9z M13.3,24.4H6.7V23h6.6V24.4z M13.3,19.6H6.7v-1.4h6.6V19.6z',
				handleSize: '80%',
				handleStyle: {
					color: '#fff',
					shadowBlur: 3,
					shadowColor: 'rgba(0, 0, 0, 0.6)',
					shadowOffsetX: 2,
					shadowOffsetY: 2
				}
			}],
			series: [
				{
					name:'系统资源使用率',
					type:'line',
					smooth:true,
					symbol: 'none',
					sampling: 'average',
					itemStyle: {
						normal: {
							color: 'rgb(255, 140, 0)'
						}
					},
					data: yData
				},
				{
					name:'1分钟',
					type:'line',
					smooth:true,
					symbol: 'none',
					sampling: 'average',
					itemStyle: {
						normal: {
							color: 'rgb(30, 144, 255)'
						}
					},
					data: zData
				},
				{
					name:'5分钟',
					type:'line',
					smooth:true,
					symbol: 'none',
					sampling: 'average',
					itemStyle: {
						normal: {
							color: 'rgb(0, 178, 45)'
						}
					},
					data: aData
				},
				{
					name:'15分钟',
					type:'line',
					smooth:true,
					symbol: 'none',
					sampling: 'average',
					itemStyle: {
						normal: {
							color: 'rgb(147, 38, 255)'
						}
					},
					data: bData
				}
			]
		};
		myChartgetload.setOption(option);
		window.addEventListener("resize",function(){
			myChartgetload.resize();
		});
	},'json');
}
//系统负载
function getload(b,e){
	$.get('/system/get_load_average?start='+b+'&end='+e,function(rdata){
		var myChartgetload = echarts.init(document.getElementById('getloadview'));
		var aData = [];
		var bData = [];
		var xData = [];
		var yData = [];
		var zData = [];
		
		for(var i = 0; i < rdata.length; i++){
			xData.push(rdata[i].addtime);
			yData.push(rdata[i].pro);
			zData.push(rdata[i].one);
			aData.push(rdata[i].five);
			bData.push(rdata[i].fifteen);
		}
		option = {
			animation: false,
			tooltip: {
				trigger: 'axis',
				axisPointer: {
	                type: 'cross'
	            }
			},
			legend: {
				data:['1分钟','5分钟','15分钟'],
				right:'16%',
				top:'10px'
			},
			axisPointer: {
				link: {xAxisIndex: 'all'},
				lineStyle: {
					color: '#aaaa',
					width: 1
				}
			},
			grid: [{ // 直角坐标系内绘图网格
					top: '60px',
					left: '5%',
					right: '55%',
					width: '40%',
					height: 'auto'
				},
				{
					top: '60px',
					left: '55%',
					width: '40%',
					height: 'auto'
				}
			],
			xAxis: [

				{ // 直角坐标系grid的x轴
					type: 'category',
					axisLine: {
						lineStyle: {
							color: '#666'
						}
					},
					data: xData
				},
				{ // 直角坐标系grid的x轴
					type: 'category',
					gridIndex: 1,
					axisLine: {
						lineStyle: {
							color: '#666'
						}
					},
					data: xData
				},
			],
			yAxis: [{
					scale: true,
					name: '资源使用率%',
					splitLine: { // y轴网格显示
						show: true,
						lineStyle:{
							color:"#ddd"
						}
					},
					nameTextStyle: { // 坐标轴名样式
						color: '#666',
						fontSize: 12,
						align: 'left'
					},
					axisLine:{
						lineStyle:{
							color: '#666',
						}
					}
				},
				{
					scale: true,
					name: '负载详情',
					gridIndex: 1,
					splitLine: { // y轴网格显示
						show: true,
						lineStyle:{
							color:"#ddd"
						}
					},
					nameTextStyle: { // 坐标轴名样式
						color: '#666',
						fontSize: 12,
						align: 'left'
					},
					axisLine:{
						lineStyle:{
							color: '#666',
						}
					}
				},
			],
			dataZoom: [{
				type: 'inside',
				start: 0,
				end: 100,
				xAxisIndex:[0,1],
				zoomLock:true
			}, {
				xAxisIndex: [0, 1],
	            type: 'slider',
				start: 0,
				end: 100,
				handleIcon: 'M10.7,11.9v-1.3H9.3v1.3c-4.9,0.3-8.8,4.4-8.8,9.4c0,5,3.9,9.1,8.8,9.4v1.3h1.3v-1.3c4.9-0.3,8.8-4.4,8.8-9.4C19.5,16.3,15.6,12.2,10.7,11.9z M13.3,24.4H6.7V23h6.6V24.4z M13.3,19.6H6.7v-1.4h6.6V19.6z',
				handleSize: '80%',
				handleStyle: {
					color: '#fff',
					shadowBlur: 3,
					shadowColor: 'rgba(0, 0, 0, 0.6)',
					shadowOffsetX: 2,
					shadowOffsetY: 2
				},
				left:'5%',
				right:'5%'
			}],
			series: [
				{
					name: '资源使用率%',
					type: 'line',
					lineStyle: {
						normal: {
							width: 2,
							color: 'rgb(255, 140, 0)'
						}
					},
					itemStyle: {
						normal: {
							color: 'rgb(255, 140, 0)'
						}
					},
					data: yData
				},
				{
					xAxisIndex: 1,
					yAxisIndex: 1,
					name: '1分钟',
					type: 'line',
					lineStyle: {
						normal: {
							width: 2,
							color: 'rgb(30, 144, 255)'
						}
					},
					itemStyle: {
						normal: {
							color: 'rgb(30, 144, 255)'
						}
					},
					data: zData
				},
				{
					xAxisIndex: 1,
					yAxisIndex: 1,
					name: '5分钟',
					type: 'line',
					lineStyle: {
						normal: {
							width: 2,
							color: 'rgb(0, 178, 45)'
						}
					},
					itemStyle: {
						normal: {
							color: 'rgb(0, 178, 45)'
						}
					},
					data: aData
				},
				{
					xAxisIndex: 1,
					yAxisIndex: 1,
					name: '15分钟',
					type: 'line',
					lineStyle: {
						normal: {
							width: 2,
							color: 'rgb(147, 38, 255)'
						}
					},
					itemStyle: {
						normal: {
							color: 'rgb(147, 38, 255)'
						}
					},
					data: bData
				}
			],
			textStyle: {
				color: '#666',
				fontSize: 12
			}
		}
		myChartgetload.setOption(option);
		window.addEventListener("resize",function(){
			myChartgetload.resize();
		})
	},'json')
}

function setNotifyValue() {
	let data = $("#notifyValueForm").serialize()
	$.post("/system/set_notify_value", data, function(rdata) {
		if(rdata.status) {
			layer.closeAll();
			layer.msg(rdata.msg, {icon: 1});
		} else {
			layer.msg(rdata.msg, {icon: 2});
		}
	},'json');
}

function openSetNotifyValue() {
	var loadT = layer.msg('正在获取中...', { icon: 16, time: 0});
	$.post("/system/get_notify_value", '', function(rdata) {
		if(rdata.status) {
			layer.close(loadT);
			let data = rdata.data
			layer.open({
				type: 1,
				area: "290px",
				title: '配置异常阈值',
				closeBtn: 1,
				shift: 5,
				shadeClose: false,
				content: "<form id='notifyValueForm' class='nitify-value-form bt-form pd20 pb70'>\
					<div class='line'>\
						<span class='tname'>CPU</span>\
						<div class='info-r plan_hms bt-input-text'>\
							<span><input type='number' name='cpu' value='" + (data.cpu == null? 80: data.cpu) + "' maxlength='3' max='100' min='-1'></span>\
							<span class='name'>%</span>\
						</div>\
					</div>\
					<div class='line'>\
						<span class='tname'>内存</span>\
						<div class='info-r plan_hms bt-input-text'>\
							<span><input type='number' name='memory' value='" + (data.memory == null? 80: data.memory) + "' maxlength='3' max='100' min='-1'></span>\
							<span class='name'>%</span>\
						</div>\
					</div>\
					<div class='line'>\
						<span class='tname'>磁盘容量</span>\
						<div class='info-r plan_hms bt-input-text'>\
							<span><input type='number' name='disk' value='" + (data.disk == null? 80: data.disk) + "' maxlength='3' max='100' min='-1'></span>\
							<span class='name'>%</span>\
						</div>\
					</div>\
					<div class='line'>\
						<span class='tname'>SSL证书预提醒</span>\
						<div class='info-r plan_hms bt-input-text'>\
							<span><input type='number' name='ssl_cert' value='" + (data.ssl_cert == null? 14: data.ssl_cert) + "' maxlength='3' min='0'></span>\
							<span class='name'>天</span>\
						</div>\
					</div>\
					<div class='bt-form-submit-btn'>\
						<button type='button' class='btn btn-danger btn-sm' onclick=\"layer.closeAll()\">关闭</button>\
						<button type='button' class='btn btn-success btn-sm' onclick=\"setNotifyValue()\">修改</button>\
					</div>\
				</form>"
			})
		} else {
			layer.msg(b.msg, {icon: 2});
		}
	},'json');
}



//下拉菜单名称
function getselectname(){
	$(".dropdown ul li a").click(function(){
		var txt = $(this).text();
		var type = $(this).attr("value");
		$(this).parents(".dropdown").find("button b").text(txt).attr("val",type);
	});
}

var cycleArray = { 'day': '每天', 'day-n': 'N天', 'hour': '每小时', 'hour-n': 'N小时', 'minute-n': 'N分钟', 'week': '每星期', 'month': '每月' }
var weekArray = { 1: '周一', 2: '周二', 3: '周三', 4: '周四', 5: '周五', 6: '周六', 0: '周日' }
var reportCycleValue = {} 

//清理
function closeOpt(){
	$("#ptime").html('');
}

//星期
function toWeek(){
	var mBody = '<div class="dropdown planweek pull-left mr20">\
				  <button class="btn btn-default dropdown-toggle" type="button" id="excode_week" data-toggle="dropdown">\
					<b val="0">' + weekArray[parseInt(reportCycleValue.week || '0')] + '</b> <span class="caret"></span>\
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
	$("#ptime").html(mBody);
	getselectname();
}
//指定1
function toWhere1(ix){
	var mBody ='<div class="plan_hms pull-left mr20 bt-input-text">\
					<span><input type="number" name="where1" value="' + (reportCycleValue.where1 || 3) + '" maxlength="2" max="31" min="0"></span>\
					<span class="name">'+ix+'</span>\
				</div>';
	$("#ptime").append(mBody);
}
//小时
function toHour(){
	var mBody = '<div class="plan_hms pull-left mr20 bt-input-text">\
					<span><input type="number" name="hour" value="' + (reportCycleValue.hour || 0) + '" maxlength="2" max="23" min="0"></span>\
					<span class="name">小时</span>\
					</div>';
	$("#ptime").append(mBody);
}

//分钟
function toMinute(){
	var mBody = '<div class="plan_hms pull-left mr20 bt-input-text">\
					<span><input type="number" name="minute" value="' + (reportCycleValue.minute || 0) + '" maxlength="2" max="59" min="0"></span>\
					<span class="name">分钟</span>\
					</div>';
	$("#ptime").append(mBody);	
}

function handleStypeChange(type){
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

function openSetReportCycle() {
	var loadT = layer.msg('正在获取中...', { icon: 16, time: 0});
	$.post("/system/get_report_cycle", '', function(rdata) {
		if(rdata.status) {
			layer.close(loadT);
			reportCycleValue = rdata.data

			layer.open({
				type: 1,
				skin: "report-cycle-layer",
				area: "550px",
				title: '配置报告频率',
				closeBtn: 1,
				shift: 5,
				btn: ['保存', '取消'],
				shadeClose: false,
				content: "<div id='reportCycleMain' class='report-cycle-main pd20 pb70'>\
					<div class='clearfix plan'>\
						<div class='dropdown plancycle pull-left mr20'>\
							<button class='btn btn-default dropdown-toggle' type='button' id='cycle' data-toggle='dropdown' style='width:94px'>\
																<b val='" + (reportCycleValue.type || 'week') + "'>" + cycleArray[reportCycleValue.type || 'week'] + "</b>\
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
						<div id='ptime' class='pull-left'>\
							<div class='dropdown planweek pull-left mr20'>\
								<button class='btn btn-default dropdown-toggle' type='button' id='excode' data-toggle='dropdown'>\
									<b val='0'>" + weekArray[parseInt(reportCycleValue.week || '0')] + "</b>\
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
								<span><input type='number' name='hour' value='" + (reportCycleValue.hour || 0) + "' maxlength='2' max='23' min='0'></span>\
								<span class='name'>小时</span>\
							</div>\
							<div class='plan_hms pull-left mr20 bt-input-text'>\
								<span><input type='number' name='minute' value='" + (reportCycleValue.minute || 0) + "' maxlength='2' max='59' min='0'></span>\
								<span class='name'>分钟</span>\
							</div>\
						</div>\
					</div>\
					<form id='set-Config' action='/crontab/add' enctype='multipart/form-data' method='post' style='display: none;'>\
						<input type='text' name='type' value='' />\
						<input type='number' name='where1' value='' />\
						<input type='number' name='hour' value='' />\
						<input type='number' name='minute' value='' />\
						<input type='text' name='week' value='' />\
						<input type='submit' />\
					</form>\
				</div>",
				success: function(index, layers) {
					$(".dropdown ul li a").click(function() {
						var txt = $(this).text();
						var type = $(this).attr("value");
						$(this).parents(".dropdown").find("button b").text(txt).attr("val",type);
						handleStypeChange(type);
					});
					if(reportCycleValue.type) {
						handleStypeChange(reportCycleValue.type);
					}
				},
				yes: function(layero, layer_id) {
					submitReportCycleForm();
				}
			})
		} else {
			layer.msg(b.msg, {icon: 2});
		}
	},'json');
}

function submitReportCycleForm() {
	var type = $(".plancycle").find("b").attr("val");
	$("#set-Config input[name='type']").val(type);

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
	
	var where1 = $('#excode_week b').attr('val');
	$("#set-Config input[name='where1']").val(where1);

	// if(where1 > is1 || where1 < is2){
	// 	$("#ptime input[name='where1']").focus();
	// 	layer.msg('表单不合法,请重新输入!',{icon:2});
	// 	return;
	// }
	
	var hour = $("#ptime input[name='hour']").val();
	if(hour > 23 || hour < 0){
		$("#ptime input[name='hour']").focus();
		layer.msg('小时值不合法!',{icon:2});
		return;
	}
	$("#set-Config input[name='hour']").val(hour);
	var minute = $("#ptime input[name='minute']").val();
	if(minute > 59 || minute < 0){
		$("#ptime input[name='minute']").focus();
		layer.msg('分钟值不合法!',{icon:2});
		return;
	}
	$("#set-Config input[name='minute']").val(minute);
	
	if (type == 'minute-n'){
		var where1 = $("#ptime input[name='where1']").val();
		$("#set-Config input[name='where1']").val(where1);
	}

	if (type == 'day-n'){
		var where1 = $("#ptime input[name='where1']").val();
		$("#set-Config input[name='where1']").val(where1);
	}

	if (type == 'hour-n'){
		var where1 = $("#ptime input[name='where1']").val();
		$("#set-Config input[name='where1']").val(where1);
	}

	if (type == 'week'){
		// TODO 星期暂时写死0，待完善逻辑
		// var where1 = $("#ptime input[name='where1']").val();
		var where1 = 0;
		$("#set-Config input[name='where1']").val(where1);
	}
	let data = $("#set-Config").serialize()
	console.log("data", data)
	$.post("/system/set_report_cycle", data, function(rdata) {
		if(rdata.status) {
			layer.closeAll();
			layer.msg(rdata.msg, {icon: 1});
		} else {
			layer.msg(rdata.msg, {icon: 2});
		}
	},'json');
}