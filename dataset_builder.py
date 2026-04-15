# -*- coding: utf-8 -*-
"""
游戏数据集自动化构建脚本
自动玩AI文本冒险游戏，收集多样化数据
"""
import os
import sys
import json
import time
import random
import datetime
import hashlib
from pathlib import Path

# 设置工作目录
WORK_DIR = Path(r"C:\Users\User\Desktop\DN-main")
DATASET_DIR = WORK_DIR / "dataset"
DATASET_DIR.mkdir(exist_ok=True)

# API基础URL
API_BASE = "http://127.0.0.1:5001"

# 日志文件
LOG_FILE = DATASET_DIR / "execution_log.txt"

def log(msg):
    """写日志"""
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def api_post(endpoint, payload, timeout=120):
    import urllib.request
    import urllib.error
    url = f"{API_BASE}/{endpoint}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}"}
    except Exception as e:
        return {"error": str(e)}

def api_get(endpoint, timeout=30):
    import urllib.request
    url = f"{API_BASE}/{endpoint}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}

def check_backend():
    """检查后端是否运行"""
    result = api_get("list-saves", timeout=5)
    if "error" in result:
        log(f"后端检查失败: {result['error']}")
        return False
    log("后端状态正常")
    return True

# ============ 数据配置 ============
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

IMAGE_STYLES = [
    "水彩风格", "厚涂油画风格", "赛璐璐风格", "像素艺术风格",
    "中国古风水墨", "扁平插画风格", "写实摄影风格",
    "动漫风格", "梦幻星云风格", "复古胶片风格"
]

ENDING_TYPES = [
    "normal_ending", "happy_ending", "bittersweet_ending",
    "mystery_ending", "romantic_ending", "tearful_ending"
]

DIFFICULTIES = ["简单", "中等", "困难"]

PROTAGONIST_ATTRS = [
    {"name": "林小雨", "personality": "内向温柔"},
    {"name": "顾星河", "personality": "阳光开朗"},
    {"name": "沈念", "personality": "沉稳内敛"},
    {"name": "苏晚晴", "personality": "活泼直率"},
    {"name": "陈默", "personality": "敏感细腻"},
    {"name": "叶知秋", "personality": "成熟稳重"},
    {"name": "程悠悠", "personality": "随性洒脱"},
    {"name": "陆子衿", "personality": "理性冷静"},
]

def generate_game_seed(round_num):
    """生成游戏参数组合"""
    random.seed(f"seed_{round_num}_{datetime.datetime.now().date()}")
    
    # 选择主题 - 确保多样性
    theme_category, sub1, sub2 = random.choice(THEMES)
    theme = random.choice([sub1, sub2])
    
    # 选择其他参数
    style = random.choice(IMAGE_STYLES)
    ending = random.choice(ENDING_TYPES)
    difficulty = random.choice(DIFFICULTIES)
    protagonist = random.choice(PROTAGONIST_ATTRS)
    
    return {
        "theme_category": theme_category,
        "theme": theme,
        "image_style": style,
        "ending_type": ending,
        "difficulty": difficulty,
        "protagonist": protagonist
    }

def create_game(params):
    """创建游戏"""
    log(f"创建游戏: 主题={params['theme']}, 风格={params['image_style']}, 结局={params['ending_type']}, 难度={params['difficulty']}")
    
    payload = {
        "gameTheme": params["theme"],
        "imageStyle": params["image_style"],
        "protagonistAttr": params["protagonist"],
        "difficulty": params["difficulty"],
        "toneKey": params["ending_type"]
    }
    
    result = api_post("generate-worldview", payload, timeout=180)
    
    if "error" in result:
        log(f"创建游戏失败: {result['error']}")
        return None
    
    game_id = result.get("game_id") or result.get("id")
    log(f"游戏创建成功: game_id={game_id}")
    return game_id

