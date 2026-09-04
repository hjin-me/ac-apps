# Assetto Corsa Python App 开发文档

本目录收录了互联网上关于 **Assetto Corsa（神力科莎 / AC）** Python App（插件 / 内挂应用）开发的相关文档与 API 参考资料，供本仓库 `AutoCam` 项目后续开发使用。

> 说明：Assetto Corsa 官方并未公开完整的 Python App SDK 文档，本文档资料主要源自社区整理的
> `inofficial_acpythondoc_v2`（非官方 Python 文档）、`ac-stubs` 类型桩、ACLIB 框架教程、
> Custom Shaders Patch（CSP）扩展文档与各开源 App 的源码与 README。内容基于检索结果整理，
> 可能与具体游戏版本（AC 1.14+ / CSP 版本）存在差异，请以实际运行环境为准。

## 目录

| 文档 | 内容 |
| :--- | :--- |
| [01-app-structure.md](01-app-structure.md) | App 目录结构、生命周期函数、安装启用、日志 |
| [02-ac-module-api.md](02-ac-module-api.md) | `ac` 模块函数 API 参考（窗口/控件/绘制/数据） |
| [03-acsys-constants.md](03-acsys-constants.md) | `acsys.CS` 车辆状态常量与 `acsys.CM` 相机模式 |
| [04-shared-memory-sim-info.md](04-shared-memory-sim-info.md) | `sim_info` / 共享内存（`acpmf_physics`/`graphics`/`static`） |
| [05-camera-and-car-control.md](05-camera-and-car-control.md) | 相机切换、聚焦车辆、排名与车队控制 |
| [06-csp-extensions.md](06-csp-extensions.md) | Custom Shaders Patch 的 `ac.ext_*` 扩展函数 |
| [07-aclib-framework.md](07-aclib-framework.md) | ACLIB 高层框架（`ACApp`/`ACData`/`ACMeta`） |
| [08-development-tooling.md](08-development-tooling.md) | 调试、热重载、类型桩、Content Manager、OBS 集成 |
| [09-testing.md](09-testing.md) | 测试规范：离线纯逻辑（stub `ac`/`acsys`）与游戏内 API 行为的分层测试 |

## 相关概念速览

**AC 有两种 Python 开发路线：**

1. **原生路线（本项目采用）**：直接使用内置 `ac` / `acsys` 模块，暴露 `acMain` / `acUpdate` /
   `acShutdown` 等全局函数，配合 `ac.newApp()` 等窗口控件 API 构建 UI。数据既可通过 `ac.getCarState()`
   获取，也可通过共享内存 `sim_info` 直接读取。
2. **框架路线（ACLIB）**：使用 `ui.gui.ac_widget`、`memory.ac_data` 等高层模块，以类继承
   `ACApp` + `update()` 的方法组织代码，封装了数据的就绪/变化事件。

**环境版本**：共享内存结构注释标注为 `AC 1.14.3`；CSP 扩展（`ext_*`）需要安装
[Custom Shaders Patch](https://acstuff.club/patch/)。

---

*资料检索日期：2026-09-04*
