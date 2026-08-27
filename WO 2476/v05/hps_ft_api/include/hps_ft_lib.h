#ifndef HPS_FT_LIB_H
#define HPS_FT_LIB_H
#include <stdint.h>
#ifdef _LINUX_
    #ifdef HPS_FT_LIB_LIBRARY
        #define HPS_FT_API __attribute__((visibility("default")))
    #else
        #define HPS_FT_API
    #endif
#else
    #ifdef HPS_FT_LIB_LIBRARY
        #define HPS_FT_API __declspec(dllexport)
    #else
        #define HPS_FT_API __declspec(dllimport)
    #endif
#endif

#ifdef __cplusplus
extern "C" {
#endif
#define HPS_FT_NULL -1
#define HPS_FT_FAIL 0
#define HPS_FT_SUCCESS 1
#define HPS_FT_SDK_VERSION_ "1.0.1"

typedef int HPS_FT_HANDLE;

#ifndef HPS_SENSOR_STRUCT
#define HPS_SENSOR_STRUCT
enum HpsInfoCode {
    FT_N0RMAL = 10000,
    ETHERNET_NO_SENSOR_ERROR = 11000,
    FT_GET_MATRIX_ERROR = 11001,
    FT_TEMP_COF_ERROR = 11002,
    FT_ADC_GAIN_ERROR = 11003,
    FT_ADC_NUM_ERROR = 11004,
    FT_ZERO_RESET_ERROR = 11005,
    FT_SET_DAC_ERROR = 11006,
    FT_NULL_MATRIX_ERROR = 11007,
    FT_DATA_ERROR = 11008,
    FT_ATTITUDE_SENSOR_INIT_ERROR = 11009,
    FT_ATTITUDE_SENSOR_DATA_ERROR = 11010,
    FT_OVERLOAD_ERROR = 11011,
    FT_NO_REFERENCE_VOLTAGE_ERROR = 11012,
    FT_NO_CROSSTALK_MATRIX_ERROR = 11013,

    //通讯状态 COMM_STATE
    COMM_N0RMAL = 20000,
    COMM_CLOSE = 20001,
    COMM_INIT = 20002,
    COMM_IP_ERROR = 21000,
    COMM_PORT_ERROR = 21001,
    COMM_TIMEOUT_ERROR = 21002,
    COMM_CMDRETURN_ERROR = 21003,
    COMM_THREAD_OPEN_ERROR = 21004,
};

enum HpsSensorCommEnum {
    RS485,
    EtherNet_UDP,
    EtherNet_TCP,
};

typedef struct hps_ft_info_t
{
    HpsInfoCode code;
    int IPOC;
    char code_info[256];
}hps_ft_info;

typedef struct hps_ft_deviceModeInfo_t
{
    uint8_t model;  //型号
    uint8_t range; //量程标号
    uint16_t id; //设备的唯一id
    uint8_t year;  //年
    uint8_t month; //月
    uint8_t date;  //日
}hps_ft_deviceModeInfo;

typedef struct hps_ft_ip_host_t
{
    int host;  //型号
    char ip[256]; //量程标号
}hps_ft_ip_host;

/*
*f_par.kalman_K = 20;
*f_par.kalman_threshold = 3000;
*f_par.num_check = 3;
*t_par.kalman_K = 20;
*t_par.kalman_threshold = 2;
*t_par.num_check = 3;
*/
typedef struct KalmanFilterPara_t
{
    uint8_t kalman_K;
    int32_t kalman_threshold;
    uint32_t num_check;
}KalmanFilterPara;
#endif

/**
*创建对象
*/
HPS_FT_API HPS_FT_HANDLE  hps_ft_createHandle(HpsSensorCommEnum comm);

/**
*销毁对象
*/
HPS_FT_API int  hps_ft_deleteHandle(HPS_FT_HANDLE *handle);


//通用指令
HPS_FT_API int  hps_ft_zero(HPS_FT_HANDLE handle);
HPS_FT_API int  hps_ft_uninitial(HPS_FT_HANDLE handle);
HPS_FT_API int  hps_ft_setStopSample(HPS_FT_HANDLE handle);
HPS_FT_API int  hps_ft_setStartSample(HPS_FT_HANDLE handle);
HPS_FT_API int  hps_ft_saveUserSetting(HPS_FT_HANDLE handle);
HPS_FT_API int  hps_ft_getRange(HPS_FT_HANDLE handle, double range[]);
HPS_FT_API int  hps_ft_getInfo(HPS_FT_HANDLE handle, hps_ft_info &info);
HPS_FT_API int  hps_ft_setLowPassFilter(HPS_FT_HANDLE handle, uint8_t range);
HPS_FT_API int  hps_ft_initial(HPS_FT_HANDLE handle, int port, const char *ip);
HPS_FT_API int  hps_ft_getData2(HPS_FT_HANDLE handle, double m_ftData[6]);
HPS_FT_API int  hps_ft_getData(HPS_FT_HANDLE handle, double m_ftData[6], hps_ft_info &info);


//以太网指令
//传感器中心点偏移(尽量不用)
HPS_FT_API int  hps_ft_setToolTransform(HPS_FT_HANDLE handle, double ToolTransform[6]);

//滤波类 FILTER
HPS_FT_API int  hps_ft_setIIRFilter(HPS_FT_HANDLE handle, bool enable);
HPS_FT_API int  hps_ft_setFIRFilter(HPS_FT_HANDLE handle, bool enable);
HPS_FT_API int  hps_ft_setMedianFilter(HPS_FT_HANDLE handle, uint8_t range);
HPS_FT_API int  hps_ft_setSmoothAverFilter(HPS_FT_HANDLE handle, uint8_t range);
HPS_FT_API int  hps_ft_setKalmanFilter(HPS_FT_HANDLE handle, bool isendble, KalmanFilterPara f_para, KalmanFilterPara t_para);

//以太网设置类 NET_SETTING
HPS_FT_API int  hps_ft_setNetIP(HPS_FT_HANDLE handle, const char *ip);
HPS_FT_API int  hps_ft_setNetMask(HPS_FT_HANDLE handle, const char *mask);
HPS_FT_API int  hps_ft_setNetGateway(HPS_FT_HANDLE handle, const char *gateway);
HPS_FT_API int  hps_ft_setNetPortNumber(HPS_FT_HANDLE handle, uint16_t portNumber);

//IO报警类 ALARM_SETTING
HPS_FT_API int  hps_ft_setAlarmSignal(HPS_FT_HANDLE handle);
HPS_FT_API int  hps_ft_clearAlarmSignal(HPS_FT_HANDLE handle);
HPS_FT_API int  hps_ft_setAlarm(HPS_FT_HANDLE handle, bool enable);
HPS_FT_API int  hps_ft_getAlarmAxis(HPS_FT_HANDLE handle, uint8_t axis[6]);
HPS_FT_API int  hps_ft_setAlarmNormalOpen(HPS_FT_HANDLE handle, bool enable);
HPS_FT_API int  hps_ft_setAlarmThresholdValue(HPS_FT_HANDLE handle, double value[6]);

#ifdef __cplusplus
}
#endif
#endif // HPS_FT_LIB_H
