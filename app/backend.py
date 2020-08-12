#!/usr/bin/env python3
#
# Robert Lynch (C) 2020
# rob@rlyn.ch
#
#
# backend.py


import os, json, sys, hashlib, yaml
from jnpr.junos.factory.factory_loader import FactoryLoader
from jnpr.junos import Device
from jnpr.junos.utils.config import Config
from collections import OrderedDict
from lxml import etree
import jxmlease

from collections import OrderedDict

directory_root=os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..'))

def login(username, password):
    #Tries to open the users file
    try:
        with open(directory_root+"/users.json") as jsonfile:
            usersFile=json.load(jsonfile)
    except:
        print("Could not open \'users.json\'")
        sys.exit()
    
    #Looks to confirm the username is in the file, then sees if the md5 has of the file is equal to the entry in the usersfile
    if username in usersFile and hashlib.md5(password.encode()).hexdigest()==usersFile[username]['password']:
        response={"Success":{"username":username, 
                            "name":usersFile[username]['name']
                            }
                }
        return response #md5 has equals the password
    else:
        return {"Error":"Invalid credentials"} #either the username is not in the users file or the password is not the same value

def loadSwitches():
    try:
        with open(directory_root+"/switches.json") as jsonfile:
            return json.load(jsonfile)
    except:
        print("Could not open \'switches.json\'")
        sys.exit()

def updateSwitchInterfaceList(ipAddress, intNum, intUp, alarm_count):
    switches=loadSwitches()
    dicIndex=next((i for i, item in enumerate(switches['switches']) if item["ipAddress"] == ipAddress), None)
    switches['switches'][dicIndex]
    switches['switches'][dicIndex]['interface_count']=intNum
    switches['switches'][dicIndex]['interfaces_up']=intUp
    switches['switches'][dicIndex]['alarm_count']=alarm_count
    
    with open(directory_root+"/switches.json", 'w') as outfile:
        json.dump(switches, outfile,indent=2, sort_keys=True)



def countInterfaces():
    switches=loadSwitches()['switches']
    intCount=upCount=alarmCount = 0

    for i in switches:
        if 'interface_count' in i:
            intCount+=i['interface_count']
        if 'interfaces_up' in i:
            upCount+=i['interfaces_up']
        if 'alarm_count' in i:
            alarmCount+=i['alarm_count']
    return {'intCount':intCount, 'upCount':upCount, 'switchCount': len(switches), 'alarm_count':alarmCount}

def getSwitchName(ipaddress):
    switches=loadSwitches()
    for i in switches['switches']:
       if i['ipAddress']==ipaddress:
           return i['name']
    return {"Error":"IP address not found"}

def getAlarms(ipAddress):
    with open(directory_root+"/config.json") as jsonfile:
        configFile=json.load(jsonfile)
    


    dev = Device(host=ipAddress, user=configFile['username'], password=configFile['password'])
    try:
        dev.open(auto_probe=5)
    except:
        return ipAddress,{"Error": "Connection refused"}
    rpc = dev.rpc.get_alarm_information()
    rpc_xml = etree.tostring(rpc, pretty_print=True, encoding='unicode')
    dev.close()
    return ipAddress, jxmlease.parse(rpc_xml)['alarm-information']

def getVLANs(ipAddress, junosUsername, junosPassword):
    dev = Device(host=ipAddress, user=junosUsername, password=junosPassword)
    try:
        dev.open(auto_probe=5)
    except:
        return {"Error": "Connection refused"}
    rpc = dev.rpc.get_vlan_information()
    rpc_xml = etree.tostring(rpc, pretty_print=True, encoding='unicode')
    dev.close()
    return jxmlease.parse(rpc_xml)['vlan-information']


