import sim
import log
from misc import Power
import usr.flags as flags
import usr.logging as I_LOG

flags.SIM_IMSI = None
flags.SIM_ICCID = None

def check() :
        SIM_status = sim.getStatus()
        if SIM_status == 1:
            print("SIM Activation Successful...!")
            return SIM_status
        else:
            print("'[ERR CODE: {}]'".format(SIM_status))
            return SIM_status
        
def get_sim_details():
        flags.SIM_IMSI = sim.getImsi()
        if flags.SIM_IMSI == -1:
            print("'FAILED TO FETCH IMSI..!'")
            return -1
        else :
            print('IMSI : {}'.format(flags.SIM_IMSI))
            
        flags.SIM_ICCID = sim.getIccid()
        if flags.SIM_ICCID == -1:
            print("'FAILED TO FETCH IMSI..!'")
            return -1
        else :
            print('ICCID : {}'.format(flags.SIM_ICCID))
            return 1

