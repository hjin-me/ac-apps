# AutoCam — Assetto Corsa AI 广播导演 App

`autocam/` 是本仓库**唯一权威（canonical）的可运行版本**，是一个跑在 Assetto Corsa（AC，神力科莎）
游戏内的 Python 2.x 插件。它像一个**AI 转播导演**：读取实时遥测，自动切换机位（`ac.setCameraMode`）
与聚焦车手（`ac.focusCar`），把同场比赛中追逐、超车、事故、进站、头车争位等情节，用接近电视转播的
镜头语言呈现给直播或录像。

> 与 `_ref/` 的关系见下文「前身背景」。本目录内容是唯一权威；`_ref/` 只作只读参考。

---

## 目录

- [前身背景](#前身背景)
- [目录结构](#目录结构)
- [功能点总览](#功能点总览)
- [安装与启用](#安装与启用)
- [相机模式（acsys.CM）](#相机模式-acsyscm)
- [配置文件与分层加载](#配置文件与分层加载)
- [机位表格式 `cam^usage^delay`](#机位表格式-camusagedelay)
- [配置项详解](#配置项详解)
- [per-car 机位权重（carCameras.ini）](#per-car-机位权重-carcamerasini)
- [离线测试](#离线测试)
- [已知限制与遗留配置](#已知限制与遗留配置)

---

## 前身背景

AutoCam 不是从零写的，它有一条清晰的血脉：

| 阶段 | 来源 | 说明 |
| :--- | :--- | :--- |
| **概念** | **Minolin 的 ActionCam** | 「自动选机位/聚焦」这一导演思路的最早公开实现。 |
| **原作者** | **Dave / Esotic** | 在 ActionCam 基础上做了 **Auto Cam V1.6**（本类是 `autoCam()` 导演循环的雏形），发布于 Overtake.gg。 |
| **增强 fork** | **autocam-main**（第三方增强版） | 重构了导演算法（`reji` / 导演循环），加入事故检测、超车锁、动态追车、本地计分板兜底等新功能，并重做了游戏内设置 UI。 |
| **本目录** | **`autocam/`（本项目）** | 从增强 fork 同步而来，剔除 OBS 链路、打上 4 个 bug 修复，作为唯一权威版本。 |

本目录的两个前身在仓库里被**原样快照**在 `_ref/`（只读、git 跟踪、禁止改动）：

- `_ref/AutoCam_V1.6/` —— 原版 Esotic Auto Cam V1.6。
- `_ref/autocam-main/` —— 增强版 fork（含 `obsremote`/`websocket` 等本目录**故意排除**的模块）。

### 为什么有两个版本？本目录的取舍

`autocam-main` 增强版功能更多，但带了若干问题和一条被禁用的 OBS 链路。`autocam/` 的处理是：

1. **同步功能**：把增强版的全部核心改动搬进来（事故检测、超车锁、按位次加权的战斗打分、
   动态追车、`getCarRealTimeLeaderboardPosition` 计分板兜底、重做的设置 UI、`WriteSettings`）。
2. **剔除 OBS**：`obsremote`/`websocket` 相关 import 与文件被注释/移除，OBS 集成只剩历史。
3. **修 4 个 bug**（见下）。
4. **`_ref/` 只读保留**：便于随时对照上游；本目录改动不反写 `_ref/`。

### 移植后打的 4 个 bug 修复

| 修复 | 问题 | 处理 |
| :--- | :--- | :--- |
| **A** | 战斗判定硬编码 `50.0`，导致真正声明的 `battleKMHPercentDiff = 15.0` 从未被使用 | 改成 `abs((k1-k2)/k1)*100 < battleKMHPercentDiff`，即「战斗」= 两车速度差在 15% 以内 |
| **B** | `acMain` 在 `ReadSettings` **之后**又硬编码 `windowx = 280` / `windowy = 530`，把用户保存的窗口尺寸覆盖掉 | 删除这两行，窗口尺寸恢复由 `AppWidth`/`AppHeight` 控制 |
| **C** | `WriteSettings()` 写回的是硬编码机位表，点「保存」会把按服务器/按 IP 调好的机位表冲掉 | 在 `ReadSettings` 里保留原始机位表字符串（`rawCameraSwitching` 等），`WriteSettings` 写回这些**原始值** |
| **D** | `dicKMH` 速度基准只在**排位赛**里写入，纯比赛赛制永不建基准 → 事故检测、掉速检测永不触发 | 基准更新/新建两个闸门从 `bIsQually and lapsSincePit == 1` 改为 `lapCount > 0 and speedKMH > 30.0`，让基准在比赛里也能自适应 |

---

## 目录结构

```
autocam/
├── apps/python/AutoCam/        # App 模块（AC 从这里加载）
│   ├── AutoCam.py              # 唯一权威源码：acMain/acUpdate/acShutdown + 导演循环 autoCam()
│   ├── AutoCamCar.py           # AutoCamCarCar 封装（一名车手的 slot 包装器）
│   ├── AutoCam_sim_info.py     # 读取 Windows 共享内存（acpmf_physics/graphics/static）
│   ├── AppCom.py               # 与广播 App 的共享全局（runningorder / event / ABot）
│   ├── win32con.py             # Windows 常量（快捷键用）
│   ├── AutoCam.ini             # 默认配置（含机位表、所有 [SETTINGS] 键）
│   ├── carCameras.ini          # per-car 机位权重
│   ├── PIT_ENTRY/              # 各赛道进站位置（当前逻辑已停用，仅保留）
│   ├── stdlib/ stdlib64/       # 平台 .pyd 桩（按 32/64 位注入 sys.path）
│   ├── tests/                  # 离线测试（stubs.py + test_autocam.py）
│   └── backup/                 # 每次启动时 self-copy 的「上一份可用副本」（gitignored）
└── content/gui/icons/          # Auto Cam_ON.png / Auto Cam_OFF.png（App 图标）
```

**加载方式**：AC 从 `apps/python/<AppName>/` 加载，`<AppName>` 就是目录名 `AutoCam`。需要把本目录
的 `apps/` 与 `content/` 放进游戏的根目录（见「安装与启用」）。

---

## 功能点总览

导演循环 `autoCam()` 每帧（由 `acUpdate` 调用）执行，优先级从高到低：

1. **事故 / 打转检测（Incident Detection）**
   实时遥测扫描；某车在高速区（基准速度 > `incidentMinNormalSpeed`）突然低于 `incidentMaxSpeed`
   （默认 25 km/h），判定为事故。立即用**电视位（Track = 3）**锁定该车 `incidentDuration` 秒，绝不漏读。

2. **超车锁（Overtake Lock）**
   逐帧对比前一轮行驶进度（`prevCarPositions`），检测到某车**位次提升**（`curr_pos < prev_pos`），
   锁定聚焦该车 5 秒并切到电视位，把超车瞬间呈现在镜头里。

3. **领跑优先的战斗打分（Battle Scoring）**
   按 `AppCom.runningorder`（或 `getCarRealTimeLeaderboardPosition` 兜底）得到的当前名次，逐对相邻车
   用 `gapBetweenCars()` 算秒差，小于 `battleGap` 记为一场「战斗」。
   每场战斗打分：`gap_score × pow(positionDecay, pos)` —— **越靠前、间隔越紧的分越高**，模拟 F1 电视
   优先拍头车的逻辑；当前聚焦车有 1.15 倍加权，防止镜头来回乱跳。
   补充判定：两车速度差须在 `battleKMHPercentDiff`（15%）内才算真在缠斗。

4. **动态追车镜头（Dynamic Chase Cam）**
   战斗中按秒差 `bestBattleGap` 分档选择机位：
   - `< tvCamThreshold`（0.3s，并排/进攻）→ 切 **Track/TV** 位，全景看超车。
   - `< chaseOnboardThreshold`（0.8s，追赶）→ 切 **Cockpit(0)** 位，从车手视角体验追逐。
   - 其余 → Track 位。
   可完全关闭（`dynamicChaseCam = 0`）退化为始终 Track。

5. **掉速 / off-pace 检测**
   用 `dicKMH`（按「车名 + 归一化赛道位置」建的**滚动速度基准 EMA**，`(旧×9 + 新)/10`）判断某车是否
   明显低于正常速度并持续 `offPaceSwitchDelay` 秒，作为 overrideCar 拉过去看。基准只在
   `lapCount > 0 && speedKMH > 30.0` 时更新，排除暖胎圈与静止车况。

6. **维修区 / 进站机位（Pit）**
   - 聚焦车进站时强制用 `pitCameraSwitching` 首项。
   - 有车正在维修道（pit lane）以 `minPitKMH`~`maxPitKMH` 之间行驶，且 PoT/KMH 有变化（不"卡住"）时，
     拉过去切到进站机位。

7. **首圈机位（First Lap）**
   聚焦车 `LapCount < 1` 时启用 `firstLapSwitching` 独立机位表（默认清一色 Track，稳定呈现发车）。

8. **倒计时镜头（Countdown）**
   发车前（`LapTime == 0` 且车辆仍在维修道）用 `countdownCam`；倒计时期间依次聚焦后排车手制造"扫场"
   效果。开跑后切回 `defaultCamera`。

9. **排位赛专注（Qualifying）**
   排位赛里找 `PerformanceMeter` 为负、处于赛道后段（`PoT` 最大）的车手聚焦，捕捉做圈速瞬间。

10. **末段冲线（Finishing）**
    领跑车距终点 800m 内、或比赛收尾时，优先聚焦接近冲线的车。

11. **通用退路（Weighted Camera Fallback）**
    没有任何 override 时，用 `cameraSwitching` 加权随机选下一个机位；`nextCam == 1`（Car 位）时进一步
    结合 `carCameras.ini` 选具体随车机位，并"车距 2~100s 内有后车"时强制最后机位（拍后视/防守）。

12. **虚拟后视镜避让（Virtual Mirror）**
    `noDrivableCamWithVirtualMirror = 1` 时禁止 `0/2`（Cockpit/Drivable）机位，改用第一个 Car 位，
    避免虚拟后视镜遮挡。

13. **游戏内设置 UI + 保存**
    窗口内含滑条/勾选框（战斗间隔、前位衰减、切换间隔、事故时长、动态追车、强制 TV、verbosity），
    点 **SAVE CONFIGURATION** 调 `WriteSettings()` 写回 `AutoCam.ini`（保留用户自定义机位表）。

14. **快捷键**
    - `Ctrl+F6`：切换 `cameraSwitchingEnabled`。
    - `Ctrl+F7`：切换 `driverSwitchingEnabled`。

15. **广播集成 / 排他名单**：`skipDrivers`（按星期几可配）、`preferredDrivers`（专属聚焦）、
    `promoText`（发车时配合 OBS 广播聊天公告）。OBS websocket 链路已剔除，仅保留对 `obs64.exe` 的探测。

---

## 安装与启用

1. 把本目录的 `apps/` 与 `content/` 并入 AC 根目录，使 `Assetto Corsa\apps\python\AutoCam\` 与
   `Assetto Corsa\content\gui\icons\Auto Cam_*.png` 就位。
2. 用 **Content Manager** 或官方启动器，进 `Settings > Assetto Corsa > Apps`，勾选 **AutoCam**。
3. 进游戏后从右侧常驻 App 栏呼出 AutoCam 窗口，点顶部 **AutoCam ACTIVE/INACTIVE** 切换启停。
4. 界面调整参数后点 **SAVE CONFIGURATION** 会写入 `AutoCam.ini`。

> 运行时代码是 Python **2.x**，依赖 AC 内置 `ac`/`acsys` 模块，**只能在游戏内运行**；
> 不能在系统 Python 里直接 `import`（见「离线测试」）。

---

## 相机模式（acsys.CM）

| 值 | 常量 | 说明 |
| :--- | :--- | :--- |
| 0 | `acsys.CM.Cockpit` | 座舱视角 |
| 1 | `acsys.CM.Car` | 车载镜头（具体哪个需再选，见 `carCameras.ini`） |
| 2 | `acsys.CM.Drivable` | 可驾驶视角 |
| 3 | `acsys.CM.Track` | **赛道/电视全景位**（转播主力） |
| 4 | `acsys.CM.Helicopter` | 直升机俯拍 |
| 5 | `acsys.CM.OnBoardFree` | 自由车载位 |
| 6 | `acsys.CM.Free` | 自由飞行位 |
| 7 | `acsys.CM.Random` | 随机位 |
| 8 | `acsys.CM.ImageGeneratorCamera` | 图像生成位 |
| 9 | `acsys.CM.Start` | 起点位 |

---

## 配置文件与分层加载

`acMain` 会**两次**调用 `ReadSettings`，后加载的覆盖先加载的：

1. 默认配置：`apps\python\AutoCam\AutoCam.ini`（`SettingsINI` 常量）。
2. 按服务器 IP 的配置：`apps\python\AutoCam\<服务器IP，小数点->下划线>.ini`；离线（IP 为空）用
   `127_0_0_1.ini`。

因此**按服务器个性化**的机位表/参数写在对应 IP 的 `.ini` 里即可，无需改动默认文件。

保存机制：`WriteSettings()` 只写默认 `AutoCam.ini`。关键修正（修复 C）：写回的是 `rawCameraSwitching` /
`rawPitCameraSwitching` / `rawBattleCams` / `rawFirstLapSwitching`（从 INI 读到的原始字符串），
**不会**覆盖用户调好的机位表。

---

## 机位表格式 `cam^usage^delay`

四个机位表统一使用管道分隔、以 `^` 分三段：

```
cam^usage^delay|cam^usage^delay|...
```

| 段 | 含义 |
| :--- | :--- |
| `cam` | 相机模式编号（见上表 `acsys.CM.*`） |
| `usage` | **权重**。例如 80 → 展开成 80 份 `GuessN` 条目，值越大被随机选中的概率越高 |
| `delay` | 该机位保持的秒数（`cameraSwitchDelay`） |

例如默认 `cameraSwitching = 3^80^18|0^10^10|1^5^8|4^2^5|7^1^5`：
- `3`（Track）权重 80、保持 18s —— **主导机位**；
- `0`（Cockpit）权重 10、10s；`1`（Car）权重 5、8s；
- `4`（Helicopter）权重 2、5s；`7`（Random）权重 1、5s。

解析产物是加权表：`cameraSwitching["GuessN"]`（机位）与 `cameraDelay["DelayN"]`（保持秒数），
随机从 `1..长度` 里选一项。四个表：

| 表（INI 键） | 作用场景 |
| :--- | :--- |
| `cameraSwitching` | 常规行驶机位 |
| `firstLapSwitching` | 首圈（`LapCount < 1`）机位 |
| `pitCameraSwitching` | 维修区 / 进站机位 |
| `battleCams` | 触发战斗时的机位 |

> 注：`battleCams` 会被 `ReadSettings` 解析为 `battleCamSwitching`/`battleCamDelay`，但当前导演循环的
> 战斗机位主要由「动态追车 / 强制 TV」分支决定，`battleCams` 更多作为兜底资料保留（见「已知限制」）。

---

## 配置项详解

下表覆盖 `AutoCam.ini` 中 `[SETTINGS]` 段全部键。默认值以随附 `AutoCam.ini` 为准。
多数设为 `1` 开启、`0` 关闭。

### 开关与基本控制

| 键 | 默认 | 说明 |
| :--- | :--- | :--- |
| `AutoCamActive` | `1` | 启动时是否启用 AutoCam（=0 相当于同时关闭机位与车手切换）。窗口顶部按钮可切换。 |
| `defaultCamera` | `3` | 开局/发车后默认机位（Track）。 |
| `countdownCam` | `5` | 发车倒计时用机位；`-1` 表示禁用倒计时逻辑。 |
| `cameraSwitchingEnabled` | `1` | 是否允许机位切换（`Ctrl+F6` 切换）。 |
| `driverSwitchingEnabled` | `1` | 是否允许车手/聚焦切换（`Ctrl+F7` 切换）。 |
| `hideicon` | `1` | 隐藏 AC 任务栏图标（映射为 `HideIcon`）。 |
| `appwidth` / `appheight` | `280` / `530` | App 窗口尺寸（`AppWidth`/`AppHeight`）。保存后生效；`acMain` 会把这些值钳制到不小于 `280×530`（修复 B 已保证不被硬编码覆盖，另加最小下限防止内容被裁切）。 |
| `backgroundopacity` | `0.5` | 窗口背景不透明度 0~1（`backgroundOpacity`）。 |
| `drawborder` | `0` | 是否绘制窗口边框（`drawBorder`）。 |
| `verbose` | `0` | 日志级别：`0` 静默、`1` 详细、`4` 最详细（含 strErr 调试）。UI 勾选框在 `1`/`4` 间切换。 |

### 机位表（见「机位表格式」）

| 键 | 默认 | 说明 |
| :--- | :--- | :--- |
| `cameraSwitching` | `3^80^18\|0^10^10\|1^5^8\|4^2^5\|7^1^5` | 常规加权机位表（转播预设）。 |
| `firstLapSwitching` | `3^1^10` | 首圈机位表。 |
| `pitCameraSwitching` | `1^1^5\|0^1^5\|4^1^5` | 维修区机位表。 |
| `battleCams` | `3^2^10\|0^1^10\|1^1^10` | 战斗机位表（当前主要作为兜底）。 |

### 切换节奏

| 键 | 默认 | 说明 |
| :--- | :--- | :--- |
| `driverSwitchDelay` | `15` | 聚焦车保持多久后再寻找下一个聚焦对象（秒）。 |
| `cameraSwitchDelay` | `10` | 默认机位切换间隔（秒），通常被各机位表里的 `delay` 覆盖。 |
| `minSwitchDelay` | `5.0` | 任一聚焦切换之间的最小间隔（秒），防止频繁跳变。 |
| `offPaceSwitchDelay` | `240.0` | 判定某车「掉速」需持续多少秒才切过去看（秒）。 |
| `minPitKMH` | `40.0` | 维修道内车速高于此值才可能被视为「正在移动」的目标（km/h）。 |
| `maxPitKMH` | `85.0` | 维修道内车速低于此值才可能被切过去（km/h）。 |

### 战斗与导播逻辑

| 键 | 默认 | 说明 |
| :--- | :--- | :--- |
| `battleGap` | `0.5` | 判定「战斗」的秒差阈值：两车间隔小于此值算一场缠斗。 |
| `positionDecay` | `0.92` | 前位优先级衰减因子。打分 `pow(positionDecay, pos)`；**越小越偏眼前排**（如 `0.88` 会更专注 P1–P5）。 |
| `leadersOverClosest` | `1` | 是否偏重前排战斗（「Prefer Leader Battles」勾选框状态）。前位加权主要由 `positionDecay` 决定。 |
| `forceTrackCamOnCloseBattles` | `1` | 战斗时是否强制电视位（关闭后动态追车不生效，见下）。 |
| `closeBattleThreshold` | `0.35` | 战斗间隔低于此值强制电视位的阈值（当前逻辑实际用 `tvCamThreshold`，见「已知限制」）。 |
| `noDrivableCamWithVirtualMirror` | `1` | 检测到虚拟后视镜时禁止 Cockpit/Drivable（`0/2`）位，改用第一个 Car 位。 |

> `battleKMHPercentDiff`（`15.0`）是战斗速度差上限的**硬编码常量**，当前不从 INI 读取；改动需改源码第 216 行。

### 动态追车（Dynamic Chase Cam）

| 键 | 默认 | 说明 |
| :--- | :--- | :--- |
| `dynamicChaseCam` | `1` | 启用动态追车镜头（随 `bestBattleGap` 分档选机位）。 |
| `tvCamThreshold` | `0.3` | 秒差**低于**此值（并排/进攻）→ 切 Track/TV 位。 |
| `chaseOnboardThreshold` | `0.8` | 秒差**低于**此值（追赶）→ 切 Cockpit 位；否则回 Track 位。 |

### 事故 / 打转检测

| 键 | 默认 | 说明 |
| :--- | :--- | :--- |
| `incidentDetection` | `1` | 开启事故/打转检测。 |
| `incidentMinNormalSpeed` | `60.0` | 判定基准：只有「正常基准速度 > 此值」的车才纳入事故检测（排除低速/慢车区）。 |
| `incidentMaxSpeed` | `25.0` | 触发阈值：当前车速 **低于**此值判定为事故。 |
| `incidentDuration` | `8.0` | 事故发生后锁定该车电视位的时长（秒）。 |

### 车队 / 广播集成

| 键 | 默认 | 说明 |
| :--- | :--- | :--- |
| `skipdrivers` | `Esotic Streaming\|Place Holder\|TV CREW\|TV CREW 2\|TV CREW 3\|pit_TV\|TV1\|TV2` | 管道分隔的**排除名单**（主持/摄影/观众车），这些司机不参与聚焦。 |
| `preferredDrivers` | （注释） | 若会话中存在，则只聚焦这些车手（`piped` 分隔）。默认注释。 |
| `promoText` | （注释） | 发车时配合 OBS/广播发送的聊天公告文本（探测到 `obs64.exe` 时发送）。默认注释。 |

**按星期几排除名单**：`ReadSettings` 会优先寻找 `Monday`~`Sunday` 键（星期几英文名）。例如
`Saturday = <名单>`，当天就用它代替 `skipDrivers`。未配置那一天则回退到 `skipdrivers`。

### 配置样例

```ini
[SETTINGS]
AutoCamActive = 1
defaultCamera = 3
verbose = 0

; 常规机位表：Track 主导，穿插 Cockpit / Car / Helicopter / Random
cameraSwitching = 3^80^18|0^10^10|1^5^8|4^2^5|7^1^5
firstLapSwitching = 3^1^10
pitCameraSwitching = 1^1^5|0^1^5|4^1^5
battleCams = 3^2^10|0^1^10|1^1^10

; 战斗与导播
battleGap = 0.5
positionDecay = 0.92
leadersOverClosest = 1
forceTrackCamOnCloseBattles = 1

; 动态追车
dynamicChaseCam = 1
tvCamThreshold = 0.3
chaseOnboardThreshold = 0.8

; 事故检测
incidentDetection = 1
incidentMinNormalSpeed = 60.0
incidentMaxSpeed = 25.0
incidentDuration = 8.0

; 维修区 / 切换节奏
minPitKMH = 40.0
maxPitKMH = 85.0
minSwitchDelay = 5.0
driverSwitchDelay = 15
cameraSwitchDelay = 10
offPaceSwitchDelay = 240.0

; 界面外观
hideicon = 1
appwidth = 280
appheight = 530
backgroundopacity = 0.5
drawborder = 0

skipdrivers = Esotic Streaming|Place Holder|TV CREW|TV CREW 2|TV CREW 3|pit_TV|TV1|TV2
```

---

## per-car 机位权重（carCameras.ini）

`carCameras.ini` 为**每种车型**指定 Car 位（`acsys.CM.Car = 1`）下具体用哪个随车镜头，格式
`<cameraIndex>^<weight>`（无 delay）：

```
[SETTINGS]
ks_ferrari_488_gt3 = 2^1|0^1|1^1|3^1|4^1|5^1
gp_2026_sf26 = 2^1|0^1|1^1|3^1|4^1|5^1
```

- `cameraIndex` 是该车质心（car model）提供的第几个镜头（`ac.setCameraCar(cam, car)`）；因车而异，
  例如 `bmw_m3_e30_dtm` 的注释说明 0=车顶前方、1=左前轮、2=驾驶位朝前、3=副驾仪表、4=副驾拍车手、5=车顶拍尾。
- `weight` 同机位表，越大越常被选中。
- 首次运行若某车未收录，`ReadCarCameras` 会用 `0^1|1^1|2^1|...` 自动补写一行。
- 当 `nextCam == 1`（Car 位）时，导演循环用该表的 `GuessN` 随机选随车镜头；若**后车距 2~100 秒**，
  强制选最后一个镜头（拍后视 / 防守）。

---

## 离线测试

纯逻辑可离线跑（打桩 `ac`/`acsys`/`AutoCam_sim_info`/`ctypes.WinDLL`），无需启动 AC：

```bash
cd autocam/apps/python/AutoCam
python3 -m unittest discover -s tests -v   # 全部
python3 -m unittest tests.test_autocam -v  # 单模块
```

文件：`tests/stubs.py`（离线桩）+ `tests/test_autocam.py`（覆盖 `safeName`/`gapBetweenCars`/`AutoCamCar`）。
详细约定见仓库根 `docs/09-testing.md`；AC API 参考见仓库根 `docs/`。

---

## 已知限制与遗留配置

- **`closeBattleThreshold`**：被读取、写回，但决策实际用的是 `tvCamThreshold`/`chaseOnboardThreshold`，
  属死配置。
- **`offPaceCanOverrideBattles`**：被读取、写回，但导演循环未使用，属死配置。
- **`battleCams`**：解析为 `battleCamSwitching`，但战斗机位由「动态追车 / 强制 TV」分支主导，更多作兜底。
- **`battleKMHPercentDiff`**：硬编码 `15.0`，不从 INI 读取（要改需源码）。
- **`AutoCamCar.py` 与 `AutoCam.py` 各自保留一份 `safeName`/`gapBetweenCars`**：前者为遗留副本，测试以
  `AutoCam.py` 内实现为准。
- **`anyDriverFinishing` 门控**：事故/超车判断处该值在该点恒为 `0`，可能使事故/超车在冲线圈触发，属可接受范围。
- **OBS 链路被剔除**：`autocam/` 不含 `obsremote`/`websocket`，仅保留 `process_exists("obs64.exe")` 探测与
  `promoText` 聊天公告。
- `PIT_ENTRY/*`：进站位置表已加载但当前逻辑停用（`loadPitEntryToDict` 在 `acMain` 里被注释）。

---

## 致谢 / 参考来源

- **原概念**：Minolin — [ActionCam](https://www.assettocorsa.net/forum/index.php?threads/concept-actioncam.31665/)
- **原作者**：Dave / **Esotic** — [Auto Cam V1.6](https://www.overtake.gg/downloads/auto-cam.28562/)
- 配合广播工具：BCast、ACTV
- 详细 AC Python 开发资料见本仓库根目录 `docs/`
