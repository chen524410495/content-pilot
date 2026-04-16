"""
CSDN平台API封装
CSDN无需OAuth，直接使用用户名密码登录
"""

import requests
import logging
import re
from typing import List, Dict, Any

from platforms import (
    BasePlatform,
    PlatformError,
    AuthenticationError,
    PublishError,
    PlatformRegistry
)

logger = logging.getLogger(__name__)


class CSDNPlatform(BasePlatform):
    """CSDN平台"""

    name = "csdn"
    display_name = "CSDN"
    max_content_length = 50000

    # CSDN API端点
    API_BASE = "https://bizapi.csdn.net"
    LOGIN_URL = "https://passport.csdn.net/v2/login"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.username = config.get('username', '')
        self.password = config.get('password', '')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })

    def authenticate(self) -> bool:
        """
        CSDN认证
        使用用户名密码登录获取cookie
        """
        try:
            # 方法1: 使用OAuth登录
            login_url = f"{self.API_BASE}/user/api/v1/login/quick"

            response = self.session.post(
                login_url,
                json={
                    'username': self.username,
                    'password': self.password
                }
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 200:
                    # 保存cookie用于后续请求
                    self.session.headers.update({
                        'X-Csrf-Token': data.get('data', {}).get('csrf', '')
                    })
                    self._authenticated = True
                    logger.info("CSDN认证成功")
                    return True

            # 方法2: 直接设置cookie（如果方法1失败）
            if not self._authenticated:
                # CSDN有时候需要先获取token
                token_url = "https://passport.csdn.net/v2/api/v1/login"
                token_resp = self.session.get(token_url)
                if token_resp.status_code == 200:
                    self._authenticated = True
                    return True

            raise AuthenticationError(f"CSDN登录失败: {response.text[:200]}")

        except requests.RequestException as e:
            raise AuthenticationError(f"CSDN认证请求失败: {str(e)}")

    def publish(self, title: str, content: str, tags: List[str] = None,
                **kwargs) -> Dict[str, Any]:
        """
        发布文章到CSDN

        参数:
            title: 文章标题
            content: 文章内容 (Markdown格式)
            tags: 标签列表
        """
        if not self._authenticated:
            raise PublishError("请先进行CSDN认证")

        # 验证内容
        valid, msg = self.validate_content(title, content)
        if not valid:
            raise PublishError(msg)

        try:
            # CSDN发布文章API
            url = f"{self.API_BASE}/blog/v2/article"

            # 转换tags为字符串
            tag_string = ','.join(tags) if tags else ''

            # 构建文章数据
            article_data = {
                'title': title,
                'content': content,
                'content_type': 'markdown',
                'tags': tag_string,
                'status': 1,  # 1=发布, 0=草稿
                'original': 1,  # 1=原创, 0=转载
                'type': 'original'
            }

            response = self.session.post(
                url,
                json=article_data
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 200:
                    article_id = data.get('data', {}).get('id', '')
                    return {
                        'success': True,
                        'article_id': str(article_id),
                        'url': f"https://blog.csdn.net/{self.username}/article/details/{article_id}",
                        'message': '发布成功'
                    }
                else:
                    raise PublishError(f"CSDN发布失败: {data.get('message', '未知错误')}")
            else:
                raise PublishError(f"CSDN发布失败: HTTP {response.status_code}")

        except requests.RequestException as e:
            raise PublishError(f"CSDN发布请求失败: {str(e)}")

    def get_status(self, article_id: str) -> Dict[str, Any]:
        """获取文章状态"""
        try:
            response = self.session.get(
                f"{self.API_BASE}/blog/v1/article/{article_id}"
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 200:
                    article_data = data.get('data', {})
                    return {
                        'article_id': article_id,
                        'title': article_data.get('title', ''),
                        'status': 'published' if article_data.get('status') == 1 else 'draft',
                        'url': f"https://blog.csdn.net/{self.username}/article/details/{article_id}",
                        'stats': {
                            'views': article_data.get('view_count', 0),
                            'likes': article_data.get('digg_count', 0),
                            'comments': article_data.get('comment_count', 0)
                        }
                    }
            return {
                'article_id': article_id,
                'status': 'unknown',
                'message': '获取状态失败'
            }

        except requests.RequestException:
            return {
                'article_id': article_id,
                'status': 'error',
                'message': '请求失败'
            }

    def get_user_info(self) -> Dict[str, Any]:
        """获取用户信息"""
        try:
            response = self.session.get(
                f"{self.API_BASE}/blog/v1/user/info"
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 200:
                    user_data = data.get('data', {})
                    return {
                        'name': user_data.get('username', ''),
                        'url': f"https://blog.csdn.net/{user_data.get('username', '')}",
                        'followers': user_data.get('followers', 0)
                    }
            return {}

        except:
            return {}

    def list_articles(self, count: int = 10) -> List[Dict[str, Any]]:
        """列出用户的文章"""
        try:
            response = self.session.get(
                f"{self.API_BASE}/blog/v1/article/user/list",
                params={'count': count}
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 200:
                    articles = []
                    for item in data.get('data', []):
                        articles.append({
                            'id': item.get('id'),
                            'title': item.get('title'),
                            'url': f"https://blog.csdn.net/{self.username}/article/details/{item.get('id')}",
                            'created': item.get('create_time'),
                            'status': 'published' if item.get('status') == 1 else 'draft'
                        })
                    return articles
            return []

        except:
            return []


# 注册平台
PlatformRegistry.register(CSDNPlatform)
