from flask import Flask, request
import json
import signal
import sys
import time
import paho.mqtt.client as paho
import re
import socket
import config
import subprocess
import uuid

from typing import Dict, Union, Optional, Literal
# from homeassistant.components.mqtt.sensor import DEVICE_CLASSES, STATE_CLASSES

app = Flask(__name__)

# Pfad zur Logdatei
LOG_FILE = '/app/logdir/backup_reports.log'

# get hostname. Because of dynamic container hostnames,
# have a look into config
if "hostname" in dir(config):
    hostname = getattr(config, "hostname")
else:
    hostname = re.sub(r'[^a-zA-Z0-9_-]', '_', socket.gethostname())



def signal_handler(signum: int = None, frame = None):
    # We get a call to this handler on each POST request 
    if signum == None:
        print('Oops: We have been called via POST request. Why the hell?')
        return handle_backup_report()
    
    signame = signal.Signals(signum).name
    print(f'Signal handler called with signal {signame} ({signum})')
    print(f'{frame:}', flush=True)

    if signum == signal.SIGTERM or signum == signal.SIGINT:
        print(f'Got Signal {signame}, terminating normally.')
        sys.exit(0)
 

def set_standard_signal_handler():
    signal.signal(signal.SIGALRM, signal_handler)
    signal.signal(signal.SIGHUP, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGUSR1, signal_handler)
    signal.signal(signal.SIGUSR2, signal_handler)
    signal.signal(signal.SIGCONT, signal_handler)


# Code is copied and adopted from https://github.com/frickler24/rpi-mqtt-monitor
def create_mqtt_client() -> paho.Client:

    def on_log(client, userdata, level, buf):
        if level == paho.MQTT_LOG_ERR:
            print("MQTT error: ", buf)

    def on_connect(client, userdata, flags, rc):
        if rc != 0:
            print("Error: Unable to connect to MQTT broker, return code:", rc)
    
    client = paho.Client(client_id="backup_status-" + hostname + str(int(time.time())))
    client.username_pw_set(config.mqtt_user, config.mqtt_password)
    client.on_log = on_log
    client.on_connect = on_connect

    try:
        client.connect(config.mqtt_host, int(config.mqtt_port))
    except Exception as e:
        print("Error connecting to MQTT broker:", e)
        return None

    return client


# Code is copied and adopted from https://github.com/frickler24/rpi-mqtt-monitor
def get_os() -> str:
    full_cmd = 'cat /etc/os-release | grep -i pretty_name'
    pretty_name: str = subprocess.Popen(full_cmd, 
                                   shell=True, 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE).communicate()[0].decode("utf-8")
    try:
        pretty_name = pretty_name.split('=')[1].replace('"', '').replace('\n', '')
    except Exception:
        pretty_name = 'Unknown'
        
    return pretty_name


# Code is copied and adopted from https://github.com/frickler24/rpi-mqtt-monitor
def check_model_name() -> str:
   full_cmd:str = "cat /sys/firmware/devicetree/base/model"
   model_name: str = subprocess.Popen(full_cmd, 
                                 shell=True, 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE).communicate()[0].decode("utf-8")
   if model_name == '':
        full_cmd = "cat /proc/cpuinfo  | grep 'name'| uniq"
        model_name = subprocess.Popen(full_cmd, 
                                      shell=True, 
                                      stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE).communicate()[0].decode("utf-8")
        try:
            model_name = model_name.split(':')[1].replace('\n', '')
        except Exception:
            model_name = 'Unknown'

   return model_name


# Code is copied and adopted from https://github.com/frickler24/rpi-mqtt-monitor
def get_manufacturer() -> str:
    try:
        full_cmd: str = "cat /proc/cpuinfo  | grep 'vendor'| uniq"
        pretty_name: str = subprocess.Popen(full_cmd, 
                                        shell=True, 
                                        stdout=subprocess.PIPE, 
                                        stderr=subprocess.PIPE).communicate()[0].decode("utf-8")
        pretty_name = pretty_name.split(':')[1].replace('\n', '')
    except Exception:
        pretty_name = 'Unknown'

    return pretty_name


