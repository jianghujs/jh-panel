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

		if(rdata.stat_all_status){
			$("#statAll").html("<input class='btswitch btswitch-ios' id='stat_witch' type='checkbox' checked><label class='btswitch-btn' for='stat_witch' onclick='setControl(\"stat\",true)'></label>");
		} else{
			$("#statAll").html("<input class='btswitch btswitch-ios' id='stat_witch' type='checkbox'><label class='btswitch-btn' for='stat_witch' onclick='setControl(\"stat\",false)'></label>");
		}

		$("#save_day").val(rdata.day);
        
        getSystemReportCron()

        $("#systemReportCronDetail .open-cron-selecter-layer").click(() => {
            openCronSelectorLayer(systemReportCron, {yes: addOrUpdateSystemReportCron});
        });
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
  debugger
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
				title: '异常通知配置',
				closeBtn: 1,
				shift: 5,
				shadeClose: false,
				content: "<form id='notifyValueForm' class='nitify-value-form bt-form pd20 pb70'>\
          <b>提醒开关：</b>\
          <div class='line flex align-center'\
						<em class='mr20'>MySQL主从同步</em>\
            <div class='pl5 pt5' id='openMysqlSlaveStatusNoticeSwitch'></div>\
          </div>\
          <input type='number' name='mysql_slave_status_notice' value='" + (data.mysql_slave_status_notice) + "' style='display:none;'>\
					<div class='line flex align-center'\
						<em class='mr20'>Rsync服务</em>\
            <div class='pl5 pt5' id='openRsyncStatusNoticeSwitch'></div>\
          </div>\
          <input type='number' name='rsync_status_notice' value='" + (data.rsync_status_notice) + "' style='display:none;'>\
          <b>异常阈值：</b>\
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
          <div style='margin-bottom: 10px; color: #cecece;'>提示：配置为-1关闭异常通知</div>\
					<div class='bt-form-submit-btn'>\
						<button type='button' class='btn btn-danger btn-sm' onclick=\"layer.closeAll()\">关闭</button>\
						<button type='button' class='btn btn-success btn-sm' onclick=\"setNotifyValue()\">修改</button>\
					</div>\
				</form>",

			});

      $("#openMysqlSlaveStatusNoticeSwitch").createRadioSwitch(data.mysql_slave_status_notice, (checked) => {
        $("input[name='mysql_slave_status_notice']").val(checked? 1: 0);
      });

      $("#openRsyncStatusNoticeSwitch").createRadioSwitch(data.rsync_status_notice, (checked) => {
        $("input[name='rsync_status_notice']").val(checked? 1: 0);
      });
		} else {
			layer.msg(b.msg, {icon: 2});
		}
	},'json');
}







// NEW 配置服务器报告

var defaultSystemReportCron = {      
    name: '[勿删]服务器报告',
    type: 'day',
    where1: '',
    hour: 0,
    minute: 0,
    week: '',
    sType: 'toShell',
    stype: 'toShell',
    sName: '',
    backupTo: 'localhost' };
var systemReportCron = {...defaultSystemReportCron};


function getSystemReportCron() {
    $.post('/crontab/get', { name: systemReportCron.name },function(rdata){
        const { status: openSystemReportCron } = rdata;
        if (openSystemReportCron) {
            systemReportCron = rdata.data;
        } else {
            systemReportCron = {...defaultSystemReportCron};
        }
        visibleDom('#systemReportCronDetail', openSystemReportCron);
        $("#openSystemReportCronSwitch").createRadioSwitch(openSystemReportCron, (checked) => {
            visibleDom('#systemReportCronDetail', checked);
            if(checked) {
                addOrUpdateSystemReportCron();
            } else {
                deleteCron(systemReportCron.id);
            }
        });
    },'json');
}



async function addOrUpdateSystemReportCron(cronSelectorData) {
    systemReportCron.sBody = systemReportCron.sbody = `
#!/bin/sh
pushd /www/server/jh-panel > /dev/null
bash /www/server/jh-panel/scripts/system_report.sh
popd > /dev/null
`
    data = {...systemReportCron, ...cronSelectorData}
    $.post(systemReportCron.id? '/crontab/modify_crond': '/crontab/add', data,function(rdata){
        $.post("/system/set_report_cycle_file", data, function(rdata) {},'json');
        getSystemReportCron();
        layer.msg(rdata.msg,{icon:rdata.status?1:2}, 5000);
    },'json');
}

function deleteCron(id) {
    if (id) {
        $.post('/crontab/del', { id },function(rdata){
            getSystemReportCron();
            layer.msg(rdata.msg,{icon:rdata.status?1:2}, 5000);
        },'json');
    }
}
