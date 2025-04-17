import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = os.urandom(24)

CONFIG_FILE = 'config.json'

# actual default values are here
def get_default_config():
    return {
        "systemInfo": {
            "rtosSchedulerPolicy": "FIFO",
            "rtosTimeSliceMsRR": 10
        },
        "persistentLogging": {
            "enabled": True,
            "samplingRateHz": 10,
            "maxLogSizeMB": 512,
            "logItems": [
                "Timestamp", "MeltTemp", "InjectionPressure",
                "VibrationAmplitude", "VibrationFrequency", "Stage"
            ]
        },
        "criticalEventCapture": {
            "enabled": True,
            "captureRateHz": 100,
            "logItems": [
                "Timestamp", "MeltTemp", "InjectionPressure",
                "VibrationAmplitude", "VibrationFrequency", "Stage"
            ],
            "preEventBufferSizeSeconds": 30,
            "postEventDurationSeconds": 60,
            "retentionPolicy": "KEEP_LAST_N_EVENTS",
            "retentionValue": 10,
            "uploadOnEvent": True
        },
        "criticalEventTriggers": {
            "triggerDefinitions": [
                {
                    "triggerId": "TEMP_HIGH",
                    "logItemName": "MeltTemp",
                    "condition": "GREATER_THAN",
                    "value": 250.0
                },
                {
                    "triggerId": "PRESSURE_LOW",
                    "logItemName": "InjectionPressure",
                    "condition": "LESS_THAN",
                    "value": 50.0
                },
                {
                    "triggerId": "VIBRATION_AMP_HIGH",
                    "logItemName": "VibrationAmplitude",
                    "condition": "GREATER_THAN",
                    "value": 2.5
                }
            ]
        },
        "networkManagement": {
            "uploadEnabled": True,
            "uploadMethod": "PERIODIC",
            "uploadAmt": 3600,
            "maxUploadRateKBps": 100,
            "networkInterface": "eth0",
            "uploadDestination": {
                "protocol": "HTTPS",
                "serverAddress": "poop.com",
                "port": 443,
                "endpointPath": "/api/",
                "cloudProviderHint": "AWS",
                "authentication": {
                    "type": "Bearer",
                    "token": "YOUR_SECURE_TOKEN_HERE"
                }
            }
        }
    }

def load_config():
    defaults = get_default_config()
    if not os.path.exists(CONFIG_FILE):
        flash(f"Configuration file '{CONFIG_FILE}' not found. Creating with defaults.", "warning")
        save_config(defaults) # Create the file if it doesn't exist
        return defaults

    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)

        return config

    except json.JSONDecodeError:
        flash(f"Error decoding JSON from '{CONFIG_FILE}'. Using default values.", "error")
        return defaults


def save_config(config_data):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=2, sort_keys=False)
        flash("Configuration saved successfully!", "success")
        return True
    except IOError as e:
        flash(f"Error saving configuration file '{CONFIG_FILE}': {e}", "error")
        return False
    except Exception as e:
        flash(f"An unexpected error occurred saving config: {e}", "error")
        return False


# --- Flask Routes ---

@app.route('/', methods=['GET'])
def index():
    current_config = load_config()
    # formatting json string for display
    try:
        triggers_json_string = json.dumps(current_config.get('criticalEventTriggers', {}).get('triggerDefinitions', []), indent=2)
    except Exception:
        triggers_json_string = "[] # Error formatting existing triggers"
        flash("Error formatting current trigger definitions for display.", "error")

    return render_template('index.html', config=current_config, triggers_json=triggers_json_string)


