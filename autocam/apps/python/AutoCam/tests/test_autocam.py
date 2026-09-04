# Offline smoke tests for AutoCam's pure logic.
#
# These run OUTSIDE Assetto Corsa. They stub `ac` / `acsys` / `AutoCam_sim_info`
# (see stubs.py) so the real app modules import on a non-Windows host, then
# exercise the functions the director actually calls at runtime.
#
# Run from the app directory:
#     python3 -m unittest discover -s tests -v
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(HERE)
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

import stubs  # noqa: E402
stubs.install()

import AutoCam  # noqa: E402  (the app module under test)
import AutoCamCar  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        # the stub's per-car state is module-global, so isolate each test
        stubs.fake_ac.reset()


class TestSafeName(Base):
    """safeName() strips characters that are unsafe in filenames/keys."""

    def test_allows_space_and_alnum(self):
        stubs.fake_ac.set_driver(0, 'Esotic Streaming')
        self.assertEqual(AutoCam.safeName(0), 'Esotic Streaming')

    def test_strips_punctuation(self):
        # `:`, `/`, `#` are not in the allowed set, digits/lower-case are kept
        stubs.fake_ac.set_driver(1, 'Driver#1/2:Test')
        self.assertEqual(AutoCam.safeName(1), 'Driver12Test')

    def test_empty_name_survives(self):
        stubs.fake_ac.set_driver(2, '')
        self.assertEqual(AutoCam.safeName(2), '')


class TestGapBetweenCars(Base):
    """gapBetweenCars() == track distance between two cars / average speed."""

    def setUp(self):
        super().setUp()
        stubs.fake_ac.set_track_length(4000.0)

    def test_returns_seconds_between_cars(self):
        # car0 ahead of car1 by 0.05 of a lap; avg speed 200 km/h
        stubs.fake_ac.set_car_state(
            0, LapCount=3, NormalizedSplinePosition=0.50, SpeedKMH=180.0)
        stubs.fake_ac.set_car_state(
            1, LapCount=3, NormalizedSplinePosition=0.45, SpeedKMH=220.0)
        # distance gap = 0.05 * 4000 = 200 m; avg speed = 200/3.6 m/s -> 3.6 s
        self.assertAlmostEqual(AutoCam.gapBetweenCars(0, 1), 3.6, places=5)

    def test_ignores_lap_difference(self):
        # same track position but different laps -> one full lap of distance
        stubs.fake_ac.set_car_state(
            0, LapCount=5, NormalizedSplinePosition=0.30, SpeedKMH=200.0)
        stubs.fake_ac.set_car_state(
            1, LapCount=4, NormalizedSplinePosition=0.30, SpeedKMH=200.0)
        # gap = 4000 m / (200/3.6) = 72 s
        self.assertAlmostEqual(AutoCam.gapBetweenCars(0, 1), 72.0, places=5)

    def test_bad_state_falls_back_to_999(self):
        stubs.fake_ac.set_car_state(0, LapCount=None)  # arithmetic blows up
        stubs.fake_ac.set_car_state(
            1, LapCount=4, NormalizedSplinePosition=0.30, SpeedKMH=200.0)
        self.assertEqual(AutoCam.gapBetweenCars(0, 1), 999.0)


class TestAutoCamCarClass(Base):
    """The AutoCamCar.AutoCamCar wrapper used to track a car slot."""

    def test_construct(self):
        stubs.fake_ac.set_driver(0, 'Esotic Streaming')
        stubs.fake_ac.set_car_name(0, 'ks_ferrari_488_gt3')
        car = AutoCamCar.AutoCamCar(0)
        self.assertEqual(car.slotId, 0)
        self.assertEqual(car.driverName, 'Esotic Streaming')
        self.assertEqual(car.carName, 'ks_ferrari_488_gt3')

    def test_check_reads_state(self):
        car = AutoCamCar.AutoCamCar(3)
        stubs.fake_ac.set_car_state(
            3, WorldPosition=(10.0, 0.0, 5.0), NormalizedSplinePosition=0.77)
        car.check()
        self.assertEqual(car.currentWorldPosition, (10.0, 0.0, 5.0))
        self.assertEqual(car.splineposition, 0.77)

    def test_distanceTo_same_car_returns_10002(self):
        a = AutoCamCar.AutoCamCar(1)
        b = AutoCamCar.AutoCamCar(1)
        self.assertEqual(a.distanceTo(b), 10002)  # self-comparison sentinel

    def test_distanceTo_pit_car_returns_10001(self):
        a = AutoCamCar.AutoCamCar(1)
        b = AutoCamCar.AutoCamCar(2)
        stubs.fake_ac.set_in_pit(1, True)
        self.assertEqual(a.distanceTo(b), 10001)  # pitted car sentinel

    def test_distanceTo_standing_car_returns_10000(self):
        a = AutoCamCar.AutoCamCar(1)
        b = AutoCamCar.AutoCamCar(2)
        stubs.fake_ac.set_car_state(1, SpeedKMH=0.0)
        self.assertEqual(a.distanceTo(b), 10000)  # standing car sentinel

    def test_distanceTo_normal_calculates(self):
        a = AutoCamCar.AutoCamCar(1)
        b = AutoCamCar.AutoCamCar(2)
        stubs.fake_ac.set_car_state(1, SpeedKMH=120.0)  # not "standing"
        a.currentWorldPosition = (0.0, 0.0, 0.0)
        b.currentWorldPosition = (3.0, 0.0, 4.0)  # hypot = 5.0
        self.assertEqual(a.distanceTo(b), 5.0)


if __name__ == '__main__':
    unittest.main()
