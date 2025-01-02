from flask import Flask, request
import json
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
