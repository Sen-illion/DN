# -*- coding: utf-8 -*-
"""
游戏数据集构建脚本 - 使用API直接调用
不需要浏览器，直接通过REST API与后端交互
"""
import os
import sys
import json
import time
import random
import datetime
import hashlib
from pathlib import Path
import urllib.request
import urllib.error

from project_paths import PROJECT_ROOT, ensure_project_dir

WORK_DIR = PROJECT_ROOT
DATASET_DIR = ensure_project_dir("dataset")
LOG_FILE = DATASET_DIR / "execution_log.txt"

API_BASE = "http://127.0.0.1:5001"

# 数据配置
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

ENDINGS = [
    "normal_ending", "happy_ending", "bittersweet_ending",
    "mystery_ending", "romantic_ending", "tearful_ending"
]

DIFFICULTIES = ["简单", "中等", "困难"]
NAMES = ["林小雨", "顾星河", "沈念", "苏晚晴", "陈默", "叶知秋", "程悠悠", "陆子衿"]
PERSONALITIES = ["内向温柔", "阳光开朗", "沉稳内敛", "活泼直率", "敏感细腻", "成熟稳重"]

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def api_post(endpoint, payload, timeout=300):
    """发送POST请求"""
    url = f"{API_BASE}/{endpoint}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500]
        return {"error": f"HTTP {e.code}: {body}"}
    except Exception as e:
        return {"error": str(e)}

def api_get(endpoint, timeout=60):
    """发送GET请求"""
    url = f"{API_BASE}/{endpoint}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500]
        return {"error": f"HTTP {e.code}: {body}"}
    except Exception as e:
        return {"error": str(e)}

def check_backend():
    """检查后端状态"""
    result = api_get("list-saves", timeout=10)
    if "error" in result:
        log(f"后端检查失败: {result['error']}")
        return False
    log("后端状态正常")
    return True

