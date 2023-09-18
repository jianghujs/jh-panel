var webShell = null;

$(window).unload(() => {
	webShell.dropInstance();
});

class WebShell {
	constructor() {
			this.socket = null;
			this.gterm = null;
			this.term_box = null;
			this.socketLoading = false;
			this.interval = null;
			this.connected = false;
	}

	static getInstance() {
		if (webShell == null)
			webShell = new WebShell();
		return webShell;
	}
	
	dropInstance() {
		layer.closeAll();
		this.gterm.destroy();
		clearInterval(this.interval);
		if (this.socket) {
				this.socket.emit('disconnect_to_ssh', '');
				this.socket.disconnect();
				this.socket.close();
				this.socket = null;
		}
		webShell = null;
	}

	async initTerm() {
		return new Promise((resolve, reject) => {
			console.log("开始创建终端")
			var termCols = 83;
			var termRows = 21;
			var sendTotal = 0;
			var term = new Terminal({ 
				cols: termCols, 
				rows: termRows, 
				screenKeys: true, 
				useStyle: true
			});

			term.open();
			term.setOption('cursorBlink', true);
			term.setOption('fontSize', 14);
			this.gterm = term;
			resolve(this.gterm);
		});
	}

	async initSocket() {
		return new Promise((resolve, reject) => {
			if (this.socketLoading) return;
			if (this.socket) {
				resolve(this.socket);
				return
			}
			console.log('开始创建socket连接')
			let loadingLayer = layer.msg('正在连接终端...', {icon: 16, shade: [0.3, '#000'], time: -1});
			this.socketLoading = true;
			this.socket = io.connect();
			this.socket.on('connect', function () {
				this.socketLoading = false;
				console.log("socket.io connected!");
				layer.close(loadingLayer);
				resolve(this.socket);
				console.log("初始化socket完成")
			});
			this.socket.emit('connect_to_ssh', '');
		});
	}

	serverResponse(data) {
			if (!this.gterm) return;
			this.socketLoading = false;
			this.gterm.write(data.data);
			if (data.data == '\r\n登出\r\n' || 
					data.data == '登出\r\n' || 
					data.data == '\r\nlogout\r\n' || 
					data.data == 'logout\r\n') {
					setTimeout(function () {
							layer.closeAll();
							this.gterm.destroy();
							clearInterval(this.interval);
					}.bind(this), 500);
			}
	}

	async open() {
		return new Promise( async (resolve) => {
			
			await this.initTerm();
			await this.initSocket();	

			this.socket.emit('webssh', '');
			this.interval = setInterval(function () {
					this.socket.emit('webssh', '');
			}.bind(this), 500);

			this.socket.on('server_response', this.serverResponse.bind(this));
			this.gterm.on('data', function (data) {
				this.socket.emit('webssh', data);
			}.bind(this));
			console.log("开始打开终端")
			

			setTimeout(function () {
					var currentDir = $("#PathPlaceBtn").attr('path');
					if (currentDir && currentDir.startsWith("/")) {
							this.socket.emit('webssh', `cd ${currentDir}\n`);
					}
					resolve(this.socket);
			}.bind(this), 600);

			this.term_box = layer.open({
					type: 1,
					title: "本地终端",
					area: ['685px', '463px'],
					closeBtn: 1,
					shadeClose: false,
					content: '<div class="term-box"><div id="term"></div></div>\
							<div class="shell-text-input">\
									<textarea type="text" class="bt-input-text-shell" placeholder="请将命令粘贴到此处.." value="" name="ssh_copy" />\
							<div class="shell-btn-group">\
									<button class="shellbutton btn btn-success btn-sm pull-right shell_btn_1">发送(Ctrl+Enter)</button>\
									<button class="shellbutton btn btn-default btn-sm pull-right shell_btn_close">关闭</button>\
							</div>\
					</div>',
					success: function() {
						console.log("success")
							$(".shell_btn_close").click(function() {
									layer.close(this.term_box);
									this.gterm.destroy();
									clearInterval(this.interval);
									this.socket.off('server_response');
							}.bind(this));
					}.bind(this),
					end: () => {
						this.gterm.destroy();
						clearInterval(this.interval);
						// emit ctrl+c to stop the process
						this.socket.emit('webssh', "\x03");
						this.socket.off('server_response');
					}
			});

			setTimeout(function () {
					$('.terminal').detach().appendTo('#term');
					$("#term").show();
					this.socket.emit('webssh', "\n");
					this.gterm.focus();
					this.setupContextMenu();
					this.setupClipboard();
					this.setupShellButton();
			}.bind(this), 100);
		})
	}

