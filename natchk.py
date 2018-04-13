#! /usr/bin/python
# -*- coding:utf-8 -*- 
#  
# @Version : 1.0  
# @Time    : 2018/4/1
# @Author  : hejl
# @File    : natchk.py  
# @Summery : Detect client's local network on which type of NAT

'''
测试用户所在环境的NAT设备类型
NAT1: Full Cone
NAT2: Restricted Cone
NAT3: Port-Restricted Cone
NAT4: Symmetric

拓普模型:
两服务端 + 一客户端，服务端要求有有独立公网IP，至少一台，
客户端在要测试的网络环境机器上执行, 服务端的防火墙需放行相关的UDP端口
                                                         C(client)
            ＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿|＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿＿
          1|   ↑8            2|    ↑7               ↑6                                   ↑9               10|   ↑11
           ↓   |              ↓    |                |                                    |                  |   |
Server1    S1:P1              S1:P2               S1:P3                                  |                  |   |
           |----------------------------------------↑3          4                    5   |                  ↓   |
Server2    +----------------------------------------------------→ S2:P1 -------------→  S2:P2 ------------→ S2:P3

序列图: (UDP响应无顺序性，6/7/8/9先后到达不影响)
c         S1:P1        S1:P2       S1:P3                 S2:P1        S2:P2          S2:P3
|           |            |           |                     |            |              |
|---------->| 1          |           |                     |            |              |
|-----------+----------->|2          |                     |            |              |
|<----------+------------|           |                     |            |              |
|7          |            |           |                     |            |              |
|           |------------+---------->|3                    |            |              |
|           |------------+-----------+-------------------->|4           |              |
|6          |            |           |                     +----------->|5             |
|<----------+------------------------|                     |            |              |
|8          |            |           |                     |            |              |
|<----------+            |           |                     |            |              |
|           |            |           |                     |            |              |
 <----------+------------+-----------+---------------------+------------|              |
|9          |            |           |                     |            |              |
|           |            |           |                     |            |              |
|           |            |           |                     |            |              |
|-----------+------------+-----------+---------------------+------------+------------->|10
|<----------+------------+-----------+---------------------+------------+--------------|11
|           |            |           |                     |            |              |
|           |            |           |                     |            |              |
|           |            |           |                     |            |              |

响应的rStep(程序内的标识响应的身份)与上面时序标号关系:
rStep1 <---> 8
rStep2 <---> 7
rStep3 <---> 3
rStep4 <---> 9
rStep5 <---> 11

传参: 
s1: 服务端1
s2: 服务端2 [可选，没有时会降低准确度]
c:  客户端

运行环境注意:
    此工具服务端和客户端都使本同一程序文件，服务端要求有两个公网IP(相应端口不能被防火墙拦截)，客户端要求能连通公网；

使用示例:
1. 获得natchk.py文件之后，修改程序开始处的服务器地址
   s1_ip='第一台具备公网IP的机器'  (本文件85行)
   s2_ip='第二台具备公网IP的机器'  (本文件90行)
2. 运行服务端程序
   第一台上运行 python natchk.py s1
   第二台上运行 python natchk.py s2
3. 在待检测的环境运行客户端程序
   python natchk.py c
   网络正常的话10内打印出检测结果
   结果输出样式Test Summery: NAT3 Port Restricted
'''

import threading
import socket
import json
import sys

s1_ip='162.219.126.121'
s1_port1=17770 # listen and recv+resp
s1_port2=17771 # listen and recv+resp
s1_port3=18770 # sendto

s2_ip='183.60.124.69'
s2_port1=27770 # listen for s1 notify; 
s2_port2=27771 # sendto
s2_port3=28770 # listen and recv+resp # check Symmetric (Last)

c_ip='0'
c_port=0
wait_timeout_ms = 5

def createUdpSock(ip, port):
    us = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if ip > 0 and port > 0:
        us.bind( (ip,port) )
        print("socket Bind to " + str(us.getsockname()) )

    return us

def udpSendTo(us, serv, port, data):
    strdata = json.dumps(data)
    return us.sendto(strdata, (serv, port))

def udpRecvFrom(us, waitsec, count):
    try:
        datalst = []
        us.settimeout(waitsec)
        for i in range(count):
            datalst.append(us.recvfrom(1024))
    except socket.timeout, e:
        pass
    return datalst


def loadJsonStr(datastr):
    try:
        dt = json.loads(datastr)
    except ValueError,e:
        dt = {}
    return dt

# Server-1 Process
def Server1_1():
    serv1 = createUdpSock(s1_ip, s1_port1)
    serv3 = createUdpSock(s1_ip, s1_port3)
    while True:
        datastr,addr = serv1.recvfrom(1024)
        datadict = loadJsonStr(datastr)
        datadict["cli_addr"] = addr[0]
        datadict["cli_port"] = addr[1]

        s1log = []
        # notify Server2 Sendto
        if s2_ip:
            datadict["rStep"] = 4
            nret = udpSendTo(serv1, s2_ip, s2_port1, datadict)
            s1log.append('notify S2(%s) nsend=%d' % (s2_ip, nret))
        datadict["rStep"] = 3
        nret = udpSendTo(serv3, addr[0], addr[1], datadict) # other port response
        s1log.append('s1_port3 resp nsend=%d' % nret)

        datadict["rStep"] = 1
        datadict["msglog"] = s1log
        nret = udpSendTo(serv1, addr[0], addr[1], datadict) # response echo
        s1log.append('s1_port1 resp nsend=%d' % nret)
        print("Serv1-Recv| client="+str(addr)+'| detail=' + ';'.join(s1log))

