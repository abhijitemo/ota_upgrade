import uos
import utime
from uos import VfsSd
import ql_fs



LOG_FILE_PATH = '/sd/log_files.txt'

def initialize_logging():
    try:
       
        ret = ql_fs.path_exists(LOG_FILE_PATH) 
        if ret is False:
            with open(LOG_FILE_PATH, 'w') as log_file:
                    log_file.write('')
    except Exception as e:
        print("[ERROR] Logging Initialization Failed:", e)

def save_to_sd(data):
    try:
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write('{}\n'.format(data))
    except Exception as e:
        print("[ERROR] Failed to save log:", e)

def log(level, tag, val):
    local_time = utime.localtime()
    log_message = '[{d:02d}-{mo:02d}-{y:04d} {h:02d}:{m:02d}:{s:02d}]: {level}: {tag}: {val}'.format(
        y=local_time[0], mo=local_time[1], d=local_time[2],
        h=local_time[3], m=local_time[4], s=local_time[5],
        level=level, tag=tag, val=val
    )
    print(log_message)
    
    if level in ["WARN", "ERROR"]:
        save_to_sd(log_message)

def info(tag, val):
    log("INFO", tag, val)

def error(tag, val):
    log("ERROR", tag, val)

def warning(tag, val):
    log("WARN", tag, val)


