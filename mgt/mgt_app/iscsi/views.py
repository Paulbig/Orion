# coding:utf-8
'''
Created on 2020/3/2
@author: Paul
@note: data
'''

from flask import Flask,views
from mgt_app.iscsi import iscsi_blueprint
from mgt_app.iscsi import model

iscsi_blueprint.add_url_rule('/', view_func=model.Index.as_view('index'))
iscsi_blueprint.add_url_rule('/index/preview', view_func=model.IndexPreview.as_view('index_preview'))
iscsi_blueprint.add_url_rule('/iscsi/write_log', view_func=model.ISCSIWrite.as_view('iscsi_write_log'))
iscsi_blueprint.add_url_rule('/vplxip' ,view_func=model.VplxIp.as_view('VplxIp'))
iscsi_blueprint.add_url_rule('/mgtip' ,view_func=model.MgtIp.as_view('MgtIp'))

iscsi_blueprint.add_url_rule('/iscsi/all', view_func=model.IscsiAll.as_view('iscsi_all'))
iscsi_blueprint.add_url_rule('/iscsi/create', view_func=model.IscsiCreate.as_view('iscsi_create'))

iscsi_blueprint.add_url_rule('/iscsi/map', view_func=model.IscsiMap.as_view('iscsi_map'))
iscsi_blueprint.add_url_rule('/iscsi/map2', view_func=model.IscsiMap2.as_view('iscsi_map2'))
iscsi_blueprint.add_url_rule('/iscsi/map/modify', view_func=model.IscsiMapModify.as_view('iscsi_map_modify'))

iscsi_blueprint.add_url_rule('/iscsi/host', view_func=model.IscsiHost.as_view('iscsi_host'))

iscsi_blueprint.add_url_rule('/iscsi/hostgroup', view_func=model.IscsiHostGroup.as_view('iscsi_hostgroup'))

iscsi_blueprint.add_url_rule('/iscsi/diskgroup', view_func=model.IscsiDiskGroup.as_view('iscsi_diskgroup'))
iscsi_blueprint.add_url_rule('/iscsi/disk', view_func=model.IscsiDisk.as_view('iscsi_disk'))
iscsi_blueprint.add_url_rule('/iscsi/portal', view_func=model.Iscsiportal.as_view('iscsi_portal'))




