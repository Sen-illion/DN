# -*- coding: utf-8 -*-
"""
游戏数据集自动构建脚本 - 基于浏览器自动化
"""
import os
import sys
import json
import time
import random
import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains

# 设置
from project_paths import PROJECT_ROOT, ensure_project_dir

WORK_DIR = PROJECT_ROOT
DATASET_DIR = ensure_project_dir("dataset")
LOG_FILE = DATASET_DIR / "execution_log.txt"

GAME_URL = "http://127.0.0.1:5001"
THEMES = [
    ("青春校园类", "高三同桌", "校园天台告白"),
    ("都市邂逅类", "便利店深夜", "地铁重逢"),
    ("古风初见类", "江南雨巷", "书院初遇"),
    ("悬疑执念类", "旧宅异响", "神秘信件"),
    ("奇幻轻恋类", "猫咪低语", "星灵坠落"),
    ("职场温情类", "加班深夜", "职场并肩"),
    ("乡村治愈类", "乡村小院", "田埂漫步"),
    ("民国情愫类", "老上海弄堂", "民国书院"),
    ("独居治愈类", "独居小屋", "深夜煮茶"),
    ("异地牵挂类", "异地相隔", "书信传情"),
    ("宠物陪伴类", "橘猫相伴", "小狗随行"),
    ("旧物回忆类", "旧相册", "老钢笔"),
    ("奇幻梦境类", "梦境相逢", "梦入古籍"),
    ("邻里温情类", "邻里相伴", "楼下闲谈"),
    ("遗憾释怀类", "旧人重逢", "错过的人"),
    ("文艺治愈类", "书店一隅", "午后读书"),
    ("奇幻信物类", "古玉为证", "银手链"),
    ("校园回忆类", "旧校服", "校园广播"),
    ("都市孤独类", "城市霓虹", "深夜街头"),
    ("古风遗憾类", "宫墙深锁", "渡口送别"),
    ("自然治愈类", "山林间", "海边漫步"),
    ("奇幻守护类", "精灵守护", "守护灵"),
    ("职场成长类", "职场历练", "前辈指引"),
    ("家庭温情类", "家常菜香", "深夜等候"),
    ("旅行邂逅类", "古镇旅行", "旅途相伴"),
    ("奇幻时光类", "时光沙漏", "时光邮局"),
    ("文艺邂逅类", "画展相遇", "琴声相伴"),
    ("古风守护类", "江湖守护", "贴身侍卫"),
    ("悬疑治愈类", "迷雾散去", "执念解开"),
]
IMAGE_STYLES = ["水彩风格", "厚涂油画风格", "赛璐璐风格", "像素艺术风格", "中国古风水墨", "扁平插画风格", "写实摄影风格", "动漫风格", "梦幻星云风格", "复古胶片风格"]
ENDINGS = ["normal_ending", "happy_ending", "bittersweet_ending", "mystery_ending", "romantic_ending", "tearful_ending"]
DIFFICULTIES = ["简单", "中等", "困难"]
NAMES = ["林小雨", "顾星河", "沈念", "苏晚晴", "陈默", "叶知秋", "程悠悠", "陆子衿"]
PERSONALITIES = ["内向温柔", "阳光开朗", "沉稳内敛", "活泼直率", "敏感细腻", "成熟稳重"]

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def init_driver():
    """初始化Chrome浏览器"""
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--window-size=1400,900")
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.implicitly_wait(5)
    return driver

def click_when_ready(driver, by, value, timeout=15):
    """等待元素可点击并点击"""
    try:
        el = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, value)))
        el.click()
        return el
    except:
        return None

def type_when_ready(driver, by, value, text, timeout=10):
    """等待元素可输入并输入"""
    try:
        el = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
        el.clear()
        el.send_keys(text)
        return el
    except:
        return None

def wait_for_text(driver, text, timeout=5):
    """等待页面包含某文本"""
    try:
        WebDriverWait(driver, timeout).until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), text))
        return True
    except:
        return False

def wait_for_ajax(driver, timeout=30):
    """等待AJAX加载完成"""
    time.sleep(2)
    try:
        WebDriverWait(driver, timeout).until(lambda d: d.execute_script("return jQuery.active == 0"))
    except:
        pass

