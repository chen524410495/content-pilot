"""
ContentPilot - Web应用入口
多平台内容发布工具
"""

import os
import yaml
import logging
from datetime import datetime
from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, session, flash
)
from apscheduler.schedulers.background import BackgroundScheduler

from platforms import PlatformRegistry
from utils import AIWriter, ContentFormatter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'content-pilot-secret-key-2024')

# 加载配置
def load_config():
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    if not os.path.exists(config_path):
        config_path = os.path.join(os.path.dirname(__file__), 'config.example.yaml')

    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

config = load_config()

# 初始化平台
platforms = {}
def init_platforms():
    """初始化所有平台"""
    platform_names = PlatformRegistry.list_platforms()
    for name in platform_names:
        platform_config = config.get(name, {})
        if platform_config:
            platform = PlatformRegistry.create_platform(name, platform_config)
            if platform:
                platforms[name] = platform
                logger.info(f"Initialized platform: {name}")

init_platforms()

# AI写作助手
ai_writer = None
if config.get('claude', {}).get('api_key'):
    ai_writer = AIWriter(config['claude']['api_key'])

# 定时任务调度器
scheduler = BackgroundScheduler()


@app.route('/')
def index():
    """首页"""
    platform_status = []
    for name, platform in platforms.items():
        info = platform.to_dict()
        platform_status.append(info)

    return render_template('index.html',
                         platforms=platform_status,
                         ai_enabled=ai_writer is not None)


@app.route('/auth/<platform_name>')
def auth_platform(platform_name):
    """平台授权"""
    if platform_name not in platforms:
        flash(f'未知平台: {platform_name}', 'error')
        return redirect(url_for('index'))

    platform = platforms[platform_name]

    # 如果平台支持获取授权URL
    if hasattr(platform, 'get_authorization_url'):
        auth_url = platform.get_authorization_url()
        return redirect(auth_url)

    # 否则尝试直接认证
    try:
        platform.authenticate()
        flash(f'{platform.display_name} 认证成功！', 'success')
    except Exception as e:
        flash(f'{platform.display_name} 认证失败: {str(e)}', 'error')

    return redirect(url_for('index'))


@app.route('/callback/<platform_name>')
def callback(platform_name):
    """OAuth回调"""
    if platform_name not in platforms:
        return jsonify({'error': '未知平台'}), 400

    code = request.args.get('code')

    try:
        platform = platforms[platform_name]
        platform.authenticate(code=code)
        flash(f'{platform.display_name} 授权成功！', 'success')
    except Exception as e:
        flash(f'{platform.display_name} 授权失败: {str(e)}', 'error')

    return redirect(url_for('index'))


@app.route('/api/publish', methods=['POST'])
def api_publish():
    """发布文章到多个平台"""
    data = request.get_json()

    title = data.get('title', '')
    content = data.get('content', '')
    tags = data.get('tags', [])
    target_platforms = data.get('platforms', [])

    if not title or not content:
        return jsonify({'success': False, 'error': '标题和内容不能为空'}), 400

    if not target_platforms:
        return jsonify({'success': False, 'error': '请选择至少一个平台'}), 400

    results = []

    for platform_name in target_platforms:
        if platform_name not in platforms:
            results.append({
                'platform': platform_name,
                'success': False,
                'error': '平台未配置'
            })
            continue

        platform = platforms[platform_name]

        # 检查认证状态
        if not platform.is_authenticated():
            try:
                platform.authenticate()
            except:
                results.append({
                    'platform': platform.display_name,
                    'success': False,
                    'error': '请先进行认证'
                })
                continue

        try:
            result = platform.publish(title, content, tags)
            results.append({
                'platform': platform.display_name,
                'success': True,
                'article_id': result.get('article_id'),
                'url': result.get('url'),
                'message': result.get('message', '发布成功')
            })
        except Exception as e:
            results.append({
                'platform': platform.display_name,
                'success': False,
                'error': str(e)
            })

    success_count = sum(1 for r in results if r['success'])
    return jsonify({
        'success': success_count > 0,
        'total': len(results),
        'success_count': success_count,
        'results': results
    })


