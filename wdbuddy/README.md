# WDBuddy — 全场景职场 AI 智能体桌面工作台

> 输入一句话，交付可验收的成果。不是"告诉你怎么做"，而是"直接把活干了"。

## 产品定位

WDBuddy 是一款桌面端 AI 办公智能体（Agent），用户用一句自然语言下达任务，产品在本地自主规划、拆解、执行多步骤任务，并交付**可验收的成果**（文档、表格、PPT、网页、图表、调研报告、海报等）。

- **过程可见**：步骤时间线、实时流式输出、Diff 回滚、版本管理
- **低使用门槛**：内置提示词增强，口语化输入也能稳定输出
- **权限分级**：敏感操作默认需确认，文件操作限定授权目录
- **桌面原型**：支持本地开发运行；微信扫码登录目前为演示实现

## 技术架构（三进程模型）

```
Renderer(React)  ──IPC──▶  Main(主进程)  ──JSON-RPC/stdio──▶  Agent Runtime(子进程)
   三栏 UI/状态              窗口/托盘/存储                       Planner/Executor/Verifier
```

| ADR | 决策 |
|---|---|
| 0001 | Agent Runtime 为独立 Node 子进程（崩溃隔离、可独立重启） |
| 0002 | SQLite（WAL）+ 步骤级检查点接口；持久化恢复尚未接通 |
| 0003 | Main↔Runtime 采用 JSON-RPC over stdio（无端口、天然进程边界） |
| 0004 | 权限检查收敛于统一沙箱层（fs-guard + policy-engine），单点强制 |
| 0005 | 模型接入统一为 OpenAI 兼容协议抽象 + Provider 适配器 |

## 目录结构（§9 唯一标准）

```
wdbuddy/
├── apps/
│   ├── desktop/     # Electron 应用壳（主进程 + preload）
│   ├── renderer/    # 渲染进程（React 18 + Zustand，三栏工作台）
│   ├── server/      # 云端服务（账号/积分/模型网关/技能市场/多端联动）
│   └── mobile/      # 多端联动端（占位）
├── packages/
│   ├── shared-types/   # ★ 全局唯一类型源
│   ├── agent-runtime/  # ★ Agent 循环（Planner/Executor/Replanner/Verifier）
│   ├── model-gateway/  # 统一流式协议 + Provider 适配器
│   ├── sandbox/        # ★ 权限强制层（fs-guard + policy-engine）
│   ├── skill-sdk/      # 技能定义 SDK（manifest + 声明式权限）
│   ├── ui/             # 跨端共享基础组件
│   └── testing/        # mock-model-server + fixtures
├── e2e/                # Playwright 黄金场景
├── configs/  scripts/  docs/
```

## 开发

```bash
# 安装依赖（仓库声明 pnpm 9.12.3；Node.js >= 20.11）
pnpm install --frozen-lockfile

# 为 Electron 安装匹配的 SQLite 原生模块（首次安装或升级依赖后执行）
node scripts/rebuild-electron-natives.mjs

# 开发模式（先构建主进程和 Runtime，再启动 Vite 与 Electron）
pnpm dev

# 构建 / 测试 / 打包
pnpm build
pnpm test
pnpm e2e
pnpm package
```

## 核心概念

- **三种任务模式**：`Ask`（只读问答）/ `Plan`（计划审批后执行）/ `Craft`（全自主执行交付）
- **沙箱双保险**：Agent 行为沙箱（fs-guard + policy-engine）约束 AI 动作；渲染沙箱（iframe + contextIsolation）约束 AI 生成内容
- **检查点恢复**：已实现中断状态提示；Runtime 当前使用内存检查点，跨进程持久化恢复尚未实现
- **类型单一事实源**：IPC 通道、JSON-RPC 协议、REST 接口类型全部由 `shared-types` 派生，禁手写重复类型

详细规格见 `docs/WDBuddy-Spec.md`。

## 当前验证与限制

- `pnpm build` 会构建各工作区，并把前端静态资源和数据库 schema 复制到桌面构建目录。
- pnpm 11 会要求批准依赖安装脚本；工作区已明确允许 `electron`、`better-sqlite3`、`esbuild`，无需批准其他依赖。
- Windows 下系统 Node.js 与 Electron 的 ABI 不同，仅完成 `pnpm install` 可能出现 `better_sqlite3.node` 版本不匹配；上面的原生模块准备脚本用于解决此问题。
- 桌面应用的模型设置独立于 Python CLI，需要在 WDBuddy「设置 → 模型」配置 API Key。
- PPT 模板克隆及真实模板预览需要 `python-pptx`：在启动桌面的同一终端中执行 `python -m pip install python-pptx`，并确保该 Python 在 PATH 中。
- 微信登录、云端模型代理、市场技能签名仍含演示或占位逻辑；移动端尚未实现。
- 2026-10-21 验证：10 个构建任务通过；隔离测试下桌面窗口、preload API、任务数据库接口启动通过；Agent Runtime 60 项、模型路由 8 项测试通过；沙箱测试 34 项通过、5 项失败，完整测试尚未通过。
