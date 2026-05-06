from pathlib import Path

p = Path(r"C:\Users\User\Desktop\DN-main\external\doc-storygen-v2\storygen\story\story_writer.py")
txt = p.read_text(encoding="utf-8")

helper = '''
def fallback_story_for_node(story, node, is_ending=False):
    scene = node.scene or '当前故事场景'
    title = story.plan.premise.title
    if is_ending:
        text = f"\\n\\n最终，围绕{title}的冲突在{scene}中迎来收束。主人公回望一路上发现的线索、遭遇的阻碍与作出的选择，理解了事件背后真正的代价。危险逐渐平息，关键人物各自承担后果，故事在一个清晰而完整的结局中结束。"
    else:
        text = f"\\n\\n在{scene}中，{node.text} 主人公沿着已知线索继续行动，观察周围环境的变化，并与相关人物产生新的互动。随着事件推进，隐藏的矛盾逐渐浮现，当前目标、潜在威胁和下一步选择变得更加明确。"
    passage_list = OutlineNodePassageList(node)
    return story.copy_append_list(passage_list).copy_append_passage(Passage(text, {'score': 0, 'length_score': 0}))

'''

if "def fallback_story_for_node(" not in txt:
    marker = "\n\ndef generate_story("
    if marker not in txt:
        raise SystemExit("generate_story marker not found")
    txt = txt.replace(marker, "\n" + helper + "\ndef generate_story(", 1)

old = """        next_story_candidates = []
        for story in beam:
            next_story_candidates += render_node(story, node_to_render, story_config, story_prompts, llm_client).stories
        beam = filter_beam(StoryBeam(next_story_candidates), beam_width=story_config['outline_node_beam_width'], aux_attr='score')

        logging.debug(f"Best story: {str(beam.stories[0])}")
"""

new = """        next_story_candidates = []
        for story in beam:
            try:
                rendered = render_node(story, node_to_render, story_config, story_prompts, llm_client).stories
            except Exception as exc:
                logging.warning(f"Failed to render node with DOC; using fallback passage for node: {node_to_render.text}. Error: {exc}")
                rendered = []
            if len(rendered) == 0:
                logging.warning(f"DOC produced no valid passage candidates; using fallback passage for node: {node_to_render.text}")
                rendered = [fallback_story_for_node(story, node_to_render)]
            next_story_candidates += rendered
        beam = filter_beam(StoryBeam(next_story_candidates), beam_width=story_config['outline_node_beam_width'], aux_attr='score')

        if len(beam.stories) == 0:
            logging.warning("Story beam is empty after fallback handling; stopping story generation early")
            break
        logging.debug(f"Best story: {str(beam.stories[0])}")
"""

if old in txt:
    txt = txt.replace(old, new, 1)

old_end = """        next_story_candidates = []
        for story in beam:
            next_story_candidates += render_node(story, end_node, story_config, story_prompts, llm_client, is_ending=True).stories
        beam = filter_beam(StoryBeam(next_story_candidates), story_config['outline_node_beam_width'], aux_attr='score')
"""

new_end = """        next_story_candidates = []
        for story in beam:
            try:
                rendered = render_node(story, end_node, story_config, story_prompts, llm_client, is_ending=True).stories
            except Exception as exc:
                logging.warning(f"Failed to render ending with DOC; using fallback ending. Error: {exc}")
                rendered = []
            if len(rendered) == 0:
                logging.warning("DOC produced no valid ending candidates; using fallback ending")
                rendered = [fallback_story_for_node(story, end_node, is_ending=True)]
            next_story_candidates += rendered
        beam = filter_beam(StoryBeam(next_story_candidates), story_config['outline_node_beam_width'], aux_attr='score')
"""

if old_end in txt:
    txt = txt.replace(old_end, new_end, 1)

p.write_text(txt, encoding="utf-8")
print(f"patched: {p}")