@app.route('/update', methods=['POST'])
def update_config():
    # Start with loading the existing config
    new_config = load_config()
    form = request.form

    # huge try catch to load all the values
    try:
        # --- System Info ---
        new_config['systemInfo']['rtosSchedulerPolicy'] = form.get('systemInfo_rtosSchedulerPolicy')
        new_config['systemInfo']['rtosTimeSliceMsRR'] = int(form.get('systemInfo_rtosTimeSliceMsRR'))

        # --- Persistent Logging ---
        new_config['persistentLogging']['enabled'] = form.get('persistentLogging_enabled', 'false').lower() == 'true'
        new_config['persistentLogging']['samplingRateHz'] = int(form.get('persistentLogging_samplingRateHz'))
        new_config['persistentLogging']['maxLogSizeMB'] = int(form.get('persistentLogging_maxLogSizeMB'))
        log_items_str = form.get('persistentLogging_logItems', '')
        new_config['persistentLogging']['logItems'] = [item.strip() for item in log_items_str.split(',') if item.strip()]

        # --- Critical Event Capture ---
        new_config['criticalEventCapture']['enabled'] = form.get('criticalEventCapture_enabled', 'false').lower() == 'true'
        new_config['criticalEventCapture']['captureRateHz'] = int(form.get('criticalEventCapture_captureRateHz'))
        crit_log_items_str = form.get('criticalEventCapture_logItems', '')
        new_config['criticalEventCapture']['logItems'] = [item.strip() for item in crit_log_items_str.split(',') if item.strip()]
        new_config['criticalEventCapture']['preEventBufferSizeSeconds'] = int(form.get('criticalEventCapture_preEventBufferSizeSeconds'))
        new_config['criticalEventCapture']['postEventDurationSeconds'] = int(form.get('criticalEventCapture_postEventDurationSeconds'))
        new_config['criticalEventCapture']['retentionPolicy'] = form.get('criticalEventCapture_retentionPolicy')
        new_config['criticalEventCapture']['retentionValue'] = int(form.get('criticalEventCapture_retentionValue'))
        new_config['criticalEventCapture']['uploadOnEvent'] = form.get('criticalEventCapture_uploadOnEvent', 'false').lower() == 'true'

        triggers_json_string_from_form = form.get('criticalEventTriggers_definitions_json')
        try:
            parsed_triggers = json.loads(triggers_json_string_from_form)

            # list check
            if isinstance(parsed_triggers, list):
                 new_config['criticalEventTriggers']['triggerDefinitions'] = parsed_triggers
            else:
                flash("Input must be a list (embedded in [])", "error")

        except json.JSONDecodeError as json_err:
            flash(f"Invalid JSON syntax in Critical Triggers text area: {json_err}. Triggers not updated.", "error")
        except Exception as e:
             flash(f"Error processing Critical Triggers: {e}. Triggers not updated.", "error")

        # --- Network Management ---
        new_config['networkManagement']['uploadEnabled'] = form.get('networkManagement_uploadEnabled', 'false').lower() == 'true'
        new_config['networkManagement']['uploadMethod'] = form.get('networkManagement_uploadMethod')
        new_config['networkManagement']['uploadAmt'] = int(form.get('networkManagement_uploadAmt'))
        new_config['networkManagement']['maxUploadRateKBps'] = int(form.get('networkManagement_maxUploadRateKBps'))
        new_config['networkManagement']['networkInterface'] = form.get('networkManagement_networkInterface')

        # --- Upload Destination ---
        new_config['networkManagement']['uploadDestination']['protocol'] = form.get('uploadDestination_protocol')
        new_config['networkManagement']['uploadDestination']['serverAddress'] = form.get('uploadDestination_serverAddress')
        new_config['networkManagement']['uploadDestination']['port'] = int(form.get('uploadDestination_port'))
        new_config['networkManagement']['uploadDestination']['endpointPath'] = form.get('uploadDestination_endpointPath')
        new_config['networkManagement']['uploadDestination']['cloudProviderHint'] = form.get('uploadDestination_cloudProviderHint')

        # --- Authentication ---
        new_config['networkManagement']['uploadDestination']['authentication']['type'] = form.get('authentication_type')
        new_config['networkManagement']['uploadDestination']['authentication']['token'] = form.get('authentication_token')

        # --- Save the updated configuration ---
        save_config(new_config)

    except ValueError as e:
        flash(f"Invalid input value: Ensure numbers are entered correctly. Error: {e}", "error")
    except KeyError as e:
        flash(f"Configuration structure error: Missing expected key '{e}'. Check config file or defaults.", "error")
    except Exception as e:
        flash(f"An unexpected error occurred during update: {e}", "error")

    # back to main page
    return redirect(url_for('index'))

@app.route('/monitor', methods=['GET'])
def monitor():

    fake_status = {
        'currentMeltTemp': 150.2,
        'currentStage': 'Pooping',
        'persistentLogUsageMB': 100.1,
        'persistentLogMaxMB': 512,
        'criticalEventsStored': 2,
        'criticalEventsMax': 10,
        'uploadQueueSize': 5,
        'lastUploadTime': '2025-04-16 23:05:12 EDT'
    }

    # pass fake data to template
    return render_template('monitor.html', status=fake_status)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

