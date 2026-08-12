#-*- coding：utf-8 -*-
import hps_ft
import time

def rs485_demo():
    ft_obj = [];
    for i in range(10):
        ft_obj.append(hps_ft.HPS_FT())
        ft_obj[i].createHandle(hps_ft.HpsSensorCommEnum.RS485)
        if(ft_obj[i].initial("",115200)!=hps_ft.HPS_FT_SUCCESS):
            ft_obj[i].uninitial()
            ft_obj[i].deleteHandle()
            ft_obj.pop(-1)
            print(ft_obj)
            break

    #设置清零滤波
    for obj in ft_obj:
        obj.setLowPassFilter(0)
        obj.zero()

    #单次模式
    for obj in ft_obj:
        obj.setStopSample()

    time.sleep(0.1)

    #单次模式采集
    for j in range(10):
        for obj in ft_obj:
            ft_pack = obj.getData()
            print(obj.getHandle(),ft_pack)
        time.sleep(0.01)

    #连续模式
    for obj in ft_obj:
        obj.setStartSample()

    time.sleep(0.1)

    #连续模式采集
    for j in range(10):
        for obj in ft_obj:
            ft_pack = obj.getData()
            print(obj.getHandle(),ft_pack)
        time.sleep(0.01)

    for obj in ft_obj:
        obj.setLowPassFilter(0)
        obj.zero()
        obj.setStopSample()

    time.sleep(0.1)

    #测试用1107 记得删除
    print("getT2")
    for obj in ft_obj:
        print(obj.getT2())

    for obj in ft_obj:
        obj.uninitial()
        obj.deleteHandle()

def ethernet_udp_demo():
    iphost=[["192.168.5.100",8080],["192.168.5.100",8000]]
    ft_obj = [];
    for i in range(10):
        ft_obj.append(hps_ft.HPS_FT())
        ft_obj[i].createHandle(hps_ft.HpsSensorCommEnum.EtherNet_UDP)
        if(ft_obj[i].initial(iphost[i][0],iphost[i][1])!=hps_ft.HPS_FT_SUCCESS):
            ft_obj[i].uninitial()
            ft_obj[i].deleteHandle()
            ft_obj.pop(-1)
            print(ft_obj)
            break

    for obj in ft_obj:
        obj.setLowPassFilter(0)
        obj.zero()

    time.sleep(0.1)

    for j in range(5):
        for obj in ft_obj:
            ft_pack = obj.getData()
            print(obj.getHandle(),ft_pack)
        time.sleep(0.01)

    for obj in ft_obj:
        obj.uninitial()
        obj.deleteHandle()

if __name__ == '__main__':
    for i in range(1):
        rs485_demo()
        #ethernet_udp_demo()
        time.sleep(1)
