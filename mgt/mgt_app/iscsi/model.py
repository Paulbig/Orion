
# coding:utf-8
'''
Created on 2020/3/2
@author: Paul
@note: data
'''
from flask import Flask, jsonify, render_template, request, make_response, views
from public import log
from ..utils import read_config
import consts
import socket
def cors_data(data_dict):
    response = make_response(jsonify(data_dict))
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'OPTIONS,HEAD,GET,POST'
    response.headers['Access-Control-Allow-Headers'] = 'x-requested-with'
    return response


class Index(views.MethodView):

    def get(self):
        return render_template("index.html")

class ISCSIWrite(views.MethodView):

    def get(self):
        if request.method == 'GET':
            log_data = request.args.to_dict()
            if log_data:
                logger = log.Log()
                logger.tid = log_data['tid']
                logger.write_to_log(log_data['t1'], log_data['t2'], log_data['d1'], log_data['d2'], log_data["data"])
        return cors_data("success")


class VplxIp(views.MethodView):
    def get(self):
        config_obj = read_config.Config()
        ip = {
            'ip': config_obj.get_ip() + ":" + config_obj.get_port()
        }
        return cors_data(ip)

class MgtIp(views.MethodView):
    def get(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        finally:
            s.close()
        mgt_ip = {'ip':ip}
        return cors_data(mgt_ip)


    
class IndexPreview(views.MethodView):

    def get(self):
        return render_template("index_preview.html")

    
class IscsiCreate(views.MethodView):

    def get(self):
        return render_template("iscsi_create.html")


class IscsiAll(views.MethodView):

    def get(self):
        return render_template("iscsi_all.html")
    
    
class IscsiMap(views.MethodView):

    def get(self):
        return render_template("iscsi_map.html")
    
    
class IscsiMap2(views.MethodView):

    def get(self):
        return render_template("iscsi_map2.html")
class IscsiMapModify(views.MethodView):

    def get(self):
        return render_template("iscsi_map_modify.html")
    
    
class IscsiHost(views.MethodView):

    def get(self):
        return render_template("iscsi_host.html")
    
    
class IscsiHostGroup(views.MethodView):

    def get(self):
        return render_template("iscsi_hostgroup.html")
    
    
class IscsiDiskGroup(views.MethodView):

    def get(self):
        return render_template("iscsi_diskgroup.html")
    
class IscsiDisk(views.MethodView):

    def get(self):
        return render_template("iscsi_disk.html")
    
    
class Iscsiportal(views.MethodView):

    def get(self):
        return render_template("iscsi_portal.html")
    
