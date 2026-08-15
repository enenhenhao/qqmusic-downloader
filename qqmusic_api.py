# -*- coding: utf-8 -*-
"""
QQ 音乐 API 封装（2026-08 实测可用）
- 搜索：c.y.qq.com/soso/fcgi-bin/client_search_cp（免 sign）
- 播放地址：u.y.qq.com/cgi-bin/musicu.fcg vkey.GetVkeyServer（免 sign，VIP 需登录 Cookie）
- 下载：dl.stream.qqmusic.qq.com / isure.stream.qqmusic.qq.com + purl
仅供个人学习与收听，请勿传播或商用。
"""
import hashlib
import json
import random
import re
import time
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
REFERER = "https://y.qq.com/"

# 音质 → vkey 请求中的 filename 前缀（VIP 登录后可用）
QUALITY = {
    "m4a": ("C400", "m4a"),   # m4a 128kbps（免费）
    "128": ("M500", "mp3"),   # mp3 128kbps（免费）
    "320": ("M800", "mp3"),   # mp3 320kbps（VIP）
    "flac": ("F000", "flac"),  # flac 无损（绿钻）
}


def _http_get(url: str, cookie: str = "", timeout: int = 25) -> bytes:
    headers = {"User-Agent": UA, "Referer": REFERER, "Accept": "*/*"}
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _http_get_text(url: str, cookie: str = "") -> str:
    return _http_get(url, cookie).decode("utf-8", "replace")


def make_sign(data: dict, key: str = "0b50b02fd1d7a9a15c2cc0a78e8f5c5f2d3e6f9a") -> str:
    """musicu.fcg 的 sign 参数（当前接口实测无需 sign，保留以备失效时启用）"""
    s = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha1((s.encode("utf-8").hex() + key).encode("utf-8")).hexdigest()


def gen_guid() -> str:
    return "".join(random.choice("0123456789abcdef") for _ in range(32))


def search(keyword: str, num: int = 10) -> list:
    """搜索歌曲，返回 [{songmid, songname, singer, album, interval, payplay}]"""
    url = ("https://c.y.qq.com/soso/fcgi-bin/client_search_cp?w="
           + urllib.parse.quote(keyword)
           + f"&format=json&p=1&n={num}&cr=1&g_tk=5381&loginUin=0&hostUin=0"
             "&inCharset=utf8&outCharset=utf-8&notice=0&platform=yqq.json&needNewCode=0")
    r = json.loads(_http_get_text(url))
    if r.get("code") != 0:
        raise RuntimeError(f"search code={r.get('code')}")
    out = []
    for s in (r.get("data", {}).get("song", {}).get("list") or []):
        out.append({
            "songmid": s.get("songmid"),
            "songname": s.get("songname"),
            "singer": ",".join(x.get("name", "") for x in s.get("singer", [])),
            "album": (s.get("album") or {}).get("name", ""),
            "interval": s.get("interval"),
            "payplay": (s.get("pay") or {}).get("payplay", 0),
        })
    return out


def get_play_url(songmid: str, guid: str, quality: str = "m4a",
                 uin: str = "0", cookie: str = "") -> str:
    """获取播放地址（jsososo 格式：comm.authst=qqmusic_key，免 sign）。
    quality: m4a/128/320/flac。VIP 歌曲需登录 cookie + 对应 uin。"""
    prefix, ext = QUALITY.get(quality, QUALITY["m4a"])
    filename = f"{prefix}{songmid}.{ext}"

    # 从 cookie 中提取 qqmusic_key，注入 comm.authst
    authst = ""
    if cookie:
        m = re.search(r"(?:^|;)\s*qqmusic_key=([^;]+)", cookie)
        authst = m.group(1) if m else ""

    param = {
        "filename": [filename],
        "guid": guid, "songmid": [songmid], "songtype": [0],
        "uin": uin, "loginflag": 1, "platform": "20",
    }
    data = {
        "req_0": {"module": "vkey.GetVkeyServer", "method": "CgiGetVkey", "param": param},
        "comm": {"uin": int(uin) if uin.isdigit() else 0, "format": "json",
                 "ct": 19, "cv": 0, "authst": authst},
    }
    query = {
        "-": "getplaysongvkey", "g_tk": 5381, "loginUin": uin, "hostUin": 0,
        "format": "json", "inCharset": "utf8", "outCharset": "utf-8", "notice": 0,
        "platform": "yqq.json", "needNewCode": 0,
        "data": json.dumps(data, ensure_ascii=False, separators=(",", ":")),
    }
    url = "https://u.y.qq.com/cgi-bin/musicu.fcg?" + urllib.parse.urlencode(query)
    r = json.loads(_http_get_text(url, cookie))
    req0 = r.get("req_0", {})
    if req0.get("code") != 0:
        raise RuntimeError(f"vkey code={req0.get('code')} msg={req0.get('msg')}")
    mid_info = (req0.get("data") or {}).get("midurlinfo") or []
    purl = mid_info[0].get("purl", "") if mid_info else ""
    return purl


def download(url: str, path: str, cookie: str = "", retries: int = 3) -> int:
    """流式下载到 path，返回字节数。失败自动重试。"""
    headers = {"User-Agent": UA, "Referer": REFERER, "Accept": "*/*"}
    if cookie:
        headers["Cookie"] = cookie
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp, open(path, "wb") as f:
                total = 0
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    total += len(chunk)
            if total > 0:
                return total
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"download failed: {last}")


def build_candidates(purl: str) -> list:
    """按经验优先级生成候选下载 URL"""
    if not purl:
        return []
    return [
        "https://dl.stream.qqmusic.qq.com/" + purl,
        "https://isure.stream.qqmusic.qq.com/" + purl,
        "http://aqqmusic.tc.qq.com/" + purl,
    ]