def getInterfaces(ipAddress, junosUsername, junosPassword):
    #Creates a view for PyEZ
    yml = '''
---
EthPortTable:
  rpc: get-interface-information
  args:
    extensive: True
    interface_name: '[agxe][et]*'
  args_key: interface_name
  item: physical-interface
  view: EthPortView

EthPortView:
  fields:
    interface: name
    description: description
    admin_status: admin-status
    link_status: oper-status
    bpdu_error: bpdu-error
    mtu: mtu
    mode: logical-interface/address-family/address-family-flags/ifff-port-mode-trunk
    inet: logical-interface/address-family/interface-address
    lacp: logical-interface/address-family/ae-bundle-name
'''
    globals().update(FactoryLoader().load(yaml.load(yml, Loader=yaml.FullLoader))) #loads the yaml file
    dev = Device(host=ipAddress, user=junosUsername, password=junosPassword)
    try:
        dev.open(auto_probe=5)
    except:
        return {"Error": "Connection refused"}
    dev.timeout=120
    interfaceTable = EthPortTable(dev).get()
    if len(interfaceTable)<1:
        dev.close()
        return {"Error":"Failed to find interface"}
    interfaceList=[]
    for i in interfaceTable:
        scripts=[{"script":"setInterfaceDescription","name":"Set Description"}, {"script":"getInterfaceConfig","name":"Get Configuration"}]
        if i.mtu=="9216":
            jumbo="enabled"
        else:
            jumbo="disabled"
        try:
            if len(i.mode)>0:
                mode="trunk"
        except:
            try:
                if len(i.inet)>0:
                    mode="layer 3"
            except:
                try:
                    if len(i.lacp)>0:
                        mode="lacp-"+i.lacp.split(".")[0]
                except:
                    mode="access"
        if mode=="trunk":
            scripts.append({"script":"trunkVLANdelete","name":"Delete Trunk VLAN"})
            scripts.append({"script":"changeAccessVLAN","name":"Change Access VLAN"})
            scripts.append({"script":"trunkVLANadd","name":"Add Trunk VLAN"})
        if mode=="access":
            scripts.append({"script":"changeAccessVLAN","name":"Change Access VLAN"})
            scripts.append({"script":"trunkVLANadd","name":"Add Trunk VLAN"})
        if i.link_status=="up" and (mode=="trunk" or mode=="access"):
            scripts.append({"script":"getMACtable","name":"Get MAC Table"})
        interfaceList.append({
            'name':i.name,
            'description' : i.description,
            'admin_status' : i.admin_status,
            'link_status' : i.link_status,
            'jumbo_frames':jumbo,
            'mode':mode,
            'scripts':scripts
        })
    dev.close()
    upCount=0
    #counts up interfaces
    for i in interfaceList:
        if i['link_status']=='up':
            upCount+=1

    try:
        alarmCount=getAlarms(ipAddress=ipAddress)[1]['alarm-summary']['active-alarm-count']
    except:
        alarmCount=0
    updateSwitchInterfaceList(ipAddress=ipAddress, intNum=len(interfaceList), intUp=upCount, alarm_count=int(alarmCount))

    return interfaceList

def getInterfaceConfig(ipAddress, interface, junosUsername, junosPassword):
    dev = Device(host=ipAddress, user=junosUsername, password=junosPassword, port=22)
    try:
        dev.open(auto_probe=5)
    except:
        return {"Error": "Connection refused"}
    try:
        resp = dev.rpc.get_config(filter_xml=etree.XML("""<configuration>
                                                                  <interfaces>
                                                                      <interface>
                                                                          <name>"""+interface+"""</name>
                                                                          <description/>
                                                                          <unit/>
                                                                      </interface>
                                                                  </interfaces>
                                                              </configuration>"""))
    except:
       dev.close()
       return {"Error":"Failed to find interface"}
    rpc_xml=etree.tostring(resp, encoding='unicode', pretty_print=True)
    result = jxmlease.parse(rpc_xml)
    if result['configuration']==None or result['configuration']=='': #If the configuration comes back Null
        return {"Error":"No configuration"}

    result=result['configuration']['interfaces']['interface']
    if 'description' not in result:
        result['description']=None
    dev.close()
    return result

def setDescription(ipAddress, interface, junosUsername, junosPassword, description):
    dev = Device(host=ipAddress, user=junosUsername, password=junosPassword, port=22)
    try:
        dev.open(auto_probe=5)
    except:
        return {"Error": "Connection refused"}

    dev.timeout=120
    conf=Config(dev)
    configString = 'set interfaces '+ str(interface)+' description \"'+description+'\"'
    try:
        conf.load(configString, format='set')
    except:
        dev.close()
        return {"Error": "Failed to load config"}
    try:
        conf.commit()
    except:
        try: #if the commit failes, we try to rollback the changes
            conf.rollback(rb_id=0)
        except:
            dev.close()
        dev.close()
        return {"Error": "Failed to commit config"}
    return {"Success": "Successfully commited interface description"}