def get_network_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


def get_mac_address():
    mac_num = uuid.getnode()
    mac = '-'.join((('%012X' % mac_num)[i:i+2] for i in range(0, 12, 2)))
    return mac


# Code is copied and adopted from https://github.com/frickler24/rpi-mqtt-monitor
def config_json(what_config, device="0"): 
    model_name = check_model_name()
    manufacturer = get_manufacturer()
    os = get_os()
    data = {
        "state_topic": "",
        "icon": "",
        "name": "",
        "unique_id": "",

        "device": {
            "identifiers": [hostname],
            "manufacturer": 'github.com/frickler24',
            "model": 'backup_status ' + config.version,
            "name": hostname,
            "sw_version": os,
            "hw_version": model_name + " by " + manufacturer + " IP:" + get_network_ip(),
            "configuration_url": "https://github.com/frickler24/backup-status",
            "connections": [["mac", get_mac_address()]]
        }
    }

    data["state_topic"] = config.mqtt_topic_prefix + "/" + hostname + "/" + what_config
    data["unique_id"] = hostname + "_" + what_config
    if what_config == "computer":
        data["icon"] = "mdi:speedometer"
        data["name"] = "Computer"
    elif what_config == "directory":
        data["icon"] = "hass:thermometer"
        data["name"] = "Directory"
    elif what_config == "end_time":
        data["icon"] = "mdi:calendar"
        data["name"] = "Uptime"
        data["value_template"] = "{{ as_datetime(value) }}"
        data["device_class"] = "timestamp"
    elif what_config == "new_chunk_size":
        data["icon"] = "mdi:harddisk"
        data["name"] = "new chunk size"
        data["unit_of_measurement"] = "B"
        data["device_class"] = "data_size"
        data["state_class"] = "measurement"
    elif what_config == "new_chunks":
        data["icon"] = "mdi:harddisk"
        data["name"] = "New Chunks"
        data["unit_of_measurement"] = ""
        data["state_class"] = "measurement"
    elif what_config == "new_file_chunk_size":
        data["icon"] = "mdi:harddisk"
        data["name"] = "New File Chunk Size"
        data["unit_of_measurement"] = "B"
        data["state_class"] = "measurement"
    elif what_config == "new_file_chunks":
        data["icon"] = "mdi:speedometer"
        data["name"] = "New File Chunks"
        data["unit_of_measurement"] = ""
        data["device_class"] = "number"
        data["state_class"] = "measurement"
    elif what_config == "new_file_size":
        data["icon"] = "mdi:harddisk"
        data["name"] = "New File Size"
        data["unit_of_measurement"] = "B"
        data["state_class"] = "measurement"
    elif what_config == "new_files":
        data["icon"] = "mdi:harddisk"
        data["name"] = "New Files"
        data["unit_of_measurement"] = ""
        data["state_class"] = "measurement"

    elif what_config == "uptime":
        data["icon"] = "mdi:calendar"
        data["name"] = "Uptime"
        data["value_template"] = "{{ as_datetime(value) }}"
        data["device_class"] = "timestamp"
    elif what_config == "uptime_seconds":
        data["icon"] = "mdi:timer-outline"
        data["name"] = "Uptime"
        data["unit_of_measurement"] = "s"
        data["device_class"] = "duration"
        data["state_class"] = "total_increasing"
    elif what_config == "wifi_signal":
        data["icon"] = "mdi:wifi"
        data["name"] = "Wifi Signal"
        data["unit_of_measurement"] = "%"
        data["state_class"] = "measurement"
        data["device_class"] = "signal_strength"
    elif what_config == "wifi_signal_dbm":
        data["icon"] = "mdi:wifi"
        data["name"] = "Wifi Signal"
        data["unit_of_measurement"] = "dBm"
        data["device_class"] = "signal_strength"
        data["state_class"] = "measurement"
    elif what_config == "rpi5_fan_speed":
        data["icon"] = "mdi:fan"
        data["name"] = "Fan Speed"
        data["unit_of_measurement"] = "RPM"
        data["state_class"] = "measurement"
    elif what_config == "status":
        data["icon"] = "mdi:lan-connect"
        data["name"] = "Status"
        data["value_template"] = "{{ 'online' if value == '1' else 'offline' }}"
    elif what_config == "git_update":
        data["icon"] = "mdi:git"
        data["name"] = "RPi MQTT Monitor"
        data["title"] = "Device Update"
        data["device_class"] = "update"
        data["state_class"] = "measurement"
        data["value_template"] = "{{ 'ON' if value_json.installed_ver != value_json.new_ver else 'OFF' }}"
    elif what_config == "update":
        version = update.check_git_version_remote(script_dir)
        data["icon"] = "mdi:update"
        data["name"] = "RPi MQTT Monitor"
        data["title"] = "New Version"
        data["state_topic"] = config.mqtt_topic_prefix + "/" + hostname + "/" + "git_update"
        data["value_template"] = "{{ {'installed_version': value_json.installed_ver, 'latest_version': value_json.new_ver } | to_json }}"
        data["device_class"] = "firmware"
        data["command_topic"] = config.mqtt_discovery_prefix + "/update/" + hostname + "/command"
        data["payload_install"] = "install"
        data['release_url'] = "https://github.com/hjelev/rpi-mqtt-monitor/releases/tag/" + version
        data['entity_picture'] = "https://raw.githubusercontent.com/hjelev/rpi-mqtt-monitor/refs/heads/master/images/update_icon.png"
        data['release_summary'] = get_release_notes(version)
    elif what_config == "restart_button":
        data["icon"] = "mdi:restart"
        data["name"] = "System Restart"
        data["command_topic"] = config.mqtt_discovery_prefix + "/update/" + hostname + "/command"
        data["payload_press"] = "restart"
        data["device_class"] = "restart"
    elif what_config == "shutdown_button":
        data["icon"] = "mdi:power"
        data["name"] = "System Shutdown"
        data["command_topic"] = config.mqtt_discovery_prefix + "/update/" + hostname + "/command"
        data["payload_press"] = "shutdown"
        data["device_class"] = "restart"
    elif what_config == "display_on":
        data["icon"] = "mdi:monitor"
        data["name"] = "Monitor ON"
        data["command_topic"] = config.mqtt_discovery_prefix + "/update/" + hostname + "/command"
        data["payload_press"] = "display_on"
        data["device_class"] = "restart"
    elif what_config == "display_off":
        data["icon"] = "mdi:monitor"
        data["name"] = "Monitor OFF"
        data["command_topic"] = config.mqtt_discovery_prefix + "/update/" + hostname + "/command"
        data["payload_press"] = "display_off"
        data["device_class"] = "restart"
    elif what_config == device + "_temp":
        data["icon"] = "hass:thermometer"
        data["name"] = device + " Temperature"
        data["unit_of_measurement"] = "°C"
        data["device_class"] = "temperature"
        data["state_class"] = "measurement"
    elif what_config == "rpi_power_status":
        data["icon"] = "mdi:flash"
        data["name"] = "RPi Power Status"  
    elif what_config == "apt_updates":
        data["icon"] = "mdi:update"
        data["name"] = "APT Updates"
    elif what_config == "ds18b20_status":
        data["icon"] = "hass:thermometer"
        data["name"] = device + " Temperature"
        data["unit_of_measurement"] = "°C"
        data["device_class"] = "temperature"
        data["state_class"] = "measurement"
        # we define again the state topic in order to get a unique state topic if we have two sensors of the same type
        data["state_topic"] = config.mqtt_topic_prefix + "/" + hostname + "/" + what_config + "_" + device
        data["unique_id"] = hostname + "_" + what_config + "_" + device
    elif what_config == "sht21_temp_status":
        data["icon"] = "hass:thermometer"
        data["name"] = device + " Temperature"
        data["unit_of_measurement"] = "°C"
        data["device_class"] = "temperature"
        data["state_class"] = "measurement"
        # we define again the state topic in order to get a unique state topic if we have two sensors of the same type
        data["state_topic"] = config.mqtt_topic_prefix + "/" + hostname + "/" + what_config + "_" + device
        data["unique_id"] = hostname + "_" + what_config + "_" + device
    elif what_config == "sht21_hum_status":
        data["icon"] = "mdi:water-percent"
        data["name"] = device + " Humidity"
        data["unit_of_measurement"] = "%"
        data["device_class"] = "temperature"
        data["state_class"] = "measurement"
        # we define again the state topic in order to get a unique state topic if we have two sensors of the same type
        data["state_topic"] = config.mqtt_topic_prefix + "/" + hostname + "/" + what_config + "_" + device
        data["unique_id"] = hostname + "_" + what_config + "_" + device
    
    else:
        return ""
    # Return our built discovery config

    if hass_api:
        result = {
            "name": data["name"],
            "icon": data["icon"],
            "state_class": data["state_class"],
        }
        if "unit_of_measurement" in data:
            result["unit_of_measurement"] = data["unit_of_measurement"]      
        if "device_class" in data:
            result["device_class"] = data["device_class"]
        if "unique_id" in data:
            result["unique_id"] = data["unique_id"] 
        if "value_template" in data:
            result["value_template"] = data["value_template"] 
            
        return result

    return json.dumps(data)


