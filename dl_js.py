# -*- coding: utf-8 -*-
"""下载 y.qq.com 的 JS 包，供分析 sign 算法"""
import json
import os
import re
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "ref_js")
os.makedirs(OUT, exist_ok=True)

with open(os.path.join(BASE, "js_resources.json"), encoding="utf-8") as f:
    urls = json.load(f)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

for u in urls:
    if "y.qq.com/ryqq/js/" not in u:
        continue
    name = u.split("/")[-1].split("?")[0]
    fn = os.path.join(OUT, name)
    if os.path.exists(fn):
        print("skip", name)
        continue
    try:
        req = urllib.request.Request(u, headers={"User-Agent": UA, "Referer": "https://y.qq.com/"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        open(fn, "wb").write(data)
        print("saved", name, len(data), "bytes")
    except Exception as e:  # noqa: BLE001
        print("FAIL", name, e)
