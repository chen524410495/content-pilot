"""
AI写作助手 - 使用Claude API
"""

import anthropic
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class AIWriter:
    """AI写作助手"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def generate_article(self, topic: str, style: str = "技术教程",
                        length: str = "medium", platform: str = "通用") -> str:
        """
        生成文章

        参数:
            topic: 文章主题
            style: 文章风格 (技术教程/科普/深度分析/轻松随笔)
            length: 文章长度 (short/medium/long)
            platform: 目标平台 (知乎/掘金/CSDN/通用)
        返回:
            生成的Markdown文章内容
        """
        length_map = {
            "short": "800-1200字",
            "medium": "1500-2500字",
            "long": "3000-5000字"
        }
        length_desc = length_map.get(length, "1500-2500字")

        platform_hints = {
            "知乎": "适合深度分析，有理有据，可以适当引用数据和案例",
            "掘金": "适合技术分享，多用代码示例，结构清晰",
            "CSDN": "适合技术干货，代码为主，讲解详细",
            "通用": "结构清晰，内容充实，深入浅出"
        }
        platform_hint = platform_hints.get(platform, platform_hints["通用"])

        prompt = f"""你是一位资深的技术博主，擅长撰写高质量的技术文章。

请根据以下主题，写一篇{length_desc}的{style}风格文章。

主题: {topic}

要求:
1. {platform_hint}
2. 使用Markdown格式输出
3. 包含以下部分:
   - 引人入胜的开头（可以用故事/问题/数据引出）
   - 清晰的正文结构（小标题分隔）
   - 有价值的总结和行动建议
4. 可以适当添加代码示例（如果适用）
5. 添加3-5个相关标签

请直接输出文章内容，不要有其他说明文字。"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            return response.content[0].text

        except Exception as e:
            logger.error(f"AI写作失败: {str(e)}")
            raise

    def improve_article(self, content: str, instruction: str = "润色优化") -> str:
        """
        改进现有文章

        参数:
            content: 原始文章内容
            instruction: 改进要求 (润色/精简/扩展/改写)
        返回:
            改进后的文章
        """
        prompt = f"""你是一位资深编辑，擅长优化技术文章。

原始文章:
---
{content}
---

请对上述文章进行"{instruction}"，保持Markdown格式，输出优化后的内容。"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            return response.content[0].text

        except Exception as e:
            logger.error(f"AI优化失败: {str(e)}")
            raise

    def generate_title(self, content: str, platform: str = "通用") -> str:
        """
        生成吸引人的标题

        参数:
            content: 文章内容摘要
            platform: 目标平台
        返回:
            生成的标题
        """
        platform_hint = {
            "知乎": "吸引眼球，引发思考",
            "掘金": "技术感强，关键词突出",
            "CSDN": "SEO友好，技术明确",
            "通用": "清晰准确，有吸引力"
        }.get(platform, "")

        prompt = f"""请为以下文章生成3个吸引人的标题。

文章摘要:
{content[:500]}...

目标平台特点: {platform_hint}

要求:
1. 每个标题不超过30字
2. 标题要有吸引力但不要标题党
3. 包含关键词
4. 用换行分隔输出

请直接输出标题，不要有其他说明。"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=200,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            return response.content[0].text

        except Exception as e:
            logger.error(f"标题生成失败: {str(e)}")
            raise

    def suggest_tags(self, content: str, count: int = 5) -> List[str]:
        """
        推荐标签

        参数:
            content: 文章内容
            count: 推荐标签数量
        返回:
            标签列表
        """
        prompt = f"""请为以下文章推荐{count}个最合适的标签。

文章内容:
{content[:1000]}...

要求:
1. 每个标签2-4个字
2. 用中文
3. 标签要准确反映文章主题
4. 用逗号分隔输出

请直接输出标签，不要有其他说明。"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=100,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            tags_text = response.content[0].text.strip()
            # 解析逗号分隔的标签
            tags = [t.strip() for t in tags_text.split('，') if t.strip()]
            return tags[:count]

        except Exception as e:
            logger.error(f"标签推荐失败: {str(e)}")
            return []
