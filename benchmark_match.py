"""
基准测试：模板匹配 vs 像素点对比的速度差异
在招募页面运行此脚本，测试抢环检测的实际耗时
"""
import cv2
import numpy as np
import pyautogui
import time
import os

# 配置
TEMPLATE_DIR = "templates"
GAME_WINDOW = None  # 将从窗口获取

def get_game_window():
    from win32 import win32gui
    hwnd = win32gui.FindWindow(None, "抖音")
    if hwnd:
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        return (left, top, right-left, bottom-top)
    return None

def take_screenshot_cv(region):
    screenshot = pyautogui.screenshot(region=region)
    return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

def benchmark():
    window = get_game_window()
    if not window:
        print("未找到游戏窗口")
        return
    print(f"游戏窗口: {window}")
    
    # 加载模板
    template_path = os.path.join(TEMPLATE_DIR, "huanqiu.png")
    template = cv2.imread(template_path)
    if template is None:
        print("无法加载 huanqiu.png 模板")
        return
    
    in_team_template = cv2.imread(os.path.join(TEMPLATE_DIR, "in-huanqiu-team.png"))
    
    print(f"模板尺寸: {template.shape}")
    print(f"模板像素数: {template.shape[0] * template.shape[1]}")
    print()
    
    # ========== 测试1：截图耗时 ==========
    times = []
    for _ in range(20):
        t0 = time.perf_counter()
        img = take_screenshot_cv(window)
        t1 = time.perf_counter()
        times.append(t1 - t0)
    print(f"【截图耗时】平均: {np.mean(times)*1000:.1f}ms, 最小: {np.min(times)*1000:.1f}ms, 最大: {np.max(times)*1000:.1f}ms")
    print(f"  截图尺寸: {img.shape}")
    print()
    
    # 取一张截图用于后续测试
    img = take_screenshot_cv(window)
    
    # ========== 测试2：全图模板匹配（matchTemplate）==========
    times = []
    for _ in range(100):
        t0 = time.perf_counter()
        result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= 0.95)
        matches = list(zip(*locations[::-1]))
        t1 = time.perf_counter()
        times.append(t1 - t0)
    print(f"【全图模板匹配 matchTemplate】平均: {np.mean(times)*1000:.2f}ms, 最小: {np.min(times)*1000:.2f}ms")
    print(f"  找到 {len(matches)} 个匹配位置")
    print()
    
    # ========== 测试3：全图模板匹配 find_all（huanqiu + in-huanqiu-team）==========
    times = []
    for _ in range(100):
        t0 = time.perf_counter()
        # 模拟当前_poor_mode_loop的检测：先in_team再huanqiu
        r1 = cv2.matchTemplate(img, in_team_template, cv2.TM_CCOEFF_NORMED)
        _, max_val1, _, _ = cv2.minMaxLoc(r1)
        r2 = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(r2 >= 0.95)
        matches = list(zip(*locations[::-1]))
        t1 = time.perf_counter()
        times.append(t1 - t0)
    print(f"【当前流程: in_team检测 + huanqiu匹配】平均: {np.mean(times)*1000:.2f}ms")
    print()
    
    # ========== 测试4：ROI区域匹配（只在已知位置附近搜索）==========
    # 从之前的匹配结果获取大致位置
    if matches:
        print(f"  已知匹配位置（相对窗口）: {matches[:5]}")
    
    # 如果有已知位置，测试ROI裁剪后的匹配速度
    if matches:
        th, tw = template.shape[:2]
        roi_margin = 20  # 上下左右扩展20像素
        times_roi = []
        for _ in range(100):
            t0 = time.perf_counter()
            found = 0
            # 在几个固定Y位置检查
            for x, y in matches[:4]:
                y1 = max(0, y - roi_margin)
                y2 = min(img.shape[0], y + th + roi_margin)
                x1 = max(0, x - roi_margin)
                x2 = min(img.shape[1], x + tw + roi_margin)
                roi = img[y1:y2, x1:x2]
                if roi.shape[0] >= th and roi.shape[1] >= tw:
                    r = cv2.matchTemplate(roi, template, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, _ = cv2.minMaxLoc(r)
                    if max_val >= 0.95:
                        found += 1
            t1 = time.perf_counter()
            times_roi.append(t1 - t0)
        print(f"【ROI区域匹配（已知位置附近）】平均: {np.mean(times_roi)*1000:.2f}ms, 找到 {found} 个")
        print()
    
    # ========== 测试5：像素点对比 ==========
    # 从模板中取几个关键像素作为特征
    if matches:
        # 取模板的几个特征像素点（中心、四角等）
        th, tw = template.shape[:2]
        sample_points = [
            (tw//2, th//2),       # 中心
            (tw//4, th//4),       # 左上
            (3*tw//4, th//4),     # 右上
            (tw//4, 3*th//4),     # 左下
            (3*tw//4, 3*th//4),   # 右下
            (tw//2, th//4),       # 上中
            (tw//2, 3*th//4),     # 下中
        ]
        # 获取模板中这些点的颜色
        template_colors = [template[py, px].tolist() for px, py in sample_points]
        
        times_pixel = []
        color_threshold = 30  # 颜色差异阈值
        for _ in range(100):
            t0 = time.perf_counter()
            found = 0
            for mx, my in matches[:4]:
                match = True
                for (spx, spy), ref_color in zip(sample_points, template_colors):
                    px, py = mx + spx, my + spy
                    if 0 <= py < img.shape[0] and 0 <= px < img.shape[1]:
                        pixel = img[py, px]
                        diff = sum(abs(int(pixel[c]) - ref_color[c]) for c in range(3))
                        if diff > color_threshold:
                            match = False
                            break
                if match:
                    found += 1
            t1 = time.perf_counter()
            times_pixel.append(t1 - t0)
        print(f"【像素点对比（7个采样点）】平均: {np.mean(times_pixel)*1000:.3f}ms, 找到 {found} 个")
        print()
    
    # ========== 汇总 ==========
    print("=" * 60)
    print("汇总对比：")
    print(f"  截图耗时:           {np.mean(times)*1000:.1f}ms  ← 瓶颈！无法优化")
    screenshot_time = np.mean(times) * 1000
    
    match_time = np.mean([t*1000 for t in times])
    print(f"  全图模板匹配:       ~{np.mean([t*1000 for t in times]):.1f}ms")
    if matches:
        roi_time = np.mean(times_roi) * 1000
        pixel_time = np.mean(times_pixel) * 1000
        print(f"  ROI区域匹配:        ~{roi_time:.2f}ms")
        print(f"  像素点对比:         ~{pixel_time:.3f}ms")
        print()
        print(f"  像素对比 vs 全图匹配 速度提升: {match_time/pixel_time:.0f}x")
        print(f"  但相对总循环时间（截图{screenshot_time:.0f}ms + 匹配）的提升:")
        total_old = screenshot_time + match_time * 2  # in_team + huanqiu
        total_new = screenshot_time + pixel_time
        print(f"    改前每轮: ~{total_old:.0f}ms")
        print(f"    改后每轮: ~{total_new:.0f}ms")
        print(f"    实际提升: {total_old/total_new:.1f}x")

if __name__ == "__main__":
    print("请确保游戏窗口已打开并在招募页面")
    print("3秒后开始测试...")
    time.sleep(3)
    benchmark()
