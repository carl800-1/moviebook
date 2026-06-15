import asyncio
import logging
import re
from typing import Optional

import aiohttp

logger = logging.getLogger("moviebook.douyin")

BASE_URL = "https://www.douyin.com"


class DouyinClient:
    """抖音客户端 - 获取用户视频、评论数据"""

    def __init__(self, cookie: str = ""):
        self.cookie = cookie
        self._session: Optional[aiohttp.ClientSession] = None
        self._user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            headers = {
                "User-Agent": self._user_agent,
                "Referer": "https://www.douyin.com/",
                "Cookie": self.cookie,
                "Accept": "application/json, text/plain, */*",
            }
            self._session = aiohttp.ClientSession(headers=headers)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_user_videos(self, user_id: str, count: int = 20) -> list[dict]:
        """获取用户视频列表"""
        session = await self._get_session()
        url = f"{BASE_URL}/api/media/user/post/list"
        params = {
            "user_id": user_id,
            "max_cursor": 0,
            "count": count,
        }
        try:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    logger.error(f"获取用户 {user_id} 视频失败: HTTP {resp.status}")
                    return []
                data = await resp.json()
                videos = data.get("data", {}).get("list", [])
                result = []
                for video in videos:
                    item = video.get("item") or video
                    result.append({
                        "video_id": item.get("id"),
                        "title": item.get("desc", ""),
                        "description": item.get("desc", ""),
                        "create_time": item.get("create_time", 0),
                    })
                return result
        except Exception as e:
            logger.error(f"获取用户 {user_id} 视频失败: {e}")
            return []

    async def get_video_comments(self, video_id: str, count: int = 100) -> list[str]:
        """获取视频评论"""
        session = await self._get_session()
        url = f"{BASE_URL}/api/comment/list"
        params = {
            "video_id": video_id,
            "cursor": 0,
            "count": count,
        }
        try:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    logger.error(f"获取视频 {video_id} 评论失败: HTTP {resp.status}")
                    return []
                data = await resp.json()
                comments = []
                for item in data.get("data", {}).get("comments", []):
                    content = item.get("text", "")
                    if content:
                        comments.append(content)
                return comments
        except Exception as e:
            logger.error(f"获取视频 {video_id} 评论失败: {e}")
            return []

    async def search_users(self, keyword: str, count: int = 10) -> list[dict]:
        """搜索用户"""
        session = await self._get_session()
        url = f"{BASE_URL}/api/search/user"
        params = {
            "keyword": keyword,
            "count": count,
        }
        try:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                users = []
                for user in data.get("data", {}).get("user_list", []):
                    users.append({
                        "uid": user.get("uid"),
                        "nickname": user.get("nickname", ""),
                        "signature": user.get("signature", ""),
                    })
                return users
        except Exception as e:
            logger.error(f"搜索用户失败 [{keyword}]: {e}")
            return []

    async def get_video_info(self, video_url: str) -> dict:
        """解析视频URL获取视频信息"""
        session = await self._get_session()
        try:
            async with session.get(video_url) as resp:
                text = await resp.text()
                # 从HTML中提取视频信息
                match = re.search(r'"desc":"(.*?)"', text)
                title = match.group(1) if match else ""
                return {"title": title}
        except Exception as e:
            logger.error(f"解析视频URL失败 [{video_url}]: {e}")
            return {"title": ""}