"""
MovieBook GUI - tkinter 窗口应用 (macOS / Windows)
运行: python3 gui.py
打包: pyinstaller --onedir --windowed --name MovieBook gui.py
"""
import json
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, scrolledtext, messagebox

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

CONFIG_FILE = PROJECT_ROOT / "config" / "config.json"

# ── 中文字体 ──
FONT_FAMILY = "PingFang SC"
FONT_SIZE = 11
FONT_MONO = "Menlo"

# ─────────────────────────── 配置读写 ───────────────────────────

def load_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "bili_cookie": "",
        "tmdb_api_key": "",
        "nas_url": "",
        "nas_api_key": "",
        "fetch_danmaku": True,
        "fetch_comments": True,
        "max_videos": 20,
        "max_comments": 100,
        "use_tmdb": True,
    }


def save_config(cfg: dict):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ─────────────────────────── 登录线程 ───────────────────────────

class LoginThread:
    def __init__(self, cookie_str: str, log_callback, done_callback):
        self.cookie_str = cookie_str
        self.log_callback = log_callback
        self.done_callback = done_callback
        self.credential = None

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._login())
            loop.close()
        except Exception as e:
            self.log_callback(f"登录异常: {e}\n")
        finally:
            self.done_callback(self.credential)

    async def _login(self):
        from bilibili_api import Credential, user

        self.log_callback("正在验证 B站登录...\n")

        cookies = {}
        for item in self.cookie_str.split(";"):
            item = item.strip()
            if "=" in item:
                k, v = item.split("=", 1)
                cookies[k.strip()] = v.strip()

        if not cookies:
            self.log_callback("Cookie 为空，请检查输入。\n")
            return

        cred = Credential.from_cookies(cookies)
        u = user.User(cred=cred)
        try:
            info = await u.get_self_info()
            name = info.get("name", "unknown")
            uid = info.get("mid", "?")
            self.log_callback(f"登录成功！用户: {name} (UID: {uid})\n")
            self.credential = cred
        except Exception as e:
            self.log_callback(f"Cookie 无效或已过期: {e}\n")


# ─────────────────────────── 运行线程 ───────────────────────────

class PipelineRunner:
    def __init__(self, config: dict, credential, log_callback, done_callback):
        self.config = config
        self.credential = credential
        self.log_callback = log_callback
        self.done_callback = done_callback
        self._task = None
        self._loop = None
        self._running = False

    def start(self):
        self._running = True
        threading.Thread(target=self._run_loop, daemon=True).start()

    def stop(self):
        self._running = False
        if self._task and self._loop:
            self._loop.call_soon_threadsafe(self._task.cancel)

    def _run_loop(self):
        import asyncio
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._task = self._loop.create_task(self._pipeline())
        try:
            self._loop.run_until_complete(self._task)
        except (asyncio.CancelledError, Exception) as e:
            if self._running:
                self.log_callback(f"错误: {e}\n")
        finally:
            self._running = False
            self._loop.call_soon_threadsafe(self.done_callback)

    async def _pipeline(self):
        from src.bilibili.client import BilibiliClient
        from src.extractor.movie_extractor import MovieExtractor
        from src.nas.nastool_client import NASToolClient

        def log(msg):
            self._loop.call_soon_threadsafe(self.log_callback, msg)

        log("=== MovieBook 开始 ===\n")

        bili = BilibiliClient(credential=self.credential)
        extractor = MovieExtractor(
            tmdb_api_key=self.config.get("tmdb_api_key", ""),
            use_tmdb=self.config.get("use_tmdb", True),
        )
        nas = NASToolClient(
            base_url=self.config.get("nas_url", ""),
            api_key=self.config.get("nas_api_key", ""),
        )

        try:
            if self.config.get("nas_url"):
                log("检查 NAS Tool 连接...\n")
                try:
                    healthy = await nas.health_check()
                    log(f"NAS Tool: {'正常' if healthy else '无法连接'}\n")
                except Exception as e:
                    log(f"NAS Tool 检查失败: {e}\n")

            log("获取 B站关注列表...\n")
            followings = await bili.get_followings(pn=1, ps=50)
            if not followings:
                log("未获取到关注列表，请检查 Cookie。\n")
                return

            log(f"共 {len(followings)} 个关注:\n")
            for f in followings:
                log(f"  - {f.get('uname', '?')} (UID: {f.get('mid', '?')})\n")

            max_videos = int(self.config.get("max_videos", 20))
            fetch_comments = self.config.get("fetch_comments", True)
            fetch_danmaku = self.config.get("fetch_danmaku", True)
            max_comments = int(self.config.get("max_comments", 100))

            all_texts = []

            for following in followings:
                uid = following.get("mid", 0)
                uname = following.get("uname", "?")
                log(f"\n采集 {uname} 的视频...\n")
                videos = await bili.get_user_videos(uid, count=max_videos)
                log(f"  获取 {len(videos)} 个视频\n")

                for video in videos:
                    all_texts.append(video.get("title", ""))
                    desc = video.get("description", "")
                    if desc:
                        all_texts.append(desc)

                    bvid = video.get("bvid", "")
                    if not bvid:
                        continue

                    if fetch_comments:
                        log(f"  评论 {bvid}...\n")
                        comments = await bili.get_video_comments(bvid, count=max_comments)
                        all_texts.extend(comments)
                        log(f"    {len(comments)} 条\n")

                    if fetch_danmaku:
                        log(f"  弹幕 {bvid}...\n")
                        danmaku = await bili.get_video_danmaku(bvid)
                        all_texts.extend(danmaku)
                        log(f"    {len(danmaku)} 条\n")

            log(f"\n共收集 {len(all_texts)} 条文本\n")
            log("开始提取电影名...\n")

            movies = await extractor.extract_and_normalize(all_texts)

            log(f"\n提取到 {len(movies)} 个电影/电视剧:\n")
            for i, m in enumerate(movies, 1):
                tag = "电影" if m.get("media_type") == "movie" else "电视"
                log(f"  {i:2d}. [{tag}] {m['title']}\n")

            if not movies:
                log("未提取到电影名。\n")
                return

            if self.config.get("nas_url") and self.config.get("nas_api_key"):
                log(f"\n推送 {len(movies)} 个到 NAS Tool...\n")
                for m in movies:
                    tid = m.get("tmdb_id")
                    if tid:
                        ok = await nas.subscribe_media(
                            tmdb_id=tid,
                            media_type=m.get("media_type", "movie"),
                        )
                        if not ok:
                            await nas.add_to_watchlist(m["title"], m.get("media_type", "movie"))
                    else:
                        await nas.add_to_watchlist(m["title"], m.get("media_type", "movie"))
                log("推送完成。\n")
            else:
                log("\n未配置 NAS Tool API Key，跳过推送。\n")

            log("\n=== 运行完成 ===\n")

        finally:
            await bili.close()
            await extractor.close()
            await nas.close()


