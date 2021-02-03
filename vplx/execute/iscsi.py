# coding=utf-8
import time
import copy
import traceback

import iscsi_json
import sundry as s
from execute.linstor import Linstor
from execute.crm import RollBack,CRMData, CRMConfig,IPaddr2,PortBlockGroup,Colocation,Order,ISCSITarget,ISCSILogicalUnit
import log
import consts


class IscsiConfig():
    def __init__(self, data_current, data_changed):
        self.logger = log.Log()
        dict_current = self.get_map_relation(data_current)
        dict_changed = self.get_map_relation(data_changed)

        self.diff, self.recover = self.get_dict_diff(dict_current, dict_changed)
        self.delete = self.diff['delete']
        self.create = self.diff['create']
        self.modify = self.diff['modify']

        if any([self.modify, self.delete]):
            self.obj_crm = CRMConfig()

        self.obj_iscsiLU = ISCSILogicalUnit()

        # 记载需要进行恢复的disk
        self.recovery_list = {'delete': set(), 'create': {}, 'modify': {}}

    def get_map_relation(self, data):
        dict_map_relation = {}
        for disk in data['Disk']:
            dict_map_relation.update({disk: set()})
        try:
            for map in data['Map'].values():
                for dg in map['DiskGroup']:
                    for disk in data['DiskGroup'][dg]:
                        set_iqn = set()
                        for hg in map['HostGroup']:
                            for host in data['HostGroup'][hg]:
                                set_iqn.add(data['Host'][host])
                        dict_map_relation[disk] = dict_map_relation[disk] | set_iqn
        except KeyError as key:
            s.prt_log(f'{key} does not exist in the configuration file, please check', 2)

        return dict_map_relation

    def get_dict_diff(self, dict1, dict2):
        # 判断dict2有没有dict1没有的key，如有dict1进行补充
        ex_key = dict2.keys() - dict1.keys()
        if ex_key:
            for i in ex_key:
                dict1.update({i: set()})

        diff = {'delete': set(), 'create': {}, 'modify': {}}
        recover = {'delete': set(), 'create': {}, 'modify': {}}
        for key in dict1:
            if set(dict1[key]) != set(dict2[key]):
                if not dict2[key]:
                    diff['delete'].add(key)
                    recover['create'].update({key: dict1[key]})
                elif not dict1[key]:
                    diff['create'].update({key: dict2[key]})
                    recover['delete'].add(key)
                else:
                    diff['modify'].update({key: dict2[key]})
                    recover['modify'].update({key: dict1[key]})

        self.logger.write_to_log('DATA', 'iSCSILogicalUnit', 'Data to be modified', '', diff)
        return diff, recover

    def show_info(self):
        nl = '\n'
        info = []
        if not any([self.create,self.delete,self.modify]):
            return ['Will not have any effect']
        if self.create:
            info_create = f'''create:\n{''.join([f"{disk}'s iqn ==> {','.join(iqn)}{nl}" for disk,iqn in self.create.items()])}'''
            info.append(info_create)
        if self.delete:
            info_delete = f'delete:\n{",".join(self.delete)}'
            info.append(info_delete)
        if self.modify:
            info_modify = f'''modify:\n{''.join([f"{disk}'s iqn ==> {','.join(iqn)}{nl}" for disk,iqn in self.modify.items()])}'''
            info.append(info_modify)
        return info


    def create_iscsilogicalunit(self):
        for disk, iqn in self.create.items():
            self.recovery_list['delete'].add(disk)
            self.obj_iscsiLU.create_mapping(disk, iqn)

    def delete_iscsilogicalunit(self):
        for disk in self.delete:
            self.recovery_list['create'].update({disk: self.recover['create'][disk]})
            self.obj_iscsiLU.delete(disk)

    def modify_iscsilogicalunit(self):
        for disk, iqn in self.modify.items():
            self.recovery_list['modify'].update({disk: self.recover['modify'][disk]})
            self.obj_iscsiLU.modify(disk, iqn)

    def rollback(self):
        print("Mapping relationship rollback")
        for disk, iqn in self.recovery_list['create'].items():
            self.obj_iscsiLU.create_mapping(disk, iqn)
        for disk in self.recovery_list['delete']:
            self.obj_iscsiLU.delete(disk)
        for disk, iqn in self.recovery_list['modify'].items():
            self.obj_iscsiLU.modify(disk, iqn)
        print("Mapping relationship rollback ends")

    def comfirm_modify(self):
        print('\n'.join(self.show_info()))
        print(f'Are you sure? y/n')
        answer = s.get_answer()
        if not answer in ['y', 'yes', 'Y', 'YES']:
            s.prt_log(f'Cancel operation', 2)

    def crm_conf_change(self):
        try:
            self.create_iscsilogicalunit()
            self.delete_iscsilogicalunit()
            self.modify_iscsilogicalunit()
        except consts.CmdError:
            s.prt_log('Command execution failed',1)
            self.logger.write_to_log('DATA', 'DEBUG', 'exception', 'Rollback', str(traceback.format_exc()))
            self.rollback()
        except Exception:
            s.prt_log('Unknown exception',1)
            self.logger.write_to_log('DATA', 'DEBUG', 'exception', 'Rollback', str(traceback.format_exc()))
            self.rollback()


