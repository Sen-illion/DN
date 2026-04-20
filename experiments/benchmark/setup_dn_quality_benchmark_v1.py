from __future__ import annotations

import csv
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
THEMES_FILE = REPO_ROOT / "game_themes_100.json"
BENCHMARK_DIR = REPO_ROOT / "experiments" / "benchmark"


SELECTED_ITEMS = [
    {
        "theme_id": 1,
        "expected_genre": "现实边陲叙事",
        "expected_tone": "克制、怀旧、微苦",
        "must_have_constraints": [
            "世界观必须围绕边陲驿站生存与人情展开",
            "首段剧情应能自然引出一条可推进的现实冲突",
            "至少返回 2 个具体可执行选项",
            "场景图应与写实风格一致",
        ],
        "forbidden_issues": [
            "现代互联网术语突兀混入",
            "调试文本或报错文本外泄",
            "图像 prompt 出现 URL 或 data:image",
            "人物设定串场到其他作品",
        ],
    },
    {
        "theme_id": 9,
        "expected_genre": "末日生存",
        "expected_tone": "压抑、坚韧、低饱和",
        "must_have_constraints": [
            "剧情必须围绕温室、生存或资源匮乏展开",
            "场景需要体现末日环境压力",
            "首轮剧情应建立明确任务目标",
            "图像风格应保持写实与低饱和",
        ],
        "forbidden_issues": [
            "出现轻喜剧化语气",
            "无关的校园/都市设定混入",
            "选项空泛无法推进",
            "图片与文本完全不匹配",
        ],
    },
    {
        "theme_id": 19,
        "expected_genre": "都市边缘现实",
        "expected_tone": "安静、细腻、生活化",
        "must_have_constraints": [
            "剧情应聚焦都市天台与养鸽人的生活处境",
            "选项应体现日常决策而非夸张冒险",
            "文本必须可读并具备人物行动线",
        ],
        "forbidden_issues": [
            "突然转为科幻或奇幻",
            "出现明显乱码",
            "主角设定与主题无关",
        ],
    },
    {
        "theme_id": 30,
        "expected_genre": "伦理现实科幻",
        "expected_tone": "冷静、辩论感、社会议题",
        "must_have_constraints": [
            "冲突应围绕克隆体或伦理审判展开",
            "首段需要建立制度或社会背景",
            "选项应体现立场或行动选择",
        ],
        "forbidden_issues": [
            "空泛哲学套话堆砌",
            "图像风格脱离写实基调",
            "剧情不含可操作冲突",
        ],
    },
    {
        "theme_id": 2,
        "expected_genre": "近未来科幻灾难",
        "expected_tone": "高压、冷峻、技术感",
        "must_have_constraints": [
            "剧情需围绕月球矿难与生存风险展开",
            "图像应体现赛博/科幻视觉元素",
            "首段要有明确危机感与行动起点",
        ],
        "forbidden_issues": [
            "出现古风或校园设定串场",
            "图像 prompt 混入无关 IP 名称",
            "选项与危机无关",
        ],
    },
    {
        "theme_id": 7,
        "expected_genre": "太空走私冒险",
        "expected_tone": "紧张、危险、流动感",
        "must_have_constraints": [
            "剧情必须围绕航线、走私或星际交易展开",
            "图像需体现赛博/太空感",
            "首段至少给出两个具体决策方向",
        ],
        "forbidden_issues": [
            "无关现实职场设定混入",
            "剧情没有行动目标",
            "视觉风格与赛博不符",
        ],
    },
    {
        "theme_id": 20,
        "expected_genre": "意识科幻",
        "expected_tone": "诡异、理性、失真感",
        "must_have_constraints": [
            "故事应围绕意识上传或遗嘱展开",
            "需要体现数字人格或身份边界问题",
            "选项应可推进主线冲突",
        ],
        "forbidden_issues": [
            "无关古代或校园设定",
            "首段没有核心问题",
            "图片风格不具未来感",
        ],
    },
    {
        "theme_id": 27,
        "expected_genre": "网络舆论赛博叙事",
        "expected_tone": "讽刺、紧绷、公众性",
        "must_have_constraints": [
            "剧情应体现偶像、舆论或全息表演元素",
            "首段必须建立公共事件背景",
            "选项需反映舆论应对或真相调查",
        ],
        "forbidden_issues": [
            "完全脱离偶像/公众事件",
            "图像缺少赛博或舞台感",
            "严重乱码或调试文本",
        ],
    },
    {
        "theme_id": 3,
        "expected_genre": "古风叙事",
        "expected_tone": "含蓄、韵味、讲述感",
        "must_have_constraints": [
            "必须体现茶肆/说书/古风场景",
            "场景图需符合水墨基调",
            "首段应有一个能继续讲下去的悬念",
        ],
        "forbidden_issues": [
            "现代都市词汇突兀混入",
            "水墨风格缺失",
            "选项不贴合古风语境",
        ],
    },
    {
        "theme_id": 8,
        "expected_genre": "古刹悬秘",
        "expected_tone": "清冷、神秘、静谧",
        "must_have_constraints": [
            "必须围绕古刹、钟楼或秘藏",
            "首段应营造探索氛围",
            "图像需与水墨古刹场景一致",
        ],
        "forbidden_issues": [
            "科幻赛博元素混入",
            "图像过于鲜艳",
            "剧情没有探索驱动",
        ],
    },
    {
        "theme_id": 21,
        "expected_genre": "书院悬疑",
        "expected_tone": "克制、推理、古典",
        "must_have_constraints": [
            "应体现书院、禁书或学术冲突",
            "选项需要与调查或应对相关",
            "整体语言要适配古典语境",
        ],
        "forbidden_issues": [
            "出现现代网络热词",
            "人物动机空洞",
            "图像风格脱离水墨",
        ],
    },
    {
        "theme_id": 4,
        "expected_genre": "海洋悬疑",
        "expected_tone": "潮湿、空旷、不安",
        "must_have_constraints": [
            "必须体现深海、信标或失联事件",
            "水彩视觉需体现海洋氛围",
            "首段剧情应有搜寻或确认线索的任务",
        ],
        "forbidden_issues": [
            "场景转成陆地校园",
            "图像毫无海洋元素",
            "选项无法推进搜索",
        ],
    },
    {
        "theme_id": 11,
        "expected_genre": "极地悬疑",
        "expected_tone": "寒冷、孤绝、压迫",
        "must_have_constraints": [
            "首段需要体现北极科考站环境压力",
            "冲突应与怪声或未知风险相关",
            "图像需匹配水彩寒地风格",
        ],
        "forbidden_issues": [
            "轻松搞笑口吻",
            "无关热带环境",
            "剧情没有悬念",
        ],
    },
    {
        "theme_id": 23,
        "expected_genre": "部落预言冒险",
        "expected_tone": "神秘、自然、仪式感",
        "must_have_constraints": [
            "应体现雨林部落与预言元素",
            "视觉需强调水彩自然环境",
            "至少一个选项要涉及信或不信预言",
        ],
        "forbidden_issues": [
            "赛博或工业场景混入",
            "图像不具雨林特征",
            "剧情缺乏仪式氛围",
        ],
    },
    {
        "theme_id": 5,
        "expected_genre": "校园奇幻",
        "expected_tone": "轻快中带压力、青春感",
        "must_have_constraints": [
            "故事必须围绕魔法学院与期末周展开",
            "动漫风格必须明确",
            "选项应贴合考试/冒险压力",
        ],
        "forbidden_issues": [
            "完全变成现实考试故事",
            "图像风格不动漫",
            "剧情没有魔法元素",
        ],
    },
    {
        "theme_id": 10,
        "expected_genre": "像素奇幻冒险",
        "expected_tone": "探索、机关感、异世界",
        "must_have_constraints": [
            "必须围绕神殿与考古展开",
            "动漫/像素趣味应在文本或视觉中有体现",
            "首段应建立探索目标",
        ],
        "forbidden_issues": [
            "完全没有神殿或遗迹",
            "图像/文本缺乏冒险感",
            "选项无实际行动性",
        ],
    },
    {
        "theme_id": 24,
        "expected_genre": "近轨道职业冒险",
        "expected_tone": "轻技术、职业化、动漫感",
        "must_have_constraints": [
            "必须体现近地轨道维修工作",
            "首段应建立故障或紧急任务",
            "图像应符合动漫风格",
        ],
        "forbidden_issues": [
            "毫无太空/轨道元素",
            "画风过于写实或油画化",
            "剧情没有维修任务",
        ],
    },
    {
        "theme_id": 6,
        "expected_genre": "近代悬疑",
        "expected_tone": "旧时代、微压抑、调查感",
        "must_have_constraints": [
            "需体现民国、电报或迷案",
            "图像应符合油画/印象派质感",
            "首段需要建立案件切入口",
        ],
        "forbidden_issues": [
            "现代赛博文本混入",
            "图像风格偏动漫",
            "剧情没有案件线索",
        ],
    },
    {
        "theme_id": 12,
        "expected_genre": "维多利亚时代幻想工艺",
        "expected_tone": "精致、压抑、古典",
        "must_have_constraints": [
            "必须体现钟表匠、机械或时代背景",
            "图像应符合 rococo 油画风格",
            "剧情应有工艺或秘密相关冲突",
        ],
        "forbidden_issues": [
            "赛博未来元素突兀混入",
            "图像风格不古典",
            "语言完全现代口语化",
        ],
    },
    {
        "theme_id": 18,
        "expected_genre": "商旅史诗",
        "expected_tone": "辽阔、风沙感、命运感",
        "must_have_constraints": [
            "必须出现沙漠商队或星图线索",
            "图像需符合经典油画风格",
            "首段剧情需要建立远行目标或风险",
        ],
        "forbidden_issues": [
            "完全没有商旅或地图元素",
            "图像缺乏沙漠氛围",
            "选项过于抽象",
        ],
    },
]


