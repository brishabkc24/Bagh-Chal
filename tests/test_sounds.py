import io
import pathlib
import re
import struct
import wave

import pytest

import sounds
from sounds import EFFECTS, RATE, SoundBoard, render


class FakeWinsound:
    """Stands in for the Windows-only winsound module and records what is played."""
    SND_FILENAME = SND_ASYNC = SND_NODEFAULT = 0

    def __init__(self, fail=False):
        self.fail = fail
        self.played = []

    def PlaySound(self, path, flags):
        if self.fail:
            raise RuntimeError("no sound device")
        self.played.append(path)


@pytest.mark.parametrize("name", sorted(EFFECTS))
def test_every_effect_renders_a_valid_wav(name):
    with wave.open(io.BytesIO(render(name))) as wav:
        assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 2, RATE)
        frames = wav.getnframes()
        samples = struct.unpack('<%dh' % frames, wav.readframes(frames))
    assert frames == sum(int(RATE * ms / 1000) for _, ms, _, _ in EFFECTS[name])
    peak = max(abs(s) for s in samples)
    assert 1000 < peak < 32767                            # audible, never clipped
    assert samples[0] == 0 and abs(samples[-1]) < 400     # starts and ends quietly: no click


def test_the_game_only_asks_for_effects_that_exist():
    # play() ignores unknown names, so a typo in gui.py would fail silently.
    source = (pathlib.Path(sounds.__file__).parent / "gui.py").read_text(encoding="utf-8")
    asked = set(re.findall(r"sounds\.play\('(\w+)'\)", source))
    asked |= set(re.findall(r"jingle = '(\w+)'", source))
    assert {'place', 'move', 'capture', 'draw'} <= asked
    assert asked <= set(EFFECTS)
    assert {'win', 'lose'} <= set(EFFECTS)


def test_muted_board_plays_nothing_and_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(sounds, "winsound", FakeWinsound())
    board = SoundBoard(enabled=False, folder=str(tmp_path / "sfx"))
    assert board.play('place') is False
    assert not (tmp_path / "sfx").exists()


def test_unknown_effect_is_ignored(tmp_path, monkeypatch):
    fake = FakeWinsound()
    monkeypatch.setattr(sounds, "winsound", fake)
    assert SoundBoard(folder=str(tmp_path)).play('no-such-sound') is False
    assert fake.played == []


def test_effect_file_is_written_once_and_reused(tmp_path, monkeypatch):
    fake = FakeWinsound()
    monkeypatch.setattr(sounds, "winsound", fake)
    board = SoundBoard(folder=str(tmp_path))
    assert board.play('capture') and board.play('capture')
    assert fake.played[0] == fake.played[1]
    assert pathlib.Path(fake.played[0]).read_bytes() == render('capture')
    assert [p.name for p in tmp_path.iterdir()] == ['capture.wav']


def test_play_never_raises_when_the_sound_device_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(sounds, "winsound", FakeWinsound(fail=True))
    board = SoundBoard(folder=str(tmp_path))
    assert board.play('move') is False
    assert board.available is False                       # gives up after the first failure
    assert board.play('move') is False


def test_silent_on_systems_without_winsound(tmp_path, monkeypatch):
    monkeypatch.setattr(sounds, "winsound", None)
    board = SoundBoard(folder=str(tmp_path))
    assert board.available is False and board.play('place') is False
