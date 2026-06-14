"""
Demo script - test the full pipeline with mock data (no real Bilibili API calls).
Run: python3 demo.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.extractor.movie_extractor import MovieExtractor
from src.nas.nastool_client import NASToolClient


async def main():
    print("=== MovieBook Demo ===\n")

    # Simulated Bilibili texts (titles + comments + danmaku)
    sample_texts = [
        "今天看了《奥本海默》太炸了，诺兰yyds",
        "推荐《流浪地球2》和《满江红》，今年最佳",
        "《沙丘2》的视觉效果真的绝了",
        "刚看完《Dune: Part Two》，Hans Zimmer 配乐太神",
        "有没有人觉得《流浪地球2》比第一部更好看",
        "《奥本海默》值得二刷，细节太多了",
        "今年最期待的电影《Barbie》",
        "《封神第一部》特效不错啊，乌尔善这次行",
        "刚看完《The Dark Knight》重映，经典永不过时",
        "《星际穿越》十周年重映必须去",
        "《年会不能停！》这个喜剧片不错",
        "强烈推荐《周处除三害》，阮经天演技炸裂",
        "今日观影《功夫熊猫4》，一般般",
        "《你想活出什么名字》是宫崎骏最后一部吗",
        "《异形：夺命舰》好恐怖，R级果然不一样",
        "电视剧推荐《繁花》王家卫拍电视剧了",
        "《漫长的季节》今年最佳国产剧没有之一",
        "《狂飙》张颂文演技太好了",
    ]

    # 1. Extract movie names
    print("[1/3] Extracting movie names from sample texts...\n")
    extractor = MovieExtractor(use_tmdb=False)
    movies = await extractor.extract_and_normalize(sample_texts)
    await extractor.close()

    print(f"\nFound {len(movies)} movie/TV titles:\n")
    for i, movie in enumerate(movies, 1):
        icon = "[MOVIE]" if movie.get("media_type") == "movie" else "[TV]   "
        print(f"  {i:2d}. {icon} {movie['title']}")

    # 2. Show what would be sent to NAS Tool
    print(f"\n[2/3] Would send {len(movies)} titles to NAS Tool:\n")
    for movie in movies:
        print(f"  -> {movie['title']} (type={movie['media_type']})")

    # 3. Test NAS Tool client (will fail gracefully if not configured)
    print("\n[3/3] NAS Tool connection test...")
    nas = NASToolClient(base_url="", api_key="")
    healthy = await nas.health_check()
    print(f"  NAS Tool configured: {bool(nas.base_url)}")
    print(f"  NAS Tool reachable: {healthy}")
    await nas.close()

    print("\n=== Demo Complete ===")
    print("\nTo use with real data:")
    print("  1. Copy config/config.example.yaml -> config/config.yaml")
    print("  2. Add your Bilibili cookie, TMDB API key, NAS Tool URL")
    print("  3. Run: python3 main.py")


if __name__ == "__main__":
    asyncio.run(main())
