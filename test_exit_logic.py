"""
测试脚本：验证 game_bot.py 中退出队伍逻辑（第564-598行）

测试内容：
1. 截图后在底部1/4区域查找退出按钮（leave-button.png / return-1.png）
2. 点击退出按钮后，在中间区域查找确认按钮（sure.png）
3. 记录每步耗时和匹配结果

使用方法：
1. 先手动进入一个不想打的环球副本队伍中
2. 运行此脚本：python test_exit_logic.py
3. 观察输出，确认按钮是否被正确识别和点击
"""

import sys
import os

# 强制刷新所有print输出
def fprint(*args, **kwargs):
    print(*args, **kwargs, flush=True)

try:
    fprint("[INIT] 正在导入依赖...")
    import win32api
    import win32con
    fprint("[INIT] win32api/win32con OK")
    import pyautogui
    fprint("[INIT] pyautogui OK")
    import cv2
    fprint("[INIT] cv2 OK")
    import numpy as np
    fprint("[INIT] numpy OK")
    from win32 import win32gui
    fprint("[INIT] win32gui OK")
    import time
    import threading
    fprint("[INIT] 所有依赖导入成功")
except Exception as e:
    fprint(f"[ERROR] 导入依赖失败: {e}")
    sys.exit(1)


class ExitLogicTester:
    def __init__(self, game_title="抖音"):
        self.game_title = game_title
        self.game_window = None
        
        # 获取templates目录路径
        if getattr(sys, 'frozen', False):
            self.template_dir = os.path.join(sys._MEIPASS, "templates")
        else:
            self.template_dir = "templates"
        
        self._template_cache = {}
        self._latest_img = None
        self._img_lock = threading.Lock()
        self.running = True

    def find_game_window(self):
        """查找并激活游戏窗口"""
        hwnd = win32gui.FindWindow(None, self.game_title)
        if hwnd:
            win32gui.SetForegroundWindow(hwnd)
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            self.game_window = (left, top, right - left, bottom - top)
            print(f"[INFO] 找到游戏窗口: {self.game_window}")
            return True
        else:
            print("[ERROR] 未找到游戏窗口")
            return False

    def _load_template(self, template_name):
        """加载并缓存模板图像"""
        if template_name not in self._template_cache:
            template_path = os.path.join(self.template_dir, template_name)
            template = cv2.imread(template_path)
            if template is None:
                print(f"[ERROR] 无法加载模板: {template_path}")
            self._template_cache[template_name] = template
        return self._template_cache[template_name]

    def _take_screenshot_cv(self):
        """截取游戏窗口画面并转换为OpenCV格式"""
        if not self.game_window:
            return None
        screenshot = pyautogui.screenshot(region=self.game_window)
        return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    def _find_template_in_image(self, img, template_name, threshold=0.95):
        """在已有截图中查找模板"""
        template = self._load_template(template_name)
        if template is None:
            return None
        result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        if max_val >= threshold:
            h, w = template.shape[:2]
            center_x = self.game_window[0] + max_loc[0] + w // 2
            center_y = self.game_window[1] + max_loc[1] + h // 2
            return (center_x, center_y, max_val)
        return None

    def click_fast(self, x, y):
        """快速点击"""
        win32api.SetCursorPos((int(x), int(y)))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    def start_screenshot_thread(self):
        """启动独立截图线程"""
        def _screenshot_loop():
            while self.running:
                img = self._take_screenshot_cv()
                if img is not None:
                    with self._img_lock:
                        self._latest_img = img
        
        thread = threading.Thread(target=_screenshot_loop, daemon=True)
        thread.start()
        print("[INFO] 截图线程已启动")
        return thread

    def test_exit_logic(self, dry_run=True):
        """
        测试退出逻辑
        
        参数:
            dry_run: True=只检测不点击，False=实际执行点击
        """
        print(f"\n{'='*60}")
        print(f"  退出逻辑测试 {'(模拟模式，不实际点击)' if dry_run else '(实际执行模式)'}")
        print(f"{'='*60}\n")
        
        if not self.find_game_window():
            return
        
        # 启动截图线程
        screenshot_thread = self.start_screenshot_thread()
        time.sleep(1)  # 等待第一帧截图
        
        # ========== 步骤1：获取截图 ==========
        print("[步骤1] 获取当前截图...")
        with self._img_lock:
            img = self._latest_img
        if img is None:
            print("[ERROR] 无法获取截图")
            return
        
        h, w = img.shape[:2]
        print(f"  截图尺寸: {w}x{h}")
        
        # 保存原始截图
        cv2.imwrite("test_screenshot_original.png", img)
        print(f"  原始截图已保存: test_screenshot_original.png")
        
        # ========== 步骤2：在底部1/4区域查找退出按钮 ==========
        print(f"\n[步骤2] 在底部1/4区域查找退出按钮...")
        offset_y = 3 * h // 4
        roi_bottom = img[offset_y:h, 0:w]
        print(f"  ROI区域: y=[{offset_y}:{h}], x=[0:{w}], 尺寸={roi_bottom.shape[1]}x{roi_bottom.shape[0]}")
        
        # 保存ROI截图
        cv2.imwrite("test_screenshot_roi_bottom.png", roi_bottom)
        print(f"  底部ROI截图已保存: test_screenshot_roi_bottom.png")
        
        exit_pos = None
        exit_btn_name = None
        for btn in ["leave-button.png", "return-1.png"]:
            t_start = time.time()
            result = self._find_template_in_image(roi_bottom, btn)
            t_elapsed = (time.time() - t_start) * 1000
            
            if result:
                pos_x, pos_y, score = result
                # 修正坐标：ROI坐标 -> 绝对坐标
                exit_pos = (pos_x, pos_y + offset_y)
                exit_btn_name = btn
                print(f"  [MATCH] {btn}: 相似度={score:.4f}, ROI坐标=({pos_x:.0f},{pos_y:.0f}), 绝对坐标=({exit_pos[0]:.0f},{exit_pos[1]:.0f}), 耗时={t_elapsed:.1f}ms")
                break
            else:
                print(f"  [MISS]  {btn}: 未匹配到, 耗时={t_elapsed:.1f}ms")
        
        if exit_pos:
            print(f"\n  >>> 找到退出按钮: {exit_btn_name} @ ({exit_pos[0]:.0f}, {exit_pos[1]:.0f})")
            
            if not dry_run:
                print(f"  >>> 点击退出按钮...")
                self.click_fast(*exit_pos)
            else:
                print(f"  >>> [模拟] 不实际点击")
        else:
            print(f"\n  >>> 未找到退出按钮 (leave-button.png 和 return-1.png 都未匹配)")
            print(f"  >>> 等待0.2秒后返回")
            if not dry_run:
                time.sleep(0.2)
            self.running = False
            return
        
        # ========== 步骤3：等待确认弹窗 ==========
        print(f"\n[步骤3] 等待确认弹窗 (sure.png)...")
        sure_found = False
        
        for i in range(20):
            sleep_time = 0.05 if i < 10 else 0.1
            if not dry_run:
                time.sleep(sleep_time)
            else:
                time.sleep(0.5)  # 模拟模式下每0.5秒检查一次
            
            with self._img_lock:
                sure_img = self._latest_img
            
            if sure_img is None:
                print(f"  第{i+1}次: 截图为空, 跳过")
                continue
            
            h_s, w_s = sure_img.shape[:2]
            offset_y_sure = h_s // 3
            roi_center = sure_img[offset_y_sure:3*h_s//4, 0:w_s]
            
            t_start = time.time()
            result = self._find_template_in_image(roi_center, "sure.png")
            t_elapsed = (time.time() - t_start) * 1000
            
            if result:
                pos_x, pos_y, score = result
                sure_pos_abs = (pos_x, pos_y + offset_y_sure)
                print(f"  第{i+1}次: [MATCH] sure.png: 相似度={score:.4f}, 绝对坐标=({sure_pos_abs[0]:.0f},{sure_pos_abs[1]:.0f}), 耗时={t_elapsed:.1f}ms")
                
                if not dry_run:
                    print(f"  >>> 点击确认按钮...")
                    self.click_fast(*sure_pos_abs)
                    print(f"  >>> 等待1.0秒过场动画...")
                    time.sleep(1.0)
                else:
                    print(f"  >>> [模拟] 不实际点击确认按钮")
                
                sure_found = True
                break
            else:
                if i < 3 or i % 5 == 0:  # 只打印部分结果，避免刷屏
                    print(f"  第{i+1}次: [MISS] sure.png 未匹配, 耗时={t_elapsed:.1f}ms")
        
        if not sure_found:
            print(f"\n  >>> 20次检查后仍未找到确认按钮 (sure.png)")
            # 保存最后一帧截图用于调试
            with self._img_lock:
                debug_img = self._latest_img
            if debug_img is not None:
                cv2.imwrite("test_screenshot_debug.png", debug_img)
                print(f"  调试截图已保存: test_screenshot_debug.png")
        
        # ========== 测试结果汇总 ==========
        print(f"\n{'='*60}")
        print(f"  测试结果汇总")
        print(f"{'='*60}")
        print(f"  退出按钮: {'找到 (' + exit_btn_name + ')' if exit_pos else '未找到'}")
        print(f"  确认按钮: {'找到' if sure_found else '未找到'}")
        print(f"  运行模式: {'模拟' if dry_run else '实际执行'}")
        print(f"{'='*60}\n")
        
        self.running = False


if __name__ == "__main__":
    import argparse
    
    fprint("[MAIN] 脚本启动")
    
    parser = argparse.ArgumentParser(description="测试退出队伍逻辑")
    parser.add_argument("--title", default="抖音", help="游戏窗口标题")
    parser.add_argument("--execute", action="store_true", help="实际执行点击（默认只检测不点击）")
    args = parser.parse_args()
    
    fprint(f"[MAIN] 游戏窗口标题: {args.title}")
    fprint(f"[MAIN] 执行模式: {'实际执行' if args.execute else '模拟检测'}")
    
    try:
        tester = ExitLogicTester(game_title=args.title)
        tester.test_exit_logic(dry_run=not args.execute)
    except Exception as e:
        fprint(f"[ERROR] 运行出错: {e}")
        import traceback
        traceback.print_exc()
