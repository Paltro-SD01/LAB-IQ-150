#include <iostream>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <string>
#include<windows.h>
#include "../include/hps_ft_lib.h"

void test_handle()
{

    double ft_data[6];
    hps_ft_info ft_info;
    HPS_FT_HANDLE ft_handle[10];

    for (size_t i = 0; i < 10; i++)
    {
        ft_handle[i]=hps_ft_createHandle(HpsSensorCommEnum::RS485);
        std::cout << ft_handle[i] << std::endl;
    }


    size_t num_ft = 0;
    for (size_t i = 0; i < 10; i++)
    {
        if(hps_ft_initial(ft_handle[i],115200,"")!=HPS_FT_SUCCESS){
            num_ft = i;
            std::cout <<"Automatic connection "<< num_ft <<" desk equipment!"<< std::endl;
            break;
        }
    }

    for (size_t i = num_ft; i < 10; i++)
    {
        hps_ft_deleteHandle(&ft_handle[i]);
        std::cout << num_ft <<ft_handle[i] << "hps_ft_deleteHandle" << std::endl;
    }

    for (size_t j = 0; j < num_ft; j++)
    {
        if(hps_ft_setLowPassFilter(ft_handle[j],0)!=HPS_FT_SUCCESS){
            std::cout << ft_handle[j] <<" hps_ft_setLowPassFilter ERROR!"<< std::endl;
        }

        if(hps_ft_zero(ft_handle[j])!=HPS_FT_SUCCESS){
            std::cout << ft_handle[j] <<" hps_ft_zero ERROR!"<< std::endl;
        }

        Sleep(100);
    }

    for (size_t i = 0; i < 1000; i++)
    {
        for (size_t j = 0; j < num_ft; j++)
        {
            if(hps_ft_getData(ft_handle[j],ft_data, ft_info)==HPS_FT_SUCCESS){
                std::cout << ft_handle[j] << "\t" << ft_info.IPOC << "\t" << int(ft_info.code) << "\t" << ft_info.code_info;
                std::cout << "[\t";
                for (int j = 0; j < 6; j++)
                {
                    std::cout << ft_data[j];
                    std::cout << "\t";
                }
                std::cout << "]" << std::endl;
            }
            else{
                std::cout << ft_handle[j] <<" hps_ft_getData ERROR!"<< std::endl;
                std::cout << ft_info.IPOC << "\t" << int(ft_info.code) << "\t" << ft_info.code_info<< std::endl;
                break;
            }
            Sleep(100);
        }
    }

    for (size_t i = 0; i < num_ft; i++)
    {
        if(hps_ft_uninitial(ft_handle[i])!=HPS_FT_SUCCESS){
            std::cout << ft_handle[i] <<" hps_ft_uninitial ERROR!"<< std::endl;
        }

        hps_ft_deleteHandle(&ft_handle[i]);
        std::cout << num_ft <<ft_handle[i] << "hps_ft_deleteHandle" << std::endl;
    }
}

void test_rs485()
{
    double ft_data[6];
    hps_ft_info ft_info;
    HPS_FT_HANDLE ft_rs485_handle;
    ft_rs485_handle=hps_ft_createHandle(HpsSensorCommEnum::RS485);

    if(hps_ft_initial(ft_rs485_handle,115200,"")!=HPS_FT_SUCCESS){
        std::cout << ft_rs485_handle <<" hps_ft_initial ERROR!"<< std::endl;
    }

    if(hps_ft_setLowPassFilter(ft_rs485_handle,0)!=HPS_FT_SUCCESS){
        std::cout << ft_rs485_handle <<" hps_ft_setLowPassFilter ERROR!"<< std::endl;
    }

    if(hps_ft_zero(ft_rs485_handle)!=HPS_FT_SUCCESS){
        std::cout << ft_rs485_handle <<" hps_ft_zero ERROR!"<< std::endl;
    }

    for (size_t i = 0; i < 10; i++)
    {
        if(hps_ft_getData(ft_rs485_handle,ft_data, ft_info)==HPS_FT_SUCCESS){
            std::cout << ft_info.IPOC << "\t" << int(ft_info.code) << "\t" << ft_info.code_info;
            std::cout << "[\t";
            for (int j = 0; j < 6; j++)
            {
                std::cout << ft_data[j];
                std::cout << "\t";
            }
            std::cout << "]" << std::endl;
            Sleep(100);
        }
        else{
            std::cout << ft_rs485_handle <<" hps_ft_getData ERROR!"<< std::endl;
            std::cout << ft_info.IPOC << "\t" << int(ft_info.code) << "\t" << ft_info.code_info<< std::endl;
            break;
        }
    }

    if(hps_ft_uninitial(ft_rs485_handle)!=HPS_FT_SUCCESS){
        std::cout << ft_rs485_handle <<" hps_ft_uninitial ERROR!"<< std::endl;
    }

    hps_ft_deleteHandle(&ft_rs485_handle);
}

int main()
{
    std::cout << "Hello World!" << std::endl;

    test_handle();

    //test_rs485();

    std::cout << "Hello World End!" << std::endl;
    return 0;
}