def changeAccessVLAN(ipAddress, interface, junosUsername, junosPassword, vlan):
    dev = Device(host=ipAddress, user=junosUsername, password=junosPassword, port=22)
    try:
        dev.open(auto_probe=5)
    except:
        return {"Error": "Connection refused"}

    dev.timeout=120
    conf=Config(dev)
    
    #deletes the existing vlans
    configString = 'delete interfaces {}.0 family ethernet-switching vlan'.format(interface)
    try:
        conf.load(configString, format='set')
    except:
        i=1 #nonsense continuation

    configString = 'set interfaces {}.0 family ethernet-switching port-mode access vlan members {}'.format(interface, vlan)
    try:
        conf.load(configString, format='set')
    except:
        dev.close()
        return {"Error": "Failed to load config"}
    try:
        conf.commit()
    except:
        try: #if the commit failes, we try to rollback the changes
            conf.rollback(rb_id=0)
        except:
            dev.close()
        dev.close()
        return {"Error": "Failed to commit config"}
    return {"Success": "Successfully commited interface description"}

def trunkVLANadd(ipAddress, interface, junosUsername, junosPassword, vlan):
    dev = Device(host=ipAddress, user=junosUsername, password=junosPassword, port=22)
    try:
        dev.open(auto_probe=5)
    except:
        return {"Error": "Connection refused"}

    dev.timeout=120
    conf=Config(dev)
    configString = 'set interfaces {}.0 family ethernet-switching port-mode trunk vlan members {}'.format(interface, vlan)
    try:
        conf.load(configString, format='set')
    except:
        dev.close()
        return {"Error": "Failed to load config"}
    try:
        conf.commit()
    except:
        try: #if the commit failes, we try to rollback the changes
            conf.rollback(rb_id=0)
        except:
            dev.close()
        dev.close()
        return {"Error": "Failed to commit config"}
    return {"Success": "Successfully commited interface description"}

def trunkVLANdelete(ipAddress, interface, junosUsername, junosPassword, vlan):
    dev = Device(host=ipAddress, user=junosUsername, password=junosPassword, port=22)
    try:
        dev.open(auto_probe=5)
    except:
        return {"Error": "Connection refused"}

    dev.timeout=120
    conf=Config(dev)
    
    #deletes the vlans
    configString = 'delete interfaces {}.0 family ethernet-switching vlan members {}'.format(interface, vlan)
    try:
        conf.load(configString, format='set')
    except:
        dev.close()
        return {"Error": "Failed to load config"}
    try:
        conf.commit()
    except:
        try: #if the commit failes, we try to rollback the changes
            conf.rollback(rb_id=0)
        except:
            dev.close()
        dev.close()
        return {"Error": "Failed to commit config"}
    return {"Success": "Successfully commited interface description"}

def getMACtable(ipAddress, interface, junosUsername, junosPassword):
    dev = Device(host=ipAddress, user=junosUsername, password=junosPassword, port=22)
    try:
        dev.open(auto_probe=5)
    except:
        return {"Error": "Connection refused"}

    dev.timeout=120
    yml = '''
---
EtherSwTable:
  rpc: get-interface-ethernet-switching-table
  item: ethernet-switching-table/mac-table-entry[mac-type='Learn']
  key: mac-address
  view: EtherSwView
EtherSwView:
  fields:
    vlan_name: mac-vlan
    mac: mac-address
    mac_type: mac-type
    mac_age: mac-age
    interface: mac-interfaces-list/mac-interfaces
'''

    globals().update(FactoryLoader().load(yaml.load(yml, Loader=yaml.FullLoader)))
    table = EtherSwTable(dev)
    try:
        table.get()
    except:
        dev.close()
        return {"Error": "Failed to get table"}
    response=[]
    if len(table)>0:
        for i in table:
            if i.interface==(interface+".0"):
                response.append({
                    "vlan_name":i.vlan_name,
                    "mac": i.mac,
                    "mac_type": i.mac_type,
                    "mac_age": i.mac_age
                })
    return response