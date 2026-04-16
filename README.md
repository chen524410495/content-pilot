# ContentPilot - 多平台内容发布工具

AI驱动的一键发布工具，支持知乎、掘金、CSDN等平台。

## 功能特性

- 🤖 **AI写作助手** - 输入主题，AI帮你生成文章
- 📝 **多平台发布** - 一键发布到多个平台
- 🎨 **格式自动转换** - 自动适配各平台格式
- ⏰ **定时发布** - 定时发布任务
- 📊 **数据汇总** - 查看各平台发布状态

## 支持平台

- [x] 知乎
- [x] 掘金
- [x] CSDN
- [ ] 微信公众号（规划中）
- [ ] 小红书（规划中）

## 快速开始

### 安装

```bash
git clone https://github.com/chen524410495/content-pilot.git
cd content-pilot
pip install -r requirements.txt
```

### 配置

1. 复制配置文件：
```bash
cp config.example.yaml config.yaml
```

2. 填写API密钥：
```yaml
zhihu:
  client_id: "your_client_id"
  client_secret: "your_client_secret"

juejin:
  client_id: "your_client_id"
  client_secret: "your_client_secret"

csdn:
  username: "your_username"
  password: "your_password"

claude:
  api_key: "your_api_key"
```

### 运行

```bash
python main.py
```

然后访问 http://localhost:5000

## 项目结构

```
content-pilot/
├── main.py              # Web应用入口
├── config.example.yaml   # 配置文件示例
├── requirements.txt      # Python依赖
├── platforms/           # 平台API封装
│   ├── __init__.py
│   ├── zhihu.py         # 知乎API
│   ├── juejin.py        # 掘金API
│   └── csdn.py          # CSDN API
├── utils/               # 工具函数
│   ├── __init__.py
│   ├── ai_writer.py     # AI写作
│   └── formatter.py     # 格式转换
├── templates/           # Web模板
│   └── index.html
└── static/              # 静态文件
    └── style.css
```

## API接口

### 发布文章

```bash
POST /api/publish
{
  "title": "文章标题",
  "content": "文章内容",
  "platforms": ["zhihu", "juejin", "csdn"],
  "tags": ["Python", "AI"]
}
```

### AI写作

```bash
POST /api/ai-write
{
  "topic": "你想写什么话题",
  "style": "技术教程",
  "length": "medium"
}
```

## 开发说明

### 添加新平台

1. 在 `platforms/` 目录创建新的平台文件
2. 继承 `BasePlatform` 类
3. 实现必要的方法

```python
from platforms import BasePlatform

class MyPlatform(BasePlatform):
    name = "myplatform"
    
    def authenticate(self):
        # 认证逻辑
        pass
    
    def publish(self, title, content, tags):
        # 发布逻辑
        pass
```

## 许可证

MIT License

## Star History

[![Star History](https://api.star-history.com/svg?repos=chen524410495/content-pilot)](https://star-history.com/#chen524410495/content-pilot)
