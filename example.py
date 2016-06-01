#!/usr/bin/python
# -*-coding:utf-8 -*-
"""
Created on 2016-5-29

@author: Danny
DannyWork Project
"""

import Queue
import random
import threading
import time
import datetime
import ping

import Adafruit_GPIO.SPI as SPI

from info import get_interfaces, get_ip_address, get_memory_stat, get_load_stat, get_interface_flow
from ssd1306 import SSD1306_128_64


WAN_INTERFACE = 'eth1'
PING_TEST_IPS = {
    '114DNS': '114.114.114.114',
    'OpenDNS': '208.67.222.222',
}


class TitleController(threading.Thread):
    """
    标题控制
    """

    queue = None
    broadcast = None
    titles = ['BPI-M1-Plus', 'OLED Display']

    def __init__(self, queue, broadcast):
        threading.Thread.__init__(self)
        self.queue = queue
        self.broadcast = broadcast

    def run(self):
        while True:
            for i in range(len(self.titles)):
                self.queue.put({'pos': 'title', 'content': self.titles[i]})
                time.sleep(10)


class FooterController(threading.Thread):
    """
    尾行控制
    """

    queue = None
    broadcast = None
    timer = 0

    default_broadcast = "Visit my website at http://www.dannysite.com"

    def __init__(self, queue, broadcast):
        threading.Thread.__init__(self)
        self.queue = queue
        self.broadcast = broadcast
        self.timer = time.time()

    def display_scroll_content(self):
        try:
            content = self.broadcast.get_nowait()
        except Queue.Empty:
            content = self.default_broadcast

        def content_iter():
            i = 0
            length = len(content) + 21
            while i < length:
                i += 1
                c = content[max(i - 21, 0):i]
                c = c.rjust(21) if i < 21 else c.ljust(21)
                yield c

        return content_iter

    def display_time(self):
        return datetime.datetime.now().strftime('%m-%d %H:%M')

    def run(self):
        while True:
            content = self.display_scroll_content() if (time.time() - self.timer) > 30 else self.display_time()

            if callable(content):
                for c in content():
                    self.queue.put({'pos': 'footer', 'content': c, 'align': 'right'})
                    time.sleep(0.15)
                self.timer = time.time()
            else:
                self.queue.put({'pos': 'footer', 'content': content, 'align': 'right'})
                time.sleep(2)


class MainContentController(threading.Thread):
    """
    主内容区控制
    """

    queue = None

    last_in_flow = 0
    last_out_flow = 0
    lst = time.time()

    def __init__(self, queue, broadcast):
        threading.Thread.__init__(self)
        self.queue = queue
        self.broadcast = broadcast

    def display_interface_information(self):
        """
        WAN 口信息显示
        """

        lines = ['<NETWORK>'.center(21), ' ' * 22, 'WAN Interface:'.ljust(21)]

        wan = get_interfaces('^({0})\w*'.format(WAN_INTERFACE))
        if wan:
            wan_text = get_ip_address(wan[0]) or 'Not connected'
        else:
            wan_text = 'Error'
        lines.append(wan_text.center(21))

        return ''.join(lines)

    def display_interface_speed(self):
        """
        WAN 口速率
        """

        lines = ['<NETWORK>'.center(22), 'Bandwidth Usage:'.ljust(21)]

        in_flow, out_flow = get_interface_flow('eth0')

        cst = time.time()
        flow_avg = [(in_flow - self.last_in_flow) / float(cst - self.lst) / 1048576.0,
                    (out_flow - self.last_out_flow) / float(cst - self.lst) / 1048576.0]
        lines.append('{0:.3f} m/s in'.format(flow_avg[0]).center(21))
        lines.append('{0:.3f} m/s out'.format(flow_avg[1]).center(21))

        self.last_in_flow, self.last_out_flow, self.lst = in_flow, out_flow, cst

        return ''.join(lines)

    def display_memory_usage(self):
        """
        内存使用率
        """

        lines = ['<SYSTEM>'.center(22), ' ' * 22, 'Memory Usage:'.ljust(21)]

        mem = get_memory_stat()
        lines.append('{0:.2f}%'.format(mem['MemUsed'] / float(mem['MemTotal']) * 100).center(21))

        return ''.join(lines)

    def display_load_avg(self):
        """
        负载
        """

        lines = ['<SYSTEM>'.center(22), ' ' * 22, 'Load Avg:'.ljust(21)]

        load_avg = get_load_stat()
        lines.append('{0} {1} {2}'.format(load_avg['lavg_1'], load_avg['lavg_5'], load_avg['lavg_15']).center(21))

        return ''.join(lines)

    def run(self):
        while True:
            for display_func in ['display_interface_information', 'display_interface_speed',
                                 'display_memory_usage', 'display_load_avg']:
                self.queue.put({'pos': 'content', 'content': getattr(self, display_func)()})
                time.sleep(5)


class NetWorkTester(threading.Thread):
    """
    网络测试
    """

    queue = None
    broadcast = None
    is_gfw_open = False

    test_ips = PING_TEST_IPS

    def __init__(self, queue, broadcast):
        threading.Thread.__init__(self)
        self.queue = queue
        self.broadcast = broadcast

    def run(self):
        while True:
            time.sleep(random.randint(30, 120))
            text = 'Network Status: '
            for name, ip in self.test_ips.items():
                last_time = ping.do_one(ip, 3)
                last_time = int(last_time * 1000) if last_time else '-'
                text += '{0}: {1}ms, '.format(name, last_time)
            self.broadcast.put(text[:-2])


class OLEDDisplay:
    """
    BPI OLED 显示控制
    """

    disp = None
    queue = None

    broadcasts = None

    def __init__(self):
        self.disp = SSD1306_128_64(rst=25, dc=24, spi=SPI.SpiDev(0, 0, max_speed_hz=8000000))
        self.disp.begin()

        self.queue = Queue.Queue()
        self.broadcasts = Queue.Queue()

    def init_threads(self):
        for controller in [TitleController, MainContentController, FooterController, NetWorkTester]:
            t = controller(self.queue, self.broadcasts)
            t.setDaemon(True)
            t.start()

    def quit(self):
        self.disp.clear()
        self.disp.display()

    def set_text_align(self, align, text, length):
        func = {
            'left': 'ljust',
            'right': 'rjust',
            'center': 'center'
        }.get(align)
        return getattr(text, func)(length)

    def set_title(self, content, align):
        self.disp.set_chars(self.set_text_align(align, content[:16], 16), size='8_16')

    def set_content(self, content, align):
        self.disp.set_chars(self.set_text_align(align, content[:105], 105), location=256)

    def set_footer(self, content, align):
        self.disp.set_chars(self.set_text_align(align, content[:21], 21), location=896)

    def main_loop(self):
        # 初始化线程
        self.init_threads()

        # 定时扫描 queue 并刷新屏幕内容
        while True:
            content = self.queue.get()
            getattr(self, 'set_{0}'.format(content.get('pos')))(content.get('content'), content.get('align', 'left'))
            self.disp.display()


if __name__ == '__main__':
    controller = OLEDDisplay()
    try:
        controller.main_loop()
    except KeyboardInterrupt:
        controller.quit()
