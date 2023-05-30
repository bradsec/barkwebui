import nltk
import numpy as np
import re
import os
import uuid
import librosa
from librosa import effects
import noisereduce as nr
from bark.generation import generate_text_semantic, preload_models
from scipy.io.wavfile import write as write_wav
from bark.api import semantic_to_waveform
from bark import SAMPLE_RATE
import collections
import contextlib
import sys
import wave
import webrtcvad


def part_filename(filename, part_number, max_length=80):
    filename = str(part_number) + "_" + filename.replace(" ", "_")
    filename = re.sub(r"[^\w]", "", filename)
    filename = filename.lower()

    if len(filename) > max_length:
        filename = filename[:max_length]

    return filename

def resample_audio(audio, original_rate, target_rate):
    return librosa.resample(audio, orig_sr=original_rate, target_sr=target_rate)

def make_dir(dir_name):
    os.makedirs(dir_name, exist_ok=True)

    return dir_name

def read_wave(path):
    with contextlib.closing(wave.open(path, 'rb')) as wf:
        num_channels = wf.getnchannels()
        assert num_channels == 1
        sample_width = wf.getsampwidth()
        assert sample_width == 2
        sample_rate = wf.getframerate()
        assert sample_rate in (8000, 16000, 32000, 48000)
        pcm_data = wf.readframes(wf.getnframes())
        return pcm_data, sample_rate


def write_wave(path, audio, sample_rate):
    audio = audio.astype(np.int16).tostring()
    with contextlib.closing(wave.open(path, 'wb')) as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio)


class Frame(object):
    def __init__(self, bytes, timestamp, duration):
        self.bytes = bytes
        self.timestamp = timestamp
        self.duration = duration


def frame_generator(frame_duration_ms, audio, sample_rate):
    n = int(sample_rate * (frame_duration_ms / 1000.0) * 2)
    offset = 0
    timestamp = 0.0
    duration = (float(n) / sample_rate) / 2.0
    while offset + n < len(audio):
        yield Frame(audio[offset:offset + n], timestamp, duration)
        timestamp += duration
        offset += n


def vad_collector(sample_rate, frame_duration_ms, padding_duration_ms, vad, frames):
    num_padding_frames = int(padding_duration_ms / frame_duration_ms)
    ring_buffer = collections.deque(maxlen=num_padding_frames)
    triggered = False

    voiced_frames = []
    for frame in frames:
        is_speech = vad.is_speech(frame.bytes, sample_rate)

        sys.stdout.write('1' if is_speech else '0')
        if not triggered:
            ring_buffer.append((frame, is_speech))
            num_voiced = len([f for f, speech in ring_buffer if speech])
            if num_voiced > 0.9 * ring_buffer.maxlen:
                triggered = True
                sys.stdout.write('+(%s)' % (ring_buffer[0][0].timestamp,))
                for f, s in ring_buffer:
                    voiced_frames.append(f)
                ring_buffer.clear()
        else:
            voiced_frames.append(frame)
            ring_buffer.append((frame, is_speech))
            num_unvoiced = len([f for f, speech in ring_buffer if not speech])
            if num_unvoiced > 0.9 * ring_buffer.maxlen:
                sys.stdout.write('-(%s)' % (frame.timestamp + frame.duration))
                triggered = False
                yield np.frombuffer(b''.join([f.bytes for f in voiced_frames]), np.int16)
                ring_buffer.clear()
                voiced_frames = []
    if triggered:
        sys.stdout.write('-(%s)' % (frame.timestamp + frame.duration))
    sys.stdout.write('\n')
    if voiced_frames:
        yield np.frombuffer(b''.join([f.bytes for f in voiced_frames]), np.int16)

def split_text_into_chunks(text_input):
    # Replace multiple newline characters with a single space
    text_input = re.sub(r'\n+', ' ', text_input)

    # Remove a period if it's directly followed by any number of spaces and a musical note
    text_input = re.sub(r'\.\s*♪', ' ♪', text_input)

    # If there are music notes in the text, split it into song parts and non-song parts
    if '♪' in text_input:
        song_parts = re.split(r'♪', text_input)
        song_parts = [part.strip() for part in song_parts if part.strip()]

        # Split song parts by sentences and non-song parts by periods
        chunks = []
        for i, part in enumerate(song_parts):
            if i % 2 == 0:
                non_song_chunks = re.split(r'\. ', part)
                # Add back the period to the end of each non-song chunk except for the last one
                non_song_chunks = [chunk.strip() + '.' for chunk in non_song_chunks[:-1]] + [non_song_chunks[-1]]
                chunks.extend(non_song_chunks)
            else:  # Song parts
                sentences = nltk.sent_tokenize(part)
                sentences = ['♪ ' + sentence.strip() + ' ♪' for sentence in sentences]
                chunks.extend(sentences)
        chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
    # If there are no music notes, just split the text by periods
    else:
        chunks = re.split(r'\. ', text_input)
        # Add back the period to the end of each chunk except for the last one
        chunks = [chunk.strip() + '.' for chunk in chunks[:-1]] + [chunks[-1].strip()]

    # Check and modify the chunks if any chunk is less than 10 words
    modified_chunks = []
    current_chunk = ""
    for i, chunk in enumerate(chunks):
        if len(current_chunk.split()) < 10:
            # Combine with the current chunk if it exists
            current_chunk += ' ' + chunk.strip()
            # If the current chunk has 10 or more words or it's the last chunk, add it to modified chunks
            if len(current_chunk.split()) >= 10 or i == len(chunks) - 1:
                modified_chunks.append(current_chunk.strip())
                current_chunk = ""
        else:
            # If the current chunk is 10 or more words, add it to modified chunks and start a new current chunk
            modified_chunks.append(current_chunk.strip())
            current_chunk = chunk.strip()

    # Check if there is a remaining current chunk and if it is, append it to modified_chunks
    if current_chunk:
        modified_chunks.append(current_chunk.strip())

    return modified_chunks

