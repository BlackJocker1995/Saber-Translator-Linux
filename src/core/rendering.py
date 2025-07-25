import logging
import math
import os
from PIL import Image, ImageDraw, ImageFont
import cv2 # 导入 cv2 备用
from PIL import ImageDraw
# 导入常量和路径助手
from src.shared import constants
from src.shared.path_helpers import resource_path, get_debug_dir # 导入 get_debug_dir

logger = logging.getLogger("CoreRendering")
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- 字体加载缓存 ---
_font_cache = {}

# --- 特殊字符的字体路径 ---
NOTOSANS_FONT_PATH = os.path.join('src', 'app', 'static', 'fonts', 'NotoSans-Medium.ttf')

# --- 需要使用特殊字体渲染的字符 ---
SPECIAL_CHARS = {'‼', '⁉'}

# --- 竖排标点符号映射表 ---
VERTICAL_PUNCTUATION_MAP = {
    # 中文标点
     '（': '︵', '）': '︶', 
    '【': '︻', '】': '︼', '「': '﹁', '」': '﹂', 
    '『': '﹃', '』': '﹄', '〈': '︿', '〉': '﹀',
    '"': '﹃', '"': '﹄', ''': '﹁', ''': '﹂',
    '《': '︽', '》': '︾', '［': '︹', '］': '︺',
    '｛': '︷', '｝': '︸', '〔': '︹', '〕': '︺',
    '—': '︱', '…': '︙', '～': '︴',
    
    # 英文标点
    '(': '︵', ')': '︶',
    '[': '︹', ']': '︺', '{': '︷', '}': '︸',
    '<': '︿', '>': '﹀', '-': '︱', '~': '︴'
}

# 特殊组合标点映射
SPECIAL_PUNCTUATION_PATTERNS = [
    ('...', '︙'),     # 连续三个点映射成竖直省略号
    ('…', '︙'),       # Unicode省略号映射成竖直省略号
    ('!!', '‼'),       # 连续两个感叹号映射成双感叹号
    ('!!!', '‼'),      # 连续三个感叹号映射成双感叹号
    ('！！', '‼'),     # 中文连续两个感叹号
    ('！！！', '‼'),   # 中文连续三个感叹号
    ('!?', '⁉'),       # 感叹号加问号映射成感叹问号组合
    ('?!', '⁉'),       # 问号加感叹号映射成感叹问号组合
    ('！？', '⁉'),     # 中文感叹号加问号
    ('？！', '⁉'),     # 中文问号加感叹号
]

def map_to_vertical_punctuation(text):
    """
    将文本中的标点符号映射为竖排标点符号。
    
    在竖排文本排版中，常规的横排标点符号会显得不协调。此函数将常规标点转换为
    专门用于竖排排版的对应标点形式，例如将横向的括号"()"转换为竖向的"︵︶"。
    同时处理特殊组合标点，如连续感叹号或问号组合等。
    
    Args:
        text (str): 原始文本，包含需要转换的标点符号
        
    Returns:
        str: 转换后的文本，标点符号已替换为竖排版本
    """
    # 首先处理特殊组合标点
    for pattern, replacement in SPECIAL_PUNCTUATION_PATTERNS:
        text = text.replace(pattern, replacement)
    
    # 然后处理单个标点
    result = ""
    i = 0
    while i < len(text):
        char = text[i]
        if char in VERTICAL_PUNCTUATION_MAP:
            result += VERTICAL_PUNCTUATION_MAP[char]
        else:
            result += char
        i += 1
    
    return result

def get_font(font_family_relative_path=constants.DEFAULT_FONT_RELATIVE_PATH, font_size=constants.DEFAULT_FONT_SIZE):
    """
    加载字体文件，带缓存功能。
    
    根据给定的字体路径和大小加载字体对象。为了提高性能，已加载的字体会被缓存。
    如果指定字体加载失败，将尝试使用默认字体。若默认字体也无法加载，
    最终会使用Pillow的内置默认字体。
    
    Args:
        font_family_relative_path (str): 字体的相对路径（相对于项目根目录）
        font_size (int): 字体大小，单位为像素
        
    Returns:
        ImageFont.FreeTypeFont or ImageFont.ImageFont: 加载的字体对象，失败则返回默认字体
    """
    # 确保 font_size 是整数
    try:
        font_size = int(font_size)
        if font_size <= 0:
             font_size = constants.DEFAULT_FONT_SIZE # 防止无效字号
    except (ValueError, TypeError):
         font_size = constants.DEFAULT_FONT_SIZE

    cache_key = (font_family_relative_path, font_size)
    if cache_key in _font_cache:
        return _font_cache[cache_key]

    font = None
    try:
        font_path_abs = resource_path(font_family_relative_path)
        if os.path.exists(font_path_abs):
            font = ImageFont.truetype(font_path_abs, font_size, encoding="utf-8")
            logger.info(f"成功加载字体: {font_path_abs} (大小: {font_size})")
        else:
            logger.warning(f"字体文件未找到: {font_path_abs} (相对路径: {font_family_relative_path})")
            raise FileNotFoundError()

    except Exception as e:
        logger.error(f"加载字体 {font_family_relative_path} (大小: {font_size}) 失败: {e}，尝试默认字体。")
        try:
            default_font_path_abs = resource_path(constants.DEFAULT_FONT_RELATIVE_PATH)
            if os.path.exists(default_font_path_abs):
                 font = ImageFont.truetype(default_font_path_abs, font_size, encoding="utf-8")
                 logger.info(f"成功加载默认字体: {default_font_path_abs} (大小: {font_size})")
            else:
                 logger.error(f"默认字体文件也未找到: {default_font_path_abs}")
                 font = ImageFont.load_default()
                 logger.warning("使用 Pillow 默认字体。")
        except Exception as e_default:
            logger.error(f"加载默认字体时出错: {e_default}", exc_info=True)
            font = ImageFont.load_default()
            logger.warning("使用 Pillow 默认字体。")

    _font_cache[cache_key] = font
    return font

