'''
*  **********************************************
*
*   Project Name    :   IoT Model
*   Company Name    :   Emo Energy
*   File Name       :   Extract.py
*   Description     :   Extracts the required data from the BMS
*   Author          :   Abhijit Narayan S
*   Created on      :   01-04-2024   
*      
*   © All rights reserved @EMO.Energy [www.emoenergy.in]
*   
*   *********************************************
'''

import ussl
import usocket as socket
import ujson
from ujson import dumps
from machine import RTC
import usr.flags as flags
import utime
import sim
import ql_fs
from usr.GPS import extract_lat_lon
from ucollections import deque
import modem
import usr.logging as I_LOG

rtc = RTC()
global_datetime_list = []



def extract_data(bms_id, bms_data, gps_data):
    data_parts = [value for value in bms_data.split(',') if value]
    imsi = sim.getImsi()
    iccid = flags.SIM_ICCID
    imei = flags.DEV_IMEI
    result = {
        "IMEI": imei,
        "IMSI": imsi,
        "ICCID": iccid,
        "Network_operator": None,
        "Time": None,
        "Date": None,
        "DeviceID": bms_id,
        "Data": {
            "packVoltage": None,
            "packCurrent": None,
            "SOC": None,
            "CellData": None,
            "TemperatureData": None,
            "Faults": None,
            "Latitude": None,
            "Longitude": None,
            "Data_Type": None,
        },
    }

    try:
        result["Data"]["packVoltage"] = int(data_parts[20]) / 100.0
        flags.Pack_Voltage = int(data_parts[20]) / 100.0
    except (ValueError) as e:
        I_LOG.error("[BMS_Extract]", "Failed to extract packVoltage: {}".format(e))

    try:
        result["Data"]["packCurrent"] = int(data_parts[21]) / 100.0
    except (ValueError) as e:
        I_LOG.error("[BMS_Extract]", "Failed to extract packCurrent: {}".format(e))

    try:
        result["Data"]["SOC"] = int(data_parts[22])
    except (ValueError) as e:
        I_LOG.error("[BMS_Extract]", "Failed to extract SOC: {}".format(e))

    try:
        result["Data"]["CellData"] = [int(value) / 1000.0 for value in data_parts[2:16]]
    except (ValueError) as e:
        I_LOG.error("[BMS_Extract]", "Failed to extract CellData: {}".format(e))

    try:
        result["Data"]["TemperatureData"] = [int(value) for value in data_parts[16:20]]
    except (ValueError) as e:
        I_LOG.error("[BMS_Extract]", "Failed to extract TemperatureData: {}".format(e))

    try:
        result["Data"]["Faults"] = ([int(value) for value in data_parts[23:29]])
        flags.faults = ([int(value) for value in data_parts[23:29]])
    except (ValueError) as e:
        I_LOG.error("[BMS_Extract]", "Failed to extract Faults: {}".format(e))

    try:
        latitude, longitude = extract_lat_lon(gps_data)
        result["Data"]["Latitude"] = str(latitude)
        flags.lat = str(latitude)
        result["Data"]["Longitude"] = str(longitude)
        flags.lon = str(longitude)
    except Exception as e:
        I_LOG.error("[BMS_Extract]", "Failed to extract GPS data: {}".format(e))

    try:
        current_time = rtc.datetime()
        date_time_str = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(current_time[0], current_time[1], current_time[2], current_time[4], current_time[5], current_time[6])
        result["Time"] = date_time_str.split()[1]
        result["Date"] = date_time_str.split()[0]
        global_datetime_list.append(date_time_str)
    except Exception as e:
        I_LOG.error("[BMS_Extract]", "Failed to extract current time: {}".format(e))
    
    result["Network_operator"] = '1'  # Assuming this is a constant value
    result["Data"]["Data_Type"] = "R"  # Set to "R" if data_type is None

    I_LOG.info("[BMS_Extract]", "Data extraction completed successfully")
    
    return result
