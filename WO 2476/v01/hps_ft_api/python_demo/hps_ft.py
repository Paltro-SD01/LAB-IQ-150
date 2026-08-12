#-*- coding：utf-8 -*-
import ctypes
import os
import sys
import platform

HPS_FT_NULL = -1
HPS_FT_FAIL = 0
HPS_FT_SUCCESS = 1
HPS_FT_SDK_VERSION_ = "1.0.0"


def machine():
    """Return type of machine."""
    if os.name == 'nt' and sys.version_info[:2] < (2, 7):
        return os.environ.get("PROCESSOR_ARCHITEW6432",
                              os.environ.get('PROCESSOR_ARCHITECTURE', ''))
    else:
        return platform.machine()


def os_bits(machine=machine()):
    """Return bitness of operating system, or None if unknown."""
    machine2bits = {'AMD64': 64, 'x86_64': 64, 'i386': 32, 'x86': 32, 'i686': 32, }
    return machine2bits.get(machine, None)


if (os_bits() == 32):
    #hps_ft_dll = ctypes.cdll.LoadLibrary("DLL_32/HPS_FTC_DLL_V2.dll")
    hps_ft_dll = ctypes.cdll.LoadLibrary("F:/Program Files/tt/QT/HPS_FT_Project/ProjectOut/release_86/hps_ft.dll")
else:
    #hps_ft_dll = ctypes.cdll.LoadLibrary("DLL_64/HPS_FTC_DLL_V2.dll")
    hps_ft_dll = ctypes.cdll.LoadLibrary("F:/Program Files/tt/QT/HPS_FT_Project/ProjectOut/release_64/hps_ft.dll")

hps_ft_dll.hps_ft_createHandle.restype = ctypes.c_int
hps_ft_dll.hps_ft_deleteHandle.restype = ctypes.c_int

hps_ft_dll.hps_ft_zero.restype = ctypes.c_int
hps_ft_dll.hps_ft_uninitial.restype = ctypes.c_int
hps_ft_dll.hps_ft_setStopSample.restype = ctypes.c_int
hps_ft_dll.hps_ft_setStartSample.restype = ctypes.c_int
hps_ft_dll.hps_ft_saveUserSetting.restype = ctypes.c_int
hps_ft_dll.hps_ft_getRange.restype = ctypes.c_int
hps_ft_dll.hps_ft_getInfo.restype = ctypes.c_int
hps_ft_dll.hps_ft_setLowPassFilter.restype = ctypes.c_int
hps_ft_dll.hps_ft_initial.restype = ctypes.c_int
hps_ft_dll.hps_ft_getData.restype = ctypes.c_int

hps_ft_dll.hps_ft_setToolTransform.restype = ctypes.c_int

hps_ft_dll.hps_ft_setIIRFilter.restype = ctypes.c_int
hps_ft_dll.hps_ft_setFIRFilter.restype = ctypes.c_int
hps_ft_dll.hps_ft_setMedianFilter.restype = ctypes.c_int
hps_ft_dll.hps_ft_setSmoothAverFilter.restype = ctypes.c_int
hps_ft_dll.hps_ft_setKalmanFilter.restype = ctypes.c_int

hps_ft_dll.hps_ft_setNetIP.restype = ctypes.c_int
hps_ft_dll.hps_ft_setNetMask.restype = ctypes.c_int
hps_ft_dll.hps_ft_setNetGateway.restype = ctypes.c_int
hps_ft_dll.hps_ft_setNetPortNumber.restype = ctypes.c_int

hps_ft_dll.hps_ft_setAlarmSignal.restype = ctypes.c_int
hps_ft_dll.hps_ft_clearAlarmSignal.restype = ctypes.c_int
hps_ft_dll.hps_ft_setAlarm.restype = ctypes.c_int
hps_ft_dll.hps_ft_getAlarmAxis.restype = ctypes.c_int
hps_ft_dll.hps_ft_setAlarmNormalOpen.restype = ctypes.c_int
hps_ft_dll.hps_ft_setAlarmThresholdValue.restype = ctypes.c_int


class HpsSensorCommEnum:
    RS485 = 0
    EtherNet_UDP = 1
    EtherNet_TCP = 2


