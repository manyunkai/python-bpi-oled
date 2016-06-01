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
    """
    获取网络接口

    :param match: 正则匹配条件，当传入此参数时，只有满足条件的才返回
    :return: list
    """

    f = os.popen("ifconfig -s|grep -v Iface|grep -v lo|awk '{print $1}'")
    interfaces = [interface.strip() for interface in f.readlines()]
    f.close()

    if match:
        interfaces = [interface for interface in interfaces if re.match(match, interface)]

    return interfaces


def get_ip_address(ifname):
    """
    获取接口 IP 地址
    :param ifname: 接口名称
    :return: IP 地址，如果没有返回 '-'
    """

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
    """
    获取内存信息

    :return: dict
    """

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
    """
    获取系统负载信息

    :return: dict
    """

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


def get_interface_flow(interfaces):
    """
    获取网卡流量

    :param interfaces: 要获取的网卡名称列表
    :return: tuple：(流入流量, 流出流量)
    """

    f = open('/proc/net/dev')
    flow_info = f.readlines()
    in_flow = []
    out_flow = []
    f.close()

    for eth_dev in flow_info:
        try:
            iface, data = [d.strip() for d in eth_dev.split(':')]
        except ValueError:
            continue
        if iface in interfaces:
            in_flow.append(int(data.split()[0]))
            out_flow.append(int(data.split()[8]))

    return sum(in_flow), sum(out_flow)
