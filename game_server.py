# -*- coding: utf-8 -*-
import os
import sys
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_file, send_from_directory

# 设置环境变量以使用 UTF-8 编码（解决 Windows GBK 编码问题）
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

from main2 import (
    llm_generate_global, 
    _generate_single_option, 
    generate_all_options, 
    modify_ending_content, 
    generate_ending_prediction,
    generate_scene_image,
    # ==================== 视频生成功能已禁用（性能优化） ====================
    # generate_scene_video,
    # get_video_task_status
    get_video_task_status  # 保留占位函数，避免导入错误
)

# 初始化Flask应用
app = Flask(__name__)

# 加载环境变量
load_dotenv()

# 存档目录配置
SAVE_DIR = "saves"

# 确保存档目录存在
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

# 图片和视频缓存目录配置
IMAGE_CACHE_DIR = "image_cache"
VIDEO_CACHE_DIR = "video_cache"

# 确保缓存目录存在
if not os.path.exists(IMAGE_CACHE_DIR):
    os.makedirs(IMAGE_CACHE_DIR)
if not os.path.exists(VIDEO_CACHE_DIR):
    os.makedirs(VIDEO_CACHE_DIR)

# 全局缓存：存储预生成的两层内容
# 结构：{scene_id: {
#   'layer1': {option_index: option_data},
#   'layer2': {option_index: {option_index: option_data}},
#   'generation_status': {option_index: 'pending'|'generating'|'completed'},
#   'generation_events': {option_index: threading.Event()},
#   'should_cancel': False,
#   'current_generating_index': None,
#   'layer2_generating': False,  # 第二层是否正在生成
#   'layer2_cancel': False,  # 第二层生成取消标志
#   'layer2_selected_option': None,  # 用户选择的选项索引（用于第二层生成控制）
#   'layer2_thread': None  # 第二层生成线程对象
# }}
pregeneration_cache = {}
cache_lock = threading.Lock()  # 线程锁，保证缓存操作的线程安全
MAX_CACHE_SIZE = 3  # 最大缓存场景数量，超过此数量将清理最旧的缓存（降低内存占用）

# 辅助函数：清理错误消息中的特殊字符（避免编码问题）
def clean_error_message(error_msg):
    """清理错误消息，移除可能导致编码问题的字符"""
    try:
        # 先尝试编码为 UTF-8
        msg = str(error_msg)
        # 移除 emoji 和特殊 Unicode 字符（保留基本 ASCII 和中文字符）
        import re
        # 保留 ASCII、中文字符、常见标点符号
        msg = re.sub(r'[^\x00-\x7F\u4e00-\u9fff\s\.,;:!?()\[\]{}\-+=]', '', msg)
        return msg
    except:
        # 如果清理失败，返回安全的默认消息
        return "发生错误，请稍后重试"

# 生成场景ID的辅助函数
def generate_scene_id(global_state_hash, current_options_hash):
    """根据全局状态和当前选项生成唯一的场景ID"""
    return f"{hash(str(global_state_hash))}_{hash(str(current_options_hash))}"

# 缓存清理函数：清理旧的、无用的缓存
def cleanup_old_cache(current_scene_id=None):
    """清理旧的缓存，保留最近使用的场景"""
    with cache_lock:
        cache_size = len(pregeneration_cache)
        if cache_size <= MAX_CACHE_SIZE:
            return
        
        # 如果提供了当前场景ID，确保它不被清理
        scenes_to_keep = set()
        if current_scene_id:
            scenes_to_keep.add(current_scene_id)
        if 'initial' in pregeneration_cache:
            scenes_to_keep.add('initial')
        
        # 计算需要清理的数量
        to_remove = cache_size - MAX_CACHE_SIZE
        
        # 找出最旧的缓存（除了要保留的）
        scenes_to_remove = []
        for scene_id in pregeneration_cache:
            if scene_id not in scenes_to_keep:
                scenes_to_remove.append(scene_id)
        
        # 如果场景太多，清理最旧的（这里简化处理，清理除了当前和initial之外的所有）
        if len(scenes_to_remove) > to_remove:
            # 只清理超出限制的部分
            scenes_to_remove = scenes_to_remove[:to_remove]
        
        # 清理选中的场景
        for scene_id in scenes_to_remove:
            cache_entry = pregeneration_cache.get(scene_id)
            if cache_entry:
                # 停止正在进行的生成
                if cache_entry.get('layer2_generating', False):
                    cache_entry['layer2_cancel'] = True
                    layer2_thread = cache_entry.get('layer2_thread')
                    if layer2_thread and layer2_thread.is_alive():
                        layer2_thread.join(timeout=0.5)
            
            del pregeneration_cache[scene_id]
            print(f"🗑️ 已清理旧缓存场景 {scene_id}（内存优化）")
        
        print(f"📊 当前缓存大小：{len(pregeneration_cache)}/{MAX_CACHE_SIZE}")

# 清理已使用选项的缓存数据
def cleanup_used_options(scene_id, used_option_index):
    """清理已使用的选项数据，释放内存"""
    with cache_lock:
        if scene_id not in pregeneration_cache:
            return
        
        cache_entry = pregeneration_cache[scene_id]
        
        # 清理第一层已使用的选项（保留当前使用的，但清理其他未使用的）
        if 'layer1' in cache_entry:
            layer1 = cache_entry['layer1']
            # 只保留当前使用的选项，清理其他未使用的选项
            if used_option_index in layer1:
                # 保留当前使用的选项数据，但可以清理其第二层数据
                if 'layer2' in cache_entry and used_option_index in cache_entry['layer2']:
                    # 清理第二层中未使用的选项
                    layer2_data = cache_entry['layer2'][used_option_index]
                    # 这里可以进一步优化，但为了安全，暂时保留
                    pass