@app.route('/api/ai-write', methods=['POST'])
def api_ai_write():
    """AI写作接口"""
    if not ai_writer:
        return jsonify({'success': False, 'error': 'AI功能未启用'}), 400

    data = request.get_json()
    topic = data.get('topic', '')
    style = data.get('style', '技术教程')
    length = data.get('length', 'medium')
    target_platform = data.get('platform', '通用')

    if not topic:
        return jsonify({'success': False, 'error': '请输入文章主题'}), 400

    try:
        content = ai_writer.generate_article(
            topic=topic,
            style=style,
            length=length,
            platform=target_platform
        )

        # 自动生成标题
        first_lines = '\n'.join(content.split('\n')[:5])
        suggested_titles = ai_writer.generate_title(first_lines, target_platform)

        # 推荐标签
        suggested_tags = ai_writer.suggest_tags(content)

        return jsonify({
            'success': True,
            'content': content,
            'titles': suggested_titles,
            'tags': suggested_tags,
            'read_time': ContentFormatter.estimate_read_time(content)
        })

    except Exception as e:
        logger.error(f"AI写作失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/improve', methods=['POST'])
def api_improve():
    """AI优化文章"""
    if not ai_writer:
        return jsonify({'success': False, 'error': 'AI功能未启用'}), 400

    data = request.get_json()
    content = data.get('content', '')
    instruction = data.get('instruction', '润色优化')

    if not content:
        return jsonify({'success': False, 'error': '请输入文章内容'}), 400

    try:
        improved = ai_writer.improve_article(content, instruction)
        return jsonify({
            'success': True,
            'content': improved,
            'read_time': ContentFormatter.estimate_read_time(improved)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/platforms/status')
def api_platforms_status():
    """获取所有平台状态"""
    status = {}
    for name, platform in platforms.items():
        try:
            if platform.is_authenticated():
                user_info = platform.get_user_info()
                status[name] = {
                    'authenticated': True,
                    'user': user_info
                }
            else:
                status[name] = {
                    'authenticated': False
                }
        except:
            status[name] = {
                'authenticated': False,
                'error': '获取状态失败'
            }

    return jsonify(status)


@app.route('/api/schedule', methods=['POST'])
def api_schedule():
    """定时发布"""
    data = request.get_json()

    title = data.get('title', '')
    content = data.get('content', '')
    tags = data.get('tags', [])
    platforms_list = data.get('platforms', [])
    publish_time = data.get('publish_time')  # ISO格式时间

    if not title or not content:
        return jsonify({'success': False, 'error': '标题和内容不能为空'}), 400

    if not publish_time:
        return jsonify({'success': False, 'error': '请指定发布时间'}), 400

    try:
        from datetime import datetime
        dt = datetime.fromisoformat(publish_time)

        job_id = f"publish_{dt.timestamp()}"

        def publish_job():
            with app.app_context():
                for platform_name in platforms_list:
                    if platform_name in platforms:
                        platform = platforms[platform_name]
                        try:
                            platform.publish(title, content, tags)
                            logger.info(f"定时发布成功: {platform_name}")
                        except Exception as e:
                            logger.error(f"定时发布失败: {platform_name} - {str(e)}")

        scheduler.add_job(
            publish_job,
            'date',
            run_date=dt,
            id=job_id
        )

        return jsonify({
            'success': True,
            'job_id': job_id,
            'publish_time': publish_time
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/format', methods=['POST'])
def api_format():
    """格式化内容"""
    data = request.get_json()
    content = data.get('content', '')
    platform = data.get('platform', '通用')

    if not content:
        return jsonify({'success': False, 'error': '内容不能为空'}), 400

    try:
        formatted = ContentFormatter.adapt_for_platform(content, platform)
        summary = ContentFormatter.generate_summary(formatted)
        read_time = ContentFormatter.estimate_read_time(formatted)

        return jsonify({
            'success': True,
            'content': formatted,
            'summary': summary,
            'read_time': read_time
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    # 启动定时任务调度器
    scheduler.start()
    logger.info("定时任务调度器已启动")

    # 启动Web服务
    server_config = config.get('server', {})
    host = server_config.get('host', '0.0.0.0')
    port = server_config.get('port', 5000)
    debug = server_config.get('debug', True)

    logger.info(f"ContentPilot 启动于 http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
