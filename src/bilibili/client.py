import asyncio
import logging
from typing import Optional

import aiohttp

logger = logging.getLogger("moviebook.bilibili")

BASE_URL = "https://api.bilibili.com"


class BilibiliClient:
    """Bilibili client using raw HTTP + cookies (no external SDK needed)."""

    def __init__(self, credential: Optional[object] = None):
        """
        Args:
            credential: bilibili_api.Credential instance or None.
                       If provided, cookies are extracted from it.
        """
        self.credential = credential
        self._session: Optional[aiohttp.ClientSession] = None

    def _get_cookies(self) -> dict:
        """Extract cookies from credential."""
        if self.credential is None:
            return {}
        if hasattr(self.credential, "get_cookies"):
            return self.credential.get_cookies()
        if hasattr(self.credential, "get_buvid_cookies"):
            return self.credential.get_buvid_cookies()
        return {}

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            cookies = self._get_cookies()
            cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Referer": "https://www.bilibili.com",
                "Cookie": cookie_str,
            }
            self._session = aiohttp.ClientSession(headers=headers, cookies=cookies)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_followings(self, pn: int = 1, ps: int = 50) -> list[dict]:
        """Get current user's followings (UP主列表)."""
        session = await self._get_session()
        url = f"{BASE_URL}/x/relation/followings"
        params = {"vmid": await self._get_self_uid(), "pn": pn, "ps": ps}
        async with session.get(url, params=params) as resp:
            data = await resp.json()
            if data.get("code") != 0:
                logger.error(f"获取关注列表失败: {data.get('message')}")
                return []
            return data.get("data", {}).get("list", [])

    async def _get_self_uid(self) -> int:
        """Get current user's UID."""
        session = await self._get_session()
        url = f"{BASE_URL}/x/web-interface/nav"
        async with session.get(url) as resp:
            data = await resp.json()
            if data.get("code") == 0:
                return data.get("data", {}).get("mid", 0)
        return 0

    async def get_user_videos(self, uid: int, count: int = 20) -> list[dict]:
        """Get UP主's video list."""
        session = await self._get_session()
        url = f"{BASE_URL}/x/space/wbi/arc/search"
        params = {"mid": uid, "ps": count, "pn": 1, "order": "pubdate"}
        async with session.get(url, params=params) as resp:
            data = await resp.json()
            if data.get("code") != 0:
                logger.error(f"获取 UP 主 {uid} 视频失败: {data.get('message')}")
                return []
            videos = data.get("data", {}).get("list", {}).get("vlist", [])
            return [
                {
                    "bvid": v.get("bvid"),
                    "title": v.get("title", ""),
                    "description": v.get("description", ""),
                    "aid": v.get("aid"),
                    "length": v.get("length", 0),
                }
                for v in videos
            ]

    async def get_video_comments(self, bvid: str, count: int = 100) -> list[str]:
        """Get video comments."""
        session = await self._get_session()
        url = f"{BASE_URL}/x/v2/reply"
        params = {"bvid": bvid, "pn": 1, "ps": count, "type": 1, "sort": 2}
        async with session.get(url, params=params) as resp:
            data = await resp.json()
            if data.get("code") != 0:
                logger.error(f"获取视频 {bvid} 评论失败: {data.get('message')}")
                return []
            replies = data.get("data", {}).get("replies", [])
            comments = []
            for reply in replies:
                content = reply.get("content", {}).get("message", "")
                if content:
                    comments.append(content)
                for sub in reply.get("replies", []) or []:
                    sub_content = sub.get("content", {}).get("message", "")
                    if sub_content:
                        comments.append(sub_content)
            return comments

    async def get_video_danmaku(self, bvid: str) -> list[str]:
        """Get video danmaku."""
        session = await self._get_session()
        url = f"{BASE_URL}/x/web-interface/view"
        params = {"bvid": bvid}
        async with session.get(url, params=params) as resp:
            data = await resp.json()
            if data.get("code") != 0:
                logger.error(f"获取视频 {bvid} 信息失败: {data.get('message')}")
                return []
            cid = data.get("data", {}).get("cid")
        if not cid:
            return []

        danmaku_url = f"{BASE_URL}/x/v2/dm/list.so"
        params = {"oid": cid, "type": 1, "oid": cid}
        async with session.get(danmaku_url, params=params) as resp:
            text = await resp.text()
            import re
            danmaku_list = re.findall(r'">(.*?)</d>', text)
            return danmaku_list