# 允许前端跨域访问
@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# 核心接口：生成游戏世界观
@app.route('/generate-worldview', methods=['POST'])
def generate_worldview():
    try:
        # 获取前端传的参数
        data = request.json
        game_theme = data.get('gameTheme', '').strip()
        protagonist_attr = data.get('protagonistAttr', {})
        difficulty = data.get('difficulty', '中等')
        tone_key = data.get('toneKey', 'normal_ending')
        image_style = data.get('imageStyle', None)  # 图片风格选择
        
        # 基础校验
        if not game_theme:
            return jsonify({"status": "error", "message": "游戏主题不能为空！"})
        
        # 调用后端生成世界观的函数
        try:
            global_state = llm_generate_global(game_theme, protagonist_attr, difficulty, tone_key)
            
            # 保存图片风格到global_state
            if image_style:
                global_state['image_style'] = image_style
                print(f"✅ 图片风格已保存到global_state: {image_style}")
        except ValueError as e:
            # 如果是API配置错误，返回明确的错误信息
            error_msg = str(e)
            if "缺少必要的API配置" in error_msg or "API" in error_msg:
                return jsonify({
                    "status": "error",
                    "message": f"AI生成功能未配置：{error_msg}\n\n请检查.env文件，确保配置了以下环境变量：\n- Camera_Analyst_API_KEY\n- Camera_Analyst_BASE_URL\n- Camera_Analyst_MODEL"
                })
            raise  # 其他ValueError继续抛出
        
        # 世界观生成成功后，立即启动第一次选项的生成（后台线程，不使用预生成机制）
        def generate_initial_options():
            """生成第一次选项（根据世界观动态生成）"""
            try:
                print(f"🔄 开始生成第一次选项（根据世界观动态生成）...")
                
                # 根据世界观生成初始场景和选项
                # 使用"开始游戏"作为初始选项，生成第一个场景和后续选项
                initial_option = "开始游戏"
                result = _generate_single_option(0, initial_option, global_state)
                
                if isinstance(result, dict):
                    initial_option_data = result.get('data', result)
                else:
                    initial_option_data = result
                
                # 获取生成的初始选项列表
                initial_options = initial_option_data.get('next_options', [])
                
                if not initial_options:
                    # 如果生成失败，使用默认选项
                    initial_options = ["继续深入探索", "查看周围环境"]
                
                # 限制选项数量为2个
                if len(initial_options) > 2:
                    initial_options = initial_options[:2]
                
                # 为这2个初始选项生成对应的剧情（并行生成）
                print(f"📝 为 {len(initial_options)} 个初始选项生成剧情...")
                all_initial_options_data = generate_all_options(global_state, initial_options)
                
                # 存储到特殊缓存位置（不使用预生成机制）
                with cache_lock:
                    if 'initial' not in pregeneration_cache:
                        pregeneration_cache['initial'] = {
                            'generation_events': {}
                        }
                    
                    initial_cache = pregeneration_cache['initial']
                    initial_cache['layer1'] = all_initial_options_data
                    # 确保initial_scene不为空，如果为空则使用默认场景
                    initial_scene = initial_option_data.get('scene', '')
                    if not initial_scene or initial_scene.strip() == '':
                        print(f"⚠️ 初始场景为空，使用默认场景")
                        initial_scene = "你开始了你的冒险之旅."
                    # 修复：提取并保存初始场景的图片数据
                    initial_scene_image = initial_option_data.get('scene_image', None)
                    if initial_scene_image:
                        print(f"✅ 初始场景图片数据已提取: {initial_scene_image.get('url', 'N/A')[:80]}...")
                    else:
                        print(f"⚠️ 初始场景没有图片数据")
                    initial_cache['initial_scene'] = initial_scene
                    initial_cache['initial_scene_image'] = initial_scene_image  # 保存图片数据
                    initial_cache['initial_options'] = initial_options
                    initial_cache['generation_status'] = {i: 'completed' for i in range(len(initial_options))}
                    initial_cache['completed'] = True
                    
                    # 触发等待事件（如果有线程在等待）
                    events = initial_cache.get('generation_events', {})
                    if 'main' in events:
                        events['main'].set()
                
                print(f"✅ 第一次选项生成完成，共生成 {len(all_initial_options_data)} 个选项的剧情")
                
            except Exception as e:
                print(f"❌ 生成第一次选项失败：{str(e)}")
                import traceback
                traceback.print_exc()
                # 即使失败，也设置一个标记，避免前端无限等待
                with cache_lock:
                    if 'initial' not in pregeneration_cache:
                        pregeneration_cache['initial'] = {
                            'generation_events': {}
                        }
                    initial_cache = pregeneration_cache['initial']
                    initial_cache['completed'] = False
                    initial_cache['error'] = str(e)
                    
                    # 触发等待事件（避免前端无限等待）
                    events = initial_cache.get('generation_events', {})
                    if 'main' in events:
                        events['main'].set()
        
        # 启动后台线程生成第一次选项（不阻塞响应）
        thread = threading.Thread(target=generate_initial_options, daemon=True)
        thread.start()
        
        # 验证返回的数据结构
        if not global_state:
            return jsonify({
                "status": "error",
                "message": "世界观生成失败：返回的数据为空"
            })
        
        # 验证核心字段
        if not global_state.get('core_worldview'):
            return jsonify({
                "status": "error",
                "message": "世界观生成失败：缺少核心世界观数据"
            })
        
        print(f"✅ 世界观生成成功，返回数据包含：")
        print(f"   - core_worldview: {bool(global_state.get('core_worldview'))}")
        print(f"   - chapters: {bool(global_state.get('core_worldview', {}).get('chapters'))}")
        print(f"   - chapter1: {bool(global_state.get('core_worldview', {}).get('chapters', {}).get('chapter1'))}")
        
        # 返回结果
        return jsonify({
            "status": "success",
            "message": "世界观生成成功！",
            "globalState": global_state
        })
    except Exception as e:
        error_msg = clean_error_message(str(e))
        return jsonify({"status": "error", "message": f"世界观生成失败：{error_msg}"})

