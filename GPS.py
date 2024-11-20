'''
*  **********************************************
*
*   Project Name    :   IoT Model
*   Company Name    :   Emo Energy
*   File Name       :   gps.py
*   Description     :   Extracts the useful data from the GPS
*   Author          :   Abhijit Narayan S
*   Created on      :   01-04-2024   
*      
*   © All rights reserved @EMO.Energy [www.emoenergy.in]
*   
*   *********************************************
'''

from machine import RTC
import usr.flags as flags
import utime
import ql_fs
import usr.logging as I_LOG
from gnss import GnssGetData
import quecgnss

# Constants
UART_PORT = 1
UART_BAUDRATE = 9600

gnss = GnssGetData(1, 9600, 8, 0, 1, 0)
rtc = RTC()
last_latitude = None
last_longitude = None
uart1 = flags.GPS_UART

# Initialize internal GNSS
def init_internal_gps():
    ret = quecgnss.init()
    if ret == 0:
        I_LOG.info("[GPS]", "Internal GNSS initialized successfully.")
    else:
        I_LOG.error("[GPS]", "Failed to initialize internal GNSS.")
    return ret == 0

def read_internal_gps():
    gps_data = quecgnss.read(256)
    string_data = gps_data[1].decode() if gps_data[1] else ""
    parts = string_data.split('\r\n')

    for part in parts:
        if part.startswith('$GNRMC'):
            return part.split(',')
    return None

def callback(para):
    if para[0] == 0:
        uartReadgp(para[2])

def uartReadgp():
    
    try:
        msg = uart1.read(256)
        utf8_msg = msg.decode()
        #I_LOG.info("[GPS_UART]", "Received GPS message: {}".format(utf8_msg.strip()))
        return utf8_msg
    except Exception as e:
        I_LOG.error("[GPS_UART]", "Failed to read GPS message: {}".format(e))
        return None

def get_gps_data():
    """Retrieve GPS data from external source and log the results."""
    try:
        gps_data = uartReadgp()
        if gps_data:
            #I_LOG.info("[GPS_UART]", "GPS Data received: {}".format(gps_data.strip()))
            return gps_data
        else:
            I_LOG.warning("[GPS_UART]", "GPS Data not received")
            return ""
    except Exception as e:
        I_LOG.error("[GPS_UART]", "Error while getting GPS data: {}".format(e))
        return ""

def extract_lat_lon(gps_data):
    """Extract latitude and longitude from GPS data, giving priority to external."""
    global last_latitude, last_longitude

    
    #raw = gnss.getLocation()
    external_lat, external_lon = None, None
    global last_latitude, last_longitude
    try:
        lines = gps_data.split('\n')
        for line in lines:
            if line.startswith('$GPRMC') and line.endswith('\r') and line.count('$GPRMC') == 1:
                data = line.split(',')
                if len(data) >= 10:
                    external_lat = data[3] + ' ' + data[4]
                    external_lon = data[5] + ' ' + data[6]
                    if 'V' in data:
                        I_LOG.warning("[GPS_UART]", "Invalid GPS data (status is 'V')")
                        print("Invalid GPS data (status is 'V')")
                        external_lon = 'invalid'
                        external_lat = 'invalid'
                        return 'invalid', 'invalid'

                    if ('N' in external_lat or 'S' in external_lat) and ('E' in external_lon or 'W' in external_lon):
                        if external_lat != last_latitude or external_lon != last_longitude:
                            last_latitude = external_lat
                            last_longitude = external_lon
                            return external_lat, external_lon


                    if '$' in external_lat or '$' in external_lon:
                        return last_latitude, last_longitude
                    else:
                        return last_latitude, last_longitude
        I_LOG.warning("[GPS_UART]", "No valid GPS data found")
        return last_latitude, last_longitude
    except Exception as e:
        I_LOG.error("[GPS_UART]", "Error while extracting latitude and longitude: {}".format(e))
        return last_latitude, last_longitude

    # else:
        
    #     latlon = list(raw)
    #     external_lat = "{} {}".format(latlon[2], latlon[3])
    #     external_lon = "{} {}".format(latlon[0], latlon[1])
    #     I_LOG.info("[GPS]", "External GPS data: lat={}, lon={}".format(external_lat, external_lon))

    #internal_data = read_internal_gps()
    #internal_lat, internal_lon = None, None
    
    # if internal_data:
    #     if 'A' in internal_data[2]:  # Valid status
    #         internal_lat = '{} {}'.format(internal_data[3], internal_data[4])
    #         internal_lon = '{} {}'.format(internal_data[5], internal_data[6])
    #         I_LOG.info("[GPS_INTER]", "Internal GPS data: lat={}, lon={}".format(internal_lat, internal_lon))
    #     else:
    #         internal_lat = 'invalid'
    #         internal_lon = 'invalid'
    #         I_LOG.warning("[GPS_INTER]", "Invalid internal GPS data (contains 'V').")

    # Determine which data to use
    # if external_lat and external_lon:  # Use external if available and valid
    #     I_LOG.info("[GPS_UART]", "Used External GPS data: lat={}, lon={}".format(external_lat, external_lon))
    #     return external_lat, external_lon
    
    # elif internal_lat and internal_lon:  # Fallback to internal if external is not valid
    #     I_LOG.info("[GPS_UART]", "Used Internal GPS data: lat={}, lon={}".format(internal_lat, internal_lon))
    #     return internal_lat, internal_lon
    # else:  
    #     I_LOG.warning("[GPS]", "No valid GPS data available.")
    #     return 'invalid', 'invalid'


