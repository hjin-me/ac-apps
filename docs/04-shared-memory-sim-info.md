# 04 · 共享内存（sim_info / acpmf_*）

AC 在 Windows 命名空间下暴露三个**内存映射文件（Memory-Mapped File）**，供外部进程或 App 直接读取
实时遥测。Python 可用内置 `mmap` 模块按结构体布局读取。本项目 `AutoCam_sim_info.py` 即按此方式实现
（注释标注已适配 **AC 1.14.3**）。

## 三个共享对象

| 对象名 | 更新频率 | 内容 |
| :--- | :--- | :--- |
| `acpmf_physics` | 高（~300 Hz） | 底层车辆物理：速度、油门、刹车、转速、档位、悬挂行程、胎温等 |
| `acpmf_graphics` | 中（~60 Hz） | 比赛/HUD 数据：状态、会话类型、当前时间、名次、圈数、扇区、轮胎配方等 |
| `acpmf_static` | 低（~1 Hz） | 静态会话信息：车辆模型、赛道名、玩家名、最大转速、车辆数等 |

> 注意：共享内存**只暴露玩家车辆**，不包含其它在赛车辆。多车遥测需用 UDP 接口或第三方工具
> （如 AppCom / acTi）。这三个对象更新频率不同，健壮的读取器需分别轮询并同步（本项目在每帧
> `acUpdate` 中新建 `AutoCam_SimInfo()` 快照读取）。

## 读取方式（ctypes 结构体）

映射到内存后，用 `ctypes.Structure` 定义布局，`from_buffer` 读取。下面是本项目的精简示例：

```python
import mmap
import ctypes
from ctypes import c_int32, c_float, c_wchar

class SPageFilePhysics(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ('packetId', c_int32),
        ('gas', c_float),
        ('brake', c_float),
        ('gear', c_int32),
        ('rpms', c_int32),
        ('speedKmh', c_float),
        # ... 更多字段
    ]

class SPageFileGraphic(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ('packetId', c_int32),
        ('status', c_int32),      # AC_OFF/AC_REPLAY/AC_LIVE/AC_PAUSE
        ('session', c_int32),     # AC_PRACTICE/QUALIFY/RACE/HOTLAP/...
        ('currentTime', c_wchar * 15),
        ('completedLaps', c_int32),
        ('position', c_int32),
        ('sessionTimeLeft', c_float),
        ('normalizedCarPosition', c_float),
        # ... 更多字段
    ]

class SPageFileStatic(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ('_smVersion', c_wchar * 15),
        ('_acVersion', c_wchar * 15),
        ('numberOfSessions', c_int32),
        ('numCars', c_int32),
        ('carModel', c_wchar * 33),
        ('track', c_wchar * 33),
        ('playerName', c_wchar * 33),
        # ... 更多字段
    ]

mmap_physics  = mmap.mmap(0, ctypes.sizeof(SPageFilePhysics), "acpmf_physics")
mmap_graphics = mmap.mmap(0, ctypes.sizeof(SPageFileGraphic), "acpmf_graphics")
mmap_static   = mmap.mmap(0, ctypes.sizeof(SPageFileStatic), "acpmf_static")

physics  = SPageFilePhysics.from_buffer(mmap_physics)
graphics = SPageFileGraphic.from_buffer(mmap_graphics)
static   = SPageFileStatic.from_buffer(mmap_static)
```

## 常用字段

本项目 `autoCam()` 中实际使用到的 graphics / static 字段：

| 字段 | 说明 |
| :--- | :--- |
| `graphics.session` | 会话类型：0=Practice，1=Qualify，2=Race |
| `graphics.status` | 状态：`AC_REPLAY(1)` / `AC_LIVE(2)` 等。本项目用 `status == 1` 判定回放 |
| `graphics.sessionTimeLeft` | 会话剩余时间（秒） |
| `graphics.numberOfLaps` | 圈数 |
| `graphics.replayTimeMultiplier` | 回放倍速 |
| `static.isTimedRace` | 是否限时赛 |
| `static.hasExtraLap` | 是否有附加圈 |
| `static.trackSPlineLength` | 赛道 spline 长度 |

## 会话类型 / 状态常量

`AutoCam_sim_info.py` 顶部定义的常量：

```python
AC_OFF, AC_REPLAY, AC_LIVE, AC_PAUSE = 0, 1, 2, 3
AC_UNKNOWN = -1
AC_PRACTICE, AC_QUALIFY, AC_RACE, AC_HOTLAP = 0, 1, 2, 3
AC_TIME_ATTACK, AC_DRIFT, AC_DRAG = 4, 5, 6
AC_NO_FLAG, AC_BLUE_FLAG, AC_YELLOW_FLAG, AC_BLACK_FLAG = 0, 1, 2, 3
AC_WHITE_FLAG, AC_CHECKERED_FLAG, AC_PENALTY_FLAG = 4, 5, 6
```

## 关键注意事项

- 共享内存每帧新建映射对象开销较高，也可在 `acMain` 中初始化一次并在 `acUpdate` 复用。
- `SPageFileGraphic` 里的 `status != AC_LIVE`（如回放）时部分字段含义不同，需在逻辑中区分。
- 若要读取多车数据，必须转用 UDP 广播 / 第三方广播 App（本项目通过 `AppCom` 获取 running order）。

---

**参考**：

- [PyAccSharedMemory（ACC 共享内存 Python 读取器）](https://github.com/rrennoir/PyAccSharedMemory)
- [assettocorsasharedmemory（共享内存库文档）](https://github.com/mdjarv/assettocorsasharedmemory)
- [ACC Shared Memory 描述](https://github.com/ProBun/ACCSharedMemory)
