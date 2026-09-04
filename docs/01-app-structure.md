# 01 · App 目录结构、生命周期与启用

## 安装目录

AC 的 Python App 放在 Steam 安装目录下的 `apps/python/` 内，每个 App 独占一个子文件夹：

```
C:\Program Files (x86)\Steam\steamapps\common\assettocorsa\apps\python\
```

每个 App 的子文件夹里放一个以 App 名命名的 `.py` 入口文件，例如：

```
apps/python/
└── AutoCam/
    ├── AutoCam.py          # 入口文件（模块名与文件夹名一致）
    ├── AutoCamCar.py
    ├── AutoCam_sim_info.py # 共享内存读取
    ├── AppCom.py           # 与广播 App 通信
    ├── AutoCam.ini         # 用户配置
    ├── carCameras.ini
    └── PIT_ENTRY/
        └── ...
```

关键约定：

- **入口文件名** 必须与 App 名匹配，AC 启动时扫描每个目录中的 Python 文件并执行，调用其中的
  `acMain`。
- 若要被 Content Manager / 游戏识别，App 目录通常还需有一个可选的 `manifest.json` 或图标资源
  （放在 `content/gui/icons/` 下，如本项目 `Auto Cam_ON.png` / `Auto Cam_OFF.png`）。
- 可在目录内自带本地 `websocket/`、`stdlib/`、`stdlib64/` 等第三方/平台依赖。

## App 图标

图标放在 AC 根目录的 `content/gui/icons/` 下，命名需与 App 名对应（空格用下划线），例如
`Auto Cam_ON.png`、`Auto Cam_OFF.png`。App 启用后会在右侧任务栏显示，可切换开关状态。

## 生命周期函数（原生路线）

AC 在加载每个 App 时按照以下生命周期调用模块内的**全局函数**：

| 函数 | 调用时机 | 作用 |
| :--- | :--- | :--- |
| `acMain(ac_version)` | App 启动、进入驾驶场景时 | 读取配置、创建窗口与控件、注册回调。**必须返回 App 名（字符串）** |
| `acUpdate(deltaT)` | 每个物理帧（tick） | 高频逻辑：读取遥测、相机切换、状态机、刷新 UI |
| `acShutdown(*args)` | App 退出 / 关闭 | 保存设置、清理资源、写日志 |

> 注意：`onFormRender(deltaT)` 等渲染钩子仅在需要**逐帧绘制自定义图形**时才会用到。
> 大部分 App 只需 `acMain` + `acUpdate` 即可。

示例（本项目 AutoCam.py）：

```python
import ac
import acsys

def acMain(ac_version):
    global camWindow
    camWindow = ac.newApp("Auto Cam")      # 创建窗口，返回窗口句柄
    ac.setSize(camWindow, 280, 530)
    ac.setBackgroundOpacity(camWindow, 0.7)
    # ... 添加控件、注册回调 ...
    return "AutoCam"                        # 必须返回 App 名

def acUpdate(deltaT):
    autoCam()                               # 每帧逻辑

def acShutdown(*args):
    ConsoleLog("AutoCam::acShutdown")       # 清理
```

## 启用 App

1. 复制 App 目录到 `apps/python/` 下（例如 `apps/python/AutoCam`）。
2. 打开 **Content Manager** 或游戏启动器。
3. **Settings > Assetto Corsa > Apps**，勾选 **AutoCam** 启用。
4. 进入游戏，右侧任务栏激活 **AutoCam** 图标以显示设置窗口。

若 App 未显示，多半是目录位置错误或入口函数报错（见下文日志）。

## 日志与调试输出

- `ac.console(message)`：输出到游戏内控制台（按 **Home** 键打开，德语键盘为 **Pos1**）。
- `ac.log(message)`：写入 `Documents\Assetto Corsa\logs\py_log.txt`。
- 打包到 AC 目录外的 App（如 OBS 外部进程）常用 `traceback`/`sys.exc_info()` 捕获异常后
  再打印。

```python
def ConsoleLog(message):
    ac.console("AutoCam(%s): %s" % (strTimestamp, message))
    ac.log("AutoCam(%s): %s" % (strTimestamp, safeText(message)))
```

## 配置持久化

配置通常用标准库 `configparser` 读写 `apps/python/<App>/<App>.ini`，例如本项目的
`WriteSettings()` / `ReadSettings()`（`SETTINGS` section），或在游戏内通过“SAVE CONFIGURATION”
按钮写回文件、按星期/服务器 IP 保存不同预设。

---

**参考**：

- [ACLIB HOWTO - Create an app](https://github.com/styinx/ACLIB/wiki/HOWTO-Create-an-app)
- [Template_Assetto_Corsa_App](https://github.com/huntervaners/Template_Assetto_Corsa_App)
- [How can I do Python apps debug? (Overtake.gg)](https://www.overtake.gg/threads/how-can-i-do-python-apps-debug.249985/)