def start_new_game(driver):
    """开始新游戏"""
    log("点击开始新游戏...")
    # 点击开始新游戏按钮
    btn = click_when_ready(driver, By.ID, "start-btn")
    if not btn:
        # 尝试使用文本定位
        try:
            btns = driver.find_elements(By.TAG_NAME, "button")
            for b in btns:
                if "开始" in b.text or "新游戏" in b.text:
                    b.click()
                    break
        except:
            pass
    time.sleep(3)
    log("进入游戏设置界面")
    return True

def configure_game(driver, theme, style, name, personality, difficulty, ending):
    """配置游戏参数"""
    log(f"配置游戏: {theme}, {style}, {name}, {personality}, {difficulty}, {ending}")
    
    # 等待设置界面加载
    time.sleep(3)
    
    # 填写主题（如果有输入框）
    try:
        inputs = driver.find_elements(By.TAG_NAME, "input")
        for inp in inputs:
            placeholder = inp.get_attribute("placeholder") or ""
            if "主题" in placeholder or "theme" in placeholder.lower():
                inp.clear()
                inp.send_keys(theme)
                log(f"已填写主题: {theme}")
                break
    except Exception as e:
        log(f"填写主题失败: {e}")
    
    # 选择风格（如果有下拉框或选项）
    try:
        style_btns = driver.find_elements(By.XPATH, "//*[contains(text(), '" + style + "')]")
        if style_btns:
            style_btns[0].click()
            log(f"已选择风格: {style}")
    except:
        pass
    
    # 选择难度
    try:
        diff_btns = driver.find_elements(By.XPATH, "//*[contains(text(), '" + difficulty + "')]")
        if diff_btns:
            diff_btns[0].click()
            log(f"已选择难度: {difficulty}")
    except:
        pass
    
    time.sleep(2)

def select_option(driver, index):
    """选择选项"""
    try:
        options = driver.find_elements(By.CSS_SELECTOR, ".option-btn, .choice-btn, [class*='option'], [class*='choice']")
        if not options:
            options = driver.find_elements(By.TAG_NAME, "button")
            options = [o for o in options if o.is_displayed() and o.rect['width'] > 50]
        
        if options and index < len(options):
            options[index].click()
            log(f"选择选项 {index + 1}")
            return True
    except Exception as e:
        log(f"选择选项失败: {e}")
    return False

def get_scene_text(driver):
    """获取当前场景文本"""
    try:
        # 尝试多种选择器
        selectors = [".scene-text", ".story-text", ".narrative", "[class*='scene']", "[class*='story']", "[class*='text']"]
        for sel in selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in elements:
                if el.is_displayed() and el.text.strip():
                    return el.text.strip()[:500]
        
        # 备用：从body获取所有p标签
        ps = driver.find_elements(By.TAG_NAME, "p")
        for p in ps:
            if p.is_displayed() and len(p.text.strip()) > 50:
                return p.text.strip()[:500]
    except:
        pass
    return ""

def get_options(driver):
    """获取所有选项按钮"""
    try:
        options = driver.find_elements(By.CSS_SELECTOR, "button.option-btn, button.choice-btn, .option-btn, .choice-btn")
        if not options:
            buttons = driver.find_elements(By.TAG_NAME, "button")
            options = [b for b in buttons if b.is_displayed() and b.rect.get('width', 0) > 80]
        return options
    except:
        return []

def take_screenshot(driver, name):
    """截图"""
    try:
        path = DATASET_DIR / f"{name}_{datetime.datetime.now().strftime('%H%M%S')}.png"
        driver.save_screenshot(str(path))
        log(f"截图: {path.name}")
        return path
    except Exception as e:
        log(f"截图失败: {e}")
        return None

