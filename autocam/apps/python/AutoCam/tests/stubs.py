# Offline test stubs: let the AC app modules be imported on a non-Windows host
# without a running Assetto Corsa instance. Assetto Corsa only ships its `ac` /
# `acsys` builtins + Windows shared memory in-game, so we substitute fakes here.
import sys
import types
import ctypes


class _FakeAC(object):
    """Controllable stand-in for Assetto Corsa's `ac` module."""

    def __init__(self):
        # (car, acsys.CS constant) -> value
        self._state = {}
        self._drivers = {}    # car -> driver name
        self._carnames = {}   # car -> car name
        self._track_len = 0.0
        self._pit = {}        # car -> 0/1
        self._pitline = {}    # car -> 0/1
        # force getCarState to raise for this (car, constant) tuple
        self._raise_on_get = None
        self.console = lambda *a, **k: None
        self.log = lambda *a, **k: None

    # ---- API surface AutoCam.py calls ----
    def getCarState(self, car, constant):
        if self._raise_on_get == (car, constant):
            raise RuntimeError('stubbed getCarState raise')
        return self._state.get((car, constant), 0.0)

    def getDriverName(self, car):
        return self._drivers.get(car, 'driver%d' % car)

    def getCarName(self, car):
        return self._carnames.get(car, 'car%d' % car)

    def getTrackLength(self, idx=0):
        return self._track_len

    def isCarInPit(self, car):
        return self._pit.get(car, 0)

    def isCarInPitline(self, car):
        return self._pitline.get(car, 0)

    # ---- helpers for tests ----
    def reset(self):
        self._state.clear()
        self._pit.clear()
        self._pitline.clear()
        self._raise_on_get = None

    def set_car_state(self, car, **constants):
        for k, v in constants.items():
            self._state[(car, k)] = v

    def set_driver(self, car, name):
        self._drivers[car] = name

    def set_car_name(self, car, name):
        self._carnames[car] = name

    def set_track_length(self, meters):
        self._track_len = meters

    def set_in_pit(self, car, on):
        self._pit[car] = 1 if on else 0

    def set_in_pitline(self, car, on):
        self._pitline[car] = 1 if on else 0


class _FakeAcSys(object):
    """Stand-in for Assetto Corsa's `acsys` module (CS/CM constant namespaces)."""
    CS = types.SimpleNamespace(
        LapCount='LapCount',
        NormalizedSplinePosition='NormalizedSplinePosition',
        SpeedKMH='SpeedKMH',
        WorldPosition='WorldPosition',
        RaceFinished='RaceFinished',
    )
    CM = types.SimpleNamespace()


def install():
    """Register fakes in sys.modules so `import AutoCam` works offline.

    Must be called before importing AutoCam / AutoCamCar. Safe to call once.
    """
    global fake_ac, fake_acsys

    fake_ac = _FakeAC()
    fake_acsys = _FakeAcSys()

    ac_mod = types.ModuleType('ac')
    for attr in ('getCarState', 'getDriverName', 'getCarName', 'getTrackLength',
                 'isCarInPit', 'isCarInPitline', 'console', 'log'):
        setattr(ac_mod, attr, getattr(fake_ac, attr))
    sys.modules['ac'] = ac_mod

    acsys_mod = types.ModuleType('acsys')
    acsys_mod.CS = fake_acsys.CS
    acsys_mod.CM = fake_acsys.CM
    sys.modules['acsys'] = acsys_mod

    # AutoCam_sim_info maps named Windows shared memory at import time, which
    # only exists on Windows. Substitute an empty module to keep the import safe.
    sys.modules['AutoCam_sim_info'] = types.ModuleType('AutoCam_sim_info')

    # AutoCam.py builds a Win32 user32 handle at import (ctypes.WinDLL), which
    # does not exist off Windows; patch it with a stub that swallows the calls.
    real = getattr(ctypes, 'WinDLL', None)
    fake_user32 = types.SimpleNamespace(
        SendInput=types.SimpleNamespace(),
        MapVirtualKeyExW=lambda *a, **k: 0,
    )
    ctypes.WinDLL = lambda *a, **k: fake_user32
    return real


# populated by install(); imported by the test modules
fake_ac = None
fake_acsys = None