def calculate_auto_font_size(text, bubble_width, bubble_height, text_direction='vertical',
                             font_family_relative_path=constants.DEFAULT_FONT_RELATIVE_PATH,
                             min_size=12, max_size=60, padding_ratio=1.0):
    """
    使用二分法计算最佳字体大小。
    
    根据给定的气泡大小和文本内容，计算能使文本恰好适合气泡的最佳字体大小。
    对文本方向（横排/竖排）有不同的计算逻辑。使用二分搜索算法，在最小和最大
    字号之间找到最佳值，确保文本能完整显示在气泡内。
    
    Args:
        text (str): 要渲染的文本内容
        bubble_width (int): 气泡宽度，单位为像素
        bubble_height (int): 气泡高度，单位为像素
        text_direction (str): 文本方向，'vertical'表示竖排，'horizontal'表示横排
        font_family_relative_path (str): 字体的相对路径
        min_size (int): 允许的最小字体大小
        max_size (int): 允许的最大字体大小
        padding_ratio (float): 内边距比例，用于控制文本与气泡边界的距离
        
    Returns:
        int: 计算得到的最佳字体大小
    """
    if not text or not text.strip() or bubble_width <= 0 or bubble_height <= 0:
        return constants.DEFAULT_FONT_SIZE

    W = bubble_width * padding_ratio
    H = bubble_height * padding_ratio
    N = len(text)
    c_w = 1.0
    l_h = 1.05

    if text_direction == 'vertical':
        W, H = H, W

    low = min_size
    high = max_size
    best_size = min_size

    while low <= high:
        mid = (low + high) // 2
        if mid == 0: break

        try:
            font = get_font(font_family_relative_path, mid)
            if font is None:
                high = mid - 1
                continue

            avg_char_width = mid * c_w
            avg_char_height = mid

            if text_direction == 'horizontal':
                chars_per_line = max(1, int(W / avg_char_width)) if avg_char_width > 0 else N # 避免除零
                lines_needed = math.ceil(N / chars_per_line) if chars_per_line > 0 else N
                total_height_needed = lines_needed * mid * l_h
                fits = total_height_needed <= H
            else: # vertical
                chars_per_column = max(1, int(H / avg_char_height)) if avg_char_height > 0 else N
                columns_needed = math.ceil(N / chars_per_column) if chars_per_column > 0 else N
                total_width_needed = columns_needed * mid * l_h
                fits = total_width_needed <= W

            if fits:
                best_size = mid
                low = mid + 1
            else:
                high = mid - 1

        except Exception as e:
            logger.error(f"计算字号 {mid} 时出错: {e}", exc_info=True)
            high = mid - 1

    result = max(min_size, best_size)
    logger.info(f"自动计算的最佳字体大小: {result}px (范围: {min_size}-{max_size})")
    return result