def play_single_game(driver, round_num, params):
    """玩一局游戏"""
    log(f"\n{'='*50}")
    log(f"第 {round_num}/50 轮: {params['theme']}")
    log(f"{'='*50}")
    
    # 访问游戏页面
    driver.get(GAME_URL)
    time.sleep(5)
    
    choices = []
    max_rounds = random.randint(5, 6)
    
    try:
        # 点击开始游戏
        start_new_game(driver)
        time.sleep(3)
        
        # 配置游戏
        configure_game(driver, params['theme'], params['image_style'], 
                       params['protagonist']['name'], params['protagonist']['personality'],
                       params['difficulty'], params['ending_type'])
        time.sleep(2)
        
        # 确认开始
        try:
            confirm_btns = driver.find_elements(By.XPATH, "//button[contains(text(), '开始') or contains(text(), '确认')]")
            if confirm_btns:
                confirm_btns[0].click()
                log("确认开始游戏")
        except:
            pass
        
        time.sleep(5)
        
        # 游戏循环
        for round_idx in range(1, max_rounds + 1):
            log(f"回合 {round_idx}/{max_rounds}")
            
            # 等待选项出现
            time.sleep(3)
            
            # 获取场景文本
            scene_text = get_scene_text(driver)
            if scene_text:
                log(f"场景文本: {scene_text[:100]}...")
            
            # 获取选项
            options = get_options(driver)
            if not options:
                log("没有找到选项，尝试等待...")
                time.sleep(5)
                options = get_options(driver)
            
            if not options:
                log("无法获取选项，结束游戏")
                break
            
            # 随机选择
            selected_idx = random.randint(0, min(2, len(options) - 1))
            selected_text = options[selected_idx].text[:100] if options[selected_idx].text else ""
            
            choices.append({
                "round": round_idx,
                "scene_description": scene_text,
                "options_count": len(options),
                "selected": selected_idx,
                "selected_text": selected_text
            })
            
            # 点击选择
            options[selected_idx].click()
            log(f"已选择: {selected_text[:50]}...")
            
            time.sleep(3)
            
            # 截图记录
            take_screenshot(driver, f"round{round_num}_{round_idx}")
            
            # 检查是否到达结局
            if any(kw in driver.page_source for kw in ["结局", "结束", "THE END", "end"]):
                log("检测到游戏结局")
                time.sleep(3)
                break
        
        # 获取最终结局文本
        final_text = get_scene_text(driver)
        
        # 游戏结束，截图
        take_screenshot(driver, f"final_round{round_num}")
        
        return {
            "round_number": round_num,
            "theme": params['theme'],
            "theme_category": params['theme_category'],
            "image_style": params['image_style'],
            "ending_type": params['ending_type'],
            "difficulty": params['difficulty'],
            "protagonist": params['protagonist'],
            "choices": choices,
            "final_scene": final_text[:500],
            "timestamp": datetime.datetime.now().isoformat()
        }
        
    except Exception as e:
        log(f"游戏异常: {e}")
        take_screenshot(driver, f"error_round{round_num}")
        return None

def main():
    log("=" * 60)
    log("游戏数据集自动构建开始")
    log("=" * 60)
    
    # 初始化浏览器
    driver = init_driver()
    
    try:
        # 检查已完成轮次
        existing = sorted([int(f.stem.split("_")[1]) for f in DATASET_DIR.glob("game_*.json")])
        start_round = (existing[-1] + 1) if existing else 1
        log(f"已有 {len(existing)} 轮，从第 {start_round} 轮开始")
        
        # 生成50轮游戏
        for i in range(start_round, 51):
            random.seed(f"seed_{i}")
            
            # 选择主题
            cat, s1, s2 = random.choice(THEMES)
            theme = random.choice([s1, s2])
            
            params = {
                "theme_category": cat,
                "theme": theme,
                "image_style": random.choice(IMAGE_STYLES),
                "ending_type": random.choice(ENDINGS),
                "difficulty": random.choice(DIFFICULTIES),
                "protagonist": {
                    "name": random.choice(NAMES),
                    "personality": random.choice(PERSONALITIES)
                }
            }
            
            result = play_single_game(driver, i, params)
            
            if result:
                # 保存结果
                game_file = DATASET_DIR / f"game_{i:03d}.json"
                with open(game_file, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                log(f"第 {i} 轮完成，保存到 {game_file.name}")
            else:
                log(f"第 {i} 轮失败")
            
            # 每5轮休息
            if i % 5 == 0:
                log(f"完成 {i} 轮，休息30秒...")
                time.sleep(30)
            
            time.sleep(5)
        
        # 汇总
        all_games = []
        for f in sorted(DATASET_DIR.glob("game_*.json")):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    all_games.append(json.load(fp))
            except:
                pass
        
        with open(DATASET_DIR / "all_games.json", "w", encoding="utf-8") as f:
            json.dump(all_games, f, ensure_ascii=False, indent=2)
        
        log(f"\n完成！共收集 {len(all_games)} 轮游戏")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