# 核心接口：生成单个选项对应的剧情（支持智能等待，不降级为实时生成）
@app.route('/generate-option', methods=['POST'])
def generate_option():
    try:
        # 获取前端传的参数
        data = request.json
        option = data.get('option', '').strip()
        global_state = data.get('globalState', {})
        option_index = data.get('optionIndex', 0)
        scene_id = data.get('sceneId', None)  # 前端传入的场景ID，用于缓存查找
        current_options = data.get('currentOptions', [])  # 当前选项列表，用于触发优先生成
        
        # 基础校验
        if not option:
            return jsonify({"status": "error", "message": "选项内容不能为空！"})
        if not global_state:
            return jsonify({"status": "error", "message": "全局状态不能为空！"})
        
        option_data = None
        need_wait = False
        wait_event = None  # 初始化wait_event
        layer2_thread_to_wait = None  # 用于在释放锁后等待第二层线程
        
        # 处理第一次生成的情况（sceneId为null或'initial'）
        if not scene_id or scene_id == 'initial':
            # 第一次生成：从initial缓存读取
            with cache_lock:
                # 如果initial缓存不存在，创建并等待
                if 'initial' not in pregeneration_cache:
                    pregeneration_cache['initial'] = {
                        'generation_events': {},
                        'completed': False
                    }
                    need_wait = True
                else:
                    initial_cache = pregeneration_cache['initial']
                    
                    # 检查是否生成完成
                    if initial_cache.get('completed', False):
                        # 如果用户选择的是"开始游戏"（option_index=0），返回初始场景
                        if option_index == 0 and option == "开始游戏":
                            # 返回初始场景和选项
                            initial_scene = initial_cache.get('initial_scene', '')
                            initial_scene_image = initial_cache.get('initial_scene_image', None)  # 修复：读取图片数据
                            initial_options = initial_cache.get('initial_options', [])
                            
                            # 确保initial_scene不为空
                            if not initial_scene or initial_scene.strip() == '':
                                print(f"⚠️ 从缓存读取的初始场景为空，使用默认场景")
                                initial_scene = "你开始了你的冒险之旅."
                            
                            option_data = {
                                "scene": initial_scene,
                                "scene_image": initial_scene_image,  # 修复：包含图片数据
                                "next_options": initial_options,
                                "flow_update": {},
                                "deep_background_links": {}
                            }
                            if initial_scene_image:
                                print(f"✅ 从initial缓存中读取初始场景和选项，场景长度: {len(initial_scene)}，包含图片数据")
                            else:
                                print(f"✅ 从initial缓存中读取初始场景和选项，场景长度: {len(initial_scene)}，无图片数据")
                            
                            # 第一次生成完成后，触发预生成（为第一次的4个选项预生成下一层）
                            # 检查是否已经触发过预生成（避免重复触发）
                            if not initial_cache.get('pregeneration_triggered', False):
                                initial_cache['pregeneration_triggered'] = True
                                
                                # 使用后台线程异步调用预生成逻辑，不阻塞响应
                                def trigger_initial_pregeneration():
                                    try:
                                        # 直接调用预生成核心逻辑函数
                                        print(f"🔄 开始为第一次选项预生成下一层内容...")
                                        _pregenerate_next_layers_logic(global_state, initial_options, 'initial_first_layer')
                                        print(f"✅ 第一次选项预生成任务已启动")
                                    except Exception as e:
                                        print(f"⚠️ 触发第一次选项预生成时发生错误：{str(e)}")
                                        import traceback
                                        traceback.print_exc()
                                
                                # 启动后台线程触发预生成
                                pregen_thread = threading.Thread(target=trigger_initial_pregeneration, daemon=True)
                                pregen_thread.start()
                        else:
                            # 从layer1中读取对应选项的数据
                            layer1_data = initial_cache.get('layer1', {})
                            if option_index in layer1_data:
                                option_data = layer1_data[option_index]
                                print(f"✅ 从initial缓存中读取选项 {option_index} 的剧情")
                            else:
                                # 如果找不到，等待生成完成
                                need_wait = True
                    else:
                        # 还未生成完成，等待
                        need_wait = True
                
                # 如果需要等待，创建等待事件
                if need_wait:
                    initial_cache = pregeneration_cache['initial']
                    events = initial_cache.setdefault('generation_events', {})
                    if 'main' not in events:
                        events['main'] = threading.Event()
                    wait_event = events['main']
        
        if scene_id and scene_id != 'initial':
            with cache_lock:
                if scene_id in pregeneration_cache:
                    cache_entry = pregeneration_cache[scene_id]
                    
                    # 情况1：缓存中已有该选项的数据
                    if 'layer1' in cache_entry and option_index in cache_entry['layer1']:
                        option_data = cache_entry['layer1'][option_index]
                        print(f"✅ 从缓存中读取场景 {scene_id} 的选项 {option_index} 的剧情")
                        
                        # 用户选择了选项，需要控制第二层生成
                        # 检查第二层是否已经开始生成
                        layer2_generating = cache_entry.get('layer2_generating', False)
                        
                        if layer2_generating:
                            # 情况1a：第二层已经开始生成
                            # 检查当前正在生成的是哪个选项的第二层
                            current_layer2_option = cache_entry.get('current_layer2_option', None)
                            
                            if current_layer2_option == option_index:
                                # 正在生成的是用户选择的选项的第二层，继续生成
                                print(f"✅ 正在生成选项 {option_index} 的第二层，继续生成")
                            else:
                                # 正在生成的不是用户选择的选项的第二层，停止生成
                                print(f"⏹️ 停止生成选项 {current_layer2_option} 的第二层（用户选择了选项 {option_index}）")
                                cache_entry['layer2_cancel'] = True
                                # 保存线程引用，在释放锁后等待（避免死锁）
                                layer2_thread_to_wait = cache_entry.get('layer2_thread')
                        else:
                            # 情况1b：第二层还未开始生成
                            # 设置标志，只生成用户选择的选项的第二层
                            print(f"📝 第二层还未开始生成，将只为选项 {option_index} 生成第二层")
                            cache_entry['layer2_selected_option'] = option_index
                            cache_entry['layer2_cancel'] = False
                    
                    # 情况2：缓存中没有该选项的数据，检查生成状态
                    elif 'generation_status' in cache_entry:
                        generation_status = cache_entry.get('generation_status', {})
                        status = generation_status.get(option_index, 'pending')
                        
                        if status == 'generating':
                            # 情况2a：正在生成中，等待生成完成
                            print(f"⏳ 选项 {option_index} 正在生成中，等待完成...")
                            need_wait = True
                            # 获取对应的事件对象
                            events = cache_entry.setdefault('generation_events', {})
                            if option_index not in events:
                                events[option_index] = threading.Event()
                            wait_event = events[option_index]
                        
                        elif status == 'pending':
                            # 情况2b：还未开始生成，优先生成该选项
                            print(f"🚀 选项 {option_index} 还未生成，优先生成...")
                            # 标记需要取消其他未开始的生成
                            cache_entry['should_cancel'] = True
                            # 如果用户选择的选项还未生成，标记为高优先级
                            generation_status[option_index] = 'generating'
                            # 创建事件对象
                            events = cache_entry.setdefault('generation_events', {})
                            if option_index not in events:
                                events[option_index] = threading.Event()
                            wait_event = events[option_index]
                            
                            # 启动单个选项的生成任务（优先生成）
                            def generate_selected_option():
                                try:
                                    result = _generate_single_option(option_index, option, global_state)
                                    if isinstance(result, dict):
                                        opt_data = result.get('data', result)
                                    else:
                                        opt_data = result
                                    
                                    with cache_lock:
                                        if scene_id in pregeneration_cache:
                                            cache_entry = pregeneration_cache[scene_id]
                                            if 'layer1' not in cache_entry:
                                                cache_entry['layer1'] = {}
                                            cache_entry['layer1'][option_index] = opt_data
                                            generation_status = cache_entry.setdefault('generation_status', {})
                                            generation_status[option_index] = 'completed'
                                            
                                            # 触发等待事件
                                            events = cache_entry.get('generation_events', {})
                                            if option_index in events:
                                                events[option_index].set()
                                            print(f"✅ 选项 {option_index} 优先生成完成")
                                except Exception as e:
                                    print(f"❌ 优先生成选项 {option_index} 失败：{str(e)}")
                                    with cache_lock:
                                        if scene_id in pregeneration_cache:
                                            events = pregeneration_cache[scene_id].get('generation_events', {})
                                            if option_index in events:
                                                events[option_index].set()
                            
                            thread = threading.Thread(target=generate_selected_option, daemon=True)
                            thread.start()
                            need_wait = True
                    else:
                        # 情况3：scene_id不在缓存中，可能是第一次选择（前端传入了新生成的sceneId）
                        # 尝试从initial缓存中查找（第一次的选项数据在initial缓存中）
                        print(f"⚠️ 场景 {scene_id} 不在缓存中，尝试从initial缓存查找...")
                        if 'initial' in pregeneration_cache:
                            initial_cache = pregeneration_cache['initial']
                            if initial_cache.get('completed', False):
                                layer1_data = initial_cache.get('layer1', {})
                                if option_index in layer1_data:
                                    option_data = layer1_data[option_index]
                                    print(f"✅ 从initial缓存中读取选项 {option_index} 的剧情（第一次选择）")
                                else:
                                    print(f"⚠️ initial缓存中也没有选项 {option_index} 的数据")
                            else:
                                print(f"⚠️ initial缓存还未完成生成")
        
        # 在释放锁后等待第二层线程退出（避免死锁）
        if layer2_thread_to_wait and layer2_thread_to_wait.is_alive():
            # 等待线程退出（最多等待2秒）
            layer2_thread_to_wait.join(timeout=2.0)
        
        # 如果需要等待，则等待生成完成
        if need_wait and wait_event:
            try:
                # 等待最多6分钟（360秒），以匹配图片生成的超时时间
                wait_event.wait(timeout=360)
                
                # 再次尝试从缓存读取
                with cache_lock:
                    # 处理第一次生成的情况
                    if not scene_id or scene_id == 'initial':
                        if 'initial' in pregeneration_cache:
                            initial_cache = pregeneration_cache['initial']
                            if initial_cache.get('completed', False):
                                if option_index == 0 and option == "开始游戏":
                                    initial_scene = initial_cache.get('initial_scene', '')
                                    initial_scene_image = initial_cache.get('initial_scene_image', None)  # 修复：读取图片数据
                                    initial_options = initial_cache.get('initial_options', [])
                                    option_data = {
                                        "scene": initial_scene,
                                        "scene_image": initial_scene_image,  # 修复：包含图片数据
                                        "next_options": initial_options,
                                        "flow_update": {},
                                        "deep_background_links": {}
                                    }
                                    if initial_scene_image:
                                        print(f"✅ 等待完成，从initial缓存中读取初始场景和选项，包含图片数据")
                                    else:
                                        print(f"✅ 等待完成，从initial缓存中读取初始场景和选项，无图片数据")
                                else:
                                    layer1_data = initial_cache.get('layer1', {})
                                    if option_index in layer1_data:
                                        option_data = layer1_data[option_index]
                                        print(f"✅ 等待完成，从initial缓存中读取选项 {option_index} 的剧情")
                    else:
                        # 处理后续生成的情况
                        if scene_id in pregeneration_cache:
                            cache_entry = pregeneration_cache[scene_id]
                            if 'layer1' in cache_entry and option_index in cache_entry['layer1']:
                                option_data = cache_entry['layer1'][option_index]
                                print(f"✅ 等待完成，从缓存中读取选项 {option_index} 的剧情")
                
                # 如果等待后仍然没有，返回错误
                if not option_data:
                    return jsonify({
                        "status": "error",
                        "message": "生成超时，请稍后重试"
                    })
            except Exception as e:
                print(f"❌ 等待生成时发生错误：{str(e)}")
                return jsonify({
                    "status": "error",
                    "message": f"等待生成失败：{str(e)}"
                })
        
        # 如果仍然没有数据（不应该发生，但做容错处理）
        if not option_data:
            print(f"⚠️ 所有方法都失败，使用默认数据")
            option_data = {
                "scene": f"你选择了：{option}。在你的努力下，你取得了一些进展。",
                "next_options": ["继续前进", "查看当前状态", "返回上一步", "探索周围环境"],
                "flow_update": {
                    "characters": {},
                    "environment": {},
                    "quest_progress": f"你正在执行任务：{option}",
                    "chapter_conflict_solved": False
                },
                "deep_background_links": {}
            }
        
        # 返回结果前，清理上一轮的缓存（如果提供了上一轮的scene_id）
        previous_scene_id = data.get('previousSceneId', None)
        if previous_scene_id and previous_scene_id != scene_id and previous_scene_id != 'initial':
            with cache_lock:
                if previous_scene_id in pregeneration_cache:
                    # 停止该场景的第二层生成（如果正在生成）
                    prev_cache_entry = pregeneration_cache[previous_scene_id]
                    if prev_cache_entry.get('layer2_generating', False):
                        prev_cache_entry['layer2_cancel'] = True
                        layer2_thread = prev_cache_entry.get('layer2_thread')
                        if layer2_thread and layer2_thread.is_alive():
                            # 等待线程退出（最多等待1秒）
                            layer2_thread.join(timeout=1.0)
                    
                    # 删除上一轮的缓存
                    del pregeneration_cache[previous_scene_id]
                    print(f"🗑️ 已清理上一轮场景 {previous_scene_id} 的缓存")
        
        # 清理当前场景中未使用的选项数据（内存优化）
        if scene_id and scene_id != 'initial' and scene_id in pregeneration_cache:
            with cache_lock:
                cache_entry = pregeneration_cache[scene_id]
                # 清理第一层中未使用的选项（保留当前使用的）
                if 'layer1' in cache_entry:
                    layer1 = cache_entry['layer1']
                    unused_indices = [idx for idx in layer1.keys() if idx != option_index]
                    for idx in unused_indices:
                        del layer1[idx]
                        print(f"🗑️ 已清理未使用的选项 {idx} 的第一层数据")
                
                # 清理第二层中未使用的选项数据
                if 'layer2' in cache_entry:
                    layer2 = cache_entry['layer2']
                    # 只保留当前使用的选项的第二层数据
                    if option_index in layer2:
                        # 保留当前选项的第二层，但可以清理其他选项的第二层
                        current_layer2 = layer2[option_index]
                        # 清理其他选项的第二层
                        unused_layer2_indices = [idx for idx in layer2.keys() if idx != option_index]
                        for idx in unused_layer2_indices:
                            del layer2[idx]
                            print(f"🗑️ 已清理未使用的选项 {idx} 的第二层数据")
        
        # 定期清理旧缓存
        cleanup_old_cache(scene_id)
        
        # 返回结果
        return jsonify({
            "status": "success",
            "message": "选项剧情生成成功！",
            "optionData": option_data
        })
    except Exception as e:
        # 详细记录错误信息
        print(f"🔴 服务器错误：{str(e)}")
        import traceback
        traceback.print_exc()
        error_msg = clean_error_message(str(e))
        return jsonify({"status": "error", "message": f"选项剧情生成失败：{error_msg}"})