# 问题，这个disk数据是根据LINSTOR来的，那么是不是进行iscsi命令之前，需要更新这个数据，或者进行校验？
class Disk():
    """
    Disk
    """

    def __init__(self):
        self.js = iscsi_json.JsonOperation()

    def update_disk(self):
        # 更新disk数据并返回
        linstor = Linstor()
        linstor_res = linstor.get_linstor_data(
            'linstor --no-color --no-utf8 r lv')
        disks = {}
        for d in linstor_res:
            disks.update({d[1]: d[5]})
        self.js.cover_data('Disk', disks)
        self.js.commit_data()
        return disks

    def show(self, disk):
        disk_all = self.update_disk()
        list_header = ["ResourceName", "Path"]
        list_data = []
        if disk == 'all' or disk is None:
            # show all
            for disk, path in disk_all.items():
                list_data.append([disk, path])
        else:
            # show one
            if self.js.check_key('Disk', disk):
                list_data.append([disk, disk_all[disk]])

        table = s.make_table(list_header, list_data)
        s.prt_log(table, 0)
        return list_data


class Host():
    """
    Host
    """

    def __init__(self):
        self.js = iscsi_json.JsonOperation()

    def _check_iqn(self, iqn):
        """
        判断iqn是否符合格式
        """
        result = s.re_findall(
            r'^iqn\.\d{4}-\d{2}\.[a-zA-Z0-9][-a-zA-Z0-9]{0,62}(\.[a-zA-Z0-9][-a-zA-Z0-9]{0,62})+(:[a-zA-Z0-9.:-]+)?$',
            iqn)
        return True if result else False

    def create(self, host, iqn):
        if self.js.check_key('Host', host):
            s.prt_log(f"Fail! The Host {host} already existed.", 1)
            return
        if not self._check_iqn(iqn):
            s.prt_log(f"The format of IQN is wrong. Please confirm and fill in again.", 1)
            return
        self.js.update_data("Host", host, iqn)
        self.js.commit_data()
        s.prt_log("Create success!", 0)
        return True

    def show(self, host):
        list_header = ["HostName", "IQN"]
        list_data = []
        host_all = self.js.json_data['Host']
        if host == 'all' or host is None:
            # show all
            for host, iqn in host_all.items():
                list_data.append([host, iqn])
        else:
            # show one
            if self.js.check_key('Host', host):
                list_data.append([host, host_all[host]])
        table = s.make_table(list_header, list_data)
        s.prt_log(table, 0)
        return list_data


    def delete(self, host):
        if not self.js.check_key('Host',host):
            s.prt_log(f"Fail！Can't find {host}", 1)
            return

        json_data_before = copy.deepcopy(self.js.json_data)
        self.js.delete_data('Host', host)
        self.js.arrange_data('Host', host)
        obj_iscsi = IscsiConfig(json_data_before, self.js.json_data)
        obj_iscsi.comfirm_modify()
        # 重新读取配置文件的数据，保证数据一致性
        json_data_now = self.js.read_json()
        if json_data_before == json_data_now:
            obj_iscsi.crm_conf_change()
        else:
            s.prt_log('The configuration file has been modified, please try again', 2)

        self.js.commit_data()
        s.prt_log(f"Delete {host} successfully", 0)

    def modify(self, host, iqn):
        if not self.js.check_key('Host', host):
            s.prt_log(f"Fail! Can't find {host}", 1)
            return
        if not self._check_iqn(iqn):
            s.prt_log(f"The format of IQN is wrong. Please confirm and fill in again.", 1)
            return

        json_data_before = copy.deepcopy(self.js.json_data)
        self.js.update_data('Host', host, iqn)
        obj_iscsi = IscsiConfig(json_data_before, self.js.json_data)
        obj_iscsi.comfirm_modify()

        # 重新读取配置文件的数据，保证数据一致性
        json_data_now = self.js.read_json()
        if json_data_before == json_data_now:
            obj_iscsi.crm_conf_change()
        else:
            s.prt_log('The configuration file has been modified, please try again', 2)

        self.js.commit_data()