class HpsFTCoord:
    HPS_FT_RUN = 10000  # 传感器运行
    HPS_ETHERNET_NO_SENSOR_ERROR = 11000  # 转接盒未连接传感器
    HPS_FT_GET_MATRIX_ERROR = 11001  # 传感器获取校正数据失败
    HPS_FT_TEMP_COF_ERROR = 11002  # 传感器温度数据异常
    HPS_FT_ADC_GAIN_ERROR = 11003  # 传感器ADC值获取异常
    HPS_FT_ADC_NUM_ERROR = 11004  # 传感器ADC数值异常
    HPS_FT_ZERO_RESET_ERROR = 11005  # 传感器清零失败
    HPS_FT_SET_DAC_ERROR = 11006  # 传感器设置ADC失败
    HPS_FT_NULL_MATRIX_ERROR = 11007  # 传感器无校正记录
    HPS_FT_DATA_ERROR = 11008  # 传感器数据异常（过载导致损坏）
    HPS_FT_ATTITUDE_SENSOR_INIT_ERROR = 11009  # 姿态传感器初始化失败
    HPS_FT_ATTITUDE_SENSOR_DATA_ERROR = 11010  # 姿态传感器输出数据错误
    HPS_FT_OVERLOAD_ERROR = 11011  # 传感器当前过载
    HPS_FT_NO_REFERENCE_VOLTAGE_ERROR = 11012  # 传感器不存在无负载基准电压
    HPS_FT_NO_CROSSTALK_MATRIX_ERROR = 11013  # 传感器无串扰补偿
    # 通讯状态
    HPS_COMM_RUN = 20000  # 运行
    HPS_COMM_CLOSE = 20001  # 关闭
    HPS_COMM_INIT = 20002  # 初始化
    HPS_COMM_IP_ERROR = 21000  # IP错误
    HPS_COMM_PORT_ERROR = 21001  # 端口错误
    HPS_COMM_TIMEOUT_ERROR = 21002  # 连接超时
    HPS_COMM_CMDRETURN_ERROR = 21003  # 指令设置错误
    HPS_COMM_THREAD_OPEN_ERROR = 21004  # 线程打开失败

class hps_ft_info(ctypes.Structure):
    _fields_ = [('code', ctypes.c_int), ('IPOC', ctypes.c_int),('code_info', ctypes.c_char * 256)]

class hps_ft_kalmanFilterPara(ctypes.Structure):
    _fields_ = [('kalman_k', ctypes.c_uint8), ('kalman_threshold', ctypes.c_int32),('num_check', ctypes.c_uint32)]


