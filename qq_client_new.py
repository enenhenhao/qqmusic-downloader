# -*- coding: utf-8 -*-
"""QQ 音乐新版加密协议客户端（u6.y.qq.com/cgi-bin/musics.fcg + ag-1 + sign）
Node 负责 sign/encrypt/decrypt（qq_crypto.js），Python 负责 HTTP
"""
import base64
import json
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request

import qqmusic_api as api

BASE = os.path.dirname(os.path.abspath(__file__))
NODE = r"C:\Program Files\nodejs\node.exe"
CRYPTO = os.path.join(BASE, "qq_crypto.js")


def _node(op: str, payload: str) -> str:
    proc = subprocess.run(
        [NODE, CRYPTO, op], input=payload,
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"node {op} failed: {proc.stderr[:300]}")
    return proc.stdout.strip()


def node_sign(data_json: str) -> str:
    return _node("sign", data_json)


def node_encrypt(data_json: str) -> str:
    """返回加密后的 base64 body"""
    return _node("encrypt", data_json)


def node_decrypt(body_b64: str) -> str:
    return _node("decrypt", body_b64)


def call(data: dict, cookie: str = "") -> dict:
    """走新协议调用 musics.fcg，返回解密后的 JSON"""
    data_json = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    sign = node_sign(data_json)
    body = node_encrypt(data_json)
    url = ("https://u6.y.qq.com/cgi-bin/musics.fcg?_=" + str(int(time.time() * 1000))
           + "&encoding=ag-1&sign=" + urllib.parse.quote(sign))
    headers = {
        "User-Agent": api.UA,
        "Referer": "https://y.qq.com/",
        "Accept": "application/octet-stream",
        "Content-Type": "text/plain",
        "Origin": "https://y.qq.com",
    }
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(url, data=body.encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        resp_bytes = r.read()
    text = node_decrypt(base64.b64encode(resp_bytes).decode())
    return json.loads(text)


def clean_cookie(s: str) -> str:
    """去掉 BOM 与首尾空白（Windows 记事本/PowerShell 保存 UTF-8 会带 BOM）"""
    return (s or "").lstrip("\ufeff").strip()


def check_login(cookie: str = "") -> dict:
    """检查登录态：code=0 且带用户数据 = 已登录；code=1000 = 未登录/过期"""
    cookie = clean_cookie(cookie)
    uin = ""
    m = re.search(r"(?:^|;)\s*uin=(\d+)", cookie or "")
    uin = m.group(1) if m else ""
    url = (f"https://c.y.qq.com/rsc/fcgi-bin/fcg_get_profile_homepage.fcg"
           f"?cid=205360838&userid={uin}&reqfrom=1")
    headers = {"User-Agent": api.UA, "Referer": api.REFERER}
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        j = json.loads(r.read().decode("utf-8", "replace"))
    d = j.get("data") or {}
    nick = ""
    if isinstance(d, dict):
        creator = d.get("creator") or {}
        nick = creator.get("nick", "") or ""
    return {"valid": j.get("code") == 0 and bool(d),
            "code": j.get("code"), "uin": uin, "nick": nick}


def search_new(keyword: str, num: int = 10) -> list:
    data = {
        "comm": {"uin": 0, "format": "json", "ct": 24, "cv": 0},
        "req_0": {"module": "music.search.SearchCgiService",
                  "method": "DoSearchForQQMusicDesktop",
                  "param": {"query": keyword, "num_per_page": num, "page_num": 1, "search_type": 0}},
    }
    r = call(data)
    req0 = r.get("req_0", {})
    body = (req0.get("data") or {}).get("body", {})
    return ((body.get("song") or {}).get("list")) or []


def vkey_new(songmid: str, quality: str, uin: str = "0", cookie: str = "") -> str:
    cookie = clean_cookie(cookie)
    prefix, ext = api.QUALITY.get(quality, api.QUALITY["m4a"])
    filename = f"{prefix}{songmid}.{ext}"
    authst = ""
    if cookie:
        m = re.search(r"(?:^|;)\s*qqmusic_key=([^;]+)", cookie)
        authst = m.group(1) if m else ""
    data = {
        "req_0": {"module": "vkey.GetVkeyServer", "method": "CgiGetVkey",
                  "param": {"filename": [filename], "guid": api.gen_guid(),
                            "songmid": [songmid], "songtype": [0], "uin": uin,
                            "loginflag": 1, "platform": "20"}},
        "comm": {"uin": int(uin) if uin.isdigit() else 0, "format": "json",
                 "ct": 19, "cv": 0, "authst": authst},
    }
    r = call(data, cookie)
    req0 = r.get("req_0", {})
    if req0.get("code") not in (0, None):
        return "", f"req0.code={req0.get('code')}"
    d0 = req0.get("data") or {}
    mi = (d0.get("midurlinfo") or [{}])[0]
    return mi.get("purl", ""), f"uin={d0.get('uin','')} result={mi.get('result')}"


if __name__ == "__main__":
    import sys
    # 测试：新协议搜索 + 免费歌 vkey
    print("== 新协议搜索《雨天咖啡馆》 ==", flush=True)
    songs = search_new("雨天咖啡馆 纯正蛋炒饭", 5)
    for s in songs[:3]:
        print("  ", s.get("songmid"), s.get("songname"), ",".join(x.get("name", "") for x in s.get("singer", [])), flush=True)
    if songs:
        mid = songs[0]["songmid"]
        print("== vkey 免费歌 ==", flush=True)
        purl, info = vkey_new(mid, "m4a")
        print("purl_len:", len(purl), "|", info, flush=True)
        if purl:
            print("PURL:", purl[:120], flush=True)
