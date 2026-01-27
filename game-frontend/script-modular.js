// ========== 代码版本标识 ==========
// 版本：使用同一定位上下文方案
// 更新时间：2024-12-XX
// 改动说明：
// 1. 背景图片通过全屏背景（#global-bg）显示
// 2. 文本和选项在选项容器内切换显示
// 3. 移除了复杂的位置计算逻辑
// ====================================
console.log('🚀 [代码版本] 使用同一定位上下文方案已加载');

// 游戏主模块
const Game = (() => {
    // 私有变量
    let gameState;
    let elements;
    let soundManager;
    // 图片风格选择相关变量
    let selectedStyle = null;
    let selectedSubStyle = null;
    let customStyleText = '';
    
    // 初始化函数
    function init() {
        // 初始化音效管理
        initSoundManager();
        
        // 初始化游戏状态
        initGameState();
        
        // 初始化DOM元素
        initElements();
        
        // 初始化事件监听
        initEventListeners();
    }
    
    // 音效管理模块
    function initSoundManager() {
        soundManager = {
            sounds: {},
            isMuted: false,
            
            // 初始化音效
            init() {
                // 预加载常用音效
                this.sounds = {
                    select: new Audio(),
                    click: new Audio(),
                    slide: new Audio(),
                    achievement: new Audio(),
                    reset: new Audio(),
                    save: new Audio(),
                    load: new Audio(),
                    confirm: new Audio(),
                    unlock: new Audio(),
                    super: new Audio(),
                    tonechange: new Audio(),
                    ending: new Audio(),
                    complete: new Audio(),
                    typeend: new Audio()
                };
            },
            
            // 播放音效
            play(soundName) {
                if (!this.isMuted && this.sounds[soundName]) {
                    try {
                        this.sounds[soundName].currentTime = 0;
                        this.sounds[soundName].play().catch(error => {
                            console.debug('音效播放失败:', error);
                        });
                    } catch (error) {
                        console.debug('音效播放异常:', error);
                    }
                }
            },
            
            // 切换静音状态
            toggleMute() {
                this.isMuted = !this.isMuted;
            }
        };
        
        // 初始化音效
        soundManager.init();
    }
    
    // 字体管理模块
    const FontManager = (() => {
        // 字体映射配置：根据游戏风格和主题选择合适的字体
        const fontMapping = {
            // 根据图片风格映射字体
            style: {
                'realistic': {
                    fontFamily: '"Noto Sans SC", sans-serif',
                    fontWeight: '400',
                    description: '现代简洁'
                },
                'anime': {
                    fontFamily: '"ZCOOL KuaiLe", cursive',
                    fontWeight: '400',
                    description: '活泼可爱'
                },
                'ink_painting': {
                    fontFamily: '"Long Cang", cursive',
                    fontWeight: '400',
                    description: '古典优雅'
                },
                'oil_painting': {
                    fontFamily: '"Noto Serif SC", serif',
                    fontWeight: '500',
                    description: '典雅庄重'
                },
                'cyberpunk': {
                    fontFamily: '"ZCOOL QingKe HuangYou", sans-serif',
                    fontWeight: '400',
                    description: '科技未来'
                },
                'custom': {
                    fontFamily: '"Noto Sans SC", sans-serif',
                    fontWeight: '400',
                    description: '自定义'
                }
            },
            // 根据游戏基调映射字体（与HTML中的data-tone值对应）
            tone: {
                'happy_ending': {
                    fontFamily: '"ZCOOL KuaiLe", cursive',
                    fontWeight: '400',
                    description: '轻松愉快'
                },
                'bad_ending': {  // HTML中使用bad_ending
                    fontFamily: '"Noto Serif SC", serif',
                    fontWeight: '500',
                    description: '沉重肃穆'
                },
                'tragic_ending': {  // 兼容旧名称
                    fontFamily: '"Noto Serif SC", serif',
                    fontWeight: '500',
                    description: '沉重肃穆'
                },
                'normal_ending': {
                    fontFamily: '"Noto Sans SC", sans-serif',
                    fontWeight: '400',
                    description: '标准'
                },
                'dark_depressing': {  // HTML中使用dark_depressing
                    fontFamily: '"ZCOOL XiaoWei", serif',
                    fontWeight: '400',
                    description: '神秘深沉'
                },
                'dark_deep': {  // 兼容旧名称
                    fontFamily: '"ZCOOL XiaoWei", serif',
                    fontWeight: '400',
                    description: '神秘深沉'
                },
                'humorous': {  // HTML中使用humorous
                    fontFamily: '"ZCOOL KuaiLe", cursive',
                    fontWeight: '400',
                    description: '幽默风趣'
                },
                'humor': {  // 兼容旧名称
                    fontFamily: '"ZCOOL KuaiLe", cursive',
                    fontWeight: '400',
                    description: '幽默风趣'
                },
                'abstract': {
                    fontFamily: '"Ma Shan Zheng", cursive',
                    fontWeight: '400',
                    description: '抽象艺术'
                },
                'aesthetic': {
                    fontFamily: '"Long Cang", cursive',
                    fontWeight: '400',
                    description: '唯美诗意'
                },
                'logical': {
                    fontFamily: '"Noto Sans SC", sans-serif',
                    fontWeight: '500',
                    description: '严谨理性'
                },
                'mysterious': {
                    fontFamily: '"ZCOOL XiaoWei", serif',
                    fontWeight: '400',
                    description: '神秘莫测'
                },
                'stream_of_consciousness': {
                    fontFamily: '"Ma Shan Zheng", cursive',
                    fontWeight: '400',
                    description: '意识流'
                }
            }
        };
        
        // 默认字体
        const defaultFont = {
            fontFamily: '"Noto Sans SC", sans-serif',
            fontWeight: '400',
            description: '默认'
        };
        
        // 获取字体配置（优先级：风格 > 基调 > 默认）
        function getFontConfig(imageStyle, tone) {
            let fontConfig = defaultFont;
            
            // 优先使用图片风格对应的字体
            if (imageStyle && imageStyle.type && fontMapping.style[imageStyle.type]) {
                fontConfig = fontMapping.style[imageStyle.type];
            }
            // 如果没有图片风格，使用基调对应的字体
            else if (tone && fontMapping.tone[tone]) {
                fontConfig = fontMapping.tone[tone];
            }
            
            return fontConfig;
        }
        
        // 应用字体到指定元素
        function applyFont(element, fontConfig) {
            if (!element || !fontConfig) return;
            
            element.style.fontFamily = fontConfig.fontFamily;
            element.style.fontWeight = fontConfig.fontWeight;
            element.style.transition = 'font-family 0.3s ease, font-weight 0.3s ease';
        }
        
        // 应用字体到游戏文本元素
        function applyFontToGame(imageStyle, tone) {
            const fontConfig = getFontConfig(imageStyle, tone);
            
            // 应用到场景文本
            const sceneText = document.getElementById('scene-text');
            if (sceneText) {
                applyFont(sceneText, fontConfig);
            }
            
            // 应用到选项列表
            const optionsList = document.getElementById('options-list');
            if (optionsList) {
                applyFont(optionsList, fontConfig);
            }
            
            // 应用到角色面板
            const characterPanel = document.querySelector('.character-panel');
            if (characterPanel) {
                applyFont(characterPanel, fontConfig);
            }
            
            console.log(`✅ 字体已应用: ${fontConfig.description} (${fontConfig.fontFamily})`);
        }
        
        return {
            getFontConfig,
            applyFont,
            applyFontToGame
        };
    })();
    
    // 工具函数：HTML转义，防止XSS攻击
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // 工具函数：输入验证
    const inputValidator = {
        // 验证游戏主题
        validateTheme(theme) {
            const trimmedTheme = theme.trim();
            if (!trimmedTheme) {
                return { valid: false, message: '游戏主题不能为空' };
            }
            if (trimmedTheme.length > 20) {
                return { valid: false, message: '游戏主题不能超过20个字符' };
            }
            // 检查是否包含特殊字符（允许中文、英文、数字和常用标点）
            const themeRegex = /^[\u4e00-\u9fa5a-zA-Z0-9\s\-_（）()《》<>【】\[\]{}，。,.:;"'!?！？]+$/;
            if (!themeRegex.test(trimmedTheme)) {
                return { valid: false, message: '游戏主题包含非法字符' };
            }
            return { valid: true, message: '' };
        },
        
        // 验证存档名称
        validateSaveName(name) {
            const trimmedName = name.trim();
            if (!trimmedName) {
                return { valid: false, message: '存档名称不能为空' };
            }
            if (trimmedName.length > 15) {
                return { valid: false, message: '存档名称不能超过15个字符' };
            }
            // 检查是否包含特殊字符
            const nameRegex = /^[\u4e00-\u9fa5a-zA-Z0-9\s\-_]+$/;
            if (!nameRegex.test(trimmedName)) {
                return { valid: false, message: '存档名称包含非法字符' };
            }
            return { valid: true, message: '' };
        }
    };
    
    // 简化的音效播放函数
    function playSound(soundName) {
        soundManager.play(soundName);
    }
    
    // ------------------------------
    // 视觉内容管理模块
    // ------------------------------
    const VisualContentManager = (() => {
        // 图片预加载缓存
        const imageCache = new Map();
        
        // 预加载图片
        function preloadImage(url) {
            return new Promise((resolve, reject) => {
                if (imageCache.has(url)) {
                    resolve(imageCache.get(url));
                    return;
                }
                
                const img = new Image();
                img.crossOrigin = 'anonymous'; // 允许跨域
                img.onload = () => {
                    imageCache.set(url, img);
                    resolve(img);
                };
                img.onerror = () => {
                    console.error('图片加载失败:', url);
                    reject(new Error(`图片加载失败: ${url}`));
                };
                img.src = url;
            });
        }
        
        // 更新场景媒体容器的背景图片位置（已废弃：不再使用背景图片，只使用图片层）
        // 注意：此函数已废弃，不再设置容器背景图片，只确保移除任何残留的背景图片
        function updateSceneMediaContainerBackground(imageUrl) {
            // 已移除scene-container，背景图片通过#global-bg全屏显示
            // 此函数保留用于兼容性，但不再执行任何操作
            console.log('🔧 [背景图片] 使用全屏背景图片（#global-bg）显示');
        }
        
        // 显示场景图片
        function displaySceneImage(imageData) {
            // ========== 代码版本标识 ==========
            // 版本：文本直接定位在图片上，无覆盖层（2024-12-XX）
            // 改动说明：已移除.narration-overlay覆盖层，文本元素直接定位在图片层上
            // 背景图片通过全屏背景（#global-bg）显示
            // 不使用背景图片，只使用图片层，文本元素直接覆盖在图片层上
            // ====================================
            console.log('🎨 displaySceneImage被调用，参数:', imageData);
            console.log('📌 [代码版本] 文本直接定位在图片上，无覆盖层 - 已移除.narration-overlay');
            
            // 注意：已移除场景图片层（#scene-image），只使用全屏背景图片（#global-bg）
            const sceneImage = document.getElementById('scene-image'); // 可能不存在，已移除
            const sceneVideo = document.getElementById('scene-video');
            const loadingDiv = document.getElementById('image-loading');
            const loadingText = document.getElementById('loading-text');
            const globalBg = document.getElementById('global-bg');
            // 已移除scene-container，不再需要
            
            // 注意：不再需要验证 sceneImage，因为已移除场景图片层
            
            // 验证图片数据
            if (!imageData) {
                console.warn('⚠️ imageData为空，只设置全屏背景');
                if (sceneVideo) sceneVideo.style.display = 'none';
                if (loadingDiv) loadingDiv.style.display = 'none';
                // 如果没有图片数据，保持当前背景（不清除，以便保留之前的背景图片）
                return;
            }
            
            // 验证URL字段（支持多种可能的字段名）
            let rawImageUrl = imageData.url || imageData.image_url || imageData.src || null;
            if (!rawImageUrl) {
                console.error('❌ imageData中没有找到URL字段:', imageData);
                if (loadingDiv) loadingDiv.style.display = 'none';
                return;
            }
            
            console.log('✅ 找到图片URL:', rawImageUrl);
            
            // 显示加载状态
            if (loadingDiv) {
                loadingDiv.style.display = 'flex';
                if (loadingText) loadingText.textContent = '正在加载场景图片...';
            }
            
            // 注意：已移除场景图片层，不再设置 sceneImage
            // 只使用全屏背景图片（#global-bg）
            if (sceneVideo) {
                sceneVideo.style.display = 'none';
            }
            
            // 问题2修复：处理相对路径（本地缓存）或外部URL
            console.log('🔍 原始图片URL:', rawImageUrl);
            console.log('🔍 图片数据类型:', typeof rawImageUrl);
            
            // 确保imageUrl是字符串
            if (typeof rawImageUrl !== 'string') {
                console.error('❌ 图片URL不是字符串类型:', rawImageUrl);
                if (loadingDiv) loadingDiv.style.display = 'none';
                return;
            }
            
            // 处理不同类型的URL - 改进逻辑，确保所有格式都能正确处理
            let finalImageUrl = rawImageUrl;
            
            // 移除URL两端的空格和特殊字符
            finalImageUrl = finalImageUrl.trim();
            
            if (finalImageUrl.startsWith('/image_cache/')) {
                // 本地缓存路径 - 转换为完整URL
                finalImageUrl = `http://127.0.0.1:5001${finalImageUrl}`;
                console.log('✅ 检测到本地缓存路径，转换为:', finalImageUrl);
            } else if (finalImageUrl.startsWith('image_cache/')) {
                // 相对路径（没有前导斜杠）
                finalImageUrl = `http://127.0.0.1:5001/${finalImageUrl}`;
                console.log('✅ 检测到相对缓存路径，转换为:', finalImageUrl);
            } else if (finalImageUrl.startsWith('http://') || finalImageUrl.startsWith('https://')) {
                // 外部URL，直接使用
                console.log('✅ 检测到外部URL，直接使用');
            } else if (finalImageUrl.startsWith('data:')) {
                // Base64数据URL，直接使用
                console.log('✅ 检测到Base64数据URL');
            } else if (finalImageUrl.startsWith('//')) {
                // 协议相对URL，添加https
                finalImageUrl = 'https:' + finalImageUrl;
                console.log('✅ 修复协议相对URL:', finalImageUrl);
            } else {
                // 尝试其他修复方式
                console.warn('⚠️ 图片URL格式异常，尝试修复:', finalImageUrl);
                
                // 如果包含image_cache关键字，尝试修复
                if (finalImageUrl.includes('image_cache')) {
                    const filename = finalImageUrl.split('image_cache')[1].replace(/^[\/\\]+/, '');
                    finalImageUrl = `http://127.0.0.1:5001/image_cache/${filename}`;
                    console.log('✅ 从异常URL中提取文件名，修复为:', finalImageUrl);
                } else {
                    console.error('❌ 无法识别的URL格式:', finalImageUrl);
                    if (loadingDiv) loadingDiv.style.display = 'none';
                    if (sceneImage) {
                        sceneImage.style.display = 'none';
                    }
                    return; // 无法修复，直接返回
                }
            }
            
            const imageUrl = finalImageUrl;
            
            console.log('🔍 处理后的图片URL:', imageUrl);
            
            // 预加载图片（添加超时机制，避免长时间等待）
            const imageLoadTimeout = setTimeout(() => {
                console.warn('⚠️ 图片加载超时（10秒），继续显示场景（不等待图片）');
                if (loadingDiv) loadingDiv.style.display = 'none';
                // 不隐藏图片元素，让它继续尝试加载（后台加载）
                // 但不会阻塞场景显示
            }, 10000); // 10秒超时
            
            preloadImage(imageUrl)
                .then(() => {
                    clearTimeout(imageLoadTimeout);
                    console.log('✅ 图片预加载成功:', imageUrl);
                    
                    // ========== 方案：使用同一定位上下文 ==========
                    // 背景图片通过全屏背景（#global-bg）显示
                    // 已移除scene-container，背景图片通过#global-bg全屏显示
                    console.log('🔧 [定位方案] 使用全屏背景图片（#global-bg）');
                    
                    // ========== 只设置全屏背景图片（已移除场景图片层） ==========
                    if (globalBg) {
                        globalBg.style.backgroundImage = `url(${imageUrl})`;
                        globalBg.style.backgroundSize = 'cover';
                        globalBg.style.backgroundPosition = 'center';
                        globalBg.style.backgroundRepeat = 'no-repeat';
                        globalBg.style.opacity = '1';
                        globalBg.style.transition = 'opacity 0.5s ease-in-out';
                        console.log('✅ 全屏背景图片已设置（文本直接显示在背景图片上）');
                    }
                    
                    // 注意：已移除场景图片层（#scene-image），不再设置 sceneImage.src
                    // 文本元素直接显示在全屏背景图片上
                    
                    // 已移除所有 sceneImage.onload 和 sceneImage.onerror 代码
                    // 因为不再使用场景图片层
                    if (loadingDiv) {
                        // 图片加载完成（实际上只设置了背景图片）
                        setTimeout(() => {
                            loadingDiv.style.display = 'none';
                            console.log('✅ 全屏背景图片已设置，文本直接显示在背景上');
                        }, 100);
                    }
                    
                    /* 已移除的代码块：
                        sceneImage.onload = () => {
                            console.log('✅ 图片onload事件触发');
                            console.log('✅ 图片尺寸:', sceneImage.naturalWidth, 'x', sceneImage.naturalHeight);
                            
                            // 确保图片层完全覆盖容器，与背景图片一致
                            sceneImage.style.setProperty('position', 'absolute', 'important');
                            sceneImage.style.setProperty('top', '0', 'important');
                            sceneImage.style.setProperty('left', '0', 'important');
                            sceneImage.style.setProperty('right', '0', 'important');
                            sceneImage.style.setProperty('bottom', '0', 'important');
                            sceneImage.style.setProperty('width', '100%', 'important');
                            sceneImage.style.setProperty('height', '100%', 'important');
                            sceneImage.style.setProperty('margin', '0', 'important');
                            sceneImage.style.setProperty('padding', '0', 'important');
                            sceneImage.style.setProperty('object-position', '50% 50%', 'important');
                            
                            // ========== 诊断工具：检测图片裁剪和错位 ==========
                            setTimeout(() => {
                                // 重新获取元素，确保在作用域内
                                // 已移除scene-container，不再需要容器检查
                                const containerRect = null;
                                const imageRect = sceneImage.getBoundingClientRect();
                                const sceneTextElement = document.getElementById('scene-text');
                                const textRect = sceneTextElement ? sceneTextElement.getBoundingClientRect() : null;
                                
                                // 获取图片的原始尺寸和显示尺寸
                                const naturalWidth = sceneImage.naturalWidth;
                                const naturalHeight = sceneImage.naturalHeight;
                                const displayWidth = imageRect.width;
                                const displayHeight = imageRect.height;
                                
                                // 计算裁剪比例
                                const containerAspect = containerRect.width / containerRect.height;
                                const imageAspect = naturalWidth / naturalHeight;
                                
                                // 判断是水平裁剪还是垂直裁剪
                                const isHorizontalCrop = imageAspect > containerAspect;
                                const isVerticalCrop = imageAspect < containerAspect;
                                
                                // 计算裁剪量
                                let cropInfo = {};
                                if (isHorizontalCrop) {
                                    const scaledHeight = containerRect.width / imageAspect;
                                    const cropTop = (scaledHeight - containerRect.height) / 2;
                                    cropInfo = {
                                        type: 'horizontal',
                                        cropTop: cropTop,
                                        cropBottom: cropTop,
                                        cropLeft: 0,
                                        cropRight: 0,
                                        scaledWidth: containerRect.width,
                                        scaledHeight: scaledHeight
                                    };
                                } else {
                                    const scaledWidth = containerRect.height * imageAspect;
                                    const cropLeft = (scaledWidth - containerRect.width) / 2;
                                    cropInfo = {
                                        type: 'vertical',
                                        cropTop: 0,
                                        cropBottom: 0,
                                        cropLeft: cropLeft,
                                        cropRight: cropLeft,
                                        scaledWidth: scaledWidth,
                                        scaledHeight: containerRect.height
                                    };
                                }
                                
                                console.log('🔍 [错位诊断] 图片裁剪分析:', {
                                    容器尺寸: { width: containerRect.width, height: containerRect.height },
                                    图片原始尺寸: { width: naturalWidth, height: naturalHeight },
                                    图片显示尺寸: { width: displayWidth, height: displayHeight },
                                    容器宽高比: containerAspect.toFixed(3),
                                    图片宽高比: imageAspect.toFixed(3),
                                    裁剪类型: cropInfo.type,
                                    裁剪信息: cropInfo,
                                    图片层位置: imageRect,
                                    文本元素位置: textRect
                                });
                                
                                // 检查背景图片和图片层设置（已移除scene-container）
                                // 背景图片通过#global-bg全屏显示
                                const bgImage = 'none';
                                const imgObjectFit = window.getComputedStyle(sceneImage).objectFit;
                                const imgObjectPosition = window.getComputedStyle(sceneImage).objectPosition;
                                
                                console.log('🔍 [错位诊断] 设置检查:');
                                console.log('  容器背景图片:', bgImage === 'none' || bgImage === '' ? '已移除（正确）' : bgImage);
                                console.log('  图片层设置:', {
                                    objectFit: imgObjectFit,
                                    objectPosition: imgObjectPosition
                                });
                                console.log('  方案: 不使用背景图片，只使用图片层');
                                console.log('  结果: 图片层和文本元素看到的是同一张图片，不会错位（文本直接定位在图片上，无覆盖层）');
                                
                                // 如果检测到仍有背景图片，输出警告并移除
                                if (bgImage !== 'none' && bgImage !== '') {
                                    console.warn('⚠️ [错位诊断] 检测到容器仍有背景图片！正在移除...');
                                    // 已移除scene-container，不再需要移除背景图片
                                    console.log('✅ [错位诊断] 背景图片已移除');
                                }
                                
                                // 检查图片层设置是否正确
                                if (imgObjectFit !== 'cover' || imgObjectPosition !== '50% 50%') {
                                    console.warn('⚠️ [错位诊断] 图片层设置不正确！');
                                    console.warn('  当前设置:', { objectFit: imgObjectFit, objectPosition: imgObjectPosition });
                                    console.warn('  应该设置为: { objectFit: "cover", objectPosition: "50% 50%" }');
                                } else {
                                    console.log('✅ [错位诊断] 图片层设置正确');
                                }
                            }, 500);
                            
                            // 调用原有的onload处理器（如果有）
                            if (existingOnload && typeof existingOnload === 'function') {
                                existingOnload.call(sceneImage);
                            }
                            
                            // 验证定位（已移除scene-container）
                            const imageRect = sceneImage.getBoundingClientRect();
                            console.log('🔍 [定位验证] 图片加载后:', {
                                图片层rect: imageRect,
                                背景图片: '通过#global-bg全屏显示'
                            });
                            
                            // 问题1和问题4修复：确保图片元素可见且opacity正确设置
                            sceneImage.style.setProperty('display', 'block', 'important');
                            sceneImage.style.setProperty('visibility', 'visible', 'important');
                            
                            // 问题4修复：确保opacity设置为1（使用important覆盖CSS）
                            setTimeout(() => {
                                sceneImage.style.setProperty('opacity', '1', 'important');
                                console.log('✅ 图片opacity已设置为1');
                            }, 100);
                            
                            if (loadingDiv) loadingDiv.style.display = 'none';
                            
                            // 调试：检查最终状态
                            const computedStyle = window.getComputedStyle(sceneImage);
                            console.log('✅ 图片显示状态:', {
                                display: computedStyle.display,
                                opacity: computedStyle.opacity,
                                visibility: computedStyle.visibility,
                                src: sceneImage.src,
                                zIndex: computedStyle.zIndex,
                                width: computedStyle.width,
                                height: computedStyle.height,
                                naturalWidth: sceneImage.naturalWidth,
                                naturalHeight: sceneImage.naturalHeight,
                                complete: sceneImage.complete
                            });
                        };
                    */
                })
                .catch(error => {
                    clearTimeout(imageLoadTimeout);
                    console.error('❌ 图片预加载失败:', error);
                    console.error('❌ 错误类型:', error.name);
                    console.error('❌ 错误消息:', error.message);
                    console.error('❌ 图片URL:', imageUrl);
                    
                    // 尝试直接设置src，跳过预加载（某些情况下预加载可能失败但直接加载可以成功）
                    console.log('🔄 预加载失败，尝试直接设置图片src...');
                    
                    // ========== 方案：不使用背景图片，只使用图片层（直接模式） ==========
                    // 背景图片通过全屏背景（#global-bg）显示
                    // 不使用背景图片，只使用图片层，让文本覆盖层直接覆盖在图片层上
                    // ====================================================
                    // 已移除scene-container，背景图片通过#global-bg全屏显示
                    console.log('🔧 [定位方案-直接模式] 使用全屏背景图片（#global-bg）');
                    
                    // 可选：也设置全屏背景（用于选项区域等其他地方）
                    if (globalBg) {
                        globalBg.style.backgroundImage = `url(${imageUrl})`;
                        globalBg.style.backgroundSize = 'cover';
                        globalBg.style.backgroundPosition = 'center';
                        globalBg.style.backgroundRepeat = 'no-repeat';
                        globalBg.style.opacity = '1';
                        globalBg.style.transition = 'opacity 0.5s ease-in-out';
                        console.log('✅ 全屏背景图片已设置（直接模式，用于选项区域）');
                    }
                    
                    // 已移除场景图片层，不再设置 sceneImage
                    // 只使用全屏背景图片（#global-bg）
                    if (loadingDiv) {
                        setTimeout(() => {
                            loadingDiv.style.display = 'none';
                            console.log('✅ 全屏背景图片已设置（直接模式）');
                        }, 100);
                    }
                });
        }
        
        // ==================== 视频显示功能已禁用（性能优化） ====================
        // 显示场景视频
        // function displaySceneVideo(videoData) {
        //     ... (已注释)
        // }
        
        // 轮询视频生成状态
        // function pollVideoStatus(taskId, callback, maxAttempts = 60) {
        //     ... (已注释)
        // }
        
        // 请求生成场景视频
        // function requestSceneVideo(sceneDescription, sceneImage) {
        //     ... (已注释)
        // }
        
        // 提供占位函数，避免调用错误
        function displaySceneVideo(videoData) {
            // 视频功能已禁用，直接隐藏视频元素
            const sceneVideo = document.getElementById('scene-video');
            if (sceneVideo) sceneVideo.style.display = 'none';
        }
        
        function requestSceneVideo(sceneDescription, sceneImage) {
            // 视频功能已禁用，不执行任何操作
            return;
        }
        
        return {
            displaySceneImage,
            displaySceneVideo,  // 保留占位函数
            preloadImage,
            requestSceneVideo  // 保留占位函数
        };
    })();
    
    // 初始化游戏状态
    function initGameState() {
        gameState = {
            currentScreen: 'menu',
            selectedDifficulty: null,
            selectedTone: null,
            protagonistAttr: {
                颜值: '普通',
                智商: '普通',
                体力: '普通',
                魅力: '普通'
            },
            gameTheme: '',
            imageStyle: null, // 图片风格选择
            currentScene: null,
            lastSceneImage: null, // 上一剧情图片（用于“下一剧情参考上一剧情图片生成”）
            currentOptions: [],
            selectedSave: null,
            chapterProgress: 0, // 章节进度（0%-100%）
            unlockedDeepBackgrounds: [], // 已解锁的深层背景
            currentTone: 'normal_ending', // 当前结局基调，默认普通结局
            currentSceneId: null, // 当前场景ID，用于缓存查找
            isLoadedGame: false, // 是否是从加载开始的游戏
            loadedSaveName: null, // 如果是从加载开始的，记录加载的存档名称
            currentTypeInterval: null, // 当前打字机动画的interval，用于清理防止重复
            textSegments: [], // 文本分段数组，每段1-2句话
            currentTextSegmentIndex: 0, // 当前显示的段落索引
            isShowingSegments: false, // 是否处于分段显示状态
            pendingOptions: null, // 待显示的选项（在所有段落显示完成后显示）
            pendingImageData: null, // 待显示的图片数据（在分段显示过程中保持不变）
            gameData: {
                core_worldview: {}, // 与后端一致的命名
                flow_worldline: {}, // 与后端一致的命名
                hidden_ending_prediction: { // 结局预测，与后端一致
                    main_tone: 'NE',
                    content: ''
                }
            }
        };
    }
    
    // 初始化DOM元素
    function initElements() {
        elements = {
            screens: {
                menu: document.getElementById('menu-screen'),
                attrSelection: document.getElementById('attr-selection-screen'),
                difficultySelection: document.getElementById('difficulty-selection-screen'),
                toneSelection: document.getElementById('tone-selection-screen'),
                themeInput: document.getElementById('theme-input-screen'),
                imageStyleSelection: document.getElementById('image-style-selection-screen'),
                setting: document.getElementById('setting-screen'),
                loading: document.getElementById('loading-screen'),
                gameplay: document.getElementById('gameplay-screen'),
                saveManagement: document.getElementById('save-management-screen'),
                ending: document.getElementById('ending-screen')
            },
            buttons: {
                start: document.getElementById('start-btn'),
                load: document.getElementById('load-btn'),
                saveManage: document.getElementById('save-manage-btn'),
                exit: document.getElementById('exit-btn'),
                confirmAttr: document.getElementById('confirm-attr-btn'),
                resetAttr: document.getElementById('reset-attr-btn'),
                confirmDifficulty: document.getElementById('confirm-difficulty-btn'),
                confirmTone: document.getElementById('confirm-tone-btn'),
                submitTheme: document.getElementById('submit-theme-btn'),
                confirmStyle: document.getElementById('confirm-style-btn'),
                startGame: document.getElementById('start-game-btn'),
                loadSelectedSave: document.getElementById('load-selected-save-btn'),
                deleteSelectedSave: document.getElementById('delete-selected-save-btn'),
                backToMenu: document.getElementById('back-to-menu-btn'),
                restartGame: document.getElementById('restart-game-btn')
            },
            inputs: {
                theme: document.getElementById('theme-input'),
                customStyle: document.getElementById('custom-style-text')
            },
            content: {
                wordCount: document.querySelector('.word-count'),
                settingTabs: document.querySelectorAll('.nav-item'),
                settingTabContents: document.querySelectorAll('.content-tab'),
                gameStyle: document.getElementById('game-style-content'),
                worldview: document.getElementById('worldview-content'),
                protagonistAbility: document.getElementById('protagonist-ability-content'),
                chapterConflict: document.getElementById('chapter-conflict-content'),
                loadingStatus: document.getElementById('loading-status'),
                loadingPercent: document.getElementById('loading-percent'),
                sceneText: document.getElementById('scene-text'),  // 旁白文案元素
                optionsList: document.getElementById('options-list'),
                progressFill: document.querySelector('.progress-fill'),
                progressNodes: document.querySelectorAll('.progress-node'),
                currentChapterText: document.querySelector('.current-chapter'),
                coreConflictText: document.querySelector('.core-conflict'),
                conflictStatusText: document.querySelector('.conflict-status'),
                endingTitle: document.getElementById('ending-title'),
                endingContent: document.getElementById('ending-content'),
                endingSummary: document.getElementById('ending-summary')
            },
            modal: {
                container: document.getElementById('modal'),
                content: document.getElementById('modal-content'),
                title: document.getElementById('modal-title'),
                text: document.getElementById('modal-text'),
                confirm: document.getElementById('modal-confirm'),
                cancel: document.getElementById('modal-cancel'),
                close: document.querySelector('.close-modal')
            },
            globalBg: document.getElementById('global-bg')
        };
    }
    
    // 屏幕切换函数（带淡入淡出动画300ms）
    function switchScreen(screenName) {
        // 安全检查
        if (!elements || !elements.screens) {
            console.error('switchScreen错误：elements.screens 不存在');
            return;
        }
        
        // 隐藏所有屏幕（淡出）
        Object.values(elements.screens).forEach(screen => {
            if (screen && screen.classList) {
                screen.classList.add('hidden');
                screen.style.opacity = '0';
                screen.style.transition = 'opacity 300ms ease';
            }
        });
        
        // 显示目标屏幕（淡入）
        const targetScreen = elements.screens[screenName];
        if (targetScreen && targetScreen.classList) {
            targetScreen.classList.remove('hidden');
            setTimeout(() => {
                targetScreen.style.opacity = '1';
            }, 50);
            gameState.currentScreen = screenName;
            
            // 特殊处理：主题输入屏清空输入
            if (screenName === 'themeInput' && elements.inputs && elements.inputs.theme) {
                elements.inputs.theme.value = '';
                if (typeof updateWordCount === 'function') {
                    updateWordCount();
                }
            }
            
            // 特殊处理：图片风格选择屏重置状态
            if (screenName === 'imageStyleSelection') {
                // 重置所有选择状态
                selectedStyle = null;
                selectedSubStyle = null;
                customStyleText = '';
                
                // 重置按钮状态
                document.querySelectorAll('.style-btn').forEach(b => {
                    b.classList.remove('ring-4', 'ring-white');
                });
                document.querySelectorAll('.submenu-btn').forEach(b => {
                    b.classList.remove('ring-4', 'ring-white');
                });
                
                // 隐藏子菜单
                document.getElementById('oil-painting-submenu').classList.add('hidden');
                document.getElementById('custom-style-input').classList.add('hidden');
                
                // 重置显示和按钮
                document.getElementById('selected-style-display').textContent = '请选择一个风格';
                if (elements.buttons.confirmStyle) {
                    elements.buttons.confirmStyle.disabled = true;
                    elements.buttons.confirmStyle.classList.add('cursor-not-allowed');
                    elements.buttons.confirmStyle.classList.remove('bg-[#1ABC9C]', 'hover:bg-[#16A085]');
                }
                
                // 清空自定义输入框
                if (elements.inputs && elements.inputs.customStyle) {
                    elements.inputs.customStyle.value = '';
                }
            }
            
            // 特殊处理：存档管理屏加载存档
            if (screenName === 'saveManagement' && typeof loadSaves === 'function') {
                loadSaves();
            }
            
            // 特殊处理：游戏界面显示角色面板
            const characterPanel = document.getElementById('character-panel');
            if (screenName === 'gameplay' && characterPanel) {
                characterPanel.style.display = 'block';
            }
        } else {
            console.error(`switchScreen错误：找不到屏幕 ${screenName}`);
        }
        
        // 播放音效
        playSound('switch');
    }
    
    // 字数统计更新
    function updateWordCount() {
        const text = elements.inputs.theme.value;
        const length = text.length;
        const maxLength = 20;
        
        elements.content.wordCount.textContent = `${length}/${maxLength}`;
        
        // 字数颜色更新
        if (length > maxLength) {
            elements.content.wordCount.className = 'word-count text-[14px] text-red-500';
            elements.inputs.theme.value = text.substring(0, maxLength);
            updateWordCount();
        } else {
            elements.content.wordCount.className = 'word-count text-[14px] text-white';
        }
    }
    
    // 重置属性
    function resetAttributes() {
        gameState.protagonistAttr = {
            颜值: '普通',
            智商: '普通',
            体力: '普通',
            魅力: '普通'
        };
        
        // 重置所有属性选项的样式
        document.querySelectorAll('.attr-option-btn').forEach(btn => {
            btn.className = 'attr-option-btn px-4 py-2 rounded-lg bg-[#7F8C8D] text-white transition-all hover:bg-[#95A5A6]';
        });
        
        // 设置默认选项为选中状态
        document.querySelectorAll('.attr-options').forEach(options => {
            const defaultOption = options.querySelector('[data-value="普通"]');
            if (defaultOption) {
                defaultOption.className = 'attr-option-btn px-4 py-2 rounded-lg bg-[#3498DB] text-white transition-all hover:bg-[#2980B9]';
            }
        });
        
        playSound('reset');
    }
    
    // 生成游戏世界观
    async function generateGameWorldview() {
        try {
            // 重置加载游戏标志（新游戏）
            gameState.isLoadedGame = false;
            gameState.loadedSaveName = null;
            
            // 显示加载状态
            elements.content.gameStyle.innerHTML = '生成中...';
            elements.content.worldview.innerHTML = '生成中...';
            elements.content.protagonistAbility.innerHTML = '<span class="highlight">生成中...</span>';
            elements.content.chapterConflict.innerHTML = '生成中...';
            
            // 调用后端API生成游戏世界观
            let response;
            try {
                response = await fetch('http://127.0.0.1:5001/generate-worldview', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        gameTheme: gameState.gameTheme,
                        protagonistAttr: gameState.protagonistAttr,
                        difficulty: gameState.selectedDifficulty,
                        toneKey: gameState.selectedTone,
                        imageStyle: gameState.imageStyle
                    }),
                    // 增加超时设置
                    signal: AbortSignal.timeout(300000) // 5分钟超时
                });
            } catch (fetchError) {
                // 处理网络连接错误
                let errorMessage = '无法连接到后端服务器。';
                if (fetchError.name === 'TimeoutError') {
                    errorMessage = '请求超时，后端服务器响应时间过长。请检查后端服务是否正常运行，或稍后重试。';
                } else if (fetchError.name === 'TypeError' && fetchError.message.includes('fetch')) {
                    errorMessage = '网络连接失败。请确认：\n1. 后端服务器是否已启动（运行 game_server.py）\n2. 服务器是否运行在 http://127.0.0.1:5001\n3. 防火墙是否阻止了连接';
                } else {
                    errorMessage = `连接错误：${fetchError.message}`;
                }
                showModal('连接错误', errorMessage, () => {});
                throw fetchError; // 重新抛出，让外层catch处理
            }
            
            // 检查HTTP状态码
            if (!response.ok) {
                const errorText = await response.text();
                let errorMessage = `服务器错误 (HTTP ${response.status})`;
                try {
                    const errorJson = JSON.parse(errorText);
                    errorMessage = errorJson.message || errorMessage;
                } catch (e) {
                    errorMessage = errorText || errorMessage;
                }
                showModal('服务器错误', errorMessage, () => {});
                throw new Error(errorMessage);
            }
            
            const result = await response.json();
            
            // 添加调试日志
            console.log('📥 收到后端响应:', result);
            console.log('📦 globalState 数据:', result.globalState);
            
            if (result.status === 'success') {
                // 更新游戏状态
                if (!result.globalState) {
                    throw new Error('后端返回的数据中缺少 globalState 字段');
                }
                
                gameState.gameData = result.globalState;
                
                // 验证数据结构完整性
                if (!gameState.gameData || !gameState.gameData.core_worldview) {
                    console.error('❌ 数据结构验证失败:', gameState.gameData);
                    throw new Error('返回的世界观数据格式不正确：缺少 core_worldview');
                }
                
                console.log('✅ 世界观数据验证通过:', gameState.gameData.core_worldview);
                
                const worldview = gameState.gameData.core_worldview;
                
                // 确保必要字段存在，如果缺失则使用默认值
                if (!worldview.game_style) worldview.game_style = gameState.gameTheme || '奇幻冒险';
                if (!worldview.world_basic_setting) worldview.world_basic_setting = `在一个充满奇幻色彩的${gameState.gameTheme}世界中，古老的预言正在悄然应验，你将踏上一段改变命运的旅程`;
                if (!worldview.protagonist_ability) worldview.protagonist_ability = `颜值${gameState.protagonistAttr.颜值}、智商${gameState.protagonistAttr.智商}、体力${gameState.protagonistAttr.体力}、魅力${gameState.protagonistAttr.魅力}`;
                
                // 确保 chapters 存在
                if (!worldview.chapters) {
                    worldview.chapters = {};
                }
                
                // 确保 chapter1 存在
                if (!worldview.chapters.chapter1) {
                    worldview.chapters.chapter1 = {
                        main_conflict: '开始你的冒险之旅，探索未知的世界',
                        conflict_end_condition: '完成初步探索，获得关键线索'
                    };
                }
                
                // 确保 chapter1 的必要字段存在
                if (!worldview.chapters.chapter1.main_conflict) {
                    worldview.chapters.chapter1.main_conflict = '开始你的冒险之旅，探索未知的世界';
                }
                if (!worldview.chapters.chapter1.conflict_end_condition) {
                    worldview.chapters.chapter1.conflict_end_condition = '完成初步探索，获得关键线索';
                }
                
                // 确保其他章节也存在（如果缺失则创建）
                if (!worldview.chapters.chapter2) {
                    worldview.chapters.chapter2 = {
                        main_conflict: '深入探索，面对更大的挑战',
                        conflict_end_condition: '克服困难，获得进展'
                    };
                }
                if (!worldview.chapters.chapter3) {
                    worldview.chapters.chapter3 = {
                        main_conflict: '最终决战，决定命运的时刻',
                        conflict_end_condition: '完成最终目标，达成结局'
                    };
                }
                
                // 更新设定界面内容
                console.log('🎨 开始更新UI界面...');
                console.log('   - game_style:', worldview.game_style);
                console.log('   - world_basic_setting:', worldview.world_basic_setting?.substring(0, 50) + '...');
                console.log('   - protagonist_ability:', worldview.protagonist_ability);
                console.log('   - chapter1:', worldview.chapters.chapter1);
                
                // 辅助函数：清理Markdown格式并转义HTML
                function cleanText(text) {
                    if (!text) return '未设置';
                    // 移除Markdown加粗标记 **text** -> text
                    text = text.replace(/\*\*(.*?)\*\*/g, '$1');
                    // 移除Markdown斜体标记 *text* -> text
                    text = text.replace(/\*(.*?)\*/g, '$1');
                    // 转义HTML特殊字符，防止XSS
                    const div = document.createElement('div');
                    div.textContent = text;
                    return div.innerHTML;
                }
                
                // 验证UI元素是否存在
                if (!elements.content.gameStyle) {
                    console.error('❌ 找不到 gameStyle 元素');
                } else {
                    const gameStyleText = cleanText(worldview.game_style);
                    elements.content.gameStyle.innerHTML = gameStyleText;
                    console.log('✅ gameStyle 已更新:', gameStyleText);
                }
                
                if (!elements.content.worldview) {
                    console.error('❌ 找不到 worldview 元素');
                } else {
                    const worldviewText = cleanText(worldview.world_basic_setting);
                    elements.content.worldview.innerHTML = worldviewText;
                    console.log('✅ worldview 已更新:', worldviewText.substring(0, 50) + '...');
                }
                
                if (!elements.content.protagonistAbility) {
                    console.error('❌ 找不到 protagonistAbility 元素');
                } else {
                    const abilityText = cleanText(worldview.protagonist_ability);
                    elements.content.protagonistAbility.innerHTML = `<span class="highlight">${abilityText}</span>`;
                    console.log('✅ protagonistAbility 已更新:', abilityText);
                }
                
                const chapter1 = worldview.chapters.chapter1;
                if (!elements.content.chapterConflict) {
                    console.error('❌ 找不到 chapterConflict 元素');
                } else {
                    if (chapter1 && chapter1.main_conflict && chapter1.conflict_end_condition) {
                        const conflictText = cleanText(chapter1.main_conflict);
                        const endConditionText = cleanText(chapter1.conflict_end_condition);
                        elements.content.chapterConflict.innerHTML = `${conflictText}（结束条件：<span class="highlight">${endConditionText}</span>）`;
                        console.log('✅ chapterConflict 已更新');
                    } else {
                        elements.content.chapterConflict.innerHTML = '章节信息未完整生成';
                        console.warn('⚠️ chapter1 数据不完整:', chapter1);
                    }
                }
                
                console.log('✅ UI界面更新完成');
                
                // 验证更新后的内容
                console.log('🔍 验证更新后的内容:');
                console.log('   - gameStyle元素内容:', elements.content.gameStyle?.textContent);
                console.log('   - worldview元素内容:', elements.content.worldview?.textContent?.substring(0, 50));
                console.log('   - protagonistAbility元素内容:', elements.content.protagonistAbility?.textContent);
                console.log('   - chapterConflict元素内容:', elements.content.chapterConflict?.textContent?.substring(0, 50));
                
                // 显示成功提示
                showModal('成功', '世界观生成成功！', () => {});
            } else {
                // 处理错误
                showModal('提示', result.message, () => {});
                
                // 使用默认数据
                gameState.gameData = {
                    core_worldview: {
                        game_style: gameState.gameTheme || '奇幻冒险',
                        world_basic_setting: `在一个充满奇幻色彩的${gameState.gameTheme}世界中，古老的预言正在悄然应验，你将踏上一段改变命运的旅程`,
                        protagonist_ability: `颜值${gameState.protagonistAttr.颜值}、智商${gameState.protagonistAttr.智商}、体力${gameState.protagonistAttr.体力}、魅力${gameState.protagonistAttr.魅力}`,
                        characters: {
                            主角: {
                                core_personality: '勇敢果断，充满好奇心',
                                shallow_background: '你是一名普通的冒险者，渴望探索未知的世界',
                                deep_background: '曾是皇家密探，因遭陷害隐姓埋名，体内隐藏着神器守护者的血脉'
                            },
                            配角1: {
                                core_personality: '聪明机智，善于谋划',
                                shallow_background: '你遇到的第一个伙伴，是一名经验丰富的向导',
                                deep_background: '表面是向导，实际是神秘组织成员，寻找神器是为了阻止灾难'
                            }
                        },
                        forces: {
                            positive: ['光明势力', '冒险者公会'],
                            negative: ['黑暗军团', '邪恶巫师'],
                            neutral: ['商人联盟', '流浪部落']
                        },
                        main_quest: `在${gameState.gameTheme}世界中，收集上古神器碎片，阻止黑暗势力毁灭世界`,
                        chapters: {
                            chapter1: {
                                main_conflict: '寻找失窃的上古神器，阻止黑暗势力复苏',
                                conflict_end_condition: '找到神器线索并击败第一个守护者'
                            },
                            chapter2: {
                                main_conflict: '揭露盟友中的内奸，保护神器不被夺走',
                                conflict_end_condition: '找出内奸并获得真正盟友的信任'
                            },
                            chapter3: {
                                main_conflict: '最终决战，击败黑暗势力首领',
                                conflict_end_condition: '成功封印黑暗势力，恢复世界和平'
                            }
                        },
                        end_trigger_condition: '完成所有章节或选择结束游戏选项'
                    },
                    flow_worldline: {
                        current_chapter: 'chapter1',
                        tone: gameState.selectedTone || 'normal_ending',
                        characters: {
                            主角: {
                                thought: '我必须勇敢地面对挑战',
                                physiology: '健康',
                                deep_background_unlocked: false,
                                deep_background_depth: 0
                            },
                            配角1: {
                                thought: '这个年轻人看起来很有潜力',
                                physiology: '健康',
                                deep_background_unlocked: false,
                                deep_background_depth: 0
                            }
                        },
                        environment: {
                            location: '迷雾森林入口',
                            weather: '小雨',
                            force_relationship: '中立'
                        },
                        quest_progress: '刚刚进入迷雾森林，寻找神器的第一个线索',
                        chapter_conflict_solved: false,
                        info_gap_record: {
                            entries: [],
                            current_super_choice: null,
                            pending_super_plot: null
                        }
                    },
                    hidden_ending_prediction: {
                        main_tone: 'NE',
                        content: '主角完成了主要任务，虽然过程中经历了许多困难，但最终达成了预期目标'
                    }
                };
                
                // 更新设定界面内容
                elements.content.gameStyle.innerHTML = gameState.gameData.core_worldview.game_style;
                elements.content.worldview.innerHTML = gameState.gameData.core_worldview.world_basic_setting;
                elements.content.protagonistAbility.innerHTML = `<span class="highlight">${gameState.gameData.core_worldview.protagonist_ability}</span>`;
                elements.content.chapterConflict.innerHTML = `${gameState.gameData.core_worldview.chapters.chapter1.main_conflict}（结束条件：<span class="highlight">${gameState.gameData.core_worldview.chapters.chapter1.conflict_end_condition}</span>）`;
            }
        } catch (error) {
            // 处理网络错误（如果还没有显示错误信息，则显示通用错误）
            if (error.name !== 'AbortError' && !error.message.includes('服务器错误')) {
                let errorMessage = '世界观生成失败。';
                if (error.name === 'TimeoutError') {
                    errorMessage = '请求超时，后端服务器响应时间过长。请检查后端服务是否正常运行，或稍后重试。';
                } else if (error.name === 'TypeError' && error.message.includes('fetch')) {
                    errorMessage = '网络连接失败。请确认：\n1. 后端服务器是否已启动（运行 game_server.py）\n2. 服务器是否运行在 http://127.0.0.1:5001\n3. 防火墙是否阻止了连接';
                } else {
                    errorMessage = `生成失败：${error.message || '未知错误'}`;
                }
                showModal('生成失败', errorMessage, () => {});
            }
            
            // 使用默认数据
            gameState.gameData = {
                core_worldview: {
                    game_style: gameState.gameTheme || '奇幻冒险',
                    world_basic_setting: `在一个充满奇幻色彩的${gameState.gameTheme}世界中，古老的预言正在悄然应验，你将踏上一段改变命运的旅程`,
                    protagonist_ability: `颜值${gameState.protagonistAttr.颜值}、智商${gameState.protagonistAttr.智商}、体力${gameState.protagonistAttr.体力}、魅力${gameState.protagonistAttr.魅力}`,
                    characters: {
                        主角: {
                            core_personality: '勇敢果断，充满好奇心',
                            shallow_background: '你是一名普通的冒险者，渴望探索未知的世界',
                            deep_background: '曾是皇家密探，因遭陷害隐姓埋名，体内隐藏着神器守护者的血脉'
                        },
                        配角1: {
                            core_personality: '聪明机智，善于谋划',
                            shallow_background: '你遇到的第一个伙伴，是一名经验丰富的向导',
                            deep_background: '表面是向导，实际是神秘组织成员，寻找神器是为了阻止灾难'
                        }
                    },
                    forces: {
                        positive: ['光明势力', '冒险者公会'],
                        negative: ['黑暗军团', '邪恶巫师'],
                        neutral: ['商人联盟', '流浪部落']
                    },
                    main_quest: `在${gameState.gameTheme}世界中，收集上古神器碎片，阻止黑暗势力毁灭世界`,
                    chapters: {
                        chapter1: {
                            main_conflict: '寻找失窃的上古神器，阻止黑暗势力复苏',
                            conflict_end_condition: '找到神器线索并击败第一个守护者'
                        },
                        chapter2: {
                            main_conflict: '揭露盟友中的内奸，保护神器不被夺走',
                            conflict_end_condition: '找出内奸并获得真正盟友的信任'
                        },
                        chapter3: {
                            main_conflict: '最终决战，击败黑暗势力首领',
                            conflict_end_condition: '成功封印黑暗势力，恢复世界和平'
                        }
                    },
                    end_trigger_condition: '完成所有章节或选择结束游戏选项'
                },
                flow_worldline: {
                    current_chapter: 'chapter1',
                    tone: gameState.selectedTone || 'normal_ending',
                    characters: {
                        主角: {
                            thought: '我必须勇敢地面对挑战',
                            physiology: '健康',
                            deep_background_unlocked: false,
                            deep_background_depth: 0
                        },
                        配角1: {
                            thought: '这个年轻人看起来很有潜力',
                            physiology: '健康',
                            deep_background_unlocked: false,
                            deep_background_depth: 0
                        }
                    },
                    environment: {
                        location: '迷雾森林入口',
                        weather: '小雨',
                        force_relationship: '中立'
                    },
                    quest_progress: '刚刚进入迷雾森林，寻找神器的第一个线索',
                    chapter_conflict_solved: false,
                    info_gap_record: {
                        entries: [],
                        current_super_choice: null,
                        pending_super_plot: null
                    }
                },
                hidden_ending_prediction: {
                    main_tone: 'NE',
                    content: '主角完成了主要任务，虽然过程中经历了许多困难，但最终达成了预期目标'
                }
            };
            
            // 更新设定界面内容
            elements.content.gameStyle.innerHTML = gameState.gameData.core_worldview.game_style;
            elements.content.worldview.innerHTML = gameState.gameData.core_worldview.world_basic_setting;
            elements.content.protagonistAbility.innerHTML = `<span class="highlight">${gameState.gameData.core_worldview.protagonist_ability}</span>`;
            elements.content.chapterConflict.innerHTML = `${gameState.gameData.core_worldview.chapters.chapter1.main_conflict}（结束条件：<span class="highlight">${gameState.gameData.core_worldview.chapters.chapter1.conflict_end_condition}</span>）`;
        }
    }
    
    // 模拟加载过程
    function simulateLoading() {
        let progress = 0;
        const loadingSteps = [
            '生成世界观...',
            '构建初始场景...',
            '生成角色关系...',
            '加载完成'
        ];
        const stepDuration = 1500;
        let currentStep = 0;
        
        // 重置加载状态
        elements.content.loadingStatus.textContent = loadingSteps[currentStep];
        elements.content.loadingPercent.textContent = '0%';
        elements.globalBg.style.opacity = '0.2';
        
        const loadingInterval = setInterval(() => {
            progress += 1;
            elements.content.loadingPercent.textContent = `${progress}%`;
            
            // 进度条动画
            elements.content.progressFill.style.width = `${progress}%`;
            
            // 切换加载文本
            if (progress % 25 === 0 && currentStep < loadingSteps.length - 1) {
                currentStep++;
                elements.content.loadingStatus.textContent = loadingSteps[currentStep];
                playSound('load');
            }
            
            // 加载至50%时背景开始淡入
            if (progress === 50) {
                elements.globalBg.style.opacity = '0.6';
                elements.globalBg.style.transition = 'opacity 1s ease';
            }
            
            // 加载完成
            if (progress === 100) {
                clearInterval(loadingInterval);
                // 环形图标放大消失动画
                const spinner = document.querySelector('.loading-spinner');
                spinner.style.transform = 'scale(1.5)';
                spinner.style.opacity = '0';
                spinner.style.transition = 'all 500ms ease';
                
                // 文本渐隐
                elements.content.loadingStatus.style.opacity = '0';
                elements.content.loadingPercent.style.opacity = '0';
                
                setTimeout(() => {
                    switchScreen('setting');
                }, 500);
            }
        }, 30);
    }
    
    // 模拟游戏加载（进入剧情）
    function simulateGameLoading() {
        // 应用字体（根据风格和基调）
        FontManager.applyFontToGame(gameState.imageStyle, gameState.tone);
        
        let progress = 0;
        elements.content.loadingStatus.textContent = '加载剧情场景...';
        elements.content.loadingPercent.textContent = '0%';
        
        const loadingInterval = setInterval(() => {
            progress += 2;
            elements.content.loadingPercent.textContent = `${progress}%`;
            elements.content.progressFill.style.width = `${progress}%`;
            
            if (progress === 100) {
                clearInterval(loadingInterval);
                setTimeout(async () => {
                    // 先检查并展示主角形象（如果已生成）
                    await showMainCharacterIfReady(() => {
                        // 主角形象展示完成后，继续原有流程
                        continueToFirstScene();
                    });
                }, 500);
            }
        });
    }
    
    // 继续到第一次场景的流程
    async function continueToFirstScene() {
        switchScreen('gameplay');
        
        // 更新章节信息
        const flowWorldline = gameState.gameData.flow_worldline;
        const currentChapter = flowWorldline.current_chapter || 'chapter1';
        const coreWorldview = gameState.gameData.core_worldview || {};
        const chapters = coreWorldview.chapters || {};
        const chapterInfo = chapters[currentChapter] || {};
        
        // 更新当前章节文本
        if (elements.content.currentChapterText) {
            elements.content.currentChapterText.textContent = `${currentChapter === 'chapter1' ? '第一章' : currentChapter === 'chapter2' ? '第二章' : '第三章'}：${chapterInfo.main_conflict || '探索中'}`;
        }
        
        // 更新核心矛盾文本
        if (elements.content.coreConflictText) {
            elements.content.coreConflictText.textContent = chapterInfo.main_conflict || '核心矛盾未定义';
        }
        
        // 显示加载指示器
        // 已移除scene-container，不再需要
        const loadingIndicator = document.createElement('div');
        loadingIndicator.className = 'loading-overlay flex items-center justify-center bg-black/70 fixed inset-0 z-50';
        loadingIndicator.innerHTML = `
            <div class="loading-content text-center">
                <div class="spinner animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
                <p class="text-white">生成初始剧情中...</p>
            </div>
        `;
        const gameplayScreen = document.getElementById('gameplay-screen');
        if (gameplayScreen) {
            gameplayScreen.appendChild(loadingIndicator);
        } else {
            // 如果找不到gameplay-screen，添加到body
            document.body.appendChild(loadingIndicator);
        }
        
        try {
            // 调用后端API生成初始场景和选项（初始场景不需要sceneId，因为没有缓存）
            // 添加超时控制（5分钟超时，因为图片生成最多需要6分钟）
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 300000); // 5分钟超时
            
            let response;
            try {
                response = await fetch('http://127.0.0.1:5001/generate-option', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        option: '开始游戏',
                        globalState: gameState.gameData,
                        optionIndex: 0,
                        sceneId: null  // 初始场景不需要sceneId
                    }),
                    signal: controller.signal
                });
            } catch (error) {
                clearTimeout(timeoutId);
                if (error.name === 'AbortError') {
                    throw new Error('请求超时（5分钟），请检查网络连接或稍后重试');
                }
                throw error;
            }
            
            clearTimeout(timeoutId);
            
            const result = await response.json();
            
            if (result.status === 'success') {
                const optionData = result.optionData;
                
                // 重要：验证后端返回的场景数据
                console.log('🔍 后端返回的optionData:', optionData);
                console.log('🔍 optionData.scene:', optionData.scene);
                console.log('🔍 optionData.scene类型:', typeof optionData.scene);
                console.log('🔍 optionData.scene长度:', optionData.scene ? optionData.scene.length : 0);
                
                // 使用后端生成的场景描述，而不是硬编码的简单场景
                // 检查场景是否为空字符串或无效
                let initialScene = optionData.scene;
                
                // 验证场景文本是否有效
                if (!initialScene || typeof initialScene !== 'string' || initialScene.trim() === '' || initialScene.length < 10) {
                    console.error('❌ 后端返回的初始场景无效:', {
                        scene: initialScene,
                        type: typeof initialScene,
                        length: initialScene ? initialScene.length : 0,
                        fullOptionData: JSON.stringify(optionData, null, 2)
                    });
                    
                    // 如果场景无效，等待一段时间后重试（最多重试2次）
                    let retryCount = 0;
                    const maxRetries = 2;
                    
                    // 初始化章节进度的辅助函数
                    const initializeChapterProgress = () => {
                        const initialProgress = Math.max(1, Math.min(3, Math.random() * 2 + 1));
                        gameState.chapterProgress = Math.round(initialProgress * 10) / 10;
                        if (gameState.gameData.flow_worldline) {
                            gameState.gameData.flow_worldline.chapter_progress = gameState.chapterProgress;
                        }
                        updateChapterProgress(gameState.chapterProgress);
                    };
                    
                    // 如果场景无效，等待一段时间后重试（最多重试2次）
                    const retryFunction = async () => {
                        retryCount++;
                        console.log(`🔄 重试获取初始场景... (${retryCount}/${maxRetries})`);
                        
                        setTimeout(async () => {
                            try {
                                // 添加超时控制（5分钟超时）
                                const retryController = new AbortController();
                                const retryTimeoutId = setTimeout(() => retryController.abort(), 300000);
                                
                                let retryResponse;
                                try {
                                    retryResponse = await fetch('http://127.0.0.1:5001/generate-option', {
                                        method: 'POST',
                                        headers: {
                                            'Content-Type': 'application/json'
                                        },
                                        body: JSON.stringify({
                                            option: '开始游戏',
                                            globalState: gameState.gameData,
                                            optionIndex: 0,
                                            sceneId: null
                                        }),
                                        signal: retryController.signal
                                    });
                                } catch (error) {
                                    clearTimeout(retryTimeoutId);
                                    if (error.name === 'AbortError') {
                                        throw new Error('重试请求超时（5分钟），请检查网络连接或稍后重试');
                                    }
                                    throw error;
                                }
                                
                                clearTimeout(retryTimeoutId);
                                const retryResult = await retryResponse.json();
                                if (retryResult.status === 'success' && retryResult.optionData.scene && retryResult.optionData.scene.trim().length >= 10) {
                                    const retryOptionData = retryResult.optionData;
                                    const retryScene = retryOptionData.scene;
                                    const retryOptions = retryOptionData.next_options || [
                                        '继续深入探索',
                                        '查看周围环境'
                                    ];
                                    const retrySceneImage = retryOptionData.scene_image || null;
                                    console.log('✅ 重试成功，使用后端生成的初始场景:', retryScene);
                                    
                                    // 更新游戏状态（如果有flow_update）
                                    if (gameState.gameData.flow_worldline && retryOptionData.flow_update) {
                                        const flowUpdate = retryOptionData.flow_update;
                                        
                                        // 更新章节进度
                                        if (flowUpdate.chapter_conflict_solved === true) {
                                            gameState.chapterProgress = 100;
                                            gameState.gameData.flow_worldline.chapter_progress = 100;
                                            updateChapterProgress(100);
                                        } else {
                                            // 确保chapterProgress已初始化，避免NaN计算
                                            if (gameState.chapterProgress === undefined || gameState.chapterProgress === null || isNaN(gameState.chapterProgress)) {
                                                initializeChapterProgress();
                                            }
                                            const remainingProgress = 100 - gameState.chapterProgress;
                                            const baseIncrement = Math.log(remainingProgress + 1) * 1.5;
                                            const randomFactor = 0.8 + Math.random() * 0.4;
                                            const progressIncrement = Math.max(0.5, Math.min(remainingProgress * 0.1, baseIncrement * randomFactor));
                                            const newProgress = Math.min(95, gameState.chapterProgress + progressIncrement);
                                            gameState.chapterProgress = Math.round(newProgress * 10) / 10;
                                            gameState.gameData.flow_worldline.chapter_progress = gameState.chapterProgress;
                                            updateChapterProgress(gameState.chapterProgress);
                                        }
                                        // 保存已计算的chapter_progress，防止被flowUpdate覆盖
                                        const preservedChapterProgress = gameState.gameData.flow_worldline.chapter_progress;
                                        Object.assign(gameState.gameData.flow_worldline, flowUpdate);
                                        // 恢复已计算的chapter_progress，确保与gameState.chapterProgress同步
                                        if (preservedChapterProgress !== undefined && preservedChapterProgress !== null) {
                                            gameState.gameData.flow_worldline.chapter_progress = preservedChapterProgress;
                                        }
                                    } else if (gameState.gameData.flow_worldline) {
                                        // 即使没有flow_update，初始场景生成后也应该有初始进度
                                        initializeChapterProgress();
                                    } else {
                                        // 如果没有flow_worldline，也初始化进度
                                        initializeChapterProgress();
                                    }
                                    
                                    // 安全移除加载指示器（如果还存在）
                                    if (loadingIndicator && loadingIndicator.parentNode) {
                                        loadingIndicator.remove();
                                    }
                                    displayScene(retryScene, retryOptions, retrySceneImage, null);
                                } else {
                                    // 重试失败，检查是否还有重试次数
                                    if (retryCount < maxRetries) {
                                        console.log(`⚠️ 重试 ${retryCount} 失败，继续重试...`);
                                        retryFunction(); // 递归重试
                                        return;
                                    }
                                    
                                    // 已达到最大重试次数，使用备用场景
                                    const flowWorldline = gameState.gameData.flow_worldline;
                                    const environment = flowWorldline ? flowWorldline.environment || {} : {};
                                    const location = environment.location || '未知地点';
                                    const weather = environment.weather || '晴朗';
                                    const questProgress = flowWorldline ? (flowWorldline.quest_progress || '') : '';
                                    const fallbackScene = `你站在${location}，${weather}。${questProgress}`;
                                    const fallbackOptions = [
                                        '继续深入探索',
                                        '查看周围环境'
                                    ];
                                    console.warn('⚠️ 重试失败，使用备用场景');
                                    initializeChapterProgress(); // 初始化章节进度
                                    // 安全移除加载指示器（如果还存在）
                                    if (loadingIndicator && loadingIndicator.parentNode) {
                                        loadingIndicator.remove();
                                    }
                                    displayScene(fallbackScene, fallbackOptions);
                                }
                            } catch (error) {
                                console.error('❌ 重试API调用异常:', error);
                                
                                // 检查是否还有重试次数
                                if (retryCount < maxRetries) {
                                    console.log(`⚠️ 重试 ${retryCount} 异常，继续重试...`);
                                    retryFunction(); // 递归重试
                                    return;
                                }
                                
                                // 已达到最大重试次数，使用备用场景
                                const flowWorldline = gameState.gameData.flow_worldline;
                                const environment = flowWorldline ? flowWorldline.environment || {} : {};
                                const location = environment.location || '未知地点';
                                const weather = environment.weather || '晴朗';
                                const questProgress = flowWorldline ? (flowWorldline.quest_progress || '') : '';
                                const fallbackScene = `你站在${location}，${weather}。${questProgress}`;
                                const fallbackOptions = [
                                    '继续深入探索',
                                    '查看周围环境'
                                ];
                                initializeChapterProgress(); // 初始化章节进度
                                // 安全移除加载指示器（如果还存在）
                                if (loadingIndicator && loadingIndicator.parentNode) {
                                    loadingIndicator.remove();
                                }
                                displayScene(fallbackScene, fallbackOptions);
                            }
                        }, 2000); // 等待2秒后重试
                    };
                    
                    retryFunction();
                    return; // 退出当前函数，等待重试
                }
                
                // 场景验证通过，移除加载指示器
                loadingIndicator.remove();
                
                let initialOptions = optionData.next_options || [
                    '继续深入探索',
                    '查看周围环境'
                ];
                
                // 限制选项数量为2个
                if (initialOptions.length > 2) {
                    initialOptions = initialOptions.slice(0, 2);
                }
                
                // 验证选项是否有效
                if (!initialOptions || !Array.isArray(initialOptions) || initialOptions.length === 0) {
                    console.warn('⚠️ 后端返回的初始选项无效，使用默认选项');
                    initialOptions = [
                        '继续深入探索',
                        '查看周围环境',
                        '检查角色状态',
                        '了解当前任务'
                    ];
                }
                
                console.log('✅ 使用后端生成的初始场景');
                console.log('   - 场景长度:', initialScene.length);
                console.log('   - 场景预览:', initialScene.substring(0, 100) + '...');
                console.log('   - 选项数量:', initialOptions.length);
                console.log('   - 选项列表:', initialOptions);
                
                // 更新游戏状态（如果有flow_update）
                if (gameState.gameData.flow_worldline && optionData.flow_update) {
                    const flowUpdate = optionData.flow_update;
                    
                    // 更新章节进度
                    if (flowUpdate.chapter_conflict_solved === true) {
                        // 章节矛盾已解决，进度设为100%
                        gameState.chapterProgress = 100;
                        gameState.gameData.flow_worldline.chapter_progress = 100;
                        updateChapterProgress(100);
                    } else {
                        // 确保chapterProgress已初始化，避免NaN计算
                        if (gameState.chapterProgress === undefined || gameState.chapterProgress === null || isNaN(gameState.chapterProgress)) {
                            // 初始进度设为1-3%（表示游戏开始）
                            const initialProgress = Math.max(1, Math.min(3, Math.random() * 2 + 1));
                            gameState.chapterProgress = Math.round(initialProgress * 10) / 10;
                            if (gameState.gameData.flow_worldline) {
                                gameState.gameData.flow_worldline.chapter_progress = gameState.chapterProgress;
                            }
                            updateChapterProgress(gameState.chapterProgress);
                        }
                        // 根据当前进度在到达结局之前的占比来确定进度更新
                        // 距离100%越近，每次增加的进度越少
                        const remainingProgress = 100 - gameState.chapterProgress;
                        // 基础增量：根据剩余进度计算，剩余越多增加越多
                        // 使用对数函数使进度增长更平滑：log(剩余进度 + 1) * 系数
                        const baseIncrement = Math.log(remainingProgress + 1) * 1.5;
                        // 添加一些随机性（±20%）
                        const randomFactor = 0.8 + Math.random() * 0.4;
                        const progressIncrement = Math.max(0.5, Math.min(remainingProgress * 0.1, baseIncrement * randomFactor));
                        const newProgress = Math.min(95, gameState.chapterProgress + progressIncrement);
                        gameState.chapterProgress = Math.round(newProgress * 10) / 10; // 保留一位小数
                        gameState.gameData.flow_worldline.chapter_progress = gameState.chapterProgress;
                        updateChapterProgress(gameState.chapterProgress);
                    }
                    // 保存已计算的chapter_progress，防止被flowUpdate覆盖
                    const preservedChapterProgress = gameState.gameData.flow_worldline.chapter_progress;
                    Object.assign(gameState.gameData.flow_worldline, flowUpdate);
                    // 恢复已计算的chapter_progress，确保与gameState.chapterProgress同步
                    if (preservedChapterProgress !== undefined && preservedChapterProgress !== null) {
                        gameState.gameData.flow_worldline.chapter_progress = preservedChapterProgress;
                    }
                } else if (gameState.gameData.flow_worldline) {
                    // 即使没有flow_update，初始场景生成后也应该有初始进度
                    // 初始进度设为1-3%（表示游戏开始）
                    const initialProgress = Math.max(1, Math.min(3, Math.random() * 2 + 1));
                    gameState.chapterProgress = Math.round(initialProgress * 10) / 10;
                    gameState.gameData.flow_worldline.chapter_progress = gameState.chapterProgress;
                    updateChapterProgress(gameState.chapterProgress);
                }
                
                // displayScene会自动触发预生成
                // 提取视觉内容数据
                let sceneImage = optionData.scene_image || null;
                // const sceneVideo = optionData.scene_video || null;  // 视频功能已禁用
                
                // 问题5修复：验证初始场景的图片数据格式
                console.log('🔍 初始场景 - 场景图片数据:', sceneImage);
                let validatedSceneImage = null;
                if (sceneImage) {
                    // 验证数据格式
                    if (typeof sceneImage === 'string') {
                        console.warn('⚠️ sceneImage是字符串，转换为对象格式');
                        validatedSceneImage = { url: sceneImage };
                    } else if (sceneImage && typeof sceneImage === 'object') {
                        if (sceneImage.url) {
                            validatedSceneImage = sceneImage;
                            console.log('✅ 初始场景图片URL:', sceneImage.url);
                        } else if (sceneImage.image_url) {
                            validatedSceneImage = { url: sceneImage.image_url };
                            console.log('✅ 使用image_url字段:', sceneImage.image_url);
                        } else {
                            console.error('❌ sceneImage对象缺少URL字段:', sceneImage);
                        }
                    } else {
                        console.error('❌ sceneImage格式无效:', sceneImage);
                    }
                } else {
                    console.warn('⚠️ 初始场景没有图片数据');
                }
                
                displayScene(initialScene, initialOptions, validatedSceneImage, null);  // 视频参数设为null
            } else {
                console.error('❌ API调用失败:', result.message);
                loadingIndicator.remove(); // 移除加载指示器
                // 如果API调用失败，使用默认场景和选项
                const flowWorldline = gameState.gameData.flow_worldline;
                const environment = flowWorldline ? flowWorldline.environment || {} : {};
                const location = environment.location || '未知地点';
                const weather = environment.weather || '晴朗';
                const questProgress = flowWorldline ? (flowWorldline.quest_progress || '') : '';
                const fallbackScene = `你站在${location}，${weather}。${questProgress}`;
                
                const initialOptions = [
                    '继续深入探索',
                    '查看周围环境'
                ];
                displayScene(fallbackScene, initialOptions);
            }
        } catch (error) {
            console.error('❌ API调用异常:', error);
            loadingIndicator.remove();
            // 如果API调用异常，使用默认场景和选项
            const flowWorldline = gameState.gameData.flow_worldline;
            const environment = flowWorldline ? flowWorldline.environment || {} : {};
            const location = environment.location || '未知地点';
            const weather = environment.weather || '晴朗';
            const questProgress = flowWorldline ? (flowWorldline.quest_progress || '') : '';
            const fallbackScene = `你站在${location}，${weather}。${questProgress}`;
            
            const initialOptions = [
                '继续深入探索',
                '查看周围环境'
            ];
            displayScene(fallbackScene, initialOptions);
        }
        
        // 初始化章节进度（1-3%，表示游戏开始）
        // 仅在进度尚未初始化时设置（避免覆盖已在成功路径或重试路径中设置的进度）
        // 注意：如果进度为0（初始值），也需要初始化，因为0%表示未开始，而1-3%表示游戏已开始
        if (gameState.chapterProgress === undefined || gameState.chapterProgress === null || isNaN(gameState.chapterProgress) || gameState.chapterProgress === 0) {
            const initialProgress = Math.max(1, Math.min(3, Math.random() * 2 + 1));
            gameState.chapterProgress = Math.round(initialProgress * 10) / 10;
            if (gameState.gameData.flow_worldline) {
                gameState.gameData.flow_worldline.chapter_progress = gameState.chapterProgress;
            }
            updateChapterProgress(gameState.chapterProgress);
        }
    }
    
    // 预生成下一层内容的辅助函数
    async function pregenerateNextLayers(globalState, currentOptions, sceneId) {
        try {
            // 异步调用预生成接口，不等待结果（后台执行）
            fetch('http://127.0.0.1:5001/pregenerate-next-layers', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    globalState: globalState,
                    currentOptions: currentOptions,
                    sceneId: sceneId,
                    // 新增：图片依赖生成（预生成也带上当前剧情图片作为参考）
                    currentSceneImage: gameState.lastSceneImage,
                    currentSceneText: gameState.currentScene
                })
            }).then(response => response.json())
              .then(result => {
                  if (result.status === 'success') {
                      console.log('✅ 预生成任务已启动，场景ID:', result.sceneId);
                      console.log('🔍 [前端] 预生成返回的 sceneId:', result.sceneId);
                      console.log('🔍 [前端] 前端传入的 sceneId:', sceneId);
                      console.log('🔍 [前端] 更新前的 gameState.currentSceneId:', gameState.currentSceneId);
                      
                      // 更新场景ID（总是更新为后端返回的 sceneId，确保匹配）
                      if (result.sceneId) {
                          gameState.currentSceneId = result.sceneId;
                          console.log('🔍 [前端] 更新后的 gameState.currentSceneId:', gameState.currentSceneId);
                      }
                  } else {
                      console.warn('⚠️ 预生成任务启动失败:', result.message);
                  }
              })
              .catch(error => {
                  console.warn('⚠️ 预生成请求失败:', error);
              });
        } catch (error) {
            console.warn('⚠️ 预生成请求异常:', error);
        }
    }
    
    // 生成新的场景ID
    function generateNewSceneId() {
        const timestamp = Date.now();
        const random = Math.random().toString(36).substring(2, 9);
        return `scene_${timestamp}_${random}`;
    }
    
    // 文本切分函数：将完整文本切分成1-2句话的段落
    function splitTextIntoSegments(text) {
        if (!text || typeof text !== 'string') {
            return [];
        }
        
        // 按句号、问号、感叹号切分，保留分隔符
        const parts = text.split(/([。！？])/);
        
        // 合并成完整的句子（包含标点）
        const completeSentences = [];
        for (let i = 0; i < parts.length; i += 2) {
            const content = parts[i] ? parts[i].trim() : '';
            const punctuation = (i + 1 < parts.length) ? parts[i + 1] : '';
            
            if (content) {
                completeSentences.push(content + punctuation);
            } else if (punctuation && completeSentences.length > 0) {
                // 如果只有标点符号，追加到上一句
                completeSentences[completeSentences.length - 1] += punctuation;
            }
        }
        
        // 过滤空句子
        const validSentences = completeSentences.filter(s => s.trim().length > 0);
        
        // 如果没有找到句子分隔符，返回整个文本作为一段
        if (validSentences.length === 0) {
            return [text.trim()];
        }
        
        // 将句子合并成段落，每段1-2句话
        const segments = [];
        for (let i = 0; i < validSentences.length; i += 2) {
            if (i + 1 < validSentences.length) {
                // 合并两句话
                segments.push(validSentences[i] + validSentences[i + 1]);
            } else {
                // 只有一句话
                segments.push(validSentences[i]);
            }
        }
        
        return segments;
    }
    
    // 显示场景文本（支持图片和视频）
    function displayScene(text, options, imageData = null, videoData = null) {
        console.log('🔍 displayScene调用:', {
            textLength: text ? text.length : 0,
            optionsCount: options ? options.length : 0,
            hasImageData: !!imageData,
            imageUrl: imageData ? imageData.url : null
        });
        
        // 重置预生成触发标志，确保每次新场景显示时都可以触发预生成
        gameState._pregenerationTriggered = false;
        
        // 文本切分：将完整文本切分成段落
        const segments = splitTextIntoSegments(text);
        console.log('📝 文本切分结果:', {
            totalSegments: segments.length,
            segments: segments
        });
        
        // 更新当前剧情文本（用于下一次请求传给后端做连续性）
        // 同时保留上一段剧情文本，便于补图/连续性上下文
        const previousSceneText = gameState.currentScene || '';
        gameState.currentScene = text || '';

        // 保存分段状态
        gameState.textSegments = segments;
        gameState.currentTextSegmentIndex = 0;
        gameState.isShowingSegments = segments.length > 1; // 如果只有一段，不需要分段显示
        gameState.pendingOptions = options;
        gameState.pendingImageData = imageData;
        
        // 重要：先显示场景文本和选项，图片加载是异步的，不应该阻塞
        // 这样可以确保即使图片加载失败，用户也能看到剧情和选项
        
        // 显示场景图片（如果有）- 只在第一次显示时设置，分段显示过程中不更换
        // 注意：只在第一次调用displayScene时设置图片，分段显示过程中保持同一张图片
        // 重要：先验证图片数据格式，确保数据有效
        if (imageData) {
            // 验证图片数据格式
            if (typeof imageData === 'string') {
                // 如果imageData是字符串，转换为对象格式
                console.warn('⚠️ imageData是字符串，转换为对象格式');
                imageData = { url: imageData };
            } else if (typeof imageData !== 'object' || imageData === null) {
                console.error('❌ imageData格式无效:', typeof imageData, imageData);
                imageData = null;
            } else if (!imageData.url) {
                // 尝试从其他字段获取URL
                if (imageData.image_url) {
                    console.warn('⚠️ 使用image_url字段');
                    imageData.url = imageData.image_url;
                } else if (imageData.src) {
                    console.warn('⚠️ 使用src字段');
                    imageData.url = imageData.src;
                } else {
                    console.error('❌ imageData对象缺少url字段:', imageData);
                    imageData = null;
                }
            }
        }
        
        // 同步更新 pendingImageData 为“校验后的”版本，避免分段显示时拿到旧格式
        gameState.pendingImageData = imageData;

        // 只有当这次有“有效新图片”时，才更新 lastSceneImage（否则保留上一张）
        if (imageData && imageData.url && typeof imageData.url === 'string' && imageData.url.trim() !== '') {
            gameState.lastSceneImage = imageData;
        }
        
        // 只在第一次显示时设置背景图片，分段显示过程中不更换
        if (imageData && imageData.url && typeof imageData.url === 'string' && imageData.url.trim() !== '') {
            console.log('✅ 开始加载场景图片（分段显示过程中将保持不变）');
            console.log('   - 图片URL:', imageData.url);
            console.log('   - 图片数据完整对象:', JSON.stringify(imageData, null, 2));
            
            // 立即调用，不使用setTimeout，确保图片能及时显示
            try {
                VisualContentManager.displaySceneImage(imageData);
            } catch (error) {
                console.error('❌ displaySceneImage调用失败:', error);
                console.error('❌ 错误堆栈:', error.stack);
                console.warn('⚠️ 图片显示失败，但场景文本和选项已正常显示');
                
                // 已移除场景图片层，不再设置 sceneImage
                // 只使用全屏背景图片（#global-bg）
                console.log('⚠️ 图片显示失败，但全屏背景图片已设置');
            }
        } else {
            console.log('⚠️ 没有有效的图片数据，保留上一张全屏背景图片显示');
            console.log('   - imageData:', imageData);

            // 补救：如果后端没返回图片（或下载/解析失败），前端异步补图，不阻塞文本/选项显示
            // - 通过独立接口生成图片，避免 /generate-option 因图片耗时而卡住
            // - 做去重与“只在仍处于该剧情时才应用结果”的保护
            try {
                const sceneTextForRequest = (text || '').trim();
                if (sceneTextForRequest) {
                    const requestKey = `${gameState.currentSceneId || 'no_scene_id'}|${sceneTextForRequest.slice(0, 200)}`;
                    if (gameState._sceneImageRequestKey !== requestKey) {
                        gameState._sceneImageRequestKey = requestKey;

                        // 取消上一条补图请求（如果还在进行）
                        if (gameState._sceneImageAbortController) {
                            try { gameState._sceneImageAbortController.abort(); } catch (_) {}
                        }
                        const controller = new AbortController();
                        gameState._sceneImageAbortController = controller;

                        const style = (gameState.gameData && gameState.gameData.image_style) ? gameState.gameData.image_style : 'default';
                        const globalStatePayload = {
                            ...(gameState.gameData || {}),
                            _visual_context: {
                                sceneId: gameState.currentSceneId || null,
                                previousSceneImage: gameState.lastSceneImage || null,
                                previousSceneText: previousSceneText || ''
                            }
                        };

                        // 获取视口尺寸，用于按视口宽高比生成图片
                        const viewportWidth = window.innerWidth;
                        const viewportHeight = window.innerHeight;
                        console.log(`📐 视口尺寸: ${viewportWidth}x${viewportHeight}`);
                        
                        fetch('http://127.0.0.1:5001/generate-scene-image', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                sceneDescription: sceneTextForRequest,
                                globalState: globalStatePayload,
                                style: style,
                                viewportWidth: viewportWidth,
                                viewportHeight: viewportHeight
                            }),
                            signal: controller.signal
                        })
                        .then(r => r.json())
                        .then(result => {
                            // 只在“仍是当前剧情”且 key 未变化时应用
                            if (gameState._sceneImageRequestKey !== requestKey) return;
                            if (sceneTextForRequest !== (gameState.currentScene || '').trim()) return;
                            if (result && result.status === 'success' && result.image && result.image.url) {
                                const img = result.image;
                                console.log('✅ 异步补图成功:', img.url);
                                try {
                                    VisualContentManager.displaySceneImage(img);
                                } catch (e) {
                                    console.warn('⚠️ 异步补图展示失败:', e);
                                }
                                // 更新状态，供“下一剧情参考上一剧情图片”使用
                                gameState.pendingImageData = img;
                                gameState.lastSceneImage = img;
                            } else {
                                console.warn('⚠️ 异步补图失败:', result && result.message ? result.message : result);
                            }
                        })
                        .catch(err => {
                            if (err && err.name === 'AbortError') return;
                            console.warn('⚠️ 异步补图请求异常:', err);
                        });
                    }
                }
            } catch (e) {
                console.warn('⚠️ 异步补图逻辑异常:', e);
            }

            // 已移除场景图片层，只使用全屏背景图片（#global-bg）
            // 如果没有新图片，全屏背景会保留上一张图片
            const sceneVideo = document.getElementById('scene-video');
            if (sceneVideo) sceneVideo.style.display = 'none';
        }
        
        // ==================== 视频显示功能已禁用（性能优化） ====================
        // 显示场景视频（如果有）
        // if (videoData) {
        //     VisualContentManager.displaySceneVideo(videoData);
        // } else if (imageData && imageData.url) {
        //     // 如果没有视频但有图片，尝试请求生成视频
        //     VisualContentManager.requestSceneVideo(text, imageData);
        // }
        
        // 显示场景文本（打字机效果）
        // 首先切换显示区域：显示文本区域，隐藏选项区域
        const textDisplayArea = document.getElementById('text-display-area');
        const optionsListArea = document.getElementById('options-list-area');
        if (textDisplayArea) {
            textDisplayArea.classList.remove('hidden');
        }
        if (optionsListArea) {
            optionsListArea.classList.add('hidden');
        }
        
        const sceneTextElement = elements.content.sceneText || document.getElementById('scene-text');
        if (sceneTextElement) {
            // 强制禁用所有缩放和变换效果（JavaScript强制设置，覆盖所有CSS和浏览器默认样式）
            const forceNoTransform = () => {
                sceneTextElement.style.setProperty('transform', 'none', 'important');
                sceneTextElement.style.setProperty('scale', '1', 'important');
                sceneTextElement.style.setProperty('transition', 'none', 'important');
                sceneTextElement.style.setProperty('animation', 'none', 'important');
                sceneTextElement.style.setProperty('pointer-events', 'none', 'important');
                sceneTextElement.style.setProperty('user-select', 'none', 'important');
                sceneTextElement.style.setProperty('outline', 'none', 'important');
                sceneTextElement.style.setProperty('-webkit-transform', 'none', 'important');
                sceneTextElement.style.setProperty('-moz-transform', 'none', 'important');
                sceneTextElement.style.setProperty('-ms-transform', 'none', 'important');
                sceneTextElement.style.setProperty('-o-transform', 'none', 'important');
                sceneTextElement.style.setProperty('touch-action', 'none', 'important'); // 禁用触摸缩放
                sceneTextElement.style.setProperty('-webkit-touch-callout', 'none', 'important');
                sceneTextElement.style.setProperty('-webkit-tap-highlight-color', 'transparent', 'important');
                sceneTextElement.style.setProperty('tap-highlight-color', 'transparent', 'important');
            };
            
            forceNoTransform();
            
            // 监听所有可能改变样式的事件，立即重置（使用捕获阶段，最早拦截）
            // 注意：移除 touchmove，允许滚动；移除 touchstart/touchend，允许滚动
            ['click', 'mousedown', 'mouseup', 'focus', 'blur', 'dblclick'].forEach(eventType => {
                sceneTextElement.addEventListener(eventType, (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation(); // 阻止其他监听器
                    forceNoTransform();
                    console.log(`🚫 [防缩放] 阻止了${eventType}事件`);
                }, true); // 使用捕获阶段，最早拦截
            });
            
            // 使用MutationObserver监控样式变化，立即重置（添加防无限循环机制）
            let isUpdating = false; // 防止无限循环的标志
            const observer = new MutationObserver((mutations) => {
                // 如果正在更新，跳过（防止无限循环）
                if (isUpdating) return;
                
                mutations.forEach((mutation) => {
                    if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
                        // 检查是否是我们的更新导致的
                        const currentStyle = sceneTextElement.getAttribute('style');
                        // 如果style中包含我们设置的属性，说明是我们自己更新的，跳过
                        if (currentStyle && currentStyle.includes('transform: none')) {
                            return; // 跳过，避免无限循环
                        }
                        
                        // 只有非我们的更新才重置
                        isUpdating = true;
                        forceNoTransform();
                        console.log('🚫 [防缩放] 检测到样式变化，已重置');
                        // 使用setTimeout确保在下一个事件循环中重置标志
                        setTimeout(() => {
                            isUpdating = false;
                        }, 0);
                    }
                });
            });
            observer.observe(sceneTextElement, {
                attributes: true,
                attributeFilter: ['style', 'class'],
                subtree: false
            });
            
            // 定期检查并重置（防止其他代码修改样式）- 降低频率避免性能问题
            const checkInterval = setInterval(() => {
                if (!isUpdating) {
                    const computedStyle = window.getComputedStyle(sceneTextElement);
                    if (computedStyle.transform !== 'none' && computedStyle.transform !== 'matrix(1, 0, 0, 1, 0, 0)') {
                        isUpdating = true;
                        console.warn('⚠️ [防缩放] 检测到transform被修改，正在重置:', computedStyle.transform);
                        forceNoTransform();
                        setTimeout(() => {
                            isUpdating = false;
                        }, 0);
                    }
                }
            }, 500); // 降低频率到500ms，减少性能影响
            
            // 保存interval ID以便清理
            sceneTextElement._noTransformInterval = checkInterval;
            
            // 修复：先清理旧的打字机动画，防止重复和重叠
            if (gameState.currentTypeInterval) {
                clearInterval(gameState.currentTypeInterval);
                gameState.currentTypeInterval = null;
            }
            
            // 完全清理旧文本内容，防止重叠显示
            sceneTextElement.classList.remove('typewriter');
            sceneTextElement.textContent = '';
            sceneTextElement.innerHTML = '';
            
            // 隐藏"->"按钮（如果存在）
            const nextSegmentBtn = document.getElementById('next-segment-btn');
            if (nextSegmentBtn) {
                nextSegmentBtn.classList.add('hidden');
            }
            
            // 获取要显示的文本段落
            const currentSegment = segments.length > 0 ? segments[0] : text;
            const segmentText = currentSegment || text;
            
            // 等待一帧确保DOM完全更新后再开始新动画
            requestAnimationFrame(() => {
                // 在开始显示第一段文本时，立即触发预生成（利用用户阅读时间）
                // 检查是否已经触发过预生成（避免重复触发）
                if (!gameState._pregenerationTriggered && options && options.length > 0) {
                    gameState._pregenerationTriggered = true;
                    
                    // 生成新的场景ID用于预生成缓存
                    const newSceneId = generateNewSceneId();
                    gameState.currentSceneId = newSceneId;
                    
                    console.log('🚀 文本开始显示，立即触发预生成（场景ID:', newSceneId, '）');
                    
                    // 异步调用预生成接口（不阻塞文本显示）
                    if (gameState.gameData && options && options.length > 0) {
                        pregenerateNextLayers(gameState.gameData, options, newSceneId);
                    }
                }
                
                // 再次强制设置样式，确保动画不会覆盖我们的设置
                sceneTextElement.style.setProperty('transform', 'none', 'important');
                sceneTextElement.style.setProperty('scale', '1', 'important');
                sceneTextElement.style.setProperty('transition', 'none', 'important');
                
                sceneTextElement.classList.add('typewriter');
                let index = 0;
                
                const typeInterval = setInterval(() => {
                    if (index < segmentText.length) {
                        sceneTextElement.textContent += segmentText.charAt(index);
                        index++;
                        // 关键信息高亮
                        // 注意：先做HTML转义，避免原文中的 <、& 等字符导致渲染吞字/吞数字
                        const highlightedText = escapeHtml(sceneTextElement.textContent)
                            .replace(/迷雾森林/g, '<span class="text-[#3498DB] font-bold">迷雾森林</span>')
                            .replace(/上古神器/g, '<span class="text-[#3498DB] font-bold">上古神器</span>')
                            .replace(/古老神庙/g, '<span class="text-[#3498DB] font-bold">古老神庙</span>')
                            .replace(/怪异/g, '<span class="text-[#3498DB] font-bold">怪异</span>');
                        sceneTextElement.innerHTML = highlightedText;
                    } else {
                        clearInterval(typeInterval);
                        gameState.currentTypeInterval = null; // 清理引用
                        sceneTextElement.classList.remove('typewriter');
                        
                        // 动画结束后再次强制设置样式，确保没有任何缩放效果
                        sceneTextElement.style.setProperty('transform', 'none', 'important');
                        sceneTextElement.style.setProperty('scale', '1', 'important');
                        sceneTextElement.style.setProperty('transition', 'none', 'important');
                        sceneTextElement.style.setProperty('animation', 'none', 'important');
                        
                        playSound('typeend');
                        
                        // 判断是否还有更多段落需要显示
                        if (gameState.isShowingSegments && gameState.currentTextSegmentIndex < segments.length - 1) {
                            // 还有更多段落，显示"->"按钮
                            console.log('✅ 当前段落显示完成，显示"->"按钮等待用户点击');
                            if (nextSegmentBtn) {
                                nextSegmentBtn.classList.remove('hidden');
                            }
                        } else {
                            // 所有段落都显示完了，显示"->"按钮等待用户点击后再显示选项
                            console.log('✅ 所有段落显示完成，显示"->"按钮等待用户点击显示选项');
                            
                            // 保存待显示的选项
                            gameState.pendingOptions = options;
                            
                            // 显示"->"按钮（点击后显示选项）
                            if (nextSegmentBtn) {
                                nextSegmentBtn.classList.remove('hidden');
                                // 标记这是最后一段，点击后应该显示选项
                                nextSegmentBtn.dataset.showOptions = 'true';
                            }
                        }
                    }
                }, 30);
                
                // 保存当前interval引用，以便下次清理
                gameState.currentTypeInterval = typeInterval;
            });
        } else {
            console.error('❌ 找不到sceneText元素，直接显示选项');
            // 如果找不到元素，直接显示选项
            generateOptions(options);
        }
        
        gameState.currentScene = text;
        gameState.currentOptions = options;
    }
    
    // 显示下一段文本
    function showNextTextSegment() {
        if (!gameState.isShowingSegments || gameState.currentTextSegmentIndex >= gameState.textSegments.length - 1) {
            console.warn('⚠️ 没有更多段落需要显示');
            return;
        }
        
        // 隐藏"->"按钮并清除显示选项标记
        const nextSegmentBtn = document.getElementById('next-segment-btn');
        if (nextSegmentBtn) {
            nextSegmentBtn.classList.add('hidden');
            nextSegmentBtn.dataset.showOptions = 'false'; // 清除显示选项标记
        }
        
        // 移动到下一段
        gameState.currentTextSegmentIndex++;
        const nextSegment = gameState.textSegments[gameState.currentTextSegmentIndex];
        
        if (!nextSegment) {
            console.warn('⚠️ 下一段文本为空');
            return;
        }
        
        const sceneTextElement = elements.content.sceneText || document.getElementById('scene-text');
        if (!sceneTextElement) {
            console.error('❌ 找不到sceneText元素');
            return;
        }
        
        // 清理旧文本
        sceneTextElement.classList.remove('typewriter');
        sceneTextElement.textContent = '';
        sceneTextElement.innerHTML = '';
        
        // 显示下一段文本（打字机效果）
        requestAnimationFrame(() => {
            sceneTextElement.style.setProperty('transform', 'none', 'important');
            sceneTextElement.style.setProperty('scale', '1', 'important');
            sceneTextElement.style.setProperty('transition', 'none', 'important');
            
            sceneTextElement.classList.add('typewriter');
            let index = 0;
            
            const typeInterval = setInterval(() => {
                if (index < nextSegment.length) {
                    sceneTextElement.textContent += nextSegment.charAt(index);
                    index++;
                    // 关键信息高亮
                    // 注意：先做HTML转义，避免原文中的 <、& 等字符导致渲染吞字/吞数字
                    const highlightedText = escapeHtml(sceneTextElement.textContent)
                        .replace(/迷雾森林/g, '<span class="text-[#3498DB] font-bold">迷雾森林</span>')
                        .replace(/上古神器/g, '<span class="text-[#3498DB] font-bold">上古神器</span>')
                        .replace(/古老神庙/g, '<span class="text-[#3498DB] font-bold">古老神庙</span>')
                        .replace(/怪异/g, '<span class="text-[#3498DB] font-bold">怪异</span>');
                    sceneTextElement.innerHTML = highlightedText;
                } else {
                    clearInterval(typeInterval);
                    gameState.currentTypeInterval = null;
                    sceneTextElement.classList.remove('typewriter');
                    
                    // 动画结束后再次强制设置样式
                    sceneTextElement.style.setProperty('transform', 'none', 'important');
                    sceneTextElement.style.setProperty('scale', '1', 'important');
                    sceneTextElement.style.setProperty('transition', 'none', 'important');
                    sceneTextElement.style.setProperty('animation', 'none', 'important');
                    
                    playSound('typeend');
                    
                    // 判断是否还有更多段落
                    if (gameState.currentTextSegmentIndex < gameState.textSegments.length - 1) {
                        // 还有更多段落，显示"->"按钮
                        console.log('✅ 当前段落显示完成，显示"->"按钮等待用户点击');
                        if (nextSegmentBtn) {
                            nextSegmentBtn.classList.remove('hidden');
                        }
                    } else {
                        // 所有段落都显示完了，显示"->"按钮等待用户点击后再显示选项
                        console.log('✅ 所有段落显示完成，显示"->"按钮等待用户点击显示选项');
                        
                        // 显示"->"按钮（点击后显示选项）
                        const nextSegmentBtn = document.getElementById('next-segment-btn');
                        if (nextSegmentBtn) {
                            nextSegmentBtn.classList.remove('hidden');
                            // 标记这是最后一段，点击后应该显示选项
                            nextSegmentBtn.dataset.showOptions = 'true';
                        }
                    }
                }
            }, 30);
            
            // 保存当前interval引用
            gameState.currentTypeInterval = typeInterval;
        });
    }
    
    // 生成选项列表
    function generateOptions(options) {
        // 确保选项区域是显示的，文本区域是隐藏的
        const textDisplayArea = document.getElementById('text-display-area');
        const optionsListArea = document.getElementById('options-list-area');
        if (textDisplayArea) {
            textDisplayArea.classList.add('hidden');
        }
        if (optionsListArea) {
            optionsListArea.classList.remove('hidden');
        }
        
        // 清空现有选项列表
        const optionsList = document.getElementById('options-list');
        if (optionsList) {
            optionsList.innerHTML = '';
        }
        
        // 使用documentFragment批量处理DOM插入，减少回流和重绘
        const fragment = document.createDocumentFragment();
        
        options.forEach((option, index) => {
            const optionCard = document.createElement('div');
            optionCard.className = 'option-card';
            optionCard.dataset.index = index;
            
            const optionNumber = document.createElement('div');
            optionNumber.className = 'option-number';
            optionNumber.textContent = index + 1;
            
            const optionText = document.createElement('div');
            optionText.className = 'option-text';
            optionText.textContent = option;
            
            optionCard.appendChild(optionNumber);
            optionCard.appendChild(optionText);
            
            // 点击事件
            optionCard.addEventListener('click', async () => {
                // 选中状态
                document.querySelectorAll('.option-card').forEach(card => {
                    card.classList.remove('selected');
                });
                optionCard.classList.add('selected');
                optionCard.classList.add('shake-animation'); // 使用CSS类替代直接操作style
                
                playSound('confirm');
                
                // 隐藏箭头 - 使用CSS类替代直接操作style
                const sceneArrow = document.querySelector('.scene-arrow');
                if (sceneArrow) {
                    sceneArrow.classList.add('hidden');
                }
                
                // 延迟显示下一段剧情
                setTimeout(async () => {
                    // 移除动画类
                    optionCard.classList.remove('shake-animation');
                    
                    const selectedOption = option;
                    
                    // 检查是否是结束游戏选项
                    if (selectedOption.includes('结束游戏，观看结局')) {
                        // 显示结局屏幕
                        showEndingScreen();
                        return;
                    }
                    
                    // 隐藏选项区域，清空选项列表
                    const optionsListArea = document.getElementById('options-list-area');
                    const optionsList = document.getElementById('options-list');
                    if (optionsListArea) {
                        optionsListArea.classList.add('hidden');
                    }
                    if (optionsList) {
                        optionsList.innerHTML = ''; // 清空选项列表
                    }
                    
                    // 显示加载状态
                    // 已移除scene-container，不再需要
                    const loadingIndicator = document.createElement('div');
                    loadingIndicator.className = 'loading-overlay flex items-center justify-center bg-black/70 fixed inset-0 z-50';
                    loadingIndicator.innerHTML = `
                        <div class="loading-content text-center">
                            <div class="spinner animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
                            <p class="text-white">生成剧情中...</p>
                        </div>
                    `;
                    const gameplayScreen = document.getElementById('gameplay-screen');
                    if (gameplayScreen) {
                        gameplayScreen.appendChild(loadingIndicator);
                    } else {
                        // 如果找不到gameplay-screen，添加到body
                        document.body.appendChild(loadingIndicator);
                    }
                    
                    try {
                        // 保存上一轮的sceneId用于缓存清理
                        const previousSceneId = gameState.currentSceneId;
                        
                        // 添加超时检测：如果30秒内没有响应，显示提示
                        const hintTimeoutId = setTimeout(() => {
                            if (loadingIndicator && loadingIndicator.parentNode) {
                                const loadingText = loadingIndicator.querySelector('p');
                                if (loadingText) {
                                    loadingText.textContent = '正在生成场景图片，请稍候...（图片生成最多需要6分钟）';
                                }
                            }
                        }, 30000); // 30秒后显示提示
                        
                        // 调用后端API生成选项（传入sceneId以便从缓存读取）
                        // 添加超时控制（5分钟超时，因为图片生成最多需要6分钟）
                        const controller = new AbortController();
                        const requestTimeoutId = setTimeout(() => controller.abort(), 300000); // 5分钟超时
                        
                        let response;
                        try {
                            // 🔍 调试日志：显示前端发送的参数
                            console.log('🔍 [前端] 调用 /generate-option：');
                            console.log('   - 选项内容：', selectedOption);
                            console.log('   - 选项索引：', index);
                            console.log('   - 发送的 sceneId：', gameState.currentSceneId);
                            console.log('   - previousSceneId：', previousSceneId);
                            
                            response = await fetch('http://127.0.0.1:5001/generate-option', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({
                                    option: selectedOption,
                                    globalState: gameState.gameData,
                                    optionIndex: index,
                                    sceneId: gameState.currentSceneId,  // 传入场景ID，从缓存读取预生成内容
                                    previousSceneId: previousSceneId,  // 传入上一轮的sceneId用于缓存清理
                                    // 新增：图片依赖生成（把上一剧情图片与文本传给后端）
                                    previousSceneImage: gameState.lastSceneImage,
                                    previousSceneText: gameState.currentScene
                                }),
                                signal: controller.signal
                            });
                        } catch (error) {
                            clearTimeout(hintTimeoutId);
                            clearTimeout(requestTimeoutId);
                            if (error.name === 'AbortError') {
                                throw new Error('请求超时（5分钟），请检查网络连接或稍后重试');
                            }
                            throw error;
                        }
                        
                        clearTimeout(hintTimeoutId);
                        clearTimeout(requestTimeoutId);
                        
                        // 检查响应状态
                        if (!response.ok) {
                            throw new Error(`HTTP错误！状态：${response.status}`);
                        }
                        
                        const result = await response.json();
                        
                        // 移除加载状态
                        if (loadingIndicator && loadingIndicator.parentNode) {
                            loadingIndicator.remove();
                        }
                        
                        if (result.status === 'success') {
                            console.log('API调用成功，生成的选项数据:', result.optionData);
                            
                            // 解析生成的剧情和选项
                            const optionData = result.optionData;
                            
                            // 重要：验证场景文本是否有效（不是空字符串或默认值）
                            let nextScene = optionData.scene;
                            if (!nextScene || nextScene.trim() === '' || nextScene.length < 10) {
                                console.warn('⚠️ 后端返回的场景文本无效或为空:', nextScene);
                                console.warn('⚠️ optionData完整内容:', JSON.stringify(optionData, null, 2));
                                // 如果场景文本无效，使用默认值，但记录警告
                                nextScene = optionData.scene || '剧情生成失败，请重试。';
                            } else {
                                console.log('✅ 后端返回的场景文本有效，长度:', nextScene.length);
                                console.log('✅ 场景文本预览:', nextScene.substring(0, 100) + '...');
                            }
                            
                            let nextOptions = optionData.next_options || [];
                            
                            // 验证选项是否有效
                            if (!nextOptions || !Array.isArray(nextOptions) || nextOptions.length === 0) {
                                console.warn('⚠️ 后端返回的选项无效或为空，使用默认选项');
                                nextOptions = ['继续前进', '查看当前状态'];
                            }
                            
                            // 限制选项数量为2个
                            if (nextOptions.length > 2) {
                                console.log('📊 选项数量超过2个，限制为前2个');
                                nextOptions = nextOptions.slice(0, 2);
                            }
                            
                            // 提取视觉内容数据
                            const sceneImage = optionData.scene_image || null;
                            // const sceneVideo = optionData.scene_video || null;  // 视频功能已禁用
                            
                            // 调试：检查选项数据
                            console.log('🔍 后端返回的next_options:', nextOptions);
                            console.log('🔍 next_options类型:', typeof nextOptions);
                            console.log('🔍 next_options长度:', nextOptions ? nextOptions.length : 0);
                            console.log('🔍 场景图片数据:', sceneImage);
                            console.log('🔍 optionData完整数据:', JSON.stringify(optionData, null, 2));
                            // console.log('场景视频数据:', sceneVideo);  // 视频功能已禁用
                            
                            // 问题5修复：验证后端返回数据格式
                            if (sceneImage) {
                                console.log('✅ 检测到场景图片数据');
                                console.log('   - 原始数据:', sceneImage);
                                console.log('   - 数据类型:', typeof sceneImage);
                                
                                // 确保sceneImage是对象格式
                                if (typeof sceneImage === 'string') {
                                    console.warn('⚠️ sceneImage是字符串，转换为对象格式');
                                    sceneImage = { url: sceneImage };
                                } else if (!sceneImage || typeof sceneImage !== 'object') {
                                    console.error('❌ sceneImage格式无效:', sceneImage);
                                    sceneImage = null;
                                } else {
                                    // 验证并修复URL字段
                                    if (!sceneImage.url) {
                                        console.warn('⚠️ sceneImage对象缺少url字段，尝试其他字段');
                                        // 尝试从其他可能的字段获取URL
                                        if (sceneImage.image_url) {
                                            console.warn('⚠️ 使用image_url字段');
                                            sceneImage.url = sceneImage.image_url;
                                        } else if (sceneImage.src) {
                                            console.warn('⚠️ 使用src字段');
                                            sceneImage.url = sceneImage.src;
                                        } else {
                                            console.error('❌ 无法找到图片URL字段，将不显示图片');
                                            console.error('❌ sceneImage对象内容:', JSON.stringify(sceneImage, null, 2));
                                            sceneImage = null;
                                        }
                                    } else {
                                        console.log('✅ 找到图片URL:', sceneImage.url);
                                        // 验证URL格式
                                        if (typeof sceneImage.url !== 'string' || sceneImage.url.trim() === '') {
                                            console.error('❌ URL格式无效:', sceneImage.url);
                                            sceneImage = null;
                                        }
                                    }
                                }
                            } else {
                                console.warn('⚠️ 未检测到场景图片数据');
                            }
                            
                            // 如果选项为空，使用默认选项（不应该发生，但做容错处理）
                            if (!nextOptions || nextOptions.length === 0) {
                                console.warn('⚠️ 后端返回的选项为空，使用默认选项');
                                nextOptions = ['继续前进', '查看当前状态'];
                            } else if (nextOptions.length < 2) {
                                console.warn('⚠️ 后端返回的选项过少（' + nextOptions.length + '个），补充默认选项');
                                const defaultOptions = ['继续前进', '查看当前状态'];
                                // 合并选项，避免重复，但最多只保留2个
                                defaultOptions.forEach(opt => {
                                    if (!nextOptions.includes(opt) && nextOptions.length < 2) {
                                        nextOptions.push(opt);
                                    }
                                });
                            }
                            
                            console.log('最终使用的选项:', nextOptions);
                            
                            // 更新游戏状态
                            if (gameState.gameData.flow_worldline && optionData.flow_update) {
                                const flowUpdate = optionData.flow_update;
                                if (flowUpdate.quest_progress) {
                                    gameState.gameData.flow_worldline.quest_progress = flowUpdate.quest_progress;
                                }
                                if (typeof flowUpdate.chapter_conflict_solved === 'boolean') {
                                    gameState.gameData.flow_worldline.chapter_conflict_solved = flowUpdate.chapter_conflict_solved;
                                }
                                
                                // 更新章节进度（每次选择选项后都更新）
                                if (flowUpdate.chapter_conflict_solved === true) {
                                    // 如果章节矛盾已解决，进度设为100%
                                    gameState.chapterProgress = 100;
                                    gameState.gameData.flow_worldline.chapter_progress = 100;
                                    updateChapterProgress(100);
                                } else {
                                    // 根据当前进度在到达结局之前的占比来确定进度更新
                                    const remainingProgress = 100 - gameState.chapterProgress;
                                    // 基础增量：根据剩余进度计算，使用对数函数使进度增长更平滑
                                    const baseIncrement = Math.log(remainingProgress + 1) * 1.5;
                                    // 添加一些随机性（±20%）
                                    const randomFactor = 0.8 + Math.random() * 0.4;
                                    // 限制增量：不超过剩余进度的10%，且最小0.5%
                                    const progressIncrement = Math.max(0.5, Math.min(remainingProgress * 0.1, baseIncrement * randomFactor));
                                    const newProgress = Math.min(95, gameState.chapterProgress + progressIncrement);
                                    gameState.chapterProgress = Math.round(newProgress * 10) / 10; // 保留一位小数
                                    gameState.gameData.flow_worldline.chapter_progress = gameState.chapterProgress;
                                    updateChapterProgress(gameState.chapterProgress);
                                }
                            } else if (gameState.gameData.flow_worldline) {
                                // 即使没有flow_update，每次选择选项后也应该更新进度
                                const remainingProgress = 100 - gameState.chapterProgress;
                                const baseIncrement = Math.log(remainingProgress + 1) * 1.5;
                                const randomFactor = 0.8 + Math.random() * 0.4;
                                const progressIncrement = Math.max(0.5, Math.min(remainingProgress * 0.1, baseIncrement * randomFactor));
                                const newProgress = Math.min(95, gameState.chapterProgress + progressIncrement);
                                gameState.chapterProgress = Math.round(newProgress * 10) / 10;
                                gameState.gameData.flow_worldline.chapter_progress = gameState.chapterProgress;
                                updateChapterProgress(gameState.chapterProgress);
                            }
                            
                            // 修复：清理场景描述中的错误信息，确保只显示正常剧情
                            let cleanedNextScene = nextScene;
                            // 移除常见的错误提示文字
                            const errorPatterns = [
                                /请求.*?失败/g,
                                /申请.*?失败/g,
                                /请.*?重试/g,
                                /侧向请求/g,
                                /生化或者失败联盟/g,
                                /出让角1/g,
                                /遣代表试/g,
                                /[^\u4e00-\u9fa5a-zA-Z0-9０-９\s，。！？、：；“”‘’（）《》【】…]+/g  // 移除所有非中文字符、非英文字符、非数字和非常见标点的内容（保留数字与常用中文标点）
                            ];
                            
                            errorPatterns.forEach(pattern => {
                                cleanedNextScene = cleanedNextScene.replace(pattern, '');
                            });

                            // 🔍 调试：统计“数字”是否在清洗阶段被误删（仅输出到控制台）
                            try {
                                const numsBefore = (nextScene || '').match(/\p{N}/gu) || [];
                                const numsAfter = (cleanedNextScene || '').match(/\p{N}/gu) || [];
                                console.log(`🔢 数字统计（任意数字字符）：清洗前 ${numsBefore.length} -> 清洗后 ${numsAfter.length}`);
                            } catch {
                                const numsBefore = (nextScene || '').match(/[0-9０-９]/g) || [];
                                const numsAfter = (cleanedNextScene || '').match(/[0-9０-９]/g) || [];
                                console.log(`🔢 数字统计（0-9/全角）：清洗前 ${numsBefore.length} -> 清洗后 ${numsAfter.length}`);
                            }
                            
                            // 确保场景描述有意义
                            if (!cleanedNextScene.trim() || cleanedNextScene.length < 10) {
                                cleanedNextScene = "你仔细观察周围的环境，准备采取行动。";
                            }
                            
                            // 更新当前场景ID（用于下次清理缓存）
                            const newSceneId = generateNewSceneId();
                            gameState.currentSceneId = newSceneId;
                            
                            // 确保加载状态已移除
                            if (loadingIndicator && loadingIndicator.parentNode) {
                                loadingIndicator.remove();
                            }
                            
                            // 问题5修复：验证并规范化图片数据格式
                            let validatedSceneImage = null;
                            if (sceneImage) {
                                console.log('🔍 验证场景图片数据格式...');
                                if (typeof sceneImage === 'string') {
                                    console.warn('⚠️ sceneImage是字符串，转换为对象格式');
                                    validatedSceneImage = { url: sceneImage };
                                } else if (sceneImage && typeof sceneImage === 'object') {
                                    if (sceneImage.url) {
                                        validatedSceneImage = sceneImage;
                                        console.log('✅ 图片数据格式正确，URL:', sceneImage.url);
                                    } else if (sceneImage.image_url) {
                                        validatedSceneImage = { url: sceneImage.image_url };
                                        console.log('✅ 使用image_url字段');
                                    } else {
                                        console.error('❌ sceneImage对象缺少URL字段:', sceneImage);
                                        console.error('❌ sceneImage完整内容:', JSON.stringify(sceneImage, null, 2));
                                    }
                                } else {
                                    console.error('❌ sceneImage格式无效:', sceneImage);
                                }
                            } else {
                                console.warn('⚠️ 没有场景图片数据');
                            }
                            
                            // 显示清理后的剧情（displayScene会自动触发预生成）
                            // 显示场景，包含视觉内容（视频功能已禁用）
                            console.log('🔄 准备显示新场景');
                            console.log('   - 场景文本长度:', cleanedNextScene.length);
                            console.log('   - 选项数量:', nextOptions.length);
                            console.log('   - 图片数据:', validatedSceneImage ? (validatedSceneImage.url || '无URL') : '无图片数据');
                            
                            // 确保在显示前移除所有加载指示器
                            const allLoadingIndicators = document.querySelectorAll('.loading-overlay');
                            allLoadingIndicators.forEach(indicator => {
                                if (indicator.parentNode) {
                                    indicator.remove();
                                }
                            });
                            
                            try {
                                displayScene(cleanedNextScene, nextOptions, validatedSceneImage, null);  // 视频参数设为null
                                console.log('✅ displayScene调用成功');
                            } catch (error) {
                                console.error('❌ displayScene调用失败:', error);
                                console.error('错误堆栈:', error.stack);
                                // 即使displayScene失败，也尝试显示文本和选项
                                // 修复：先清理旧的打字机动画
                                if (gameState.currentTypeInterval) {
                                    clearInterval(gameState.currentTypeInterval);
                                    gameState.currentTypeInterval = null;
                                }
                                const sceneTextElement = document.getElementById('scene-text');
                                if (sceneTextElement) {
                                    sceneTextElement.classList.remove('typewriter');
                                    sceneTextElement.textContent = '';
                                    sceneTextElement.innerHTML = '';
                                    sceneTextElement.textContent = cleanedNextScene;
                                }
                                generateOptions(nextOptions);
                            }
                        } else {
                            console.error('API调用失败:', result.message);
                            // 移除加载状态
                            if (loadingIndicator && loadingIndicator.parentNode) {
                                loadingIndicator.remove();
                            }
                            // 显示有意义的错误信息
                            const errorMessage = result.message || '剧情生成失败，请重试。';
                            displayScene(errorMessage, ['继续游戏', '返回主菜单'], null, null);
                        }
                    } catch (error) {
                        console.error('❌ API调用异常:', error);
                        console.error('❌ 错误详情:', error.stack);
                        console.error('❌ 错误类型:', error.name);
                        console.error('❌ 错误消息:', error.message);
                        
                        // 移除加载状态（确保移除）
                        const allLoadingIndicators = document.querySelectorAll('.loading-overlay');
                        allLoadingIndicators.forEach(indicator => {
                            if (indicator.parentNode) {
                                indicator.remove();
                            }
                        });
                        
                        // 判断错误类型
                        let errorMessage = '剧情生成失败，请重试。';
                        if (error.name === 'TypeError' && error.message.includes('fetch')) {
                            errorMessage = '网络连接失败，请检查后端服务是否运行。';
                        } else if (error.message.includes('timeout') || error.message.includes('超时')) {
                            errorMessage = '请求超时，可能是后端处理时间过长，请稍后重试。';
                        } else if (error.message.includes('HTTP错误')) {
                            errorMessage = `服务器错误：${error.message}，请检查后端日志。`;
                        }
                        
                        // 显示友好的错误信息
                        try {
                            displayScene(errorMessage, ['继续游戏', '返回主菜单'], null, null);
                        } catch (displayError) {
                            console.error('❌ displayScene也失败了:', displayError);
                            // 最后的降级方案：直接更新文本和选项
                            // 修复：先清理旧的打字机动画
                            if (gameState.currentTypeInterval) {
                                clearInterval(gameState.currentTypeInterval);
                                gameState.currentTypeInterval = null;
                            }
                            const sceneTextElement = document.getElementById('scene-text');
                            if (sceneTextElement) {
                                sceneTextElement.classList.remove('typewriter');
                                sceneTextElement.textContent = '';
                                sceneTextElement.innerHTML = '';
                                sceneTextElement.textContent = errorMessage;
                            }
                            generateOptions(['继续游戏', '返回主菜单']);
                        }
                    }
            
            // 本地选项生成逻辑（作为API调用失败的回退）
            function generateLocalOptions(selectedOption, loadingIndicator) {
                // 移除加载状态
                loadingIndicator.remove();
                
                console.log('使用本地逻辑生成剧情和选项，selectedOption:', selectedOption);
                
                // 根据游戏状态和选择生成更丰富的剧情和选项
                const coreWorldview = gameState.gameData.core_worldview || {};
                const flowWorldline = gameState.gameData.flow_worldline || {};
                const currentChapter = flowWorldline.current_chapter || 'chapter1';
                const chapters = coreWorldview.chapters || {};
                const chapterInfo = chapters[currentChapter] || {};
                const protagonistAttr = gameState.protagonistAttr || {};
                
                // 根据不同的选择生成不同的剧情和选项
                let nextScene = '';
                let nextOptions = [];
                
                // 生成丰富的剧情和选项，考虑当前游戏状态、角色属性和选择内容
                if (selectedOption.includes('继续深入探索')) {
                    // 根据角色属性生成不同的剧情
                    let attrScene = '';
                    if (protagonistAttr.智商 === '高') {
                        attrScene = '你运用你的智慧，很快发现了一条隐藏的捷径。';
                    } else if (protagonistAttr.体力 === '高') {
                        attrScene = '你的体力充沛，即使在崎岖的地形上也能轻松前进。';
                    } else {
                        attrScene = '你一步一步地前进，虽然速度不快，但很稳。';
                    }
                    
                    nextScene = `你决定继续深入探索，沿着${chapterInfo.main_conflict || '任务'}的线索前进。前方的道路似乎更加崎岖，但你心中充满了决心。${attrScene}${flowWorldline.quest_progress || '你需要继续推进主线任务。'}`;
                    
                    // 生成多样化的选项
                    nextOptions = [
                        '使用智慧寻找捷径',
                        '凭借体力强行突破',
                        '小心谨慎地前进',
                        '寻找其他探索路径'
                    ];
                } else if (selectedOption.includes('查看周围环境')) {
                    // 根据角色属性生成不同的剧情
                    let attrScene = '';
                    if (protagonistAttr.智商 === '高') {
                        attrScene = '你很快发现了一些之前没有注意到的细节和线索。';
                    } else if (protagonistAttr.颜值 === '高') {
                        attrScene = '你的美貌吸引了一些NPC的注意，他们主动向你提供了一些有用的信息。';
                    } else {
                        attrScene = '你仔细观察，发现了一些可能有用的线索。';
                    }
                    
                    nextScene = `你仔细观察周围的环境，${attrScene}${flowWorldline.quest_progress || '这些发现可能会对你的任务有所帮助。'}`;
                    
                    // 生成多样化的选项
                    nextOptions = [
                        '深入分析这些发现',
                        '记录这些发现，继续前进',
                        '根据发现调整行动计划',
                        '寻找更多的线索'
                    ];
                } else if (selectedOption.includes('检查角色状态')) {
                    // 根据角色属性生成不同的剧情
                    let attrScene = '';
                    if (protagonistAttr.体力 === '低') {
                        attrScene = '你感觉有些疲惫，需要休息一下。';
                    } else if (protagonistAttr.魅力 === '高') {
                        attrScene = '你的魅力让同伴对你充满了信心。';
                    } else {
                        attrScene = '你和同伴的状态都还不错，可以继续前进。';
                    }
                    
                    nextScene = `你检查了自己和同伴的状态，${attrScene}${flowWorldline.quest_progress || '大家都还保持着良好的状态，可以继续前进。'}`;
                    
                    // 生成多样化的选项
                    nextOptions = [
                        '继续前进，保持当前状态',
                        '调整战术，更好地利用每个人的优势',
                        '分配资源，确保大家都能保持最佳状态',
                        '制定应急计划，应对可能的危险'
                    ];
                } else if (selectedOption.includes('了解当前任务')) {
                    // 根据角色属性生成不同的剧情
                    let attrScene = '';
                    if (protagonistAttr.智商 === '高') {
                        attrScene = '你很快理解了任务的核心内容和要求。';
                    } else {
                        attrScene = '你仔细回顾了任务目标，确认了需要做什么。';
                    }
                    
                    nextScene = `你仔细回顾了当前的任务目标，${attrScene}确认了${chapterInfo.main_conflict || '任务的核心内容'}。${flowWorldline.quest_progress || '你需要继续推进任务，完成当前章节的目标。'}`;
                    
                    // 生成多样化的选项
                    nextOptions = [
                        '制定详细的行动计划',
                        '寻找更多关于任务的信息',
                        '联系其他可能提供帮助的人',
                        '直接前往任务目标地点'
                    ];
                } else {
                    // 默认情况，生成更丰富的剧情和选项
                    nextScene = `你选择了${selectedOption}，剧情按此方向推进。前方的道路充满未知，你需要谨慎应对每一个选择。${flowWorldline.quest_progress || '你需要继续推进主线任务。'}`;
                    
                    // 生成多样化的选项
                    nextOptions = [
                        '继续沿着当前方向前进',
                        '探索周围的区域',
                        '与同伴讨论下一步行动',
                        '考虑是否需要调整计划'
                    ];
                }
                
                console.log('本地生成的场景:', nextScene);
                console.log('本地生成的选项:', nextOptions);
                
                // 更新世界线的主线进度
                if (gameState.gameData.flow_worldline) {
                    gameState.gameData.flow_worldline.quest_progress = nextScene.substring(0, 100) + '...';
                    
                    // 检查章节矛盾是否解决
                    if (gameState.chapterProgress >= 100) {
                        gameState.gameData.flow_worldline.chapter_conflict_solved = true;
                    }
                    
                    // 每次选择后更新结局内容
                    //updateEndingContent();
                }
                    
                    // 显示下一段剧情
                displayScene(nextScene, nextOptions);
            }

                }, 500);
            });
            
            fragment.appendChild(optionCard);
        });
        
        // 清空并一次性插入所有选项，减少回流
        elements.content.optionsList.innerHTML = '';
        elements.content.optionsList.appendChild(fragment);
    }
    
    // 解锁深层背景
    function unlockDeepBackground(charName, content) {
        // 添加到已解锁列表
        if (!gameState.unlockedDeepBackgrounds.includes(charName)) {
            gameState.unlockedDeepBackgrounds.push(charName);
        }
        
        // 更新游戏数据中角色的深层背景解锁状态（与后端一致）
        if (gameState.gameData.flow_worldline.characters[charName]) {
            gameState.gameData.flow_worldline.characters[charName].deep_background_unlocked = true;
            gameState.gameData.flow_worldline.characters[charName].deep_background_depth = 1;
        }
        
        // 更新世界线的深层背景解锁标记
        if (!gameState.gameData.flow_worldline.deep_background_unlocked_flag) {
            gameState.gameData.flow_worldline.deep_background_unlocked_flag = [];
        }
        if (!gameState.gameData.flow_worldline.deep_background_unlocked_flag.includes(charName)) {
            gameState.gameData.flow_worldline.deep_background_unlocked_flag.push(charName);
        }
        
        // 创建弹窗
        const modal = document.createElement('div');
        modal.className = 'unlock-toast fixed inset-0 bg-black/70 flex items-center justify-center z-50 animate-fadeIn';
        modal.innerHTML = `
            <div class="w-[400px] h-[220px] bg-[rgba(0,0,0,0.8)] backdrop-blur-sm rounded-[12px] border-2 border-[#9B59B6] p-[25px] animate-zoomIn">
                <div class="flex items-center mb-4">
                    <div class="w-[32px] h-[32px] bg-[#9B59B6]/30 rounded-full flex items-center justify-center mr-3">
                        <i class="fa fa-unlock text-[#9B59B6] text-xl"></i>
                    </div>
                    <h3 class="text-[20px] font-bold text-[#9B59B6]">解锁深层背景</h3>
                </div>
                <div class="text-[16px] text-white leading-[1.5] mb-6">
                    <span class="text-[#9B59B6] font-bold">${charName}的过往：</span>${content}
                </div>
                <button class="close-unlock-btn text-[14px] text-white hover:text-[#9B59B6] self-end">关闭</button>
            </div>
        `;
        document.body.appendChild(modal);
        
        // 关闭按钮事件
        modal.querySelector('.close-unlock-btn').addEventListener('click', () => {
            modal.style.opacity = '0';
            modal.style.transition = 'opacity 200ms ease';
            setTimeout(() => {
                document.body.removeChild(modal);
            }, 200);
        });
        
        // 5秒后自动关闭
        setTimeout(() => {
            if (document.body.contains(modal)) {
                modal.style.opacity = '0';
                setTimeout(() => {
                    document.body.removeChild(modal);
                }, 200);
            }
        }, 5000);
        
        // 触发结局主基调修改（与后端modify_ending_tone一致）
        modifyEndingTone(`解锁了${charName}的深层背景：${content.substring(0, 50)}...`);
        
        playSound('unlock');
    }
    
    // 修改结局主基调（与后端modify_ending_tone函数一致）
    function modifyEndingTone(triggerEvent) {
        // 随机模拟结局主基调变化，实际项目中会调用后端API
        const toneOptions = ['HE', 'BE', 'NE'];
        const newTone = toneOptions[Math.floor(Math.random() * toneOptions.length)];
        
        // 更新结局预测
        gameState.gameData.hidden_ending_prediction.main_tone = newTone;
        
        // 根据新的主基调更新结局内容
        //updateEndingContent();
        
        console.log(`结局主基调已修改：${gameState.gameData.hidden_ending_prediction.main_tone}，触发事件：${triggerEvent}`);
    }
    
    // 更新结局内容（与后端modify_ending_content函数一致）
    /*
    function updateEndingContent() {
        const currentTone = gameState.gameData.hidden_ending_prediction.main_tone;
        const currentContent = gameState.gameData.hidden_ending_prediction.content;
        
        // 根据主基调更新结局内容
        let newContent = currentContent;
        switch(currentTone) {
            case 'HE':
                newContent = '主角成功达成所有目标，与重要角色和解，获得圆满结局';
                break;
            case 'BE':
                newContent = '主角虽然努力奋斗，但最终未能达成目标，付出了巨大代价';
                break;
            case 'NE':
                newContent = '主角完成了主要任务，虽然过程中经历了许多困难，但最终达成了预期目标';
                break;
        }
        
        gameState.gameData.hidden_ending_prediction.content = newContent;
    }
    */
    // 显示爽点触发提示
    function showSuperToast(text) {
        const toast = document.createElement('div');
        toast.className = 'super-toast';
        toast.innerHTML = `
            <i class="fa fa-star text-yellow-400 text-2xl mb-2 animate-bounce"></i>
            <div>${text}</div>
        `;
        document.body.appendChild(toast);
        
        // 3秒后渐隐
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 300ms ease';
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 300);
        }, 3000);
        
        playSound('super');
    }
    
    // 显示结局屏幕
    function showEndingScreen() {
        // 根据结局主基调获取对应的中文描述
        const toneMap = {
            'HE': '圆满结局',
            'BE': '悲剧结局',
            'NE': '普通结局'
        };
        
        const endingTone = gameState.gameData.hidden_ending_prediction.main_tone;
        const endingContent = gameState.gameData.hidden_ending_prediction.content;
        
        // 更新结局屏幕内容
        elements.content.endingTitle.textContent = `${toneMap[endingTone]} - ${gameState.gameTheme}`;
        elements.content.endingContent.textContent = endingContent;
        
        // 根据基调设置不同的背景
        let endingBg = '';
        switch(endingTone) {
            case 'HE':
                endingBg = 'linear-gradient(135deg, rgba(46,204,113,0.8), rgba(26,188,156,0.8))';
                break;
            case 'BE':
                endingBg = 'linear-gradient(135deg, rgba(155,89,182,0.8), rgba(142,68,173,0.8))';
                break;
            case 'NE':
                endingBg = 'linear-gradient(135deg, rgba(52,152,219,0.8), rgba(41,128,185,0.8))';
                break;
        }
        elements.screens.ending.style.background = endingBg;
        
        // 显示结局屏幕
        switchScreen('ending');
        playSound('ending');
    }
    
    // 更新章节进度
    function updateChapterProgress(percent) {
        gameState.chapterProgress = percent;
        elements.content.progressFill.style.width = `${percent}%`;
        elements.content.progressFill.style.transition = 'width 300ms ease';
        
        // 进度状态标识
        let statusText = '';
        let statusColor = '';
        if (percent < 30) {
            statusText = '探索中';
            statusColor = 'text-blue-500';
        } else if (percent < 70) {
            statusText = '推进中';
            statusColor = 'text-orange-500';
        } else {
            statusText = '即将解决';
            statusColor = 'text-green-500';
        }
        
        if (elements.content.conflictStatusText) {
            elements.content.conflictStatusText.textContent = statusText;
            elements.content.conflictStatusText.className = `conflict-status text-[14px] ${statusColor}`;
        }
    }
    
    // 保存游戏状态（调用后端API，同时保留localStorage缓存）
    // isUpdate: 如果为true，表示更新原存档；如果为false，表示保存为新存档
    async function saveGame(saveName, isUpdate = false) {
        // 准备发送给后端的数据（与main2.py中的格式保持一致）
        // 将当前场景保存到 flow_worldline 中
        const gameDataCopy = JSON.parse(JSON.stringify(gameState.gameData || {}));
        if (!gameDataCopy.flow_worldline) {
            gameDataCopy.flow_worldline = {};
        }
        gameDataCopy.flow_worldline.current_scene = gameState.currentScene || '';
        
        const saveData = {
            saveName: saveName || `存档${(JSON.parse(localStorage.getItem('gameSaves')) || []).length + 1}`,
            globalState: gameDataCopy, // 完整的后端数据结构（包含当前场景）
            protagonistAttr: {...gameState.protagonistAttr},
            difficulty: gameState.selectedDifficulty || '',
            lastOptions: [...gameState.currentOptions]
        };
        
        console.log('准备保存游戏，存档名称:', saveData.saveName, '是否更新:', isUpdate);
        console.log('游戏数据:', saveData.globalState);
        
        // 调用后端API保存游戏
        try {
            const response = await fetch('http://127.0.0.1:5001/save-game', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(saveData)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            console.log('后端保存响应:', result);
            
            if (result.status === 'success') {
                // 后端保存成功，同时更新localStorage缓存
                const gameSave = {
                    name: saveData.saveName,
                    time: new Date().toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }),
                    progress: `${gameState.gameData?.flow_worldline?.current_chapter === 'chapter1' ? '第一章' : gameState.gameData?.flow_worldline?.current_chapter === 'chapter2' ? '第二章' : '第三章'} ${gameState.chapterProgress || 0}%`,
                    gameState: {
                        protagonistAttr: {...gameState.protagonistAttr},
                        gameTheme: gameState.gameTheme,
                        currentScene: gameState.currentScene,
                        currentOptions: [...gameState.currentOptions],
                        chapterProgress: gameState.chapterProgress,
                        unlockedDeepBackgrounds: [...gameState.unlockedDeepBackgrounds],
                        currentTone: gameState.currentTone,
                        gameData: JSON.parse(JSON.stringify(gameState.gameData || {}))
                    }
                };
                
                // 保存到本地存储（作为缓存）
                const saves = JSON.parse(localStorage.getItem('gameSaves')) || [];
                const existingSaveIndex = saves.findIndex(save => save.name === gameSave.name);
                
                if (existingSaveIndex >= 0) {
                    saves[existingSaveIndex] = gameSave;
                } else {
                    saves.push(gameSave);
                }
                
                localStorage.setItem('gameSaves', JSON.stringify(saves));
                playSound('save');
                
                const message = isUpdate ? `游戏已成功更新：${saveData.saveName}` : `游戏已成功保存：${saveData.saveName}`;
                showModal('保存成功', message, () => {});
            } else {
                // 后端保存失败，提示用户重试
                console.error('后端保存失败:', result.message);
                showModal('保存失败', result.message || '保存失败，请重试', () => {});
            }
        } catch (error) {
            console.error('保存游戏失败:', error);
            showModal('保存失败', `保存失败，请重试：${error.message}`, () => {});
        }
    }
    
    // 展示主角形象（全屏）
    function showMainCharacterImage(imageUrl, onContinue) {
        // 创建全屏展示面板
        const characterPanel = document.createElement('div');
        characterPanel.id = 'main-character-panel';
        characterPanel.className = 'fixed inset-0 bg-black/95 flex flex-col items-center justify-center z-[100]';
        characterPanel.innerHTML = `
            <div class="character-content flex flex-col items-center justify-center max-w-4xl w-full px-8 animate-fade-in">
                <div class="character-title text-[32px] font-bold text-white mb-8 text-center">
                    这是你的主角形象
                </div>
                <div class="character-image-container mb-8 relative">
                    <img 
                        id="main-character-img" 
                        src="${imageUrl}" 
                        alt="主角形象" 
                        class="max-w-full max-h-[70vh] object-contain rounded-lg shadow-2xl"
                        style="animation: fadeIn 0.5s ease-in;"
                    />
                    <div id="character-loading" class="absolute inset-0 flex items-center justify-center bg-black/50 rounded-lg" style="display: none;">
                        <div class="text-center">
                            <div class="loading-spinner w-[60px] h-[60px] rounded-full border-[6px] border-[#1ABC9C] border-t-transparent animate-spin mx-auto mb-4"></div>
                            <p class="text-white text-lg">加载中...</p>
                        </div>
                    </div>
                </div>
                <button 
                    id="character-continue-btn" 
                    class="w-[200px] h-[50px] rounded-[8px] bg-[#1ABC9C] text-[18px] font-bold text-white transition-all hover:bg-[#16A085] hover:scale-105 active:scale-95 shadow-lg"
                >
                    继续
                </button>
            </div>
        `;
        document.body.appendChild(characterPanel);
        
        // 图片加载处理
        const img = characterPanel.querySelector('#main-character-img');
        const loadingDiv = characterPanel.querySelector('#character-loading');
        
        img.onload = () => {
            loadingDiv.style.display = 'none';
        };
        
        img.onerror = () => {
            loadingDiv.style.display = 'none';
            console.error('❌ 主角形象图片加载失败');
            // 如果图片加载失败，显示错误提示
            const errorMsg = document.createElement('div');
            errorMsg.className = 'text-red-500 text-center mt-4';
            errorMsg.textContent = '图片加载失败，但可以继续游戏';
            characterPanel.querySelector('.character-image-container').appendChild(errorMsg);
        };
        
        // 继续按钮事件
        const continueBtn = characterPanel.querySelector('#character-continue-btn');
        continueBtn.addEventListener('click', () => {
            // 隐藏动画
            characterPanel.style.opacity = '0';
            characterPanel.style.transition = 'opacity 0.3s ease-out';
            setTimeout(() => {
                document.body.removeChild(characterPanel);
                if (onContinue) {
                    onContinue();
                }
            }, 300);
        });
        
        // 按ESC键关闭
        const handleEsc = (e) => {
            if (e.key === 'Escape') {
                characterPanel.style.opacity = '0';
                characterPanel.style.transition = 'opacity 0.3s ease-out';
                setTimeout(() => {
                    document.body.removeChild(characterPanel);
                    document.removeEventListener('keydown', handleEsc);
                    if (onContinue) {
                        onContinue();
                    }
                }, 300);
            }
        };
        document.addEventListener('keydown', handleEsc);
    }
    
    // 检查并等待主角形象生成完成
    async function showMainCharacterIfReady(onContinue) {
        try {
            // 检查 globalState 中是否有主角形象信息
            const mainCharacter = gameState.gameData?.main_character;
            const gameId = gameState.gameData?.game_id;
            
            if (!gameId) {
                console.warn('⚠️ 没有游戏ID，跳过主角形象展示');
                if (onContinue) onContinue();
                return;
            }
            
            // 构建主角形象图片URL
            const imageUrl = mainCharacter && mainCharacter.image_url
                ? (mainCharacter.image_url.startsWith('http') 
                    ? mainCharacter.image_url 
                    : `http://127.0.0.1:5001${mainCharacter.image_url}`)
                : `http://127.0.0.1:5001/initial/main_character/${gameId}/main_character.png`;
            
            // 检查图片是否存在（通过尝试加载）
            const checkImageExists = () => {
                return new Promise((resolve) => {
                    const img = new Image();
                    img.onload = () => resolve(true);
                    img.onerror = () => resolve(false);
                    img.src = imageUrl;
                });
            };
            
            // 如果已经有主角形象信息，直接展示
            if (mainCharacter && mainCharacter.image_url) {
                console.log('✅ 主角形象已生成，开始展示');
                showMainCharacterImage(imageUrl, onContinue);
                return;
            }
            
            // 如果主角形象还未生成，等待生成完成
            console.log('⏳ 主角形象还在生成中，等待完成...');
            const maxWaitTime = 300000; // 5分钟
            const checkInterval = 2000; // 每2秒检查一次
            const startTime = Date.now();
            
            const checkMainCharacter = async () => {
                try {
                    const exists = await checkImageExists();
                    
                    if (exists) {
                        console.log('✅ 主角形象生成完成，开始展示');
                        // 更新 gameState
                        if (!gameState.gameData.main_character) {
                            gameState.gameData.main_character = {
                                game_id: gameId,
                                image_url: `/initial/main_character/${gameId}/main_character.png`
                            };
                        }
                        showMainCharacterImage(imageUrl, onContinue);
                        return;
                    }
                    
                    // 如果还没生成完成，检查是否超时
                    if (Date.now() - startTime < maxWaitTime) {
                        // 继续等待
                        setTimeout(checkMainCharacter, checkInterval);
                    } else {
                        // 超时，跳过展示
                        console.warn('⚠️ 主角形象生成超时，跳过展示');
                        if (onContinue) onContinue();
                    }
                } catch (error) {
                    console.error('❌ 检查主角形象状态失败:', error);
                    // 出错时跳过展示
                    if (onContinue) onContinue();
                }
            };
            
            // 开始检查
            setTimeout(checkMainCharacter, checkInterval);
            
        } catch (error) {
            console.error('❌ 检查主角形象失败:', error);
            // 出错时跳过展示，继续游戏
            if (onContinue) onContinue();
        }
    }
    
    // 显示世界观和世界线信息面板
    function showWorldviewInfoPanel(worldview, worldline, onConfirm) {
        // 创建信息面板
        const infoPanel = document.createElement('div');
        infoPanel.id = 'worldview-info-panel';
        infoPanel.className = 'fixed inset-0 bg-black/80 flex items-center justify-center z-50';
        infoPanel.innerHTML = `
            <div class="info-panel-content bg-[rgba(0,0,0,0.9)] backdrop-blur-sm rounded-[12px] p-8 max-w-3xl w-full mx-4 max-h-[80vh] overflow-y-auto transition-all duration-300 transform scale-95 opacity-0">
                <div class="info-panel-header mb-6">
                    <h2 class="text-[24px] font-bold text-white mb-2">游戏信息</h2>
                    <div class="text-[14px] text-[#999999]">请查看当前游戏的世界观和进度</div>
                </div>
                <div class="info-panel-body space-y-6">
                    <div class="worldview-section">
                        <h3 class="text-[18px] font-bold text-[#1ABC9C] mb-3">世界观摘要</h3>
                        <div class="worldview-content text-[16px] text-white leading-[1.8] bg-[rgba(255,255,255,0.05)] p-4 rounded-[8px]">
                            ${worldview || '暂无世界观信息'}
                        </div>
                    </div>
                    <div class="worldline-section">
                        <h3 class="text-[18px] font-bold text-[#1ABC9C] mb-3">当前章节进度</h3>
                        <div class="worldline-content text-[16px] text-white leading-[1.8] bg-[rgba(255,255,255,0.05)] p-4 rounded-[8px]">
                            ${worldline || '暂无世界线信息'}
                        </div>
                    </div>
                </div>
                <div class="info-panel-footer mt-8 flex justify-end">
                    <button id="info-panel-confirm-btn" class="w-[120px] h-[45px] rounded-[8px] bg-[#1ABC9C] text-[16px] font-bold text-white transition-all hover:bg-[#16A085]">
                        确定
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(infoPanel);
        
        // 显示动画
        setTimeout(() => {
            const content = infoPanel.querySelector('.info-panel-content');
            content.style.transform = 'scale(1)';
            content.style.opacity = '1';
        }, 50);
        
        // 确认按钮事件
        const confirmBtn = infoPanel.querySelector('#info-panel-confirm-btn');
        confirmBtn.addEventListener('click', () => {
            // 隐藏动画
            const content = infoPanel.querySelector('.info-panel-content');
            content.style.transform = 'scale(0.95)';
            content.style.opacity = '0';
            setTimeout(() => {
                document.body.removeChild(infoPanel);
                if (onConfirm) {
                    onConfirm();
                }
            }, 300);
        });
        
        // 按ESC键关闭
        const handleEsc = (e) => {
            if (e.key === 'Escape') {
                const content = infoPanel.querySelector('.info-panel-content');
                content.style.transform = 'scale(0.95)';
                content.style.opacity = '0';
                setTimeout(() => {
                    document.body.removeChild(infoPanel);
                    document.removeEventListener('keydown', handleEsc);
                    if (onConfirm) {
                        onConfirm();
                    }
                }, 300);
            }
        };
        document.addEventListener('keydown', handleEsc);
    }
    
    // 加载游戏状态（从后端加载，同时更新localStorage缓存）
    async function loadGameState(saveName) {
        try {
            // 调用后端API加载存档
            const response = await fetch('http://127.0.0.1:5001/load-game', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    saveName: saveName
                })
            });
            
            const result = await response.json();
            
            if (result.status === 'success' && result.saveData) {
                const saveData = result.saveData;
                
                // 恢复游戏状态（从后端数据格式转换）
                gameState.gameData = JSON.parse(JSON.stringify(saveData.global_state || {}));
                gameState.protagonistAttr = {...(saveData.protagonist_attr || {})};
                gameState.selectedDifficulty = saveData.difficulty || '';
                
                // 恢复当前场景和选项
                const lastOptions = saveData.last_options || [];
                gameState.currentOptions = [...lastOptions];
                
                // 从flow_worldline中提取当前场景（如果有）
                const flowWorldline = gameState.gameData.flow_worldline || {};
                gameState.currentScene = flowWorldline.current_scene || '';
                
                // 计算章节进度（从flow_worldline中获取）
                const currentChapter = flowWorldline.current_chapter || 'chapter1';
                gameState.chapterProgress = flowWorldline.chapter_progress || 0;
                
                // 恢复其他状态
                gameState.unlockedDeepBackgrounds = flowWorldline.unlocked_deep_backgrounds || [];
                gameState.currentTone = gameState.gameData.hidden_ending_prediction?.main_tone || 'normal_ending';
                
                // 标记这是从加载开始的游戏
                gameState.isLoadedGame = true;
                gameState.loadedSaveName = saveName;
                
                // 同步更新localStorage缓存
                const gameSave = {
                    name: saveName,
                    time: saveData.timestamp || new Date().toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }),
                    progress: `${currentChapter === 'chapter1' ? '第一章' : currentChapter === 'chapter2' ? '第二章' : '第三章'} ${gameState.chapterProgress}%`,
                    gameState: {
                        protagonistAttr: {...gameState.protagonistAttr},
                        gameTheme: gameState.gameTheme,
                        currentScene: gameState.currentScene,
                        currentOptions: [...gameState.currentOptions],
                        chapterProgress: gameState.chapterProgress,
                        unlockedDeepBackgrounds: [...gameState.unlockedDeepBackgrounds],
                        currentTone: gameState.currentTone,
                        gameData: JSON.parse(JSON.stringify(gameState.gameData))
                    }
                };
                
                const saves = JSON.parse(localStorage.getItem('gameSaves')) || [];
                const existingSaveIndex = saves.findIndex(s => s.name === saveName);
                if (existingSaveIndex >= 0) {
                    saves[existingSaveIndex] = gameSave;
                } else {
                    saves.push(gameSave);
                }
                localStorage.setItem('gameSaves', JSON.stringify(saves));
                
                // 切换到游戏界面
                switchScreen('gameplay');
                updateChapterProgress(gameState.chapterProgress);
                
                // 准备世界观和世界线信息
                const coreWorldview = gameState.gameData.core_worldview || {};
                const worldviewSummary = coreWorldview.world_basic_setting || coreWorldview.game_style || '暂无世界观信息';
                const chapterName = currentChapter === 'chapter1' ? '第一章' : (currentChapter === 'chapter2' ? '第二章' : '第三章');
                const worldlineInfo = `${chapterName}，进度：${gameState.chapterProgress}%`;
                
                // 先显示信息面板，用户点击确定后再显示剧情和选项
                showWorldviewInfoPanel(worldviewSummary, worldlineInfo, () => {
                    // 用户点击确定后，显示当前场景和选项
                    if (gameState.currentScene) {
                        displayScene(gameState.currentScene, gameState.currentOptions);
                    } else if (gameState.currentOptions.length > 0) {
                        // 如果没有场景文本，至少显示选项
                        displayScene('', gameState.currentOptions);
                    }
                    playSound('load');
                });
            } else {
                // 后端加载失败，尝试从localStorage加载缓存
                const saves = JSON.parse(localStorage.getItem('gameSaves')) || [];
                const save = saves.find(s => s.name === saveName);
                
                if (save && save.gameState) {
                    // 从缓存恢复游戏状态
                    gameState.protagonistAttr = {...save.gameState.protagonistAttr};
                    gameState.gameTheme = save.gameState.gameTheme;
                    gameState.currentScene = save.gameState.currentScene;
                    gameState.currentOptions = [...save.gameState.currentOptions];
                    gameState.chapterProgress = save.gameState.chapterProgress;
                    gameState.unlockedDeepBackgrounds = [...save.gameState.unlockedDeepBackgrounds];
                    gameState.currentTone = save.gameState.currentTone;
                    gameState.gameData = JSON.parse(JSON.stringify(save.gameState.gameData));
                    
                    // 标记这是从加载开始的游戏
                    gameState.isLoadedGame = true;
                    gameState.loadedSaveName = saveName;
                    
                    // 切换到游戏界面
                    switchScreen('gameplay');
                    updateChapterProgress(gameState.chapterProgress);
                    
                    // 应用字体（根据风格和基调）
                    const imageStyle = gameState.gameData.image_style || gameState.imageStyle;
                    const tone = gameState.currentTone || gameState.tone;
                    FontManager.applyFontToGame(imageStyle, tone);
                    
                    // 准备世界观和世界线信息
                    const coreWorldview = gameState.gameData.core_worldview || {};
                    const worldviewSummary = coreWorldview.world_basic_setting || coreWorldview.game_style || '暂无世界观信息';
                    const flowWorldline = gameState.gameData.flow_worldline || {};
                    const currentChapter = flowWorldline.current_chapter || 'chapter1';
                    const chapterName = currentChapter === 'chapter1' ? '第一章' : (currentChapter === 'chapter2' ? '第二章' : '第三章');
                    const worldlineInfo = `${chapterName}，进度：${gameState.chapterProgress}%`;
                    
                    // 先显示信息面板
                    showWorldviewInfoPanel(worldviewSummary, worldlineInfo, () => {
                        if (gameState.currentScene) {
                            displayScene(gameState.currentScene, gameState.currentOptions);
                        }
                        playSound('load');
                    });
                    showModal('提示', '已从缓存加载存档（后端加载失败）', () => {});
                } else {
                    showModal('加载失败', result.message || '加载失败，请重试', () => {});
                }
            }
        } catch (error) {
            console.error('加载游戏失败:', error);
            // 网络错误，尝试从localStorage加载缓存
            const saves = JSON.parse(localStorage.getItem('gameSaves')) || [];
            const save = saves.find(s => s.name === saveName);
            
            if (save && save.gameState) {
                gameState.protagonistAttr = {...save.gameState.protagonistAttr};
                gameState.gameTheme = save.gameState.gameTheme;
                gameState.currentScene = save.gameState.currentScene;
                gameState.currentOptions = [...save.gameState.currentOptions];
                gameState.chapterProgress = save.gameState.chapterProgress;
                gameState.unlockedDeepBackgrounds = [...save.gameState.unlockedDeepBackgrounds];
                gameState.currentTone = save.gameState.currentTone;
                gameState.gameData = JSON.parse(JSON.stringify(save.gameState.gameData));
                
                // 标记这是从加载开始的游戏
                gameState.isLoadedGame = true;
                gameState.loadedSaveName = saveName;
                
                // 切换到游戏界面
                switchScreen('gameplay');
                updateChapterProgress(gameState.chapterProgress);
                
                // 应用字体（根据风格和基调）
                const imageStyle = gameState.gameData.image_style || gameState.imageStyle;
                const tone = gameState.currentTone || gameState.tone;
                FontManager.applyFontToGame(imageStyle, tone);
                
                // 准备世界观和世界线信息
                const coreWorldview = gameState.gameData.core_worldview || {};
                const worldviewSummary = coreWorldview.world_basic_setting || coreWorldview.game_style || '暂无世界观信息';
                const flowWorldline = gameState.gameData.flow_worldline || {};
                const currentChapter = flowWorldline.current_chapter || 'chapter1';
                const chapterName = currentChapter === 'chapter1' ? '第一章' : (currentChapter === 'chapter2' ? '第二章' : '第三章');
                const worldlineInfo = `${chapterName}，进度：${gameState.chapterProgress}%`;
                
                // 先显示信息面板
                showWorldviewInfoPanel(worldviewSummary, worldlineInfo, () => {
                    if (gameState.currentScene) {
                        displayScene(gameState.currentScene, gameState.currentOptions);
                    }
                    playSound('load');
                });
                showModal('提示', '已从缓存加载存档（网络错误）', () => {});
            } else {
                showModal('加载失败', '加载失败，请重试', () => {});
            }
        }
    }
    
    // 加载存档列表（从后端获取，同时保留localStorage缓存）
    async function loadSaves() {
        const saveContainer = document.querySelector('.save-cards');
        if (!saveContainer) {
            console.error('存档容器不存在');
            return;
        }
        
        // 完全清空现有存档卡片（包括HTML中的默认卡片）
        saveContainer.innerHTML = '';
        
        // 确保只加载一次，避免重复
        if (saveContainer.dataset.loading === 'true') {
            return;
        }
        saveContainer.dataset.loading = 'true';
        
        // 从后端获取存档列表
        let saves = [];
        try {
            const response = await fetch('http://127.0.0.1:5001/list-saves', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            console.log('后端返回的存档列表:', result);
            
            if (result.status === 'success' && result.saves && Array.isArray(result.saves)) {
                // 转换后端数据格式为前端格式
                saves = result.saves.map(save => {
                    // 格式化时间
                    let formattedTime = '';
                    if (save.timestamp) {
                        try {
                            const date = new Date(save.timestamp);
                            formattedTime = date.toLocaleString('zh-CN', { 
                                year: 'numeric', 
                                month: '2-digit', 
                                day: '2-digit', 
                                hour: '2-digit', 
                                minute: '2-digit' 
                            });
                        } catch (e) {
                            formattedTime = save.timestamp;
                        }
                    }
                    
                    return {
                        name: save.name,
                        time: formattedTime,
                        progress: `${save.chapter || '第一章'} 0%` // 进度需要从存档数据中计算，这里先用默认值
                    };
                });
                
                console.log('转换后的存档列表:', saves);
                
                // 同步更新localStorage缓存
                localStorage.setItem('gameSaves', JSON.stringify(saves));
            } else {
                // 后端获取失败，从localStorage读取缓存
                saves = JSON.parse(localStorage.getItem('gameSaves')) || [];
                console.warn('从后端获取存档列表失败，使用缓存:', result.message || '未知错误');
            }
        } catch (error) {
            console.error('获取存档列表失败:', error);
            // 网络错误，从localStorage读取缓存
            saves = JSON.parse(localStorage.getItem('gameSaves')) || [];
        }
        
        // 使用documentFragment批量处理DOM插入，减少回流和重绘
        const fragment = document.createDocumentFragment();
        
        saves.forEach(save => {
            const saveCard = document.createElement('div');
            saveCard.className = 'save-card w-[280px] h-[180px] rounded-[12px] bg-white/10 p-6 flex flex-col justify-between relative cursor-pointer hover:border-2 hover:border-[#1ABC9C] hover:scale-103 transition-all group';
            saveCard.innerHTML = `
                <div class="save-header flex justify-between items-start">
                    <div class="save-name text-[18px] font-bold text-white" contenteditable="true">${save.name}</div>
                    <button class="delete-save text-red-500 hover:text-red-700 opacity-0 group-hover:opacity-100 transition-opacity">
                        <i class="fa fa-times"></i>
                    </button>
                </div>
                <div class="save-info">
                    <div class="save-time text-[14px] text-[#999999]">${save.time}</div>
                    <div class="save-progress text-[14px] text-white text-right">${save.progress}</div>
                </div>
                <div class="selected-mark hidden absolute bottom-4 right-6 text-white">
                    <i class="fa fa-check-circle"></i>
                </div>
            `;
            
            // 存档名称修改后保存
            const nameEl = saveCard.querySelector('.save-name');
            nameEl.addEventListener('blur', () => {
                const newName = nameEl.textContent;
                const validation = inputValidator.validateSaveName(newName);
                if (validation.valid) {
                    // 保存修改到本地存储
                    const updatedSave = saves.find(s => s.name === save.name);
                    if (updatedSave) {
                        updatedSave.name = escapeHtml(newName);
                        updatedSave.time = new Date().toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
                        localStorage.setItem('gameSaves', JSON.stringify(saves));
                        playSound('save');
                    }
                } else {
                    // 恢复原名称
                    nameEl.textContent = save.name;
                    showModal('提示', validation.message, () => {});
                }
            });
            
            fragment.appendChild(saveCard);
        });
        
        // 一次性插入所有存档卡片，减少回流
        saveContainer.appendChild(fragment);
        
        // 添加新建存档按钮（只添加一个）
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = `
            <div class="save-card w-[280px] h-[180px] rounded-[12px] bg-[#3498DB]/30 p-6 flex flex-col items-center justify-center cursor-pointer hover:bg-[#3498DB]/50 transition-all">
                <i class="fa fa-plus text-white text-3xl mb-3"></i>
                <div class="save-name text-[16px] font-bold text-white">新建存档</div>
            </div>
        `;
        const newCard = tempDiv.firstElementChild;
        saveContainer.appendChild(newCard);
        
        // 绑定新建存档按钮事件
        newCard.addEventListener('click', () => {
            const newSave = {
                name: `存档${saves.length + 1}`,
                time: new Date().toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }),
                progress: '第一章 0%'
            };
            saves.push(newSave);
            localStorage.setItem('gameSaves', JSON.stringify(saves));
            saveContainer.dataset.loading = 'false';
            loadSaves(); // 重新加载存档列表
            playSound('save');
        });
        
        // 重置加载标志
        saveContainer.dataset.loading = 'false';
    }
    
    // 删除存档（调用后端API，同时更新localStorage缓存）
    async function deleteSave(saveName) {
        try {
            const response = await fetch('http://127.0.0.1:5001/delete-save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    saveName: saveName
                })
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                // 后端删除成功，同步更新localStorage缓存
                const saves = JSON.parse(localStorage.getItem('gameSaves')) || [];
                const updatedSaves = saves.filter(save => save.name !== saveName);
                localStorage.setItem('gameSaves', JSON.stringify(updatedSaves));
                playSound('delete');
            } else {
                // 后端删除失败，提示用户
                showModal('删除失败', result.message || '删除失败，请重试', () => {});
            }
        } catch (error) {
            console.error('删除存档失败:', error);
            showModal('删除失败', '删除失败，请重试', () => {});
        }
    }
    
    // 显示弹窗
    function showModal(title, text, confirmCallback, showCancel = true) {
        elements.modal.title.textContent = title;
        elements.modal.text.textContent = text;
        elements.modal.container.classList.remove('hidden');
        setTimeout(() => {
            elements.modal.content.classList.add('scale-100', 'opacity-100');
        }, 50);
        
        // 是否显示取消按钮
        if (!showCancel) {
            elements.modal.cancel.classList.add('hidden');
        } else {
            elements.modal.cancel.classList.remove('hidden');
        }
        
        // 确认按钮事件
        elements.modal.confirm.onclick = () => {
            hideModal();
            confirmCallback();
        };
        
        // 取消按钮事件
        elements.modal.cancel.onclick = hideModal;
        
        // 关闭按钮事件
        elements.modal.close.onclick = hideModal;
    }
    
    // 隐藏弹窗
    function hideModal() {
        elements.modal.content.classList.remove('scale-100', 'opacity-100');
        setTimeout(() => {
            elements.modal.container.classList.add('hidden');
        }, 300);
    }
    
    // 退出确认弹窗（主菜单使用）
    function showExitConfirmModal() {
        showModal('确认退出', '确定要退出游戏吗？未保存的进度将丢失', () => {
            window.close();
        });
    }
    
    // 游戏内退出确认弹窗（包含存档选项）
    function showInGameExitConfirmModal() {
        // 判断是否是加载的游戏
        const isLoadedGame = gameState.isLoadedGame && gameState.loadedSaveName;
        const loadedSaveName = gameState.loadedSaveName || '';
        
        // 创建自定义弹窗，包含退出确认和存档选项
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black/70 flex items-center justify-center z-50';
        
        // 根据是否是加载的游戏，显示不同的选项
        let saveOptionsHTML = '';
        if (isLoadedGame) {
            // 加载的游戏：显示三个选项（更新原存档/保存为新存档/不保存）
            saveOptionsHTML = `
                <div class="save-options mb-4 space-y-3">
                    <label class="flex items-center cursor-pointer">
                        <input type="radio" name="save-option" value="update" class="mr-2 w-4 h-4" checked>
                        <span class="text-[16px] text-white">更新原存档（${loadedSaveName}）</span>
                    </label>
                    <label class="flex items-center cursor-pointer">
                        <input type="radio" name="save-option" value="new" class="mr-2 w-4 h-4">
                        <span class="text-[16px] text-white">保存为新存档</span>
                    </label>
                    <label class="flex items-center cursor-pointer">
                        <input type="radio" name="save-option" value="none" class="mr-2 w-4 h-4">
                        <span class="text-[16px] text-white">不保存</span>
                    </label>
                </div>
                <div id="save-name-input-container" class="hidden mb-4">
                    <label class="block text-[14px] text-white mb-2">存档名称：</label>
                    <input type="text" id="exit-save-name" class="w-full h-[40px] bg-[rgba(255,255,255,0.1)] border-2 border-[#3498DB] rounded-[4px] text-white px-3 outline-none" placeholder="请输入存档名称" maxlength="15">
                    <div class="text-[12px] text-[#999999] mt-1">最多15个字符</div>
                </div>
            `;
        } else {
            // 新游戏：显示两个选项（保存为新存档/不保存）
            saveOptionsHTML = `
                <div class="save-options mb-4 space-y-3">
                    <label class="flex items-center cursor-pointer">
                        <input type="radio" name="save-option" value="new" class="mr-2 w-4 h-4" checked>
                        <span class="text-[16px] text-white">保存为新存档</span>
                    </label>
                    <label class="flex items-center cursor-pointer">
                        <input type="radio" name="save-option" value="none" class="mr-2 w-4 h-4">
                        <span class="text-[16px] text-white">不保存</span>
                    </label>
                </div>
                <div id="save-name-input-container" class="mb-4">
                    <label class="block text-[14px] text-white mb-2">存档名称：</label>
                    <input type="text" id="exit-save-name" class="w-full h-[40px] bg-[rgba(255,255,255,0.1)] border-2 border-[#3498DB] rounded-[4px] text-white px-3 outline-none" placeholder="请输入存档名称" maxlength="15">
                    <div class="text-[12px] text-[#999999] mt-1">最多15个字符</div>
                </div>
            `;
        }
        
        modal.innerHTML = `
            <div class="modal-content bg-[rgba(0,0,0,0.8)] backdrop-blur-sm rounded-[8px] p-6 transition-all duration-300 transform scale-95 opacity-0" style="min-width: 400px;">
                <div class="modal-header flex justify-between items-center mb-4">
                    <h3 class="modal-title text-[18px] font-bold text-white">确认退出游戏</h3>
                    <button class="close-exit-modal text-white hover:text-[#E74C3C]">
                        <i class="fa fa-times"></i>
                    </button>
                </div>
                <div class="modal-body mb-6">
                    <p class="modal-text text-[16px] text-white mb-4">确定要退出当前游戏吗？</p>
                    ${saveOptionsHTML}
                </div>
                <div class="modal-footer flex justify-end gap-4">
                    <button class="btn-modal cancel w-[100px] h-[40px] rounded-[4px] bg-[#7F8C8D] text-white transition-all" id="exit-modal-cancel">取消</button>
                    <button class="btn-modal confirm w-[100px] h-[40px] rounded-[4px] bg-[#1ABC9C] text-white transition-all" id="exit-modal-confirm">确认</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        // 显示动画
        setTimeout(() => {
            const content = modal.querySelector('.modal-content');
            content.style.transform = 'scale(1)';
            content.style.opacity = '1';
        }, 50);
        
        // 存档选项切换
        const saveOptions = modal.querySelectorAll('input[name="save-option"]');
        const saveNameContainer = modal.querySelector('#save-name-input-container');
        const saveNameInput = modal.querySelector('#exit-save-name');
        
        saveOptions.forEach(option => {
            option.addEventListener('change', () => {
                if (option.value === 'new') {
                    saveNameContainer.classList.remove('hidden');
                    saveNameInput.focus();
                } else {
                    saveNameContainer.classList.add('hidden');
                }
            });
        });
        
        // 关闭按钮
        const closeBtn = modal.querySelector('.close-exit-modal');
        const cancelBtn = modal.querySelector('#exit-modal-cancel');
        const confirmBtn = modal.querySelector('#exit-modal-confirm');
        
        const closeModal = () => {
            const content = modal.querySelector('.modal-content');
            content.style.transform = 'scale(0.95)';
            content.style.opacity = '0';
            setTimeout(() => {
                document.body.removeChild(modal);
            }, 300);
        };
        
        closeBtn.addEventListener('click', closeModal);
        cancelBtn.addEventListener('click', closeModal);
        
        // 确认按钮
        confirmBtn.addEventListener('click', async () => {
            const selectedOption = modal.querySelector('input[name="save-option"]:checked').value;
            
            if (selectedOption === 'update') {
                // 更新原存档
                try {
                    closeModal();
                    await saveGame(loadedSaveName, true);
                    setTimeout(() => {
                        switchScreen('menu');
                        playSound('switch');
                    }, 2000);
                } catch (error) {
                    console.error('更新存档失败:', error);
                    showModal('提示', '更新存档失败，请重试', () => {}, false);
                }
            } else if (selectedOption === 'new') {
                // 保存为新存档
                const saveName = saveNameInput.value.trim();
                if (!saveName) {
                    showModal('提示', '请输入存档名称', () => {}, false);
                    return;
                }
                
                // 验证存档名称
                const validation = inputValidator.validateSaveName(saveName);
                if (!validation.valid) {
                    showModal('提示', validation.message, () => {}, false);
                    return;
                }
                
                try {
                    closeModal();
                    await saveGame(saveName, false);
                    setTimeout(() => {
                        switchScreen('menu');
                        playSound('switch');
                    }, 2000);
                } catch (error) {
                    console.error('保存游戏失败:', error);
                    showModal('提示', '保存游戏失败，请重试', () => {}, false);
                }
            } else {
                // 不保存，直接返回主菜单
                closeModal();
                switchScreen('menu');
                playSound('switch');
            }
        });
        
        // 按ESC键关闭
        const handleEsc = (e) => {
            if (e.key === 'Escape') {
                closeModal();
                document.removeEventListener('keydown', handleEsc);
            }
        };
        document.addEventListener('keydown', handleEsc);
    }
    
    // 初始化事件监听
    function initEventListeners() {
        // 主菜单按钮
        elements.buttons.start.addEventListener('click', () => switchScreen('attrSelection'));
        elements.buttons.load.addEventListener('click', () => {
            switchScreen('saveManagement');
            // loadSaves() 会在 switchScreen 中自动调用，不需要重复调用
        });
        elements.buttons.saveManage.addEventListener('click', () => {
            switchScreen('saveManagement');
            // loadSaves() 会在 switchScreen 中自动调用，不需要重复调用
        });
        elements.buttons.exit.addEventListener('click', showExitConfirmModal);
        
        // 属性选择按钮
        elements.buttons.confirmAttr.addEventListener('click', () => {
            switchScreen('difficultySelection');
        });
        elements.buttons.resetAttr.addEventListener('click', resetAttributes);
        
        // 属性选项点击事件
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('attr-option-btn')) {
                const optionBtn = e.target;
                const attrOptions = optionBtn.parentElement;
                const attrName = attrOptions.dataset.attr;
                const attrValue = optionBtn.dataset.value;
                
                // 更新属性状态
                gameState.protagonistAttr[attrName] = attrValue;
                
                // 更新UI样式
                attrOptions.querySelectorAll('.attr-option-btn').forEach(btn => {
                    btn.className = 'attr-option-btn px-4 py-2 rounded-lg bg-[#7F8C8D] text-white transition-all hover:bg-[#95A5A6]';
                });
                optionBtn.className = 'attr-option-btn px-4 py-2 rounded-lg bg-[#3498DB] text-white transition-all hover:bg-[#2980B9]';
                
                playSound('select');
            }
        });
        
        // 难度选择卡片
        document.querySelectorAll('.difficulty-card').forEach(card => {
            card.addEventListener('click', () => {
                document.querySelectorAll('.difficulty-card').forEach(c => {
                    c.classList.remove('selected', 'border-3', 'translate-y-[-5px]');
                    c.querySelector('.selected-mark').classList.add('hidden');
                });
                // 选中效果
                const difficulty = card.dataset.difficulty;
                let borderColor = '';
                let textColor = '';
                switch(difficulty) {
                    case '简单': borderColor = 'border-green-500'; textColor = 'text-green-500'; break;
                    case '中等': borderColor = 'border-[#F39C12]'; textColor = 'text-[#F39C12]'; break;
                    case '困难': borderColor = 'border-[#E74C3C]'; textColor = 'text-[#E74C3C]'; break;
                }
                card.classList.add('selected', 'border-3', 'translate-y-[-5px]', borderColor, `shadow-[0_0_20px_${borderColor.replace('border-', '')}]`);
                card.querySelector('.selected-mark').classList.remove('hidden');
                card.querySelector('.selected-mark').className = `selected-mark ${textColor}`;
                gameState.selectedDifficulty = difficulty;
                elements.buttons.confirmDifficulty.classList.remove('bg-[#7F8C8D]', 'cursor-not-allowed');
                elements.buttons.confirmDifficulty.classList.add('bg-[#27AE60]', 'cursor-pointer');
                playSound('select');
            });
        });
        elements.buttons.confirmDifficulty.addEventListener('click', () => {
            if (gameState.selectedDifficulty) {
                switchScreen('toneSelection');
            } else {
                showModal('提示', '请选择游戏难度', () => {});
            }
        });
        
        // 基调选择卡片
        document.querySelectorAll('.tone-card').forEach(card => {
            card.addEventListener('click', () => {
                document.querySelectorAll('.tone-card').forEach(c => c.classList.remove('selected'));
                card.classList.add('selected');
                gameState.selectedTone = card.dataset.tone;
                gameState.currentTone = card.dataset.tone;
                
                // 背景渐变切换
                let gradient = '';
                switch(card.dataset.tone) {
                    case 'happy_ending': gradient = 'linear-gradient(135deg, rgba(46,204,113,0.3), rgba(26,188,156,0.3))'; break;
                    case 'bad_ending': gradient = 'linear-gradient(135deg, rgba(155,89,182,0.3), rgba(142,68,173,0.3))'; break;
                    case 'normal_ending': gradient = 'linear-gradient(135deg, rgba(52,152,219,0.3), rgba(41,128,185,0.3))'; break;
                    case 'dark_depressing': gradient = 'linear-gradient(135deg, rgba(52,73,94,0.5), rgba(44,62,80,0.5))'; break;
                    case 'humorous': gradient = 'linear-gradient(135deg, rgba(241,196,15,0.3), rgba(243,156,18,0.3))'; break;
                    case 'abstract': gradient = 'linear-gradient(135deg, rgba(155,89,182,0.3), rgba(142,68,173,0.3))'; break;
                    case 'aesthetic': gradient = 'linear-gradient(135deg, rgba(233,30,99,0.3), rgba(211,47,47,0.3))'; break;
                    case 'logical': gradient = 'linear-gradient(135deg, rgba(76,175,80,0.3), rgba(67,160,71,0.3))'; break;
                    case 'mysterious': gradient = 'linear-gradient(135deg, rgba(255,152,0,0.3), rgba(251,140,0,0.3))'; break;
                    case 'stream_of_consciousness': gradient = 'linear-gradient(135deg, rgba(103,58,183,0.3), rgba(93,58,183,0.3))'; break;
                }
                elements.globalBg.style.background = gradient;
                elements.globalBg.style.transition = 'background 500ms ease';
                playSound('select');
            });
        });
        elements.buttons.confirmTone.addEventListener('click', () => {
            if (gameState.selectedTone) {
                showModal('提示', '基调已确定，剧情将按此风格生成', () => {
                    switchScreen('themeInput');
                }, false);
            } else {
                showModal('提示', '请选择故事基调', () => {});
            }
        });
        
        // 主题输入
        elements.inputs.theme.addEventListener('input', updateWordCount);
        elements.buttons.submitTheme.addEventListener('click', async () => {
            const theme = elements.inputs.theme.value;
            const validation = inputValidator.validateTheme(theme);
            if (validation.valid) {
                gameState.gameTheme = escapeHtml(theme.trim());
                // 跳转到图片风格选择界面
                switchScreen('imageStyleSelection');
            } else {
                showModal('提示', validation.message, () => {});
            }
        });
        
        // 设定界面标签切换
        elements.content.settingTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const tabId = tab.dataset.tab;
                elements.content.settingTabs.forEach(t => t.classList.remove('bg-[#1ABC9C]', 'border-l-3', 'border-white'));
                elements.content.settingTabContents.forEach(c => {
                    c.classList.add('hidden');
                    c.classList.remove('animate-fadeIn');
                });
                tab.classList.add('bg-[#1ABC9C]', 'border-l-3', 'border-white');
                const activeTab = document.getElementById(`${tabId}-tab`);
                activeTab.classList.remove('hidden');
                activeTab.classList.add('animate-fadeIn');
                playSound('click');
            });
        });
        
        // 图片风格选择逻辑
        // 风格按钮点击事件
        document.querySelectorAll('.style-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                // 重置所有按钮状态
                document.querySelectorAll('.style-btn').forEach(b => {
                    b.classList.remove('ring-4', 'ring-white');
                });
                
                // 选中当前按钮
                btn.classList.add('ring-4', 'ring-white');
                selectedStyle = btn.dataset.style;
                selectedSubStyle = null; // 重置子风格
                customStyleText = ''; // 重置自定义文本
                
                // 隐藏所有子菜单
                document.getElementById('oil-painting-submenu').classList.add('hidden');
                document.getElementById('custom-style-input').classList.add('hidden');
                
                // 根据选择的风格显示相应的子菜单
                if (selectedStyle === 'oil_painting') {
                    // 显示油画风格子选项
                    document.getElementById('oil-painting-submenu').classList.remove('hidden');
                    document.getElementById('selected-style-display').textContent = '已选择：油画风格（请选择具体类型）';
                    elements.buttons.confirmStyle.disabled = true;
                    elements.buttons.confirmStyle.classList.add('cursor-not-allowed');
                } else if (selectedStyle === 'custom') {
                    // 显示自定义输入框
                    document.getElementById('custom-style-input').classList.remove('hidden');
                    document.getElementById('selected-style-display').textContent = '已选择：自定义（请输入风格）';
                    elements.buttons.confirmStyle.disabled = true;
                    elements.buttons.confirmStyle.classList.add('cursor-not-allowed');
                } else {
                    // 其他风格直接显示选择
                    const styleName = btn.dataset.styleName;
                    document.getElementById('selected-style-display').textContent = `已选择：${styleName}`;
                    elements.buttons.confirmStyle.disabled = false;
                    elements.buttons.confirmStyle.classList.remove('cursor-not-allowed');
                    elements.buttons.confirmStyle.classList.add('bg-[#1ABC9C]', 'hover:bg-[#16A085]');
                }
                
                playSound('click');
            });
        });
        
        // 油画风格子选项点击事件
        document.querySelectorAll('.submenu-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                // 重置所有子选项按钮状态
                document.querySelectorAll('.submenu-btn').forEach(b => {
                    b.classList.remove('ring-4', 'ring-white');
                });
                
                // 选中当前子选项
                btn.classList.add('ring-4', 'ring-white');
                selectedSubStyle = btn.dataset.substyle;
                const subStyleName = btn.dataset.substyleName;
                document.getElementById('selected-style-display').textContent = `已选择：油画风格 - ${subStyleName}`;
                elements.buttons.confirmStyle.disabled = false;
                elements.buttons.confirmStyle.classList.remove('cursor-not-allowed');
                elements.buttons.confirmStyle.classList.add('bg-[#1ABC9C]', 'hover:bg-[#16A085]');
                
                playSound('click');
            });
        });
        
        // 自定义输入框输入事件
        if (elements.inputs.customStyle) {
            elements.inputs.customStyle.addEventListener('input', () => {
                customStyleText = elements.inputs.customStyle.value.trim();
                if (customStyleText.length > 0) {
                    document.getElementById('selected-style-display').textContent = `已选择：自定义 - ${customStyleText}`;
                    elements.buttons.confirmStyle.disabled = false;
                    elements.buttons.confirmStyle.classList.remove('cursor-not-allowed');
                    elements.buttons.confirmStyle.classList.add('bg-[#1ABC9C]', 'hover:bg-[#16A085]');
                } else {
                    document.getElementById('selected-style-display').textContent = '已选择：自定义（请输入风格）';
                    elements.buttons.confirmStyle.disabled = true;
                    elements.buttons.confirmStyle.classList.add('cursor-not-allowed');
                }
            });
        }
        
        // 确认风格按钮点击事件
        elements.buttons.confirmStyle.addEventListener('click', async () => {
            if (elements.buttons.confirmStyle.disabled) {
                return;
            }
            
            // 根据选择的风格保存到gameState
            if (selectedStyle === 'oil_painting' && selectedSubStyle) {
                // 油画风格需要保存子风格
                gameState.imageStyle = {
                    type: 'oil_painting',
                    subtype: selectedSubStyle
                };
            } else if (selectedStyle === 'custom' && customStyleText) {
                // 自定义风格
                gameState.imageStyle = {
                    type: 'custom',
                    value: customStyleText
                };
            } else if (selectedStyle) {
                // 其他风格
                gameState.imageStyle = {
                    type: selectedStyle
                };
            } else {
                showModal('提示', '请先选择一个图片风格', () => {});
                return;
            }
            
            console.log('✅ 图片风格已选择:', gameState.imageStyle);
            
            // 应用字体（根据风格和基调）
            FontManager.applyFontToGame(gameState.imageStyle, gameState.tone);
            
            // 跳转到加载界面，开始生成世界观
            switchScreen('loading');
            simulateLoading();
            await generateGameWorldview();
        });
        
        // 开始游戏
        elements.buttons.startGame.addEventListener('click', () => {
            switchScreen('loading');
            simulateGameLoading();
        });
        
        // 存档管理按钮
        elements.buttons.loadSelectedSave.addEventListener('click', () => {
            if (gameState.selectedSave) {
                switchScreen('loading');
                // 延迟加载，模拟加载过程
                setTimeout(() => {
                    loadGameState(gameState.selectedSave);
                }, 1500);
            } else {
                showModal('提示', '请选择要加载的存档', () => {});
            }
        });
        elements.buttons.deleteSelectedSave.addEventListener('click', async () => {
            if (gameState.selectedSave) {
                showModal('确认删除', '确定要删除该存档吗？删除后无法恢复', async () => {
                    await deleteSave(gameState.selectedSave);
                    await loadSaves();
                });
            } else {
                showModal('提示', '请选择要删除的存档', () => {});
            }
        });
        elements.buttons.backToMenu.addEventListener('click', () => switchScreen('menu'));
        elements.buttons.restartGame.addEventListener('click', () => switchScreen('menu'));
        
        // 示例主题点击填充
        document.querySelector('.theme-examples').addEventListener('click', (e) => {
            if (e.target.tagName === 'SPAN') {
                const example = e.target.textContent.trim();
                elements.inputs.theme.value = example;
                updateWordCount();
            }
        });
        
        // 存档卡片选择
        document.addEventListener('click', (e) => {
            if (e.target.closest('.save-card') && !e.target.closest('.delete-save')) {
                const saveCard = e.target.closest('.save-card');
                // 检查是否是新建存档按钮（通过文本内容判断）
                const cardText = saveCard.textContent || '';
                if (!cardText.includes('新建存档')) {
                    document.querySelectorAll('.save-card').forEach(card => {
                        card.classList.remove('border-2', 'border-[#1ABC9C]', 'scale-103');
                        card.querySelector('.selected-mark')?.classList.add('hidden');
                    });
                    saveCard.classList.add('border-2', 'border-[#1ABC9C]', 'scale-103');
                    saveCard.querySelector('.selected-mark')?.classList.remove('hidden');
                    gameState.selectedSave = saveCard.querySelector('.save-name').textContent.trim();
                }
            }
        });
        
        // 删除存档按钮
        document.addEventListener('click', async (e) => {
            if (e.target.closest('.delete-save')) {
                e.stopPropagation();
                const saveCard = e.target.closest('.save-card');
                const saveName = saveCard.querySelector('.save-name').textContent.trim();
                showModal('确认删除', `确定要删除存档"${saveName}"吗？`, async () => {
                    await deleteSave(saveName);
                    await loadSaves();
                });
            }
        });
        
        // 角色面板拖动
        const characterPanel = document.getElementById('character-panel');
        let isDragging = false;
        let startX, startY, offsetX, offsetY;
        
        characterPanel.addEventListener('mousedown', (e) => {
            if (e.target.closest('.panel-header')) {
                isDragging = true;
                startX = e.clientX;
                startY = e.clientY;
                offsetX = characterPanel.offsetLeft;
                offsetY = characterPanel.offsetTop;
                characterPanel.style.cursor = 'grabbing';
            }
        });
        
        document.addEventListener('mousemove', (e) => {
            if (isDragging) {
                const newX = e.clientX - startX + offsetX;
                const newY = e.clientY - startY + offsetY;
                characterPanel.style.left = `${newX}px`;
                characterPanel.style.top = `${newY}px`;
            }
        });
        
        document.addEventListener('mouseup', () => {
            isDragging = false;
            characterPanel.style.cursor = 'move';
        });
        
        // 关闭角色面板
        document.querySelector('.close-panel').addEventListener('click', () => {
            characterPanel.style.display = 'none';
        });
        
        // 游戏结束按钮事件
        const endGameBtn = document.getElementById('end-game-btn');
        if (endGameBtn) {
            endGameBtn.addEventListener('click', () => {
                // 显示退出确认弹窗（包含存档选项）
                showInGameExitConfirmModal();
            });
        }
        
        // 下一段文本按钮事件（右下角"->"按钮）
        const nextSegmentBtn = document.getElementById('next-segment-btn');
        if (nextSegmentBtn) {
            nextSegmentBtn.addEventListener('click', () => {
                playSound('click');
                
                // 🔧 修复：检查是否是最后一段，如果是则显示选项，否则显示下一段文本
                if (nextSegmentBtn.dataset.showOptions === 'true') {
                    // 最后一段，点击后显示选项
                    console.log('✅ 用户点击"->"按钮，显示选项');
                    
                    // 隐藏"->"按钮
                    nextSegmentBtn.classList.add('hidden');
                    nextSegmentBtn.dataset.showOptions = 'false';
                    
                    // 隐藏文本显示区域，显示选项区域
                    const textDisplayArea = document.getElementById('text-display-area');
                    const optionsListArea = document.getElementById('options-list-area');
                    if (textDisplayArea) {
                        textDisplayArea.classList.add('hidden');
                    }
                    if (optionsListArea) {
                        optionsListArea.classList.remove('hidden');
                    }
                    
                    // 显示选项
                    const optionsToShow = gameState.pendingOptions || gameState.currentOptions || [];
                    generateOptions(optionsToShow);
                    
                    // 注意：预生成已经在文本开始显示时触发，这里不再重复触发
                    // 如果预生成没有在文本开始显示时触发（例如单段文本的情况），这里作为备用触发
                    if (!gameState._pregenerationTriggered && optionsToShow && optionsToShow.length > 0) {
                        const newSceneId = generateNewSceneId();
                        gameState.currentSceneId = newSceneId;
                        console.log('🚀 备用触发预生成（场景ID:', newSceneId, '）');
                        if (gameState.gameData) {
                            pregenerateNextLayers(gameState.gameData, optionsToShow, newSceneId);
                        }
                        gameState._pregenerationTriggered = true;
                    }
                    
                    // 重置分段显示状态
                    gameState.isShowingSegments = false;
                    gameState.currentTextSegmentIndex = 0;
                    gameState.textSegments = [];
                    gameState.pendingOptions = null;
                } else {
                    // 不是最后一段，显示下一段文本
                    showNextTextSegment();
                }
            });
        }
    }
    
    // 暴露公共方法
    return {
        init,
        saveGame
    };
})();