	setupContextMenu() {
			var can = $("#term");
			can.contextmenu(function (e) {
					var menuPosition = this.calculateMenuPosition(e, can);
					var selectText = this.gterm.getSelection();
					var style_str = '';
					var paste_str = '';
					if (!selectText) {
							if (!getCookie('shell_copy_body')) {
									paste_str = 'style="color: #bbb;" disable';
							}
							style_str = 'style="color: #bbb;" disable';
					} else {
							setCookie('ssh_selection', selectText);
					}

					var menudiv = '<ul class="contextmenu">\
							<li><a class="shell_copy_btn menu_ssh" ' + style_str + '>复制到剪切板</a></li>\
							<li><a  onclick="webShell.shell_paste_text()" '+ paste_str+'>粘贴选中项</a></li>\
							<li><a onclick="webShell.shell_to_baidu()" ' + style_str + '>百度搜索</a></li>\
							<li><a onclick="webShell.shell_to_google()" ' + style_str + '>谷歌搜索</a></li>\
					</ul>';
					$("body").append(menudiv);
					$(".shell_copy_btn").attr('data-clipboard-text', selectText);
					$(".contextmenu").css({
							"left": menuPosition.left,
							"top": menuPosition.top,
							"z-index": 99999999,
							"position": 'fixed',
							"background": "white",
							"padding": "5px"
					});
					$(".contextmenu li").css({
							"cursor": 'pointer',
							"padding": "5px"
					});
					$(".contextmenu li").hover(function () {
							$(this).css({
									"background": "#eee"
							});
					}, function () {
							$(this).css({
									"background": "white"
							});
					});
					return false;
			}.bind(this));
			can.click(() => {
					this.remove_ssh_menu();
			});
	}

	calculateMenuPosition(e, can) {
			var winWidth = can.width();
			var winHeight = can.height();
			var mouseX = e.pageX;
			var mouseY = e.pageY;
			var menuWidth = $(".contextmenu").width();
			var menuHeight = $(".contextmenu").height();
			var minEdgeMargin = 10;
			var menuLeft, menuTop;

			if (mouseX + menuWidth + minEdgeMargin >= winWidth &&
					mouseY + menuHeight + minEdgeMargin >= winHeight) {
					menuLeft = mouseX - menuWidth - minEdgeMargin + "px";
					menuTop = mouseY - menuHeight - minEdgeMargin + "px";
			}
			else if (mouseX + menuWidth + minEdgeMargin >= winWidth) {
					menuLeft = mouseX - menuWidth - minEdgeMargin + "px";
					menuTop = mouseY + minEdgeMargin + "px";
			}
			else if (mouseY + menuHeight + minEdgeMargin >= winHeight) {
					menuLeft = mouseX + minEdgeMargin + "px";
					menuTop = mouseY - menuHeight - minEdgeMargin + "px";
			}
			else {
					menuLeft = mouseX + minEdgeMargin + "px";
					menuTop = mouseY + minEdgeMargin + "px";
			}
			return { left: menuLeft, top: menuTop };
	}

	setupClipboard() {
			var clipboard = new ClipboardJS('.shell_copy_btn');
			clipboard.on('success', function (e) {
					layer.msg('复制成功!');
					setCookie('shell_copy_body', e.text);
					this.remove_ssh_menu();
					this.gterm.focus();
			}.bind(this));

			clipboard.on('error', function (e) {
					layer.msg('复制失败，浏览器不兼容!');
					setCookie('shell_copy_body', e.text);
					this.remove_ssh_menu();
					this.gterm.focus();
			}.bind(this));
	}

	setupShellButton() {
			$(".shellbutton").click(function () {
					var tobj = $("textarea[name='ssh_copy']");
					var ptext = tobj.val();
					tobj.val('');
					if ($(this).text().indexOf('Alt') != -1) {
							ptext += "\n";
					}
					this.socket.emit('webssh', ptext);
					this.gterm.focus();
			}.bind(this));
			$("textarea[name='ssh_copy']").keydown(function (e) {
					if (e.ctrlKey && e.keyCode == 13) {
							$(".shell_btn_1").click();
					} else if (e.altKey && e.keyCode == 13) {
							$(".shell_btn_1").click();
					}
			});
	}

	
	shell_to_baidu() {
		var selectText = getCookie('ssh_selection');
		this.remove_ssh_menu();
		window.open('https://www.baidu.com/s?wd=' + selectText)
		this.gterm.focus();
	}

	shell_to_google() {
		var selectText = getCookie('ssh_selection');
		this.remove_ssh_menu();
		window.open('https://www.google.com/search?q=' + selectText)
		this.gterm.focus();
	}

	shell_paste_text(){
			this.socket.emit('webssh', getCookie('ssh_selection'));
			this.remove_ssh_menu();
			this.gterm.focus();
	}

	remove_ssh_menu() {
			$(".contextmenu").remove();
	}

	async sleep(time) {
			return new Promise((resolve) => setTimeout(resolve, time));
	}

}
