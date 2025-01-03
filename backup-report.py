from flask import Flask, request
import json
import signal
import os
import time
import paho.mqtt.client as paho
import re
import socket
import config

app = Flask(__name__)

# Pfad zur Logdatei
LOG_FILE = '/app/logdir/backup_reports.log'

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

    return 'Backup-Bericht erfolgreich gespeichert.', 200


def handler(signum, frame):
    signame = signal.Signals(signum).name
    print(f'Signal handler called with signal {signame} ({signum})')
    print(f'{frame:}', flush=True)

    if signum == signal.SIGTERM or signum == signal.SIGINT:
        print(f'Got Signal {signame}, terminating normally.')
        os._exit(0)
 

def set_standard_signal_handler():
    signal.signal(signal.SIGALRM, handler)
    signal.signal(signal.SIGHUP, handler)
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGUSR1, handler)
    signal.signal(signal.SIGUSR2, handler)
    signal.signal(signal.SIGCONT, handler)


# Code is copied and adopted from https://github.com/frickler24/rpi-mqtt-monitor
def create_mqtt_client():

    def on_log(client, userdata, level, buf):
        if level == paho.MQTT_LOG_ERR:
            print("MQTT error: ", buf)

    def on_connect(client, userdata, flags, rc):
        if rc != 0:
            print("Error: Unable to connect to MQTT broker, return code:", rc)
    
    client = paho.Client(client_id="backupserver-" + hostname + str(int(time.time())))
    client.username_pw_set(config.mqtt_user, config.mqtt_password)
    client.on_log = on_log
    client.on_connect = on_connect
    try:
        client.connect(config.mqtt_host, int(config.mqtt_port))
    except Exception as e:
        print("Error connecting to MQTT broker:", e)
        return None
    return client

if "hostname" in dir(config):
    hostname = getattr(config, "hostname")
else:
    hostname = re.sub(r'[^a-zA-Z0-9_-]', '_', socket.gethostname())

if __name__ == '__main__':

    set_standard_signal_handler()
    print(f'{hostname=}, {dir(config)=}')

    # for key in dir(config):
    #     print(f'Gefunden: {key}, Wert = {getattr(config, key)}')
    
    print(f'{hostname=}')
    
    app.run(host='0.0.0.0', port=5000, debug=False)
