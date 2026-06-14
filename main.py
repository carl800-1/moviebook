import asyncio
import logging
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.utils.config import load_config
from src.utils.logger import setup_logger
from src.bilibili.client import BilibiliClient
from src.extractor.movie_extractor import MovieExtractor
from src.nas.nastool_client import NASToolClient


async def run_pipeline():
    config = load_config()

    # 初始化日志
    log_cfg = config.get("logging", {})
    logger = setup_logger(
        level=log_cfg.get("level", "INFO"),
        log_file=log_cfg.get("file"),
    )

    logger.info("=" * 50)
    logger.info("MovieBook 启动")
    logger.info("=" * 50)

    # 初始化各模块
    bili_cfg = config.get("bilibili", {})
    extractor_cfg = config.get("extractor", {})
    nas_cfg = config.get("nas_tool", {})
    tmdb_cfg = config.get("tmdb", {})

    bili_client = BilibiliClient(cookie=bili_cfg.get("cookie", ""))
    extractor = MovieExtractor(
        tmdb_api_key=tmdb_cfg.get("api_key", ""),
        language=tmdb_cfg.get("language", "zh-CN"),
        use_tmdb=extractor_cfg.get("use_tmdb", True),
    )
    nas_client = NASToolClient(
        base_url=nas_cfg.get("base_url", ""),
        api_key=nas_cfg.get("api_key", ""),
    )

    try:
        # 检查 NAS Tool 连通性
        if nas_cfg.get("base_url"):
            healthy = await nas_client.health_check()
            logger.info(f"NAS Tool 连通性: {'✅ 正常' if healthy else '❌ 无法连接'}")

        # 遍历关注的 UP 主
        up_uids = bili_cfg.get("up_uids", [])
        max_videos = bili_cfg.get("max_videos_per_user", 20)
        fetch_comments = bili_cfg.get("fetch_comments", True)
        fetch_danmaku = bili_cfg.get("fetch_danmaku", True)
        max_comments = bili_cfg.get("max_comments_per_video", 100)

        all_texts = []  # 收集所有文本用于提取电影名

        for uid in up_uids:
            logger.info(f"正在采集 UP 主 {uid} 的视频...")
            videos = await bili_client.get_user_videos(uid, count=max_videos)
            logger.info(f"  获取到 {len(videos)} 个视频")

            for video in videos:
                # 收集视频标题和描述
                all_texts.append(video.get("title", ""))
                if video.get("description"):
                    all_texts.append(video.get("description", ""))

                # 采集评论
                if fetch_comments:
                    bvid = video.get("bvid", "")
                    if bvid:
                        logger.info(f"  采集视频 {bvid} 评论...")
                        comments = await bili_client.get_video_comments(bvid, count=max_comments)
                        all_texts.extend(comments)
                        logger.info(f"    获取到 {len(comments)} 条评论")

                # 采集弹幕
                if fetch_danmaku:
                    bvid = video.get("bvid", "")
                    if bvid:
                        logger.info(f"  采集视频 {bvid} 弹幕...")
                        danmaku = await bili_client.get_video_danmaku(bvid)
                        all_texts.extend(danmaku)
                        logger.info(f"    获取到 {len(danmaku)} 条弹幕")

        logger.info(f"总共收集到 {len(all_texts)} 条文本")

        # 提取电影名
        logger.info("开始提取电影名...")
        movies = await extractor.extract_and_normalize(all_texts)
        logger.info(f"提取到 {len(movies)} 个电影/电视剧")

        if not movies:
            logger.info("未提取到任何电影名，程序结束")
            return

        # 输出结果
        logger.info("\n提取结果:")
        logger.info("-" * 40)
        for movie in movies:
            media_type = "🎬" if movie.get("media_type") == "movie" else "📺"
            logger.info(f"  {media_type} {movie['title']} (置信度: {movie.get('confidence', 0):.2f})")

        # 推送到 NAS Tool
        if nas_cfg.get("base_url") and nas_cfg.get("api_key"):
            logger.info("\n推送到 NAS Tool...")
            default_dir = nas_cfg.get("default_directory", "")
            for movie in movies:
                tmdb_id = movie.get("tmdb_id")
                if tmdb_id:
                    success = await nas_client.subscribe_media(
                        tmdb_id=tmdb_id,
                        media_type=movie.get("media_type", "movie"),
                        directory=default_dir,
                    )
                    if not success:
                        # 降级：添加到观看清单
                        await nas_client.add_to_watchlist(
                            title=movie["title"],
                            media_type=movie.get("media_type", "movie"),
                        )
                else:
                    # 没有 TMDB ID，尝试搜索
                    await nas_client.add_to_watchlist(
                        title=movie["title"],
                        media_type=movie.get("media_type", "movie"),
                    )
        else:
            logger.info("\n未配置 NAS Tool，跳过推送")
            logger.info("提取的电影列表:")
            for movie in movies:
                logger.info(f"  - {movie['title']}")

    finally:
        await bili_client.close()
        await extractor.close()
        await nas_client.close()


def main():
    try:
        asyncio.run(run_pipeline())
    except KeyboardInterrupt:
        print("\n程序已中断")
    except FileNotFoundError as e:
        print(f"\n❌ {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
