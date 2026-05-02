# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Windows-only Python game automation bot for "向僵尸开炮" (Shoot at the Zombies), a WeChat mini-program. Uses OpenCV template matching and pixel sampling to detect game state, simulates mouse/keyboard input via pyautogui and win32api.

## Commands

```bash
# Run the bot (launches Tkinter GUI)
python game_bot.py

# Install dependencies
pip install pyautogui opencv-python numpy pywin32 pynput

# Build standalone exe
build_exe.bat

# Benchmarks and manual tests (require live game window)
python benchmark_match.py
python test_exit_logic.py
python test_leave_team.py
```

No automated test framework, linter, or CI is configured.

## Architecture

**Single-file monolith** — all logic in `game_bot.py` (~1800 lines).

**Two classes:**
- `GameBot` (line 38-) — Core engine: window management, screenshot capture, template matching, mouse input, game state machines
- `GameBotGUI` (line 1428-) — Tkinter GUI wrapper, config persistence to `config.json`

**Template matching** — ~100 PNG templates in `templates/` directory. Default threshold 0.8, huanqiu level matching uses 0.95+. `cv2.matchTemplate` with `TM_CCOEFF_NORMED`.

**Performance-critical path (mode 0, rich_mode=1 "poor mode"):**
- Three-thread architecture: screenshot thread (~25fps), detection thread (matchTemplate-based, ~4.5Hz), main click loop (~5μs/click via `win32api.mouse_event`)
- Detection thread uses state-driven detection: `recruit → team → battle → unknown` cycle, only checks relevant templates per state
- `_fast_find_huanqiu()` uses pixel sampling (numpy vectorized) as ~50x faster alternative to matchTemplate for finding huanqiu buttons
- Shared state protected by `threading.Lock` (`_state_lock`, `_img_lock`)
- `_detection_reset` flag signals detection thread to reset state machine after battle ends

**Four game modes:** Mode 0 (Huanqiu), Mode 1 (Main story), Mode 2 (Normal expedition), Mode 3 (Super expedition). Each has its own branch in `main_loop()`.

**Config** — `config.json` stores: `game_title`, `mode`, `rich_mode`, `battle_count`, `battle_time`, `priority_skills` (5 skill names), `target_huanqiu_levels` (level numbers).

## Key Constraints

- Windows only (win32api, win32gui)
- Recommended game window size: 542x1010 pixels for accurate template matching
- Default game window title: "抖音"
- Templates are resolution-sensitive; re-capture if window size changes
- Python GIL: `cv2.matchTemplate` releases GIL during C++ execution (enables true parallelism in detection thread); numpy operations do not release GIL
- All user-facing text and docs are in Chinese