class HPS_FT(object):
    def __init__(self):
        self.__info = hps_ft_info()
        self.__handle = ctypes.c_int(-1)
        self.__ft = (ctypes.c_double * 6)()
        self.__axis = (ctypes.c_double * 6)()
        self.__range = (ctypes.c_double * 6)()
        self.__tr = ctypes.c_int(-1)

    def getHandle(self):
        return self.__handle

    def __dump_dict(self,data):
        info = {}
        # 通过_fields_获取每一个字段
        # 检查每个字段的类型，根据不同类型分别处理
        # 支持递归迭代
        for k, v in data._fields_:
            av = getattr(data, k)
            if type(v) == type(ctypes.Structure):
                av = av.dump_dict()
            elif type(v) == type(ctypes.Array):
                av = ctypes.cast(av, ctypes.c_char_p).value.decode()
            else:
                pass
            info[k] = av
        return info

    def array2list(self, c_array):
        return [i for i in c_array]

    def list2array(self, py_list, len):
        return (ctypes.c_double * len)(*(tuple(i for i in py_list)))

    def createHandle(self,ft_CommEnum):
        """
        *创建对象
        """
        self.__handle = ctypes.c_int(hps_ft_dll.hps_ft_createHandle(ctypes.c_int(ft_CommEnum)))
        return self.__handle

    def deleteHandle(self):
        """
        *销毁对象
        """
        return hps_ft_dll.hps_ft_deleteHandle(ctypes.pointer(self.__handle))

    def zero(self):
        """
        *传感器清零.
        """
        return hps_ft_dll.hps_ft_zero(self.__handle)

    def uninitial(self):
        """
        *断开传感器连接
        """
        return hps_ft_dll.hps_ft_uninitial(self.__handle)

    def setStopSample(self):
        return hps_ft_dll.hps_ft_setStopSample(self.__handle)

    def setStartSample(self):
        return hps_ft_dll.hps_ft_setStartSample(self.__handle)

    def saveUserSetting(self):
        return hps_ft_dll.hps_ft_saveUserSetting(self.__handle)

    def getRange(self):
        self.__tr = hps_ft_dll.hps_ft_getRange(self.__handle, ctypes.pointer(self.__range))
        return (self.__tr, self.array2list(self.__range))

    def getInfo(self):
        self.__tr = hps_ft_dll.hps_ft_getInfo(self.__handle, ctypes.pointer(self.__info))
        return (self.__tr, self.__dump_dict(self.__info))

    def setLowPassFilter(self,level):
        return hps_ft_dll.hps_ft_setLowPassFilter(self.__handle, ctypes.c_uint8(level))

    def initial(self, ip, port):
        return hps_ft_dll.hps_ft_initial(self.__handle, ctypes.c_int(port), ctypes.c_char_p(ip.encode()))

    def getData(self):
        self.__tr = hps_ft_dll.hps_ft_getData(self.__handle, ctypes.pointer(self.__ft), ctypes.pointer(self.__info))
        return (self.__tr, self.array2list(self.__ft), self.__dump_dict(self.__info))

    def setToolTransform(self,toolTransform):
        return hps_ft_dll.hps_ft_setToolTransform(self.__handle, self.list2array(toolTransform, 6))

    def setIIRFilter(self, enable):
        return hps_ft_dll.hps_ft_setIIRFilter(self.__handle, ctypes.c_bool(enable))

    def setFIRFilter(self, enable):
        return hps_ft_dll.hps_ft_setFIRFilter(self.__handle, ctypes.c_bool(enable))

    def setMedianFilter(self, level):
        return hps_ft_dll.hps_ft_setMedianFilter(self.__handle, ctypes.c_uint8(level))

    def setSmoothAverFilter(self, level):
        return hps_ft_dll.hps_ft_setSmoothAverFilter(self.__handle, ctypes.c_uint8(level))

    def setKalmanFilter(self,enable, f_para, t_para):
        return hps_ft_dll.hps_ft_setKalmanFilter(self.__handle, ctypes.c_bool(enable), ctypes.pointer(f_para), ctypes.pointer(t_para))

    def setNetIP(self, ip):
        return hps_ft_dll.hps_ft_setNetIP(self.__handle, ctypes.c_char_p(ip.encode()))

    def setNetMask(self, mask):
        return hps_ft_dll.hps_ft_setNetMask(self.__handle, ctypes.c_char_p(mask.encode()))

    def setNetGateway(self, gateway):
        return hps_ft_dll.hps_ft_setNetGateway(self.__handle, ctypes.c_char_p(gateway.encode()))

    def setNetPortNumber(self, portNumber):
        return hps_ft_dll.hps_ft_setNetPortNumber(self.__handle, ctypes.c_uint16(portNumber))

    def setAlarmSignal(self):
        return hps_ft_dll.hps_ft_setAlarmSignal(self.__handle)

    def clearAlarmSignal(self):
        return hps_ft_dll.hps_ft_clearAlarmSignal(self.__handle)

    def setAlarm(self, enable):
        return hps_ft_dll.hps_ft_setAlarm(self.__handle, ctypes.c_bool(enable))

    def getAlarmAxis(self):
        self.__tr = hps_ft_dll.hps_ft_getAlarmAxis(self.__handle, ctypes.pointer(self.__axis))
        return (self.__tr, self.array2list(self.__axis))

    def setAlarmNormalOpen(self, enable):
        return hps_ft_dll.hps_ft_setAlarmNormalOpen(self.__handle, ctypes.c_bool(enable))

    def setAlarmThresholdValue(self, value):
        return hps_ft_dll.hps_ft_setAlarmThresholdValue(self.__handle, self.list2array(value, 6))
