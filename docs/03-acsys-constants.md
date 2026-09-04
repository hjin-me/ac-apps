# 03 · `acsys` 常量：车辆状态与相机模式

> `acsys` 模块提供 `ac.getCarState()` 用的状态标识符 `acsys.CS`，以及相机模式枚举 `acsys.CM`。
> 使用方式：`import ac, acsys` 后 `ac.getCarState(0, acsys.CS.SpeedKMH)`。

## `acsys.CS` —— 车辆状态标识符

`ac.getCarState(<CAR_ID>, <INFO_ID>)` 的第二个参数。下面是文档与社区常见、且本项目实际用到的值
（标注 ⭐），以及其它常见值。

### 本项目 AutoCam.py 实际使用的

| 常量 | 类型 | 说明 |
| :--- | :--- | :--- |
| `acsys.CS.SpeedKMH` ⭐ | float | 当前速度（km/h） |
| `acsys.CS.LapTime` ⭐ | float | 当前圈用时（ms）；跨线或重置时归零 |
| `acsys.CS.LapCount` ⭐ | int | 当前圈数 |
| `acsys.CS.NormalizedSplinePosition` ⭐ | float | 车辆在赛道 spline 上的归一化位置（0=起跑线，1=终点线） |
| `acsys.CS.PerformanceMeter` ⭐ | float | 距个人最佳圈的时间差（秒） |
| `acsys.CS.SuspensionTravel` ⭐ | 4D | 悬挂行程（每轮） |
| `acsys.CS.RaceFinished` ⭐ | int | 是否完赛 |

### 其它常见值

| 常量 | 说明 |
| :--- | :--- |
| `SpeedMS` | 速度（m/s） |
| `SpeedMPH` | 速度（mph） |
| `Gas` / `Brake` / `Clutch` | 油门 / 刹车 / 离合（0–1） |
| `Gear` | 当前档位 |
| `RPM` | 转速 |
| `SteeringAngle` | 转向角 |
| `LastLap` / `BestLap` | 上一圈 / 最佳圈用时 |
| `Position` | 当前名次 |
| `IsInPit` | 是否进站（注意与 `ac.isCarInPitlane()` 区别） |
| `WorldPosition` | 世界坐标（3D 向量） |
| `Velocity` / `Acceleration` | 速度 / 加速度向量 |
| `AngularVeloctiy` | 角速度向量 |
| `TyreWear` / `TyreTemp` | 轮胎磨损 / 温度（FL/FR/RL/RR） |

> 轮胎相关的取值需要第三个参数，例如 `ac.getCarState(0, acsys.CS.TyreWear, acsys.CS.FL)`。

### 备注

- `NormalizedSplinePosition` 在点到点（山道/爬坡）场地可能不能唯一标识位置，因为进站段与
  终点后段同样有 spline 值，计时时应结合跨线事件处理。
- `LapTime` 跨线或重置时会归零，因此自定义计时要结合 spline 位置在多个测量点间追踪。

## `acsys.CM` —— 相机模式

相机模式枚举，用于 `ac.setCameraMode(m)` / `ac.getCameraMode()`。本项目 AutoCam.py 注释中给出了
完整对照：

| 常量 | 值 | 说明 |
| :--- | :--- | :--- |
| `acsys.CM.Cockpit` | 0 | 座舱（车载）视角 |
| `acsys.CM.Car` | 1 | 车外跟随视角 |
| `acsys.CM.Drivable` | 2 | 可驾驶（自由）视角 |
| `acsys.CM.Track` | 3 | Track / TV 机位（广播）视角 |
| `acsys.CM.Helicopter` | 4 | 直升机视角 |
| `acsys.CM.OnBoardFree` | 5 | 车载自由视角 |
| `acsys.CM.Free` | 6 | 自由摄像机 |
| `acsys.CM.Random` | 7 | 随机 |
| `acsys.CM.ImageGeneratorCamera` | 8 | 图像生成相机 |
| `acsys.CM.Start` | 9 | 起跑相机 |

在广播导演类 App 中常用的映射：

```python
# 驾驶/座舱        0    acsys.CM.Cockpit
# 车外跟随         1    acsys.CM.Car
# 可驾驶自由       2    acsys.CM.Drivable
# TV 广播机位      3    acsys.CM.Track
```

## 用法示例

```python
import ac
import acsys

car = 0                              # 0 始终是玩家车辆
speed = ac.getCarState(car, acsys.CS.SpeedKMH)
lap   = ac.getCarState(car, acsys.CS.LapCount)
pot   = ac.getCarState(car, acsys.CS.NormalizedSplinePosition)

ac.setCameraMode(acsys.CM.Track)     # 切到 TV 机位
ac.focusCar(car)                      # 聚焦某辆车
```

---

**参考**：

- [ACPythonDocumentation（`acsys.CS` 常量说明）](https://www.scribd.com/document/629250993/ACPythonDocumentation)
- 本项目 `AutoCam.py` 中相机模式注释与 `acsys.CS.*` 调用