def generate_voice(text_input, voice, progress_callback=None, text_temp=0.7, waveform_temp=0.7, speed=1.0, pitch=0, reduce_noise=False, remove_silence=False):
    print("Generating text with Bark AI voice...")
    print(f"Voice: {voice}, Text Temp: {text_temp}, Waveform Temp: {waveform_temp}, Speed: {speed}, Pitch: {pitch}, Reduce Noise: {reduce_noise}, Remove Silence: {remove_silence}")
    
    script = text_input.replace("\n", " ").strip()
    chunks = split_text_into_chunks(script)
    output_filename = None
    total_parts = len(chunks)
    parts_processed = 0
    pieces = []
    sample_rate = 24000
    silence = np.zeros(int(0.25 * SAMPLE_RATE))

    for i, chunk in enumerate(chunks):
        parts_processed += 1
        print(f"Processing part {parts_processed} of {total_parts}: {chunk}")

        semantic_tokens = generate_text_semantic(
            chunk,
            history_prompt=voice,
            temp=text_temp,
            min_eos_p=0.05,
        )

        audio_array = semantic_to_waveform(semantic_tokens, history_prompt=voice, temp=waveform_temp)

        audio_array = audio_array / np.max(np.abs(audio_array))
        audio_array_int16 = np.int16(audio_array * 32767)
        pieces.append(audio_array_int16)

        if parts_processed != total_parts:
            pieces.append(silence.copy())

        if progress_callback:
            progress_callback(parts_processed, total_parts) 

    full_audio = np.concatenate(pieces)
    full_audio = full_audio / np.max(np.abs(full_audio))

    # For remove_silence webrtcvad.Vad doesn't support 24000 sample rate, nearest supported is 16000
    if remove_silence:
        sample_rate = 16000
        full_audio = resample_audio(full_audio, SAMPLE_RATE, sample_rate)

    print(f'This output audio sample will be: {sample_rate}')
    print(f'Processing final audio...')

    final_audio = np.int16(full_audio * 32767)

    if len(final_audio) > 0:
        final_audio_int16 = np.frombuffer(final_audio, dtype=np.int16)
        
        if reduce_noise:
            print(f'Running noise reduction on audio...')
            final_audio = nr.reduce_noise(y=final_audio_int16, sr=sample_rate) 
        else:
            final_audio = final_audio_int16

        if remove_silence:
            print(f'Removing silence from audio...')
            frame_duration_ms = 30
            padding_duration_ms = 300
            vad = webrtcvad.Vad(3 if remove_silence else 0)
            frames = frame_generator(frame_duration_ms, final_audio, sample_rate)
            segments = vad_collector(sample_rate, frame_duration_ms, padding_duration_ms, vad, frames)
            concataudio = [segment for segment in segments]
            final_audio = b"".join(concataudio)
            final_audio = np.frombuffer(final_audio, dtype=np.int16)
        
        # Convert to float for librosa processing
        final_audio_float = final_audio.astype(np.float32) / 32767

        # Adjust speed for the full audio
        if speed != 1.0:
            print(f'Adjusting audio speed to: {speed}')
            librosa_speed = 1.0 * speed
            final_audio_float = librosa.effects.time_stretch(final_audio_float, rate=librosa_speed)

        # Adjust pitch for the full audio
        if pitch != 0:
            print(f'Adjusting audio pitch by: {pitch}')
            final_audio_float = librosa.effects.pitch_shift(y=final_audio_float, sr=sample_rate, n_steps=pitch)

        # Convert back to int16 for saving to wav file
        final_audio_final = np.int16(final_audio_float * 32767)

        output_filename = f"{uuid.uuid4().hex}.wav"
        write_wav(os.path.join("static", "output", output_filename), sample_rate, final_audio_final)

    print(f"Audio generation completed: {output_filename}")
    return output_filename



