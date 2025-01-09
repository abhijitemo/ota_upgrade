
import usr.flags as flags
from machine import RTC
import utime
from ftplib import FTP
import uos
from machine import Timer
from uos import VfsSd
import usr.flags as flags
import ql_fs
import sim, modem
from usr.GPS import extract_lat_lon, get_gps_data
from usr.Data_Extract import global_datetime_list
import usr.logging as I_LOG
import usr.flags as flag
import gc
import ujson


#timer1 = Timer(Timer.Timer1)

FTP_HOST = flag.FTP_HOST
FTP_PORT = flag.FTP_PORT
FTP_USER = flag.FTP_USER
FTP_PASSWD = flag.FTP_PASSWD
LOCAL_FILENAME = flag.SD_UPLOAD_FILENAME
FTP_DIR_BASE = flag.FTP_DIR_BASE


rtc = RTC()

MAX_QUEUE_SIZE = 10
data_queue_real = []
data_queue_save = []
upload_in_progress = False
data_queue_sd = []
max_queue_size = 10 

def initialize_sd_card():
    try:
        udev = VfsSd("sd_fs")
        uos.mount(udev, "/sd")
        udev.set_det(udev.GPIO30, 0)
        flags.SD_Card_working_status_flag = True
        I_LOG.info("[SD_CARD]", "SD Card Mounted Successfully....!")
        return True
    except Exception as e:
        flags.SD_Card_working_status_flag = False
        I_LOG.error("[SD_CARD]", "Failed to mount SD card")
        return False

# Check SD Card Status
def check_sd_card():
    if flags.SD_Card_working_status_flag:
        I_LOG.info("[SD_CARD]", "SD Card is mounted.")
        return True
    else:
        I_LOG.error("[SD_CARD]", "SD Card is not mounted.")
        return False


def save_to_sd_card(filename, batch_data):
    try:
        I_LOG.info("[SD_CARD]", "Saving BMS data to SD card: {}".format(filename))
        with open(filename, "a+") as f:
            for data in batch_data:
                
                json_string = ujson.dumps(data)
                
                f.write(json_string + "\n")
                I_LOG.info("[SD_CARD]", "Data saved: {}".format(json_string))
            
        I_LOG.info("[SD_CARD]", "BMS data saved to SD card: {}".format(filename))
    except Exception as e:
        I_LOG.error("[SD_CARD]", "Error saving BMS data to SD card: {}".format(e))



def sd_ftp_send():
    bms_id = flag.BMS_ID
    ftp_directory = "{}{}".format(FTP_DIR_BASE, bms_id)
    ftp = None  # Initialize ftp variable for cleanup
    gc.enable()
    try:
        I_LOG.info("[SD_CARD]", "File {} is above 1 MB, preparing to send.".format(LOCAL_FILENAME))

        # Create FTP connection
        ftp = FTP()
        ftp.connect(FTP_HOST, FTP_PORT)
        ftp.login(FTP_USER, FTP_PASSWD)

        # Ensure the BMS_ID directory exists on the FTP server
        try:
            ftp.cwd(ftp_directory)
        except:
            ftp.mkd(ftp_directory)
            ftp.cwd(ftp_directory)

        # Find the next file number for the upload (from bms_data1.txt to bms_data9.txt)
        for i in range(1, 10):
            ftp_filename = "bms_data{}.txt".format(i)
            if ftp_filename not in ftp.nlst():
                break
        else:   
            ftp_filename = "bms_data1.txt"  # Reset to 1 if all 9 files exist

        # Upload the file
        with open(LOCAL_FILENAME, 'rb') as file:
            I_LOG.info("[FTP]", "Storing the sd card file")
            
            res = ftp.storbinary('STOR {}'.format(ftp_filename), file)
            
            I_LOG.info("[FTP]", "FTP upload response: {}".format(res))

        if res.startswith('226'):
            I_LOG.info("[FTP]", "Upload of {} to FTP server {} successful.".format(ftp_filename, FTP_HOST))
            # Clear the local file after a successful upload
            #timer1.stop()
            gc.collect()
            uos.remove(LOCAL_FILENAME)  # Truncate the file content
            I_LOG.info("[SD_CARD]", "Local file {} cleared after upload.".format(LOCAL_FILENAME))
            return True  # Indicate success
        else:
            I_LOG.error("[FTP]", "Upload of {} to FTP server failed.".format(ftp_filename))
            #timer1.stop()
            gc.collect()
            #uos.remove(LOCAL_FILENAME)
            return False  # Indicate failure

    except Exception as e:
        
        if e is '[Errno 103] ECONNABORTED':
            I_LOG.error("[FTP]", "Connection aborted error (Errno 103) during FTP upload.")
            #timer1.stop()
            gc.collect()
            #uos.remove(LOCAL_FILENAME)  # Remove file from SD card if ECONNABORTED occurs
        else:
            I_LOG.error("[FTP]", "Error during FTP file upload: {}".format(e))
            gc.collect()
            #timer1.stop()


        return False  # Indicate failure

    finally:
        # Always close FTP connection if open
        if ftp:
            ftp.quit()
        # Run garbage collection to free memory
        gc.collect()


