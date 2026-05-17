import time

import httpx

BILI_HEADERS = {
    "Referer": "https://www.bilibili.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

_url_cache: dict[str, tuple[str, float]] = {}
CACHE_TTL = 3600


async def get_video_info(bvid: str) -> dict:
    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    async with httpx.AsyncClient(headers=BILI_HEADERS, timeout=15.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") != 0:
            raise RuntimeError(f"Bilibili API error: {result.get('message', 'unknown')}")
        return result["data"]


async def get_play_url(bvid: str, cid: int, qn: int = 32) -> dict:
    url = f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&fnval=0&qn={qn}"
    async with httpx.AsyncClient(headers=BILI_HEADERS, timeout=15.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") != 0:
            raise RuntimeError(f"Bilibili playurl error: {result.get('message', 'unknown')}")
        return result["data"]


async def get_dash_play_url(bvid: str, cid: int, qn: int = 32) -> dict:
    url = f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&fnval=4048&qn={qn}&fourk=1"
    async with httpx.AsyncClient(headers=BILI_HEADERS, timeout=15.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") != 0:
            raise RuntimeError(f"Bilibili DASH API error: {result.get('message', 'unknown')}")
        return result["data"]


async def resolve_video_url(bvid: str, page: int, qn: int = 32) -> dict:
    cache_key = f"{bvid}:{page}"
    cached = _url_cache.get(cache_key)
    if cached:
        cached_url, cached_expires = cached
        if time.time() < cached_expires:
            return {"url": cached_url, "format": "mp4", "quality": 32, "expires_at": cached_expires}
    info = await get_video_info(bvid)
    pages = info.get("pages", [])
    if not pages or page < 1 or page > len(pages):
        raise ValueError(f"Invalid page {page} for bvid {bvid}, total pages: {len(pages)}")
    cid = pages[page - 1]["cid"]
    play_data = await get_play_url(bvid, cid, qn)
    durl = play_data.get("durl", [])
    if not durl:
        raise RuntimeError(f"No video URL returned for bvid={bvid}, cid={cid}")
    video_url = durl[0]["url"]
    expires_at = time.time() + CACHE_TTL
    _url_cache[cache_key] = (video_url, expires_at)
    return {"url": video_url, "format": "mp4", "quality": play_data.get("quality", qn), "expires_at": expires_at}
