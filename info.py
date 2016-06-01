# -*-coding:utf-8 -*-
"""
Created on 2016-5-29

@author: Danny
DannyWork Project
"""

import os
import socket
import fcntl
import struct
import re


def get_interfaces(match=None):
    f = os.popen("ifconfig -s|grep -v Iface|grep -v lo|awk '{print $1}'")
    interfaces = [interface.strip() for interface in f.readlines()]
    f.close()

    if match:
        interfaces = [interface for interface in interfaces if re.match(match, interface)]

    return interfaces


def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        return socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,
            struct.pack('256s', ifname[:15])
        )[20:24])
    except IOError:
        return '-'


def get_memory_stat():
    mem = {}

    f = open('/proc/meminfo')
    lines = f.readlines()
    f.close()

    for line in lines:
        if len(line) < 2:
            continue
        name = line.split(':')[0]
        var = line.split(':')[1].split()[0]
        mem[name] = float(var)
    mem['MemUsed'] = mem['MemTotal'] - mem['MemFree']
    return mem


def get_load_stat():
    f = open('/proc/loadavg')
    con = f.read().split()
    f.close()

    return {
        'lavg_1': con[0],
        'lavg_5': con[1],
        'lavg_15': con[2],
        'nr': con[3],
        'last_pid': con[4]
    }


def get_interface_flow(interface):
    f = open('/proc/net/dev')
    flow_info = f.readlines()
    in_flow = []
    out_flow = []
    f.close()

    for eth_dev in flow_info:
        if interface in eth_dev:
            in_flow.append(int(eth_dev.split(':')[1].split()[0]))
            out_flow.append(int(eth_dev.split(':')[1].split()[8]))

    return sum(in_flow), sum(out_flow)
