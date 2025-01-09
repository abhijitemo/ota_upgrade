import utime
import _thread
from machine import RTC, Timer
import ql_fs
import sms
import app_fota
import uos
import usr.flags as flags
from misc import Power
from usr.BMS_data import get_bms_data
from usr.GPS import get_gps_data
from usr.Data_Extract import extract_data
from usr.Network_upload import SimpleSSLClient
from usr.SD_CARD import save_to_sd_card, initialize_sd_card, sd_extract,sd_ftp_send
from usr.ota_upgrade import sms_callback
import usr.logging as I_LOG
import sim
import modem
from machine import UART
from usr.hardware import hardware_check, config_init, update_bms_uart

MAX_QUEUE_SIZE = 10
data_queue_real = []
data_queue_save = []
data_lock = _thread.allocate_lock()
upload_in_progress = False
data_queue_sd = []
sd_max_queue_size = 5
rtc = RTC()

# State Definitions
STATE_IDLE = 0
STATE_START = 1
STATE_HARDWARE_CHECK = 2
STATE_SYSTEM_CONFIG = 3
STATE_DATA_ACQUISITION = 4
STATE_BATCH_PROCESSING = 5
STATE_SD_CARD_BACKUP = 6
STATE_SD_CARD_PROCESSING =7
STATE_OTA_CHECK = 8
STATE_SD_CARD_UPLOAD = 9
STATE_RETRY = 10


current_state = STATE_IDLE

def set_state(state):
    global current_state
    current_state = state

def start():
    print('')
    I_LOG.info("[START]", "Entering Start State")
    I_LOG.info("[START]", "Module Powered-ON [CODE : {}] ".format(Power.powerOnReason()))
    I_LOG.info("[START]", "Configuring Device Parameters......!")
    flags.DEV_IMEI = modem.getDevImei()
    print(flags.DEV_IMEI)
    if(flags.DEV_IMEI != -1):
        I_LOG.info("[START]", "Fetched DEV IMEI")
        return 1
    else:
        I_LOG.info("[START]", "Dev IMEI Error")
        return -1

def data_fetch():
    try:
        I_LOG.info("[DATA_FETCH]", "Fetching BMS and GPS data")
        bms_id, bms_data = get_bms_data()
        gps_data = get_gps_data()
        utime.sleep(1)
        return bms_id, bms_data, gps_data
    
    except Exception as e:
        I_LOG.error("[DATA_FETCH]", "Error fetching data: {}".format(e))
        utime.sleep(1)
        return None, None, None
    

def process_acquired_data(bms_id, bms_data, gps_data):
    try:
        I_LOG.info("[DATA_EXTRACT]", "Processing acquired data")
        extracted_data = extract_data(bms_id, bms_data, gps_data)
        return extracted_data
    except Exception as e:
        I_LOG.error("[DATA_EXTRACT]", "Failed to process acquired data: {}".format(e))
        return None

def append_data_to_queue(extracted_data, bms_data):
    with data_lock:
        data_queue_real.append(extracted_data)
        #data_queue_save.append(bms_data)
        data_queue_save.append(extracted_data)
    I_LOG.info("[DATA_EXTRACT]", "Data appended to queue. Queue size: {}".format(len(data_queue_real)))

def prepare_data_for_upload():
    global upload_in_progress
    data_to_upload = []
    data_to_save = []

    with data_lock:
        if len(data_queue_real) >= MAX_QUEUE_SIZE and not upload_in_progress:
            upload_in_progress = True
            data_to_upload = data_queue_real[:]
            data_to_save = data_queue_save[:]
            del data_queue_real[:]
            del data_queue_save[:]
            I_LOG.info("[DATA_EXTRACT]", "Prepared real-time data for upload.")

    return data_to_upload, data_to_save

def upload_data(client, combined_data_to_upload):
    try:
        I_LOG.info("[NETWORK_UPLOAD]", "Uploading combined real-time and SD card data (if available) to network")
        response = client.send_data_over_ssl(combined_data_to_upload)
        return response
    except Exception as e:
        I_LOG.error("[NETWORK_UPLOAD]", "Failed to upload combined data to network: {}".format(e))
        return False

def save_data_to_sd_card(data_to_save):
    try:
        I_LOG.info("[SD_CARD]", "Saving data to SD card")
        save_to_sd_card('sd/bms_data.txt', data_to_save)
    except Exception as e:
        I_LOG.error("[SD_CARD]", "Failed to save data to SD card: {}".format(e))

def reset_upload_in_progress():
    global upload_in_progress
    upload_in_progress = False
    I_LOG.info("[NETWORK_UPLOAD]", "Upload in progress reset")

def sd_card_data_task():
    I_LOG.info("[SD_CARD]", "SD card data task triggered")
    try:
        I_LOG.info("[SD_CARD]", "Saving queued data to SD card")
        if data_queue_save:
            save_data_to_sd_card(data_queue_save)
            I_LOG.info("[SD_CARD]", "Data successfully backed up to SD card.")
            data_queue_save.clear()
        else:
            I_LOG.info("[SD_CARD]", "No data available for SD card backup.")
    except Exception as e:
        I_LOG.error("[SD_CARD]", "Error during SD card backup: {}".format(e))


def check_for_ota_upgrade():
    try:
        I_LOG.info("[FOTA]", "Setting up SMS Callback for OTA and other functions")
        sms.setCallback(sms_callback)
    except Exception as e:
        I_LOG.error("[FOTA]", "Failed to check for OTA upgrade: {}".format(e))



def delete_sd_card_file():
    I_LOG.info("[SD_CARD]", "Deleting SD card file")
    try:
        size = ql_fs.path_getsize('sd/bms_data.txt')
        if size >= 1000000:
            uos.remove('sd/bms_data.txt')
        config = ql_fs.read_json('usr/Device_config.json')
        config['SD_START_LINE'] = 0
    except OSError as e:
        I_LOG.error("[SD_CARD]", "Error deleting SD card file: {}".format(e))
