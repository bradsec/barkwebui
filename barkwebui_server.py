from flask import Flask, render_template, request, send_from_directory, jsonify
from flask_socketio import SocketIO, emit
import os
import json
import time
from barkwebui_connector import generate_voice

app = Flask(__name__)
socketio = SocketIO(app)
generation_task = None

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

@app.route('/static/output/<path:filename>')
def serve_static(filename):
    return send_from_directory('static/output', filename)

@socketio.on('start_generation')
def handle_start_generation(data):
    text_input = data['text_input']
    voice = data['voice']
    text_temp = float(data['text_temp'])
    waveform_temp = float(data['waveform_temp'])
    reduce_noise = data['reduce_noise']
    remove_silence = data['remove_silence']
    speed = float(data['speed'])
    pitch = int(data['pitch'])
    if text_input.strip() == '':
        emit('error', {'error': 'Text is empty.'})
        return

    start_time = time.time()
    filename = generate_voice(text_input, voice, update_progress, text_temp, waveform_temp, speed, pitch, reduce_noise, remove_silence)
    end_time = time.time()
    duration = round(end_time - start_time, 2)
    print(f"Generation took {duration} seconds")

    # Write data to JSON
    write_to_json(text_input, filename, voice, text_temp, waveform_temp, speed, pitch, reduce_noise, remove_silence, duration)

    # Emit 'generation_complete' event with the filename
    emit('generation_complete', {'filename': filename, 'generation_time': duration})

def update_progress(current, total):
    progress = current / total
    emit('generation_progress', {'progress': progress}, broadcast=True)

@app.route('/static/output/<path:filename>', methods=['DELETE'])
def delete_file(filename):
    try:
        file_path = os.path.join('static/output', filename)
        os.remove(file_path)

        # Remove data from JSON
        remove_from_json(filename)
        return jsonify({'message': 'File deleted successfully'})
    except OSError as e:
        return jsonify({'message': 'Error deleting file: ' + str(e)}), 500

def write_to_json(text_input, filename, voice, text_temp, waveform_temp, speed, pitch, reduce_noise, remove_silence, duration):
    data = {}
    json_file = os.path.join('static/json', 'barkwebui.json')
    try:
        # Read existing data
        with open(json_file, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    # Remove the .wav extension from the filename
    file_id = os.path.splitext(filename)[0]

    # Append new data to the beginning of the JSON list
    data = {file_id: {
        'textInput': text_input,
        'voice': voice,
        'textTemp': text_temp,
        'waveformTemp': waveform_temp,
        'speed': speed,
        'pitch': pitch,
        'reduceNoise': reduce_noise,
        'removeSilence': remove_silence,
        'outputFile': filename,
        'generationTime': duration
    }, **data}

    # Write the data back to the file with pretty formatting
    with open(json_file, 'w') as f:
        json.dump(data, f, indent=4)


def remove_from_json(filename):
    data = {}
    json_file = os.path.join('static/json', 'barkwebui.json')
    try:
        # Read existing data
        with open(json_file, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    # Remove the .wav extension from the filename
    file_id = os.path.splitext(filename)[0]

    # Remove the data entry for the given filename
    if file_id in data:
        del data[file_id]

    # Check if data is empty after removal
    if not data:
        os.remove(json_file)
    else:
        # If not, write the data back to the file with pretty formatting
        with open(json_file, 'w') as f:
            json.dump(data, f, indent=4)


if __name__ == '__main__':
    # Note will allow access from other devices on same network.
    socketio.run(app, host='0.0.0.0', debug=True)