class DiskGroup():
    """
    DiskGroup
    """

    def __init__(self):
        # 更新json文档中的disk信息
        disk = Disk()
        disk.update_disk()
        self.js = iscsi_json.JsonOperation()

    def create(self, diskgroup, disk):
        if self.js.check_key('DiskGroup', diskgroup):
            s.prt_log(f'Fail! The Disk Group {diskgroup} already existed.', 1)
            return
        for i in disk:
            if self.js.check_key('Disk', i) == False:
                s.prt_log(f"Fail! Can't find {i}.Please give the true name.", 1)
                return

        self.js.update_data('DiskGroup', diskgroup, disk)
        self.js.commit_data()
        s.prt_log("Create success!", 0)
        return True

    def show(self, dg):
        list_header = ["DiskgroupName", "DiskName"]
        list_data = []
        hg_all = self.js.json_data['DiskGroup']

        if dg == 'all' or dg is None:
            # show all
            for dg, disk in hg_all.items():
                list_data.append([dg, ' '.join(disk)])
        else:
            # show one
            if self.js.check_key('DiskGroup', dg):
                list_data.append([dg, ' '.join(hg_all[dg])])

        table = s.make_table(list_header, list_data)
        s.prt_log(table, 0)
        return list_data


    def delete(self, dg):
        if not self.js.check_key('DiskGroup', dg):
            s.prt_log(f"Fail! Can't find {dg}", 1)
            return

        json_data_before = copy.deepcopy(self.js.json_data)
        self.js.delete_data('DiskGroup', dg)
        self.js.arrange_data('DiskGroup', dg)
        obj_iscsi = IscsiConfig(json_data_before, self.js.json_data)
        obj_iscsi.comfirm_modify()
        # 重新读取配置文件的数据，保证数据一致性
        json_data_now = self.js.read_json()
        if json_data_before == json_data_now:
            obj_iscsi.crm_conf_change()
        else:
            s.prt_log('The configuration file has been modified, please try again', 2)

        self.js.commit_data()
        s.prt_log(f"Delete {dg} success!", 0)

    def add_disk(self, dg, list_disk):
        if not self.js.check_key('DiskGroup', dg):
            s.prt_log(f"Fail！Can't find {dg}", 1)
            return
        for disk in list_disk:
            if disk in self.js.json_data['DiskGroup'][dg]:
                s.prt_log(f'{disk} already exists in {dg}', 1)
                return
            if not self.js.check_key("Disk", disk):
                s.prt_log(f'The disk does not exist in the configuration file and cannot be added', 1)
                return

        json_data_before = copy.deepcopy(self.js.json_data)
        self.js.append_member('DiskGroup', dg, list_disk)
        obj_iscsi = IscsiConfig(json_data_before, self.js.json_data)
        obj_iscsi.comfirm_modify()

        # 重新读取配置文件的数据，保证数据一致性
        json_data_now = self.js.read_json()
        if json_data_before == json_data_now:
            obj_iscsi.crm_conf_change()
        else:
            s.prt_log('The configuration file has been modified, please try again', 2)
        self.js.commit_data()

    def remove_disk(self, dg, list_disk):
        if not self.js.check_key('DiskGroup', dg):
            s.prt_log(f"Fail！Can't find {dg}", 1)
            return
        for disk in list_disk:
            if not disk in self.js.json_data['DiskGroup'][dg]:
                s.prt_log(f'{disk} does not exist in {dg} and cannot be removed', 1)
                return


        json_data_before = copy.deepcopy(self.js.json_data)
        self.js.remove_member('DiskGroup', dg, list_disk)
        if not self.js.json_data['DiskGroup'][dg]:
            self.js.delete_data('DiskGroup', dg)
            self.js.arrange_data('DiskGroup', dg)
            print(f'{dg} and the map related to {dg} have been modified/deleted')

        obj_iscsi = IscsiConfig(json_data_before, self.js.json_data)
        obj_iscsi.comfirm_modify()

        # 重新读取配置文件的数据，保证数据一致性
        json_data_now = self.js.read_json()
        if json_data_before == json_data_now:
            obj_iscsi.crm_conf_change()
        else:
            s.prt_log('The configuration file has been modified, please try again', 2)

        self.js.commit_data()

    """
    hostgroup 操作
    """


