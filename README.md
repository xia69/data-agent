# DataAgent — 智能数据查询 Agent

基于 LangGraph 构建的自然语言数据查询系统。用户输入中文问题，Agent 自动完成关键词提取、向量召回、SQL 生成、校验执行，返回查询结果。

## 技术栈

| 层 | 技术 |
|---|---|
| Agent 框架 | LangGraph (StateGraph) |
| LLM | DeepSeek-V4-Pro (OpenAI 兼容) |
| 向量存储 | Qdrant 1.16 |
| Embedding | BAAI/bge-large-zh-v1.5 (TEI CPU) |
| 全文检索 | Elasticsearch 8.x + IK 分词 |
| 结构化元数据 | MySQL 8.0 |
| Web 框架 | FastAPI + SSE 流式 |
| 前端 | 纯 HTML/CSS/JS |
| 包管理 | uv |

## 架构

```
用户问题
  → extract_keywords (结巴 + 关键词提取)
  → recall_column / recall_metric / recall_value (三路并行召回)
  → merge_retrieved_info (合并 + MySQL 补全 + 主外键)
  → filter_table / filter_metric (LLM 过滤)
  → add_extra_context (日期/DB 上下文)
  → generate_sql (LLM 生成 SQL)
  → validate_sql (数仓语法校验)
  → correct_sql (LLM 纠错，校验失败时触发)
  → run_sql (执行 + 返回结果)
```

## 启动

> 所有命令均在项目根目录 `data-agent/` 下执行。

### 1. 环境准备

```bash
uv sync
```

### 2. 启动 Docker 服务

```bash
cd docker && docker compose up -d
```

启动后确认容器状态：

```bash
docker ps    # 应看到 mysql, elasticsearch, qdrant, embedding 四个容器在运行
```

### 3. 构建元数据知识库

```bash
python -m app.scripts.build_meta_knowledge --conf conf/meta_config.yaml
```

### 4. 启动 API

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

看到 `Application startup complete.` 表示启动成功。

### 5. 打开前端

浏览器打开 `web/index.html`，输入问题即可查询。

## 配置

LLM、数据库、embedding 等配置在 `conf/app_config.yaml`。

提示词管理在 `prompts/` 目录，按文件名加载，修改后无需改代码即可生效。

## 项目结构

```
data-agent/
├── app/
│   ├── agent/          # LangGraph 图定义 + 节点
│   │   ├── graph.py    # 图构建
│   │   ├── nodes/      # 12 个节点
│   │   ├── state.py    # 状态定义
│   │   ├── context.py  # 依赖注入
│   │   ├── llm.py      # LLM 客户端
│   │   └── sse_event.py # SSE 事件工具
│   ├── api/            # FastAPI
│   ├── services/       # 业务服务层
│   ├── repositories/   # 数据仓库层 (MySQL/Qdrant/ES)
│   ├── entities/       # 实体 dataclass
│   ├── clients/        # 客户端管理器
│   ├── conf/           # 配置 dataclass
│   └── prompt/         # 提示词加载器
├── conf/               # YAML 配置文件
├── prompts/            # 提示词文件
├── docker/             # Docker Compose
└── web/                # 前端页面
```
