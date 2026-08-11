# 掌盟去广告 Quantumult X 重写

基于 `quantumult-x-2026-08-11-112000.har` 解析生成。当前规则覆盖掌盟展示广告位、底栏运营角标、活动插入流，以及部分统计/追踪上报。

## 使用

1. 把 `zhangmeng.conf` 里的 `RAW_BASE` 改成脚本所在目录的 raw 地址。
2. 在 Quantumult X 添加远程重写，订阅 `zhangmeng.conf` 的 raw 地址。
3. 打开 MitM，并安装/信任证书。
4. 打开掌上英雄联盟，触发开屏、首页、资讯流、活动弹窗。
5. 如果仍有广告，重新导出 HAR，重点搜索 `platflashbox`、`floatbox`、`platbanner`、`platstrongshell`、`bottomtab_tip`、`activity`。

## 本地调试建议

先不要一上来写很宽的 `reject`。掌盟的接口里广告、活动、资讯可能混在同一个 JSON 里，直接拒绝请求容易导致页面空白。

推荐流程：

1. 抓到可疑接口后，复制响应体。
2. 确认响应是 JSON，再用 `script-response-body` 清字段。
3. 只有确认是纯广告图片、纯广告配置接口时，再使用 `reject-200`。

## 规则发布

如果仓库 raw 地址是：

```text
https://raw.githubusercontent.com/<user>/<repo>/main/rewrite_remote/zhangmeng
```

则把 `zhangmeng.conf` 中的：

```text
RAW_BASE/zhangmeng.adblock.js
```

替换为：

```text
https://raw.githubusercontent.com/<user>/<repo>/main/rewrite_remote/zhangmeng/zhangmeng.adblock.js
```

## 常见需要补的点

- 开屏广告：URL 或字段常见 `splash`、`startup`、`launch`
- 弹窗浮层：URL 或字段常见 `popup`、`poplayer`
- 信息流广告：响应数组里常见 `ad`、`advert`、`promotion`
- 活动运营位：字段可能是 `operation`、`market`、`material`，这类容易误伤，建议逐条确认

## 本次 HAR 命中的接口

展示广告位，走 `script-response-body` 返回空结构：

- `https://mlol.qt.qq.com/go/recommend/platflashbox`
- `https://mlol.qt.qq.com/go/recommend/floatbox`
- `https://mlol.qt.qq.com/go/recommend/platbanner`
- `https://mlol.qt.qq.com/go/recommend/platstrongshell`
- `https://mlol.qt.qq.com/go/zone/bottomtab_tip`
- `https://mlol.qt.qq.com/go/zone/newgamereminder`
- `https://mlol.qt.qq.com/go/content_svr/feeds/activity`

统计/追踪上报，走 `reject-200`：

- `https://ads.privacy.qq.com/optout/get_status`
- `https://hc.tdm.qq.com:8013/tdm/v1/route`
- `https://receiver.tdm.qq.com:8013/tdm/v1/kv`
- `https://sentry.qt.qq.com/api/26/envelope/`
- `https://gatherer.m.qq.com/gatherer_conf/GetConf`
- `https://szmg.qq.com/cgi-bin/log_data.fcg`
- `https://szmg.qq.com/heartbeat`
- `http://tracker-01.qvb.qcloud.com/api/v5/mobile/announce`
