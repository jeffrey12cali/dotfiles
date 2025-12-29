#!/usr/bin/env python3
"""
Waybar MPRIS module script.

Why this exists:
- python-gi Playerctl collapses multiple Chromium instances to a single name ("chromium"),
  which can cause mismatches (display shows one tab/app; click controls another).
- `playerctl -l` exposes instance-aware bus names (e.g. chromium.instance1234).

So we use `playerctl` as the backend for both displaying and controlling, ensuring the
same "selected player" is used for output and for click actions.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import logging
import os
import pathlib
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Iterable, Optional

logger = logging.getLogger(__name__)

FIELD_SEP = "\x1f"  # unlikely to appear in metadata
DEFAULT_STATE_PATH = os.environ.get(
    "WAYBAR_MPRIS_STATE",
    os.path.join(os.path.expanduser("~"), ".cache", "waybar-mediaplayer", "state.json"),
)


@dataclass(frozen=True)
class PlayerSnapshot:
    bus: str
    status: str  # Playing/Paused/Stopped
    artist: str
    title: str
    identity: str

    @property
    def display_text(self) -> str:
        track_info = ""
        if self.artist and self.title:
            track_info = f"{self.artist} - {self.title}"
        elif self.title:
            track_info = self.title
        elif self.identity:
            track_info = self.identity
        else:
            track_info = ""

        if not track_info:
            return ""

        if self.status == "Playing":
            return " " + track_info
        return " " + track_info


def _split_patterns(value: Optional[str]) -> list[str]:
    if not value:
        return []
    parts = [p.strip() for p in value.split(",")]
    return [p for p in parts if p]


def _matches_any(text: str, patterns: Iterable[str]) -> bool:
    for pat in patterns:
        if fnmatch.fnmatch(text, pat):
            return True
    return False


def run_playerctl(args: list[str], timeout_s: float = 1.0) -> str:
    try:
        cp = subprocess.run(
            ["playerctl", *args],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=timeout_s,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    return cp.stdout.strip()


def list_player_buses() -> list[str]:
    out = run_playerctl(["-l"], timeout_s=1.0)
    if not out:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def snapshot_player(bus: str) -> Optional[PlayerSnapshot]:
    fmt = FIELD_SEP.join(
        [
            "{{status}}",
            "{{artist}}",
            "{{title}}",
            "{{mpris:identity}}",
        ]
    )
    out = run_playerctl(["-p", bus, "metadata", "--format", fmt], timeout_s=1.0)
    if not out:
        # Some players return empty metadata when Stopped; still try to get status.
        status = run_playerctl(["-p", bus, "status"], timeout_s=1.0)
        status = status if status else "Stopped"
        return PlayerSnapshot(bus=bus, status=status, artist="", title="", identity="")

    parts = out.split(FIELD_SEP)
    # Be defensive: metadata fields can be missing.
    while len(parts) < 4:
        parts.append("")
    status, artist, title, identity = (p.strip() for p in parts[:4])
    status = status or "Stopped"
    return PlayerSnapshot(bus=bus, status=status, artist=artist, title=title, identity=identity)


def choose_player(
    players: list[PlayerSnapshot],
    current_bus: Optional[str],
    prefer: list[str],
) -> Optional[PlayerSnapshot]:
    if not players:
        return None

    by_bus = {p.bus: p for p in players}
    current = by_bus.get(current_bus) if current_bus else None

    playing = [p for p in players if p.status == "Playing"]
    paused = [p for p in players if p.status == "Paused"]

    def pick_best(candidates: list[PlayerSnapshot]) -> Optional[PlayerSnapshot]:
        if not candidates:
            return None
        preferred = [p for p in candidates if _matches_any(p.bus, prefer) or _matches_any(p.identity, prefer)]
        return (preferred[0] if preferred else candidates[0])

    # If something is playing, prefer that. Keep current if it's playing and no preferred alternative exists.
    if playing:
        if current and current.status == "Playing":
            preferred_playing = [p for p in playing if _matches_any(p.bus, prefer) or _matches_any(p.identity, prefer)]
            if not preferred_playing:
                return current
        return pick_best(playing)

    # Otherwise show paused if any (keep current if it's paused)
    if paused:
        if current and current.status == "Paused":
            preferred_paused = [p for p in paused if _matches_any(p.bus, prefer) or _matches_any(p.identity, prefer)]
            if not preferred_paused:
                return current
        return pick_best(paused)

    # Fall back to anything (keep current if it still exists)
    return current or pick_best(players)


def write_output(text: str, bus: str) -> None:
    output = {
        "text": text,
        # Make it styleable per player bus (includes chromium.instanceXXXX)
        "class": "custom-" + bus.replace("/", "_"),
        "alt": bus,
    }
    sys.stdout.write(json.dumps(output) + "\n")
    sys.stdout.flush()


def clear_output() -> None:
    sys.stdout.write("\n")
    sys.stdout.flush()


def signal_handler(_sig, _frame):
    sys.stdout.write("\n")
    sys.stdout.flush()
    sys.exit(0)


def do_action(action: str, ignore: list[str], prefer: list[str]) -> int:
    # Prefer targeting exactly what the bar is currently showing.
    pinned_bus = read_state_bus()
    buses = [b for b in list_player_buses() if not _matches_any(b, ignore)]
    if pinned_bus and pinned_bus in buses:
        cmd = action
        if cmd == "prev":
            cmd = "previous"
        run_playerctl(["-p", pinned_bus, cmd], timeout_s=2.0)
        return 0

    snaps: list[PlayerSnapshot] = []
    for b in buses:
        s = snapshot_player(b)
        if s:
            snaps.append(s)

    chosen = choose_player(snaps, current_bus=None, prefer=prefer)
    if not chosen:
        return 0

    cmd = action
    # playerctl uses "previous" not "prev"
    if cmd == "prev":
        cmd = "previous"
    run_playerctl(["-p", chosen.bus, cmd], timeout_s=2.0)
    return 0


def read_state_bus() -> Optional[str]:
    try:
        p = pathlib.Path(DEFAULT_STATE_PATH)
        data = json.loads(p.read_text(encoding="utf-8"))
        bus = data.get("bus")
        return bus if isinstance(bus, str) and bus else None
    except Exception:
        return None


def write_state_bus(bus: Optional[str]) -> None:
    try:
        p = pathlib.Path(DEFAULT_STATE_PATH)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        payload = {"bus": bus or "", "ts": time.time()}
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        tmp.replace(p)
    except Exception:
        # Never let state persistence break the bar.
        return


def watch(poll_interval: float, ignore: list[str], prefer: list[str]) -> int:
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    current_bus: Optional[str] = None
    last_payload: Optional[str] = None

    while True:
        buses = [b for b in list_player_buses() if not _matches_any(b, ignore)]
        snaps: list[PlayerSnapshot] = []
        for b in buses:
            s = snapshot_player(b)
            if s:
                snaps.append(s)

        chosen = choose_player(snaps, current_bus=current_bus, prefer=prefer)
        if not chosen or not chosen.display_text:
            if last_payload != "":
                clear_output()
                last_payload = ""
            if current_bus is not None:
                current_bus = None
                write_state_bus(None)
        else:
            if current_bus != chosen.bus:
                current_bus = chosen.bus
                write_state_bus(current_bus)
            payload = json.dumps(
                {
                    "text": chosen.display_text,
                    "class": "custom-" + chosen.bus.replace("/", "_"),
                    "alt": chosen.bus,
                }
            )
            if payload != last_payload:
                sys.stdout.write(payload + "\n")
                sys.stdout.flush()
                last_payload = payload

        time.sleep(poll_interval)


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="count", default=0)
    parser.add_argument("--enable-logging", action="store_true")
    parser.add_argument(
        "--action",
        choices=["play-pause", "play", "pause", "stop", "next", "previous", "prev"],
        help="Perform a single action on the currently selected player and exit.",
    )
    parser.add_argument(
        "--ignore",
        default=os.environ.get("WAYBAR_MPRIS_IGNORE", ""),
        help="Comma-separated glob patterns of player buses/identities to ignore (env: WAYBAR_MPRIS_IGNORE).",
    )
    parser.add_argument(
        "--prefer",
        default=os.environ.get("WAYBAR_MPRIS_PREFER", ""),
        help="Comma-separated glob patterns of player buses/identities to prefer when multiple are active (env: WAYBAR_MPRIS_PREFER).",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=float(os.environ.get("WAYBAR_MPRIS_POLL", "1.0")),
        help="Polling interval seconds for watch mode (env: WAYBAR_MPRIS_POLL).",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    if arguments.enable_logging:
        logfile = os.path.join(os.path.dirname(os.path.realpath(__file__)), "media-player.log")
        logging.basicConfig(
            filename=logfile,
            level=logging.DEBUG,
            format="%(asctime)s %(name)s %(levelname)s:%(lineno)d %(message)s",
        )

    logger.setLevel(max((3 - arguments.verbose) * 10, 0))

    ignore = _split_patterns(arguments.ignore)
    prefer = _split_patterns(arguments.prefer)

    if arguments.action:
        return do_action(arguments.action, ignore=ignore, prefer=prefer)

    return watch(arguments.poll_interval, ignore=ignore, prefer=prefer)


if __name__ == "__main__":
    raise SystemExit(main())
