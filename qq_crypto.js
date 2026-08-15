// QQ音乐加密原语提取器：加载 webpack bundle，捕获 sign/encrypt/decrypt 函数
const fs = require('fs');
const path = require('path');

const DIR = __dirname;
const JS = path.join(DIR, 'ref_js');

// ---------- 浏览器环境 shims ----------
const noop = () => {};
const mkEl = () => ({ style: {}, setAttribute: noop, appendChild: noop, addEventListener: noop,
  removeEventListener: noop, getContext: () => null, focus: noop, click: noop,
  set src(v) {}, get src() { return ''; }, set href(v) {}, get href() { return ''; },
  set textContent(v) {}, get textContent() { return ''; }, classList: { add: noop, remove: noop, contains: () => false },
  dataset: {}, attributes: {}, childNodes: [], children: [] });

global.window = global;
global.self = global;
global.navigator = {
  userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  platform: 'Win32', language: 'zh-CN', languages: ['zh-CN', 'zh'], onLine: true,
  vendor: 'Google Inc.', appVersion: '5.0 (Windows NT 10.0; Win64; x64)', cookieEnabled: true,
  maxTouchPoints: 0, hardwareConcurrency: 8, deviceMemory: 8,
};
global.location = {
  href: 'https://y.qq.com/', protocol: 'https:', host: 'y.qq.com', hostname: 'y.qq.com',
  port: '', pathname: '/', search: '', hash: '', origin: 'https://y.qq.com',
  assign: noop, replace: noop, reload: noop,
};
const storage = (() => { let m = {}; return { getItem: k => (k in m ? m[k] : null), setItem: (k, v) => { m[k] = String(v); }, removeItem: k => { delete m[k]; }, clear: () => { m = {}; }, key: i => Object.keys(m)[i] || null, get length() { return Object.keys(m).length; } }; })();
global.localStorage = storage;
global.sessionStorage = storage;
global.document = {
  documentElement: { style: {} },
  body: mkEl(), head: mkEl(), createElement: mkEl, createElementNS: () => mkEl(),
  createTextNode: () => ({}), createDocumentFragment: () => mkEl(),
  getElementById: () => null, getElementsByTagName: () => [], getElementsByClassName: () => [],
  querySelector: () => null, querySelectorAll: () => [],
  addEventListener: noop, removeEventListener: noop, createEvent: () => ({ initEvent: noop }),
  addEventListener: noop,
  cookie: '', readyState: 'complete', title: '', URL: 'https://y.qq.com/',
  hidden: false, visibilityState: 'visible', documentURI: 'https://y.qq.com/',
  implementation: { createHTMLDocument: () => ({ body: mkEl(), createElement: mkEl }) },
  execCommand: noop, exitFullscreen: noop, hasFocus: () => true,
};
global.window.matchMedia = () => ({ matches: false, addListener: noop, removeListener: noop, addEventListener: noop, removeEventListener: noop, media: '' });
global.window.addEventListener = noop;
global.window.removeEventListener = noop;
global.window.requestAnimationFrame = (cb) => setTimeout(cb, 16);
global.window.cancelAnimationFrame = (id) => clearTimeout(id);
global.window.devicePixelRatio = 1;
global.window.screen = { width: 1920, height: 1080, availWidth: 1920, availHeight: 1040, colorDepth: 24, orientation: { type: 'landscape-primary' } };
global.window.innerWidth = 1920; global.window.innerHeight = 937;
global.window.outerWidth = 1920; global.window.outerHeight = 1040;
global.window.pageXOffset = 0; global.window.pageYOffset = 0;
global.window.screenX = 0; global.window.screenY = 0;
global.window.getComputedStyle = () => ({});
global.window.CSS = { supports: () => false, escape: (s) => s };
global.window.history = { length: 1, state: null, pushState: noop, replaceState: noop, back: noop, go: noop };
global.window.open = () => null;
global.window.postMessage = noop;
global.window.close = noop;
global.window.focus = noop;
global.window.blur = noop;
global.window.scrollTo = noop;
global.window.scroll = noop;
global.window.stop = noop;
global.window.print = noop;
global.window.alert = noop;
global.window.confirm = () => true;
global.window.prompt = () => null;
global.window.Image = function () { return mkEl(); };
global.window.Audio = function () { return mkEl(); };
global.window.Node = { ELEMENT_NODE: 1, TEXT_NODE: 3 };
global.window.HTMLElement = function () {}; global.window.Element = function () {};
global.window.Event = function () {}; global.window.CustomEvent = function () {};
global.window.MutationObserver = function () { return { observe: noop, disconnect: noop, takeRecords: () => [] }; };
global.window.IntersectionObserver = function () { return { observe: noop, disconnect: noop, unobserve: noop, takeRecords: () => [] }; };
global.window.ResizeObserver = function () { return { observe: noop, disconnect: noop, unobserve: noop }; };
global.window.PerformanceObserver = function () { return { observe: noop, disconnect: noop }; };
global.window.XMLHttpRequest = function () {
  this.open = noop; this.send = noop; this.setRequestHeader = noop;
  this.overrideMimeType = noop; this.abort = noop; this.getAllResponseHeaders = () => '';
  this.getResponseHeader = () => null; this.readyState = 4; this.status = 200; this.response = '';
  this.responseText = ''; this.responseType = ''; this.withCredentials = false;
  this.upload = {}; this.onreadystatechange = null;
};
global.window.reportCgi = { reportSend: noop };
global.window.__webpack_public_path__ = 'https://y.qq.com/ryqq/js/';
global.performance = global.performance || require('perf_hooks').performance;
global.crypto = global.crypto || require('crypto').webcrypto;
global.TextEncoder = global.TextEncoder || require('util').TextEncoder;
global.TextDecoder = global.TextDecoder || require('util').TextDecoder;