# Code is copied and adopted from https://github.com/frickler24/rpi-mqtt-monitor
def publish_to_mqtt(report):
    client = create_mqtt_client()
    if client is None:
        return

    client.loop_start()

  # Publish values received in status report
    for key, value in report.items():
        if config.discovery_messages:
            client.publish(f"{config.mqtt_discovery_prefix}/sensor/{config.mqtt_topic_prefix}/{hostname}_{key}/config",
                config_json(key), qos=config.qos)
        client.publish(f"{config.mqtt_topic_prefix}/{hostname}/{key}", value, qos=config.qos, retain=config.retain)
    
    while len(client._out_messages) > 0:
        time.sleep(0.1)
        client.loop()

    client.loop_stop()
    client.disconnect()


def put_data(report_data: Dict[str, Union[str, int, float, Literal["Success"]]]) -> None:
    """
    Print data from report

    Args:
        report_data (Dict[str, Union[str, int, float, Literal["Success"]]]): Ein Wörterbuch mit den Berichtsdaten.
    """

    def get_len_of_longest_item(report_data: Dict[str, Union[str, int, float, Literal["Success"]]]) -> None:
        """
        Find longest key for formatting the output

        Args:
            report_data (Dict[str, Union[str, int, float, Literal["Success"]]]): Ein Wörterbuch mit den Berichtsdaten.
        
        Returns:
            length (int)
        """
        maxlen: int = 0
        for key, _ in report_data.items():
            maxlen = max(maxlen, len(key))
        return maxlen + 1

    print('The report data:')
    # print(f'{report_data}', flush=True)
    
    maxlen: int = get_len_of_longest_item(report_data)
    for key, val in report_data.items():
        print(f'{key:{maxlen}}: {val}')


# This function is called for each POST Request
@app.route('/backup_report', methods=['POST'])
def handle_backup_report():
    """
    Endpoint zum Empfangen von Backup-Berichten.
    Die Daten werden in einer Logdatei gespeichert.
    """
    report_data = request.get_json()

    # Schreibe den Bericht in die Logdatei
    with open(LOG_FILE, 'a') as log:
        log.write(json.dumps(report_data))
        log.write('\n')

    put_data(report_data)
    return 'Backup-Bericht erfolgreich gespeichert.', 200


if __name__ == '__main__':

    set_standard_signal_handler()

    app.run(host='0.0.0.0', port=5000, debug=False)
