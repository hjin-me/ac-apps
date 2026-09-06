# 02 · `ac` 模块函数 API 参考

> 以下为社区整理的**非官方** AC Python 文档（`inofficial_acpythondoc_v2`）与
> [ac-stubs](https://github.com/rikby/ac-stubs) 类型桩中提取的 `ac` 模块函数清单。
> 标注 ⭐ 的是本项目 AutoCam 实际使用到的函数。

## 车辆状态与遥测

| 函数 | 说明 |
| :--- | :--- |
| `ac.getCarState(<CAR_ID>, <INFO_ID>, <OPTIONAL_ID>)` ⭐ | 返回车辆状态（标量 / 3D/4D 向量 / 轮胎特定值）。`INFO_ID` 用 `acsys.CS.*`，见 [03](03-acsys-constants.md)。可选第三参用于轮胎，如 FL/FR/RL/RR |
| `ac.getCarName(<CAR_ID>)` ⭐ | 车辆名称（字符串） |
| `ac.getDriverName(<CAR_ID>)` | 车手名（字符串） |
| `ac.getTrackName(<CAR_ID>)` | 赛道名 |
| `ac.getTrackConfiguration(<CAR_ID>)` | 赛道配置 |
| `ac.getTrackLength(<CAR_ID>)` ⭐ | 赛道长度（米） |
| `ac.getCarSkin(carID)` | 车辆皮肤 |
| `ac.getDriverNationCode(carID)` | 车手国籍代码 |
| `ac.getLastSplits(<CAR_ID>)` / `ac.getCurrentSplits(carID)` | 计时点（Python list） |
| `ac.getWindSpeed()` / `ac.getWindDirection()` | 风速 / 风向 |
| `ac.getCarsCount()` ⭐ | 场上车辆数量 |
| `ac.isConnected(<CAR_ID>)` ⭐ | 车辆是否在线连接 |
| `ac.isCarInPitlane()` ⭐ | 是否在维修道（别名 `isCarInPitline`） |
| `ac.isAIControlled()` | 是否 AI 控制 |
| `ac.isAcLive()` | 是否实时 AC 会话 |

## 调试与日志

| 函数 | 说明 |
| :--- | :--- |
| `ac.log(<VALUE>)` ⭐ | 写入 `py_log.txt` |
| `ac.console(<VALUE>)` ⭐ | 输出到游戏内控制台（Home 键） |

## 窗口 / App 管理

| 函数 | 说明 |
| :--- | :--- |
| `ac.newApp(<VALUE>)` ⭐ | 创建 App 窗口，返回窗口 ID |
| `ac.setTitle(CONTROL_ID, TITLE)` ⭐ | 设置标题 |
| `ac.setSize(CONTROL_ID, W, H)` ⭐ | 设置尺寸 |
| `ac.setPosition(CONTROL_ID, X, Y)` ⭐ | 设置位置 |
| `ac.getPosition(CONTROL_ID)` | 返回 `(x, y)` |
| `ac.setIconPosition(CONTROL_ID, X, Y)` ⭐ | 设置任务栏图标偏移（`0,-9000` 可隐藏） |
| `ac.setTitlePosition(CONTROL_ID, X, Y)` | 标题位置 |
| `ac.setText(CONTROL_ID, VALUE)` ⭐ | 设置文本 |
| `ac.getText(CONTROL_ID)` | 读取文本 |
| `ac.setBackgroundOpacity(CONTROL_ID, VALUE)` ⭐ | 背景透明度（0–1） |
| `ac.setBackgroundColor(CONTROL_ID, R, G, B)` | 背景颜色 |
| `ac.setBackgroundTexture(CONTROL_ID, PATH)` | 背景纹理（相对 AC 根目录） |
| `ac.drawBackground(CONTROL_ID, 0/1)` | 是否绘制背景 |
| `ac.drawBorder(CONTROL_ID, 0/1)` ⭐ | 是否绘制边框 |
| `ac.setVisible(CONTROL_ID, 0/1)` | 显示/隐藏 |
| `ac.setFontAlignment(CONTROL_ID, "left/right/center")` | 文本对齐 |
| `ac.setFontColor(CONTROL_ID, R, G, B, A)` | 字体颜色（0–1），注意不是 `addOnClickedListener` |
| `ac.setFontSize` | 设置字号（注：在部分文档中缺失，本仓库已使用） |
| `ac.addOnAppActivatedListener(CONTROL_ID, fn)` | App 激活回调 |
| `ac.addOnAppDismissedListener(CONTROL_ID, fn)` | App 关闭回调 |
| `ac.addRenderCallback(CONTROL_ID, fn)` | 渲染完成回调 |

## 控件

### Button
| 函数 | 说明 |
| :--- | :--- |
| `ac.addButton(WINDOW, TEXT)` ⭐ | 添加按钮，返回 ID |
| `ac.addOnClickedListener(CTRL, fn)` ⭐ | 点击回调 |

### Spinner（数值调节器）
| 函数 | 说明 |
| :--- | :--- |
| `ac.addSpinner(WINDOW, VALUE)` ⭐ | 添加 spinner |
| `ac.setRange(CTRL, MIN, MAX)` ⭐ | 取值范围 |
| `ac.setValue(CTRL, VALUE)` ⭐ | 设置当前值 |
| `ac.getValue(CTRL)` | 读取当前值 |
| `ac.setStep(CTRL, VALUE)` ⭐ | 步进 |
| `ac.addOnValueChangeListener(CTRL, fn)` ⭐ | 数值变化回调（回调接收新值） |

### CheckBox
| 函数 | 说明 |
| :--- | :--- |
| `ac.addCheckBox(WINDOW, TEXT)` ⭐ | 添加勾选框 |
| `ac.addOnClickedListener(CTRL, fn)` ⭐ | 点击回调 |
| `ac.addOnCheckBoxChanged(CTRL, fn)` | 勾选变化回调（回调收到 name 与 1/-1） |

> ⚠️ 实测（AC 1.14.3）**没有** `ac.isChecked` 与 `ac.setChecked` —— 调用会抛 `AttributeError`
> （`module object has no attribute isChecked`）。这两项是社区文档检索产物，实机不存在。
> 本项目因此把布尔项渲染为**自带状态的自管理按钮**（`addButton` + `setText` 反映 ON/OFF），
> 状态以 Python 全局为准，点击时翻转并刷新按钮文字，避免依赖不存在的勾选读写接口。

### Graph（图表）
| 函数 | 说明 |
| :--- | :--- |
| `ac.addGraph(WINDOW, VALUE)` | 添加图表 |
| `ac.addSerieToGraph(CTRL, R, G, B)` | 添加数据序列 |
| `ac.addValueToGraph(CTRL, SERIE_INDEX, VALUE)` | 追加数值 |
| `ac.setRange(CTRL, MIN, MAX, MAX_POINTS)` | 设置范围与点数 |

### ProgressBar / TextInput / ListBox / TextBox
| 控件 | 函数 |
| :--- | :--- |
| ProgressBar | `ac.addProgressBar(WINDOW, VALUE)` |
| TextInput | `ac.addTextInput(WINDOW, VALUE)`、`ac.setFocus(CTRL, 0/1)`、`ac.addOnValidateListener(CTRL, fn)`（回车事件；注意 `addInputText` 无效） |
| ListBox | `ac.addListBox(WINDOW, NAME)`、`ac.addItem(CTRL, NAME)`、`ac.removeItem(CTRL, ID)`、`ac.getItemCount(CTRL)`、`ac.setItemNumberPerPage(CTRL, N)`、`ac.highlightListBoxItem(CTRL, ID)`、`ac.addOnListBoxSelectionListener(CTRL, fn)`、`ac.getSelectedItems(CTRL)`、`ac.setAllowMultiSelection(CTRL, 0/1)` |
| TextBox | `ac.addTextBox(WINDOW, NAME)` — 文档标注 **尚不可用** |

## 图形 / 渲染

| 函数 | 说明 |
| :--- | :--- |
| `ac.newTexture(PATH)` | 从 AC 安装目录加载纹理，返回 ID |
| `ac.glBegin(PRIMITIVE_ID)` | 开始图元（0=lines, 1=line strip, 2=triangles, 3=quads） |
| `ac.glEnd()` | 结束图元 |
| `ac.glVertex2f(X, Y)` | 顶点 |
| `ac.glColor3f(R, G, B)` / `ac.glColor4f(R, G, B, A)` | 颜色（0–1） |
| `ac.glQuad(X, Y, W, H)` | 绘制四边形 |
| `ac.glQuadTextured(X, Y, W, H, TEXTURE_ID)` | 纹理四边形 |

## Free Camera（2020 更新）

```python
ac.freeCameraSetClearColor(r, g, b, alpha)
ac.freeCameraMoveForward(float)
ac.freeCameraMoveRight(float)
ac.freeCameraMoveUpWorld(float)
ac.freeCameraRotatePitch(float)
ac.freeCameraRotateHeading(float)
ac.freeCameraRotateRoll(float)
```

## 会话 / 其他（2020 更新）

- `ac.restart()` — 重启。
- `ac.sendChatMessage(string_msg)` ⭐ — 发送聊天消息/广播文本（本项目用于发送 promo 文本）。
- `ac.getCarEngineBrakeCount()` / `ac.getCarPowerControllerCount()` — 引擎刹车 / 动力控制器数量。
- `ac.addOnChatMessageListener(WindowID, fn)` — 聊天消息回调。
- `ac.getServerName()` / `ac.getServerIP()` ⭐ — 服务器名 / IP（本项目用于加载 IP 相关配置）。
- `ac.focusCar(CAR_ID)` ⭐、`ac.getFocusedCar()` ⭐、`ac.setCameraMode(m)` ⭐、
  `ac.setCameraCar(CAM_ID, CAR_ID)` ⭐、`ac.getCameraCarCount(CAR_ID)` ⭐、
  `ac.getCameraMode()` ⭐、`ac.isCameraOnBoard(CAR_ID)` ⭐ —
  相机与聚焦控制，详见 [05](05-camera-and-car-control.md)。
- `ac.getCarRealTimeLeaderboardPosition(CAR_ID)` ⭐ — 实时排名位置。

> 说明：上述 `focusCar` / `setCameraMode` / `getCarRealTimeLeaderboardPosition` 等函数在旧版
> 文档中缺失，属于 AC 较高版本或 CSP 提供的 API。一份可离线校验的完整接口可安装
> `pip install ac-stubs` 生成类型桩，供 IDE 自动补全。

---

**参考**：

- [rikby/ac-stubs（含 `ACPythonDoc.txt` 完整接口 dump）](https://github.com/rikby/ac-stubs)
- [ACPythonDocumentation（非官方文档）](https://www.scribd.com/document/629250993/ACPythonDocumentation)
