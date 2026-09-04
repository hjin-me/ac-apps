# 06 · Custom Shaders Patch（CSP）的 `ac.ext_*` 扩展函数

[Custom Shaders Patch（CSP）](https://acstuff.club/patch/) 是 AC 的社区扩展（由 x4fab / Peter Boese
开发），在基础 `ac` 模块之外，通过 `ac.ext_*` / 其它扩展提供了大量额外能力。**使用这些函数需要安装
CSP**，且版本需满足相应要求。

## 可用性判断

因为 `ext_*` 是运行时注入的，调用前应做“能力探测”（try/except），本项目就是这么做的：

```python
cmExtensions = 0
try:
    camFOV = ac.ext_getCameraFov()
    cmExtensions = 1
    ConsoleLog("using cm extensions")
except:
    ConsoleLog("no cm extensions")
```

同理，`ac.ext_isVirtualMirrorForced()` 也需要 try/except，因为并非所有 CSP 版本都提供。

## 本项目用到 / 注释中列出的扩展函数

| 函数 | 说明 |
| :--- | :--- |
| `ac.ext_getCameraFov()` ⭐ | 读取相机 FOV（存在即视为 CSP/CM 扩展可用） |
| `ac.ext_isVirtualMirrorForced()` ⭐ | 虚拟后视镜是否被强制开启（CSP v0.1.49 新增） |
| `ac.ext_setCameraFov` | 设置相机 FOV |
| `ac.ext_getCameraMatrix` / `ac.ext_getCameraProj` / `ac.ext_getCameraView` | 相机矩阵 / 投影 / 视图 |
| `ac.ext_getCameraPos()` | 相机世界坐标 |
| `ac.ext_getTrackCamerasNumber()` | 赛道机位组数量（TV1/TV2/Static…） |
| `ac.ext_getCurrentTrackCamera()` / `ac.ext_setCurrentTrackCamera()` | 当前 / 设置赛道机位组 |
| `ac.ext_getCurrentCamera()` / `ac.ext_setCurrentCamera()` | 当前 / 设置相机 |
| `ac.ext_getCurrentDrivableCamera()` / `ac.ext_setCurrentDrivableCamera()` | 当前 / 设置可驾驶相机 |
| `ext_chaserCameraDebugText` | 追车相机调试文本 |

> 注意：`ext_*` 函数的确切签名与可用性随 CSP 版本变化，且公开文档较少。最可靠的方式是查看
> CSP 源码、其 Discord 或 `acscripts`（官方扩展脚本）。

## 扩展 App 结构

CSP 扩展 App 与普通 Python App 结构一致——将脚本解压到 AC 根目录（`steamapps\common\assettocorsa`）。
官方示例仓库 [acc-extension-apps](https://github.com/ac-custom-shaders-patch/acc-extension-apps) 提供：

- **AccExtHelper** — 切换 VAO / 车手 / 倒车
- **AccExtMirrors** — 智能后视镜控制
- **AccExtRain** — 雨刮 / 雨量
- **AccExtWeather** — 时间与天气

## 注意事项

- 只有安装了 CSP 的客户端才能使用 `ext_*`；未安装时会抛异常，因此必须先探测。
- 版本不匹配可能导致部分函数缺失，建议在代码中做特性检测而非简单假设存在。
- CSP 也给游戏带来 `NormalizedSplinePosition`、`ext.getTrackCamerasNumber` 等能力的增强，
  可提升广播导播类的观感表现。

---

**参考**：

- [Custom Shaders Patch 官网](https://acstuff.club/patch/)
- [acc-extension-apps（CSP 官方扩展 App 示例）](https://github.com/ac-custom-shaders-patch/acc-extension-apps)
- [CSP v0.1.49 Changelog（新增 `ext_isVirtualMirrorForced`）](https://c1xtz.github.io/csp-logs/changelog/0-1-49)
