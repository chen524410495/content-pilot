"""
ContentPilot - 多平台内容发布工具
平台基类和注册表
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class PlatformError(Exception):
    """平台相关错误"""
    pass


class AuthenticationError(PlatformError):
    """认证错误"""
    pass


class PublishError(PlatformError):
    """发布错误"""
    pass


class BasePlatform(ABC):
    """平台基类，所有平台需要实现此接口"""

    name: str = "base"  # 平台标识符
    display_name: str = "基础平台"  # 显示名称
    max_content_length: int = 50000  # 最大内容长度

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.access_token = config.get('access_token', '')
        self._authenticated = False

    @abstractmethod
    def authenticate(self) -> bool:
        """
        认证接口
        返回: 是否认证成功
        """
        pass

    @abstractmethod
    def publish(self, title: str, content: str, tags: List[str] = None,
                **kwargs) -> Dict[str, Any]:
        """
        发布文章
        参数:
            title: 文章标题
            content: 文章内容 (Markdown格式)
            tags: 标签列表
        返回:
            dict: {
                "success": bool,
                "article_id": str,
                "url": str,
                "message": str
            }
        """
        pass

    @abstractmethod
    def get_status(self, article_id: str) -> Dict[str, Any]:
        """
        获取文章状态
        """
        pass

    def validate_content(self, title: str, content: str) -> tuple[bool, str]:
        """
        验证内容是否合法
        返回: (是否合法, 错误信息)
        """
        if not title or len(title.strip()) == 0:
            return False, "标题不能为空"

        if len(title) > 100:
            return False, "标题长度不能超过100字符"

        if len(content) > self.max_content_length:
            return False, f"内容长度不能超过{self.max_content_length}字符"

        return True, ""

    def is_authenticated(self) -> bool:
        """检查是否已认证"""
        return self._authenticated

    def to_dict(self) -> Dict[str, Any]:
        """返回平台配置信息（不包含敏感数据）"""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "authenticated": self._authenticated
        }


class PlatformRegistry:
    """平台注册表"""

    _platforms: Dict[str, type] = {}

    @classmethod
    def register(cls, platform_class: type):
        """注册平台"""
        if not issubclass(platform_class, BasePlatform):
            raise ValueError(f"{platform_class} must inherit from BasePlatform")
        cls._platforms[platform_class.name] = platform_class
        logger.info(f"Registered platform: {platform_class.name}")

    @classmethod
    def get_platform(cls, name: str) -> Optional[type]:
        """获取平台类"""
        return cls._platforms.get(name)

    @classmethod
    def list_platforms(cls) -> List[str]:
        """列出所有已注册的平台"""
        return list(cls._platforms.keys())

    @classmethod
    def create_platform(cls, name: str, config: Dict[str, Any]) -> Optional[BasePlatform]:
        """创建平台实例"""
        platform_class = cls.get_platform(name)
        if platform_class:
            return platform_class(config)
        return None


# 导入并注册所有平台
from platforms.zhihu import ZhihuPlatform
from platforms.juejin import JuejinPlatform
from platforms.csdn import CSDNPlatform

__all__ = [
    'BasePlatform',
    'PlatformError', 
    'AuthenticationError',
    'PublishError',
    'PlatformRegistry'
]
