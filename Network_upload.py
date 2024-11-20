'''
*  **********************************************
*
*   Project Name    :   IoT Model
*   Company Name    :   Emo Energy
*   File Name       :   Network_upload.py
*   Description     :   Uploads the extracted data to the network
*   Author          :   Abhijit Narayan S
*   Created on      :   01-04-2024   
*      
*   © All rights reserved @EMO.Energy [www.emoenergy.in]
*   
*   *********************************************
'''


import usr.flags as flags
import usocket as socket
import ussl
from ujson import dumps
from usr.Data_Extract import global_datetime_list
import usr.logging as I_LOG
# Define server parameters

SERVER_ADDRESS = flags.SERVER_ADDRESS
SERVER_PORT = flags.SERVER_PORT
HANDLER_ADDRESS = flags.HANDLER_ADDRESS

class SimpleSSLClient:
    def __init__(self):
        self.server_address = SERVER_ADDRESS
        self.server_port = SERVER_PORT
        self.handler_address = HANDLER_ADDRESS

    def establish_ssl_connection(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            addr = socket.getaddrinfo(self.server_address, self.server_port)[0][-1]
            sock.connect(addr)
            ssl_sock = ussl.wrap_socket(sock, server_hostname=self.server_address)
            I_LOG.info("[NETWORK_UPLOAD]", "Successfully established SSL connection to {}:{}".format(self.server_address, self.server_port))
            return ssl_sock
        except Exception as e:
            I_LOG.error("[NETWORK_UPLOAD]", "Failed to establish SSL connection: {}".format(e))
            return None

    def send_data_over_ssl(self, HTTP_data):
        ssl_sock = self.establish_ssl_connection()
        if ssl_sock is None:
            return False
        
        try:
            request_template = (
                "POST /{handler} HTTP/1.1\r\n"
                "Host: {host}\r\n"
                "Content-Type: application/json\r\n"
                "Content-Length: {length}\r\n"
                "\r\n"
                "{data}"
            )

            # Combine all data entries into one list
            data_list = []
            for individual_data in HTTP_data:
                json_data = {
                    "IMEI": individual_data['IMEI'],
                    "IMSI": individual_data['IMSI'],
                    "ICCID": individual_data['ICCID'],
                    "Network_operator": individual_data['Network_operator'],
                    "Time": individual_data['Time'],
                    "Date": individual_data['Date'],
                    "DeviceID": individual_data['DeviceID'],
                    "Data": {
                        "packVoltage": individual_data['Data']['packVoltage'],
                        "packCurrent": individual_data['Data']['packCurrent'],
                        "SOC": individual_data['Data']['SOC'],
                        "CellData": individual_data['Data']['CellData'].copy(),
                        "TemperatureData": individual_data['Data']['TemperatureData'].copy(),
                        "Faults": individual_data['Data']['Faults'],
                        "Latitude": individual_data['Data']['Latitude'],
                        "Longitude": individual_data['Data']['Longitude'],
                        "Data_Type": individual_data['Data']['Data_Type'],
                    }
                }
                data_list.append(json_data)

            json_data_string = dumps(data_list)
            request = request_template.format(
                handler=self.handler_address,
                host=self.server_address,
                length=len(json_data_string),
                data=json_data_string
            )

            I_LOG.info("[NETWORK_UPLOAD]", "Combined Request: {}".format(request))
            ssl_sock.write(request.encode("utf-8"))

            # Read and print the server's response
            response = ssl_sock.read(32).decode("utf-8")
            I_LOG.info("[NETWORK_UPLOAD]", "Server response: {}".format(response))
            response_list = response.split("\r\n")
            response_list = response_list[0].split(' ')
            status_code = int(response_list[1])

            if status_code == 200:
                I_LOG.info("[NETWORK_UPLOAD]", "Successfully sent to network")
                global_datetime_list.clear()
                return True
            else:
                I_LOG.error("[NETWORK_UPLOAD]", "Failed to send to network, status code: {}".format(status_code))
                return False
        except Exception as e:
            I_LOG.error("[NETWORK_UPLOAD]", "Failed to send data over SSL: {}".format(e))
            return False
        finally:
            ssl_sock.close()

        return True
