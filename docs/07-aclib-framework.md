# 07 · ACLIB 高层框架

[ACLIB](https://github.com/styinx/ACLIB) 是一套为 AC Python App 提供更高层封装的框架，与原生
`acMain` / `acUpdate` 路线不同：它以类继承 + `update()` 方法组织代码，并通过事件驱动访问数据。
适合希望在不开箱即用 `ac` 裸 API 的情况下更快开发的场景。

## 前置检查

开发前先确保 ACLIB 正常工作：启动 AC，按 **Home**（德语 **Pos1**）打开控制台，确认无 ACLIB 警告；
关闭游戏后检查 **`C:/Users/<yourname>/Documents/Assetto Corsa/ACLIB/log.txt`** 是否已生成。无警告/报错
即可继续。

## 文件放置

每个 App 是独立文件，命名必须为 **`ACLIB_<app_name>.py`**，放在：

```
C:/Program Files (x86)/Steam/steamapps/common/assettocorsa/apps/python/ACLIB/apps/
```

**命名约定**：文件名的 `ACLIB_` 后缀部分 `_` 之后必须与文件内类名一致：
`ACLIB_Time.py` → 类 `Time`；`ACLIB_Stats.py` → 类 `Stats`。

```
apps/
 |- ACLIB_SuperApp.py
 |- ACLIB_Time.py
 |- ACLIB_Stats.py
```

## 基类与导入

```python
from memory.ac_data import ACData
from memory.ac_meta import ACMeta
from ui.gui.ac_widget import ACApp, ACLabel
from ui.gui.layout import ACGrid
from util.format import Format
```

## App 尺寸 / 位置

在 `__init__` 中调用 `super().__init__(name, x, y, w, h)`，传 App 名（显示在任务栏）与初始位置、
尺寸：

```python
super().__init__('My local Time', 200, 200, 160, 80)
```

## 生命周期

ACLIB 不使用 `acMain`/`acUpdate`/`acShutdown` 全局函数。控件在 `__init__` 中创建，动态数值在
`update(self, delta)` 中刷新。

## 布局与控件

- `ACLabel` — 文本控件，可传初始文本与父对象。
- `ACGrid(rows, cols, parent)` — 网格布局，尺寸填满 App，单元格均分
  （如 200×100 的 App 用 4×4 网格 → 50×25 单元格）。
- `grid.add(widget, x, y)` — 放置控件（左上角为 0,0）。
- `hide_decoration()` — 隐藏 AC 符号与标题。

## 事件驱动数据（ACData / ACMeta）

等待数据就绪而非立即读取 —— 订阅事件：

```python
self._data.on(ACData.EVENT.READY, self.on_ready)
```

就绪后可请求数值，如 `self._data.timing.lap`、`self._data.tyres.compound`，并可订阅变化事件
`ACData.EVENT.LAP_CHANGED`、`ACData.EVENT.COMPOUND_CHANGED`。

## 示例：ACLIB_Time

```python
from time import time
from memory.ac_data import ACData
from memory.ac_meta import ACMeta
from ui.gui.ac_widget import ACApp, ACLabel
from ui.gui.layout import ACGrid
from util.format import Format

class Time(ACApp):
    def __init__(self, data: ACData = None, meta: ACMeta = None):
        super().__init__('My local Time', 200, 200, 160, 80)
        self._start = time()
        self._grid = ACGrid(2, 2, self)
        self._local_time = ACLabel(self, '')
        self._session_time = ACLabel(self, '')
        self._grid.add(ACLabel(self, 'Local time:'), 0, 0)
        self._grid.add(self._local_time, 1, 0)
        self._grid.add(ACLabel(self, 'Expired time:'), 0, 1)
        self._grid.add(self._session_time, 1, 1)
        self.hide_decoration()

    def update(self, delta: int):
        self._local_time.text = Format.time()
        self._session_time.text = Format.duration(time() - self._start)
```

## 示例：ACLIB_Stats（带事件）

```python
class Stats(ACApp):
    def __init__(self, data: ACData = None, meta: ACMeta = None):
        super().__init__('My Stats App', 200, 200, 200, 100)
        self._data = data
        self._meta = meta
        self._grid = ACGrid(4, 4, self)
        self._grid.add(ACLabel(self._grid, 'Lap'), 0, 0)
        self._grid.add(ACLabel(self._grid, 'Compound'), 0, 1)
        self._lap = ACLabel(self._grid)
        self._compound = ACLabel(self._grid)
        self._grid.add(self._lap, 1, 0)
        self._grid.add(self._compound, 1, 1)
        self._data.on(ACData.EVENT.READY, self.on_ready)

    def on_ready(self):
        self._lap.text = self._data.timing.lap
        self._compound.text = self._data.tyres.compound
        self._data.on(ACData.EVENT.LAP_CHANGED, self.on_lap_changed)
        self._data.on(ACData.EVENT.COMPOUND_CHANGED, self.on_compound_changed)

    def on_lap_changed(self, lap: int):
        self._lap.text = lap

    def on_compound_changed(self, compound: str):
        self._compound.text = compound
```

## 与原生路线的取舍

| 维度 | 原生 `ac`/`acsys`（本项目） | ACLIB |
| :--- | :--- | :--- |
| 结构 | 全局 `acMain`/`acUpdate` | 类继承 `ACApp` + `update()` |
| 数据 | `ac.getCarState()` / 共享内存 | `ACData`/`ACMeta` 事件驱动 |
| 场景 | 任意可直控 API 的 App | 愿封装、快速搭建 UI 的 App |

---

**参考**：

- [ACLIB HOWTO - Create an app](https://github.com/styinx/ACLIB/wiki/HOWTO-Create-an-app)
- [ACLIB 仓库](https://github.com/styinx/ACLIB)
