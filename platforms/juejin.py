"""
掘金平台API封装
文档: https://juejin.cn/extensions
"""

import requests
import logging
from typing import List, Dict, Any

from platforms import (
    BasePlatform,
    PlatformError,
    AuthenticationError,
    PublishError,
    PlatformRegistry
)

logger = logging.getLogger(__name__)


class JuejinPlatform(BasePlatform):
    """掘金平台"""

    name = "juejin"
    display_name = "掘金"
    max_content_length = 100000  # 掘金限制

    # 掘金API端点
    API_BASE = "https://api.juejin.cn"
    AUTH_URL = "https://juejin.cn/auth/authorization"
    TOKEN_URL = "https://api.juejin.cn/user/oauth2/token"

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

    def get_authorization_url(self, redirect_uri: str = "http://localhost:5000/callback/juejin") -> str:
        """获取授权URL"""
        import urllib.parse
        params = {
            'client_id': self.client_id,
            'redirect_uri': redirect_uri,
            'scope': '',
            'response_type': 'code',
            'state': 'juejin_auth'
        }
        return f"{self.AUTH_URL}?{urllib.parse.urlencode(params)}"

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
                    'redirect_uri': 'http://localhost:5000/callback/juejin'
                }
            )
            data = response.json()

            if 'data' in data and 'access_token' in data['data']:
                self.access_token = data['data']['access_token']
                self._authenticated = True
                self.session.headers.update({
                    'Authorization': f'Bearer {self.access_token}'
                })
                logger.info("掘金认证成功")
                return True
            else:
                raise AuthenticationError(f"获取token失败: {data.get('err_msg', '未知错误')}")

        except requests.RequestException as e:
            raise AuthenticationError(f"掘金认证请求失败: {str(e)}")

    def _verify_token(self) -> bool:
        """验证token是否有效"""
        try:
            response = self.session.post(
                f"{self.API_BASE}/user/verify_token",
                headers={'Authorization': f'Bearer {self.access_token}'}
            )
            return response.status_code == 200 and response.json().get('err_no') == 0
        except:
            return False

    def publish(self, title: str, content: str, tags: List[str] = None,
                category: str = "全部", **kwargs) -> Dict[str, Any]:
        """
        发布文章到掘金

        参数:
            title: 文章标题
            content: 文章内容 (Markdown格式)
            tags: 标签列表
            category: 文章分类 (全部/前端/JavaScript/后端/Python等)
        """
        if not self._authenticated:
            raise PublishError("请先进行掘金认证")

        # 验证内容
        valid, msg = self.validate_content(title, content)
        if not valid:
            raise PublishError(msg)

        try:
            # 掘金发布文章API
            url = f"{self.API_BASE}/content_api/v1/article"

            # 转换分类
            category_map = {
                "全部": 0,
                "前端": 1,
                "后端": 2,
                "Android": 3,
                "iOS": 4,
                "人工智能": 5,
                "开发工具": 6,
                "阅读": 7
            }
            category_id = category_map.get(category, 0)

            # 构建文章数据
            article_data = {
                'title': title,
                'content': content,
                'content_type': 'markdown',
                'category': category_id,
                'tags': tags or [],
                'status': 1  # 1=发布, 4=草稿
            }

            response = self.session.post(
                url,
                json=article_data
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('err_no') == 0:
                    article_data_resp = data.get('data', {})
                    article_id = article_data_resp.get('article_id', '')
                    return {
                        'success': True,
                        'article_id': str(article_id),
                        'url': f"https://juejin.cn/post/{article_id}",
                        'message': '发布成功'
                    }
                else:
                    raise PublishError(f"掘金发布失败: {data.get('err_msg', '未知错误')}")
            else:
                raise PublishError(f"掘金发布失败: HTTP {response.status_code}")

        except requests.RequestException as e:
            raise PublishError(f"掘金发布请求失败: {str(e)}")

    def get_status(self, article_id: str) -> Dict[str, Any]:
        """获取文章状态"""
        try:
            response = self.session.get(
                f"{self.API_BASE}/content_api/v1/article/{article_id}"
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('err_no') == 0:
                    article_data = data.get('data', {})
                    return {
                        'article_id': article_id,
                        'title': article_data.get('title', ''),
                        'status': 'published' if article_data.get('status') == 1 else 'draft',
                        'url': f"https://juejin.cn/post/{article_id}",
                        'stats': {
                            'likes': article_data.get('digg_count', 0),
                            'comments': article_data.get('comment_count', 0),
                            'views': article_data.get('view_count', 0)
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
                f"{self.API_BASE}/user/api/v1/user_info",
                headers={'Authorization': f'Bearer {self.access_token}'}
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('err_no') == 0:
                    user_data = data.get('data', {})
                    return {
                        'name': user_data.get('name', ''),
                        'url': f"https://juejin.cn/user/{user_data.get('user_id', '')}",
                        'followers': user_data.get('follower_count', 0)
                    }
            return {}

        except:
            return {}

    def list_articles(self, count: int = 10) -> List[Dict[str, Any]]:
        """列出用户的文章"""
        try:
            response = self.session.get(
                f"{self.API_BASE}/content_api/v1/article/user_list",
                params={'count': count},
                headers={'Authorization': f'Bearer {self.access_token}'}
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('err_no') == 0:
                    articles = []
                    for item in data.get('data', []):
                        articles.append({
                            'id': item.get('article_id'),
                            'title': item.get('title'),
                            'url': f"https://juejin.cn/post/{item.get('article_id')}",
                            'created': item.get('ctime'),
                            'status': 'published' if item.get('status') == 1 else 'draft'
                        })
                    return articles
            return []

        except:
            return []


# 注册平台
PlatformRegistry.register(JuejinPlatform)
