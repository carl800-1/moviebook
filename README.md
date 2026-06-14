# MovieBook

从 B站博主视频/评论中提取电影名，自动对接 NAS Tool 收藏电影/电视剧。

## 功能

- 📺 采集 B站 UP 主视频列表、评论、弹幕
- 🎬 智能提取电影/电视剧名称（正则 + TMDB 标准化）
- 📡 对接 NAS Tool 自动收藏
- ⏰ 支持定时运行和手动触发

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

复制 `config/config.example.yaml` 为 `config/config.yaml`，填入你的配置：

```bash
cp config/config.example.yaml config/config.yaml
```

### 3. 运行

```bash
python main.py
```

## 项目结构

```
moviebook/
├── main.py              # 入口
├── config/              # 配置文件
├── src/
│   ├── bilibili/        # B站数据采集
│   ├── extractor/       # 电影名提取与标准化
│   ├── nas/             # NAS Tool 对接
│   └── utils/           # 工具函数
├── logs/                # 日志
└── tests/               # 测试
```

## License

MIT