# 预生成两层内容的核心逻辑（提取为独立函数，可被其他函数调用）
def _pregenerate_next_layers_logic(global_state, current_options, scene_id):
    """
    预生成两层内容的核心逻辑（优先级策略 + 渐进式缓存）
    可以被接口函数或其他函数调用
    """
    # 如果没有提供scene_id，生成一个新的
    if not scene_id:
        scene_id = generate_scene_id(str(global_state), str(current_options))
    
    print(f"🔄 开始预生成场景 {scene_id} 的两层内容（优先级策略）...")
    
    # 在后台线程中异步执行预生成，不阻塞响应
    def async_pregenerate():
        try:
            # 初始化缓存条目（需要先加锁检查，避免重复初始化）
            with cache_lock:
                if scene_id not in pregeneration_cache:
                    pregeneration_cache[scene_id] = {
                        'layer1': {},
                        'layer2': {},
                        'generation_status': {},
                        'generation_events': {},
                        'should_cancel': False,
                        'current_generating_index': None,
                        'layer2_generating': False,
                        'layer2_cancel': False,
                        'layer2_selected_option': None,
                        'layer2_thread': None,
                        'current_layer2_option': None
                    }
                
                cache_entry = pregeneration_cache[scene_id]
                
                # 初始化所有选项的状态为 'pending'
                generation_status = cache_entry['generation_status']
                for i in range(len(current_options)):
                    if i not in generation_status:
                        generation_status[i] = 'pending'
                        # 创建事件对象
                        if 'generation_events' not in cache_entry:
                            cache_entry['generation_events'] = {}
                        if i not in cache_entry['generation_events']:
                            cache_entry['generation_events'][i] = threading.Event()
            
            # 第一层：并行生成所有选项（按优先级顺序提交任务），生成一个立即写入缓存
            print(f"📝 预生成第一层：并行生成 {len(current_options)} 个选项的下一轮剧情...")
            
            # 定义单个选项的生成任务函数
            def generate_single_option_task(opt_idx, option):
                """生成单个选项的任务函数"""
                # 在设置状态为 'generating' 之前就检查取消标志和状态
                with cache_lock:
                    if scene_id not in pregeneration_cache:
                        return
                    cache_entry = pregeneration_cache[scene_id]
                    generation_status = cache_entry.get('generation_status', {})
                    current_status = generation_status.get(opt_idx, 'pending')
                    
                    # 如果已经完成，不需要再生成
                    if current_status == 'completed':
                        return
                    
                    # 如果正在生成中，可能是用户选择的优先生成任务，避免重复生成
                    if current_status == 'generating':
                        # 检查缓存中是否已有数据（可能是优先生成任务已经完成）
                        if 'layer1' in cache_entry and opt_idx in cache_entry['layer1']:
                            return  # 已有数据，不需要重复生成
                        # 否则继续等待或生成（这里选择继续，因为可能是正常的并行生成）
                    
                    # 检查取消标志（只取消 'pending' 状态的选项）
                    if cache_entry.get('should_cancel', False):
                        if current_status == 'pending':
                            # 如果该选项还未开始生成，取消它
                            print(f"⏭️ 选项 {opt_idx} 被取消生成（用户选择了其他选项）")
                            return
                    
                    # 更新状态为 'generating'（只有在 pending 状态时才设置）
                    if current_status == 'pending':
                        generation_status[opt_idx] = 'generating'
                        cache_entry['current_generating_index'] = opt_idx
                
                print(f"📝 开始并行生成选项 {opt_idx + 1}/{len(current_options)}: {option[:30]}...")
                
                # 生成单个选项的剧情
                try:
                    result = _generate_single_option(opt_idx, option, global_state)
                    if isinstance(result, dict):
                        option_data = result.get('data', result)
                    else:
                        option_data = result
                    
                    # 立即写入缓存（渐进式缓存）
                    with cache_lock:
                        if scene_id in pregeneration_cache:
                            cache_entry = pregeneration_cache[scene_id]
                            if 'layer1' not in cache_entry:
                                cache_entry['layer1'] = {}
                            cache_entry['layer1'][opt_idx] = option_data
                            cache_entry['generation_status'][opt_idx] = 'completed'
                            
                            # 触发等待事件（如果有线程在等待）
                            events = cache_entry.get('generation_events', {})
                            if opt_idx in events:
                                events[opt_idx].set()
                            
                            print(f"✅ 选项 {opt_idx} 生成完成并已写入缓存")
                except Exception as e:
                    print(f"❌ 生成选项 {opt_idx} 失败：{str(e)}")
                    import traceback
                    traceback.print_exc()
                    with cache_lock:
                        if scene_id in pregeneration_cache:
                            cache_entry = pregeneration_cache[scene_id]
                            cache_entry['generation_status'][opt_idx] = 'pending'
                            events = cache_entry.get('generation_events', {})
                            if opt_idx in events:
                                events[opt_idx].set()
            
            # 使用线程池并行生成所有选项（按优先级顺序提交任务）
            with ThreadPoolExecutor(max_workers=len(current_options)) as executor:
                # 按优先级顺序（0→1→2→3）提交所有任务
                futures = []
                for opt_idx in range(len(current_options)):
                    option = current_options[opt_idx]
                    future = executor.submit(generate_single_option_task, opt_idx, option)
                    futures.append((opt_idx, future))
                
                # 等待所有任务完成（可选，但保留以便跟踪完成状态）
                for opt_idx, future in futures:
                    try:
                        future.result()  # 等待任务完成，如果有异常会抛出
                    except Exception as e:
                        print(f"❌ 选项 {opt_idx} 的任务执行异常：{str(e)}")
            
            # 清理当前生成索引
            with cache_lock:
                if scene_id in pregeneration_cache:
                    pregeneration_cache[scene_id]['current_generating_index'] = None
            
            print(f"✅ 第一层预生成完成，共生成 {len(pregeneration_cache.get(scene_id, {}).get('layer1', {}))} 个选项的剧情")
            print("---------------------------------------------- 第一层预生成完成 ----------------------------------------------")
            
            # 第二层：为第一层的每个选项的next_options预生成再下一层剧情（继续在后台异步生成）
            print(f"📝 预生成第二层：为下一轮选项生成再下一层剧情...")
            print("---------------------------------------------- 开始第二层预生成 ----------------------------------------------")
            
            def generate_layer2():
                try:
                    # 先获取需要的数据，然后释放锁
                    selected_option = None
                    layer1_data = {}
                    need_process_options = []
                    
                    with cache_lock:
                        if scene_id not in pregeneration_cache:
                            return
                        cache_entry = pregeneration_cache[scene_id]
                        layer1_data = cache_entry.get('layer1', {}).copy()  # 复制数据，避免长时间持有锁
                        selected_option = cache_entry.get('layer2_selected_option', None)
                    
                    # 检查是否有用户选择的选项（如果用户在选择时设置了）
                    # 如果用户已经选择了选项，只生成该选项的第二层
                    if selected_option is not None:
                        print(f"📝 只为用户选择的选项 {selected_option} 生成第二层")
                        if selected_option not in layer1_data:
                            print(f"⚠️ 用户选择的选项 {selected_option} 不在第一层数据中")
                            return
                        
                        # 只处理用户选择的选项
                        opt_idx = selected_option
                        layer1_option_data = layer1_data[opt_idx]
                        next_options = layer1_option_data.get('next_options', [])
                        
                        if next_options:
                            # 检查取消标志（在锁外快速检查）
                            with cache_lock:
                                if scene_id not in pregeneration_cache:
                                    return
                                cache_entry = pregeneration_cache[scene_id]
                                if cache_entry.get('layer2_cancel', False):
                                    print(f"⏹️ 选项 {opt_idx} 的第二层生成被取消")
                                    return
                                # 标记当前正在生成的选项
                                cache_entry['current_layer2_option'] = opt_idx
                            
                            # 更新global_state（应用第一层的flow_update）
                            updated_global_state = global_state.copy()
                            if 'flow_worldline' not in updated_global_state:
                                updated_global_state['flow_worldline'] = {}
                            flow_update = layer1_option_data.get('flow_update', {})
                            if flow_update:
                                updated_global_state['flow_worldline'].update(flow_update)
                            
                            # 为下一轮的每个选项生成再下一层剧情（在锁外执行，避免长时间持有锁）
                            try:
                                layer2_data = generate_all_options(updated_global_state, next_options)
                                
                                # 再次检查取消标志并写入缓存（生成过程中可能被取消）
                                with cache_lock:
                                    if scene_id in pregeneration_cache:
                                        cache_entry = pregeneration_cache[scene_id]
                                        if cache_entry.get('layer2_cancel', False):
                                            print(f"⏹️ 选项 {opt_idx} 的第二层生成在生成过程中被取消")
                                            return
                                        
                                        if 'layer2' not in cache_entry:
                                            cache_entry['layer2'] = {}
                                        cache_entry['layer2'][opt_idx] = layer2_data
                                        print(f"✅ 选项 {opt_idx} 的第二层生成完成，共生成 {len(layer2_data)} 个选项的剧情")
                            except Exception as e:
                                print(f"❌ 生成选项 {opt_idx} 的第二层失败：{str(e)}")
                        
                        print(f"✅ 第二层预生成完成（仅生成用户选择的选项）")
                        print("---------------------------------------------- 第二层预生成完成（用户选择模式） ----------------------------------------------")
                    else:
                        # 用户还未选择，为所有第一层选项生成第二层
                        layer2_count = 0
                        for opt_idx, layer1_option_data in layer1_data.items():
                            # 检查取消标志（在锁外快速检查）
                            with cache_lock:
                                if scene_id not in pregeneration_cache:
                                    return
                                cache_entry = pregeneration_cache[scene_id]
                                if cache_entry.get('layer2_cancel', False):
                                    print(f"⏹️ 第二层生成被取消（用户选择了其他选项）")
                                    return
                                # 标记当前正在生成的选项
                                cache_entry['current_layer2_option'] = opt_idx
                            
                            next_options = layer1_option_data.get('next_options', [])
                            if next_options:
                                # 更新global_state（应用第一层的flow_update）
                                updated_global_state = global_state.copy()
                                if 'flow_worldline' not in updated_global_state:
                                    updated_global_state['flow_worldline'] = {}
                                flow_update = layer1_option_data.get('flow_update', {})
                                if flow_update:
                                    updated_global_state['flow_worldline'].update(flow_update)
                                
                                # 为下一轮的每个选项生成再下一层剧情（在锁外执行，避免长时间持有锁）
                                try:
                                    layer2_data = generate_all_options(updated_global_state, next_options)
                                    
                                    # 再次检查取消标志并写入缓存（生成过程中可能被取消）
                                    with cache_lock:
                                        if scene_id in pregeneration_cache:
                                            cache_entry = pregeneration_cache[scene_id]
                                            if cache_entry.get('layer2_cancel', False):
                                                print(f"⏹️ 选项 {opt_idx} 的第二层生成在生成过程中被取消")
                                                return
                                            
                                            if 'layer2' not in cache_entry:
                                                cache_entry['layer2'] = {}
                                            cache_entry['layer2'][opt_idx] = layer2_data
                                            layer2_count += len(layer2_data)
                                except Exception as e:
                                    print(f"❌ 生成选项 {opt_idx} 的第二层失败：{str(e)}")
                        
                        print(f"✅ 第二层预生成完成，共生成 {layer2_count} 个选项的剧情")
                        print(f"✅ 场景 {scene_id} 的两层内容预生成全部完成")
                        print("---------------------------------------------- 第二层预生成完成（全量模式） ----------------------------------------------")
                except Exception as e:
                    print(f"❌ 生成第二层时发生错误：{str(e)}")
                    import traceback
                    traceback.print_exc()
                finally:
                    # 标记第二层生成完成
                    with cache_lock:
                        if scene_id in pregeneration_cache:
                            pregeneration_cache[scene_id]['layer2_generating'] = False
                            pregeneration_cache[scene_id]['current_layer2_option'] = None
            
            # 第二层在后台线程中继续生成（不阻塞）
            with cache_lock:
                if scene_id in pregeneration_cache:
                    cache_entry = pregeneration_cache[scene_id]
                    cache_entry['layer2_generating'] = True
                    cache_entry['layer2_cancel'] = False
                    layer2_thread = threading.Thread(target=generate_layer2, daemon=True)
                    cache_entry['layer2_thread'] = layer2_thread
                    layer2_thread.start()
                
        except Exception as e:
            print(f"❌ 预生成过程中发生错误：{str(e)}")
            import traceback
            traceback.print_exc()
    
    # 启动后台线程执行预生成
    thread = threading.Thread(target=async_pregenerate, daemon=True)
    thread.start()
    
    return scene_id

