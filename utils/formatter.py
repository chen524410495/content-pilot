"""
格式转换器 - 各平台格式适配
"""

import re
import markdown
from typing import Dict, List, Any
from html.parser import HTMLParser


class HTMLTextExtractor(HTMLParser):
    """从HTML中提取纯文本"""

    def __init__(self):
        super().__init__()
        self.text_parts = []

    def handle_data(self, data):
        self.text_parts.append(data)

    def get_text(self):
        return ''.join(self.text_parts)


class ContentFormatter:
    """内容格式转换器"""

    # 各平台支持的Markdown扩展
    PLATFORM_FEATURES = {
        "zhihu": {
            "code_block": True,  # 代码块
            "math": True,  # 数学公式
            "table": True,  # 表格
            "toc": True,  # 目录
            "quote": True,  # 引用
            "image": True,  # 图片
            "video": True,  # 视频
        },
        "juejin": {
            "code_block": True,
            "math": False,
            "table": True,
            "toc": False,
            "quote": True,
            "image": True,
            "video": False,
        },
        "csdn": {
            "code_block": True,
            "math": True,
            "table": True,
            "toc": False,
            "quote": True,
            "image": True,
            "video": False,
        },
        "通用": {
            "code_block": True,
            "math": True,
            "table": True,
            "toc": True,
            "quote": True,
            "image": True,
            "video": False,
        }
    }

    @classmethod
    def markdown_to_html(cls, markdown_text: str, platform: str = "通用") -> str:
        """
        将Markdown转换为HTML

        参数:
            markdown_text: Markdown格式文本
            platform: 目标平台
        返回:
            HTML格式文本
        """
        # 基础转换
        html = markdown.markdown(
            markdown_text,
            extensions=[
                'tables',       # 表格
                'fenced_code',  # 代码块
                'nl2br',       # 换行转<br>
                'sane_lists',  # 列表
            ]
        )

        # 平台特定处理
        features = cls.PLATFORM_FEATURES.get(platform, cls.PLATFORM_FEATURES["通用"])

        if not features.get("image"):
            # 移除图片标签
            html = re.sub(r'<img[^>]*>', '', html)

        if not features.get("video"):
            # 移除视频标签
            html = re.sub(r'<video[^>]*>.*?</video>', '', html, flags=re.DOTALL)

        return html

    @classmethod
    def html_to_text(cls, html_text: str) -> str:
        """从HTML提取纯文本"""
        extractor = HTMLTextExtractor()
        extractor.feed(html_text)
        return extractor.get_text()

    @classmethod
    def clean_markdown(cls, markdown_text: str) -> str:
        """清理Markdown文本"""
        # 移除多余的空行
        text = re.sub(r'\n{3,}', '\n\n', markdown_text)

        # 移除可疑的URL（可能是追踪链接）
        text = re.sub(r'\[([^\]]+)\]\(https?://[^\)]*utm_[^\)]*\)', r'\1', text)

        # 规范化代码块标记
        text = re.sub(r'```(\w+)', r'```\1', text)

        return text.strip()

    @classmethod
    def adapt_for_platform(cls, markdown_text: str, platform: str) -> str:
        """
        根据平台特性适配内容

        参数:
            markdown_text: 原始Markdown
            platform: 目标平台
        返回:
            适配后的Markdown
        """
        text = cls.clean_markdown(markdown_text)
        features = cls.PLATFORM_FEATURES.get(platform, cls.PLATFORM_FEATURES["通用"])

        if not features.get("toc"):
            # 移除目录
            text = re.sub(r'\[TOC\]\s*', '', text, flags=re.IGNORECASE)

        if not features.get("math"):
            # 移除数学公式（保留普通文本）
            text = re.sub(r'\$\$[^\$]+\$\$', '', text)
            text = re.sub(r'\$[^\$]+\$', '', text)

        return text

    @classmethod
    def extract_first_paragraph(cls, markdown_text: str) -> str:
        """提取文章第一段（用于摘要）"""
        # 移除front matter
        text = re.sub(r'^---.*?---\s*', '', markdown_text, flags=re.DOTALL)

        # 移除标题
        lines = text.split('\n')
        paragraphs = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith('#'):
                continue
            if line.startswith('```'):
                continue
            if line.startswith('!['):
                continue
            paragraphs.append(line)
            if len('\n'.join(paragraphs)) > 200:
                break

        return '\n'.join(paragraphs)[:200]

    @classmethod
    def split_into_sections(cls, markdown_text: str) -> List[Dict[str, str]]:
        """将文章拆分为多个章节"""
        sections = []
        current_title = "开头"
        current_content = []

        lines = markdown_text.split('\n')
        for line in lines:
            # 检测一级标题
            if line.startswith('# '):
                if current_content:
                    sections.append({
                        'title': current_title,
                        'content': '\n'.join(current_content).strip()
                    })
                current_title = line[2:].strip()
                current_content = []
            else:
                current_content.append(line)

        # 添加最后一个章节
        if current_content:
            sections.append({
                'title': current_title,
                'content': '\n'.join(current_content).strip()
            })

        return sections

    @classmethod
    def estimate_read_time(cls, markdown_text: str) -> int:
        """
        估算阅读时间（分钟）

        基于中文字数计算，假设阅读速度400字/分钟
        """
        # 提取纯文本
        text = re.sub(r'```[\s\S]*?```', '', markdown_text)  # 移除代码块
        text = re.sub(r'`[^`]+`', '', text)  # 移除行内代码
        text = re.sub(r'#+\s*', '', text)  # 移除标题标记
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # 移除链接

        # 计算中文字符数
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        # 计算英文单词数（每个单词约1.5个字符）
        english_words = len(re.findall(r'[a-zA-Z]+', text))
        english_chars = english_words * 5

        total_chars = chinese_chars + english_chars
        minutes = max(1, round(total_chars / 400))

        return minutes

    @classmethod
    def generate_summary(cls, markdown_text: str, max_length: int = 100) -> str:
        """生成文章摘要"""
        first_para = cls.extract_first_paragraph(markdown_text)
        summary = cls.html_to_text(first_para)

        if len(summary) > max_length:
            summary = summary[:max_length] + "..."

        return summary

    @classmethod
    def sanitize_html(cls, html_text: str, allowed_tags: List[str] = None) -> str:
        """
        清理HTML，只保留安全的标签

        参数:
            html_text: HTML文本
            allowed_tags: 允许的标签列表
        """
        if allowed_tags is None:
            allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3',
                           'ul', 'ol', 'li', 'blockquote', 'pre', 'code', 'a',
                           'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td']

        # 简单实现，实际生产环境应该用bleach库
        return html_text
