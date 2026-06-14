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

### 2. 运行 GUI（推荐）

```bash
python3 gui.py
```

或者在 macOS 上直接双击打包好的 `dist/MovieBook.app`。

### 3. 获取 B站 Cookie

1. 浏览器打开 bilibili.com 并登录
2. 按 F12 → Network → 随便找个 bilibili.com 的请求
3. 复制 Cookie 头的值，粘贴到界面的 Cookie 输入框

### 4. 配置 NAS Tool

在界面左侧填入 NAS Tool 地址和 API Key。

## 打包

### macOS .app 应用（双击运行，无命令行窗口）

```bash
pyinstaller --onedir --windowed --name MovieBook gui.py
```

输出在 `dist/MovieBook.app`，可以复制到应用程序文件夹。

### Windows exe

```bash
pyinstaller --onefile --windowed --name MovieBook.exe gui.py
```

## 项目结构

```
moviebook/
├── gui.py                # GUI 窗口入口
├── main.py               # 命令行入口
├── demo.py               # 演示脚本（无需配置）
├── requirements.txt      # Python 依赖
├── config/
│   └── config.example.yaml
├── src/
│   ├── bilibili/        # B站数据采集
│   ├── extractor/       # 电影名提取与标准化
│   ├── nas/             # NAS Tool 对接
│   └── utils/           # 工具函数
├── dist/                 # 打包输出
├── logs/                 # 日志
└── tests/                # 测试
```

## License

MIT
