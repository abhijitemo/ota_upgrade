'''
*  **********************************************
*
*   Project Name    :   IoT Model
*   Company Name    :   Emo Energy
*   File Name       :   AT_commands.py
*   Description     :   Sending AT commands to receive the data from the BMS.
*   Author          :   Abhijit Narayan S
*   Created on      :   01-04-2024   
*      
*   © All rights reserved @EMO.Energy [www.emoenergy.in]
*   
*   *********************************************
'''





from machine import UART
import utime
import usr.flags as flags
import ql_fs
import usr.logging as I_LOG
uart_port = 2 
uart_baudrate = 9600  
uart2 = flags.BMS_UART



def callback(para):
        if(0 == para[0]):
            uartRead(para[2])
def uartRead():
    try:
        msg = uart2.readline()
        utf8_msg = msg.decode()
        I_LOG.info("[BMS_UART]", "Received UART message: {}".format(utf8_msg.strip()))
        return utf8_msg
    except Exception as e:
        I_LOG.error("[BMS_UART]", "Failed to read UART message: {}".format(e))
        return None

def uartWrite(msg):
        uart2.write(msg)
        I_LOG.info("[BMS_UART]", "Sent UART message: {}".format(msg))


def get_bms_data():
    #data_response = uartRead()
    data_response = "AT+,A04061223,3145,3165,3185,3204,3145,3165,3185,3204,3145,3165,3185,3204,3145,3165,45,46,48,49,4846,02104,023,001,000,001,001,001,001,\r\n"
    #utime.sleep(1)
    if data_response:
        parts = data_response.split(',')
        bms_id = parts[1] if len(parts) > 1 else None
        flags.BMS_ID = bms_id
        I_LOG.info("[BMS_UART]", "BMS Data received: {}".format(parts))
        
    else:
        bms_id = None
        data_response = None    

    return bms_id, data_response


