"""main.py and gui.py need Tk and Pillow, which the test job does not install,
so they are never imported here. They are at least compiled, so a syntax error
cannot reach the .exe build unnoticed."""
import pathlib
import py_compile

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("name", ["main.py", "gui.py", "ai.py", "board_logic.py", "sounds.py"])
def test_module_compiles(name, tmp_path):
    py_compile.compile(str(ROOT / name), cfile=str(tmp_path / (name + "c")), doraise=True)
