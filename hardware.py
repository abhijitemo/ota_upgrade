import utime
import usr.flags as flags
import checkNet
from uos import VfsSd
import uos
from misc import Power
from usr.network import check_net  # Import the check_net function
import usr.logging as I_LOG
import usr.SD_CARD as I_SD
import ql_fs  # Import the ql_fs library for file operations
import sms

LOG_FILE_PATH = '/sd/log_files.txt'



def hardware_check():
    print("********************* HARDWARE CONNECTIONS CHECK ********************")
    
    print("CHECKING NETWORK PRESENCE")
    
    # Use the check_net function from network.py
    network_status = check_net()
    if network_status == 1:
        flags.Network_connection_flag = True
    else:
        flags.Network_connection_flag = False
    
    print("CHECKING SD CARD PRESENCE")

    flags.SD_Card_working_status_flag = I_SD.initialize_sd_card()
    
    
    if flags.Network_connection_flag is True:
        if flags.SD_Card_working_status_flag is True:
            I_LOG.info("[SIM]", "Network and Data available....!")
            I_LOG.info("[SD_CARD]", "SD Card mount success...!")
            I_LOG.initialize_logging()
        else:
            I_LOG.info("[SIM]", "Network and Data available....!")
            I_LOG.error("[SD_CARD]", "SD Card mount failed...!")
            #Power.powerRestart()
    else:
        if flags.SD_Card_working_status_flag:
            I_LOG.info("[SD_CARD]", "SD Card mount success...!")
            I_LOG.initialize_logging()
            I_LOG.error("[SD_CARD]", "Network Error(No DATA/NETWORK in SIM)...! (Redirecting saves to SD CARD)")
            

        else:
            I_LOG.error("[SIM]", "Network Error(No DATA/NETWORK in SIM)...!")
            I_LOG.error("[SD_CARD]", "SD Card mount failed...!")
            Power.powerRestart()
    
    print("********************* HARDWARE CONNECTIONS CHECK COMPLETE ********************")

def config_init():
    # Read the JSON file to get the configuration
    config_file_path = 'usr/Device_config.json'
    device_config = ql_fs.read_json(config_file_path)

    # Update the BMS_Uart and GPS_Uart settings in flags.py
    flags.BMS_UART = flags.UART(flags.UART.UART2, device_config['BMS_Uart'], 8, 0, 1, 0)
    flags.GPS_UART = flags.UART(flags.UART.UART1, device_config['GPS_Uart'], 8, 0, 1, 0)

    
    flags.SERVER_ADDRESS = device_config['SERVER_ADDRESS']
    flags.HANDLER_ADDRESS = device_config['HANDLER_ADDRESS']
    sms.deleteMsg(1,4) 
    # Log the updated configurations
    I_LOG.info("[CONFIG]", "BMS_UART set to {}".format(device_config['BMS_Uart']))
    I_LOG.info("[CONFIG]", "GPS_UART set to {}".format(device_config['GPS_Uart']))
    I_LOG.info("[CONFIG]", "Server Address set to {}".format(device_config['SERVER_ADDRESS']))
    I_LOG.info("[CONFIG]", "Handler Address set to {}".format(device_config['HANDLER_ADDRESS']))
    I_LOG.info("[CONFIG]", "Cleared SMS messages {}")
    # If needed, save any changes back to the config file
    ql_fs.touch(config_file_path, device_config)

def update_bms_uart(baud_rate):
    try:
        device_config = ql_fs.read_json('usr/Device_config.json')
        device_config['BMS_Uart'] = baud_rate
        ql_fs.touch('usr/Device_config.json', device_config)
        I_LOG.info("[CONFIG_UPDATE]", "BMS_UART updated in Device_config.json to {}".format(baud_rate))

    except Exception as e:
        I_LOG.error("[CONFIG_UPDATE]", "Failed to update BMS_UART: {}".format(e))