def main() -> int:
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
    themes = json.loads(THEMES_FILE.read_text(encoding="utf-8"))["items"]
    by_id = {item["id"]: item for item in themes}

    benchmark_items = []
    for idx, spec in enumerate(SELECTED_ITEMS, start=1):
        theme = by_id[spec["theme_id"]]
        benchmark_items.append(
            {
                "benchmark_id": f"DNQBV1_{idx:03d}",
                "theme_id": theme["id"],
                "theme": theme["theme"],
                "image_style": theme["image_style"],
                "expected_genre": spec["expected_genre"],
                "expected_tone": spec["expected_tone"],
                "must_have_constraints": spec["must_have_constraints"],
                "forbidden_issues": spec["forbidden_issues"],
            }
        )

    benchmark_payload = {
        "benchmark_name": "DN-quality-benchmark-v1",
        "version": 1,
        "description": "DN 项目首版固定质量基准集。用于效率实验中的统一输入集与效果护栏评测。",
        "sample_size": len(benchmark_items),
        "design_notes": {
            "selection_strategy": "按主题与画风分层抽样，覆盖 realistic / cyberpunk / ink_painting / watercolor / anime / oil_painting",
            "recommended_use": [
                "所有配置对比必须优先使用该固定任务集",
                "优先统计世界观、首段剧情、首图、主角图的自动代理指标",
                "必要时从该集合中抽样进行人工评分",
            ],
        },
        "items": benchmark_items,
    }

    json_path = BENCHMARK_DIR / "dn_quality_benchmark_v1.json"
    json_path.write_text(json.dumps(benchmark_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    flat_rows = []
    for item in benchmark_items:
        flat_rows.append(
            {
                "benchmark_id": item["benchmark_id"],
                "theme_id": item["theme_id"],
                "theme": item["theme"],
                "image_style_type": item["image_style"]["type"],
                "image_style_subtype": item["image_style"].get("subtype", ""),
                "expected_genre": item["expected_genre"],
                "expected_tone": item["expected_tone"],
                "must_have_constraints": " | ".join(item["must_have_constraints"]),
                "forbidden_issues": " | ".join(item["forbidden_issues"]),
            }
        )

    csv_path = BENCHMARK_DIR / "dn_quality_benchmark_v1_flat.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(flat_rows[0].keys()))
        writer.writeheader()
        writer.writerows(flat_rows)

    template_rows = []
    for item in benchmark_items:
        template_rows.append(
            {
                "benchmark_id": item["benchmark_id"],
                "theme_id": item["theme_id"],
                "theme": item["theme"],
                "config_name": "",
                "run_id": "",
                "rater_id": "",
                "theme_alignment_1to5": "",
                "narrative_coherence_1to5": "",
                "option_actionability_1to5": "",
                "visual_consistency_1to5": "",
                "artifact_cleanliness_1to5": "",
                "playable_0or1": "",
                "image_usable_0or1": "",
                "major_error_0or1": "",
                "comment": "",
            }
        )

    template_csv_path = BENCHMARK_DIR / "dn_human_rating_template_v1.csv"
    with template_csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(template_rows[0].keys()))
        writer.writeheader()
        writer.writerows(template_rows)

    print(json_path)
    print(csv_path)
    print(template_csv_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