def play_game_loop(game_id, round_num):
    """玩一局游戏，返回所有选择和结局"""
    choices = []
    max_rounds = random.randint(5, 6)  # 每轮5-6个选择
    
    for round_idx in range(1, max_rounds + 1):
        log(f"  回合 {round_idx}/{max_rounds}...")
        
        # 获取当前场景
        scene_data = api_get(f"game/{game_id}", timeout=30)
        
        if "error" in scene_data:
            log(f"  获取场景失败: {scene_data['error']}")
            break
        
        # 提取场景信息和选项
        scene_desc = ""
        options = []
        
        if "current_scene" in scene_data:
            cs = scene_data["current_scene"]
            scene_desc = cs.get("description", "") or cs.get("text", "")
            options = cs.get("options", []) or cs.get("choices", [])
        elif "scene" in scene_data:
            s = scene_data["scene"]
            scene_desc = s.get("description", "") or s.get("text", "")
            options = s.get("options", []) or s.get("choices", [])
        elif "text" in scene_data:
            scene_desc = scene_data.get("text", "")
            options = scene_data.get("options", [])
        else:
            # 尝试从原始数据中提取
            scene_desc = str(scene_data.get("description", scene_data.get("content", "")))
            options = scene_data.get("options", scene_data.get("choices", []))
        
        # 清洗选项
        if isinstance(options, dict):
            options = list(options.values())
        
        # 选择一个选项（随机）
        if not options:
            log(f"  无可用选项，结束游戏")
            break
        
        selected = random.randint(0, min(len(options) - 1, 2))
        selected_text = options[selected] if isinstance(options[selected], str) else str(options[selected])
        
        choices.append({
            "round": round_idx,
            "scene_description": scene_desc[:500] if scene_desc else "",
            "options": [str(o) for o in options[:3]],
            "selected": selected,
            "result_text": ""
        })
        
        log(f"  选择选项 {selected + 1}/{len(options)}")
        
        # 提交选择
        select_payload = {
            "gameId": game_id,
            "sceneId": scene_data.get("scene_id", scene_data.get("current_scene", {}).get("id", "")),
            "optionIndex": selected
        }
        
        select_result = api_post("select-option", select_payload, timeout=120)
        
        if "error" in select_result:
            log(f"  选择失败: {select_result['error']}")
            # 继续尝试获取下一场景
        
        # 短暂等待让服务器处理
        time.sleep(2)
    
    # 获取最终结局
    final_data = api_get(f"game/{game_id}", timeout=30)
    final_ending = ""
    
    if isinstance(final_data, dict):
        final_ending = final_data.get("ending", final_data.get("final_ending", ""))
        if isinstance(final_ending, dict):
            final_ending = final_ending.get("text", str(final_ending))
        if isinstance(final_ending, str) and len(final_ending) < 10:
            final_ending = final_data.get("content", final_data.get("text", ""))[:500]
    
    # 更新选择的result_text
    if choices and final_ending:
        choices[-1]["result_text"] = final_ending[:300]
    
    return choices, final_ending

def run_round(round_num):
    """运行一轮游戏"""
    log(f"\n{'='*50}")
    log(f"开始第 {round_num}/50 轮游戏")
    log(f"{'='*50}")
    
    # 生成参数
    params = generate_game_seed(round_num)
    
    # 创建游戏
    game_id = create_game(params)
    if not game_id:
        log(f"第 {round_num} 轮失败：无法创建游戏")
        return None
    
    # 等待初始化
    time.sleep(3)
    
    # 玩游戏
    choices, final_ending = play_game_loop(game_id, round_num)
    
    if not choices:
        log(f"第 {round_num} 轮失败：无法获取游戏数据")
        return None
    
    # 构建数据
    game_data = {
        "game_id": game_id,
        "round_number": round_num,
        "theme": params["theme"],
        "theme_category": params["theme_category"],
        "image_style": params["image_style"],
        "ending_type": params["ending_type"],
        "difficulty": params["difficulty"],
        "protagonist": params["protagonist"],
        "choices": choices,
        "final_ending": str(final_ending)[:1000] if final_ending else "",
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    # 保存单个游戏数据
    game_file = DATASET_DIR / f"game_{round_num:03d}.json"
    save_json(game_file, game_data)
    log(f"第 {round_num} 轮完成，保存到 {game_file.name}")
    
    return game_data

def main():
    log("=" * 60)
    log("游戏数据集构建脚本启动")
    log("=" * 60)
    
    # 检查后端
    if not check_backend():
        log("错误：后端服务未运行！")
        return
    
    # 清理旧日志
    if LOG_FILE.exists():
        # 保留最后100行
        lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
        if len(lines) > 100:
            LOG_FILE.write_text("\n".join(lines[-100:]), encoding="utf-8")
    
    # 收集已完成轮次
    existing = sorted([int(f.stem.split("_")[1]) for f in DATASET_DIR.glob("game_*.json")])
    start_round = (existing[-1] + 1) if existing else 1
    
    log(f"数据集目录: {DATASET_DIR}")
    log(f"已有游戏: {existing}")
    log(f"从第 {start_round} 轮开始")
    
    # 运行50轮游戏
    for round_num in range(start_round, 51):
        try:
            result = run_round(round_num)
            if result:
                log(f"第 {round_num} 轮成功")
            else:
                log(f"第 {round_num} 轮失败，重试...")
                time.sleep(10)
                result = run_round(round_num)
                if result:
                    log(f"第 {round_num} 轮重试成功")
        except Exception as e:
            log(f"第 {round_num} 轮异常: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(15)
        
        # 每5轮休息一下
        if round_num % 5 == 0 and round_num < 50:
            log(f"完成 {round_num} 轮，休息15秒...")
            time.sleep(15)
    
    # 汇总所有数据
    all_games = []
    for f in sorted(DATASET_DIR.glob("game_*.json")):
        try:
            all_games.append(load_json(f))
        except Exception as e:
            log(f"加载 {f.name} 失败: {e}")
    
    save_json(DATASET_DIR / "all_games.json", all_games)
    log(f"\n数据集构建完成！共收集 {len(all_games)} 轮游戏")
    log(f"汇总文件: {DATASET_DIR / 'all_games.json'}")

if __name__ == "__main__":
    main()
