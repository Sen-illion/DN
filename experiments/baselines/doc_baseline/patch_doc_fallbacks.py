from pathlib import Path

p = Path(r"C:\Users\User\Desktop\DN-main\external\doc-storygen-v2\scripts\plan\generate.py")
txt = p.read_text(encoding="utf-8")

entity_old = """    if not success:
        raise Exception('Failed to generate entities')
    logging.info(f'Generated entities: {plan.entity_list}')
"""

entity_new = """    if not success:
        logging.warning('Failed to generate initial entities; using DOC baseline fallback entities instead')
        plan.entity_list = EntityList()
        plan.entity_list.entities.append(Entity('主人公', '故事的核心行动者，负责推动冒险、调查和关键选择。'))
        plan.entity_list.entities.append(Entity('关键同伴', '与主人公同行或协作的重要角色，提供线索、冲突或帮助。'))
        plan.entity_list.entities.append(Entity('主要对手', '阻碍主人公目标的敌对人物、势力或危险存在。'))
        plan.entity_list.entities.append(Entity('神秘遗物', '与主题核心冲突相关的重要物品、秘密或力量来源。'))
        plan.entity_list.entities.append(Entity('故事地点', '承载主要事件、转折和冲突的核心场景。'))
    logging.info(f'Generated entities: {plan.entity_list}')
"""

if entity_old in txt:
    txt = txt.replace(entity_old, entity_new)

start_marker = "    if not success:\n        logging.warning('Failed to generate outline; using DOC baseline fallback outline instead')"
end_marker = "    logging.info(f'Generated plan: {plan}')"

start = txt.find(start_marker)
if start == -1:
    old_outline_raise = """    if not success:
        raise Exception('Failed to generate outline')
    
    logging.info(f'Generated plan: {plan}')
"""
    if old_outline_raise not in txt:
        raise SystemExit("outline patch target not found")
    outline_block = """    if not success:
        logging.warning('Failed to generate outline; using DOC baseline fallback outline instead')
        entity_names = [entity.name for entity in plan.entity_list]
        if len(entity_names) == 0:
            entity_names = ['主人公']
        plan.outline = OutlineNode('', None)
        fallback_events = [
            ('主人公进入主题中的核心地点，发现这里隐藏着异常传闻和未解冲突。', '故事核心地点的入口或聚集处。'),
            ('主人公与关键人物相遇，获得关于主要秘密、危险或目标的线索。', '人物交谈与线索浮现的场景。'),
            ('主人公开始追查核心秘密，并遭遇阻碍、误导或外部威胁。', '危险逐渐逼近的探索场景。'),
            ('冲突升级，主人公必须在有限信息下做出影响后续命运的选择。', '紧张对峙或关键抉择场景。'),
            ('主人公面对主要对手或核心真相，完成最终行动并收束故事。', '最终揭示与结局场景。'),
        ]
        for event_text, scene_text in fallback_events:
            child = OutlineNode(event_text, plan.outline, scene_text, entity_names[:3])
            plan.outline.children.append(child)
    
    logging.info(f'Generated plan: {plan}')
"""
    txt = txt.replace(old_outline_raise, outline_block)
else:
    end = txt.find(end_marker, start)
    if end == -1:
        raise SystemExit("outline end marker not found")
    outline_block = """    if not success:
        logging.warning('Failed to generate outline; using DOC baseline fallback outline instead')
        entity_names = [entity.name for entity in plan.entity_list]
        if len(entity_names) == 0:
            entity_names = ['主人公']
        plan.outline = OutlineNode('', None)
        fallback_events = [
            ('主人公进入主题中的核心地点，发现这里隐藏着异常传闻和未解冲突。', '故事核心地点的入口或聚集处。'),
            ('主人公与关键人物相遇，获得关于主要秘密、危险或目标的线索。', '人物交谈与线索浮现的场景。'),
            ('主人公开始追查核心秘密，并遭遇阻碍、误导或外部威胁。', '危险逐渐逼近的探索场景。'),
            ('冲突升级，主人公必须在有限信息下做出影响后续命运的选择。', '紧张对峙或关键抉择场景。'),
            ('主人公面对主要对手或核心真相，完成最终行动并收束故事。', '最终揭示与结局场景。'),
        ]
        for event_text, scene_text in fallback_events:
            child = OutlineNode(event_text, plan.outline, scene_text, entity_names[:3])
            plan.outline.children.append(child)
    
"""
    txt = txt[:start] + outline_block + txt[end:]

p.write_text(txt, encoding="utf-8")
print(f"patched: {p}")
