#!/usr/bin/env python3
"""
keep_awake_while_claude.py — stop Windows idle-sleeping while the Claude desktop app is open,
so a session followed from the phone (Remote Control) stays reachable.

It changes no Windows setting: it holds the same "system required" request that
scan_daily_update.py uses (common_utils.keep_awake), and the request ends when this process
exits. It exits by itself within a minute of the Claude desktop app closing.
The screen can still turn off, and closing the laptop lid still sleeps.

Start it hidden (from the repo folder):
    pythonw keep_awake_while_claude.py           # now: holds while Claude is open, then exits
    pythonw keep_awake_while_claude.py --watch   # at logon: waits for Claude, holds while it is
                                                 # open, releases when it closes, keeps watching
Stop it early: end the pythonw.exe process in Task Manager.
"""

import ctypes
import os
import sys
import time
from datetime import datetime

import psutil

from common_utils import keep_awake

APP_MARKER = "\\windowsapps\\claude_"   # the desktop app's install path
CHECK_SECONDS = 60
LOG = os.path.join("logs", "keep_awake_while_claude.log")


def log(msg):
    os.makedirs("logs", exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}\n")


def claude_app_running():
    for p in psutil.process_iter(["exe"]):
        exe = (p.info.get("exe") or "").lower()
        if APP_MARKER in exe:
            return True
    return False


def another_instance_running():
    me = os.getpid()
    name = os.path.basename(__file__).lower()
    for p in psutil.process_iter(["pid", "cmdline"]):
        if p.info["pid"] == me:
            continue
        cmd = " ".join(p.info.get("cmdline") or []).lower()
        if name in cmd and "python" in cmd:
            return True
    return False


def release():
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)   # ES_CONTINUOUS alone = clear


def watch():
    log(f"watch mode started (pid {os.getpid()})")
    held = False
    while True:
        running = claude_app_running()
        if running and not held:
            keep_awake()
            held = True
            log("Claude opened: holding the PC awake")
        elif held and not running:
            release()
            held = False
            log("Claude closed: released")
        time.sleep(CHECK_SECONDS)


def main():
    if another_instance_running():
        log("already running, this copy exits")
        return
    if not claude_app_running():
        log("Claude desktop app not running, nothing to do")
        return
    keep_awake()
    log(f"started (pid {os.getpid()}): holding the PC awake while Claude is open")
    while claude_app_running():
        time.sleep(CHECK_SECONDS)
    log("Claude desktop app closed: released, exiting")


if __name__ == "__main__":
    if sys.platform != "win32":
        sys.exit(0)
    if "--watch" in sys.argv:
        if another_instance_running():
            log("already running, this copy exits")
        else:
            watch()
    else:
        main()