def sd_extract(sd_data):
    if len(sd_data) > 5:
        data_parts = [value for value in sd_data.split(',') if value]
        result = {
            "IMEI": None,
            "IMSI": None,
            "ICCID": None,
            "Network_operator": '1',  # Assuming this is a constant value
            "Time": None,
            "Date": None,
            "DeviceID": None,
            "Data": {
                "packVoltage": None,
                "packCurrent": None,
                "SOC": None,
                "CellData": None,
                "TemperatureData": None,
                "Faults": None,
                "Latitude": None,
                "Longitude": None,
                "Data_Type": "B",  # Set to "B" for backup data type
            },
        }

        try:
            result["DeviceID"] = data_parts[7]
        except (IndexError, ValueError) as e:
            I_LOG.error("[SD_CARD]", "Failed to extract DeviceID: {}".format(e))

        try:
            result["Data"]["packVoltage"] = int(data_parts[26]) / 100.0
        except (IndexError, ValueError) as e:
            I_LOG.error("[SD_CARD]", "Failed to extract packVoltage: {}".format(e))

        try:
            result["Data"]["packCurrent"] = int(data_parts[27]) / 100.0
        except (IndexError, ValueError) as e:
            I_LOG.error("[SD_CARD]", "Failed to extract packCurrent: {}".format(e))

        try:
            result["Data"]["SOC"] = int(data_parts[28])
        except (IndexError, ValueError) as e:
            I_LOG.error("[SD_CARD]", "Failed to extract SOC: {}".format(e))

        try:
            result["Data"]["CellData"] = [int(value) / 1000.0 for value in data_parts[8:22]]
        except (IndexError, ValueError) as e:
            I_LOG.error("[SD_CARD]", "Failed to extract CellData: {}".format(e))

        try:
            result["Data"]["TemperatureData"] = [int(value) for value in data_parts[22:26]]
        except (IndexError, ValueError) as e:
            I_LOG.error("[SD_CARD]", "Failed to extract TemperatureData: {}".format(e))

        try:
            result["Data"]["Faults"] = ([int(value) for value in data_parts[29:35] if ('N' not in value and 'E' not in value)])
        except (IndexError, ValueError) as e:
            I_LOG.error("[SD_CARD]", "Failed to extract Faults: {}".format(e))

        try:
            result["Data"]["Latitude"] = str(data_parts[-2]) if data_parts[-2] and ('N' in data_parts[-2] or 'S' in data_parts[-2] or 'Inv' in data_parts[-2]) else None
            result["Data"]["Longitude"] = str(data_parts[-1]) if data_parts[-1] and ('E' in data_parts[-1] or 'W' in data_parts[-1] or 'Inv' in data_parts[-1]) else None
        except (IndexError, ValueError) as e:
            I_LOG.error("[SD_CARD]", "Failed to extract GPS data: {}".format(e))
        try:
            year = int(data_parts[0])
            month = int(data_parts[1])
            day = int(data_parts[2])
            hour = int(data_parts[4])
            minute = int(data_parts[5])
            second = int(data_parts[6])
            date_string = "{:04d}-{:02d}-{:02d}".format(year, month, day)
            time_string = "{}:{}:{}".format(hour, minute, second)
            result["Time"] = time_string
            result["Date"] = date_string
        except (IndexError, ValueError) as e:
            I_LOG.error("[SD_CARD]", "Failed to extract date/time: {}".format(e))

        try:
            result["IMSI"] = flags.SIM_IMSI
        except Exception as e:
            I_LOG.error("[SD_CARD]", "Failed to extract IMSI: {}".format(e))

        try:
            result["ICCID"] = flags.SIM_ICCID
        except Exception as e:
            I_LOG.error("[SD_CARD]", "Failed to extract ICCID: {}".format(e))

        try:
            result["IMEI"] = flags.DEV_IMEI
        except Exception as e:
            I_LOG.error("[SD_CARD]", "Failed to extract IMEI: {}".format(e))

        return result
    return None

