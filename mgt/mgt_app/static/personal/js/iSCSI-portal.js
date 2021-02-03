/*
 * 2020.9.29 Paul
 * note : 英文简写说明
 * 
 * */

// 操作提示
var vplxIp = get_vlpx_ip();
var tid = Date.parse(new Date()).toString();// 获取到毫秒的时间戳，精确到毫秒
var tid = tid.substr(0, 10);
var mgtIp = get_mgt_ip();

function get_mgt_ip() {
	var obj = new Object();
	$.ajax({
		url : "/mgtip",
		type : "GET",
		dataType : "json",
		async : false,
		success : function(data) {
			obj = "http://" + data["ip"];
		}
	});

	return obj;
}

function get_vlpx_ip() {
	var obj = new Object();
	$.ajax({
		url : "/vplxip",
		type : "GET",
		dataType : "json",
		async : false,
		success : function(data) {
			obj = "http://" + data["ip"];
		}
	});

	return obj;
}

function div_success() {
	document.getElementById('light_success').style.display = 'block';
	setTimeout("light_success.style.display='none'", 2000);
}

function div_failed() {
	document.getElementById('light_failed').style.display = 'block';
	document.getElementById('fade').style.display = 'block';
	setTimeout("light_failed.style.display='none'", 4000);
	setTimeout("fade.style.display='none'", 4000);
}

host_table();
function host_table() {
	$
			.ajax({
				url : vplxIp + "/host/show/oprt",
				type : "GET",
				dataType : "json",
				data : {
					tid : tid,
					ip : mgtIp
				},
				async : false,
				success : function(status) {
					write_to_log(tid, 'OPRT', 'ROUTE', vplxIp,
							'/host/show/oprt', status);
					$
							.ajax({
								url : vplxIp + "/host/show/data",
								type : "GET",
								dataType : "json",
								data : {
									tid : tid,
									ip : mgtIp
								},
								async : false,
								success : function(host_result) {
									write_to_log(tid, 'DATA', 'ROUTE', vplxIp,
											'/host/show/data', JSON
													.stringify(host_result));
									for (i in host_result) {
										tr = '<td style="width: 100px;">'
												+ i
												+ '</td>'
												+ '<td>'
												+ host_result[i]
												+ '</td>'
												+ '<td style="width: 200px;">'
												+ '<button  onClick="btn_show(this);">编辑</button>'+'<button  onClick="btn_show_delete(this);">删除</button>'
												+ '</td>';
										$("#Host_Table_Show").append(
												'<tr>' + tr + '</tr>')
									}
								},
								error : function() {
									write_to_log(tid, 'DATA', 'ROUTE', vplxIp,
											'/host/show/data', 'error');
								}

							});
				},
				error : function() {
					write_to_log(tid, 'DATA', 'ROUTE', vplxIp,
							'/host/show/oprt', 'error');
				}
			});
};
