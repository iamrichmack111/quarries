from __future__ import annotations

import os
import shutil
import subprocess
import sys


class ClipboardError(RuntimeError):
    pass


def copy_text(text: str) -> None:
    if not text:
        raise ClipboardError("There is no Hebrew text to copy.")

    commands: list[list[str]] = []

    if sys.platform == "darwin":
        commands.append(["pbcopy"])
    else:
        if os.environ.get("WAYLAND_DISPLAY") and shutil.which("wl-copy"):
            commands.append(["wl-copy"])
        if shutil.which("xclip"):
            commands.append(["xclip", "-selection", "clipboard"])
        if shutil.which("xsel"):
            commands.append(["xsel", "--clipboard", "--input"])

    for command in commands:
        try:
            subprocess.run(
                command,
                input=text.encode("utf-8"),
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return
        except (OSError, subprocess.CalledProcessError):
            continue

    raise ClipboardError(
        "No supported clipboard command was found. "
        "Install wl-clipboard, xclip, or xsel on Linux."
    )