class HostGroup():
    def __init__(self):
        self.js = iscsi_json.JsonOperation()

    def create(self, hostgroup, host):
        if self.js.check_key('HostGroup', hostgroup):
            s.prt_log(f'Fail! The HostGroup {hostgroup} already existed.', 1)
            return
        for i in host:
            if self.js.check_key('Host', i) == False:
                s.prt_log(f"Fail! Can't find {i}.Please give the true name.", 1)
                return

        self.js.update_data('HostGroup', hostgroup, host)
        self.js.commit_data()
        s.prt_log("Create success!", 0)
        return True

    def show(self, hg):
        list_header = ["HostGroupName", "HostName"]
        list_data = []
        hg_all = self.js.json_data['HostGroup']

        if hg == 'all' or hg is None:
            # show all
            for hg, host in hg_all.items():
                list_data.append([hg, ' '.join(host)])
        else:
            # show one
            if self.js.check_key('HostGroup', hg):
                list_data.append([hg, ' '.join(hg_all[hg])])

        table = s.make_table(list_header, list_data)
        s.prt_log(table, 0)
        return list_data


    def delete(self, hg):
        if not self.js.check_key('HostGroup', hg):
            s.prt_log(f"Fail! Can't find {hg}", 1)
            return

        json_data_before = copy.deepcopy(self.js.json_data)
        self.js.delete_data('HostGroup', hg)
        self.js.arrange_data('HostGroup', hg)
        obj_iscsi = IscsiConfig(json_data_before, self.js.json_data)
        obj_iscsi.comfirm_modify()
        # 重新读取配置文件的数据，保证数据一致性
        json_data_now = self.js.read_json()
        if json_data_before == json_data_now:
            obj_iscsi.crm_conf_change()
        else:
            s.prt_log('The configuration file has been modified, please try again', 2)

        self.js.commit_data()
        s.prt_log(f"Delete {hg} success!", 0)

    def add_host(self, hg, list_host):
        if not self.js.check_key('HostGroup', hg):
            s.prt_log(f"Fail！Can't find {hg}", 1)
            return
        for host in list_host:
            if host in self.js.json_data['HostGroup'][hg]:
                s.prt_log(f'{host} already exists in {hg}', 1)
                return
            if not self.js.check_key("Host", host):
                s.prt_log(f'{host} does not exist in the configuration file and cannot be added', 1)
                return

        json_data_before = copy.deepcopy(self.js.json_data)
        self.js.append_member('HostGroup', hg, list_host)
        obj_iscsi = IscsiConfig(json_data_before, self.js.json_data)
        obj_iscsi.comfirm_modify()

        # 重新读取配置文件的数据，保证数据一致性
        json_data_now = self.js.read_json()
        if json_data_before == json_data_now:
            obj_iscsi.crm_conf_change()
        else:
            s.prt_log('The configuration file has been modified, please try again', 2)

        # 配置文件更新修改的资源
        self.js.commit_data()

    def remove_host(self, hg, list_host):
        if not self.js.check_key('HostGroup', hg):
            s.prt_log(f"Fail！Can't find {hg}", 1)
            return
        for host in list_host:
            if not host in self.js.json_data['HostGroup'][hg]:
                s.prt_log(f'{host} does not exist in {hg} and cannot be removed', 1)
                return
        json_data_before = copy.deepcopy(self.js.json_data)
        self.js.remove_member('HostGroup', hg, list_host)
        if not self.js.json_data['HostGroup'][hg]:
            self.js.delete_data('HostGroup', hg)
            self.js.arrange_data('HostGroup',hg)
            print(f'{hg} and the map related to {hg} have been modified/deleted')
        obj_iscsi = IscsiConfig(json_data_before, self.js.json_data)
        obj_iscsi.comfirm_modify()

        # 重新读取配置文件的数据，保证数据一致性
        json_data_now = self.js.read_json()
        if json_data_before == json_data_now:
            obj_iscsi.crm_conf_change()
        else:
            s.prt_log('The configuration file has been modified, please try again', 2)

        # 配置文件的改变
        self.js.commit_data()

    """
    map操作
    """