// 页面加载完成后初始化游戏
// 强制禁用scene-text的所有缩放效果（全局初始化）
function forceDisableSceneTextScale() {
    const sceneTextElement = document.getElementById('scene-text');
    if (sceneTextElement) {
            const forceNoTransform = () => {
                sceneTextElement.style.setProperty('transform', 'none', 'important');
                sceneTextElement.style.setProperty('scale', '1', 'important');
                sceneTextElement.style.setProperty('transition', 'none', 'important');
                sceneTextElement.style.setProperty('animation', 'none', 'important');
                sceneTextElement.style.setProperty('pointer-events', 'none', 'important');
                sceneTextElement.style.setProperty('user-select', 'none', 'important');
                sceneTextElement.style.setProperty('outline', 'none', 'important');
                sceneTextElement.style.setProperty('-webkit-transform', 'none', 'important');
                sceneTextElement.style.setProperty('-moz-transform', 'none', 'important');
                sceneTextElement.style.setProperty('-ms-transform', 'none', 'important');
                sceneTextElement.style.setProperty('-o-transform', 'none', 'important');
                sceneTextElement.style.setProperty('will-change', 'auto', 'important');
                // 强制移除所有背景样式，确保完全透明
                sceneTextElement.style.setProperty('background', 'transparent', 'important');
                sceneTextElement.style.setProperty('background-color', 'transparent', 'important');
                sceneTextElement.style.setProperty('background-image', 'none', 'important');
                sceneTextElement.style.setProperty('box-shadow', 'none', 'important');
                sceneTextElement.style.setProperty('backdrop-filter', 'none', 'important');
                sceneTextElement.style.setProperty('-webkit-backdrop-filter', 'none', 'important');
            };
        
        forceNoTransform();
        
        // 监听所有可能改变样式的事件
        // 注意：移除 touchstart/touchend，允许滚动
        ['click', 'mousedown', 'mouseup', 'focus', 'blur', 'keydown', 'keyup'].forEach(eventType => {
            sceneTextElement.addEventListener(eventType, (e) => {
                e.preventDefault();
                e.stopPropagation();
                forceNoTransform();
            }, true);
        });
        
        // 使用MutationObserver监控样式变化（添加防无限循环机制）
        let isUpdating = false; // 防止无限循环的标志
        const observer = new MutationObserver((mutations) => {
            // 如果正在更新，跳过（防止无限循环）
            if (isUpdating) return;
            
            mutations.forEach((mutation) => {
                if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
                    // 检查是否是我们的更新导致的（通过检查style属性）
                    const currentStyle = sceneTextElement.getAttribute('style');
                    // 如果style中包含我们设置的属性，说明是我们自己更新的，跳过
                    if (currentStyle && currentStyle.includes('transform: none')) {
                        return; // 跳过，避免无限循环
                    }
                    
                    // 只有非我们的更新才重置
                    isUpdating = true;
                    forceNoTransform();
                    // 使用setTimeout确保在下一个事件循环中重置标志
                    setTimeout(() => {
                        isUpdating = false;
                    }, 0);
                }
            });
        });
        observer.observe(sceneTextElement, {
            attributes: true,
            attributeFilter: ['style', 'class'],
            subtree: false
        });
        
        // 定期检查并重置（防止其他代码修改样式）- 降低频率避免性能问题
        const checkInterval = setInterval(() => {
            if (!isUpdating) {
                const computedStyle = window.getComputedStyle(sceneTextElement);
                if (computedStyle.transform !== 'none' && computedStyle.transform !== 'matrix(1, 0, 0, 1, 0, 0)') {
                    isUpdating = true;
                    forceNoTransform();
                    setTimeout(() => {
                        isUpdating = false;
                    }, 0);
                }
            }
        }, 500); // 降低频率到500ms，减少性能影响
        
        // 保存interval ID以便清理
        sceneTextElement._noTransformInterval = checkInterval;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    console.log('📦 [初始化] DOMContentLoaded事件触发');
    console.log('📦 [代码版本] 使用同一定位上下文方案');
    Game.init();
    // 延迟执行，确保DOM完全加载
    setTimeout(forceDisableSceneTextScale, 100);
    setTimeout(forceDisableSceneTextScale, 500);
    setTimeout(forceDisableSceneTextScale, 1000);
    
    // 验证定位上下文结构
    setTimeout(() => {
        const sceneTextElement = document.getElementById('scene-text');
        const sceneImage = document.getElementById('scene-image');
        
        console.log('🔍 [初始化验证] 结构检查:');
        console.log('  ✅ 已移除scene-container，背景图片通过#global-bg全屏显示');
        
        if (sceneTextElement) {
            console.log('  ✅ #scene-text 存在:', {
                position: window.getComputedStyle(sceneTextElement).position,
                parent: sceneTextElement.parentElement?.className
            });
        } else {
            console.log('  ❌ #scene-text 不存在');
        }
        
        if (sceneImage) {
            console.log('  ✅ #scene-image 存在:', {
                position: window.getComputedStyle(sceneImage).position,
                parent: sceneImage.parentElement?.className
            });
        } else {
            console.log('  ❌ #scene-image 不存在');
        }
    }, 1500);
});

// 页面加载完成后也执行
window.addEventListener('load', () => {
    console.log('📦 [初始化] window.load事件触发');
    forceDisableSceneTextScale();
});