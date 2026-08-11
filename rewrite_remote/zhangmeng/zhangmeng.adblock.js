/*
 * 掌盟去广告 - Quantumult X response script
 *
 * 用法：
 * 1. 先用 QuanX MitM 抓包，确认广告接口 URL。
 * 2. 将 URL 特征补到 zhangmeng.conf 的 rewrite 正则。
 * 3. 如果接口字段特殊，在 HANDLERS 里给该 URL 加定制清理逻辑。
 */

const AD_KEY_RE = /(^|_)(ad|ads|advert|advertise|advertisement|splash|startup|launch|popup|pop|poplayer|banner|promotion|promote|market|marketing|material|commercial|feed_ad|recommend_ad)(_|$)/i;
const AD_VALUE_RE = /(广告|推广|开屏|弹窗|浮层|splash|advert|adid|gdt|ams_ad)/i;
const KEEP_KEY_RE = /^(address|admin|advance|advantage|adapter|add|added|addition|additional|adcode)$/i;

const url = $request && $request.url ? $request.url : "";
let body = $response && typeof $response.body === "string" ? $response.body : "";

const HANDLERS = [
  {
    test: /\/go\/recommend\/(?:platflashbox|floatbox|platbanner|platstrongshell)(?:\?|$)/i,
    run: emptyRecommend,
  },
  {
    test: /\/go\/zone\/(?:bottomtab_tip|newgamereminder)(?:\?|$)/i,
    run: emptyZoneTip,
  },
  {
    test: /\/go\/content_svr\/feeds\/activity(?:\?|$)/i,
    run: emptyFeeds,
  },
  {
    test: /(?:ad|ads|advert|splash|startup|launch|popup|poplayer|banner|promotion|material|market)/i,
    run: cleanGenericJson,
  },
];

function isPlainObject(value) {
  return Object.prototype.toString.call(value) === "[object Object]";
}

function isAdKey(key) {
  return AD_KEY_RE.test(key) && !KEEP_KEY_RE.test(key);
}

function looksLikeAdObject(obj) {
  if (!isPlainObject(obj)) return false;

  const keys = Object.keys(obj);
  if (keys.some(isAdKey)) return true;

  const joined = keys
    .map((key) => {
      const value = obj[key];
      if (typeof value === "string" || typeof value === "number") {
        return `${key}:${value}`;
      }
      return key;
    })
    .join("|");

  return AD_VALUE_RE.test(joined);
}

function emptyFor(value) {
  if (Array.isArray(value)) return [];
  if (isPlainObject(value)) return {};
  if (typeof value === "boolean") return false;
  if (typeof value === "number") return 0;
  if (typeof value === "string") return "";
  return null;
}

function walk(value, parentKey = "") {
  if (Array.isArray(value)) {
    return value
      .filter((item) => !looksLikeAdObject(item))
      .map((item) => walk(item, parentKey));
  }

  if (!isPlainObject(value)) return value;

  const next = {};
  Object.keys(value).forEach((key) => {
    const item = value[key];

    if (isAdKey(key)) {
      next[key] = emptyFor(item);
      return;
    }

    if (Array.isArray(item) && isAdKey(parentKey || key)) {
      next[key] = [];
      return;
    }

    next[key] = walk(item, key);
  });

  return next;
}

function normalizeCommonEnvelope(data) {
  if (!isPlainObject(data)) return data;

  ["data", "result", "results", "list", "items"].forEach((key) => {
    if (Array.isArray(data[key])) {
      data[key] = data[key].filter((item) => !looksLikeAdObject(item));
    }
  });

  return data;
}

function cleanGenericJson(rawBody) {
  const data = JSON.parse(rawBody);
  return JSON.stringify(normalizeCommonEnvelope(walk(data)));
}

function emptyRecommend() {
  return JSON.stringify({
    code: 0,
    result: 0,
    msg: "success",
    data: null,
  });
}

function emptyZoneTip() {
  return JSON.stringify({
    code: 0,
    result: 0,
    ret_code: 0,
    msg: "success",
    err_msg: "success",
    data: null,
  });
}

function emptyFeeds() {
  return JSON.stringify({
    result: 0,
    msg: "",
    err_msg: "",
    data: {
      result: 0,
      next: "",
      feedsInfo: [],
    },
  });
}

function main() {
  const handler = HANDLERS.find((item) => item.test.test(url));
  if (!body && !handler) return {};
  if (!handler) return { body };

  try {
    return { body: handler.run(body) };
  } catch (error) {
    console.log(`zhangmeng.adblock.js failed: ${error}`);
    return { body };
  }
}

$done(main());