// ---------- 加载 chunks ----------
const runtimeFile = fs.readdirSync(JS).find(f => f.startsWith('runtime~'));
if (!runtimeFile) throw new Error('runtime chunk not found');
eval(fs.readFileSync(path.join(JS, runtimeFile), 'utf8'));

for (const f of fs.readdirSync(JS)) {
  if (f.startsWith('runtime~') || !f.endsWith('.js')) continue;
  let src = fs.readFileSync(path.join(JS, f), 'utf8');
  src = src.split('delete ne._getSecuritySign').join('global.__qqSignFn=ne._getSecuritySign');
  src = src.split('delete oe.__cgiEncrypt,delete oe.__cgiDecrypt').join('global.__qqEnc=oe.__cgiEncrypt,global.__qqDec=oe.__cgiDecrypt');
  try {
    eval(src);
    console.error('chunk ok:', f);
  } catch (e) {
    console.error('chunk eval error:', f, e.message);
  }
}
console.error('captured: signFn=' + !!global.__qqSignFn + ' enc=' + !!global.__qqEnc + ' dec=' + !!global.__qqDec);

// ---------- 操作分发 ----------
const op = process.argv[2];
const input = fs.readFileSync(0, 'utf-8').trim();

(async () => {
  if (op === 'sign') {
    console.log(global.__qqSignFn(input));
  } else if (op === 'encrypt') {
    const out = await global.__qqEnc(input);
    // 加密函数返回 base64 字符串（POST body 即此文本）
    if (typeof out === 'string') { console.log(out.trim()); }
    else if (out instanceof ArrayBuffer) { console.log(Buffer.from(out).toString('base64')); }
    else if (ArrayBuffer.isView(out)) { console.log(Buffer.from(out.buffer, out.byteOffset, out.byteLength).toString('base64')); }
    else { console.log(JSON.stringify(out)); }
  } else if (op === 'decrypt') {
    let out;
    const attempts = [input.trim(), Buffer.from(input.trim(), 'base64'), Buffer.from(input.trim(), 'base64').buffer];
    for (const a of attempts) {
      try {
        out = await global.__qqDec(a);
        console.error('decrypt attempt type:', Object.prototype.toString.call(out), 'len:', (out && (out.length ?? out.byteLength)) ?? '?');
        if (out && (out.length || out.byteLength)) break;
      } catch (e) {
        console.error('decrypt attempt err:', e.message);
      }
    }
    if (typeof out === 'string') { console.log(out); }
    else if (out instanceof ArrayBuffer) { console.log(Buffer.from(out).toString('utf8')); }
    else if (ArrayBuffer.isView(out)) { console.log(Buffer.from(out.buffer, out.byteOffset, out.byteLength).toString('utf8')); }
    else { console.log(JSON.stringify(out)); }
  } else {
    console.error('unknown op'); process.exit(2);
  }
})().catch(e => { console.error('op error:', e); process.exit(1); });