# --- 占位符，后续步骤会添加 ---
def draw_multiline_text_vertical(draw, text, font, x, y, max_height,
                                 fill=constants.DEFAULT_TEXT_COLOR,
                                 rotation_angle=constants.DEFAULT_ROTATION_ANGLE,
                                 # 新增描边参数
                                 enable_stroke=False,
                                 stroke_color="#FFFFFF",
                                 stroke_width=0,
                                 bubble_width=None): # bubble_width 用于居中
    if not text:
        return
    
    # 将标点符号转换为竖排样式
    text = map_to_vertical_punctuation(text)

    lines = []
    current_line = ""
    current_column_height = 0
    # Pillow的行高通常由字体大小决定，可微调 line_spacing
    # font.getsize("A")[1] 或 font.getbbox("A")[3] - font.getbbox("A")[1] 可以估算单行高度
    # 简单的处理方式：
    line_height_approx = font.size + 1 # 字间距为1像素

    for char in text:
        # 简单按字符高度估算，更精确的需要 font.getmask(char).size[1]
        # 但 Pillow 的 ImageFont 没有直接的 get_character_height
        # 这里我们简化，认为每个字符占用的垂直空间主要是字体大小
        if current_column_height + line_height_approx <= max_height:
            current_line += char
            current_column_height += line_height_approx
        else:
            lines.append(current_line)
            current_line = char
            current_column_height = line_height_approx
    lines.append(current_line)

    # 列宽也基于字体大小估算
    column_width_approx = font.size + 3 # 假设列间距

    # 计算文本段落的总宽度
    total_text_width_for_centering = len(lines) * column_width_approx
    
    # 在竖排文本中，x 通常是气泡的右边界（如果从右往左写）或左边界（如果从左往右写列）
    # 这里我们假设 x 是起始列的绘制基准x坐标 (通常是最右边列的右边界)
    # 如果提供了 bubble_width，则进行居中对齐
    if bubble_width is not None:
        # x 此时应为气泡的右边界
        bubble_center_x = x - bubble_width / 2
        current_x_base = bubble_center_x + total_text_width_for_centering / 2 # 最右列的右边界
    else:
        current_x_base = x # 不居中，直接使用传入的 x

    # 计算垂直方向文本总高度，用于居中
    max_chars_in_line = 0
    if lines:
        max_chars_in_line = max(len(line) for line in lines if line) # 防止空行
    total_text_height_for_centering = max_chars_in_line * line_height_approx

    if total_text_height_for_centering < max_height:
        vertical_offset = (max_height - total_text_height_for_centering) / 2
        start_y_base = y + vertical_offset
    else:
        start_y_base = y

    # 如果需要旋转，先获取原始图像
    original_image = None
    center_x_rot, center_y_rot = 0, 0
    if rotation_angle != 0:
        if hasattr(draw, '_image'):
            original_image = draw._image
        
        # 计算旋转中心：气泡的中心
        center_x_rot = (x - bubble_width / 2) if bubble_width else (current_x_base - total_text_width_for_centering / 2)
        center_y_rot = y + max_height / 2

    # 预加载NotoSans字体，用于特殊字符
    special_font = None
    font_size = font.size  # 获取当前字体大小

    current_x_col = current_x_base # 当前列的右边界x坐标
    for line_idx, line in enumerate(lines):
        current_y_char = start_y_base # 当前字符的y坐标
        for char_idx, char in enumerate(line):
            # 检查是否为需要特殊字体的字符
            current_font = font
            if char in SPECIAL_CHARS:
                if special_font is None:
                    try:
                        # 第一次遇到特殊字符时加载特殊字体
                        special_font = get_font(NOTOSANS_FONT_PATH, font_size)
                    except Exception as e:
                        logger.error(f"加载NotoSans字体失败: {e}，回退到普通字体")
                        special_font = font  # 如果加载失败，使用普通字体
                
                if special_font is not None:
                    current_font = special_font
            
            # 使用当前选定的字体计算字符尺寸
            bbox = current_font.getbbox(char)
            char_width = bbox[2] - bbox[0]
            
            # 对于竖排，我们通常需要将字符的右上角或中心对齐到 (current_x_col - char_width, current_y_char)
            # Pillow的 text 方法的 xy 参数是文本的左上角。
            # 对于单个字符，其左上角就是 (current_x_col - char_width, current_y_char)
            text_x_char = current_x_col - char_width
            text_y_char = current_y_char
            
            # 准备传递给 draw.text 的参数字典
            text_draw_params = {
                "font": current_font,
                "fill": fill
            }
            if enable_stroke and stroke_width > 0:
                text_draw_params["stroke_width"] = int(stroke_width)
                text_draw_params["stroke_fill"] = stroke_color
                # logger.debug(f"V-Stroke: char='{char}', width={stroke_width}, color={stroke_color}")
            
            if rotation_angle != 0 and original_image is not None:
                try:
                    # 创建一个透明的临时图像用于绘制和旋转单个字符
                    temp_char_img = Image.new('RGBA', original_image.size, (0, 0, 0, 0))
                    temp_char_draw = ImageDraw.Draw(temp_char_img)
                    
                    # 在临时图像上绘制当前字符
                    temp_char_draw.text((text_x_char, text_y_char), char, **text_draw_params)
                    
                    # 旋转临时图像
                    rotated_char_img = temp_char_img.rotate(
                        rotation_angle, 
                        resample=Image.Resampling.BICUBIC,
                        center=(center_x_rot, center_y_rot),
                        expand=False
                    )
                    
                    # 将旋转后的图像合成到原始图像
                    original_image.paste(rotated_char_img, (0,0), rotated_char_img)
                except Exception as e_rot:
                    logger.error(f"旋转渲染竖排字符 '{char}' 失败: {e_rot}, 回退到直接渲染")
                    draw.text((text_x_char, text_y_char), char, **text_draw_params)
            else:
                # 直接绘制，应用描边（如果启用）
                draw.text((text_x_char, text_y_char), char, **text_draw_params)
                
            current_y_char += line_height_approx
        current_x_col -= column_width_approx

