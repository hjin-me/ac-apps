# 08 · 开发工具链：调试、热重载、类型桩、OBS 集成

针对 AC Python App 的辅助工具与常用实践。

## 类型桩（IDE 自动补全）

官方未公开完整 SDK，社区用[类型桩](https://github.com/rikby/ac-stubs)提供 `ac`/`acsys` 的
autocomplete：

```bash
pip install ac-stubs
```

它暴露一个统一的 `ac` 模块接口，在 PyCharm 等 IDE 中可获得补全。仓库内附 `ACPythonDoc.txt`
（完整的非官方接口 dump）与 `grab-func.py`（抓取函数脚本）。

## 离线测试 / 烟雾测试

`AssettoCorsaDevLibs` 提供了 `ac`/`acsys` 的 **stub 模块**，可在不启动游戏的前提下临时替换真实
模块，用于编写单元测试或烟雾测试。适合 CI 中对纯逻辑（比如 AutoCam 的导播决策、gap 计算）做校验。

## 热重载（Hot Reload）

[assetto-corsa-hot-plugin](https://github.com/jamessanford/assetto-corsa-hot-plugin) 允许在游戏运行时
修改插件：从外部（如 Linux 机器）发送更新、捕获异常、进入 REPL，无需重启游戏即可迭代。对逻辑调试
非常省时。

## 游戏内调试

- 用 `ac.console(message)` 打印到游戏内控制台（**Home** 键，德语键盘 **Pos1**）。
- 用 `ac.log(message)` 写入 `Documents\Assetto Corsa\logs\py_log.txt`。
- 崩溃排查：捕获 `sys.exc_info()` + `traceback.format_exception` 后 `ac.log` / `ac.console`。

## Content Manager（CM）

AC 的现代化启动器。**Settings → Assetto Corsa → Apps** 可图形化启用/禁用 App；**App Manager**
可管理和安装 App，并能直接看到 `py_log.txt` 的运行日志，是调试的首选入口。

## OBS Studio 集成

本项目通过 `obsremote.py` / `websocket/` 连接 OBS WebSocket，控制推流、切换场景、响应比赛阶段。
要点：

- AC Python 侧一般用 `websocket-client` 连接 OBS 的 websocket 端口（默认按 OBS 版本，IP 与密码
  可配置）。
- 因 AC 使用 Python 2.x 环境，需把 `websocket` 库与缺少的 `win32con`、`ctypes.pyd` 等一起打包进
  App 目录（如 `AutoCam/stdlib/`、`stdlib64/`）。
- 代码中对 Windows API 的调用（`ctypes.WinDLL('user32')`、`SendInput`）用于实现全局快捷键与
  键鼠模拟，详见本项目 `AutoCam.py` 的 hotkey 部分。

## 平台依赖

AC 的内置 Python 是较早的 2.x，且缺少部分平台模块。常见做法：

- 在 App 目录内附带 `stdlib/`、`stdlib64/`（32/64 位）的 `.pyd`，并用
  `sys.path.insert(0, sysdir)` 优先加载，如本项目：
  ```python
  import platform
  sysdir = os.path.dirname(__file__)+'/stdlib64' if platform.architecture()[0]=="64bit" else os.path.dirname(__file__)+'/stdlib'
  sys.path.insert(0, sysdir)
  ```
- 需要 `import ac, acsys`，Windows 命名空间共享内存用 `mmap`。

---

**参考**：

- [rikby/ac-stubs（类型桩）](https://github.com/rikby/ac-stubs)
- [jamessanford/assetto-corsa-hot-plugin（热重载）](https://github.com/jamessanford/assetto-corsa-hot-plugin)
- [albertowd/live-telemetry（App 示例）](https://github.com/albertowd/live-telemetry)
- [Template_Assetto_Corsa_App（App 模板）](https://github.com/huntervaners/Template_Assetto_Corsa_App)
