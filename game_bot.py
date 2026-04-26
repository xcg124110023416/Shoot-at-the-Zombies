import win32api
import win32con
from cv2.gapi.streaming import timestamp
import pyautogui
import cv2
import numpy as np
from win32 import win32gui
import time
import random
import os
import sys
import argparse
import json
from pynput import keyboard
import tkinter as tk
from tkinter import ttk, messagebox
import threading

SKILL_LIST = [
    {"name": "子弹", "template": ["skill.png", "skill-1.png"]},
    {"name": "温压弹", "template": ["skill-wyd.png", "skill-wyd-1.png"]},
    {"name": "干冰弹", "template": ["skill-gbd.png", "skill-gbd-1.png"]},
    {"name": "冰雹", "template": ["skill-bb.png", "skill-bb-1.png"]},
    {"name": "车", "template": ["skill-c.png", "skill-c-1.png"]},
    {"name": "电", "template": ["skill-d.png", "skill-d-1.png"]},
    {"name": "风刃", "template": ["skill-fr.png", "skill-fr-1.png"]},
    {"name": "激光", "template": ["skill-jg.png", "skill-jg-1.png"]},
    {"name": "龙卷风", "template": ["skill-ljf.png", "skill-ljf-1.png"]},
    {"name": "燃油", "template": ["skill-ry.png", "skill-ry-1.png"]},
    {"name": "射线", "template": ["skill-sx.png", "skill-sx-1.png"]},
    {"name": "无人机", "template": ["skill-wrj.png", "skill-wrj-1.png"]},
    {"name": "跃迁", "template": ["skill-yq.png", "skill-yq-1.png"]},
    {"name": "空投", "template": ["skill-kt.png", "skill-kt-1.png"]},
]

HUANQIU_TARGET_LEVELS = list(range(1, 21))