def draw_multiline_text_horizontal(draw, text, font, x, y, max_width,
                                  fill=constants.DEFAULT_TEXT_COLOR, # 保持默认文本填充色
                                  rotation_angle=constants.DEFAULT_ROTATION_ANGLE,
                                  # 新增描边参数，这些将从 bubble_styles 中提取
                                  enable_stroke=False,
                                  stroke_color="#FFFFFF",
                                  stroke_width=0):
    if not text:
        return

    lines = []
    current_line = ""
    current_line_width = 0

    for char in text:
        bbox = font.getbbox(char)
        char_width = bbox[2] - bbox[0]
        space_width = font.getbbox(' ')[2] - font.getbbox(' ')[0]

        if current_line_width + char_width <= max_width:
            current_line += char
            current_line_width += char_width
        else:
            lines.append(current_line)
            current_line = char
            current_line_width = char_width

    lines.append(current_line)

    current_y = y
    line_height = font.size + 5
    
    # 预加载NotoSans字体，用于特殊字符
    special_font = None
    font_size = font.size  # 获取当前字体大小
    
    # 如果需要旋转，先获取原始图像
    original_image = None
    center_x_rot, center_y_rot = 0, 0 # 旋转中心
    if rotation_angle != 0:
        if hasattr(draw, '_image'):
            original_image = draw._image
            
        # 计算文本块的中心点，用于旋转
        center_x_rot = x + max_width / 2
        total_text_height = len(lines) * line_height
        center_y_rot = y + total_text_height / 2

    for line in lines:
        current_x = x
        for char in line:
            # 检查是否为需要特殊字体的字符
            current_font = font
            if char in SPECIAL_CHARS:
                if special_font is None:
                    try:
                        # 第一次遇到特殊字符时加载特殊字体
                        special_font = get_font(NOTOSANS_FONT_PATH, font_size)
                    except Exception as e:
                        logger.error(f"加载NotoSans字体失败: {e}，回退到普通字体")
                        special_font = font  # 如果加载失败，使用普通字体
                
                if special_font is not None:
                    current_font = special_font

            # 使用当前选定的字体计算字符尺寸
            bbox = current_font.getbbox(char)
            char_width = bbox[2] - bbox[0]
            char_height = bbox[3] - bbox[1]
            
            # 准备传递给 draw.text 的参数字典
            text_draw_params = {
                "font": current_font,
                "fill": fill # 文本本身的颜色
            }
            if enable_stroke and stroke_width > 0:
                text_draw_params["stroke_width"] = int(stroke_width) # Pillow 需要整数
                text_draw_params["stroke_fill"] = stroke_color       # 描边的颜色
                # logger.debug(f"H-Stroke: char='{char}', width={stroke_width}, color={stroke_color}")
            
            if rotation_angle != 0 and original_image is not None:
                try:
                    # 创建一个透明的临时图像用于绘制和旋转单个字符
                    # 尺寸可以根据字符和旋转角度估算，或者用一个足够大的固定尺寸再裁剪
                    # 为简化，这里使用原始图像尺寸的临时画布，后续可以优化
                    temp_char_img = Image.new('RGBA', original_image.size, (0, 0, 0, 0))
                    temp_char_draw = ImageDraw.Draw(temp_char_img)
                    
                    # 在临时图像的 (current_x, current_y) 位置绘制字符
                    temp_char_draw.text((current_x, current_y), char, **text_draw_params)
                    
                    # 旋转这个包含单个字符的临时图像
                    rotated_char_img = temp_char_img.rotate(
                        rotation_angle,
                        resample=Image.Resampling.BICUBIC, # 或者 NEAREST 如果要求锐利
                        center=(center_x_rot, center_y_rot), # 使用计算好的旋转中心
                        expand=False # 不扩展图像边界
                    )
                    
                    # 将旋转后的字符图像粘贴回原始图像 (带透明度蒙版)
                    # 注意：Image.paste 的第三个参数是蒙版。如果 rotated_char_img 是 RGBA，它自身可以作为蒙版。
                    original_image.paste(rotated_char_img, (0,0), rotated_char_img)
                except Exception as e_rot:
                    logger.error(f"旋转渲染字符 '{char}' 失败: {e_rot}, 回退到直接渲染")
                    draw.text((current_x, current_y), char, **text_draw_params)
            else:
                # 直接绘制，应用描边（如果启用）
                draw.text((current_x, current_y), char, **text_draw_params)
            
            current_x += char_width
        current_y += line_height

