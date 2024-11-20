import utime
import sms
import app_fota
from misc import Power
import usr.logging as I_LOG
import ql_fs
import usr.flags as flag
import usr.BMS_data as bms
import uos

MODULE_FILES = {
    1: 'BMS_data.py',
    2: 'Data_Extract.py',
    3: 'flags.py',
    4: 'GPS.py',
    5: 'hardware.py',
    6: 'iot_sm.py',
    7: 'logging.py',
    8: 'main_.py',
    9: 'network.py',
    10: 'Network_upload.py',
    11: 'ota_upgrade.py',
    12: 'SD_CARD.py',
    13: 'SIM.py'
}

def sms_callback(args):
    """Callback function that triggers on receiving an SMS."""
    I_LOG.info("[OTA_UPGRADE]", "SMS callback triggered with args: {}".format(args))
    ind_flag = args[1]
    if ind_flag >= 0:  # New message indicator flags
        I_LOG.info("[OTA_UPGRADE]", "New SMS received, checking for upgrade/reset commands")
        ota_upgrade_check()

sms.setCallback(sms_callback)

def ota_upgrade_check():
    """Check for an upgrade or reset command in SMS and perform the action."""
    I_LOG.info("[OTA_UPGRADE]", "Checking for SMS Command..")
    phone_number = None
    try:
        if sms.getMsgNums() > 0:
            msg_content = sms.searchTextMsg(0)[1]
            phone_number = sms.searchTextMsg(0)[0]
            module_to_upgrade = None

            if msg_content.strip().upper().startswith('AT+RESET'):
                I_LOG.info("[OTA_UPGRADE]", "Received reset command")
                sms.deleteMsg(1, 4)
                message = 'AT+RESET || DONE'
                txtmsg = sms.sendTextMsg(phone_number, message, 'GSM')
                if txtmsg == 1:
                    I_LOG.info("[OTA_UPGRADE]", "Sent acknowledgment message for reset command")
                else:
                    I_LOG.error("[OTA_UPGRADE]", "Failed to send acknowledgment message for reset command")
                utime.sleep(2)
                Power.powerRestart()  # Reset the device

            
            if msg_content.strip().upper().startswith('AT+SDDELETE'):
                I_LOG.info("[OTA_UPGRADE]", "Received Sd delete command")
                sms.deleteMsg(1, 4)
                message = 'AT+SDDELETE || DONE'
                
                txtmsg = sms.sendTextMsg(phone_number, message, 'GSM')
                uos.remove('/sd/bms_data.txt')
                if txtmsg == 1:
                    I_LOG.info("[OTA_UPGRADE]", "Sent acknowledgment message for sd delete command")
                else:
                    I_LOG.error("[OTA_UPGRADE]", "Failed to send acknowledgment message for sd delete command")
                utime.sleep(2)
                Power.powerRestart()  # Reset the device

            elif msg_content.strip().upper().startswith('AT+BMSINFO'):
                I_LOG.info("[OTA_UPGRADE]", "Received BMSINFO command")
                sms.deleteMsg(1, 4)
                packvol = flag.Pack_Voltage
                faults = flag.faults
                lati = flag.lat
                longi = flag.lon
                message = 'AT+BMSINFO || {}, {}, {}, {}'.format(packvol,faults,lati,longi)
                txtmsg = sms.sendTextMsg(phone_number, message, 'GSM')
                if txtmsg == 1:
                    I_LOG.info("[OTA_UPGRADE]", "Sent acknowledgment message for packvoltage command")
                else:
                    I_LOG.error("[OTA_UPGRADE]", "Failed to send acknowledgment message for packvoltage command")
                utime.sleep(1)
            
            elif msg_content.strip().upper().startswith('AT+BLOCK='):
                I_LOG.info("[OTA_UPGRADE]", "Received BMS_BLOCK command")
                sms.deleteMsg(1, 4)
                module = msg_content.split('=')[1].strip().upper()
                msg = "AT+BLOCK={}\r\n".format(module)
                bms.uartWrite(msg)
                response = bms.uartRead()
                if response.strip().upper().startswith('OK'):
                    message = 'AT+BLOCK={} || DONE'.format(module)
                if response.strip().upper().startswith('FAIL'):
                    message = 'AT+BLOCK={} || FAIL'.format(module)
                
                txtmsg = sms.sendTextMsg(phone_number, message, 'GSM')
                if txtmsg == 1:
                    I_LOG.info("[OTA_UPGRADE]", "Sent acknowledgment message for packvoltage command")
                else:
                    I_LOG.error("[OTA_UPGRADE]", "Failed to send acknowledgment message for packvoltage command")
                utime.sleep(1)

            elif msg_content.strip().upper().startswith('AT+BMSRESET'):
                I_LOG.info("[OTA_UPGRADE]", "Received BMS_RESET command")
                sms.deleteMsg(1, 4)
                msg = "AT+BMSRESET\r\n"
                bms.uartWrite(msg)
                response = bms.uartRead()
                if response.strip().upper().startswith('OK'):
                    message = 'AT+BMSRESET || DONE'
                if response.strip().upper().startswith('FAIL'):
                    message = 'AT+BMSRESET || FAIL'
                
                txtmsg = sms.sendTextMsg(phone_number, message, 'GSM')
                if txtmsg == 1:
                    I_LOG.info("[OTA_UPGRADE]", "Sent acknowledgment message for packvoltage command")
                else:
                    I_LOG.error("[OTA_UPGRADE]", "Failed to send acknowledgment message for packvoltage command")
                utime.sleep(1)

            elif msg_content.strip().upper().startswith('AT+UPGRADE='):
                sms.deleteMsg(1, 4)
                module = msg_content.split('=')[1].strip().upper()
                if module == 'ALL':
                    I_LOG.info("[OTA_UPGRADE]", "Received upgrade command for all modules.")
                    module_to_upgrade = 'ALL'
                elif module.isdigit() and int(module) in MODULE_FILES:
                    module_to_upgrade = int(module)
                    I_LOG.info("[OTA_UPGRADE]", "Received upgrade command for module {} ({})".format(module_to_upgrade, MODULE_FILES[module_to_upgrade]))
                else:
                    I_LOG.error("[OTA_UPGRADE]", "Invalid module in upgrade command: {}".format(module))
                    message = 'AT+UPGRADE=INVALID COMMAND -- {}'.format(module)
                    sms.sendTextMsg(phone_number, message, 'GSM')

                if module_to_upgrade:
                    try:
                        result = run_fota(module_to_upgrade)
                        I_LOG.info("[OTA_UPGRADE]", "FOTA UPGRADE OF FILES RETURNED: {}".format(result))
                        message = 'AT+UPGRADE={} || {}'.format(
                                'ALL' if module_to_upgrade == 'ALL' else MODULE_FILES[module_to_upgrade],
                                'DONE' if result is None or result is 0 else 'FAILED'
                            )
                        if result is None or result is 0:
                            txtmsg = sms.sendTextMsg(phone_number, message, 'GSM')
                            if txtmsg == 1:
                                I_LOG.info("[OTA_UPGRADE]", "Sent acknowledgment message to source number")
                            else:
                                I_LOG.error("[OTA_UPGRADE]", "Failed to send acknowledgment message to source number")
                                Power.powerRestart()
                        
                    except Exception as e:
                        I_LOG.error("[OTA_UPGRADE]", "Exception occurred during upgrade: {}".format(e))
                        error_message = 'AT+UPGRADE=FAILED -- {}'.format(e)
                        sms.sendTextMsg(phone_number, error_message, 'GSM')
    except Exception as e:
        I_LOG.error("[OTA_UPGRADE]", "Exception occurred during SMS handling: {}".format(e))
        if phone_number:
            error_message = "AT+ERROR = Exception: {}".format(e)
            sms.sendTextMsg(phone_number, error_message, 'GSM')
        else:
            I_LOG.error("[OTA_UPGRADE]", "Failed to retrieve phone number to send error message")

def run_fota(module=None):
    """Run the OTA update process for the specified module."""
    base_url = "https://raw.githubusercontent.com/abhijitemo/ota_upgrade/master/"
    fota = app_fota.new()
    try:
        if module == 'ALL':
            download_list = [{'url': '{}{}'.format(base_url, filename), 'file_name': '/usr/{}'.format(filename)} for filename in MODULE_FILES.values()]
            upgrade = fota.bulk_download(download_list)
            fota.set_update_flag()
            I_LOG.info("[OTA_UPGRADE]", "Upgrading all modules")
            utime.sleep(2)
            return upgrade 
        elif isinstance(module, int) and module in MODULE_FILES:
            file_name = '/usr/{}'.format(MODULE_FILES[module])
            url = "{}{}".format(base_url, MODULE_FILES[module])
            upgrade = fota.download(url, file_name)
            fota.set_update_flag()
            I_LOG.info("[OTA_UPGRADE]", "Upgrading module: {}".format(MODULE_FILES[module]))
            utime.sleep(2)
            return upgrade 
        else:
            raise ValueError("Invalid module name: {}".format(module))
    except Exception as e:
        I_LOG.error("[OTA_UPGRADE]", "Exception during FOTA process: {}".format(e))
        return False
