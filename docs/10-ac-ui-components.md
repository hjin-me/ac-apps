# 10 · AC 原生 UI 组件与布局

AC 的**原生路线**（直接使用内置 `ac` 模块，暴露 `acMain` / `acUpdate` / `acShutdown`）在 UI 上
有一个与 Web / 桌面框架截然不同的底层事实：**它没有布局管理器**。所有控件都靠**绝对坐标手动摆放**，
理解这一点是正确构建 AC App UI 的前提。

> 本文偏「行为引擎」：讲清原生 UI 到底怎么工作、有哪些实机坑。控件 API 的完整清单见
> [02-ac-module-api.md](02-ac-module-api.md)；高层的网格布局框架见
> [07-aclib-framework.md](07-aclib-framework.md)。

## 两条 UI 开发路线

| 路线 | UI 定位方式 | 布局引擎 | 本项目 |
| :--- | :--- | :--- | :--- |
| **原生 `ac`/`acsys`** | `ac.setPosition(ctrl, x, y)` 手动绝对定位 | **没有** | ✅ 采用 |
| **ACLIB 框架** | `ACGrid(rows, cols)` 网格 + `grid.add(widget, x, y)` | 有（`ACGrid`） | 否 |

原生路线没有 `ACGrid` 那样的自动均分网格，也没有 flex / 相对定位、没有自动回流。元素多起来后
必须自己算好每个控件的坐标，这正是本仓库早期 UI「控件堆叠到左上角」问题的根源（见下文踩坑）。

## 窗口与坐标系

### 创建窗口

```python
win = ac.newApp("Auto Cam")          # 创建 App 窗口，返回窗口 ID
ac.setSize(win, 280, 90)             # 定义内容区边界（宽 × 高）
ac.drawBorder(win, 0)                # 0 不画边框，1 画
ac.setBackgroundOpacity(win, 0.7)    # 背景不透明度 0~1
ac.setTitle(win, "Auto Cam")         # 标题文字
```

### 坐标规则（关键）

- **原点在窗口内容区的左上角**，即标题栏下方，**不是**屏幕左上角。
- **y 向下递增**（与屏幕坐标系一致，但与常见数学坐标系相反）。
- 单位是**窗口内局部的像素**，会跟着 AC 的 UI 缩放系数一起缩放（不是绝对屏幕像素）。
- 坐标是**相对窗口**的，不是相对父控件（原生 UI 没有父控件嵌套层级，所有控件都挂在窗口下）。

### `setSize` 决定"可见边界"

`ac.setSize(win, w, h)` 定义的是**内容区边界**。控件若被摆到 `(x, y)` 后其右/下边缘越过了这个
边界，行为不可靠——**要么被裁切，要么回退到默认位置 `(0, 0)` 渲染**（见踩坑 1）。因此窗口尺寸
必须**由内容反推**：先排出所有控件的坐标，取最大 `y` 和最大 `x` 再加边距作为窗口尺寸。

## 常用控件

每个控件都用 `ac.add*` 创建（返回控件 ID），再用 `ac.set*` 调整外观 / 监听。以下为 AutoCam 实测
用到的组合：

### Label（文本）

```python
lbl = ac.addLabel(win, "--")            # 创建文本控件
ac.setPosition(lbl, 14, 8)              # 文本左上角 (x, y)
ac.setFontSize(lbl, 18)                 # 字号
ac.setText(lbl, "新文本")               # 运行时改内容
ac.setFontAlignment(lbl, "left")        # left / center / right
```

### Button

```python
btn = ac.addButton(win, "AutoCam ACTIVE")
ac.setPosition(btn, 15, 22)
ac.setSize(btn, 250, 28)                # 按钮自身尺寸
ac.setFontSize(btn, 14)
ac.addOnClickedListener(btn, onClick)   # 点击回调
ac.setText(btn, "AutoCam INACTIVE")     # 运行时改标签
```

### Spinner（数值调节器）

```python
spin = ac.addSpinner(win, "")
ac.setPosition(spin, 180, 98)
ac.setSize(spin, 85, 22)
ac.setRange(spin, 0.1, 2.5)             # 取值范围
ac.setStep(spin, 0.1)                   # 步进
ac.setValue(spin, 0.5)                  # 当前值
ac.addOnValueChangeListener(spin, onChange)  # 回调接收新值
```

### CheckBox（注意：实机是残缺的，见踩坑 3）

```python
chk = ac.addCheckBox(win, "Enable X")
ac.addOnClickedListener(chk, onClick)   # 点击回调
# ⚠️ 实机没有 ac.isChecked / ac.setChecked，读取/设置勾选态的接口缺失
```

## 实机踩坑（已在本仓库验证）

### 1. 控件堆叠到左上角 —— 根因是边界 / 定位，不是控件总数

现象：多个控件挤在窗口左上角重叠。

原因有二，**核心是前者**：
- 控件摆到 `(x, y)` 后**越过了 `setSize` 定义的边界**；或
- `setPosition` **没设 / 设错**导致回退到默认 `(0, 0)`。