class GameBot:
    def __init__(self, game_title="游戏窗口标题", battle_time=0, battle_count=0, mode=0, priority_skills=None, rich_mode=0, target_huanqiu_levels=None, wait_time=60):
        self.running = True
        self.hotkey_listener = None
        """初始化游戏机器人"""
        self.game_title = game_title
        self.battle_time = battle_time
        self.battle_count = battle_count
        self.game_window = None
        self.screenshot_dir = "screenshots"
        self.priority_skills = priority_skills if priority_skills else []
        self.rich_mode = rich_mode
        self.target_huanqiu_levels = target_huanqiu_levels if target_huanqiu_levels else []
        self.expedition_in_team_max_time = time.time() + wait_time  # 最大等待时间，单位秒 当前时间戳+wait_time秒
        self.wait_time = wait_time  # 等待时间，单位秒
        
        # 获取templates目录路径（支持PyInstaller打包后的路径）
        if getattr(sys, 'frozen', False):
            # 如果是打包后的exe文件
            self.template_dir = os.path.join(sys._MEIPASS, "templates")
        else:
            # 如果是开发环境
            self.template_dir = "templates"
        
        self.mode = mode
        self._template_cache = {}  # 模板图像缓存，避免重复读取磁盘

        # 创建必要的目录
        os.makedirs(self.screenshot_dir, exist_ok=True)

    def find_game_window(self):
        """查找并激活游戏窗口"""
        hwnd = win32gui.FindWindow(None, self.game_title)
        if hwnd:
            win32gui.SetForegroundWindow(hwnd)
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            self.game_window = (left, top, right-left, bottom-top)
            print(f"找到游戏窗口: {self.game_window}")
            return True
        else:
            print("未找到游戏窗口")
            return False

    def resize_game_window(self, width=542, height=1010):
        """调整游戏窗口大小"""
        hwnd = win32gui.FindWindow(None, self.game_title)
        if hwnd:
            # 获取当前窗口位置
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            # 计算窗口边框和标题栏的大小
            # 先获取客户区大小
            client_rect = win32gui.GetClientRect(hwnd)
            client_width = client_rect[2] - client_rect[0]
            client_height = client_rect[3] - client_rect[1]
            # 计算边框和标题栏的总大小
            border_width = (right - left) - client_width
            border_height = (bottom - top) - client_height
            # 计算需要设置的窗口总大小
            window_width = width + border_width
            window_height = height + border_height
            # 设置新的窗口大小
            win32gui.MoveWindow(hwnd, left, top, window_width, window_height, True)
            # 更新游戏窗口信息
            self.game_window = (left, top, width, height)
            print(f"游戏窗口已调整为: {self.game_window}")
            return True
        else:
            print("未找到游戏窗口，无法调整大小")
            return False

    def find_fullscreen_window(self):
        """查找全屏幕窗口"""
        # 使用pyautogui获取屏幕尺寸，更简单可靠
        try:
            # 获取主屏幕尺寸
            width, height = pyautogui.size()
            left, top = 0, 0
            self.game_window = (left, top, width, height)
            print(f"全屏幕窗口: {self.game_window}")
            return True
        except Exception as e:
            print(f"获取屏幕尺寸时出错: {e}")
            # 如果pyautogui失败，尝试使用win32gui的基本方法
            try:
                width = win32gui.GetSystemMetrics(0)  # SM_CXSCREEN
                height = win32gui.GetSystemMetrics(1) # SM_CYSCREEN
                left, top = 0, 0
                self.game_window = (left, top, width, height)
                print(f"使用备用方法获取全屏幕窗口: {self.game_window}")
                return True
            except Exception as e2:
                print(f"备用方法也失败: {e2}")
                return False
    def take_screenshot(self):
        """截取游戏窗口画面"""
        if not self.game_window:
            if not self.find_game_window():
                return None
        
        screenshot = pyautogui.screenshot(region=self.game_window)
        return screenshot

    def save_screenshot(self, filename=None):
        """保存截图"""
        screenshot = self.take_screenshot()
        if screenshot:
            if not filename:
                filename = f"{self.screenshot_dir}/{int(time.time())}.png"
            screenshot.save(filename)
            print(f"截图已保存: {filename}")
            return filename
        return None

    def find_template(self, template_name, threshold=0.8):
        """在游戏窗口中查找模板图像"""
        template_path = os.path.join(self.template_dir, template_name)

        screenshot = self.take_screenshot()
        if not screenshot:
            return None
        
        # 转换为OpenCV格式
        img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        template = cv2.imread(template_path)
        
        if template is None:
            print(f"无法加载模板: {template_path}")
            return None
        
        # 模板匹配
        result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= threshold:
            h, w = template.shape[:2]
            center_x = self.game_window[0] + max_loc[0] + w // 2
            center_y = self.game_window[1] + max_loc[1] + h // 2
            print(f"找到匹配: {template_path}, 位置: ({center_x}, {center_y}), 相似度: {max_val:.2f}")
            return (center_x, center_y)
        
        # print(f"未找到匹配: {template_path}")
        return None
        # print(f"未找到匹配: {template_name}")
        return None

    def find_all_templates(self, template_name, threshold=0.8):
        """在游戏窗口中查找所有匹配的模板图像位置"""
        template_path = os.path.join(self.template_dir, template_name)
        
        screenshot = self.take_screenshot()
        if not screenshot:
            return []
        
        # 转换为OpenCV格式
        img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        template = cv2.imread(template_path)
        
        if template is None:
            print(f"无法加载模板: {template_path}")
            return []
        
        # 模板匹配
        result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
        
        # 获取所有超过阈值的匹配位置
        locations = np.where(result >= threshold)
        matches = []
        
        # 获取模板尺寸
        h, w = template.shape[:2]
        
        # 处理找到的匹配位置
        for pt in zip(*locations[::-1]):  # 切换x和y坐标
            center_x = self.game_window[0] + pt[0] + w // 2
            center_y = self.game_window[1] + pt[1] + h // 2
            matches.append((center_x, center_y))
            print(f"找到匹配: {template_path}, 位置: ({center_x}, {center_y})")
        
        return matches

    # ========== 截图复用优化方法 ==========
    def _load_template(self, template_name):
        """加载并缓存模板图像，避免每次都从磁盘读取"""
        if template_name not in self._template_cache:
            template_path = os.path.join(self.template_dir, template_name)
            template = cv2.imread(template_path)
            if template is None:
                print(f"无法加载模板: {template_path}")
            self._template_cache[template_name] = template
        return self._template_cache[template_name]

    def _take_screenshot_cv(self):
        """截取游戏窗口画面并直接转换为OpenCV格式"""
        screenshot = self.take_screenshot()
        if not screenshot:
            return None
        return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    def _find_template_in_image(self, img, template_name, threshold=0.95):
        """在已有的截图中查找模板（复用截图，避免重复截屏）"""
        template = self._load_template(template_name)
        if template is None:
            return None
        result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        if max_val >= threshold:
            h, w = template.shape[:2]
            center_x = self.game_window[0] + max_loc[0] + w // 2
            center_y = self.game_window[1] + max_loc[1] + h // 2
            return (center_x, center_y)
        return None

    def _find_all_templates_in_image(self, img, template_name, threshold=0.8):
        """在已有的截图中查找所有匹配位置（复用截图，避免重复截屏）"""
        template = self._load_template(template_name)
        if template is None:
            return []
        result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= threshold)
        matches = []
        h, w = template.shape[:2]
        for pt in zip(*locations[::-1]):
            center_x = self.game_window[0] + pt[0] + w // 2
            center_y = self.game_window[1] + pt[1] + h // 2
            matches.append((center_x, center_y))
        return matches

    def _init_pixel_samples(self):
        """从huanqiu.png模板中提取像素采样点，用于快速像素扫描替代模板匹配"""
        template = self._load_template("huanqiu.png")
        if template is None:
            self._huanqiu_pixels = None
            return
        
        th, tw = template.shape[:2]
        # 选取7个关键采样点（相对模板左上角的偏移 x, y）
        sample_offsets = [
            (tw//2, th//2),       # 中心
            (tw//4, th//4),       # 左上
            (3*tw//4, th//4),     # 右上
            (tw//4, 3*th//4),     # 左下
            (3*tw//4, 3*th//4),   # 右下
            (tw//2, th//4),       # 上中
            (tw//2, 3*th//4),     # 下中
        ]
        sample_colors = [template[sy, sx].tolist() for sx, sy in sample_offsets]
        
        self._huanqiu_pixels = {
            'offsets': sample_offsets,
            'colors': sample_colors,
            'tw': tw, 'th': th,
            'threshold': 50,  # L1颜色差异阈值（3通道总和）
        }
        print(f"像素采样初始化完成: 模板尺寸 {tw}x{th}, 采样点 {len(sample_offsets)} 个")

    def _fast_find_huanqiu(self, img):
        """使用像素采样快速查找所有环球按钮位置（替代matchTemplate，快~50倍）
        
        原理：
        1. 用numpy向量化操作，在全图扫描2个参考像素做快速初筛
        2. 对少量候选位置，用剩余5个采样点验证
        3. 合并距离过近的重复匹配
        """
        if self._huanqiu_pixels is None:
            return self._find_all_templates_in_image(img, "huanqiu.png")
        
        ps = self._huanqiu_pixels
        tw, th = ps['tw'], ps['th']
        threshold = ps['threshold']
        h, w = img.shape[:2]
        
        valid_h = h - th + 1
        valid_w = w - tw + 1
        if valid_h <= 0 or valid_w <= 0:
            return []
        
        # 用前2个采样点做numpy向量化初筛（同时匹配2个像素，大幅减少候选数）
        cx1, cy1 = ps['offsets'][0]  # 中心
        cx2, cy2 = ps['offsets'][1]  # 左上
        ref1 = np.array(ps['colors'][0], dtype=np.int16)
        ref2 = np.array(ps['colors'][1], dtype=np.int16)
        
        pixels1 = img[cy1:cy1+valid_h, cx1:cx1+valid_w].astype(np.int16)
        diff1 = np.sum(np.abs(pixels1 - ref1), axis=2)
        
        pixels2 = img[cy2:cy2+valid_h, cx2:cx2+valid_w].astype(np.int16)
        diff2 = np.sum(np.abs(pixels2 - ref2), axis=2)
        
        candidates = np.argwhere((diff1 < threshold) & (diff2 < threshold))
        
        if len(candidates) == 0:
            return []
        
        # 用剩余5个采样点验证候选位置
        matches = []
        for y, x in candidates:
            valid = True
            for i in range(2, len(ps['offsets'])):
                sx, sy = ps['offsets'][i]
                px, py = x + sx, y + sy
                if 0 <= py < h and 0 <= px < w:
                    pixel = img[py, px]
                    d = abs(int(pixel[0]) - ps['colors'][i][0]) + \
                        abs(int(pixel[1]) - ps['colors'][i][1]) + \
                        abs(int(pixel[2]) - ps['colors'][i][2])
                    if d > threshold:
                        valid = False
                        break
                else:
                    valid = False
                    break
            if valid:
                center_x = self.game_window[0] + x + tw // 2
                center_y = self.game_window[1] + y + th // 2
                matches.append((center_x, center_y))
        
        # 去重：合并距离过近的匹配点
        if len(matches) > 1:
            filtered = [matches[0]]
            for m in matches[1:]:
                too_close = False
                for f in filtered:
                    if abs(m[0]-f[0]) < tw//2 and abs(m[1]-f[1]) < th//2:
                        too_close = True
                        break
                if not too_close:
                    filtered.append(m)
            matches = filtered
        
        return matches

    def click(self, x, y, duration=0.2, human_like=True):
        """模拟鼠标点击"""
        if human_like:
            # 添加随机偏移，模拟人类点击
            x += random.randint(-5, 5)
            y += random.randint(-5, 5)
            duration += random.uniform(-0.1, 0.1)
            duration = max(0.1, duration)
        
        pyautogui.moveTo(x, y, duration=duration)
        pyautogui.click()
        print(f"点击位置: ({x}, {y})")
    
    def click_fast(self, x, y):
        """快速点击，使用win32api直接发送鼠标事件"""
        win32api.SetCursorPos((int(x), int(y)))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    def click_fast_batch(self, positions):
        """批量快速点击多个位置，逐个点击确保每个都完成"""
        for x, y in positions:
            win32api.SetCursorPos((int(x), int(y)))
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.05)

    def press_key(self, key, presses=1, interval=0.1, human_like=True):
        """模拟按键"""
        if human_like:
            interval += random.uniform(-0.05, 0.05)
            interval = max(0.05, interval)
        
        pyautogui.press(key, presses=presses, interval=interval)
        print(f"按下按键: {key}")

    def find_click_receive(self):
        """判断能否点击领取按钮"""
        receive_button = self.find_template("receive.png")
        if receive_button:
            self.click(*receive_button)
            time.sleep(0.1)

    def find_click_im(self):
        """判断能否点击环球页面"""
        im = self.find_template("im.png")
        if im:
            self.click(*im)
            time.sleep(0.1)

    def find_click_continue(self):
        """判断能否点击继续按钮"""
        continue_button = self.find_template("click-continue.png")
        if continue_button:
            self.click(*continue_button)
            time.sleep(0.1)
            
    def find_team_up(self):
        """判断能否发现队伍页面"""
        return self.find_template("recruitment-1.png")
    def _grab_huanqiu_spots(self, img):
        """在已有截图上查找环球按钮并快速批量点击抢坑（使用像素对比加速）
        
        找到位置后缓存，快速重复点击多轮，避免每次都重新截图扫描
        """
        positions = self._fast_find_huanqiu(img)
        if positions:
            click_positions = [(pos[0] + 100, pos[1]) for pos in positions]
            click_positions.reverse()  # 倒序点击
            # 缓存位置，快速重复点击多轮（省去重复截图+扫描的开销）
            for _ in range(10):
                if not self.running:
                    break
                self.click_fast_batch(click_positions)
            return True
        return False

    def _handle_battle(self):
        """处理战斗过程（从战斗中到战斗结束）"""
        print("进入战斗处理...")
        battle_start_time = time.time()
        while self.running:
            battling = self.find_battling()
            if not battling:
                # 增加防抖：可能是打boss时的过场警告动画或全屏技能导致图标短暂消失
                # 等待2秒后再确认一次，如果还是没有战斗图标，才真正判定为战斗结束
                time.sleep(2)
                if not self.find_battling():
                    print("确认战斗已结束，退出战斗循环")
                    break
            print("正在战斗中")
            self.find_click_skill()
            self.find_click_battling_continue()
            time.sleep(3)
            self.find_click_reconnection()
            self.find_click_close()
            self.find_click_return()
            if self.battle_time > 0 and time.time() - battle_start_time > self.battle_time:
                print(f"战斗时间超过{self.battle_time}秒,退出")
                self.find_click_stop()
                self.find_click_exit()
            print("战斗时间:", time.time() - battle_start_time)
        # 战斗结束后处理
        self.find_click_return()
        self.find_click_continue()
        self.find_click_receive()
        self.find_click_home_close()

    def _poor_mode_loop(self):
        """穷B模式专用主循环
        
        核心设计：
        1. 抢环优先 - 绝大部分时间用于快速抢环，不做无关检测
        2. 单截图复用 - 同一张截图同时检测队伍状态和环球按钮，减半截图开销
        3. 招募页面一次性进入 - 确认在招募页面后不再重复检测
        4. 进队快速判断 - 一旦进队立即检测是否目标环，快速决策
        5. 定期轻量检查 - 重连等不频繁检查
        """
        # self._init_pixel_samples()  # 已废弃，现改用缓存坐标连点器模式
        grab_count = 0
        in_recruitment_page = False
        
        # 启动独立截图线程：持续以~25fps截图，主线程只读最新帧
        self._latest_img = None
        self._img_lock = threading.Lock()
        
        def _screenshot_loop():
            while self.running:
                img = self._take_screenshot_cv()
                if img is not None:
                    with self._img_lock:
                        self._latest_img = img
                # 无需sleep，截图本身~39ms就是天然节流
        
        screenshot_thread = threading.Thread(target=_screenshot_loop, daemon=True)
        screenshot_thread.start()
        
        while self.running:
            # 确保游戏窗口存在
            if not self.game_window and not self.find_game_window():
                time.sleep(5)
                continue
            
            # ========== 读取最新截图（瞬间，不阻塞） ==========
            with self._img_lock:
                img = self._latest_img
            if img is None:
                time.sleep(0.1)  # 等待第一帧截图
                continue
            
            # ========== 快速检测：是否已进入队伍（轻量，只做一次模板匹配） ==========
            # 优化：队伍状态栏固定在屏幕上半部分，截取精确区间(ROI)能极大提升匹配速度
            h, w = img.shape[:2]
            roi_top = img[h//6:h//4, w//5:4*w//5]
            in_team = self._find_template_in_image(roi_top, "in-huanqiu-team.png")
            
            if in_team:
                in_recruitment_page = False
                self._cached_join_pos = None  # 清除连点缓存
                grab_count = 0
                
                # 同一张截图检测当前到底是哪个环（找置信度最高的，防止3和6误判）
                # 优化：因为"难度XX"必定在屏幕上半部分，截取精确区间(ROI)能提升数倍速度
                best_level = None
                best_score = 0
                h, w = img.shape[:2]
                roi_img = img[h//6:h//4, w//5:4*w//5]  # 只搜索对应的区间
                
                for level in range(1, 21):
                    # 直接调用底层的matchTemplate以获取具体分数
                    template = self._load_template(f"huanqiu-{level}.png")
                    if template is None:
                        continue
                    # 确保模板不比ROI还大
                    if template.shape[0] > roi_img.shape[0] or template.shape[1] > roi_img.shape[1]:
                        continue
                        
                    result = cv2.matchTemplate(roi_img, template, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, _ = cv2.minMaxLoc(result)
                    if max_val > best_score and max_val >= 0.90:  # 基础阈值0.9
                        best_score = max_val
                        best_level = level
                
                target_level = None
                if best_level in self.target_huanqiu_levels:
                    target_level = best_level
                

                if target_level:
                    # 命中不想打的环，快速离开重抢
                    print(f"命中不想打的环球副本 huanqiu-{target_level}.png，快速离开重抢")
                    # 优化：退出按钮固定在屏幕最下面 1/4 区域
                    h, w = img.shape[:2]
                    offset_y = 3 * h // 4
                    roi_bottom = img[offset_y:h, 0:w]
                    exit_pos = None
                    for btn in ["leave-button.png", "return-1.png"]:
                        pos = self._find_template_in_image(roi_bottom, btn)
                        if pos:
                            exit_pos = (pos[0], pos[1] + offset_y)
                            break
                    if exit_pos:
                        self.click_fast(*exit_pos)
                        # 等待确认弹窗出现，多次尝试找sure按钮 (增加到20次，防止弹窗太慢)
                        for _ in range(20):
                            time.sleep(0.1)  # 必须有等待！否则瞬间循环完，游戏还没弹出框
                            with self._img_lock:
                                sure_img = self._latest_img
                            if sure_img is not None:
                                # 优化：确定按钮固定在屏幕 1/3 到 3/4 的中间区域
                                h, w = sure_img.shape[:2]
                                offset_y_sure = h // 3
                                roi_center = sure_img[offset_y_sure:3*h//4, 0:w]
                                sure_pos = self._find_template_in_image(roi_center, "sure.png")
                                if sure_pos:
                                    # 修正相对坐标到绝对坐标
                                    sure_pos_abs = (sure_pos[0], sure_pos[1] + offset_y_sure)
                                    self.click_fast(*sure_pos_abs)
                                    time.sleep(1.5)  # 点击确认后，等待游戏彻底退出队伍画面（过场时间）
                                    break
                    else:
                        time.sleep(0.2)  # 没找到退出按钮也等一下，防止疯狂刷屏
                    continue
                
                # 好队伍，等待队长开始
                # 检测是否已开始战斗（用同一张截图做轻量检测）
                is_battling = False
                h_bat, w_bat = img.shape[:2]
                roi_battling = img[h_bat//3:2*h_bat//3, 0:w_bat]
                for tmpl in ['battling.png', 'battling-3.png', 'choose-skill.png']:
                    if self._find_template_in_image(roi_battling, tmpl):
                        is_battling = True
                        break
                
                if is_battling:
                    self._handle_battle()
                    continue
                
                print("当前队伍符合要求，等待队长开始战斗...")
                self._was_in_team = True  # 记录状态：我们刚才在队伍里
                time.sleep(1)
                continue
            
            # ========== 极速连点通道（短路逻辑） ==========
            # 只要处于招募页面，直接走捷径，完全绕开下面的“是否在战斗”检测！
            if in_recruitment_page:
                if getattr(self, '_cached_join_pos', None) is None:
                    # 优化：招募坑位必定在画面 1/4 到 5/6 之间
                    h_huanqiu, w_huanqiu = img.shape[:2]
                    offset_y_huanqiu = h_huanqiu // 4
                    roi_huanqiu = img[offset_y_huanqiu:5*h_huanqiu//6, 0:w_huanqiu]
                    raw_positions = self._find_all_templates_in_image(roi_huanqiu, "huanqiu.png", threshold=0.8)
                    positions = [(p[0], p[1] + offset_y_huanqiu) for p in raw_positions] if raw_positions else []
                    if positions:
                        # 找到所有位置中 y 坐标最大的（最下面的那个环）
                        bottom_pos = max(positions, key=lambda p: p[1])
                        self._cached_join_pos = bottom_pos
                        print(f"锁定最下方坑位坐标: {bottom_pos}，开启连点模式！")
                
                if getattr(self, '_cached_join_pos', None):
                    # 极速微循环爆点
                    for _ in range(5):
                        self.click_fast(*self._cached_join_pos)
                    
                    grab_count += 1
                    # 定期轻量检查
                    if grab_count % 200 == 0:
                        with self._img_lock:
                            check_img = self._latest_img
                        if check_img is not None:
                            reconnect_pos = self._find_template_in_image(check_img, "reconnection.png")
                            if reconnect_pos:
                                self.click_fast(*reconnect_pos)
                            h_check, w_check = check_img.shape[:2]
                            roi_recruit = check_img[h_check//4:h_check//2, 0:w_check]
                            if not self._find_template_in_image(roi_recruit, "recruitment-1.png"):
                                in_recruitment_page = False
                                self._cached_join_pos = None  # 清除连点缓存
                                print("检测到已离开招募页面，等待画面加载...")
                                time.sleep(0.5)
                    # ★★★ 核心：直接进入下一帧，跳过所有的战斗和页面跳转检测！ ★★★
                    continue
            
            # ========== 不在队伍中 ==========
            
            # 如果刚刚还在队伍里，现在突然不在了，说明正在加载进战斗（或者被踢了）
            if getattr(self, '_was_in_team', False):
                print("检测到离开队伍，等待游戏过场动画（加载战斗或回主城）...")
                time.sleep(2.0)  # 给足够的时间让战斗画面或主城画面加载出来
                self._was_in_team = False
                continue  # 让下一个循环用最新画面重新判断
                
            # 检测是否在战斗中（战斗相关UI在画面的 1/3 到 2/3 之间）
            is_battling = False
            h_bat2, w_bat2 = img.shape[:2]
            roi_battling2 = img[h_bat2//3:h_bat2//2, 0:w_bat2]
            for tmpl in ['battling-2.png', 'battling-3.png', 'choose-skill.png', 'choose-skill-1.png']:
                if self._find_template_in_image(roi_battling2, tmpl):
                    is_battling = True
                    break
            if is_battling:
                in_recruitment_page = False
                self._cached_join_pos = None  # 清除连点缓存
                self._handle_battle()
                continue
            
            # 首次或离开队伍后，需要确保进入招募页面（一次性操作）
            if not in_recruitment_page:
                on_recruit = self._find_template_in_image(img, "recruitment-1.png")
                if on_recruit:
                    in_recruitment_page = True
                else:
                    # 尝试进入招募页面
                    recruit_btn = self._find_template_in_image(img, "recruitment.png")
                    if recruit_btn:
                        self.click(*recruit_btn)
                        time.sleep(0.5)  # 等待页面切换动画
                    else:
                        im_btn = self._find_template_in_image(img, "im.png")
                        if im_btn:
                            self.click(*im_btn)
                            time.sleep(0.8)  # 等待聊天窗口弹出动画
                        else:
                            # 找不到im和招募，可能在其他页面
                            # 优先尝试点击战斗按钮切回主界面（主界面有im入口）
                            for btn in ["battle.png", "battle-1.png"]:
                                pos = self._find_template_in_image(img, btn)
                                if pos:
                                    self.click(*pos)
                                    time.sleep(0.5)  # 等待切回主界面动画
                                    break
                    continue
            

    def find_in_huanqiu_team(self):
        """是否在环球队伍"""
        huanqiu_team = self.find_template("in-huanqiu-team.png")
        if huanqiu_team:
            return True
        return False

    def find_target_huanqiu_team(self):
        """判断是否命中用户选择的目标环球副本"""
        for level in self.target_huanqiu_levels:
            template_name = f"huanqiu-{level}.png"
            huanqiu_team = self.find_template(template_name)
            if huanqiu_team:
                print(f"发现目标环球副本: {template_name}")
                return level, huanqiu_team
        return None, None

    def leave_huanqiu_team(self):
        """离开当前环球副本"""
        leave_button = self.find_leave_button()
        if leave_button:
            self.click(*leave_button)
            print("点击离开按钮")
            time.sleep(0.1)
            self.find_click_sure()
            return True
        return False

    def find_click_home_close(self):
        """判断能否点击关闭按钮"""

        closes = ['home-close.png', 'home-close-1.png','home-close-2-text.png', 'home-close-2.png']

        for close in closes:
            close = self.find_template(close)
            if close:
                self.click(*close)
                time.sleep(0.1)
                break

    def find_click_close(self):
        """判断能否点击关闭按钮"""
        closes = [
            "close.png",
            "auto-close.png",
            "battling-4.png",
        ]
        for close in closes:
            close = self.find_template(close)
            if close:
                self.click(*close)
                time.sleep(0.1)
                return True
        return False
    def find_click_reconnection(self):
        """判断能否点击重新连接按钮"""
        reconnection = self.find_template("reconnection.png")
        if reconnection:
            self.click(*reconnection)
            time.sleep(0.1)
            
    def find_huanqiu(self):
        """判断能否发现环球按钮"""
        return self.find_template("huanqiu.png")

    def find_click_start_button(self):
        """判断能否点击战斗按钮"""
        battles = ['battle.png', 'battle-1.png']
        for battle in battles:
            battle = self.find_template(battle)
            if battle:
                self.click(*battle)
                time.sleep(0.1)
                return True
        return False
    def find_click_sure(self):
        """判断能否点击确定按钮"""
        sure = self.find_template("sure.png")
        if sure:
            self.click(*sure)
            time.sleep(0.1)
            
    def find_click_battling_continue(self):
        """判断能否点击继续战斗按钮"""
        continue_battle = self.find_template("battling-continue.png")
        if continue_battle:
            self.click(*continue_battle)
            time.sleep(0.1)
            
    def find_click_skill(self):
        """判断能否点击技能按钮"""
        choose_skill = self.find_template("choose-skill.png")
        if not choose_skill:
            choose_skill = self.find_template("choose-skill-1.png")
            if not choose_skill:
                return None

        # 首先检查4个优先技能
        for priority_skill_templates in self.priority_skills:
            if priority_skill_templates:
                # priority_skill_templates 是模板文件名列表
                for template in priority_skill_templates:
                    # 确保文件名包含.png扩展名
                    if not template.endswith('.png'):
                        template = f"{template}.png"
                    skill_pos = self.find_template(template)
                    if skill_pos:
                        self.click(*skill_pos)
                        time.sleep(0.1)
                        return None

        # 如果优先技能未匹配到，从全部技能中按顺序匹配
        for skill in SKILL_LIST:
            for template in skill["template"]:
                # 确保文件名包含.png扩展名
                if not template.endswith('.png'):
                    template = f"{template}.png"
                skill_pos = self.find_template(template)
                if skill_pos:
                    self.click(*skill_pos)
                    time.sleep(0.1)
                    return None

        return None
        
    def find_battling(self):
        """判断是否在战斗中"""
        battles = ['battling.png', 'battling-3.png', 'battling-4.png', 'battling-5.png', "auto-close.png", "choose-skill.png", "choose-skill-1.png"]
        for battle in battles:
            xy = self.find_template(battle)
            if xy:
                return xy
        return None

    def find_click_dont_battle_return(self):
        """判断能否点击返回按钮"""
        return_button = self.find_template("return-1.png")
        if return_button:
            self.click(*return_button)
            time.sleep(0.1)
            
    def find_click_return(self):
        """判断能否点击返回主界面"""
        return_button = self.find_template("return.png")
        if return_button:
            self.click(*return_button)
            time.sleep(0.1)
            
    def find_click_stop(self):
        """判断能否点击停止按钮"""
        stop = self.find_template("battling.png")
        if stop:
            self.click(*stop)
            time.sleep(0.1)
            
    def find_click_exit(self):
        """判断能否点击退出按钮"""
        exit_button = self.find_template("exit.png")
        if exit_button:
            self.click(*exit_button)
            time.sleep(0.1)
            
    def find_click_card(self):
        """判断能否点击卡关按钮"""
        card = self.find_template("card-normal.png")
        if card:
            self.click(*card)
            time.sleep(0.2)
            card = self.find_template("card-start.png")
            if card:
                self.click(*card)
                time.sleep(0.1)
                
    def find_click_orange_start_game(self):
        """判断能否点击橘子开始游戏按钮"""
        orange_start_game = self.find_template("orange-start.png")
        print(orange_start_game)
        if orange_start_game:
            self.click(*orange_start_game)
            time.sleep(0.1)
            
    def find_expedition_team(self):
        """判断能否在远征队伍中"""
        expedition_team_icons = ["expedition-team.png", "expedition-team-2.png"]
        for icon in expedition_team_icons:
            expedition_team = self.find_template(icon)
            if expedition_team:
                return True
        return False
    def find_click_base(self):
        """判断能否点击基地按钮"""
        bases_icon = ["base.png", "base-2.png"]
        for icon in bases_icon:
            base = self.find_template(icon)
            if base:
                break
        if base:
            self.click(*base)
            time.sleep(0.1)
            
    def find_click_experience(self):
        """判断能否点击历练按钮"""
        experience_icon = ["experience.png"]
        for icon in experience_icon:
            experience = self.find_template(icon)
            if experience:
                break
        if experience:
            self.click(*experience)
            time.sleep(0.1)
    def find_click_expedition_challenge(self):
        """判断能否点击远征挑战按钮"""
        challenge_icon = ["expedition-challenge.png", "expedition-challenge-1.png"]
        for icon in challenge_icon:
            challenge = self.find_template(icon)
            if challenge:
                break
        if challenge:
            self.click(*challenge)
            time.sleep(0.1)
            
    def find_expedition_difficulty(self):
        """判断能否发现远征困难按钮"""
        difficulty_icon = ["expedition-difficulty.png"]
        for icon in difficulty_icon:
            difficulty = self.find_template(icon)
            if difficulty:
                return True
        return False
    def find_expedition_normal(self):
        """判断能否发现远征普通按钮"""
        normal_icon = ["expedition-normal.png"]
        for icon in normal_icon:
            normal = self.find_template(icon)
            if normal:
                return True
        return False
    def find_click_expedition_team_hall(self):
        """判断能否点击远征队伍大厅按钮"""
        continue_icon = ["expedition-team-hall.png"]
        for icon in continue_icon:
            continue_button = self.find_template(icon)
            if continue_button:
                self.click(*continue_button)
                time.sleep(0.1)
                break
    def find_click_expedition_fast_join(self):
        """判断能否点击远征快速加入按钮"""
        fast_join_icon = ["expedition-fast-join.png"]
        for icon in fast_join_icon:
            fast_join = self.find_template(icon)
            if fast_join:
                self.click(*fast_join)
                time.sleep(0.1)
                break
    def find_expedition_tickets(self):
        """判断能否发现远征门票按钮"""
        tickets_icon = ["expedition-tickets.png"]
        for icon in tickets_icon:
            tickets = self.find_template(icon)
            if tickets:
                return True
        return False
    def click_expedition_fast_join(self):
        """点击远征快速加入按钮"""
        self.find_click_expedition_team_hall()
        self.find_click_expedition_fast_join()
        time.sleep(1)
        self.expedition_in_team_max_time = time.time() + self.wait_time  # 当前时间戳+wait_time秒 wait_time秒后重新点击
    def find_click_expedition_ready(self):
        """判断能否点击远征准备按钮"""
        ready_icon = ["expedition-ready.png"]
        for icon in ready_icon:
            ready = self.find_template(icon)
            if ready:
                self.click(*ready)
                time.sleep(0.1)
                break
    def find_expedition_personnels(self):
        """判断能否发现远征人员按钮"""
        personnel_icon = ["expedition-personnel.png"]
        for icon in personnel_icon:
            personnels = self.find_all_templates(icon, 0.9)
            return len(personnels)
    def find_expedition_exit(self):
        """判断能否发现远征退出按钮"""
        exit_icon = ["expedition-exit.png"]
        for icon in exit_icon:
            exit = self.find_template(icon)
            if exit:
                return exit
        return None
    def find_leave_button(self):
        """判断能否点击离开按钮"""
        leave_icon = ["leave-button.png"]
        for icon in leave_icon:
            leave = self.find_template(icon)
            if leave:
                return leave
        return None
    def find_click_huanqiu_challenge(self):
        """判断能否点击环球挑战按钮"""
        challenge_icon = ["huanqiu-challenge.png"]
        for icon in challenge_icon:
            challenge = self.find_template(icon)
            if challenge:
                self.click(*challenge)
                time.sleep(0.1)
                break
    def find_huanqiu_invite(self):
        """判断能否发现环球邀请按钮"""
        invite_icon = ["huanqiu-invite.png"]
        for icon in invite_icon:
            invite = self.find_template(icon)
            if invite:
                return invite
        return None
    def find_click_huanqiu_post_recruitment(self):
        """判断能否点击环球发布招募按钮"""
        post_recruitment_icon = ["huanqiu-post-recruitmen.png"]
        for icon in post_recruitment_icon:
            post_recruitment = self.find_template(icon)
            if post_recruitment:
                self.click(*post_recruitment)
                time.sleep(0.1)
                break
    def find_click_start_game_button(self):
        """判断能否点击开始游戏按钮"""
        start_game_icon = ["start-game-button.png"]
        for icon in start_game_icon:
            start_game = self.find_template(icon)
            if start_game:
                self.click(*start_game)
                time.sleep(0.1)
                break
    def find_expedition_vice_captain(self):
        """判断能否远征副队长按钮"""
        vice_captain_icon = ["expedition-vice-captain.png"]
        for icon in vice_captain_icon:
            vice_captain = self.find_template(icon)
            if vice_captain:
                return True
        return False
    def find_expedition_vice_captain_tag(self):
        """判断能否发现远征副队长标签按钮"""
        vice_captain_tag_icon = ["expedition-vice-captain-tag.png"]
        for icon in vice_captain_tag_icon:
            vice_captain_tag = self.find_template(icon)
            if vice_captain_tag:
                return True
        return False
    def find_expedition_elite_tag(self):
        """判断能否发现远征精英标签按钮"""
        elite_tag_icon = ["expedition-elite-tag.png"]
        for icon in elite_tag_icon:
            elite_tag = self.find_template(icon)
            if elite_tag:
                return elite_tag
        return None
    def find_click_start_challenge(self):
        """判断能否点击开始挑战按钮"""
        start_challenge_icon = ["start-challenge.png"]
        for icon in start_challenge_icon:
            start_challenge = self.find_template(icon)
            if start_challenge:
                self.click(*start_challenge)
                time.sleep(0.1)
                break
    def find_expedition_health_100s(self):
        """判断能否发现远征健康值100按钮"""
        expedition_health_icon = ["expedition-health-100.png"]
        for icon in expedition_health_icon:
            expedition_healths = self.find_all_templates(icon)
            if len(expedition_healths) > 0:
                return expedition_healths
        return []
    def find_click_expedition_continue(self):
        """判断能否点击远征继续按钮"""
        continue_icon = ["expedition-continue.png"]
        for icon in continue_icon:
            continue_icon = self.find_template(icon)
            if continue_icon:
                self.click(*continue_icon)
                time.sleep(0.1)
                break
    def expedition_in_team(self, in_expedition):
        """判断是否在远征团队中"""
        if not in_expedition:
            self.click_expedition_fast_join()
        else:
            tickets = self.find_expedition_tickets()
            # 穷B模式
            if tickets and self.rich_mode == 1:
                self.click_expedition_fast_join()
            else:
                if self.rich_mode == 0:
                    vice_captain = self.find_expedition_vice_captain()
                    if not vice_captain:
                        self.find_click_start_game_button()
                self.find_click_expedition_ready()
                self.find_click_sure()
    def on_hotkey(self, key):
        """快捷键回调函数"""
        try:
            if key == keyboard.Key.esc:
                print("检测到ESC键，正在停止脚本...")
                self.running = False
                if self.hotkey_listener:
                    self.hotkey_listener.stop()
                return False
        except AttributeError:
            pass
        return True

    def setup_hotkey(self):
        """设置快捷键监听"""
        print("已设置快捷键: ESC键 - 停止脚本")
        self.hotkey_listener = keyboard.Listener(on_release=self.on_hotkey)
        self.hotkey_listener.start()

    def main_loop(self, iterations=None):
        """主循环"""
        # 设置快捷键监听
        self.setup_hotkey()
        
        print("开始自动刷图脚本...")
        print("提示: 按下ESC键可以随时停止脚本")
        count = self.battle_count
        
        # timestamp = time.time()
        while self.running:
            # 检查是否达到迭代次数
            if iterations and count >= iterations:
                print(f"已完成 {iterations} 次刷图，脚本停止")
                self.running = False
                break
            
            # 确保游戏窗口被找到
            if not self.game_window and not self.find_game_window():
                time.sleep(5)
                continue
            # 点击领取
            self.find_click_receive()
            
            # 关闭按钮
            self.find_click_home_close()
            
            # 检查是否需要重新连接
            self.find_click_reconnection()
            
            # 是否确定
            self.find_click_sure()
            
            # 是不是通关了
            self.find_click_return()

            batileTime = None
            # 是不是在战斗中
            while True and self.running:

                battling = self.find_battling()
                if not battling:
                    break
                print("正在战斗中")
                # 点击技能
                self.find_click_skill()
                # 点击继续战斗
                self.find_click_battling_continue()
                time.sleep(3)
                # 点击重新连接
                self.find_click_reconnection()
                # 关闭窗口
                self.find_click_close()
                # 点击返回
                self.find_click_return()

                if batileTime is None:
                    batileTime = time.time()
                else:
                    if self.battle_time > 0 and time.time() - batileTime > self.battle_time:
                        print(f"战斗时间超过{self.battle_time}秒,退出")
                        self.find_click_stop()
                        self.find_click_exit()
                print("战斗时间:", time.time() - batileTime)
            
            # 是否刷环球
            if self.mode == 0:
                # 穷B模式：使用专用高速循环（跳过主循环中的无关检测）
                if self.rich_mode == 1:
                    self._poor_mode_loop()
                    break  # _poor_mode_loop 内部有自己的循环，退出后结束主循环
                    
                # 土豪消费模式
                elif self.rich_mode == 0:
                    in_huanqiu_team = self.find_in_huanqiu_team()
                    if not in_huanqiu_team:
                        # 打环球
                        self.find_click_base()
                        self.find_click_experience()
                        self.find_click_huanqiu_challenge()
                    else:
                        invite_button = self.find_huanqiu_invite()
                        if invite_button:
                            self.click(*invite_button)
                            time.sleep(0.2)
                            self.find_click_huanqiu_post_recruitment()
                            self.find_click_home_close()
                            time.sleep(1)
                        else:
                            self.find_click_start_game_button()
                            self.find_click_start_challenge()
            # 是否刷卡关
            if self.mode == 1:
                # 先确定位置
                start_button = self.find_click_start_button()
                if not start_button:
                    # 不打远征
                    self.find_click_dont_battle_return()
                    self.find_click_continue()
                    continue
                # 检查当前页面是否在卡关页面
                self.find_click_card()
            if self.mode in [2, 3]:
                # 先找是不是在远征队伍中
                in_expedition_team = self.find_expedition_team()
                if not in_expedition_team:
                    # 打远征
                    self.find_click_base()
                    self.find_click_experience()
                    self.find_click_expedition_challenge()
                else:
                    expedition_exit_button = self.find_expedition_exit()
                    if expedition_exit_button:
                        self.find_click_expedition_continue()
                        self.find_click_close()
                        # 一个人就退出
                        vice_captain_tag = self.find_expedition_vice_captain_tag()
                        # personnel_count = 1")
                        if vice_captain_tag:
                            print("发现人走光")
                            self.click(*expedition_exit_button)
                            self.find_click_sure()
                        else:
                            elite_tag = self.find_expedition_elite_tag()
                            if elite_tag:
                                # y轴向下100个像素
                                elite_tag = (elite_tag[0], elite_tag[1] + 100)
                                self.click(*elite_tag)
                                time.sleep(0.1)
                                self.find_click_start_challenge()
                            expedition_healths = self.find_expedition_health_100s()
                            if len(expedition_healths) == 1:
                                expedition_health = expedition_healths[0]
                                # y轴向上100个像素
                                expedition_health = (expedition_health[0], expedition_health[1] - 100)
                                self.click(*expedition_health)
                                time.sleep(0.1)
                                self.find_click_start_challenge()
                if self.mode == 2:
                    in_normal = self.find_expedition_normal()
                    if not in_normal:
                        in_normal = not self.find_expedition_difficulty()
                    self.expedition_in_team(in_normal)
                if self.mode == 3:
                    in_difficulty = self.find_expedition_difficulty()
                    self.expedition_in_team(in_difficulty)
                if time.time() > self.expedition_in_team_max_time:
                    print("等待时间超过最大时间,重新点击")
                    self.click_expedition_fast_join()
                else:
                    remain_time = self.expedition_in_team_max_time - time.time()
                    remain_time = int(remain_time)
                    print(f"等待时间剩余{remain_time}秒")
            # 点击继续
            self.find_click_continue()
            # 每100秒随机点个位置
            # if time.time() - timestamp > 100:
                # 随机点击
                # self.click(random.randint(int(self.game_window[2]), int(self.game_window[0])), random.randint(int(self.game_window[1]), int(self.game_window[3])))
                # self.click(500, 100)
                # timestamp = time.time()

class GameBotGUI:
    CONFIG_FILE = "config.json"
    
    def __init__(self, root):
        self.root = root
        self.root.title("游戏机器人操作界面")
        self.root.geometry("680x700")
        self.root.resizable(False, False)
        
        self.bot = None
        self.is_running = False
        
        # 创建界面组件
        self.create_widgets()
        
        # 加载保存的配置
        self.load_config()
    
    def get_skill_template_by_name(self, name):
        """根据技能名称获取模板文件名列表"""
        for skill in SKILL_LIST:
            if skill["name"] == name:
                return skill["template"]
        return None
    
    def load_config(self):
        """加载保存的配置"""
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 加载基本参数
                    if 'game_title' in config:
                        self.game_title_var.set(config['game_title'])
                    if 'mode' in config:
                        self.mode_var.set(config['mode'])
                        self.on_mode_changed(None)
                    if 'rich_mode' in config:
                        self.rich_mode_var.set(config['rich_mode'])
                    if 'battle_count' in config:
                        self.battle_count_var.set(config['battle_count'])
                    if 'battle_time' in config:
                        self.battle_time_var.set(config['battle_time'])
                    # 加载优先技能配置
                    priority_skills = config.get('priority_skills', [])
                    for i, skill_name in enumerate(priority_skills):
                        if i < len(self.priority_skill_vars):
                            self.priority_skill_vars[i].set(skill_name)
                    # 加载目标环球副本
                    target_huanqiu_levels = config.get('target_huanqiu_levels', [])
                    if hasattr(self, 'huanqiu_target_vars'):
                        for level in target_huanqiu_levels:
                            if level in self.huanqiu_target_vars:
                                self.huanqiu_target_vars[level].set(1)
        except Exception as e:
            print(f"加载配置失败: {e}")
    
    def save_config(self):
        """保存当前配置"""
        try:
            config = {
                'game_title': self.game_title_var.get(),
                'mode': self.mode_var.get(),
                'rich_mode': self.rich_mode_var.get(),
                'battle_count': self.battle_count_var.get(),
                'battle_time': self.battle_time_var.get(),
                'priority_skills': [var.get() for var in self.priority_skill_vars],
                'target_huanqiu_levels': [level for level, var in self.huanqiu_target_vars.items() if var.get()] if hasattr(self, 'huanqiu_target_vars') else []
            }
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def create_widgets(self):
        # 游戏标题
        ttk.Label(self.root, text="游戏窗口标题:").grid(row=0, column=0, padx=10, pady=5, sticky=tk.W)
        self.game_title_var = tk.StringVar(value="抖音")
        self.game_title_entry = ttk.Entry(self.root, textvariable=self.game_title_var, width=30)
        self.game_title_entry.grid(row=0, column=1, padx=10, pady=5, sticky=tk.W)
        
        # 模式选择
        ttk.Label(self.root, text="模式:").grid(row=1, column=0, padx=10, pady=5, sticky=tk.W)
        self.mode_var = tk.StringVar(value="环球")
        self.mode_combo = ttk.Combobox(self.root, textvariable=self.mode_var, values=["环球", "主线", "普通远征", "超级远征"], width=15, state="readonly")
        self.mode_combo.grid(row=1, column=1, padx=10, pady=5, sticky=tk.W)
        self.mode_combo.bind("<<ComboboxSelected>>", self.on_mode_changed)
        
        # 消费模式选择（仅环球、普通远征、超级远征显示）
        self.rich_mode_label = ttk.Label(self.root, text="消费模式:")
        self.rich_mode_label.grid(row=2, column=0, padx=10, pady=5, sticky=tk.W)
        self.rich_mode_frame = ttk.Frame(self.root)
        self.rich_mode_var = tk.IntVar(value=0)
        ttk.Radiobutton(self.rich_mode_frame, text="我是土豪", variable=self.rich_mode_var, value=0).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(self.rich_mode_frame, text="我是穷B", variable=self.rich_mode_var, value=1).pack(side=tk.LEFT, padx=5)
        self.rich_mode_frame.grid(row=2, column=1, padx=10, pady=5, sticky=tk.W)
        
        # 战斗次数
        ttk.Label(self.root, text="战斗次数:").grid(row=3, column=0, padx=10, pady=5, sticky=tk.W)
        self.battle_count_var = tk.IntVar(value=0)
        self.battle_count_spinbox = ttk.Spinbox(self.root, from_=0, to=999, textvariable=self.battle_count_var, width=10)
        self.battle_count_spinbox.grid(row=3, column=1, padx=10, pady=5, sticky=tk.W)
        ttk.Label(self.root, text="(0表示无限循环)").grid(row=3, column=2, padx=5, pady=5, sticky=tk.W)
        
        # 战斗时间
        ttk.Label(self.root, text="战斗时间(秒):").grid(row=4, column=0, padx=10, pady=5, sticky=tk.W)
        self.battle_time_var = tk.IntVar(value=0)
        self.battle_time_spinbox = ttk.Spinbox(self.root, from_=0, to=999, textvariable=self.battle_time_var, width=10)
        self.battle_time_spinbox.grid(row=4, column=1, padx=10, pady=5, sticky=tk.W)
        ttk.Label(self.root, text="(0表示无限制)").grid(row=4, column=2, padx=5, pady=5, sticky=tk.W)
        
        # 优先技能选项（5个）
        ttk.Label(self.root, text="优先技能(从上到下):").grid(row=6, column=0, padx=10, pady=5, sticky=tk.W)


        
        # 获取技能名称列表
        skill_names = [skill["name"] for skill in SKILL_LIST]
        
        # 5个优先技能下拉框
        self.priority_skill_vars = []
        self.priority_skill_combos = []
        for i in range(5):
            var = tk.StringVar(value="")
            self.priority_skill_vars.append(var)
            combo = ttk.Combobox(self.root, textvariable=var, values=[""] + skill_names, width=15, state="readonly")
            combo.grid(row=5+i, column=1, padx=10, pady=3, sticky=tk.W)
            combo.bind("<<ComboboxSelected>>", self.on_skill_selected)
            self.priority_skill_combos.append(combo)
            ttk.Label(self.root, text=f"优先级{i+1}").grid(row=5+i, column=2, padx=5, pady=3, sticky=tk.W)

        # 目标环球副本选择
        self.huanqiu_target_label = ttk.Label(self.root, text="不想打的寰球副本:")
        self.huanqiu_target_label.grid(row=10, column=0, padx=10, pady=5, sticky=tk.W)
        self.huanqiu_target_frame = ttk.LabelFrame(self.root, text="命中后离开重抢")
        self.huanqiu_target_vars = {}
        for index, level in enumerate(HUANQIU_TARGET_LEVELS):
            var = tk.IntVar(value=0)
            self.huanqiu_target_vars[level] = var
            row = index // 4
            column = index % 4
            checkbutton = ttk.Checkbutton(self.huanqiu_target_frame, text=f"环球{level}", variable=var)
            checkbutton.grid(row=row, column=column, padx=8, pady=4, sticky=tk.W)
            if not hasattr(self, 'huanqiu_target_checks'):
                self.huanqiu_target_checks = []
            self.huanqiu_target_checks.append(checkbutton)
        self.huanqiu_target_frame.grid(row=11, column=0, columnspan=3, padx=10, pady=8, sticky=tk.W)
        self.huanqiu_target_frame.grid_remove()

        # 默认模式是环球，所以默认显示
        self.on_mode_changed(None)
        
        # 按钮框架
        button_frame = ttk.Frame(self.root)
        button_frame.grid(row=12, column=0, columnspan=3, padx=10, pady=20)
        
        # 开始按钮
        self.start_btn = ttk.Button(button_frame, text="开始", command=self.start_bot, width=15)
        self.start_btn.pack(side=tk.LEFT, padx=10)
        
        # 停止按钮
        self.stop_btn = ttk.Button(button_frame, text="停止", command=self.stop_bot, width=15, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=10)
        
        # 调整窗口大小按钮
        self.resize_btn = ttk.Button(button_frame, text="调整窗口大小", command=self.resize_window, width=15)
        self.resize_btn.pack(side=tk.LEFT, padx=10)
        
        # 退出按钮
        self.quit_btn = ttk.Button(button_frame, text="退出", command=self.quit_app, width=15)
        self.quit_btn.pack(side=tk.LEFT, padx=10)
        
        # 状态标签
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(self.root, textvariable=self.status_var, foreground="green").grid(row=13, column=0, columnspan=3, padx=10, pady=10)
        
        # 提示标签
        ttk.Label(self.root, text="提示: 按ESC键暂停脚本", foreground="blue").grid(row=14, column=0, columnspan=3, padx=10, pady=5, sticky=tk.W)
    
    def on_skill_selected(self, event):
        """技能选择事件，防止重复选择"""
        # 获取所有已选择的技能
        selected_skills = [var.get() for var in self.priority_skill_vars if var.get()]
        
        # 获取所有技能名称
        all_skills = [skill["name"] for skill in SKILL_LIST]
        
        # 更新每个下拉框的可选项
        for i, combo in enumerate(self.priority_skill_combos):
            current_value = self.priority_skill_vars[i].get()
            # 可选项：空 + 未被其他下拉框选中的技能
            available = [""] + [s for s in all_skills if s not in selected_skills or s == current_value]
            combo['values'] = available
    
    def on_mode_changed(self, event):
        """模式选择事件，控制土豪/穷B单选框显示"""
        mode = self.mode_var.get()
        # 仅环球、普通远征、超级远征显示土豪/穷B选项
        if mode in ["环球", "普通远征", "超级远征"]:
            self.rich_mode_label.grid(row=2, column=0, padx=10, pady=5, sticky=tk.W)
            self.rich_mode_frame.grid(row=2, column=1, padx=10, pady=5, sticky=tk.W)
        else:
            self.rich_mode_label.grid_remove()
            self.rich_mode_frame.grid_remove()

        if hasattr(self, "huanqiu_target_label") and hasattr(self, "huanqiu_target_frame"):
            if mode == "环球":
                self.huanqiu_target_label.grid()
                self.huanqiu_target_frame.grid()
            else:
                self.huanqiu_target_label.grid_remove()
                self.huanqiu_target_frame.grid_remove()

    def get_selected_target_huanqiu_levels(self):
        """获取已勾选的目标环球副本编号"""
        return [level for level, var in self.huanqiu_target_vars.items() if var.get()]
    
    def start_bot(self):
        """开始运行游戏机器人"""
        try:
            # 获取界面参数
            game_title = self.game_title_var.get()
            mode_text = self.mode_var.get()
            mode_map = {"环球": 0, "主线": 1, "普通远征": 2, "超级远征": 3}
            mode = mode_map.get(mode_text, 0)
            battle_count = self.battle_count_var.get()
            battle_time = self.battle_time_var.get()
            rich_mode = self.rich_mode_var.get()
            target_huanqiu_levels = self.get_selected_target_huanqiu_levels()
            
            # 获取5个优先技能（将中文名称转换为模板文件名）
            priority_skills = []
            for var in self.priority_skill_vars:
                skill_name = var.get()
                if skill_name:
                    template = self.get_skill_template_by_name(skill_name)
                    if template:
                        priority_skills.append(template)
            
            # 保存配置
            self.save_config()
            
            # 验证参数
            if not game_title:
                messagebox.showerror("错误", "请输入游戏窗口标题")
                return
            
            # 创建GameBot实例
            self.bot = GameBot(game_title, battle_time, battle_count, mode, priority_skills, rich_mode, target_huanqiu_levels)
            
            # 更新状态
            self.status_var.set("运行中...")
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            
            # 禁用所有参数控件
            self.game_title_entry.config(state=tk.DISABLED)
            self.mode_combo.config(state=tk.DISABLED)
            for child in self.rich_mode_frame.winfo_children():
                child.config(state=tk.DISABLED)
            self.battle_count_spinbox.config(state=tk.DISABLED)
            self.battle_time_spinbox.config(state=tk.DISABLED)
            for combo in self.priority_skill_combos:
                combo.config(state=tk.DISABLED)
            for checkbutton in getattr(self, 'huanqiu_target_checks', []):
                checkbutton.config(state=tk.DISABLED)
            self.resize_btn.config(state=tk.DISABLED)
            
            # 创建并启动线程
            self.bot_thread = threading.Thread(target=self.run_bot, daemon=True)
            self.bot_thread.start()
            
        except Exception as e:
            messagebox.showerror("错误", f"启动失败: {str(e)}")
            self.status_var.set("就绪")
    
    def run_bot(self):
        """运行游戏机器人主循环"""
        try:
            # 运行主循环，直到达到指定次数或被停止
            while self.bot and self.bot.running:
                # 运行一次主循环迭代
                self.bot.main_loop(iterations=1)
                # 短暂休眠，避免CPU占用过高
                time.sleep(0.1)
        except Exception as e:
            print(f"运行出错: {str(e)}")
        finally:
            # 停止运行
            self.root.after(0, self.stop_bot)
    
    def stop_bot(self):
        """停止游戏机器人"""
        if self.bot:
            self.bot.running = False
            self.bot = None
        
        # 更新状态
        self.status_var.set("已停止")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
        # 启用所有参数控件
        self.game_title_entry.config(state=tk.NORMAL)
        self.mode_combo.config(state=tk.NORMAL)
        for child in self.rich_mode_frame.winfo_children():
            child.config(state=tk.NORMAL)
        self.battle_count_spinbox.config(state=tk.NORMAL)
        self.battle_time_spinbox.config(state=tk.NORMAL)
        for combo in self.priority_skill_combos:
            combo.config(state=tk.NORMAL)
        for checkbutton in getattr(self, 'huanqiu_target_checks', []):
            checkbutton.config(state=tk.NORMAL)
        self.resize_btn.config(state=tk.NORMAL)
    
    def resize_window(self):
        """调整游戏窗口大小"""
        try:
            # 创建临时GameBot实例来调整窗口大小
            game_title = self.game_title_var.get()
            temp_bot = GameBot(game_title=game_title)
            if temp_bot.resize_game_window():
                self.status_var.set("窗口大小已调整为542*1010")
            else:
                self.status_var.set("未找到游戏窗口，无法调整大小")
        except Exception as e:
            self.status_var.set(f"调整窗口大小失败: {e}")
    
    def quit_app(self):
        """退出应用程序"""
        self.save_config()
        if self.bot:
            self.bot.running = False
        self.root.quit()

if __name__ == "__main__":
    # 创建主窗口
    root = tk.Tk()
    
    # 设置窗口图标（可选）
    try:
        root.iconbitmap(default=None)
    except:
        pass
    
    # 创建GUI实例
    app = GameBotGUI(root)
    
    # 运行主循环
    root.mainloop()

# 使用说明:
# 1. 安装必要的依赖: pip install pyautogui opencv-python pillow pynput pywin32
# 2. 替换脚本中的游戏窗口标题为你的游戏窗口标题
# 3. 在 templates 文件夹中添加游戏界面元素的截图作为模板
# 4. 运行脚本: python game_bot.py
# 5. 脚本会自动查找游戏窗口，开始战斗，收集奖励
#
# 注意事项:
# - 本脚本仅提供基础框架，需要根据具体游戏进行调整
# - 为了提高识别准确率，建议使用游戏窗口的原始分辨率
# - 使用时请确保游戏窗口未被遮挡
# - 可以通过添加更多的模板和状态判断来提高脚本的智能性
# - 游戏过程中尽量不要操作鼠标和键盘，以免干扰脚本运行