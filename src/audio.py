import sounddevice as sd
import numpy as np

# Sound variables
CALLBACKS_PER_SECOND = 38               # Callbacks per second (system dependent)
SUS_FINDING_FREQUENCY = 2               # Calculates SUS *n* times every second
SOUND_AMPLITUDE_THRESHOLD = 20          # Amplitude considered for SUS calc
SUS_COUNT_THRESHOLD = 2                 # Number of consecutive high-amplitude checks to trigger cheat flag

# Packing *n* frames to calculate SUS
FRAMES_COUNT = int(CALLBACKS_PER_SECOND / SUS_FINDING_FREQUENCY)
AMPLITUDE_LIST = [0] * FRAMES_COUNT
SUS_COUNT = 0
count = 0

def _calculate_rms(indata):
    """Calculate the Root Mean Square (RMS) value of the audio data."""
    return np.sqrt(np.mean(indata**2)) * 1000

def _audio_callback(indata, outdata, frames, time, status, alert_manager, audio_state):
    """This function is called for each audio block from the sound device."""
    global SUS_COUNT, count # These can remain as module-level state for the callback
    rms_amplitude = _calculate_rms(indata)
    AMPLITUDE_LIST.append(rms_amplitude)
    count += 1
    AMPLITUDE_LIST.pop(0)
    
    if count == FRAMES_COUNT:
        avg_amp = sum(AMPLITUDE_LIST) / FRAMES_COUNT
        
        if avg_amp > SOUND_AMPLITUDE_THRESHOLD:
            SUS_COUNT += 1
        else:
            # Reset the counter if the sound is no longer sustained
            SUS_COUNT = 0

        # If the sound has been sustained long enough, set the cheat flag
        if SUS_COUNT >= SUS_COUNT_THRESHOLD:
            audio_state["is_cheating"] = 1
        else:
            audio_state["is_cheating"] = 0 # Reset the flag if sound is no longer sustained

        count = 0

def sound(alert_manager, audio_state):
    """Starts listening to the microphone and updates shared state."""
    # Use a lambda to pass the shared state objects to the callback.
    with sd.Stream(callback=lambda indata, outdata, frames, time, status: _audio_callback(indata, outdata, frames, time, status, alert_manager, audio_state)):
        sd.sleep(-1)

if __name__ == "__main__":
    pass # This module is not meant to be run directly
