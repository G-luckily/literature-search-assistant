# 暗色模式重新设计（方案 B：高对比暗色）

## 目标

将当前暗色模式从玻璃质感方案重构为高对比、灰阶分层的暗色主题，解决现有 CSS 碎片化导致的视觉层次不清、对比度不足问题。

## 核心问题

现有 `styles.css` 中存在 4+ 个独立的 `html[data-theme="dark"]` 块，Pencil Design System 覆盖块（行 ~7271+）因源码顺序最晚而优先级最高，将侧栏和卡片压至极低透明度（3-6%），导致界面扁平、缺乏层次。

## 色板系统

```
--bg               #0a0a0f   页面背景
--bg-elevated      #101018   侧栏背景
--surface          #1a1a24   卡片底色
--surface-hover    #20202e   卡片悬停
--surface-raised   #12121a   输入框/次要按钮
--line             #2a2a3a   分割线/边框
--line-hover       #3a3a4e   悬停边框
--text-primary     #f1f5f9   主要文字
--text-secondary   #94a3b8   次要文字
--text-muted       #64748b   禁用/辅助文字
--accent           #3b82f6   强调色（蓝）
--accent-hover     #2563eb   强调悬停
--accent-soft      rgba(59,130,246,0.08)  选中底色
--accent-tag       rgba(59,130,246,0.1)   标签底色
--accent-text      #93c5fd   选中文字/标签文字
--shadow           0 12px 32px rgba(0,0,0,0.4)
--shadow-soft      0 4px 12px rgba(0,0,0,0.3)
```

## 字体层级

| 层级 | 字重 | 大小 | 行高 | 用途 |
|------|------|------|------|------|
| caption | 600 | 11px | 1.4 | 导航分组/标签 |
| ui | 500 | 13px | 1.5 | 导航链接/按钮/卡片正文 |
| body | 400 | 14px | 1.6 | 输入框/段落 |
| card-title | 600 | 15px | 1.4 | 卡片标题 |
| page-title | 700 | 20px | 1.3 | 页面主标题 |

字体系列：Inter / "Noto Sans SC" / sans-serif（与日间模式一致）

## 组件规范

### 侧栏
- 背景色：`#101018`，纯色填充
- 右侧边框：`1px solid #1e1e2e`
- 导航链接：13px、500、`#94a3b8`
- 选中项：背景 `rgba(59,130,246,0.08)`、文字 `#93c5fd`
- hover：背景 `rgba(255,255,255,0.03)`

### 卡片
- 背景色：`#1a1a24`，无 backdrop-filter/blur
- 边框：`1px solid #2a2a3a`
- border-radius：12px
- 阴影：`0 4px 12px rgba(0,0,0,0.3)`
- hover：背景 `#20202e`，边框 `#3a3a4e`

### 按钮
- 主要按钮：背景 `#2563eb`，hover `#1d4ed8`，10px radius，白色文字
- 次要按钮：背景 `#12121a`，边框 `#2a2a3a`，hover 边框 `#3a3a4e`
- 无渐变色，无玻璃效果

### 输入框
- 背景色：`#12121a`，无玻璃效果
- 边框：`1px solid #2a2a3a`
- focus：边框 `#3b82f6` + 3px 蓝色 ring `rgba(59,130,246,0.15)`

### 标签/徽标
- 背景：`rgba(59,130,246,0.1)` + 1px 边框 `rgba(59,130,246,0.15)`
- 文字色：`#93c5fd`

### Topbar
- 背景色：`#0d0d15`（纯色，无玻璃效果）
- 下边框：`1px solid #1e1e2e`
- 图标按钮：背景 `#1a1a24`，边框 `#2a2a3a`

### 页面背景
- 纯色 `#0a0a0f`，无径向渐变

### 氛围光晕（可选）
- 若保留 ambient-glow 元素，改用蓝色调：`rgba(59,130,246,0.08)`

## 页面布局

2-column 布局不变：`240px minmax(0, 1fr)`
- 侧栏固定 240px
- 主内容区自适应

## 响应式

- 与日间模式共用断点
- 暗色模式只改颜色变量和背景，不改布局断点
- 移动端：侧栏自动隐藏的行为与日间一致

## 改动范围

### 必需改动
- `src/litassist/web_static/styles.css`：
  - 删除所有旧 `html[data-theme="dark"]` 块（约 4 个独立块）
  - 在 `Pencil Design System` 的 `html[data-theme="dark"]` 位置统一重写为新色板+组件规则
  - 删除所有 backdrop-filter / blur 在暗色中的使用
  - 删除所有 radial-gradient 背景（改为纯色）
  - 替换青色系强调色为蓝色系

### 不修改
- `light-theme.css` — 日间模式不动
- `index.html` — 结构不动
- `app.js` — 逻辑不动

## 质量检查清单

- [ ] 所有色值使用 CSS 变量（禁止硬编码）
- [ ] 组件 hover/focus-visible/active 状态全部覆盖
- [ ] 无 `!important`（仅 Chart.js canvas 覆写等必要场景保留）
- [ ] 侧栏、卡片、输入框 hover 状态一致
- [ ] 两个主题切换无闪烁/错位
- [ ] 无 backdrop-filter（此方案不用玻璃效果）