def generate_params(round_num):
    """生成游戏参数"""
    random.seed(f"round_{round_num}_{datetime.datetime.now().date()}")
    
    cat, s1, s2 = random.choice(THEMES)
    theme = random.choice([s1, s2])
    
    return {
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

def extract_game_id(result):
    """从API响应中提取game_id"""
    if "game_id" in result:
        return result["game_id"]
    if "id" in result:
        return result["id"]
    if "data" in result and isinstance(result["data"], dict):
        return result["data"].get("game_id") or result["data"].get("id")
    return None

def extract_scenes_and_options(game_data):
    """从游戏数据中提取场景和选项"""
    scenes = []
    options = []
    
    def traverse(obj, depth=0):
        if depth > 10:
            return
        if isinstance(obj, dict):
            # 尝试找到场景文本
            for key in ["scene", "text", "description", "content", "story"]:
                if key in obj:
                    val = obj[key]
                    if isinstance(val, str) and len(val) > 20:
                        scenes.append(val)
            
            # 尝试找到选项
            for key in ["options", "choices", "selections"]:
                if key in obj and isinstance(obj[key], (list, dict)):
                    if isinstance(obj[key], list):
                        for item in obj[key]:
                            if isinstance(item, str):
                                options.append(item)
                            elif isinstance(item, dict):
                                for k in ["text", "content", "description"]:
                                    if k in item and isinstance(item[k], str):
                                        options.append(item[k])
                                        break
            
            for v in obj.values():
                traverse(v, depth + 1)
        elif isinstance(obj, list):
            for item in obj:
                traverse(item, depth + 1)
    
    traverse(game_data)
    return scenes, options

def play_game(round_num):
    """玩一局游戏并返回数据"""
    params = generate_params(round_num)
    
    log(f"\n{'='*50}")
    log(f"第 {round_num}/50 轮: {params['theme']}")
    log(f"风格:{params['image_style']} 结局:{params['ending_type']} 难度:{params['difficulty']}")
    log(f"{'='*50}")
    
    # 创建游戏
    log("创建游戏中...")
    payload = {
        "gameTheme": params["theme"],
        "imageStyle": params["image_style"],
        "protagonistAttr": params["protagonist"],
        "difficulty": params["difficulty"],
        "toneKey": params["ending_type"]
    }
    
    result = api_post("generate-worldview", payload, timeout=300)
    
    if "error" in result:
        log(f"创建游戏失败: {result['error']}")
        return None
    
    game_id = extract_game_id(result)
    if not game_id:
        log(f"无法获取game_id: {str(result)[:200]}")
        return None
    
    log(f"游戏创建成功: {game_id}")
    
    # 等待初始化
    time.sleep(5)
    
    choices = []
    max_rounds = random.randint(5, 6)
    
    for round_idx in range(1, max_rounds + 1):
        log(f"回合 {round_idx}/{max_rounds}")
        
        # 获取当前游戏状态
        game_data = api_get(f"game/{game_id}", timeout=60)
        
        if "error" in game_data:
            log(f"获取游戏状态失败: {game_data['error']}")
            break
        
        # 提取场景和选项
        scenes, opts = extract_scenes_and_options(game_data)
        
        current_scene = scenes[-1] if scenes else ""
        available_options = opts[-3:] if opts else []
        
        if not available_options:
            log("没有可用选项，尝试预生成...")
            # 尝试预生成下一层
            pregen = api_post("pregenerate-next-layers", {"gameId": game_id}, timeout=120)
            if "error" not in pregen:
                time.sleep(3)
                game_data = api_get(f"game/{game_id}", timeout=60)
                scenes, opts = extract_scenes_and_options(game_data)
                available_options = opts[-3:] if opts else []
        
        if not available_options:
            log("仍无选项，可能游戏结束")
            break
        
        # 随机选择
        selected_idx = random.randint(0, min(2, len(available_options) - 1))
        selected_text = available_options[selected_idx]
        
        choices.append({
            "round": round_idx,
            "scene": current_scene[:300] if current_scene else "",
            "options": available_options[:3],
            "selected": selected_idx,
            "selected_text": selected_text[:200] if isinstance(selected_text, str) else str(selected_text)[:200]
        })
        
        log(f"选择: {selected_text[:50]}...")
        
        # 提交选择
        scene_id = game_data.get("current_scene_id") or game_data.get("scene_id") or ""
        
        select_payload = {
            "gameId": game_id,
            "sceneId": scene_id,
            "optionIndex": selected_idx
        }
        
        select_result = api_post("select-option", select_payload, timeout=120)
        
        if "error" in select_result:
            log(f"选择失败: {select_result['error']}")
        
        # 等待下一场景生成
        time.sleep(5)
    
    # 获取最终结局
    final_data = api_get(f"game/{game_id}", timeout=60)
    final_scene = ""
    
    if "error" not in final_data:
        scenes, _ = extract_scenes_and_options(final_data)
        final_scene = " | ".join(scenes[-3:])[:1000] if scenes else ""
    
    return {
        "round_number": round_num,
        "game_id": game_id,
        "theme": params["theme"],
        "theme_category": params["theme_category"],
        "image_style": params["image_style"],
        "ending_type": params["ending_type"],
        "difficulty": params["difficulty"],
        "protagonist": params["protagonist"],
        "choices": choices,
        "final_scene": final_scene,
        "timestamp": datetime.datetime.now().isoformat()
    }

def main():
    log("=" * 60)
    log("游戏数据集构建开始 (API模式)")
    log("=" * 60)
    
    if not check_backend():
        log("错误：后端服务未运行！")
        return
    
    # 检查已有数据
    existing = sorted([int(f.stem.split("_")[1]) for f in DATASET_DIR.glob("game_*.json")])
    start_round = (existing[-1] + 1) if existing else 1
    log(f"已有 {len(existing)} 轮，从第 {start_round} 轮开始")
    
    success_count = len(existing)
    
    # 运行50轮
    for i in range(start_round, 51):
        try:
            result = play_game(i)
            
            if result:
                # 保存
                game_file = DATASET_DIR / f"game_{i:03d}.json"
                with open(game_file, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                
                success_count += 1
                log(f"第 {i} 轮完成 ({success_count}/50)")
            else:
                log(f"第 {i} 轮失败，重试...")
                time.sleep(10)
                result = play_game(i)
                if result:
                    game_file = DATASET_DIR / f"game_{i:03d}.json"
                    with open(game_file, "w", encoding="utf-8") as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                    success_count += 1
                    log(f"第 {i} 轮重试成功")
            
        except Exception as e:
            log(f"异常: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(15)
        
        # 每5轮休息
        if i % 5 == 0:
            log(f"完成 {i} 轮，休息20秒...")
            time.sleep(20)
        
        time.sleep(3)
    
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
    log(f"数据目录: {DATASET_DIR}")

if __name__ == "__main__":
    main()
