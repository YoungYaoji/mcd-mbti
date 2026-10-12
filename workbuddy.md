# workbuddy.md — 麦门人格鉴定所（mcd-mbti）WorkBuddy 开发上下文

> 本文件记录参赛项目「麦门人格鉴定所」使用**腾讯 WorkBuddy 智能体**完成开发的全过程对话上下文，
> 用于麦当劳程序员创意开发大赛 **WorkBuddy 专项奖励**核验。
>
> - 项目仓库：https://github.com/YoungYaoji/mcd-mbti
> - 开发日期：2026-10-12（单日完成选题 → 开发 → 实测 → 修 Bug → 推送 → 报名全流程）
> - 开发者 GitHub 账号：YoungYaoji
> - 参赛报名 Issue：[M-China/mcd-developer-innovation-challenge#520](https://github.com/M-China/mcd-developer-innovation-challenge/issues/520)（官方已回复"您的作品已成功参赛"）

---

## 一、项目是什么

**麦门人格鉴定所（MCD MBTI Lab）**：基于麦当劳中国 MCP Server 真实数据的 MBTI 人格鉴定 Skill。

不答题、不抽签——四轴评分全部由用户的真实订单计算：

- 拉取 `order-list`（历史订单：餐品明细 / 门店 / 金额 / 时间）→ 四轴评分核心数据源
- 拉取 `query-my-coupons`（持券数量）→ 「精算度」成分信号
- 拉取 `query-my-account`（积分账户）→ 鉴定报告资产维度
- 拉取 `list-nutrition-foods`（160+ 餐品营养表）→ 经典款 / 新品判定背景数据

四轴口径：**EI 社交能量**（大套餐占比 / 场均商品数）、**SN 点单风格**（新品命中率）、
**TF 消费决策**（低客单占比 + 持券数）、**JP 时间节律**（时段集中度 + 深夜单占比）。
输出 16 型麦门人格 + 五维麦门成分（猎奇 / 嗜辣 / 夜猫 / 精算 / 分享）+ 一张可晒的 SVG 鉴定卡。
订单不足 3 单时诚实降级为「尝鲜体验版」并明示样本量，**绝不编造人格**。

---

## 二、开发时间线（对话上下文实录）

### 阶段 1：参赛与选题

**用户**：参加了麦当劳程序员创意开发大赛（2026-10-09 ~ 10-25，排名按 GitHub Star，前 100 获奖），
让 WorkBuddy 基于麦当劳 MCP 想一个创意选题。

**WorkBuddy 执行**：读取大赛规则（`refs/challenge/`），确认参赛硬性要求（README.md /
CONTEST_DECLARATION.md / MCP_INTEGRATION.md / mcp-config.example.json / 源代码 / workbuddy.md），
首版选题为「麦门黄历」（赛博玄学 + MCP 真实数据），目录 `mcd-almanac/`，
单日完成架构并产出 2 个 commit：

- `scripts/mcd_client.py` —— 纯标准库 MCP Streamable HTTP 客户端（initialize → tools/call）
- `scripts/lunar.py` —— 1900-2099 农历转换（lunarInfo 表，经 lunardate 参考实现全量校验零差异）
- `scripts/fortune.py` —— 运势引擎（日期种子同日同盘，MCP Tool 信号驱动宜忌）
- `scripts/render_card.py` / `run.py` —— SVG 传统黄历卡片 + CLI（`--mock` 演示）

### 阶段 2：MCP 真实数据实测

**用户**：在 `~/.workbuddy/mcp.json` 配好 mcd-mcp 连接器（按官方指南，`url` 为 `https://mcp.mcd.cn` 根路径），提供 Token 要求实测。

**WorkBuddy 执行**：initialize 成功，实测服务器共 **35 个 Tool**。关键发现：MCP 返回**不是 JSON
而是 Markdown 文本**，分两类格式——① Markdown 摘要（campaign-calendar / available-coupons /
query-my-coupons）；② "API Response Information" 型（order-list / query-my-account /
list-nutrition-foods，末尾 `## Original Response` 跟一段 JSON，nutrition 的 data 还是 CSV 文本）。
解析层按真实格式重写。另发现抽奖官方不公示概率 → 放弃伪造期望值，改「奖池透视」+ 积分充裕度建议。
真实跑通：3 活动 / 3 张待领券 / 928 积分 / 幸运餐品「草莓拉明顿」。

### 阶段 3：项目转向 —— 麦门人格鉴定所

**用户**：否掉黄历方案，改用 MBTI 方向，要「用真实订单数据算出人格」。

**WorkBuddy 执行**：新建 `mcd-mbti/`（黄历项目保留未动）。先用真实数据探路：
`order-list` 返回 10 单真实订单（2026-08-01 ~ 09-18，3 家门店，¥6 ~ 71.8，含 comboItemList 完整明细）。
据此设计四轴算法与 16 型人格命名，架构：

- `scripts/mcd_client.py` —— 复用黄历项目的 MCP 客户端
- `scripts/persona.py` —— 订单聚合 + 四轴评分 + 16 型匹配 + 五维成分
- `scripts/render_card.py` —— 麦当劳红黄配色 SVG 测评卡
- `scripts/run.py` —— CLI（mock 订单样本按真实格式构造，零 Token 可体验）

用户本人真实鉴定结果：**ENTP 麦门发明家**（E64/N61/T77/P62，猎奇84/嗜辣95/精算73/分享95）。

### 阶段 4：三轮用户截图反馈修 Bug

开发过程中用户通过截图反馈迭代三轮，全部由 WorkBuddy 定位根因并修复：

1. **四轴字母极性 bug**：EI/JP 评分方向与字母映射反了 → 改用「高分极」统一逻辑修复
2. **SVG 与文本百分比不一致**：新增 `axis_display()` 统一口径；顺带发现 mock 测试漏传 coupons 导致的假性不一致
3. **天平填充方向 + 标签溢出（同一视觉问题反馈三次）**：dominant 在右时填充仍从左起 → 改天平式右起填充；
   最终根因是百分比标签冲出天平背景框（标签起点 622 + 文字宽 > 背景右缘 640）→
   `bar_w` 380→336、标签起点 622→566 收进框内，并把天平改为双色对峙条

### 阶段 5：GitHub 推送与报名

**用户**：安装 gh CLI 2.102.0 至 `E:/software/GitHub CLI/`（不在 PATH），登录账号 YoungYaoji。

**WorkBuddy 执行**：手动配置 credential helper（gitconfig 值中带空格路径需用 `"..."` 包在 `!` 后）；
本机代理 127.0.0.1:10921 对 github.com 间歇 502，推送靠多重试成功：

- 仓库推送：https://github.com/YoungYaoji/mcd-mbti （public，main）
- 设置 `MCD_MCP_TOKEN` secret，`weekly-persona.yml` 每周一自动刷新人格卡归档
- 报名 Issue #520 按官方模板格式发布 → **官方机器人回复"您的作品已成功参赛"**

### 阶段 6：攒 Star 物料

- `gh repo edit --add-topic` 添加 mcdonalds/mcp/mbti/personality-test/python/svg 六个 topics
- 人格卡转 PNG：cairosvg 缺 Windows cairo DLL → 改用 Edge headless
  （`--headless --screenshot --window-size=680,1408 --force-device-scale-factor=2`）截 2x 高清图
- 朋友圈宣传图 `examples/promo.svg`（1080×1440：金拱门 logo + 标题 + 人格卡嵌入 + 6 张数据贴纸 + CTA 条）
- 配色升级：四轴天平改 MBTI 经典四色 × 麦当劳红黄（E=麦当劳红/I=MBTI蓝、S=绿/N=紫、T=深蓝/F=暖橙、J=玫红/P=金）
- 推广文案去 AI 味重写（口语化短句，保留真实数据：402 元 / 3 门店 / 11 张券 / 嗜辣 95%）
- push 遇代理 502 时，降级用 `gh api` Contents API（PUT /contents，base64+sha）直接更新远端文件，
  本地 fetch 恢复后 `reset --hard origin/main` 对齐历史

---

## 三、WorkBuddy 能力使用清单

| 能力 | 用在哪 |
|---|---|
| 对话式需求拆解与架构设计 | 选题、四轴算法口径、16 型人格命名 |
| 文件读写 / 编辑 | 全部 `scripts/*.py`、SVG 模板、参赛文档 |
| Shell 命令执行 | MCP 实测、git 提交推送、gh CLI 报名、Edge headless 截图 |
| MCP 连接器（mcd-mcp） | 按官方指南配置于 `~/.workbuddy/mcp.json`，拉取真实订单/券/积分/餐品数据 |
| 多轮截图反馈迭代 | 三轮视觉 Bug 定位修复（极性 / 口径 / 溢出） |
| 联网检索 | 大赛规则、MCP 官方文档、农历算法参考实现 |

## 四、真实性说明

- 项目全部代码、文档、配图均在 WorkBuddy 会话中开发完成，开发过程记录于项目 `.workbuddy/memory/` 工作日志
- 人格评分数据源为开发者本人麦当劳账户真实订单（10 单 / 2026-08-01 ~ 09-18），未使用任何虚假数据
- 项目为原创，未抄袭、未使用他人代码；CONTEST_DECLARATION.md 使用官方原文未做任何改动
