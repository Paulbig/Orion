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
function write_to_log(tid, t1, t2, d1, d2, data) {
	$.ajax({
		url : '/iscsi/write_log',
		type : "get",
		dataType : "json",
		data : {
			tid : tid,
			t1 : t1,
			t2 : t2,
			d1 : d1,
			d2 : d2,
			data : data
		},
		async : false,
		success : function(write_log_result) {
		}
	});
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
				url : vplxIp + "/portal/show/oprt",
				type : "GET",
				dataType : "json",
				data : {
					tid : tid,
					ip : mgtIp
				},
				async : false,
				success : function(status) {
					write_to_log(tid, 'OPRT', 'ROUTE', vplxIp,
							'/portal/show/oprt', status);
					$
							.ajax({
								url : vplxIp + "/portal/show/data",
								type : "GET",
								dataType : "json",
								data : {
									tid : tid,
									ip : mgtIp
								},
								async : false,
								success : function(portal_data) {
									var target_data = get_target();
									write_to_log(tid, 'DATA', 'ROUTE', vplxIp,
											'/portal/show/data', JSON
													.stringify(portal_data));
									for (i in portal_data) {
										var portal_data_small = portal_data[i]
										tr = '<td style="width: 100px;">'
												+ i
												+ '</td>'
												+ '<td>'
												+ portal_data_small['ip']
												+ '</td>'
												+ '<td>'
												+ portal_data_small['port']
												+ '</td>'
												+ '<td>'
												+ portal_data_small['netmask']
												+ '</td>'
												+ '<td class="pop-title" title='+JSON
												.stringify(target_data[ portal_data_small['target']])+'>'
												+ portal_data[i]['target']
												+ '</td>'
//												+ '<td class="data-toggle="popover"">'
//												+ portal_data[i]['target']
//												+ '</td>'
												+ '<td style="width: 200px;">'
												+ '<button  onClick="btn_show(this);">编辑</button>'+'<button  onClick="btn_show_delete(this);">删除</button>'
												+ '</td>';
										$("#Portal_Table_Show").append(
												'<tr>' + tr + '</tr>')
									}
								},
								error : function() {
									write_to_log(tid, 'DATA', 'ROUTE', vplxIp,
											'/portal/show/data', 'error');
								}

							});
				},
				error : function() {
					write_to_log(tid, 'DATA', 'ROUTE', vplxIp,
							'/portal/show/oprt', 'error');
				}
			});
};


function get_target() {
	var obj = new Object();
	$
	.ajax({
		url : vplxIp + "/target/show/data",
		type : "GET",
		dataType : "json",
		data : {
			tid : tid,
			ip : mgtIp
		},
		async : false,
		success : function(target_result) {
			$
			.ajax({
				url : vplxIp + "/target/show/data",
				type : "GET",
				dataType : "json",
				data : {
					tid : tid,
					ip : mgtIp
				},
				async : false,
				success : function(target_data) {
					obj = target_data;
					
				}
				});
		}
		
	});
	return obj;
}
//function test() {
//    alert('关注成功');
//}
//
//function title() {
//    return '田喜碧Hebe(节制的人生)';
//}
//
//function content() {
//    var data = $("<form><ul><li><span aria-hidden='true' class='icon_globe'></span>&nbsp;<font>粉丝数:</font>7389223</li>" +
//             "<li><span aria-hidden='true' class='icon_piechart'></span>&nbsp;<font>关注:</font>265</li>" +
//             "<li><span aria-hidden='true' class='icon_search_alt'></span>&nbsp;<font>微博:</font>645</li>" +
//             "<li><span aria-hidden='true' class='icon_pens_alt'></span>&nbsp;<font>所在地:</font>台湾</li>" +
//             "<input id='btn' type='button' value='关注' οnclick='test()'/></form>");
//    
//    return data;
//}
//
//$(function() {
//    $("[data-toggle='popover']").popover({
//        html : true,  
//        title: title(),  
//        delay:{show:500, hide:1000},
//        content: function() {
//          return content();  
//        } 
//    });
//});
