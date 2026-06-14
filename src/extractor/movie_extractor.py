import logging
import re
from typing import Optional

import aiohttp

logger = logging.getLogger("moviebook.extractor")

# 常见电影/剧名指示词
MOVIE_PATTERNS = [
    # 中文电影名（书名号）
    r"《([^》]{2,30})》",
    # 英文电影名（斜体标记或纯大写单词组合）
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b",
]

# 过滤词：匹配到的内容如果包含这些，大概率不是电影名
FILTER_WORDS = [
    "电影", "影评", "解说", "推荐", "安利", "reaction", "Reaction",
    "好看", "烂片", "神作", "经典", "必看", "合集", "盘点",
    "UP主", "up主", "博主", "视频", "B站", "bilibili",
    "推荐", "分享", "记录", "日常", "vlog", "VLOG",
]

# 已知电影/剧名缓存（避免重复查询 TMDB）
_name_cache: dict[str, dict] = {}


class MovieExtractor:
    def __init__(self, tmdb_api_key: str = "", language: str = "zh-CN", use_tmdb: bool = True):
        self.tmdb_api_key = tmdb_api_key
        self.language = language
        self.use_tmdb = use_tmdb and bool(tmdb_api_key)
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    def extract_candidates(self, text: str) -> list[str]:
        """从文本中提取候选电影名"""
        candidates = []
        for pattern in MOVIE_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                name = match.strip()
                if self._is_valid_movie_name(name):
                    candidates.append(name)
        return list(set(candidates))

    def _is_valid_movie_name(self, name: str) -> bool:
        """判断是否为有效的电影名"""
        if len(name) < 2 or len(name) > 50:
            return False
        for word in FILTER_WORDS:
            if word.lower() in name.lower():
                return False
        # 过滤纯数字
        if name.isdigit():
            return False
        return True

    async def normalize_with_tmdb(self, name: str) -> Optional[dict]:
        """通过 TMDB API 标准化电影名"""
        if name in _name_cache:
            return _name_cache[name]

        if not self.use_tmdb:
            return {"title": name, "original_name": name, "media_type": "movie", "confidence": 0.5}

        session = await self._get_session()
        url = "https://api.themoviedb.org/3/search/multi"
        params = {
            "api_key": self.tmdb_api_key,
            "query": name,
            "language": self.language,
            "page": 1,
        }
        try:
            async with session.get(url, params=params) as resp:
                data = await resp.json()
                results = data.get("results", [])
                if not results:
                    _name_cache[name] = None
                    return None

                best = results[0]
                result = {
                    "title": best.get("title") or best.get("name", name),
                    "original_name": best.get("original_title") or best.get("original_name", ""),
                    "media_type": best.get("media_type", "movie"),  # movie or tv
                    "overview": best.get("overview", ""),
                    "poster_path": best.get("poster_path", ""),
                    "release_date": best.get("release_date") or best.get("first_air_date", ""),
                    "tmdb_id": best.get("id"),
                    "confidence": best.get("popularity", 0) / 100,
                }
                _name_cache[name] = result
                return result
        except Exception as e:
            logger.error(f"TMDB 查询失败 [{name}]: {e}")
            return None

    async def extract_and_normalize(self, texts: list[str]) -> list[dict]:
        """从多条文本中提取并标准化电影名"""
        all_candidates = []
        for text in texts:
            candidates = self.extract_candidates(text)
            all_candidates.extend(candidates)

        # 去重
        unique_candidates = list(set(all_candidates))
        logger.info(f"提取到 {len(unique_candidates)} 个候选电影名")

        results = []
        for name in unique_candidates:
            normalized = await self.normalize_with_tmdb(name)
            if normalized:
                results.append(normalized)
                logger.info(f"  ✅ {name} → {normalized['title']}")
            else:
                logger.debug(f"  ❌ {name} → 未找到匹配")

        return results
