import logging
from typing import Optional

import aiohttp

logger = logging.getLogger("moviebook.nas_tool")


class NASToolClient:
    def __init__(self, base_url: str, api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json",
        }
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self.headers)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def search_media(self, title: str, media_type: str = "movie") -> list[dict]:
        """在 NAS Tool 中搜索媒体"""
        session = await self._get_session()
        url = f"{self.base_url}/api/v1/media/search"
        params = {"title": title, "type": media_type}
        try:
            async with session.get(url, params=params) as resp:
                data = await resp.json()
                if data.get("code") == 200:
                    return data.get("data", [])
                logger.error(f"搜索失败: {data.get('message')}")
                return []
        except Exception as e:
            logger.error(f"搜索媒体失败 [{title}]: {e}")
            return []

    async def subscribe_media(self, tmdb_id: int, media_type: str = "movie", directory: str = "") -> bool:
        """订阅/收藏媒体到 NAS Tool"""
        session = await self._get_session()
        url = f"{self.base_url}/api/v1/subscribe"
        payload = {
            "tmdb_id": tmdb_id,
            "media_type": media_type,
            "directory": directory,
        }
        try:
            async with session.post(url, json=payload) as resp:
                data = await resp.json()
                if data.get("code") == 200:
                    logger.info(f"成功订阅 TMDB ID {tmdb_id}")
                    return True
                logger.error(f"订阅失败: {data.get('message')}")
                return False
        except Exception as e:
            logger.error(f"订阅媒体失败 [{tmdb_id}]: {e}")
            return False

    async def add_to_watchlist(self, title: str, media_type: str = "movie") -> bool:
        """添加到 NAS Tool 观看清单"""
        session = await self._get_session()
        url = f"{self.base_url}/api/v1/watchlist"
        payload = {
            "title": title,
            "media_type": media_type,
        }
        try:
            async with session.post(url, json=payload) as resp:
                data = await resp.json()
                if data.get("code") == 200:
                    logger.info(f"成功添加到观看清单: {title}")
                    return True
                logger.error(f"添加到观看清单失败: {data.get('message')}")
                return False
        except Exception as e:
            logger.error(f"添加到观看清单失败 [{title}]: {e}")
            return False

    async def health_check(self) -> bool:
        """检查 NAS Tool 是否可用"""
        session = await self._get_session()
        try:
            async with session.get(f"{self.base_url}/api/v1/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                return resp.status == 200
        except Exception:
            return False