class Map():
    def __init__(self):
        self.js = iscsi_json.JsonOperation()
        disk = Disk()
        disk.update_disk()

        # 用于收集创建成功的resource
        # self.target_name, self.target_iqn = self.get_target()


    def create(self, map, list_hg, list_dg):
        """
        创建map
        :param map:
        :param hg: list,
        :param dg: list,
        :return:T/F
        """
        # 创建前的检查
        if self.js.check_key('Map', map):
            s.prt_log(f'The Map "{map}" already existed.', 2)
            return
        for hg in list_hg:
            if not self.js.check_key('HostGroup', hg):
                s.prt_log(f"Can't find {hg}", 2)
                return
        for dg in list_dg:
            if not self.js.check_key('DiskGroup', dg):
                s.prt_log(f"Can't find {dg}", 2)
                return

        json_data_before = copy.deepcopy(self.js.json_data)
        self.js.update_data('Map', map, {'HostGroup': list_hg, 'DiskGroup': list_dg})
        obj_iscsi = IscsiConfig(json_data_before, self.js.json_data)

        # 已经被使用过的disk(ilu)需不需要提示
        dict_disk_inuse = obj_iscsi.modify
        if dict_disk_inuse:
            s.prt_log(f"Disk:{','.join(dict_disk_inuse.keys())} has been mapped,will modify their allowed initiators",0)

        obj_iscsi.create_iscsilogicalunit()
        obj_iscsi.modify_iscsilogicalunit()

        self.js.commit_data()
        s.prt_log('Create map success!', 0)
        return True

    def show(self, map):
        list_header = ["MapName", "HostGroup", "DiskGroup"]
        list_data = []
        map_all = self.js.json_data['Map']

        if map == 'all' or map is None:
            # show all
            for map, data in map_all.items():
                list_data.append([map, " ".join(data['HostGroup']), " ".join(data['DiskGroup'])])
        else:
            # show one
            if self.js.check_key('Map', map):
                list_data.append([map, " ".join(map_all[map]['HostGroup']), " ".join(map_all[map]['DiskGroup'])])

        table = s.make_table(list_header, list_data)
        s.prt_log(table, 0)
        return list_data


    #  执行map展示的时候，会展示对应dg和hg的数据（全部三个表格），暂时保留代码
    # def get_spe_map(self, map):
    #     list_hg = []
    #     list_dg = []
    #     if not self.js.check_key('Map', map):
    #         s.prt_log('No map data', 2)
    #     # {map1: {"HostGroup": [hg1, hg2], "DiskGroup": [dg1, dg2]}
    #     map_data = self.js.get_data('Map').get(map)
    #     hg_list = map_data["HostGroup"]
    #     dg_list = map_data["DiskGroup"]
    #     for hg in hg_list:
    #         host = self.js.get_data('HostGroup').get(hg)
    #         for i in host:
    #             iqn = self.js.get_data('Host').get(i)
    #             list_hg.append([hg, i, iqn])
    #     for dg in dg_list:
    #         disk = self.js.get_data('DiskGroup').get(dg)
    #         for i in disk:
    #             path = self.js.get_data('Disk').get(i)
    #             list_dg.append([dg, i, path])
    #     return [{map: map_data}, list_hg, list_dg]
    #
    # def show_spe_map(self, map):
    #     list_data = self.get_spe_map(map)
    #     header_map = ["MapName", "HostGroup", "DiskGroup"]
    #     header_host = ["HostGroup", "HostName", "IQN"]
    #     header_disk = ["DiskGroup", "DiskName", "Disk"]
    #     table_map = s.show_map_data(header_map, list_data[0])
    #     table_hg = s.show_spe_map_data(header_host, list_data[1])
    #     table_dg = s.show_spe_map_data(header_disk, list_data[2])
    #     result = [str(table_map), str(table_hg), str(table_dg)]
    #     s.prt_log('\n'.join(result), 0)
    #     return list_data

    # 调用crm删除map
    def delete_map(self, map):
        if not self.js.check_key('Map', map):
            s.prt_log(f"Fail！Can't find {map}", 2)
            return

        json_data_before = copy.deepcopy(self.js.json_data)
        self.js.delete_data('Map', map)
        obj_iscsi = IscsiConfig(json_data_before, self.js.json_data)
        obj_iscsi.comfirm_modify()
        obj_iscsi.crm_conf_change()
        self.js.commit_data()
        s.prt_log("Delete map successfully", 0)
        return True

    def add_hg(self, map, list_hg):
        if not self.js.check_key('Map', map):
            s.prt_log(f"Fail！Can't find {map}", 1)
            return
        for hg in list_hg:
            if hg in self.js.json_data["Map"][map]["HostGroup"]:
                s.prt_log(f'{hg} already exists in {map}', 1)
                return
            if not self.js.check_key("HostGroup", hg):
                s.prt_log(f'{hg} does not exist in the configuration file and cannot be added', 1)
                return

        json_data_before = copy.deepcopy(self.js.json_data)
        self.js.append_member('HostGroup', map, list_hg, type='Map')
        obj_iscsi = IscsiConfig(json_data_before, self.js.json_data)
        obj_iscsi.comfirm_modify()

        # 重新读取配置文件的数据，保证数据一致性
        json_data_now = self.js.read_json()
        if json_data_before == json_data_now:
            obj_iscsi.crm_conf_change()
        else:
            s.prt_log('The configuration file has been modified, please try again', 2)

        # 提交json的修改
        self.js.commit_data()

    def add_dg(self, map, list_dg):
        if not self.js.check_key('Map', map):
            s.prt_log(f"Fail！Can't find {map}", 1)
            return
        for dg in list_dg:
            if dg in self.js.json_data["Map"][map]["DiskGroup"]:
                s.prt_log(f'{dg} already exists in {map}', 1)
                return
            if not self.js.check_key("DiskGroup", dg):
                s.prt_log(f'{dg} does not exist in the configuration file and cannot be added', 1)
                return

        json_data_before = copy.deepcopy(self.js.json_data)
        self.js.append_member('DiskGroup', map, list_dg, type='Map')
        obj_iscsi = IscsiConfig(json_data_before, self.js.json_data)
        obj_iscsi.comfirm_modify()

        # 重新读取配置文件的数据，保证数据一致性
        json_data_now = self.js.read_json()
        if json_data_before == json_data_now:
            obj_iscsi.crm_conf_change()
        else:
            s.prt_log('The configuration file has been modified, please try again', 2)

        # 提交json的修改
        self.js.commit_data()

    def remove_hg(self, map, list_hg):
        if not self.js.check_key('Map', map):
            s.prt_log(f"Fail！Can't find {map}", 1)
            return
        for hg in list_hg:
            if not hg in self.js.json_data["Map"][map]["HostGroup"]:
                s.prt_log(f'{hg} does not exist in {map} and cannot be removed', 1)
                return

        # 获取修改前的数据进行复制，之后进行对json数据的修改，从而去对比获取需要改动的映射关系再使用crm命令修改
        json_data_before = copy.deepcopy(self.js.json_data)
        self.js.remove_member('HostGroup', map, list_hg, type='Map')
        obj_iscsi = IscsiConfig(json_data_before, self.js.json_data)
        obj_iscsi.comfirm_modify()

        # 重新读取配置文件的数据，保证数据一致性
        json_data_now = self.js.read_json()
        if json_data_before == json_data_now:
            obj_iscsi.crm_conf_change()
        else:
            s.prt_log('The configuration file has been modified, please try again', 2)

        # 配置文件删除/移除成员
        if not self.js.json_data['Map'][map]['HostGroup']:
            self.js.delete_data('Map', map)
            print(f'{map} deleted')

        self.js.commit_data()

    def remove_dg(self, map, list_dg):
        # 验证
        if not self.js.check_key('Map', map):
            s.prt_log(f"Fail！Can't find {map}", 1)
            return
        for dg in list_dg:
            if not dg in self.js.json_data["Map"][map]["DiskGroup"]:
                s.prt_log(f'{dg} does not exist in {map} and cannot be removed', 1)
                return

        # 获取修改前的数据进行复制，之后进行对json数据的修改，从而去获取映射关系再使用crm命令修改
        json_data_before = copy.deepcopy(self.js.json_data)
        self.js.remove_member('DiskGroup', map, list_dg, type='Map')  # 对临时json对象的操作
        obj_iscsi = IscsiConfig(json_data_before, self.js.json_data)
        obj_iscsi.comfirm_modify()

        # 重新读取配置文件的数据，保证数据一致性
        json_data_now = self.js.read_json()
        if json_data_before == json_data_now:
            obj_iscsi.crm_conf_change()
        else:
            s.prt_log('The configuration file has been modified, please try again', 2)

        if not self.js.json_data['Map'][map]['DiskGroup']:
            self.js.delete_data('Map', map)
            print(f'{map} deleted')

        self.js.commit_data()


