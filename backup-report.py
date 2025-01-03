from flask import Flask, request
import json
import signal
import os

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

    if signum == signal.SIGTERM:
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

if __name__ == '__main__':
    set_standard_signal_handler()
    app.run(host='0.0.0.0', port=5000, debug=False)
