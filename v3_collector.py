# -*- coding: utf-8 -*-
"""游戏数据集构建 - 正确交互版"""
import json, time, random, datetime, sys, traceback, copy
import urllib.request, urllib.error
from pathlib import Path

DATASET_DIR = Path(r"C:\Users\User\Documents\DN_dataset")
DATASET_DIR.mkdir(parents=True, exist_ok=True)
API_BASE = "http://127.0.0.1:5001"

THEMES = [
    ("青春校园", "高三同桌", "校园天台告白"),
    ("都市邂逅", "便利店深夜", "地铁重逢"),
    ("古风初见", "江南雨巷", "书院初遇"),
    ("悬疑执念", "旧宅异响", "神秘信件"),
    ("奇幻轻恋", "猫咪低语", "星灵坠落"),
    ("职场温情", "加班深夜", "职场并肩"),
    ("乡村治愈", "乡村小院", "田埂漫步"),
    ("民国情愫", "老上海弄堂", "民国书院"),
    ("独居治愈", "独居小屋", "深夜煮茶"),
    ("异地牵挂", "异地相隔", "书信传情"),
    ("宠物陪伴", "橘猫相伴", "小狗随行"),
    ("旧物回忆", "旧相册", "老钢笔"),
    ("奇幻梦境", "梦境相逢", "梦入古籍"),
    ("邻里温情", "邻里相伴", "楼下闲谈"),
    ("遗憾释怀", "旧人重逢", "错过的人"),
    ("文艺治愈", "书店一隅", "午后读书"),
    ("奇幻信物", "古玉为证", "银手链"),
    ("校园回忆", "旧校服", "校园广播"),
    ("都市孤独", "城市霓虹", "深夜街头"),
    ("古风遗憾", "宫墙深锁", "渡口送别"),
    ("自然治愈", "山林间", "海边漫步"),
    ("奇幻守护", "精灵守护", "守护灵"),
    ("职场成长", "职场历练", "前辈指引"),
    ("家庭温情", "家常菜香", "深夜等候"),
    ("旅行邂逅", "古镇旅行", "旅途相伴"),
    ("奇幻时光", "时光沙漏", "时光邮局"),
    ("文艺邂逅", "画展相遇", "琴声相伴"),
    ("古风守护", "江湖守护", "贴身侍卫"),
    ("悬疑治愈", "迷雾散去", "执念解开"),
]
STYLES = ["水彩风格", "厚涂油画", "赛璐璐", "像素艺术", "水墨", "扁平插画", "写实", "动漫", "梦幻星云", "复古胶片"]
ENDINGS = ["normal_ending", "happy_ending", "bittersweet_ending", "mystery_ending", "romantic_ending", "tearful_ending"]
DIFFS = ["简单", "中等", "困难"]
NAMES = ["林小雨", "顾星河", "沈念", "苏晚晴", "陈默", "叶知秋", "程悠悠", "陆子衿"]
PERSONALITIES = ["内向温柔", "阳光开朗", "沉稳内敛", "活泼直率", "敏感细腻", "成熟稳重"]

def api_post(endpoint, payload, timeout=300):
    url = f"{API_BASE}/{endpoint}"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            print(f"    API {endpoint}: {time.time()-t0:.1f}s", flush=True)
            return result
    except Exception as e:
        print(f"    API {endpoint} FAILED after {time.time()-t0:.1f}s: {e}", flush=True)
        return {"error": str(e)}

