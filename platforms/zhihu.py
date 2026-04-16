"""
知乎平台API封装
文档: https://www.zhihu.com/apps
"""

import requests
import logging
from typing import List, Dict, Any
from urllib.parse import urlencode

from platforms import (
    BasePlatform,
    PlatformError,
    AuthenticationError,
    PublishError,
    PlatformRegistry
)

logger = logging.getLogger(__name__)


class ZhihuPlatform(BasePlatform):
    """知乎平台"""

    name = "zhihu"
    display_name = "知乎"
    max_content_length = 100000  # 知乎限制

    # 知乎API端点
    API_BASE = "https://api.zhihu.com"
    AUTH_URL = "https://api.zhihu.com/oauth/authoriz"
    TOKEN_URL = "https://api.zhihu.com/oauth/access_token"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client_id = config.get('client_id', '')
        self.client_secret = config.get('client_secret', '')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ContentPilot/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })

    def get_authorization_url(self, redirect_uri: str = "http://localhost:5000/callback/zhihu") -> str:
        """获取授权URL"""
        params = {
            'client_id': self.client_id,
            'redirect_uri': redirect_uri,
            'scope': 'answer.write article.publish',
            'response_type': 'code',
            'state': 'zhihu_auth'
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    def authenticate(self, code: str = None) -> bool:
        """
        认证接口
        如果有access_token直接使用，否则通过code换取
        """
        if self.access_token:
            # 验证token是否有效
            if self._verify_token():
                self._authenticated = True
                return True

        if not code:
            raise AuthenticationError("需要授权码进行认证")

        # 通过code获取access_token
        try:
            response = self.session.post(
                self.TOKEN_URL,
                json={
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': 'http://localhost:5000/callback/zhihu'
                }
            )
            data = response.json()

            if 'access_token' in data:
                self.access_token = data['access_token']
                self._authenticated = True
                self.session.headers.update({
                    'Authorization': f'Bearer {self.access_token}'
                })
                logger.info("知乎认证成功")
                return True
            else:
                raise AuthenticationError(f"获取token失败: {data.get('error', '未知错误')}")

        except requests.RequestException as e:
            raise AuthenticationError(f"知乎认证请求失败: {str(e)}")

    def _verify_token(self) -> bool:
        """验证token是否有效"""
        try:
            response = self.session.get(
                f"{self.API_BASE}/people/me",
                headers={'Authorization': f'Bearer {self.access_token}'}
            )
            return response.status_code == 200
        except:
            return False

    def publish(self, title: str, content: str, tags: List[str] = None,
                **kwargs) -> Dict[str, Any]:
        """
        发布文章到知乎

        参数:
            title: 文章标题
            content: 文章内容 (Markdown格式)
            tags: 标签列表
        """
        if not self._authenticated:
            raise PublishError("请先进行知乎认证")

        # 验证内容
        valid, msg = self.validate_content(title, content)
        if not valid:
            raise PublishError(msg)

        try:
            # 知乎文章API
            url = f"{self.API_BASE}/articles"

            # 构建文章数据
            article_data = {
                'title': title,
                'content': content,
                'content_type': 'markdown',
                'tags': tags or []
            }

            response = self.session.post(
                url,
                json=article_data
            )

            if response.status_code == 201:
                data = response.json()
                article_id = data.get('id', '')
                return {
                    'success': True,
                    'article_id': str(article_id),
                    'url': f"https://zhuanlan.zhihu.com/p/{article_id}",
                    'message': '发布成功'
                }
            else:
                error_msg = response.json().get('error', {}).get('message', '发布失败')
                raise PublishError(f"知乎发布失败: {error_msg}")

        except requests.RequestException as e:
            raise PublishError(f"知乎发布请求失败: {str(e)}")

    def get_status(self, article_id: str) -> Dict[str, Any]:
        """获取文章状态"""
        try:
            response = self.session.get(
                f"{self.API_BASE}/articles/{article_id}"
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    'article_id': article_id,
                    'title': data.get('title', ''),
                    'status': 'published' if data.get('is_published') else 'draft',
                    'url': f"https://zhuanlan.zhihu.com/p/{article_id}",
                    'stats': {
                        'likes': data.get('voteup_count', 0),
                        'comments': data.get('comment_count', 0),
                        'views': data.get('view_count', 0)
                    }
                }
            else:
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
                f"{self.API_BASE}/people/me",
                headers={'Authorization': f'Bearer {self.access_token}'}
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    'name': data.get('name', ''),
                    'url': data.get('url', ''),
                    'followers': data.get('follower_count', 0)
                }
            return {}

        except:
            return {}

    def list_articles(self, count: int = 10) -> List[Dict[str, Any]]:
        """列出用户的文章"""
        try:
            response = self.session.get(
                f"{self.API_BASE}/articles",
                params={'count': count},
                headers={'Authorization': f'Bearer {self.access_token}'}
            )

            if response.status_code == 200:
                data = response.json()
                articles = []
                for item in data.get('data', []):
                    articles.append({
                        'id': item.get('id'),
                        'title': item.get('title'),
                        'url': f"https://zhuanlan.zhihu.com/p/{item.get('id')}",
                        'created': item.get('created_time'),
                        'status': 'published' if item.get('is_published') else 'draft'
                    })
                return articles
            return []

        except:
            return []


# 注册平台
PlatformRegistry.register(ZhihuPlatform)