> 早期文档里「超过约 13 个控件就会叠顶」的结论，其实是**这个现象的观测阈值**，并非硬性上限。
> 真正的成因是控件尺寸 / 坐标超出内容区边界。只要把每个控件都收进窗口边界内（或适当放大窗口），
> 控件多也不会叠顶。

修复手法：用 `setSize(win, w, h)` 的上限反推坐标 —— 先数出控件所需的最大 `x + width` 与
`y + height`，据此设置窗口尺寸，保证所有控件落在边界内。

### 2. 标题栏无法彻底去掉

`ac.setTitle(win, "")` 或 `ac.newApp("")` **只清空标题文字**，不会移除标题栏那一条 chrome。
AC 没有提供彻底去掉窗口标题栏的原生 API。

- 用 `ac.newApp("")`（空 App 名）会让该窗口**从右侧 App 列表消失**——HUD 这类想常驻、不靠侧边栏
  呼出的窗口可考虑；但副作用是不能再从任务栏切换它。
- 用 `ac.newApp("Auto Cam HUD")` + `ac.setTitle(win, "")` 保留侧边栏入口，仅隐藏窗口内标题文字。
- 标题栏会占走内容区上方的一段高度，`y=0` 仍位于其下方，控件定位不受影响。

### 3. 布尔项：没有 `isChecked` / `setChecked`

AC 1.14.3 的 `ac` 模块**不存在** `ac.isChecked` 与 `ac.setChecked`（调用抛
`AttributeError: module object has no attribute isChecked`）。社区文档里的这两项是检索产物。

于是本项目把布尔项渲染成**自带状态的按钮**：

```python
def makeToggle(win, text, on, onClick):
    btn = ac.addButton(win, "%s: %s" % (text, "ON" if on else "OFF"))
    ac.addOnClickedListener(btn, onClick)
    return btn

def flip(btn, label, state):
    state = not state
    ac.setText(btn, "%s: %s" % (label, "ON" if state else "OFF"))
    return state
```

状态以 Python 全局为准，点击时翻转并刷新按钮文字，绕开不存在的勾选读写接口。

### 4. 字体颜色 / 字号不稳定，需静默降级

`ac.setFontColor(ctrl, r, g, b)`（注意是 0~1 浮点，不是 0~255）与 `ac.setFontSize` 并非对每种
控件都稳定支持。本项目封装了 `setLabelColor`，失败时静默回退到默认白字：

```python
def setLabelColor(ctrl, r, g, b, a=1.0):
    try:
        ac.setFontColor(ctrl, r, g, b, a)
    except:
        pass     # 装不上就保持默认，绝不让 App 崩溃
```

### 5. 替换字体（`setCustomFont` / `initFont`）

除字号/颜色/对齐外，原生 `ac` **还能替换整个字体族**，只是走的是另一组社区接口，不在
`setFontSize`/`setFontColor` 那套里：

| 函数 | 作用 |
| :--- | :--- |
| `ac.initFont(<id>, <字体名>, <bold>, <italic>)` | 注册一个字体到指定 ID（0/1 控制加粗、斜体） |
| `ac.setCustomFont(<控件ID>, <字体名>, <bold>, <italic>)` | 把某控件设为指定字体 |

```python
ac.initFont(0, "Unispace", 0, 0)
ac.setCustomFont(speedLabel, "Unispace", 0, 1)
# 或直接用字体名设单个控件
ac.setCustomFont(gearLabel, "DS-DIGITAL", 1, 1)
```

**三个关键坑**：

- 字体文件需放在游戏 **`content/font`** 目录（car mod 是 `fonts`）。
- 代码里的字体名是**双击字体文件显示的内部 family 名**，不是文件名——文件 `unispace bd.ttf`
  → 写 `"Unispace"`。
- 换字体后**字号多半要重调**，因为不同字形尺寸不同。
- 同样按 `setFontColor` 的套路 **try/except 静默降级**处理（不一定每种控件/版本都支持）。

### 6. 窗口最小尺寸保护

若控件特意摆到很深的位置（如 y=515）、而用户 / INI 保存了更小的窗口，控件会被裁切。可在
`acMain` 里把窗口尺寸钳制到一个**由内容反推**的最小值：

```python
if windowx < 280:
    windowx = 280
if windowy < 530:
    windowy = 530
```

## 与 ACLIB 的关系

若觉得手动算坐标太痛苦，可改用 **ACLIB**（见 [07](07-aclib-framework.md)）。其 `ACGrid`
是真正的网格布局引擎：`ACGrid(rows, cols, parent)` 把 App 内容区均分成单元格，
`grid.add(widget, x, y)` 自动定位。但 ACLIB 是另一套加载模型（`ACLIB_*.py` 文件、`ACApp` 类 +
`update(delta)`），不经过 `acMain`，且本仓库不依赖它。

---

**参考**：

- [02-ac-module-api.md](02-ac-module-api.md)（控件 API 完整清单）
- [07-aclib-framework.md](07-aclib-framework.md)（ACLIB 网格布局）
- 本项目 `AutoCam.py` 中 `setLabelColor` / `buildHudWindow` / `acMain` 窗口构建部分