class Portal():
    def __init__(self):
        self.logger = log.Log()
        self.js = iscsi_json.JsonOperation()

    def create(self, name, ip, port=3260, netmask=24):
        if not self._check_name(name):
            s.prt_log(f'{name} naming does not conform to the specification', 1)
            return
        if not self._check_IP(ip):
            s.prt_log(f'{ip} does not meet specifications', 1)
            return
        if not self._check_port(port):
            s.prt_log(f'{port} does not meet specifications(Range：3260-65535)', 1)
            return
        if not self._check_netmask(netmask):
            s.prt_log(f'{netmask} does not meet specifications(Range：1-32)',1)
            return
        if self.js.check_key('Portal', name):
            s.prt_log(f'{name} already exists, please use another name', 1)
            return
        if self.js.check_in_res('Portal','ip',ip):
            s.prt_log(f'{ip} is already in use, please use another IP',1)
            return

        try:
            obj_ipadrr = IPaddr2()
            obj_ipadrr.create(name, ip, netmask)

            obj_portblock = PortBlockGroup()
            obj_portblock.create(f'{name}_prtblk_on', ip, port, action='block')
            obj_portblock.create(f'{name}_prtblk_off', ip, port, action='unblock')

            Colocation.create(f'col_{name}_prtblk_on', f'{name}_prtblk_on', name)
            Colocation.create(f'col_{name}_prtblk_off', f'{name}_prtblk_off', name)
            Order.create(f'or_{name}_prtblk_on', name, f'{name}_prtblk_on')
        except Exception as ex:
            self.logger.write_to_log('DATA', 'DEBUG', 'exception', 'Rollback', str(traceback.format_exc()))
            RollBack.rollback(ip,port,netmask)
            return

        # 验证
        status = self._check_status(name)

        if status == 'OK':
            self.js.update_data('Portal', name, {'ip': ip, 'port': str(port),'netmask':str(netmask),'target':[]})
            self.js.commit_data()
        elif status == 'NETWORK_ERROR':
            obj_ipadrr.delete(name)
            obj_portblock.delete(f'{name}_prtblk_on')
            obj_portblock.delete(f'{name}_prtblk_off')
            s.prt_log('The portal cannot be created normally due to the wrong IP address network segment or other network problems, please reconfigure', 1)

    def delete(self, name):
        if not self.js.check_key('Portal', name):
            s.prt_log(f"Fail！Can't find {name}", 1)
            return
        target = self.js.json_data['Portal'][name]['target']
        if target:
            s.prt_log(f'In use：{",".join(target)}. Can not delete', 1)
            return

        try:
            obj_ipadrr = IPaddr2()
            obj_ipadrr.delete(name)

            obj_portblock = PortBlockGroup()
            obj_portblock.delete(f'{name}_prtblk_on')
            obj_portblock.delete(f'{name}_prtblk_off')

        except Exception as ex:
            self.logger.write_to_log('DATA', 'DEBUG', 'exception', 'Rollback', str(traceback.format_exc()))
            portal = self.js.json_data['Portal'][name]
            RollBack.rollback(portal['ip'], portal['port'], portal['netmask'])
            # 恢复colocation和order
            if RollBack.dict_rollback['IPaddr2']:
                Colocation.create(f'col_{name}_prtblk_on', f'{name}_prtblk_on', name)
                Colocation.create(f'col_{name}_prtblk_off', f'{name}_prtblk_off', name)
                Order.create(f'or_{name}_prtblk_on', name, f'{name}_prtblk_on')
            return

        # 验证
        crm_data = CRMData()
        dict = crm_data.get_vip()
        if not name in dict.keys():
            self.js.delete_data('Portal',name)
            self.js.commit_data()
            print(f'Delete {name} successfully')
        else:
            print(f'Failed to delete {name}, please check')


    def modify(self, name, ip, port ,netmask):
        if not self.js.check_key('Portal',name):
            s.prt_log(f"Fail！Can't find {name}", 1)
            return
        flag_only_netmask = True
        portal = self.js.json_data['Portal'][name]

        # 指定了ip
        if ip:
            if not self._check_IP(ip):
                s.prt_log(f'{ip} does not meet specifications',1)
                return
            if self.js.check_in_res('Portal', 'ip', ip):
                s.prt_log(f'{ip} is already in use, please use another IP', 1)
                return
            flag_only_netmask = False
        else:
            ip = portal['ip']

        # 指定了port
        if port:
            if not self._check_port(port):
                s.prt_log(f'{port} does not meet specifications(Range：3260-65535)',1)
                return
            flag_only_netmask = False
        else:
            port = portal['port']
        # 指定了netmask
        if netmask:
            if not self._check_netmask(netmask):
                s.prt_log(f'{netmask} does not meet specifications(Range：1-32)', 1)
        else:
            netmask = portal['netmask']

        if portal['ip'] == ip and portal['port'] == str(port) and portal['netmask'] == str(netmask):
            s.prt_log(f'The parameters are the same, no need to modify',1)
            return

        if flag_only_netmask:
            # 只执行了netmask进行修改，这种情况下只需要对vip的netmask进行修改就行
            try:
                obj_ipadrr = IPaddr2()
                obj_ipadrr.modify(name, ip, netmask)

                obj_portblock = PortBlockGroup()
                obj_portblock.modify(f'{name}_prtblk_on', ip, port)
                obj_portblock.modify(f'{name}_prtblk_off', ip, port)
            except Exception as ex:
                self.logger.write_to_log('DATA', 'DEBUG', 'exception', 'Rollback', str(traceback.format_exc()))
                RollBack.rollback(portal['ip'],portal['port'],portal['netmask'])
                return

        else:
            if portal['target']:
                # 反馈修改影响
                print(f'Target：{",".join(portal["target"])}using this portal.These targets will be modified synchronously, whether to continue?y/n')
                answer = s.get_answer()
                if not answer in ['y', 'yes', 'Y', 'YES']:
                    s.prt_log('Modify canceled', 2)

                try:
                    obj_ipadrr = IPaddr2()
                    obj_ipadrr.modify(name, ip, netmask)

                    obj_portblock = PortBlockGroup()
                    obj_portblock.modify(f'{name}_prtblk_on', ip, port)
                    obj_portblock.modify(f'{name}_prtblk_off', ip, port)

                    obj_target = ISCSITarget()
                    for target in portal['target']:
                        obj_target.modify(target, ip, port)
                except Exception as ex:
                    self.logger.write_to_log('DATA', 'DEBUG', 'exception', 'Rollback', str(traceback.format_exc()))
                    RollBack.rollback(portal['ip'], portal['port'], portal['netmask'])
                    return

            else:
                # 直接修改
                try:
                    obj_ipadrr = IPaddr2()
                    obj_ipadrr.modify(name, ip, netmask)

                    obj_portblock = PortBlockGroup()
                    obj_portblock.modify(f'{name}_prtblk_on', ip, port)
                    obj_portblock.modify(f'{name}_prtblk_off', ip, port)
                except Exception as ex:
                    self.logger.write_to_log('DATA', 'DEBUG', 'exception', 'Rollback', str(traceback.format_exc()))
                    RollBack.rollback(portal['ip'], portal['port'], portal['netmask'])
                    return

        # 暂不验证（见需求）

        # 更新数据
        portal['ip'] = ip
        portal['port'] = str(port)
        portal['netmask'] = str(netmask)
        for target in portal['target']:
            self.js.json_data['Target'][target]['ip'] = ip
            self.js.json_data['Target'][target]['port'] = str(port)
        self.js.commit_data()
        s.prt_log(f'Modify {name} successfully',0)


    def show(self):
        """
        用表格展示所有portal数据
        :return: all portal
        """
        list_header = ["Portal", "IP", "Port", "Netmask", "iSCSITarget"]
        list_data = []
        for portal, data in self.js.json_data['Portal'].items():
            list_data.append([portal, data['ip'], data['port'], data['netmask'], ",".join(data['target'])])
        table = s.make_table(list_header, list_data)
        s.prt_log(table, 0)
        return list_data


    def _check_name(self, name):
        result = s.re_search(r'^[a-zA-Z][a-zA-Z0-9_]*$', name)
        # 添加从JSON中验证这个Name有没有被portal使用
        return True if result else False

    def _check_IP(self, ip):
        result = s.re_search(
            r'^((2([0-4]\d|5[0-5]))|[1-9]?\d|1\d{2})(\.((2([0-4]\d|5[0-5]))|[1-9]?\d|1\d{2})){3}$', ip)
        # 添加从JSON中验证这个IP有没有被portal使用
        return True if result else False

    def _check_port(self, port):
        if not isinstance(port, int):
            return False
        return True if 3260 <= port <= 65535 else False

    def _check_netmask(self, netmask):
        if not isinstance(netmask, int):
            return False
        return True if 1 <= netmask <= 32 else False

    def _check_status(self, name):
        """
        验证portal的状态
        :param name: portal name
        :return:
        """
        time.sleep(1)
        obj_crm = CRMConfig()
        status = obj_crm.get_crm_res_status(name, type='IPaddr2')
        if status == 'STARTED':
            s.prt_log(f'Create {name} successfully', 1)
            return 'OK'
        elif status == 'NOT_STARTED':
            failed_actions = obj_crm.get_failed_actions(name)
            if failed_actions == 0:
                return 'NETWORK_ERROR'
            elif failed_actions:
                s.prt_log(failed_actions, 1)
                return 'OTHER_ERROR'
            else:
                s.prt_log('Unknown error, please check', 1)
                return 'UNKNOWN_ERROR'
        else:
            s.prt_log(f'Failed to create {name}, please check', 1)
            return 'FAIL'