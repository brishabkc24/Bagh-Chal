# sounds.py
"""Sound effects, synthesised at run time so the game ships no audio files.

Every effect is a handful of decaying sine notes. It is written once to a small
WAV in the temp folder and played through winsound, which exists on Windows
only. On any other system, or if the sound device refuses, play() does nothing.
"""
import io
import math
import os
import struct
import tempfile
import wave

try:
    import winsound
except ImportError:           # not Windows
    winsound = None

RATE = 22050                  # samples per second, mono, 16 bit

# name -> notes played one after the other.
# A note is (start frequency Hz, length ms, volume 0..1, end frequency Hz).
# A different end frequency makes the pitch glide, which turns a tone into a thud.
EFFECTS = {
    'select':  [(880, 45, 0.25, 880)],
    'place':   [(520, 110, 0.60, 520)],
    'move':    [(420, 90, 0.50, 420)],
    'capture': [(200, 90, 0.90, 110), (120, 240, 0.90, 60)],
    'illegal': [(160, 120, 0.45, 150)],
    'win':     [(523, 110, 0.55, 523), (659, 110, 0.55, 659),
                (784, 110, 0.55, 784), (1047, 380, 0.60, 1047)],
    'lose':    [(392, 160, 0.50, 392), (330, 160, 0.50, 330), (262, 420, 0.55, 262)],
    'draw':    [(440, 160, 0.50, 440), (440, 320, 0.50, 440)],
}


def _note(freq, ms, volume, end_freq):
    """Samples (-1..1) of one plucked note: 4 ms attack, exponential decay, two
    soft overtones. The envelope starts and ends at zero, so notes never click."""
    count = int(RATE * ms / 1000)
    attack = max(1, int(RATE * 0.004))
    samples = []
    phase = 0.0
    for i in range(count):
        t = i / count
        phase += 2 * math.pi * (freq + (end_freq - freq) * t) / RATE
        envelope = min(1.0, i / attack) * math.exp(-5.0 * t)
        tone = math.sin(phase) + 0.35 * math.sin(2 * phase) + 0.15 * math.sin(3 * phase)
        samples.append(volume * envelope * tone / 1.5)
    return samples


def render(name):
    """The complete WAV file for one effect, as bytes."""
    samples = []
    for note in EFFECTS[name]:
        samples.extend(_note(*note))
    frames = struct.pack('<%dh' % len(samples),
                         *(int(max(-1.0, min(1.0, s)) * 32767) for s in samples))
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes(frames)
    return buffer.getvalue()


class SoundBoard:
    """Plays the effects by name. Safe on every platform: play() never raises,
    it returns True only when a sound was actually started."""

    def __init__(self, enabled=True, folder=None):
        self.enabled = enabled
        self.available = winsound is not None
        self.folder = folder or os.path.join(tempfile.gettempdir(), 'baghchal-sounds')
        self._paths = {}

    def path(self, name):
        """Path of the effect's WAV file, written on first use."""
        if name not in self._paths:
            data = render(name)
            os.makedirs(self.folder, exist_ok=True)
            path = os.path.join(self.folder, name + '.wav')
            # Reuse a file left by an earlier run: a second copy of the game
            # may be playing it right now, and Windows would refuse the write.
            if not os.path.exists(path) or os.path.getsize(path) != len(data):
                with open(path, 'wb') as handle:
                    handle.write(data)
            self._paths[name] = path
        return self._paths[name]

    def play(self, name):
        if not (self.enabled and self.available) or name not in EFFECTS:
            return False
        try:
            winsound.PlaySound(self.path(name), winsound.SND_FILENAME
                               | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
            return True
        except (RuntimeError, OSError):   # no sound device, read-only temp folder
            self.available = False
            return False
