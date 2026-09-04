# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A **legacy Assetto Corsa Python 2.x app** named **AutoCam** — an "AI broadcast director" that reads live
telemetry and automatically switches cameras and driver focus to follow battles, incidents, and pit stops.
It uses the **native `ac` / `acsys` modules** (classic `acMain`/`acUpdate`/`acShutdown` global lifecycle),
**not** the ACLIB class-based framework. This is not a web/node/TS project.

Top-level layout:
- `autocam/` — **canonical runnable app** (the source of truth). Edit here.
- `_ref/` — read-only git-tracked **reference copies**: `AutoCam_V1.6/` (original) and `autocam-main/`
  (enhanced fork). Never build or edit here; `autocam/` is authoritative.
- `docs/` — gathered Assetto Corsa Python dev reference (`docs/README.md` is the index). Read the relevant
  file before touching `ac`/`acsys`/`ac.ext_*` usage.

## Build / lint / test

There is **no build, lint, or test pipeline** — this is an in-game plugin that only runs inside Assetto Corsa
(it requires the `ac`/`acsys` modules present in AC's Python runtime, so it cannot be `import`ed under system
Python). The only static check that works:

```bash
python3 -m py_compile autocam/apps/python/AutoCam/AutoCam.py
```

A `SyntaxWarning: invalid escape sequence '\.'` in `AutoCam.py` ~line 282 is pre-existing and harmless.
Runtime testing happens in-game (enable the app via Content Manager; logs go to
`Documents\Assetto Corsa\logs\py_log.txt`, console via the Home key). Config is edited in-game and persisted by
clicking the **Save** button.

## App architecture

### Load path and lifecycle
AC loads an app from `apps/python/<AppName>/`, where `<AppName>` is the directory name (here `AutoCam`).
- `autocam/apps/python/AutoCam/` holds the module; `autocam/content/gui/icons/` the app icon; `stdlib/` /
  `stdlib64/` are bundled platform `.pyd` shims injected via `sys.path.insert` based on `platform.architecture()`.
- `acMain(ac_version)` builds the UI, reads all INIs, must return the app name; `acUpdate(deltaT)` polls each
  frame; `acShutdown()` cleans up. The director decision loop is `autoCam()`, called from `acUpdate`.

### Data sources (two of them)
- Live per-car state via `ac.getCarState(id, acsys.CS.*)` (speed, lap count, spline position, in-pit, etc.).
- Whole-session data via Windows shared memory `acpmf_physics`/`graphics`/`static`, read in
  `AutoCam_sim_info.py` (mmap + ctypes).
- `AutoCamCar.AutoCamCar` wraps one car slot and provides `gapBetweenCars()` / `distanceTo()` helpers;
  `AppCom` (`initialize()`) holds the global `runningorder` string and event/ABot state.

### Config layering (order matters)
`acMain` calls `ReadSettings` **twice** — first on the default `SettingsINI = apps\python\AutoCam\AutoCam.ini`,
then on a **per-server IP** INI (`apps\python\AutoCam\<serverIP with dots→underscores>.ini`; offline =
`127_0_0_1.ini`). The later load **overrides** the earlier. `ReadCarCameras()` then loads per-car camera
weights from `carCameras.ini`. `WriteSettings()` (invoked by the Save button / `onSaveSettingsClick`) writes
**only** the default `SettingsINI`.

### Camera model
Camera modes are the `acsys.CM.*` constants (0=Cockpit, 1=Car, 2=Drivable, 3=Track, 4=Helicopter, 5=OnBoardFree,
6=Free, 7=Random). There are two independent switching concerns: **which camera mode** and **which car is
focused** (`ac.focusCar(id)` + `ac.setCameraMode(mode)`).

### Schedule format
Camera schedules are pipe-delimited `cam^usage^delay|cam^usage^delay|...` strings parsed into weighted dicts:
`cameraSwitching["GuessN"]` (cam) and `cameraDelay["DelayN"]` (delay), where `usage` is a **weight** expanded
into N duplicate `GuessN` entries to drive a weighted random pick. The same pattern is used for
`pitCameraSwitching`, `firstLapSwitching`, and `battleCams`. The weight is transient — the original raw string
is retained in `rawCameraSwitching` / `rawPitCameraSwitching` / `rawBattleCams` / `rawFirstLapSwitching`
(kept so the Save button writes back the user's schedule instead of a hardcoded preset).

### The director loop (`autoCam()`)
Runs each frame after session setup: front-priority battle scoring (`math.pow(positionDecay, pos)` weighted by
gap), overtake lock, incident/spin detection and off-pace override (both driven by a per-`(car, spline pos)`
speed baseline in `dicKMH`), pit-lane handling, dynamic chase camera, and finally weighted camera
selection. Central mutable state: `overrideCar`, `setCamera`, `cameraSwitchTimer`, `cameraSwitchDelay`;
runtime scratch maps `dic` / `dicKMH` / `dicCars`.

### Other things to know
- **CSP extensions are feature-detected** with `try/except` (e.g. `ac.ext_isVirtualMirrorForced()`); never
  assume an `ext_*` exists.
- **OBS integration is intentionally excluded** from `autocam/` — the `obsremote` / `websocket` imports are
  commented out and those bundles are not present. They only exist as history in `_ref/autocam-main/`.
- On every launch `acMain` self-copies `AutoCam.py` into `backup/` (gitignored) as a "last working copy".
- Camera schedules and config keys are documented inline at the top of `AutoCam.ini`.