# 新增接口：预生成两层内容（优先级策略 + 渐进式缓存）
@app.route('/pregenerate-next-layers', methods=['POST'])
def pregenerate_next_layers():
    """
    预生成两层内容（按优先级顺序渐进式生成）：
    - 第一层：按优先级顺序（0→1→2→3）逐个生成，生成一个立即写入缓存
    - 第二层：第一层完成后，继续在后台生成第二层
    """
    try:
        # 获取前端传的参数
        data = request.json
        global_state = data.get('globalState', {})
        current_options = data.get('currentOptions', [])
        scene_id = data.get('sceneId', None)  # 当前场景ID
        
        # 基础校验
        if not global_state:
            return jsonify({"status": "error", "message": "全局状态不能为空！"})
        if not current_options:
            return jsonify({"status": "error", "message": "当前选项列表不能为空！"})
        
        # 调用预生成核心逻辑
        scene_id = _pregenerate_next_layers_logic(global_state, current_options, scene_id)
        
        # 立即返回，告知前端预生成已启动
        return jsonify({
            "status": "success",
            "message": "预生成任务已启动！",
            "sceneId": scene_id
        })
        
    except Exception as e:
        print(f"🔴 预生成接口错误：{str(e)}")
        import traceback
        traceback.print_exc()
        error_msg = clean_error_message(str(e))
        return jsonify({"status": "error", "message": f"预生成任务启动失败：{error_msg}"})