def render_all_bubbles(draw_image, all_texts, bubble_coords, bubble_styles):
    """
    在图像上渲染所有气泡的文本，使用各自的样式。
    
    根据提供的文本列表、气泡坐标和样式设置，将文本渲染到相应的气泡位置。
    支持不同的文本方向、字体、颜色和描边效果等样式设置。每个气泡可以有
    独立的样式设置，未指定的样式参数将使用默认值。
    
    Args:
        draw_image (PIL.ImageDraw.ImageDraw): PIL的绘图对象，用于在图像上绘制文本
        all_texts (list): 所有气泡的文本列表
        bubble_coords (list): 所有气泡的坐标列表，格式为[(x1, y1, x2, y2), ...]
        bubble_styles (dict): 包含气泡样式信息的字典，结构为：
            {
                'fontSizes': {气泡索引: 字体大小},
                'fontFamilies': {气泡索引: 字体路径},
                'textDirections': {气泡索引: 文本方向},
                'positionOffsets': {气泡索引: {'x': x偏移, 'y': y偏移}},
                'textColors': {气泡索引: 文本颜色},
                'rotationAngles': {气泡索引: 旋转角度},
                'enableStroke': {气泡索引: 是否启用描边},
                'strokeColors': {气泡索引: 描边颜色},
                'strokeWidths': {气泡索引: 描边宽度}
            }
    
    Returns:
        None: 函数直接在提供的draw_image上绘制，不返回新对象
    """
    logger.info(f"渲染所有气泡文本，共 {len(all_texts)} 个气泡")

    # --- 强制转换 draw_image 为 ImageDraw.ImageDraw ---
    
    if not hasattr(draw_image, "text") or not hasattr(draw_image, "rectangle"):
        # 假定传入的是 PIL.Image.Image
        draw_image = ImageDraw.Draw(draw_image)
        logger.info("[DEBUG] 自动将 draw_image 转为 ImageDraw.Draw 实例。")
    # ------------------------------------------------

    # 兼容两种 bubble_styles 结构：新结构 {'0': {...}}，旧结构 {'fontSizes': {...}}
    is_new_style = False
    if not any(k.startswith('font') or k.endswith('s') for k in bubble_styles.keys()):
        is_new_style = True

    for i, (text, (x1, y1, x2, y2)) in enumerate(zip(all_texts, bubble_coords)):
        if not text:
            continue

        bubble_index = str(i)  # 气泡索引转为字符串，用于字典键

        if is_new_style:
            style = bubble_styles.get(bubble_index, {})
            font_size = style.get('fontSize', constants.DEFAULT_FONT_SIZE)
            font_family_rel = style.get('fontFamily', constants.DEFAULT_FONT_RELATIVE_PATH)
            text_direction = style.get('text_direction', constants.DEFAULT_TEXT_DIRECTION)
            position_offset = style.get('position_offset', {'x': 0, 'y': 0})
            text_color = style.get('text_color', constants.DEFAULT_TEXT_COLOR)
            rotation_angle = style.get('rotation_angle', constants.DEFAULT_ROTATION_ANGLE)
            enable_stroke = style.get('enableStroke', False)
            stroke_color = style.get('strokeColor', "#FFFFFF")
            stroke_width = int(style.get('strokeWidth', 0))
        else:
            font_sizes = bubble_styles.get('fontSizes', {})
            font_families = bubble_styles.get('fontFamilies', {})
            text_directions = bubble_styles.get('textDirections', {})
            position_offsets = bubble_styles.get('positionOffsets', {})
            text_colors = bubble_styles.get('textColors', {})
            rotation_angles = bubble_styles.get('rotationAngles', {})
            enable_stroke_settings = bubble_styles.get('enableStroke', {})
            stroke_colors = bubble_styles.get('strokeColors', {})
            stroke_widths = bubble_styles.get('strokeWidths', {})

            font_size = font_sizes.get(bubble_index, constants.DEFAULT_FONT_SIZE)
            font_family_rel = font_families.get(bubble_index, constants.DEFAULT_FONT_RELATIVE_PATH)
            text_direction = text_directions.get(bubble_index, constants.DEFAULT_TEXT_DIRECTION)
            position_offset = position_offsets.get(bubble_index, {'x': 0, 'y': 0})
            text_color = text_colors.get(bubble_index, constants.DEFAULT_TEXT_COLOR)
            rotation_angle = rotation_angles.get(bubble_index, constants.DEFAULT_ROTATION_ANGLE)
            enable_stroke = enable_stroke_settings.get(bubble_index, False)
            stroke_color = stroke_colors.get(bubble_index, "#FFFFFF")
            stroke_width = int(stroke_widths.get(bubble_index, 0))

        x_offset = position_offset.get('x', 0)
        y_offset = position_offset.get('y', 0)

        # 获取字体
        font = get_font(font_family_rel, font_size)
        if font is None:
            logger.error(f"获取字体失败: {font_family_rel} (大小: {font_size})，跳过气泡 {i}")
            continue

        # 绘制文本
        try:
            bubble_width = x2 - x1
            bubble_height = y2 - y1

            # 关键日志：渲染前输出当前气泡的字体参数
            logger.info(
                f"[字体调试] 气泡{i} 渲染参数: font_family='{font_family_rel}', font_size={font_size}, text_direction='{text_direction}', text='{text[:20]}...'"
            )

            # 计算文本位置
            if text_direction == 'vertical':
                # 竖直排版：右边是第一列，从右向左绘制
                start_x = x2 + x_offset  # 从右边框开始
                start_y = y1 + y_offset  # 从上边框开始

                # 在气泡内绘制竖排文本
                draw_multiline_text_vertical(
                    draw_image,
                    text,
                    font,
                    start_x,
                    start_y,
                    bubble_height,
                    fill=text_color, # 使用指定的文本颜色
                    rotation_angle=rotation_angle, # 使用指定的旋转角度
                    enable_stroke=enable_stroke, # 传递描边设置
                    stroke_color=stroke_color,
                    stroke_width=stroke_width,
                    bubble_width=bubble_width # 传递气泡宽度以支持居中
                )
            else:  # 'horizontal'
                # 水平排版：顶部是第一行，从上往下绘制
                start_x = x1 + x_offset  # 从左边框开始
                start_y = y1 + y_offset  # 从上边框开始

                # 在气泡内绘制横排文本
                draw_multiline_text_horizontal(
                    draw_image,
                    text,
                    font,
                    start_x,
                    start_y,
                    bubble_width,
                    fill=text_color, # 使用指定的文本颜色
                    rotation_angle=rotation_angle, # 使用指定的旋转角度
                    enable_stroke=enable_stroke, # 传递描边设置
                    stroke_color=stroke_color,
                    stroke_width=stroke_width
                )

            logger.info(f"成功渲染气泡 {i} 文本: '{text[:20]}...' (方向: {text_direction})")
        except Exception as e:
            logger.error(f"渲染气泡 {i} 文本时出错: {e}", exc_info=True)

