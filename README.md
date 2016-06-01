# python-bpi-oled
使用 Python 控制香蕉派（BPI）SPI OLED（SSD1306） 的显示

### 介绍

使用 Python 以及 Adafruit 的 Python GPIO 库（Adafruit_Python_GPIO） 来控制 BPI 的 OLED 并循环显示网卡IP、流量、内存使用率及系统负载等信息。具体如下：

* 屏幕点阵是 128 x64，分两种字号显示，一种是 6 x 8，一种是 8 x 16，姑且称其为小号字和大号字；
* 以小号字的高度为参照，将屏幕显示分为 8 行（大号字占 2 行）；
* 把屏幕分为三个部分，最上面的两行为一个部分（这两行也刚好 LED 颜色为黄色，其余为蓝色），用来当作固定的标题区；最下面的一行为时间或滚动文字区；中间的为主内容区；
* 主内容区来回显示 WAN 口 IP 信息、WAN 口流量信息、内存使用率及系统负载；
* 底部主要显示时钟，附加滚动显示网络状态（分别对几个重点关注的 IP 进行定时 ping）。

### 运行环境

* 在 Bananian Linux 15.04 中测试通过；
* 需加载 spi-sun7i 模块；
* Python 2.7.3 版本
* 具体的环境配置可查看：https://www.dannysite.com/blog/244/

### Python 库

* Adafruit-GPIO==1.0.0
* Adafruit-PureIO==0.2.0
* PIL==1.1.7
* RPi.GPIO==0.5.8
* smbus==1.1
* spidev==3.2
