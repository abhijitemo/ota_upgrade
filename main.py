import utime
import _thread
from machine import Timer, WDT
from usr.hardware import hardware_check, config_init
import usr.iot_sm as state
import ql_fs
from misc import Power
import usr.flags as flag
import sms
import net
from usr.ota_upgrade import sms_callback
import usr.logging as I_LOG
from usr.network import checkNet  # Import the checkNet module for network status checking


MAX_RETRIES = 5
retry_count = 0
timer1 = Timer(Timer.Timer1)
network_timer = Timer(Timer.Timer2)  # Timer for network status check
failed_state = None
sd_card_backup_start_time = None
sd_upload_fail_count = 0
SD_UPLOAD_FILENAME = flag.SD_UPLOAD_FILENAME
sd_upload_flag = False

# Watchdog Timer Initialization
wdt = WDT(120)  # Enables the watchdog and sets the timeout period to 240 seconds

def feed_watchdog(t):
    """Feed the watchdog to prevent system reset."""
    I_LOG.info("[WATCHDOG]", "Watchdog Timer FED")
    wdt.feed()

def module_reset():
    I_LOG.info("[MODULE_RESET]", "Maximum retries reached, resetting module")
    Power.powerRestart()

def reset_retry_count():
    global retry_count
    retry_count = 0

def increment_retry_count():
    global retry_count
    retry_count += 1
    if retry_count >= MAX_RETRIES:
        module_reset()

def check_network_and_reset(t):
    global sd_card_backup_start_time, last_sms_time
    stage, state = checkNet.waitNetworkReady(30)
    range_value = net.csqQueryPoll()  # Getting the network range

    current_time = utime.time()

    if stage == 3 and state == 1:
        I_LOG.info("[NETWORK_CHECK]", "Network connection successful during SD card backup.")
        try:
            sms.sendTextMsg('7356820493', 'Network connection restored. Range: {}'.format(range_value), 'GSM')
            I_LOG.info("[SMS]", "Sent SMS: Network connection restored.")
            retry_count+=1
            if(range_value<12):
                module_reset()
            increment_retry_count()
        except Exception as e:
            I_LOG.error("[SMS]", "Failed to send SMS: {}".format(e))
        
        sd_card_backup_start_time = None  # Reset the start time as the connection is back
        last_sms_time = None  # Reset the last SMS time
    else:
        I_LOG.warning("[NETWORK_CHECK]", "Network connection failed during SD card backup. stage={}, state={}".format(stage, state))
        message = "Network down for 30 minutes. Range: {}".format( range_value)
        try:
            sms.sendTextMsg('7356820493', message, 'GSM')
            
            last_sms_time = current_time  # Update the last SMS time
        except Exception as e:
            I_LOG.info("[SMS]", "No data sent to network for 30 minutes: {}".format(message))
            I_LOG.error("[SMS]", "Failed to send SMS: {}".format(e))
        module_reset()