def save(i, data):
    try:
        with open(DATASET_DIR / f"game_{i:03d}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"    Saved game_{i:03d}.json", flush=True)
        return True
    except Exception as e:
        print(f"    Save error: {e}", flush=True)
        return False

def play(i):
    random.seed(f"seed_{i}")
    cat, s1, s2 = random.choice(THEMES)
    theme = random.choice([s1, s2])
    params = {
        "theme": theme, "cat": cat,
        "style": random.choice(STYLES), "ending": random.choice(ENDINGS),
        "diff": random.choice(DIFFS),
        "protagonist": {"name": random.choice(NAMES), "personality": random.choice(PERSONALITIES)}
    }
    
    print(f"\n[{i}/50] {theme} | {params['style']} | {params['ending']}", flush=True)
    
    # Step 1: 创建游戏世界观
    print(f"    Creating worldview...", flush=True)
    r = api_post("generate-worldview", {
        "gameTheme": theme, "imageStyle": params["style"],
        "protagonistAttr": params["protagonist"],
        "difficulty": params["diff"], "toneKey": params["ending"]
    }, timeout=300)
    
    if "error" in r:
        print(f"    Create failed: {r['error']}", flush=True)
        return None
    
    global_state = r.get("globalState", {})
    game_id = global_state.get("game_id", "unknown")
    print(f"    game_id: {game_id}", flush=True)
    
    # 等待初始选项预生成
    time.sleep(3)
    
    choices = []
    current_options = []
    scene_id = None
    max_rounds = random.randint(5, 6)
    
    for rnd in range(1, max_rounds + 1):
        print(f"    Round {rnd}/{max_rounds}", flush=True)
        
        # 确定选项文本
        if rnd == 1:
            # 第一次：使用"开始游戏"
            option_text = "开始游戏"
            option_index = 0
        else:
            if not current_options:
                print(f"    No options available, ending game", flush=True)
                break
            # 随机选择一个选项
            option_index = random.randint(0, min(2, len(current_options) - 1))
            option_text = current_options[option_index] if isinstance(current_options[option_index], str) else str(current_options[option_index])
        
        print(f"    Choosing: {option_text[:40]}...", flush=True)
        
        # Step 2: 调用 generate-option
        opt_payload = {
            "option": option_text,
            "optionIndex": option_index,
            "globalState": global_state,
            "sceneId": scene_id or "initial",
            "currentOptions": current_options
        }
        
        opt_result = api_post("generate-option", opt_payload, timeout=300)
        
        if "error" in opt_result:
            print(f"    Option generation failed: {opt_result['error']}", flush=True)
            break
        
        # 提取结果
        data = opt_result.get("data", opt_result)
        scene_text = data.get("scene", "")
        next_options = data.get("next_options", [])
        scene_image = data.get("scene_image", {})
        flow_update = data.get("flow_update", {})
        
        # 更新globalState
        if "globalState" in opt_result:
            global_state = opt_result["globalState"]
        elif "updated_global_state" in opt_result:
            global_state = opt_result["updated_global_state"]
        
        # 更新scene_id
        new_scene_id = opt_result.get("sceneId") or data.get("sceneId")
        if new_scene_id:
            scene_id = new_scene_id
        
        choices.append({
            "round": rnd,
            "option_text": option_text[:100],
            "option_index": option_index,
            "scene": scene_text[:300] if scene_text else "",
            "next_options": [str(o)[:80] for o in (next_options or [])[:3]],
            "has_image": bool(scene_image and scene_image.get("url"))
        })
        
        current_options = next_options or []
        print(f"    Scene: {scene_text[:60]}... | Next: {len(next_options or [])} options", flush=True)
        
        # 短暂等待
        time.sleep(2)
    
    # Step 3: 生成结局
    print(f"    Generating ending...", flush=True)
    ending_result = api_post("generate-ending", {
        "globalState": global_state,
        "gameId": game_id
    }, timeout=300)
    
    ending_text = ""
    if "error" not in ending_result:
        ending_data = ending_result.get("data", ending_result)
        ending_text = ending_data.get("ending", ending_data.get("text", ""))
        if isinstance(ending_text, dict):
            ending_text = ending_text.get("text", str(ending_text))
    
    # 保存游戏
    api_post("save-game", {"gameId": game_id, "globalState": global_state}, timeout=60)
    
    return {
        "round": i,
        "game_id": game_id,
        "theme": theme,
        "category": cat,
        "style": params["style"],
        "ending_type": params["ending"],
        "difficulty": params["diff"],
        "protagonist": params["protagonist"],
        "choices": choices,
        "ending_text": str(ending_text)[:500] if ending_text else "",
        "timestamp": datetime.datetime.now().isoformat()
    }

def main():
    print("=" * 50, flush=True)
    print("Game Dataset Builder v3 - Correct API Flow", flush=True)
    print(f"Dataset dir: {DATASET_DIR}", flush=True)
    print("=" * 50, flush=True)
    
    # 检查后端
    try:
        r = urllib.request.urlopen(f"{API_BASE}/list-saves", timeout=10)
        print("Backend OK", flush=True)
    except:
        print("Backend NOT available!", flush=True)
        return
    
    # 已有数据
    existing = sorted([int(f.stem.split("_")[1]) for f in DATASET_DIR.glob("game_*.json")])
    start = (existing[-1] + 1) if existing else 1
    success = len(existing)
    print(f"Existing: {success}, starting from {start}", flush=True)
    
    for i in range(start, 51):
        try:
            result = play(i)
            if result and save(i, result):
                success += 1
                print(f"  -> OK [{success}/50]", flush=True)
            else:
                print(f"  -> FAILED, retry in 15s...", flush=True)
                time.sleep(15)
                result = play(i)
                if result and save(i, result):
                    success += 1
                    print(f"  -> retry OK [{success}/50]", flush=True)
        except Exception as e:
            print(f"  -> EXCEPTION: {e}", flush=True)
            traceback.print_exc()
            time.sleep(15)
        
        if i % 5 == 0 and i < 50:
            print(f"\n--- {i} done ({success} success), rest 20s ---\n", flush=True)
            time.sleep(20)
    
    # 汇总
    all_games = []
    for f in sorted(DATASET_DIR.glob("game_*.json")):
        try:
            with open(f, encoding="utf-8") as fp:
                all_games.append(json.load(fp))
        except: pass
    
    with open(DATASET_DIR / "all_games.json", "w", encoding="utf-8") as f:
        json.dump(all_games, f, ensure_ascii=False, indent=2)
    
    print(f"\nDONE! Total: {len(all_games)} games collected", flush=True)
    print(f"Output: {DATASET_DIR}", flush=True)

if __name__ == "__main__":
    main()