# 新增接口：获取预生成的第二层内容
@app.route('/get-pregenerated-layer2', methods=['POST'])
def get_pregenerated_layer2():
    """获取预生成的第二层内容（当用户选择了第一层的某个选项后，可以立即获取第二层）"""
    try:
        data = request.json
        scene_id = data.get('sceneId', None)
        layer1_option_index = data.get('layer1OptionIndex', None)
        layer2_option_index = data.get('layer2OptionIndex', None)
        
        if not scene_id or layer1_option_index is None or layer2_option_index is None:
            return jsonify({"status": "error", "message": "参数不完整！"})
        
        with cache_lock:
            if scene_id in pregeneration_cache:
                cache_entry = pregeneration_cache[scene_id]
                if 'layer2' in cache_entry and layer1_option_index in cache_entry['layer2']:
                    layer2_data = cache_entry['layer2'][layer1_option_index]
                    if layer2_option_index in layer2_data:
                        return jsonify({
                            "status": "success",
                            "optionData": layer2_data[layer2_option_index]
                        })
        
        return jsonify({"status": "error", "message": "未找到预生成的第二层内容！"})
        
    except Exception as e:
        print(f"🔴 获取预生成内容错误：{str(e)}")
        error_msg = clean_error_message(str(e))
        return jsonify({"status": "error", "message": f"获取失败：{error_msg}"})

# 新增接口：保存游戏
@app.route('/save-game', methods=['POST'])
def save_game():
    """
    保存游戏状态到文件
    接收前端传来的游戏状态数据，保存为JSON文件
    """
    try:
        data = request.json
        save_name = data.get('saveName', '').strip()
        global_state = data.get('globalState', {})
        protagonist_attr = data.get('protagonistAttr', {})
        difficulty = data.get('difficulty', '')
        last_options = data.get('lastOptions', [])
        
        # 基础校验
        if not save_name:
            return jsonify({"status": "error", "message": "存档名称不能为空！"})
        # 允许空的global_state（可能是游戏刚开始还没有生成世界观）
        if global_state is None:
            global_state = {}
        
        # 构造存档数据（与main2.py中的格式保持一致）
        save_data = {
            "global_state": global_state,
            "protagonist_attr": protagonist_attr,
            "difficulty": difficulty,
            "last_options": last_options,
            "timestamp": str(datetime.now())
        }
        
        # 生成存档文件名
        save_filename = f"{save_name}.json"
        save_path = os.path.join(SAVE_DIR, save_filename)
        
        # 保存到文件（带重试机制）
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, ensure_ascii=False, indent=2)
                print(f"✅ 游戏已保存到：{save_path}")
                return jsonify({
                    "status": "success",
                    "message": "游戏已成功保存！",
                    "savePath": save_path
                })
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ 保存失败（尝试 {attempt + 1}/{max_retries}），重试中...")
                    import time
                    time.sleep(0.5)  # 等待0.5秒后重试
                else:
                    raise e
        
    except Exception as e:
        print(f"🔴 保存游戏错误：{str(e)}")
        import traceback
        traceback.print_exc()
        error_msg = clean_error_message(str(e))
        return jsonify({"status": "error", "message": f"保存失败，请重试：{error_msg}"})