def state_machine():
    global failed_state
    current_state = state.STATE_START   

    while True:
        if current_state == state.STATE_START:
            print("[STATE_MACHINE]", "Entering START state")
            state.start()
            state.check_for_ota_upgrade() #setting up sms callback
            feed_watchdog(None)
            current_state = state.STATE_HARDWARE_CHECK
            utime.sleep(1)
        
        elif current_state == state.STATE_HARDWARE_CHECK:
            I_LOG.info("[STATE_MACHINE]", "Entering HARDWARE_CHECK state")
            try:
                hardware_check()
                #initialize_logging()
                feed_watchdog(None)
                current_state = state.STATE_SYSTEM_CONFIG
            except Exception as e:
                I_LOG.error("[HARDWARE_CHECK]", "Error in hardware check: {}".format(e))
                failed_state = current_state  
                current_state = state.STATE_RETRY  

        elif current_state == state.STATE_SYSTEM_CONFIG:
            I_LOG.info("[STATE_MACHINE]", "Entering SYSTEM CONFIG state")
            try:
                config_init()
                feed_watchdog(None)
                current_state = state.STATE_DATA_ACQUISITION
            except Exception as e:
                I_LOG.error("[SYSTEM_CONFIG]", "Error in system config: {}".format(e))
                failed_state = current_state  
                current_state = state.STATE_RETRY  

        elif current_state == state.STATE_DATA_ACQUISITION:
            I_LOG.info("[STATE_MACHINE]", "Entering DATA_ACQUISITION state")
            global SD_UPLOAD_FILENAME, sd_upload_fail_count, sd_upload_flag
            try:
                bms_id, bms_data, gps_data = state.data_fetch()
                feed_watchdog(None)
                if ql_fs.path_exists(SD_UPLOAD_FILENAME):
                    if sd_upload_fail_count < 3 and ql_fs.path_getsize(SD_UPLOAD_FILENAME) >= 100000 and net.csqQueryPoll() >=20:
                        print(ql_fs.path_getsize(SD_UPLOAD_FILENAME))
                        current_state = state.STATE_SD_CARD_UPLOAD  
                        sd_upload_flag = True
                if bms_data is None:
                    I_LOG.warning("[DATA_ACQUISITION]", "BMS data is None, retrying data acquisition")
                    utime.sleep(1)
                    current_state = state.STATE_DATA_ACQUISITION  # Stay in data acquisition state
                elif bms_data.startswith("AT+UART=1"):
                    state.update_bms_uart(9600)
                    I_LOG.info("[BMS_UART]", "BMS_UART updated to 9600.....Restarting")
                    Power.powerRestart()
                elif bms_data.startswith("AT+UART=2"):
                    state.update_bms_uart(57600)
                    I_LOG.info("[BMS_UART]", "BMS_UART updated to 57600.....Restarting")
                    Power.powerRestart()
                elif bms_data.startswith("AT+UART=3"):
                    state.update_bms_uart(115200)
                    I_LOG.info("[BMS_UART]", "BMS_UART updated to 115200.....Restarting")
                    Power.powerRestart()
                elif bms_data.startswith("AT+RESET"):
                    I_LOG.info("[MODULE_RESET]", "AT+RESET received, resetting module")
                    Power.powerRestart()
                elif bms_id and bms_data and bms_data.startswith("AT+") and sd_upload_flag is False:
                    extracted_data = state.process_acquired_data(bms_id, bms_data, gps_data)
                    if extracted_data:
                        state.append_data_to_queue(extracted_data, bms_data)
                        current_state = state.STATE_BATCH_PROCESSING
                elif bms_id and not bms_data and sd_upload_flag is False:
                    I_LOG.warning("[DATA_ACQUISITION]", "Invalid BMS data, retrying...")
                    current_state = state.STATE_DATA_ACQUISITION  # Repeat data acquisition
                feed_watchdog(None)
            except Exception as e:
                I_LOG.error("[DATA_ACQUISITION]", "Error in data acquisition: {}".format(e))
                failed_state = current_state  
                current_state = state.STATE_RETRY  # Only move to retry if an actual exception occurs
    

        elif current_state == state.STATE_BATCH_PROCESSING:
            I_LOG.info("[STATE_MACHINE]", "Entering BATCH_PROCESSING state")
            try:
                
                data_to_upload, data_to_save = state.prepare_data_for_upload()
                if data_to_upload:
                    client = state.SimpleSSLClient()
                    upload_response = state.upload_data(client, data_to_upload)
                    if upload_response is True:
                        I_LOG.info("[NETWORK_UPLOAD]", "Data upload to network completed successfully.")
                        current_state = state.STATE_DATA_ACQUISITION
                        
                        reset_retry_count()
                    else:
                        I_LOG.error("[NETWORK_UPLOAD]", "Network upload failed, backing up to SD card.")
                        current_state = state.STATE_SD_CARD_BACKUP  # Transition to SD card backup state
                    state.reset_upload_in_progress()

                    data_to_upload.clear()
                else:
                    I_LOG.info("[BATCH_PROCESSING]", "Queue has not been filled.")
                    current_state = state.STATE_DATA_ACQUISITION
                feed_watchdog(None)
            except Exception as e:
                I_LOG.error("[BATCH_PROCESSING]", "Error in batch processing: {}".format(e))
                failed_state = current_state  
                current_state = state.STATE_RETRY  

        elif current_state == state.STATE_SD_CARD_BACKUP:
            I_LOG.info("[STATE_MACHINE]", "Entering SD_CARD_BACKUP state")
            try:
                
                state.save_data_to_sd_card(data_to_save)
                I_LOG.info("[SD_CARD_BACKUP]", "Data backup to SD card completed.")
                
                network_timer.start(period=1800000, mode=network_timer.PERIODIC, callback=check_network_and_reset)
                
                
                current_state = state.STATE_DATA_ACQUISITION  # Return to data acquisition
                feed_watchdog(None)
            except Exception as e:
                I_LOG.error("[SD_CARD_BACKUP]", "Error in SD card backup: {}".format(e))
                failed_state = current_state  
                current_state = state.STATE_RETRY

        elif current_state == state.STATE_SD_CARD_UPLOAD:
            I_LOG.info("[STATE_MACHINE]", "Entering SD_CARD_UPLOAD state")
            try:
                feed_watchdog(None)
                ret = state.sd_ftp_send(feed_watchdog)
                if ret is True:
                    I_LOG.info("[SD_CARD_UPLOAD]", "Data upload from SD card to FTP Server completed.")
                    sd_upload_fail_count = 0
                    sd_upload_flag = False
                if ret is False:
                    I_LOG.info("[SD_CARD_UPLOAD]", "Data upload from SD card to FTP Server failed.")
                    sd_upload_fail_count+=1
                    sd_upload_flag = False
                
                current_state = state.STATE_DATA_ACQUISITION  # Return to data acquisition
                feed_watchdog(None)
            except Exception as e:
                I_LOG.error("[SD_CARD_BACKUP]", "Error in SD card upload: {}".format(e))
                failed_state = current_state  
                current_state = state.STATE_RETRY

        elif current_state == state.STATE_OTA_CHECK:
            I_LOG.info("[STATE_MACHINE]", "Entering OTA_CHECK state")
            try:
                state.check_for_ota_upgrade()
                feed_watchdog(None)
                current_state = state.STATE_DATA_ACQUISITION
            except Exception as e:
                I_LOG.error("[OTA_CHECK]", "Error in OTA check: {}".format(e))
                failed_state = current_state  
                current_state = state.STATE_RETRY  

        elif current_state == state.STATE_RETRY:
            I_LOG.info("[STATE_MACHINE]", "Entering RETRY state")
            increment_retry_count()
            feed_watchdog(None)
            current_state = failed_state  
            utime.sleep(2)  # Small delay before retry

        elif current_state == state.STATE_IDLE:
            I_LOG.info("[STATE_MACHINE]", "Entering IDLE state")
            utime.sleep(5)
            feed_watchdog(None)
            current_state = state.STATE_DATA_ACQUISITION

        else:
            I_LOG.error("[STATE_MACHINE]", "Invalid state")
            current_state = state.STATE_IDLE

def main():
    print("[Main] Starting state machine")
    _thread.start_new_thread(state_machine, ())  
    #state_machine()
    

if __name__ == "__main__":
    main()
    print("[Main] Setting up watchdog feeding timer")
    _thread.start_new_thread(state.data_fetch, ())  
    

    # Watchdog feeding timer
    while True:
        utime.sleep(1)

