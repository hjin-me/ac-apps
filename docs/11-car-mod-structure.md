# 11 · 车辆 Mod 目录结构与数据格式

车辆 mod 是 AC 内容组织的基础单元。理解它的目录结构与各配置文件格式，有助于读懂
`ac.getCarName` / `ac.getCarSkin` 的返回值、排查 mod 不显示 / 涂装不加载的问题，以及
正确编写 AutoCam 的 `carCameras.ini`（按车型文件夹名配置）。

## 基础位置与最外层规则

车辆 mod 放在 AC 根目录 `content/cars/` 下，**每个 mod 必须是一个直接放在 `cars/` 里的扁平文件夹**：

```
assettocorsa/content/cars/<car_folder>/
```

> ⚠️ 最常见的失败原因就是**层级嵌套过深**（`cars/<car>/<car>/data.acd`）或路径放错
> （如放进 `Documents\Assetto Corsa` 而非游戏安装目录）。文件夹名必须**全小写、无空格**，
> 且服务器 / 客户端两端大小写严格一致。

## 车辆文件夹顶层结构

```
content/cars/<car_folder>/
├── ui/ui_car.json        # 菜单身份/规格元数据（必填，缺了车不显示）
├── data/                 # 物理与配置（也可能被加密成 data.acd）
├── sfx/                  # 音效（banks 等）
├── skins/                # 涂装，每套一个子文件夹
├── texture/              # 贴图（常用；命名因 mod 而异）
├── extensions/           # CSP 扩展（可选，需装 Custom Shaders Patch）
├── animations/           # 动画（可选）
├── *.kn5                # 3D 模型（车身 + 碰撞体）
├── body_shadow           # 车身阴影（可选）
├── livery.png / preview.jpg  # 可选预览图
└── ui_skin.json          # ★ 注意：单皮肤的 ui_skin.json 应放在 skins/<skin>/ 内，不是根目录
```

## `data/` 目录：物理与配置

一个车辆的全部物理/设置数据都放在 `data/` 目录。它既可普通展开，也可被打包成
**`data.acd`（加密归档）**——`.acd` 无法直接编辑，须先解包（Content Manager 或 ACD 工具）
修改后再重新打包。

### `car.ini` —— 全局属性

车辆的顶层物理与图形设置：

| 键 | 说明 |
| :--- | :--- |
| `TOTALMASS` | 底盘质量（不含油/车手） |
| `INERTIA` | 三轴惯性（俯仰/偏航/侧倾） |
| `CG_LOCATION` | 重心坐标 |
| `MIN_RPM` / `MAX_RPM` | 发动机工作区间 |
| `GRAPHICS_OFFSET` | 对齐视觉模型与物理中心 |
| `ffb_mult` | 力反馈强度 |
| `SLIPSTREAM_DRAFT` / `SLIPSTREAM_DISTANCE` | 尾流（draft）参数 |
| `[CONTROLS] STEER_LOCK` | 转向角度（如 450 = 450°） |

### `engine.ini` —— 发动机特性

| 节 / 键 | 说明 |
| :--- | :--- |
| `[ENGINE_DATA] LIMITER` | 断油转速 |
| `[ENGINE_DATA] LIMITER_HZ` | 断油频率（影响红线区表针表现） |
| `[ENGINE_DATA] MINIMUM` | 怠速 RPM（如 900） |
| `[ENGINE_DATA] INERTIA` | 曲轴转动惯量（影响油门响应） |
| `[ENGINE_DATA] MAX_BOOST` / `WASTEGATE` | 涡轮增压压力 / 泄压阀（涡轮车） |
| `[COAST_REF]` | 发动机制动/滑行的 RPM 与扭矩 |
| `[DAMAGE]` | 超转/过热损伤阈值 |
| `HEADER_POWER_CURVE`（power.lut） | **扭矩-转速曲线**，对动力手感影响最大 |

> 提高 `LIMITER` / 增压值时，需同步调高 `[DAMAGE]` 里对应阈值（`RPM_THRESHOLD`/
> `TURBO_BOOST_THRESHOLD`），否则会导致发动机损伤。

### `drivetrain.ini` —— 传动系统

| 键 / 节 | 说明 |
| :--- | :--- |
| `GEAR_RATIO` | 各档齿比 |
| `FINAL_RATIO` | 主减速比 |
| `GEAR_EFFICIENCY` | 传动损耗 |
| `[DIFFERENTIAL] POWER` / `COAST` | 加速/减速锁止百分比 |
| AWD 标记 | 四驱标记 |
| `[GEARBOX] CHANGE_UP_TIME` / `CHANGE_DN_TIME` | 换档耗时 |
| `[AUTO_SHIFTER]` / `[AUTOBLIP]` | 自动档 / 自动补油 |
| `[UPSHIFT_PROFILE]` / `[DOWNSHIFT_PROFILE]` | 升/降档离合结合时间 |
| `.rto` 文件（`1st.rto`、`final.rto` 等） | 可选替代齿比 setup |

