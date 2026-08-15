# qqmusic-downloader

QQ 音乐网页版接口逆向研究项目：从线上 JS 实机提取 VMP 签名与 ag-1 加解密原语，实现搜索、登录、下载全链路。

> ⚠️ 仅供技术学习与个人收听，请勿用于商业用途或公开传播下载内容。QQ 音乐服务条款禁止未授权抓取，请控制请求频率。

## 背景

QQ 音乐网页版播放地址接口（2026-08 实测）：
- 端点：`u6.y.qq.com/cgi-bin/musics.fcg`（旧 `musicu.fcg` 已失效，返回 104009）
- 请求体：**ag-1 加密**（base64 文本）
- 请求签名：**VMP 虚拟机保护**的 SHA-1 派生算法（`zz` 开头），密钥内嵌于混淆字节码
- GitHub 上大多数旧教程（如 jsososo/QQMusicApi 的 sign.js）已失效

## 核心原理

`qq_crypto.js` 在 Node 中加载 y.qq.com 的 webpack bundle（配浏览器环境 shims），
在源码层面把 `delete ne._getSecuritySign` / `delete oe.__cgiEncrypt,delete oe.__cgiDecrypt`
替换为全局赋值，**在官方函数被销毁前截胡**，从而黑盒调用官方签名/加解密：

```
明文 JSON → node qq_crypto.js sign     → sign
明文 JSON → node qq_crypto.js encrypt  → 加密体（base64）
加密响应   → node qq_crypto.js decrypt → 明文 JSON
```

> `qq_crypto.js` 依赖 `ref_js/` 目录（y.qq.com 的 webpack chunks），该目录不含在仓库内，
> 请先运行 `python dl_js.py` 抓取。若未抓取，脚本会自动回退旧协议（免费歌曲通常仍可下载）。

## 用法

```bash
# 0. 环境：Python 3.10+（requests, playwright）、Node.js 18+
pip install requests playwright

# 1. 抓取 JS 素材（供 qq_crypto.js 提取加密原语；不抓也能用旧协议回退）
python dl_js.py

# 2. 下载免费歌曲（无需登录）
python download.py "雨天咖啡馆 纯正蛋炒饭"

# 3. 登录（弹出浏览器，手机 QQ 扫码；持久化配置，下次通常免登录）
python login_browser.py

# 4. 下载 VIP 歌曲（flac→320→128 自动降级；需要绿钻账号，普通账号会得到 104003）
python vip_download.py "晴天 周杰伦"
```

## 登录与权限说明

- **免费歌曲（payplay=0）无需登录**，匿名即可下载 128k
- `check_login()`（`qq_client_new.py`）：调用 `fcg_get_profile_homepage.fcg` 检测登录态
  （`code=0` 有效 / `code=1000` 已过期）；`vip_download.py` 会在 cookie 失效时自动拉起浏览器重新登录
- 错误码：`104009` = 签名/协议错误；`104003` = 无 VIP/音质权限（**服务端权限判决，客户端无法绕过**）；
  免费歌曲的 320k/无损音质同样需要绿钻

## 失效更新方法论

QQ 音乐反爬更新频繁。当请求返回 `104009` 或加解密往返失败时：
1. 浏览器抓包看新端点/新参数（Playwright 监听 `musics.fcg` 请求）
2. 重新 `python dl_js.py` 下载 JS，搜索 `musics.fcg` 定位请求包装器
3. 找到 `_getSecuritySign` / `__cgiEncrypt` / `__cgiDecrypt` 的提取现场，更新 `qq_crypto.js` 里的补丁字符串

## 文件结构

| 文件 | 作用 | 是否必需 |
|---|---|---|
| `qq_crypto.js` | 核心：加载线上 bundle，提取并暴露 sign/encrypt/decrypt 三个 CLI | 必需（新协议） |
| `qq_client_new.py` | 新版协议客户端（sign → encrypt → POST → decrypt），含登录态检测 | 必需 |
| `qqmusic_api.py` | 搜索（client_search_cp）与旧协议回退 | 必需 |
| `download.py` | 免费歌曲下载 CLI | 必需 |
| `vip_download.py` | VIP 歌曲下载（音质降级 + 自动重登） | 必需 |
| `login_browser.py` | Playwright 扫码登录（持久化配置） | VIP 下载时需要 |
| `dl_js.py` | 抓取 y.qq.com 的 JS 素材（`ref_js/`） | 新协议需要 |
| `README.md` / `LICENSE` / `.gitignore` | 文档与许可 | - |

## License

MIT