def render_single_bubble(
    image,
    bubble_index,
    all_texts,
    bubble_coords,
    fontSize=constants.DEFAULT_FONT_SIZE,
    fontFamily=constants.DEFAULT_FONT_RELATIVE_PATH,
    text_direction=constants.DEFAULT_TEXT_DIRECTION,
    position_offset={'x': 0, 'y': 0},
    use_inpainting=False,
    is_single_bubble_style=False,
    text_color=constants.DEFAULT_TEXT_COLOR,
    rotation_angle=constants.DEFAULT_ROTATION_ANGLE,
    use_lama=False,
    fill_color=constants.DEFAULT_FILL_COLOR,
    # 新增描边参数 (这些应来自前端对单个气泡的设置，或全局设置)
    enable_stroke_param=False,
    stroke_color_param="#FFFFFF",
    stroke_width_param=0
    ):
    """
    使用新的文本和样式重新渲染单个气泡（通过更新样式并渲染所有气泡实现）。
    """
    logger.info(f"开始渲染单气泡 {bubble_index}，字体: {fontFamily}, 大小: {fontSize}, 方向: {text_direction}")

    if bubble_index < 0 or bubble_index >= len(bubble_coords):
        logger.error(f"无效的气泡索引 {bubble_index}")
        return image # 返回原始图像

    # --- 获取基础图像 (优先使用干净背景) ---
    img_pil = None
    clean_image_base = None
    if hasattr(image, '_clean_image') and isinstance(getattr(image, '_clean_image'), Image.Image):
        clean_image_base = getattr(image, '_clean_image').copy()
        img_pil = clean_image_base
    elif hasattr(image, '_clean_background') and isinstance(getattr(image, '_clean_background'), Image.Image):
        clean_image_base = getattr(image, '_clean_background').copy()
        img_pil = clean_image_base

    if img_pil is None:
        logger.warning(f"单气泡 {bubble_index} 渲染时未找到干净背景，将执行修复/填充...")
        target_coords = [bubble_coords[bubble_index]]
        
        # 导入修复相关模块
        from src.core.inpainting import inpaint_bubbles
        from src.interfaces.lama_interface import is_lama_available
        # from src.interfaces.migan_interface import is_migan_available
        
        inpainting_method = 'solid'
        if use_lama and is_lama_available(): inpainting_method = 'lama'
        # elif use_inpainting and is_migan_available(): inpainting_method = 'migan'
        img_pil, generated_clean_bg = inpaint_bubbles(
            image, target_coords, method=inpainting_method, fill_color=fill_color
        )
        if generated_clean_bg: clean_image_base = generated_clean_bg.copy()

    # --- 获取或创建样式字典 ---
    bubble_styles_to_use = {}
    if hasattr(image, '_bubble_styles') and isinstance(getattr(image, '_bubble_styles'), dict):
         bubble_styles_to_use = getattr(image, '_bubble_styles').copy()
         bubble_styles_to_use = {str(k): v for k, v in bubble_styles_to_use.items()}
         logger.debug(f"单气泡渲染：从图像加载了 {len(bubble_styles_to_use)} 个样式。")
    else:
         logger.warning("单气泡渲染：未找到保存的气泡样式，将创建默认样式。")
         # 如果图像没有样式，为所有气泡创建基于全局默认的样式
         global_font_size_setting = constants.DEFAULT_FONT_SIZE # 或者从某个全局状态获取
         global_auto_font_size = False
         global_font_family = constants.DEFAULT_FONT_RELATIVE_PATH
         global_text_dir = constants.DEFAULT_TEXT_DIRECTION
         global_text_color = constants.DEFAULT_TEXT_COLOR
         global_rot_angle = constants.DEFAULT_ROTATION_ANGLE
         # 从函数参数获取全局描边设置（如果这是全局描边）
         global_enable_stroke = enable_stroke_param
         global_stroke_color = stroke_color_param
         global_stroke_width = stroke_width_param
    
         for i in range(len(bubble_coords)):
             bubble_styles_to_use[str(i)] = {
                 'fontSize': global_font_size_setting, 'autoFontSize': global_auto_font_size,
                 'fontFamily': global_font_family, 'text_direction': global_text_dir,
                 'position_offset': {'x': 0, 'y': 0}, 'text_color': global_text_color,
                 'rotation_angle': global_rot_angle,
                 'enableStroke': global_enable_stroke, # 添加全局描边
                 'strokeColor': global_stroke_color,
                 'strokeWidth': global_stroke_width
             }

    # --- 更新目标气泡的样式 ---
    target_style = bubble_styles_to_use.get(str(bubble_index), {}).copy() # 获取现有或空字典的副本
    is_auto_font_size = isinstance(fontSize, str) and fontSize.lower() == 'auto'
    target_font_rel = fontFamily # 假设 fontFamily 已经是相对路径
    
    target_style.update({
        'fontSize': fontSize, # 保存 'auto' 或数字
        'autoFontSize': is_auto_font_size,
        'fontFamily': target_font_rel,
        'text_direction': text_direction,
        'position_offset': position_offset,
        'text_color': text_color,
        'rotation_angle': rotation_angle,
        # 更新描边参数 (从函数参数获取，这些是针对这个气泡的最新设置)
        'enableStroke': enable_stroke_param,
        'strokeColor': stroke_color_param,
        'strokeWidth': stroke_width_param
    })
    
    # 如果是自动字号，需要计算并保存 (确保 calculate_auto_font_size 已导入)
    if is_auto_font_size:
         bubble_width = bubble_coords[bubble_index][2] - bubble_coords[bubble_index][0]
         bubble_height = bubble_coords[bubble_index][3] - bubble_coords[bubble_index][1]
         text_to_render = all_texts[bubble_index] if bubble_index < len(all_texts) else ""
         calculated_size = calculate_auto_font_size(
             text_to_render, bubble_width, bubble_height, text_direction, target_font_rel
         )
         target_style['calculated_font_size'] = calculated_size
         target_style['fontSize'] = calculated_size # 更新 fontSize 为计算值
         logger.info(f"单气泡 {bubble_index}: 自动计算字号为 {calculated_size}px")

    bubble_styles_to_use[str(bubble_index)] = target_style
    logger.debug(f"单气泡渲染：更新气泡 {bubble_index} 的样式为: {target_style}")

    # --- 更新目标气泡的文本 ---
    # 确保 all_texts 长度足够
    if len(all_texts) <= bubble_index:
         all_texts.extend([""] * (bubble_index - len(all_texts) + 1))
    # 更新文本 (假设 all_texts 是从前端获取的最新列表)
    # logger.debug(f"单气泡渲染：使用文本列表: {all_texts}")

    # --- 调用核心渲染函数渲染所有气泡 ---
    render_all_bubbles(
        img_pil,
        all_texts, # 传递包含所有最新文本的列表
        bubble_coords,
        bubble_styles_to_use # 传递更新后的样式字典
    )

    # --- 准备返回值 ---
    img_with_bubbles_pil = img_pil
    # 附加必要的属性
    if hasattr(image, '_lama_inpainted'): setattr(img_with_bubbles_pil, '_lama_inpainted', getattr(image, '_lama_inpainted', False))
    if clean_image_base:
         setattr(img_with_bubbles_pil, '_clean_image', clean_image_base)
         setattr(img_with_bubbles_pil, '_clean_background', clean_image_base)
    # 附加更新后的样式
    setattr(img_with_bubbles_pil, '_bubble_styles', bubble_styles_to_use)

    return img_with_bubbles_pil

