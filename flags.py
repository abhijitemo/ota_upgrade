'''
*  **********************************************
*
*   Project Name    :   IoT Model
*   Company Name    :   Emo Energy
*   File Name       :   flags.py
*   Description     :   Contains all flag variables
*   Author          :   Abhijit Narayan S
*   Created on      :   01-04-2024   
*      
*   © All rights reserved @EMO.Energy [www.emoenergy.in]
*   
*   *********************************************
'''
import sim
import modem
from machine import UART
from gnss import GnssGetData




#************* Global Variables *****************       DO NOT CHANGE THE CONTENTS OF THIS BLOCK            *****************************

Global_utc_time = None
Global_utc_date = None
SIM_IMSI = None #sim.getImsi()
SIM_ICCID = None #sim.getIccid() 
DEV_IMEI = None #modem.getDevImei() 
SERVER_ADDRESS = "emosens.in"
HANDLER_ADDRESS = "iot_handler.php"
SD_UPLOAD_FILENAME = '/sd/bms_data.txt'
SERVER_PORT =443
Log_file_path = None
BMS_UART = UART(UART.UART2, 9600, 8, 0, 1, 0)
GPS_UART = UART(UART.UART1, 9600, 8, 0, 1, 0)
GNSS = GnssGetData(1, 9600, 8, 0, 1, 0)
BMS_ID = ""
Pack_Voltage = 0
FTP_HOST = 'emosens.in'
FTP_PORT = 21
FTP_USER = 'hhxfnz5vxzp0'
FTP_PASSWD = 'Emo123!@**'
MAX_FILE_SIZE_MB = 1
FTP_DIR_BASE = 'public_html/'
faults = ''
lat = ''
lon = ''

#***************** FLAGS ********************           DO NOT CHANGE THE CONTENTS OF THIS BLOCK            *****************************

PDP_netw_conn_re_establish_flag = False
BMS_packet_received_flag = False
Format_data_exception_flag = False
First_BMS_Data_Received_flag = False
Data_present_in_queue_flag = False
Data_present_in_SD_card_flag = False
GPS_data_collection_status_flag = False
Failed_to_upload_data_to_server_flag = False
Network_connection_flag = False
SD_Card_working_status_flag = False
Hardware_init_status_flag = False
SSL_socket_conn_status_flag = False
Data_formatted_ready_for_upload_flag = False
Global_time_init_ntp_flag = False
Send_SMS_flag = True
Queue_filled_flag = False