# 新增接口：列出所有存档
@app.route('/list-saves', methods=['GET'])
def list_saves():
    """
    列出所有存档文件
    返回存档名称列表和基本信息
    """
    try:
        saves = []
        if os.path.exists(SAVE_DIR):
            for file in os.listdir(SAVE_DIR):
                if file.endswith('.json'):
                    save_name = file[:-5]  # 去掉.json后缀
                    save_path = os.path.join(SAVE_DIR, file)
                    
                    # 读取存档基本信息（不加载完整数据）
                    try:
                        with open(save_path, 'r', encoding='utf-8') as f:
                            save_data = json.load(f)
                        
                        # 获取存档时间
                        timestamp = save_data.get('timestamp', '')
                        
                        # 计算进度信息
                        global_state = save_data.get('global_state', {})
                        flow_worldline = global_state.get('flow_worldline', {})
                        current_chapter = flow_worldline.get('current_chapter', 'chapter1')
                        chapter_name = '第一章' if current_chapter == 'chapter1' else ('第二章' if current_chapter == 'chapter2' else '第三章')
                        
                        saves.append({
                            "name": save_name,
                            "timestamp": timestamp,
                            "chapter": chapter_name
                        })
                    except Exception as e:
                        print(f"⚠️ 读取存档 {save_name} 信息失败：{str(e)}")
                        saves.append({
                            "name": save_name,
                            "timestamp": "",
                            "chapter": "未知"
                        })
        
        return jsonify({
            "status": "success",
            "saves": saves
        })
        
    except Exception as e:
        print(f"🔴 列出存档错误：{str(e)}")
        import traceback
        traceback.print_exc()
        error_msg = clean_error_message(str(e))
        return jsonify({"status": "error", "message": f"列出存档失败：{error_msg}", "saves": []})

# 新增接口：加载游戏
@app.route('/load-game', methods=['POST'])
def load_game():
    """
    加载指定存档
    接收存档名称，返回完整的游戏状态数据
    """
    try:
        data = request.json
        save_name = data.get('saveName', '').strip()
        
        if not save_name:
            return jsonify({"status": "error", "message": "存档名称不能为空！"})
        
        # 生成存档文件名
        save_filename = f"{save_name}.json"
        save_path = os.path.join(SAVE_DIR, save_filename)
        
        # 检查文件是否存在
        if not os.path.exists(save_path):
            return jsonify({"status": "error", "message": f"存档文件不存在：{save_name}"})
        
        # 读取存档数据（带重试机制）
        max_retries = 3
        save_data = None
        for attempt in range(max_retries):
            try:
                with open(save_path, 'r', encoding='utf-8') as f:
                    save_data = json.load(f)
                break  # 成功读取，退出重试循环
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ 加载失败（尝试 {attempt + 1}/{max_retries}），重试中...")
                    import time
                    time.sleep(0.5)  # 等待0.5秒后重试
                else:
                    raise e
        
        if not save_data:
            return jsonify({"status": "error", "message": "加载失败，请重试"})
        
        print(f"✅ 游戏已从：{save_path} 加载")
        
        # 返回完整的存档数据
        return jsonify({
            "status": "success",
            "message": "游戏加载成功！",
            "saveData": save_data
        })
        
    except Exception as e:
        print(f"🔴 加载游戏错误：{str(e)}")
        import traceback
        traceback.print_exc()
        error_msg = clean_error_message(str(e))
        return jsonify({"status": "error", "message": f"加载失败，请重试：{error_msg}"})

# 新增接口：删除存档
@app.route('/delete-save', methods=['POST'])
def delete_save():
    """
    删除指定存档文件
    """
    try:
        data = request.json
        save_name = data.get('saveName', '').strip()
        
        if not save_name:
            return jsonify({"status": "error", "message": "存档名称不能为空！"})
        
        # 生成存档文件名
        save_filename = f"{save_name}.json"
        save_path = os.path.join(SAVE_DIR, save_filename)
        
        # 检查文件是否存在
        if not os.path.exists(save_path):
            return jsonify({"status": "error", "message": f"存档文件不存在：{save_name}"})
        
        # 删除文件
        os.remove(save_path)
        print(f"✅ 已删除存档：{save_path}")
        
        return jsonify({
            "status": "success",
            "message": "存档已成功删除！"
        })
        
    except Exception as e:
        print(f"🔴 删除存档错误：{str(e)}")
        import traceback
        traceback.print_exc()
        error_msg = clean_error_message(str(e))
        return jsonify({"status": "error", "message": f"删除存档失败：{error_msg}"})

# 新增接口：生成游戏结局
@app.route('/generate-ending', methods=['POST'])
def generate_ending():
    """
    生成游戏结局（基于当前游戏状态）
    当用户主动选择结束游戏时调用此接口
    """
    try:
        # 获取前端传的参数
        data = request.json
        global_state = data.get('globalState', {})
        
        # 基础校验
        if not global_state:
            return jsonify({"status": "error", "message": "全局状态不能为空！"})
        
        print(f"🔄 开始生成游戏结局...")
        
        # 确保隐藏结局预测存在
        if 'hidden_ending_prediction' not in global_state:
            print(f"📝 生成初始结局预测...")
            global_state['hidden_ending_prediction'] = generate_ending_prediction(global_state)
        
        # 基于当前游戏进度修改结局内容（生成最终结局）
        print(f"📝 基于当前游戏进度生成最终结局...")
        modify_ending_content(global_state)
        
        # 获取最终的结局预测
        ending_prediction = global_state.get('hidden_ending_prediction', {})
        main_tone = ending_prediction.get('main_tone', 'NE')
        content = ending_prediction.get('content', '主角完成了主要任务，虽然过程中经历了许多困难，但最终达成了预期目标')
        
        print(f"✅ 游戏结局生成完成，主基调：{main_tone}")
        
        # 返回结果
        return jsonify({
            "status": "success",
            "message": "游戏结局生成成功！",
            "ending": {
                "main_tone": main_tone,
                "content": content
            }
        })
        
    except Exception as e:
        print(f"🔴 生成游戏结局错误：{str(e)}")
        import traceback
        traceback.print_exc()
        error_msg = clean_error_message(str(e))
        return jsonify({"status": "error", "message": f"生成游戏结局失败：{error_msg}"})

# ------------------------------
# 图片缓存管理函数
# ------------------------------
import hashlib

def get_cached_image(prompt_hash: str) -> str:
    """从缓存获取图片路径"""
    cache_path = Path(IMAGE_CACHE_DIR) / f"{prompt_hash}.png"
    if cache_path.exists():
        return str(cache_path)
    return None