# Server-1 Process
def Server1_2():
    ServEcho(s1_ip, s1_port2, 2)

def ServEcho(servIP, servPort, rStep):
    serv = createUdpSock(servIP, servPort)
    while True:
        datastr,addr = serv.recvfrom(1024)
        datadict = loadJsonStr(datastr)
        datadict["cli_addr"] = addr[0]
        datadict["cli_port"] = addr[1]
        datadict["rStep"] = rStep
        udpSendTo(serv, addr[0], addr[1], datadict)


# Server-2 Process # listen for Server1's notify
def Server2_1():
    serv1 = createUdpSock(s2_ip, s2_port1)
    serv2 = createUdpSock(s2_ip, s2_port2)
    while True:
        datastr,addr = serv1.recvfrom(1024)
        datadict = loadJsonStr(datastr)
        if not "cli_addr" in datadict:
            print('Invalid NotifyMsg:'+datastr)
            continue
        cliaddr = datadict["cli_addr"]
        cliport = datadict["cli_port"]
        # datadict["rStep"] = 4
        nret = udpSendTo(serv2, cliaddr, cliport, datadict)
        print('Serv1(%s) Notify test Client(%s), nsend=%d' % (addr,cliaddr, nret) )

# Server-2 Process # Check Last
def Server2_2():
    ServEcho(s2_ip, s2_port3, 5)

# check is valid bind IP addr for server
def isValidServAddr(ipv4):
    try:
        addrs = socket.getaddrinfo(socket.gethostname(),None)
    except:
        addrs = []
    addrlist = [item[4][0] for item in addrs if ':' not in item[4][0]]
    bret = ipv4 in addrlist
    if not bret:
        try:
            stmp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            stmp.bind( (ipv4, 60330) )
            bret = True
        except BaseException,e:
            bret = False
            print('IpAddr %s isnot local addr%s'%(ipv4, addrlist))
            print(e)
        finally:
            stmp.close()
    return bret

def runS1():
    if not isValidServAddr(s1_ip):
        return 1

    t1 = threading.Thread(target=Server1_1, name='S1-Listen1')
    t2 = threading.Thread(target=Server1_2, name='S1-Echo')

    t1.start()
    t2.start()
    t1.join()
    t2.join()
    return 0

def runS2():
    if not isValidServAddr(s2_ip):
        return 2

    t1 = threading.Thread(target=Server2_1, name='S2-ListenNotify')
    t2 = threading.Thread(target=Server2_2, name='S2-Echo')

    t1.start()
    t2.start()
    t1.join()
    t2.join()
    return 0

# client process
def runClient():
    clisock = createUdpSock(c_ip, c_port)

    udpSendTo(clisock, s1_ip, s1_port1, {'step': 1})
    udpSendTo(clisock, s1_ip, s1_port2, {'step': 2})
    print('client Sock is %s' % str(clisock.getsockname()))

    # 接收各路响应
    resplst1 = udpRecvFrom(clisock, wait_timeout_ms, 4)

    resplst2 = []
    if s2_ip > '':
        udpSendTo(clisock, s2_ip, s2_port3, {'step': 3}) # server-2 echo
        resplst2 = udpRecvFrom(clisock, wait_timeout_ms, 1)

    clisock.close()
    calcSummery(resplst1, resplst2)

def calcSummery(rsp1, rsp2):
    rspmap = {}
    for item in rsp1+rsp2:
        nitem = json.loads(item[0])
        nitem['serv'] = item[1]
        rspmap[nitem.get('rStep')] = nitem
        print(nitem)
    if not 1 in rspmap:
        print('Server1 not work Or Offline')
        return
    if s2_ip > '' and not 5 in rspmap:
        print('Server2 not work')
        return
    
    nat_type = 'unknow'
    if s2_ip > '': # 完整的服务
        if 4 in rspmap:
            nat_type = 'NAT1 Cone'
        elif rspmap[1]['cli_port'] != rspmap[5]['cli_port']:
            nat_type = 'NAT4 Symmetric'
        elif 3 in rspmap:
            nat_type = 'NAT2 Address Restricted'
        else:
            nat_type = 'NAT3 Port Restricted'
    else:
        if rspmap[1]['cli_port'] != rspmap[2]['cli_port']:
            nat_type = 'NAT4 Symmetric'
        elif 3 in rspmap:
            nat_type = 'NAT2 Address Restricted(Maybe) or NAT1'
        else:
            nat_type = 'NAT3 Port Restricted(Maybe)'
    
    print("Test Summery: "+nat_type)


if __name__ == "__main__":
    param = ''
    if len(sys.argv) > 1:
        param = sys.argv[1]
    runfunlst = {'s1': runS1, 's2': runS2, 'c': runClient}
    while not param in runfunlst:
        param = raw_input('''Please Select Run Mode:
        s1: Server-1 Process
        s2: Server-2 Process
        c:  Client  
        >>''')
        param = param.strip()

    run = runfunlst[param]
    run()