def re_render_text_in_bubbles(
    image,
    all_texts,
    bubble_coords,
    fontSize=constants.DEFAULT_FONT_SIZE,
    fontFamily=constants.DEFAULT_FONT_RELATIVE_PATH,
    text_direction=constants.DEFAULT_TEXT_DIRECTION,
    use_inpainting=False,
    blend_edges=True,
    inpainting_strength=constants.DEFAULT_INPAINTING_STRENGTH,
    use_lama=False,
    fill_color=constants.DEFAULT_FILL_COLOR,
    text_color=constants.DEFAULT_TEXT_COLOR,
    rotation_angle=constants.DEFAULT_ROTATION_ANGLE,
    # 新增全局描边参数 (这些是全局设置，会应用到所有气泡，除非被 bubble_styles 覆盖)
    enable_stroke_param=False,
    stroke_color_param="#FFFFFF",
    stroke_width_param=0
    ):
    """
    使用新的文本和样式重新渲染气泡中的文字。
    """
    logger.info(f"开始重新渲染，字体: {fontFamily}, 大小: {fontSize}, 方向: {text_direction}")

    if not all_texts or not bubble_coords:
        logger.warning("缺少文本或坐标，无法重新渲染。")
        return image # 返回原始图像

    # --- 获取基础图像 (优先使用干净背景) ---
    img_pil = None
    clean_image_base = None
    if hasattr(image, '_clean_image') and isinstance(getattr(image, '_clean_image'), Image.Image):
        clean_image_base = getattr(image, '_clean_image').copy()
        img_pil = clean_image_base
        logger.info("重渲染：使用 _clean_image 作为基础。")
    elif hasattr(image, '_clean_background') and isinstance(getattr(image, '_clean_background'), Image.Image):
        clean_image_base = getattr(image, '_clean_background').copy()
        img_pil = clean_image_base
        logger.info("重渲染：使用 _clean_background 作为基础。")

    # 如果没有干净背景，则需要重新执行修复/填充
    if img_pil is None:
        logger.warning("重渲染时未找到干净背景，将重新执行修复/填充...")
        
        # 导入修复相关模块
        from src.core.inpainting import inpaint_bubbles
        from src.interfaces.lama_interface import is_lama_available
        # from src.interfaces.migan_interface import is_migan_available
        
        inpainting_method = 'solid'
        if use_lama and is_lama_available(): inpainting_method = 'lama'
        # elif use_inpainting and is_migan_available(): inpainting_method = 'migan'

        logger.info(f"重渲染时选择修复/填充方法: {inpainting_method}")
        img_pil, generated_clean_bg = inpaint_bubbles(
            image, bubble_coords, method=inpainting_method, fill_color=fill_color,
            migan_strength=inpainting_strength, migan_blend_edges=blend_edges
        )
        if generated_clean_bg: clean_image_base = generated_clean_bg.copy()

    # --- 准备样式字典 ---
    bubble_styles_to_use = {}
    
    # 检查图像是否已经有预定义的气泡样式字典
    if hasattr(image, '_bubble_styles') and isinstance(getattr(image, '_bubble_styles'), dict):
        # 优先使用预定义样式
        bubble_styles_to_use = getattr(image, '_bubble_styles').copy() # 深拷贝
        bubble_styles_to_use = {str(k): v for k, v in bubble_styles_to_use.items()}
        logger.info(f"使用图像预定义的气泡样式，共 {len(bubble_styles_to_use)} 个")
        # 对于已有的样式，如果它们没有描边属性，则用全局描边参数补充
        for i_str in bubble_styles_to_use:
            if 'enableStroke' not in bubble_styles_to_use[i_str]:
                bubble_styles_to_use[i_str]['enableStroke'] = enable_stroke_param
            if 'strokeColor' not in bubble_styles_to_use[i_str]:
                bubble_styles_to_use[i_str]['strokeColor'] = stroke_color_param
            if 'strokeWidth' not in bubble_styles_to_use[i_str]:
                bubble_styles_to_use[i_str]['strokeWidth'] = stroke_width_param
    else:
        # 没有预定义样式，使用全局设置创建新样式
        logger.info("没有找到预定义气泡样式，使用全局设置创建样式")
        
        # 获取全局设置参数
        is_auto_font_size_global = isinstance(fontSize, str) and fontSize.lower() == 'auto'
        font_family_rel = fontFamily
        
        logger.info(f"使用传入的全局颜色设置: {text_color}, 旋转角度: {rotation_angle}")
        
        # 为所有气泡创建新的样式字典，使用全局设置
        for i in range(len(bubble_coords)):
            bubble_styles_to_use[str(i)] = {
                'fontSize': fontSize,
                'autoFontSize': is_auto_font_size_global,
                'fontFamily': font_family_rel,
                'text_direction': text_direction,  # 全局文字方向
                'position_offset': {'x': 0, 'y': 0},  # 保持默认位置
                'text_color': text_color,  # 使用从请求获取的颜色
                'rotation_angle': rotation_angle,  # 使用从请求获取的旋转角度
                # 添加全局描边设置
                'enableStroke': enable_stroke_param,
                'strokeColor': stroke_color_param,
                'strokeWidth': stroke_width_param
            }

    # --- 调用核心渲染函数 ---
    render_all_bubbles(
        img_pil, # 在获取的基础图像上绘制
        all_texts,
        bubble_coords,
        bubble_styles_to_use
    )

    # --- 准备返回值 ---
    img_with_bubbles_pil = img_pil
    # 附加必要的属性
    if hasattr(image, '_lama_inpainted'): setattr(img_with_bubbles_pil, '_lama_inpainted', getattr(image, '_lama_inpainted', False))
    if clean_image_base:
         setattr(img_with_bubbles_pil, '_clean_image', clean_image_base)
         setattr(img_with_bubbles_pil, '_clean_background', clean_image_base)
    setattr(img_with_bubbles_pil, '_bubble_styles', bubble_styles_to_use) # 附加更新后的样式

    return img_with_bubbles_pil