def cache_image(prompt_hash: str, image_url: str) -> str:
    """缓存图片到本地"""
    try:
        # 检查是否是相对路径（本地缓存路径）
        if image_url.startswith('/image_cache/') or image_url.startswith('image_cache/'):
            # 已经是本地缓存路径，不需要下载
            cache_path = Path(IMAGE_CACHE_DIR) / f"{prompt_hash}.png"
            if cache_path.exists():
                print(f"✅ 图片已在本地缓存：{cache_path}")
                return str(cache_path)
            else:
                # 如果文件不存在，尝试从相对路径提取hash
                import re
                hash_match = re.search(r'([a-f0-9]{32})\.png', image_url)
                if hash_match:
                    existing_hash = hash_match.group(1)
                    existing_path = Path(IMAGE_CACHE_DIR) / f"{existing_hash}.png"
                    if existing_path.exists():
                        # 复制文件到新的hash名称
                        import shutil
                        shutil.copy2(existing_path, cache_path)
                        print(f"✅ 从现有缓存复制图片：{cache_path}")
                        return str(cache_path)
                raise ValueError(f"本地缓存文件不存在：{image_url}")
        
        # 检查是否是完整的URL
        if not (image_url.startswith('http://') or image_url.startswith('https://')):
            raise ValueError(f"无效的图片URL格式：{image_url}（需要完整的HTTP/HTTPS URL或本地缓存路径）")
        
        # 下载图片
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        cache_path = Path(IMAGE_CACHE_DIR) / f"{prompt_hash}.png"
        
        with open(cache_path, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ 图片已缓存：{cache_path}")
        return str(cache_path)
    except Exception as e:
        print(f"❌ 图片缓存失败：{str(e)}")
        raise

def generate_image_with_cache(scene_description: str, style: str, global_state: Dict) -> Dict:
    """带缓存的图片生成"""
    # 生成缓存键
    prompt_hash = hashlib.md5(f"{scene_description}_{style}".encode()).hexdigest()
    
    # 检查缓存
    cached_path = get_cached_image(prompt_hash)
    if cached_path:
        print(f"✅ 使用缓存的图片：{prompt_hash}")
        return {
            "url": f"/image_cache/{prompt_hash}.png",
            "prompt": scene_description,
            "style": style,
            "width": 1024,
            "height": 1024,
            "cached": True
        }
    
    # 生成新图片
    image_data = generate_scene_image(scene_description, global_state, style)
    if not image_data or not image_data.get('url'):
        return None
    
    image_url = image_data['url']
    
    # 检查图片URL是否是本地缓存路径（说明已经在main2.py中缓存过了）
    if image_url.startswith('/image_cache/') or image_url.startswith('image_cache/'):
        # 已经是本地缓存路径，直接返回，不需要再次缓存
        print(f"✅ 图片已在main2.py中缓存，使用现有路径：{image_url}")
        return {
            "url": image_url,
            "prompt": scene_description,
            "style": style,
            "width": 1024,
            "height": 1024,
            "cached": True
        }
    
    # 缓存图片（只有当image_url是完整的HTTP/HTTPS URL时才需要下载）
    try:
        local_path = cache_image(prompt_hash, image_url)
        return {
            "url": f"/image_cache/{prompt_hash}.png",
            "prompt": scene_description,
            "style": style,
            "width": 1024,
            "height": 1024,
            "cached": False
        }
    except Exception as e:
        print(f"⚠️ 图片缓存失败，使用原始URL：{str(e)}")
        return image_data

# ------------------------------
# 视觉内容生成API接口
# ------------------------------

@app.route('/generate-scene-image', methods=['POST'])
def generate_scene_image_api():
    """单独生成场景图片的接口"""
    try:
        data = request.json
        scene_description = data.get('sceneDescription', '')
        global_state = data.get('globalState', {})
        style = data.get('style', 'default')
        
        if not scene_description:
            return jsonify({"status": "error", "message": "场景描述不能为空"})
        
        image_data = generate_scene_image(scene_description, global_state, style)
        
        if image_data:
            return jsonify({
                "status": "success",
                "image": image_data
            })
        else:
            return jsonify({
                "status": "error",
                "message": "图片生成失败"
            })
    except Exception as e:
        print(f"🔴 生成场景图片错误：{str(e)}")
        import traceback
        traceback.print_exc()
        error_msg = clean_error_message(str(e))
        return jsonify({"status": "error", "message": f"生成场景图片失败：{error_msg}"})

# ==================== 视频生成API接口已禁用（性能优化） ====================
# @app.route('/generate-scene-video', methods=['POST'])
# def generate_scene_video_api():
#     """异步生成场景视频（5-10秒）"""
#     ... (已注释)

# @app.route('/video-status/<task_id>', methods=['GET'])
# def get_video_status_api(task_id):
#     """查询视频生成状态"""
#     ... (已注释)

# 提供占位接口，返回错误提示
@app.route('/generate-scene-video', methods=['POST'])
def generate_scene_video_api():
    """视频生成功能已禁用"""
    return jsonify({
        "status": "error",
        "message": "视频生成功能已禁用（性能优化）"
    })

@app.route('/video-status/<task_id>', methods=['GET'])
def get_video_status_api(task_id):
    """视频生成功能已禁用"""
    return jsonify({
        "status": "error",
        "message": "视频生成功能已禁用（性能优化）"
    }), 404

@app.route('/image_cache/<filename>')
def serve_cached_image(filename):
    """提供缓存的图片文件"""
    try:
        cache_path = Path(IMAGE_CACHE_DIR) / filename
        if cache_path.exists() and cache_path.suffix.lower() in ['.png', '.jpg', '.jpeg']:
            return send_file(cache_path, mimetype='image/png')
        return jsonify({"status": "error", "message": "图片不存在"}), 404
    except Exception as e:
        print(f"🔴 提供缓存图片错误：{str(e)}")
        return jsonify({"status": "error", "message": "无法提供图片"}), 500

# 前端静态文件路由
@app.route('/')
def index():
    """返回前端首页"""
    return send_from_directory('game-frontend', 'index.html')

@app.route('/<path:filename>')
def frontend_files(filename):
    """提供前端静态文件（JS、CSS等）"""
    # 排除API路由和图片缓存路由
    if filename.startswith('api/') or filename.startswith('image_cache/'):
        return jsonify({"status": "error", "message": "路径不存在"}), 404
    try:
        return send_from_directory('game-frontend', filename)
    except:
        return jsonify({"status": "error", "message": "文件不存在"}), 404

# 启动服务
if __name__ == "__main__":
    print("=== 文本冒险游戏API服务器 ===")
    print("前端访问地址：http://127.0.0.1:5001")
    print("API端点：")
    print("  POST /generate-worldview - 生成游戏世界观")
    print("  POST /generate-option - 生成单个选项对应的剧情（支持缓存）")
    print("  POST /pregenerate-next-layers - 预生成两层内容")
    print("  POST /get-pregenerated-layer2 - 获取预生成的第二层内容")
    print("  POST /generate-ending - 生成游戏结局")
    print("  POST /save-game - 保存游戏")
    print("  GET /list-saves - 列出所有存档")
    print("  POST /load-game - 加载游戏")
    print("  POST /delete-save - 删除存档")
    print("  POST /generate-scene-image - 生成场景图片")
    # print("  POST /generate-scene-video - 生成场景视频（5-10秒）")  # 已禁用
    # print("  GET /video-status/<task_id> - 查询视频生成状态")  # 已禁用
    print("  GET /image_cache/<filename> - 获取缓存的图片")
    print("===============================")
    app.run(host='0.0.0.0', port=5001, debug=True)