# ─────────────────────────── GUI 界面 ───────────────────────────

class MovieBookApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("MovieBook")
        self.root.geometry("920x660")
        self.root.minsize(780, 520)

        # 全局字体
        self.font = (FONT_FAMILY, FONT_SIZE)
        self.font_bold = (FONT_FAMILY, FONT_SIZE, "bold")
        self.font_mono = (FONT_MONO, 10)
        self.root.option_add("*Font", self.font)

        self._runner = None
        self._credential = None

        self._build_ui()
        self._load_config()

    def _build_ui(self):
        # ── 顶部: B站登录 ──
        login_frame = ttk.LabelFrame(self.root, text="B站登录", padding=8)
        login_frame.pack(fill=tk.X, padx=10, pady=(8, 4))

        ttk.Label(login_frame, text="Cookie:").pack(side=tk.LEFT)
        self._cookie_var = tk.StringVar()
        self._cookie_entry = ttk.Entry(login_frame, textvariable=self._cookie_var, width=65, show="•")
        self._cookie_entry.pack(side=tk.LEFT, padx=(6, 6), fill=tk.X, expand=True)

        self._login_btn = ttk.Button(login_frame, text="登录", command=self._on_login)
        self._login_btn.pack(side=tk.LEFT, padx=(0, 4))

        self._login_status = ttk.Label(login_frame, text="未登录", foreground="gray")
        self._login_status.pack(side=tk.LEFT, padx=4)

        # ── 中间: 左右分栏 ──
        middle = ttk.Frame(self.root)
        middle.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        # 左侧: 配置
        left = ttk.LabelFrame(middle, text="配置", padding=8)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 6))

        self._cfg_vars = {}
        self._build_field(left, "tmdb_api_key", "TMDB API Key:", 0, show="•")
        self._build_field(left, "nas_url", "NAS Tool 地址:", 1)
        self._build_field(left, "nas_api_key", "NAS API Key:", 2, show="•")

        # 复选框
        cb = ttk.Frame(left)
        cb.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(8, 0))
        self._fetch_comments_var = tk.BooleanVar(value=True)
        self._fetch_danmaku_var = tk.BooleanVar(value=True)
        self._use_tmdb_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(cb, text="采集评论", variable=self._fetch_comments_var).pack(anchor=tk.W)
        ttk.Checkbutton(cb, text="采集弹幕", variable=self._fetch_danmaku_var).pack(anchor=tk.W)
        ttk.Checkbutton(cb, text="TMDB 标准化", variable=self._use_tmdb_var).pack(anchor=tk.W)

        # 数值
        sf = ttk.Frame(left)
        sf.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(8, 0))
        ttk.Label(sf, text="每个UP主最多视频:").pack(side=tk.LEFT)
        self._max_videos_var = tk.StringVar(value="20")
        ttk.Spinbox(sf, from_=1, to=100, width=6, textvariable=self._max_videos_var).pack(side=tk.LEFT, padx=(4, 12))
        ttk.Label(sf, text="每视频最多评论:").pack(side=tk.LEFT)
        self._max_comments_var = tk.StringVar(value="100")
        ttk.Spinbox(sf, from_=10, to=500, width=6, textvariable=self._max_comments_var).pack(side=tk.LEFT, padx=4)

        # 右侧: 日志
        right = ttk.LabelFrame(middle, text="运行日志", padding=4)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._log = scrolledtext.ScrolledText(
            right, wrap=tk.WORD, state=tk.DISABLED,
            font=self.font_mono, background="#1e1e1e", foreground="#d4d4d4",
            insertbackground="#d4d4d4",
        )
        self._log.pack(fill=tk.BOTH, expand=True)

        # ── 底部按钮 ──
        bottom = ttk.Frame(self.root, padding=(10, 6))
        bottom.pack(fill=tk.X)

        self._run_btn = ttk.Button(bottom, text="开始运行", command=self._on_run)
        self._run_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        self._stop_btn = ttk.Button(bottom, text="停止", command=self._on_stop, state=tk.DISABLED)
        self._stop_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        ttk.Button(bottom, text="保存配置", command=self._on_save).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _build_field(self, parent, key, label, row, show=None):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=2)
        var = tk.StringVar()
        entry = ttk.Entry(parent, textvariable=var, width=40, show=show or "")
        entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(6, 0))
        self._cfg_vars[key] = var

    # ── 配置读写 ──

    def _load_config(self):
        cfg = load_config()
        self._cookie_var.set(cfg.get("bili_cookie", ""))
        for key, var in self._cfg_vars.items():
            var.set(str(cfg.get(key, "")))
        self._fetch_comments_var.set(cfg.get("fetch_comments", True))
        self._fetch_danmaku_var.set(cfg.get("fetch_danmaku", True))
        self._use_tmdb_var.set(cfg.get("use_tmdb", True))
        self._max_videos_var.set(str(cfg.get("max_videos", 20)))
        self._max_comments_var.set(str(cfg.get("max_comments", 100)))

    def _collect_config(self):
        cfg = {"bili_cookie": self._cookie_var.get().strip()}
        for key, var in self._cfg_vars.items():
            cfg[key] = var.get().strip()
        cfg["fetch_comments"] = self._fetch_comments_var.get()
        cfg["fetch_danmaku"] = self._fetch_danmaku_var.get()
        cfg["use_tmdb"] = self._use_tmdb_var.get()
        cfg["max_videos"] = int(self._max_videos_var.get() or 20)
        cfg["max_comments"] = int(self._max_comments_var.get() or 100)
        return cfg

    def _on_save(self):
        cfg = self._collect_config()
        save_config(cfg)
        self._append_log("配置已保存。\n")

    # ── 登录 ──

    def _on_login(self):
        cookie = self._cookie_var.get().strip()
        if not cookie:
            messagebox.showwarning("提示", "请先填写 B站 Cookie")
            return
        self._login_btn.config(state=tk.DISABLED)
        self._login_status.config(text="登录中...", foreground="blue")
        self._append_log("正在登录 B站...\n")
        LoginThread(cookie, self._append_log, self._on_login_done).start()

    def _on_login_done(self, credential):
        def _update():
            self._login_btn.config(state=tk.NORMAL)
            if credential:
                self._credential = credential
                self._login_status.config(text="已登录 ✓", foreground="green")
            else:
                self._login_status.config(text="登录失败", foreground="red")
        self.root.after(0, _update)

    # ── 运行 / 停止 ──

    def _on_run(self):
        if not self._credential:
            messagebox.showwarning("提示", "请先登录 B站")
            return
        cfg = self._collect_config()
        save_config(cfg)

        self._run_btn.config(state=tk.DISABLED)
        self._stop_btn.config(state=tk.NORMAL)
        self._login_btn.config(state=tk.DISABLED)
        self._log.config(state=tk.NORMAL)
        self._log.delete("1.0", tk.END)
        self._log.config(state=tk.DISABLED)

        self._runner = PipelineRunner(cfg, self._credential, self._append_log, self._on_done)
        self._runner.start()

    def _on_stop(self):
        if self._runner:
            self._runner.stop()
            self._append_log("\n--- 用户停止 ---\n")
        self._on_done()

    def _on_done(self):
        def _update():
            self._run_btn.config(state=tk.NORMAL)
            self._stop_btn.config(state=tk.DISABLED)
            self._login_btn.config(state=tk.NORMAL)
            self._runner = None
        self.root.after(0, _update)

    def _append_log(self, text):
        def _update():
            self._log.config(state=tk.NORMAL)
            self._log.insert(tk.END, text)
            self._log.see(tk.END)
            self._log.config(state=tk.DISABLED)
        self.root.after(0, _update)


def main():
    root = tk.Tk()
    MovieBookApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
