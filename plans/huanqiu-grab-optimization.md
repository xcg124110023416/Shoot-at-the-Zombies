# 穷逼模式抢环流程优化方案（最终版）

## 优化清单

| # | 优化项 | 状态 | 说明 |
|---|--------|------|------|
| 1 | 连点密度+微间隔 | ✅ 实施 | 5次→10次，加5ms间隔 |
| 2 | 环等级检测提前退出 | ✅ 实施 | 保留全量检测，匹配度>=0.99时提前退出 |
| 3 | 退出队伍等待优化 | ✅ 实施 | 前10次0.05s，后10次0.1s；确认后等待1.5s→1.0s |
| 4 | 等待队长响应时间降低 | ✅ 实施 | 1s→0.3s |
| 5 | 招募页扫描用像素采样 | ✅ 实施 | 用 `_fast_find_huanqiu` 替代 matchTemplate |
| 6 | 离队后渐进式等待 | ✅ 实施 | 固定2s→每0.5s检测画面是否加载完成 |
| 7 | 多点偏移点击 | ✅ 实施 | 缓存坐标±3像素随机偏移 |
| 8 | 降低定期检测频率 | ✅ 实施 | 招募页检测从每200次改为每500次 |

---

## 详细实施说明

### 优化1：连点密度+微间隔

**文件**: `game_bot.py` 第629-631行

**当前代码**:
```python
for _ in range(5):
    self.click_fast(*self._cached_join_pos)
```

**改为**:
```python
cx, cy = self._cached_join_pos
for _ in range(10):
    ox = cx + random.randint(-3, 3)
    oy = cy + random.randint(-3, 3)
    self.click_fast(ox, oy)
    time.sleep(0.005)
```

**说明**: 连点次数5→10，每次加5ms微间隔防止事件合并，同时包含±3像素随机偏移（合并了优化7）。

---

### 优化2：环等级检测提前退出

**文件**: `game_bot.py` 第537-550行

**当前代码**:
```python
for level in range(1, 21):
    ...
    if max_val > best_score and max_val >= 0.90:
        best_score = max_val
        best_level = level
```

**改为**:
```python
for level in range(1, 21):
    ...
    if max_val > best_score and max_val >= 0.90:
        best_score = max_val
        best_level = level
        if max_val >= 0.99:  # 极高置信度，提前退出
            break
```

**说明**: 保留全量检测确保准确性，但匹配度达到0.99+时提前退出，最佳情况从20次降到1-3次。

---

### 优化3：退出队伍等待优化

**文件**: `game_bot.py` 第570-591行

**当前代码**:
```python
for _ in range(20):
    time.sleep(0.1)
    ...
    if sure_pos:
        self.click_fast(*sure_pos_abs)
        time.sleep(1.5)
        break
```

**改为**:
```python
for i in range(20):
    time.sleep(0.05 if i < 10 else 0.1)
    ...
    if sure_pos:
        self.click_fast(*sure_pos_abs)
        time.sleep(1.0)
        break
```

**说明**: 前10次快速检查（0.05s间隔），后10次正常速度（0.1s间隔）。确认后等待从1.5s降到1.0s。

---

### 优化4：等待队长响应时间降低

**文件**: `game_bot.py` 第609行

**当前代码**:
```python
time.sleep(1)
```

**改为**:
```python
time.sleep(0.3)
```

---

### 优化5：招募页扫描用像素采样

**文件**: `game_bot.py` 第620行

**当前代码**:
```python
raw_positions = self._find_all_templates_in_image(roi_huanqiu, "huanqiu.png", threshold=0.8)
positions = [(p[0], p[1] + offset_y_huanqiu) for p in raw_positions] if raw_positions else []
if positions:
    bottom_pos = max(positions, key=lambda p: p[1])
    self._cached_join_pos = bottom_pos
```

**改为**:
```python
raw_positions = self._fast_find_huanqiu(roi_huanqiu)
if raw_positions:
    bottom_pos = max(raw_positions, key=lambda p: p[1])
    self._cached_join_pos = (bottom_pos[0], bottom_pos[1] + offset_y_huanqiu)
```

**注意**: `_fast_find_huanqiu` 返回的坐标已经包含了 `self.game_window` 的偏移，而这里传入的 `roi_huanqiu` 是裁剪后的图像。需要确认 `_fast_find_huanqiu` 是否能正确处理裁剪后的图像坐标。如果不能，需要在调用前初始化像素采样点，或者直接使用 `_find_all_templates_in_image` 但降低阈值。

**备选方案**（如果像素采样不兼容ROI裁剪）:
```python
# 保持原有matchTemplate方式，但只找最下方一个
raw_positions = self._find_all_templates_in_image(roi_huanqiu, "huanqiu.png", threshold=0.8)
if raw_positions:
    bottom_pos = max(raw_positions, key=lambda p: p[1])
    self._cached_join_pos = (bottom_pos[0], bottom_pos[1] + offset_y_huanqiu)
```

---

### 优化6：离队后渐进式等待

**文件**: `game_bot.py` 第655-659行

**当前代码**:
```python
if getattr(self, '_was_in_team', False):
    print("检测到离开队伍，等待游戏过场动画...")
    time.sleep(2.0)
    self._was_in_team = False
    continue
```

**改为**:
```python
if getattr(self, '_was_in_team', False):
    print("检测到离开队伍，等待游戏过场动画...")
    self._was_in_team = False
    for _ in range(8):  # 最多等4秒
        time.sleep(0.5)
        with self._img_lock:
            check_img = self._latest_img
        if check_img is not None:
            h, w = check_img.shape[:2]
            roi_check = check_img[h//4:h//2, 0:w]
            if (self._find_template_in_image(roi_check, "recruitment-1.png") or
                self._find_template_in_image(check_img, "battling-2.png") or
                self._find_template_in_image(check_img, "battling-3.png")):
                break
    continue
```

---

### 优化7：多点偏移点击

已合并到优化1中实现。

---

### 优化8：降低定期检测频率

**文件**: `game_bot.py` 第635行

**当前代码**:
```python
if grab_count % 200 == 0:
```

**改为**:
```python
if grab_count % 500 == 0:
```

---

## 注意事项

1. **优化5的坐标问题**: `_fast_find_huanqiu` 内部使用 `self.game_window` 偏移计算绝对坐标，但传入的是裁剪后的ROI图像。实施时需要确认坐标是否正确，可能需要调整。
2. **优化6的模板检测**: 渐进式等待中检测 `battling-2.png` 和 `battling-3.png`，这些模板需要在 `_template_cache` 中预加载，否则首次加载会有额外开销。
3. **time.sleep精度**: Windows上 `time.sleep(0.005)` 实际精度约15ms，这是正常的。
