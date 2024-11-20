import net
import log
import checkNet
import usr.flags as flags
from usr.SIM import check, get_sim_details
import usr.logging as I_LOG


def check_sgnl_str():
    netw_signal_str = net.csqQueryPoll()  # Add exit functions if necessary
    if netw_signal_str in range(6):
        I_LOG.error("[NETWORK_SIGNAL]", "Signal Strength : [{}] : too Low...!".format(netw_signal_str))
        return -1
    elif netw_signal_str in range(6, 11):
        I_LOG.info("[NETWORK_SIGNAL]", "Signal Strength : [{}] : Low...!".format(netw_signal_str))
        return 1
    elif netw_signal_str in range(11, 21):
        I_LOG.info("[NETWORK_SIGNAL]", "Signal Strength : [{}] : Medium...!".format(netw_signal_str))
        return 1
    elif netw_signal_str in range(21, 32):
        I_LOG.info("[NETWORK_SIGNAL]", "Signal Strength : [{}] : High...!".format(netw_signal_str))
        return 1
    else:
        I_LOG.error("[NETWORK_SIGNAL]", "'Error obtaining signal [ERR CODE : {}]'".format(netw_signal_str))
        return -1

def check_net():
    stage, state = checkNet.waitNetworkReady(10)
    sim_check_ret = check()

    if stage == 1:
        if state == 0:
            I_LOG.error("[NETWORK_CHECK]", "'SIM CARD NOT INSERTED...!'")
            flags.Network_connection_flag = False
            return -1
        elif state != 1:
            I_LOG.error("[NETWORK_CHECK]", "'SIM CARD ERROR [ERR CODE : {}]'".format(state))
            flags.Network_connection_flag = False
            return -1

    elif stage == 2:
        if state == -1:
            I_LOG.error("[NETWORK_CHECK]", "'NETWORK REGISTRATION API FAILED...!'")
            flags.Network_connection_flag = False
            return -1
        elif state == 0 or state == 2:
            I_LOG.error("[NETWORK_CHECK]", "'TIMEOUT : NETWORK REGISTRATION FAILED...! [ERR : {}]'".format(state))
            if sim_check_ret == 1:
                sgnl_check_ret = check_sgnl_str()
                if sgnl_check_ret == -1:
                    I_LOG.error("[NETWORK_CHECK]", "'LOW SIGNAL : NETWORK REGISTRATION FAILED...!'")
                    flags.Network_connection_flag = False
                    return -1
                else:
                    I_LOG.info("[NETWORK_CHECK]", "SIGNAL STRENGTH NORMAL...!")
            else:
                I_LOG.error("[NETWORK_CHECK]", "'SIM CARD ERROR'")
                flags.Network_connection_flag = False
                return -1
        else:
            I_LOG.error("[NETWORK_CHECK]", "'[ERR CODE {}] : NETWORK REGISTRATION FAILED...! '".format(state))
            flags.Network_connection_flag = False
            return -1

    elif stage == 3:
        if state == 0:
            sim_check_ret = check()
            if sim_check_ret != 1:
                I_LOG.error("[NETWORK_CHECK]", "'SIM CARD ERROR'")
                flags.Network_connection_flag = False
                return -1
            else:
                I_LOG.info("[NETWORK_CHECK]", "SIM CARD STATUS NORMAL")
                get_sim_details()
                netw_check_ret = net.getState()
                if netw_check_ret == -1:
                    I_LOG.error("[NETWORK_CHECK]", "Network Registration Failed")
                    flags.Network_connection_flag = False
                    return -1
                else:
                    I_LOG.info("[NETWORK_CHECK]", 'Network Info : {}'.format(netw_check_ret))
                    flags.Network_connection_flag = False
                    return -1
        elif state == 1:
            I_LOG.info("[NETWORK_CHECK]", "NETWORK REGISTRATION SUCCESSFUL....!")
            flags.Network_connection_flag = True
            flags.PDP_netw_conn_re_establish_flag = False
            get_sim_details()
            return 1