# --- 测试代码 ---
if __name__ == '__main__':
    print("--- 测试渲染核心逻辑 (字体加载和自动字号) ---")

    # 测试字体加载
    print("\n测试字体加载:")
    font_default = get_font()
    print(f"默认字体: {type(font_default)}")
    font_custom = get_font(constants.DEFAULT_FONT_RELATIVE_PATH, 30) # 使用常量
    print(f"宋体 30px: {type(font_custom)}")
    font_cached = get_font(constants.DEFAULT_FONT_RELATIVE_PATH, 30)
    print(f"宋体 30px (缓存): {type(font_cached)}")
    font_fail = get_font("non_existent.ttf", 20)
    print(f"无效字体: {type(font_fail)}")

    # 测试自动字号
    print("\n测试自动字号:")
    text_short = "短文本"
    text_long_v = "这是一段非常非常非常非常非常非常非常非常非常非常非常非常长的竖排测试文本内容"
    text_long_h = "This is a very very very very very very very very very very very very long horizontal test text content"
    bubble_w, bubble_h = 100, 200

    size_short = calculate_auto_font_size(text_short, bubble_w, bubble_h, 'vertical')
    print(f"短文本竖排 ({bubble_w}x{bubble_h}): {size_short}px")

    size_long_v = calculate_auto_font_size(text_long_v, bubble_w, bubble_h, 'vertical')
    print(f"长文本竖排 ({bubble_w}x{bubble_h}): {size_long_v}px")

    size_long_h = calculate_auto_font_size(text_long_h, bubble_w, bubble_h, 'horizontal')
    print(f"长文本横排 ({bubble_w}x{bubble_h}): {size_long_h}px")

    size_long_h_wide = calculate_auto_font_size(text_long_h, 300, 100, 'horizontal')
    print(f"长文本横排宽气泡 (300x100): {size_long_h_wide}px")