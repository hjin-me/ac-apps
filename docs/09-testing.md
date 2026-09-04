# 09 · 测试规范（离线 + 游戏内）

AutoCam 的测试分两层。**纯逻辑可以离线跑（不启动 AC）**；**只有真正调用 AC API 的"行为"必须进游戏**。
本文件约定离线测试的写法与边界，游戏内的部分引用 [08-development-tooling.md](08-development-tooling.md)。

## 核心结论：不一定全程游戏内测试

AC 的 `ac` / `acsys` 只在游戏运行时存在，因此任何直接调用它们的代码都无法在普通解释器里跑。
但 AutoCam 的**决策逻辑**（机位表解析、`gapBetweenCars`、`safeName`、打分、`dicKMH` EMA）是
纯计算，把 `ac` / `acsys` 打桩后即可离线验证。

### 可离线测试（纯逻辑）
- `AutoCam.gapBetweenCars()` —— 两车"时间差"计算
- `AutoCam.safeName()` —— 驱动名字符清洗（用于生成安全的 key/文件名）
- `AutoCamCar.AutoCamCar` 类 —— `__init__` / `check()` / `distanceTo()`（哨兵码 10000/10001/10002/10003 与 50× 车房加成）

### 必须在游戏内（stub 测不了真实效果）
- `ac.newApp` / `ac.addButton` / `ac.addSlider` 等建 UI
- `ac.getCarState` / `acsys.CS.*` 实时状态
- `ac.focusCar` / `ac.setCameraMode` 切镜头
- Windows 命名共享内存 `acpmf_*`（`AutoCam_sim_info.py` 的 mmap）
- `ctypes.WinDLL`/`SendInput` 全局快捷键

游戏内迭代用 **CSP Live reload**（见 [08-development-tooling.md](08-development-tooling.md)）缩短周期，
不必每次重开完整比赛。

## 离线测试怎么搭

测试放在 **`autocam/apps/python/AutoCam/tests/`**（与 App 源码同目录，`import AutoCam` 自动可解析）：

```
tests/
├── stubs.py           # 离线桩：ac / acsys / AutoCam_sim_info / ctypes.WinDLL
└── test_autocam.py    # 用例
```

### 为什么需要 `stubs.py`
直接 `import AutoCam.py` 在非 Windows 主机会崩，原因有二，`stubs.py` 的 `install()` 都处理了：

1. **`ctypes.WinDLL('user32')`**（AutoCam.py 顶部）—— Windows 专属；`install()` 把 `ctypes.WinDLL`
   替换成一个吞掉调用的假对象。
2. **`AutoCam_sim_info.py` 在模块级就 mmap 共享内存**（`mmap.mmap(0, size, "acpmf_physics")`）——
   那是 Windows 命名共享内存，非 Windows 上直接 `TypeError`；`install()` 用空模块顶替
   `AutoCam_sim_info`，避免执行到那行。

`install()` 先往 `sys.modules` 塞进假 `ac` / `acsys` / `AutoCam_sim_info`，再打桩 `ctypes.WinDLL`，
然后才能 `import AutoCam` / `import AutoCamCar`。

### 桩的使用约定
- **`stubs.install()` 必须在 `import AutoCam` 之前调用**。
- 通过 `stubs.fake_ac` 读写可控状态（`set_car_state(car, LapCount=.., SpeedKMH=..)`、
  `set_driver`、`set_car_name`、`set_track_length`、`set_in_pit`、`set_in_pitline`）。
- **桩状态是模块级全局**，会跨用例泄漏 → 每个用例前调用 `stubs.fake_ac.reset()`（测试基类 `Base.setUp` 已做）。
- 不要写 `from stubs import fake_ac` 后再 `install()`——那会绑定到 `None`；要 `import stubs` 后用
  `stubs.fake_ac`。

## 运行方式

用 stdlib `unittest`，**零依赖**（pytest 未安装也无需装）：

```bash
cd autocam/apps/python/AutoCam
python3 -m unittest discover -s tests -v   # 全部
python3 -m unittest tests.test_autocam -v  # 单模块
```

## 编写规范
1. 优先测**真实运行时**用到的函数（AutoCam.py 自己那份 `safeName`/`gapBetweenCars`，而非
   `AutoCamCar.py` 里的重复副本——后者是遗留死代码）。
2. 一个用例只鉴证一个行为；预期值手工算好写死（如 gap=3.6s），不要用被测函数自身去算。
3. 环境无关：测试用 `python3` 跑；被测源码须保持 AC 的 Python 2.x 兼容（不要引入 Py3 专属语法）。
4. 新纯逻辑应尽量**抽成独立函数**再测，避免只能靠桩戳穿积木式的大函数。

## 待办（如果继续扩展）
- 把机位表 `cam^usage^delay` 解析从 `ReadSettings` 抽成纯函数并加用例（当前是内联在函数里，测不到）。
- 把战斗打分 `pow(positionDecay, pos)` / 事故判定的 `dicKMH` 基准 EMA 抽函数覆盖。
- 清理 `AutoCamCar.py` 与 `AutoCam.py` 重复的 `safeName` / `gapBetweenCars`（重复让测试目标不清晰）。
