# 05 · 相机切换、聚焦车辆与排名控制

本项目（AutoCam）的核心是 AI 导播：根据遥测、间距、事故，动态切换聚焦车辆与相机机位。这里汇总
相关的 `ac` API 与常用模式。

## 相机模式

```python
import ac
import acsys

ac.setCameraMode(acsys.CM.Track)   # 切到 TV 机位
mode = ac.getCameraMode()          # 读取当前模式
```

常见机位（完整枚举见 [03](03-acsys-constants.md#acsyscm--相机模式)）：
`Cockpit(0)` 座舱、`Car(1)` 车外跟随、`Drivable(2)` 可驾驶自由、`Track(3)` TV/广播。

## 聚焦车辆

```python
ac.focusCar(CAR_ID)        # 聚焦某辆车
focused = ac.getFocusedCar()   # 当前聚焦车辆
```

聚焦后，若搭配 `ac.isCameraOnBoard(CAR_ID)` 可判断当前是否在车载视角，进而决定是否切到外部机位。

## 车辆相机（F6 切换）

```python
ac.setCameraCar(CAMERA_ID, CAR_ID)   # 设置 F6 相机索引（绝对或相对）
count = ac.getCameraCarCount(CAR_ID) # 该车的 F6 相机数量
```

本项目按车辆型号从 `carCameras.ini` 读取每个 SKIN 的相机编号与权重，在 `battleCamSwitching` /
`pitCameraSwitching` / `firstLapSwitching` 等字典中配置“机位 + 权重 + 停留时长”。

## 相机与聚焦的组合用法

```python
def focus_tv(car):
    ac.focusCar(car)
    ac.setCameraMode(acsys.CM.Track)   # 广播机位
    lastFocusSwitch = time.clock()
    cameraSwitchDelay = 8.0            # 锁定 8 秒
```

## 车辆信息与排名

```python
count = ac.getCarsCount()                       # 场上车辆数
name  = ac.getCarName(car)                      # 车辆名
pos   = ac.getCarRealTimeLeaderboardPosition(car)  # 实时排名（P1 为 0 或 1，依版本）
speed = ac.getCarState(car, acsys.CS.SpeedKMH)
lap   = ac.getCarState(car, acsys.CS.LapCount)
pot   = ac.getCarState(car, acsys.CS.NormalizedSplinePosition)
inpit = ac.isCarInPitlane(car)
conn  = ac.isConnected(car)
```

> 本项目 `getPosition(car)` 优先使用广播 App（`AppCom.runningorder`）传递的 running order，
> 失败时回退到 `ac.getCarRealTimeLeaderboardPosition(car)`，从而支持离线/本地回放。

## 常见逻辑模式（AutoCam）

- **间距计算（gap）**：`gapBetweenCars` 结合两车 `NormalizedSplinePosition` 与赛道长度换算距离。
- **事故检测**：记录赛道某点（`keyPoTKMH = "Car%sKMH%0.3f" % (name, pot)`）的正常速度，当某车
  在高速区（>60 km/h 正常速度）跌破 25 km/h 时判为事故，`ac.focusCar` + `setCameraMode(Track)`
  并锁定 `incidentDuration` 秒。
- **超车锁定**：比较前后帧 `getPosition`，名次上升则锁定 5 秒。
- **战斗判定**：判断当前聚焦车与前后车的 gap 是否小于 `battleGap`，聚焦车是否在缠斗。
- **TV 机位强制**：缠斗且 gap < `closeBattleThreshold` 时，强制 `setCameraMode(acsys.CM.Track)`。

## 会话状态读取

优先用 `sim_info`（见 [04](04-shared-memory-sim-info.md)）判断会话类型/状态：

```python
sim_info_obj = AutoCam_sim_info.AutoCam_SimInfo()
bIsQually  = sim_info_obj.graphics.session == 1
bIsRace    = sim_info_obj.graphics.session == 2
inReplay   = sim_info_obj.graphics.status == AC_REPLAY
```

---

**参考**：

- [ACPythonDocumentation](https://www.scribd.com/document/629250993/ACPythonDocumentation)
- 本项目 `AutoCam.py` 中 `autoCam()` / `getPosition()` / 相机切换逻辑
