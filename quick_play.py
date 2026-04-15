# -*- coding: utf-8 -*-
import sys
import os
import time
import random

# Set UTF-8 output before any other imports
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

WORK_DIR = r"C:\Users\User\Desktop\DN-main"
GAME_URL = "http://127.0.0.1:5001"

def init_driver():
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--window-size=1400,900")
    options.add_argument("--user-data-dir=C:\\Users\\User\\AppData\\Local\\Google\\Chrome\\User Data")
    options.add_argument("--profile-directory=Default")
    try:
        driver = webdriver.Chrome(options=options)
    except Exception as e:
        print(f"Failed with user data, trying no-sandbox: {e}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1400,900")
        driver = webdriver.Chrome(options=options)
    
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.implicitly_wait(5)
    return driver

def get_option_buttons(driver):
    """Get all visible option buttons"""
    try:
        # Try specific selectors first
        buttons = driver.find_elements(By.CSS_SELECTOR, "button")
        visible_buttons = [b for b in buttons if b.is_displayed() and b.rect.get('width', 0) > 80]
        
        # Filter for option-like buttons
        option_buttons = []
        for b in visible_buttons:
            text = b.text.strip()
            if text and len(text) > 5 and len(text) < 300:
                option_buttons.append(b)
        
        return option_buttons
    except Exception as e:
        print(f"Error getting buttons: {e}")
        return []

def main():
    print("=" * 60)
    print("快速游戏测试 - 随机选择选项")
    print("=" * 60)
    
    driver = init_driver()
    
    try:
        print(f"访问游戏: {GAME_URL}")
        driver.get(GAME_URL)
        time.sleep(5)
        
        # Step 1: Click start button
        print("查找并点击「开始新游戏」按钮...")
        try:
            start_btn = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.ID, "start-btn"))
            )
            start_btn.click()
            print("已点击开始新游戏")
        except TimeoutException:
            print("未找到开始按钮，尝试XPath...")
            try:
                btns = driver.find_elements(By.TAG_NAME, "button")
                for b in btns:
                    if "开始" in b.text and b.is_displayed():
                        b.click()
                        print(f"点击了: {b.text[:30]}")
                        break
            except Exception as e:
                print(f"XPath点击失败: {e}")
        
        time.sleep(3)
        
        # Step 2: Configure game settings
        print("等待游戏设置界面...")
        time.sleep(5)
        
        # Step 3: Start game
        print("查找并点击确认/开始按钮...")
        try:
            confirm_btns = driver.find_elements(By.XPATH, "//button[contains(text(), '开始游戏') or contains(text(), '确认') or contains(text(), '生成')]")
            for b in confirm_btns:
                if b.is_displayed() and b.rect.get('width', 0) > 100:
                    b.click()
                    print(f"点击了: {b.text[:30]}")
                    break
        except Exception as e:
            print(f"确认按钮点击失败: {e}")
        
        time.sleep(5)
        
        # Step 4: Game loop - random selections
        for round_num in range(1, 8):
            print(f"\n回合 {round_num}")
            
            # Wait for options to appear
            time.sleep(4)
            
            buttons = get_option_buttons(driver)
            
            if not buttons:
                print("未找到选项按钮，刷新并重试...")
                time.sleep(5)
                buttons = get_option_buttons(driver)
            
            if not buttons:
                print("仍然没有找到按钮，尝试其他方式...")
                try:
                    all_btns = driver.find_elements(By.TAG_NAME, "button")
                    buttons = [b for b in all_btns if b.is_displayed() and b.rect.get('width', 0) > 50 and b.text.strip()]
                except:
                    pass
            
            if not buttons:
                print("无法继续，没有可点击的按钮")
                break
            
            # Random selection
            idx = random.randint(0, min(2, len(buttons) - 1))
            btn_text = buttons[idx].text.strip()[:80]
            print(f"选择 ({idx+1}/{len(buttons)}): {btn_text}")
            buttons[idx].click()
            
            time.sleep(4)
            
            # Check for ending
            page_source = driver.page_source
            if any(kw in page_source for kw in ["结局", "结束", "THE END", "Game Over", "通关"]):
                print("检测到游戏结局！")
                break
        
        print("\n" + "=" * 60)
        print("游戏完成")
        print("=" * 60)
        time.sleep(5)
        
    except Exception as e:
        print(f"游戏过程出错: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("关闭浏览器...")
        time.sleep(2)
        driver.quit()

if __name__ == "__main__":
    main()
