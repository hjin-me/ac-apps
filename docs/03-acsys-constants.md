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

## AutoCam 中各机位的实际使用

AutoCam 并不会无差别使用全部枚举。下表是**实际被导演循环用到或配置**的机位及其用途（⭐ 为常用）：

| 机位 | 值 | AutoCam 用途 | 出现位置 |
| :--- | :--- | :--- | :--- |
| `Cockpit`（座舱） | 0 | 动态追车·**追赶镜头**（`gap < chaseOnboardThreshold`）；维修区表；`battleCams` | `autoCam()` 战斗分支、`pitCameraSwitching` |
| `Car`（车外跟随） | 1 | **唯一会按车细分随车镜头的机位**（走 `carCameras.ini`）；维修区表；虚拟后视镜强制 | `autoCam()` Car 特判、`pitCameraSwitching`、`noDrivableCamWithVirtualMirror` |
| `Drivable`（可驾驶） | 2 | 默认表权重为 0；仅作为虚拟后视镜检测时**要禁用的目标** | `autoCam()` 虚拟后视镜分支 |
| `Track`（电视位） | 3 | **绝对主力**——默认 / 首圈 / 战斗 / 事故 / 超车全靠它 | `SetCamera(3, …)` 多处 |
| `Helicopter`（直升机） | 4 | 常规加权表、维修区表 | `cameraSwitching`、`pitCameraSwitching` |
| `OnBoardFree`（自由车载） | 5 | `countdownCam` 倒计时 | 倒计时逻辑 |
| `Free`（自由飞行） | 6 | 常规表权重为 0 | `cameraSwitching` |
| `Random`（随机） | 7 | 常规加权表 | `cameraSwitching` |

### 机位选择的分层逻辑（优先级从高到低）

1. **事故 Incident** → 强制 `SetCamera(3, "incident: …")`，锁 `incidentDuration` 秒。
2. **超车锁 Overtake Lock** → 强制 `SetCamera(3, "overtake: …")`，锁 5 秒。
3. **进站强制** → 聚焦车进维修道时，强制 `pitCameraSwitching["Guess1"]`。
4. **动态追车 Dynamic Chase**（战斗时）按 `bestBattleGap` 三档：
   - `gap < tvCamThreshold(0.3)` → **Track(3)**（并排/进攻）
   - `gap < chaseOnboardThreshold(0.8)` → **Cockpit(0)**（追赶）
   - 否则 → **Track(3)**
   - `forceTrackCamOnCloseBattles=1` 时恒 **Track(3)**。
5. **加权随机 Fallback**（无 override）：进维修道用 `pitCameraSwitching`，首圈用 `firstLapSwitching`，常规用 `cameraSwitching`。
6. **Car(1) 特判**：当 `nextCam==1`，从 `dicCars`（`carCameras.ini` 每车型镜头表）**随机挑随车镜头**；若后车距 2~100 秒则**强制选最后一个镜头**（拍后视/防守）。
7. **虚拟后视镜覆盖**：`noDrivableCamWithVirtualMirror=1` 时，检测到当前是 Cockpit(0)/Drivable(2) → **强制切到 Car(1)** 并设默认随车镜头。

### 当前生效的机位预设（AutoCam.ini）

| 键 | 值 | 说明 |
| :--- | :--- | :--- |
| `defaultCamera` | `3` | 开局/发车后默认（Track） |
| `countdownCam` | `5` | 倒计时（OnBoardFree） |
| `cameraSwitching` | `3^80^18\|0^10^10\|1^5^8\|4^2^5\|7^1^5` | 常规加权：Track 80 / Cockpit 10 / Car 5 / Helicopter 2 / Random 1 |
| `firstLapSwitching` | `3^1^10` | 首圈清一色 Track |
| `pitCameraSwitching` | `1^1^5\|0^1^5\|4^1^5` | Car / Cockpit / Helicopter |
| `battleCams` | `3^2^10\|0^1^10\|1^1^10` | Track 主导 + Cockpit/Car（**实际决策被动态追车分支覆盖，多为死配置**） |

> 一句话：真正主导全场的是 **Track(3) 电视位**（事故/超车/战斗/发车/加权回退都以它为核心）；**Car(1)**
> 是唯一会按车细分随车镜头的机位；**Cockpit(0)** 只在「追赶镜头」和维修区出现；**Dynamic Chase**
> 是唯一会在战斗中主动切到座舱机位的逻辑；`Helicopter(4)`/`Random(7)` 仅在常规加权表，
> `OnBoardFree(5)` 仅在倒计时，`Drivable(2)`/`Free(6)` 实际权重为 0（形同虚设）。

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
