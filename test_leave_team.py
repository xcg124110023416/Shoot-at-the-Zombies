"""
单独测试：检测不想打的环并快速退出
使用方法：
1. 游戏停留在队伍界面（寰球救援-难度XX 的页面）
2. 修改下面的 TARGET_LEVELS 为你不想打的环
3. 运行此脚本
"""
import cv2
import numpy as np
import pyautogui
import win32api
import win32con
from win32 import win32gui
import time
import os

# ========== 配置 ==========
GAME_TITLE = "抖音"
TEMPLATE_DIR = "templates"
THRESHOLD = 0.98  # 模板匹配阈值
TARGET_LEVELS = [17, 18, 19, 20]  # 不想打的环（修改这里）

# ========== 工具函数 ==========
def find_game_window():
    hwnd = win32gui.FindWindow(None, GAME_TITLE)
    if hwnd:
        rect = win32gui.GetWindowRect(hwnd)
        return (rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1])
    return None

def take_screenshot(window):
    screenshot = pyautogui.screenshot(region=window)
    return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

_template_cache = {}
def load_template(name):
    if name not in _template_cache:
        path = os.path.join(TEMPLATE_DIR, name)
        tmpl = cv2.imread(path)
        if tmpl is None:
            print(f"  ⚠ 模板不存在: {path}")
        _template_cache[name] = tmpl
    return _template_cache[name]

def find_in_image(img, template_name, threshold=THRESHOLD):
    template = load_template(template_name)
    if template is None:
        return None
    result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    if max_val >= threshold:
        h, w = template.shape[:2]
        return (max_loc[0] + w // 2, max_loc[1] + h // 2, max_val)
    return None

def click_fast(window, rel_x, rel_y):
    abs_x = window[0] + rel_x
    abs_y = window[1] + rel_y
    win32api.SetCursorPos((int(abs_x), int(abs_y)))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    print(f"  ✓ 点击: ({abs_x}, {abs_y})")

# ========== 主测试 ==========
def test():
    print("=" * 50)
    print("测试：检测不想打的环并退出")
    print(f"不想打的环: {TARGET_LEVELS}")
    print("=" * 50)
    
    # 1. 找游戏窗口
    window = find_game_window()
    if not window:
        print("❌ 未找到游戏窗口")
        return
    print(f"✓ 游戏窗口: {window}")
    
    # 2. 截图
    print("\n--- 截图 ---")
    img = take_screenshot(window)
    print(f"  截图尺寸: {img.shape}")
    
    # 3. 检测是否在队伍中
    print("\n--- 检测是否在队伍中 ---")
    in_team = find_in_image(img, "in-huanqiu-team.png")
    if in_team:
        print(f"  ✓ 检测到 in-huanqiu-team.png (置信度: {in_team[2]:.3f})")
    else:
        print(f"  ✗ 未检测到 in-huanqiu-team.png")
        print("  提示: 请确保游戏在队伍界面，且模板图片正确")
        # 即使没检测到也继续测试其他模板
    
    # 4. 检测具体是哪个环
    print("\n--- 检测环球副本等级 ---")
    detected_level = None
    for level in range(1, 21):
        tmpl_name = f"huanqiu-{level}.png"
        if not os.path.exists(os.path.join(TEMPLATE_DIR, tmpl_name)):
            continue
        result = find_in_image(img, tmpl_name)
        if result:
            is_target = level in TARGET_LEVELS
            mark = "🎯 命中！" if is_target else ""
            print(f"  ✓ 检测到 {tmpl_name} (置信度: {result[2]:.3f}) {mark}")
            if is_target and detected_level is None:
                detected_level = level
        # 列出所有可用的模板
    
    if detected_level:
        print(f"\n>>> 命中不想打的环: 环球{detected_level}")
    else:
        print(f"\n>>> 未命中不想打的环（当前环不在排除列表中）")
    
    # 5. 查找退出按钮
    print("\n--- 查找退出按钮 ---")
    for btn in ["leave-button.png", "return-1.png"]:
        result = find_in_image(img, btn)
        if result:
            print(f"  ✓ 找到 {btn} 位置=({result[0]}, {result[1]}) 置信度={result[2]:.3f}")
        else:
            print(f"  ✗ 未找到 {btn}")
    
    # 6. 如果命中不想打的环，执行退出
    if detected_level:
        print("\n--- 执行退出 ---")
        exit_pos = None
        for btn in ["leave-button.png", "return-1.png"]:
            exit_pos = find_in_image(img, btn)
            if exit_pos:
                print(f"  使用 {btn} 退出")
                break
        
        if exit_pos:
            input("  按回车键执行点击退出（或Ctrl+C取消）...")
            click_fast(window, exit_pos[0], exit_pos[1])
            
            # 等待确认弹窗
            time.sleep(0.3)
            img2 = take_screenshot(window)
            sure_pos = find_in_image(img2, "sure.png")
            if sure_pos:
                print(f"  ✓ 找到确认按钮")
                click_fast(window, sure_pos[0], sure_pos[1])
                print("  ✓ 已点击确认，退出完成！")
            else:
                print("  ✗ 未找到确认按钮 (sure.png)")
        else:
            print("  ✗ 未找到任何退出按钮")
    
    print("\n测试完成。")

if __name__ == "__main__":
    test()
