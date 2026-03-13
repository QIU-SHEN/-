# WeChat AI Publisher

微信公众号自动发布工具

## 功能

- **ResearchAgent** - 获取热点新闻
- **WritingAgent** - AI撰写文章
- **ComplianceAgent** - 合规审查
- **PublishAgent** - 自动发布

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行

```bash
# GUI版本（推荐）
python gui_app.py

# 命令行版本
python auto_publish.py
```

### 3. 使用

1. 选择新闻类型（科技/财经/娱乐等）
2. 输入作者名字
3. 点击"一键发布"
4. 扫码确认完成发布

## 文件结构

```
.
├── auto_publish.py          # 命令行版本
├── gui_app.py               # GUI版本（微信风格）
├── requirements.txt         # 依赖
├── src/
│   └── agents/
│       ├── research_agent.py    # 热点获取
│       ├── writing_agent.py     # 文章撰写
│       ├── compliance_agent.py  # 合规审查
│       └── publish_agent.py     # 发布
│   └── tools/
│       ├── rpa_tool.py          # RPA自动化
│       └── wechat_api.py        # 微信API
├── config/
│   └── config.yaml          # 配置
└── data/
    ├── hot_topics/          # 热点文件
    ├── articles/            # 生成的文章
    └── rpa_state/           # 登录状态
```

## 配置

编辑 `config/config.yaml`:

```yaml
wechat:
  use_rpa: true
  auto_publish: true  # true=直接发布, false=保存草稿

api:
  ecnu_key: "your-api-key"
```

## 依赖

- Python 3.10+
- playwright - 浏览器自动化
- requests - HTTP请求
- pywebview - GUI界面
- pyyaml - 配置解析

## 说明

- 首次运行需下载Playwright浏览器（约100MB）
- 登录状态保存在 `data/rpa_state/`
- 生成的文章保存在 `data/articles/`