### 其它物理文件

| 文件 | 说明 |
| :--- | :--- |
| `tyres.ini` | 轮胎侧偏特性、压力敏感度、载荷特性 |
| `brakes.ini` | 最大扭矩、`BRAKE_BIAS`（0=全后 / 1=全前）、`COOLING_RATE` |
| `electronics.ini` | ABS / TC / ESP / 自动档 |
| `power.lut` | **扭矩-转速查表**，可编辑改动力曲线 |
| `fuel_cons.ini` | 油耗 |
| `ctrl_turbo.ini` / `ctrl_ers.ini` / `kers.ini` | 涡轮/动能量回收/ERS 控制 |

## `ui/ui_car.json` —— 菜单身份与规格

车辆在选车菜单里的显示名、品牌、级别、性能参数均在这里。位于 `ui/` 子文件夹
（**不是**车辆根目录）。缺失/损坏会导致车辆**不在列表里显示**。

| 字段 | 说明 |
| :--- | :--- |
| `name` | 显示名（如 `"BMW M3 E92"`） |
| `brand` | 品牌（无则 `"Various"`） |
| `class` | 级别（`"street"` / `"GT3"` / `"F1"`） |
| `tags` | 检索标签数组 |
| `specs` | 性能规格对象：`bhp`/`torque`/`weight`/`topspeed`/`acceleration`/`pwratio` |
| `description` | 描述 |
| 可选 | `year`/`country`/`author`/`version`/`url` |

```json
{
  "name": "BMW M3 E92",
  "brand": "bmw",
  "class": "street",
  "specs": {
    "bhp": "414",
    "torque": "400 Nm",
    "weight": "1580 kg",
    "topspeed": "250 km/h",
    "acceleration": "4.8s",
    "pwratio": "3.81"
  },
  "tags": ["street", "germany"]
}
```

> 📌 **对 AutoCam 的意义**：`ui_car.json` 里的 `name` 才是「人类可读的车型显示名」。
> 但 Python API **没有暴露**这个字段——`ac.getCarName(car)` 返回的是**车辆文件夹名**（如
> `ks_ferrari_488_gt3`），即模型 id。要显示友好名需**自己维护一份「文件夹名 → 显示名」映射表**。

## skins/ 目录：涂装

每套涂装一个**独立子文件夹**，位于 `skins/` 下：

```
content/cars/<car>/skins/<skin_name>/
├── preview.jpg          # 选车界面预览图
├── ui_skin.json         # 涂装级元数据（车手名/车队/国籍/车号/赞助商）
├── skin.ini             # 驾驶座舱模型：DRIVER_NAME/TEAM_NAME/SUIT/HELMET/GLOVES/NUMBER/FLAG
└── *.dds / *.png        # 涂装贴图
```

> ⚠️ `ui_skin.json` 必须放在**该 skin 自己的子文件夹**里，而不是车辆根目录——放错会导致涂装
> 加载失败渲染成空白/白色车。

> 📌 **对 AutoCam 的意义**：`ac.getCarSkin(car)` 返回的就是**这个 skins 子文件夹名**（如
> `default`、`alex_9l`）。它反映的是「用哪套涂装」，不是车型。车手名应改用
> `ac.getDriverName`；国籍用 `ac.getDriverNationCode`。

## setup 文件格式（玩家可调设置）

玩家保存的调校放在 `Documents\Assetto Corsa\setups\<car_folder>\<track>\<setup>.ini`，
覆盖 `drivetrain.ini` 等默认值：

```ini
[INTERNAL_GEAR_2]
VALUE=5
[INTERNAL_GEAR_3]
VALUE=8
[WING_1]
VALUE=6
```

## 服务器引用

专用服务器里，`cfg/server_cfg.ini` 的 `CARS` 行列出允许的车辆**文件夹名**；
`cfg/entry_list.ini` 网格槽位用 `MODEL=` 引用同名的车辆文件夹。因此服务器与客户端文件名必须一致。

---

**参考**：

- [AC Supply — Mod Folder Anatomy (Cars, Tracks & Skins)](https://www.acsupply.cx/blog/mod-folder-anatomy-cars-tracks-skins)
- [AC Supply — Install Car Mods Guide](https://www.acsupply.cx/guides/install-car-mods)
- [gro-ove/actools-uijson（ui_car.json 编辑工具）](https://github.com/gro-ove/actools-uijson)
- [Assetto Corsa Modding Cards Textbook — Car Physics Configuration Files](https://learncoachassist.com/topics/assetto_corsa_modding_cards/textbook/car-physics-configuration-files)
- 本项目 `autocam/apps/python/AutoCam/carCameras.ini`（按车辆文件夹名配置随车镜头）
