# RAG Knowledge Base System

轻量级RAG知识库系统，为别墅Bot提供智能问答支持。

## 📁 目录结构

```
rag/
├── __init__.py          # RAG系统主入口
├── knowledge_base.py    # 知识库管理（支持热更新）
├── indexer.py          # TF-IDF索引构建
├── retriever.py        # 检索器
├── generator.py         # 答案生成器
├── test_rag.py         # 测试脚本
└── data/
    ├── villas.json     # 14套别墅详情（中英泰三语）
    ├── faq.json       # 15个常见问题
    ├── guides.json     # 8个入住指南
    ├── nearby.json     # 15个周边攻略
    └── rag_index.db    # SQLite索引数据库
```

## 🔧 四阶段架构

### 1. 数据准备 (Knowledge Base)
- **14套别墅**: 芭提雅、曼谷、普吉岛
- **15个FAQ**: 预订、入住、费用、设施等
- **8个入住指南**: 准备事项、安全须知等
- **15个周边攻略**: 景点、美食、购物
- 支持**中/英/泰**三语

### 2. 索引构建 (Indexer)
- **TF-IDF算法**: 关键词权重计算
- **倒排索引**: 词项 → 文档映射
- **SQLite存储**: 轻量级，无需额外服务
- **支持热更新**: 修改知识库文件自动重建索引

### 3. 检索 (Retriever)
- **关键词提取**: 中/英/泰混合分词
- **Top-K检索**: 返回最相关的5条
- **置信度阈值**: 0.1（过滤低相关度）
- **分类检索**: villa/faq/guide/nearby

### 4. 生成 (Generator)
- **模板生成**: 无LLM时使用规则生成
- **多语言输出**: 中文/英文/泰文
- **来源标注**: 标注信息来源和相关性

## 🚀 使用方法

### 基本使用

```python
from rag import get_rag_system

# 初始化RAG系统
rag = get_rag_system()

# 问答
answer = rag.query("普吉岛有什么好玩的？")
print(answer)
```

### 分类检索

```python
# 别墅推荐
answer = rag.query_villa("我想要带泳池的别墅")

# FAQ查询
answer = rag.query_faq("如何取消预订？")

# 周边攻略
answer = rag.query_nearby("普吉岛", region="普吉岛")
```

### 模块集成

```python
from modules import init_rag, rag_answer

# 初始化
init_rag()

# 问答
answer = rag_answer("Cinq Royal别墅价格？")
```

### 热更新

```python
from modules import reload_rag

# 更新知识库后重新加载
reload_rag()
```

## 📊 知识库数据

### 别墅数据 (villas.json)

```json
{
  "id": "HKT001",
  "name": "Cinq Royal 总统套房别墅",
  "region": "普吉岛",
  "price_per_night": 8888,
  "bedrooms": 5,
  "amenities": ["私人沙滩", "无边泳池", "管家服务", ...],
  "description_en": "...",
  "description_th": "..."
}
```

### FAQ数据 (faq.json)

```json
{
  "id": "faq001",
  "question": "如何预订别墅？",
  "answer": "...",
  "question_en": "...",
  "question_th": "..."
}
```

## ⚙️ 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| confidence_threshold | 0.1 | 置信度阈值 |
| top_k | 5 | 检索返回数量 |
| language | zh | 输出语言 |

## 🔄 热更新流程

1. 修改 `rag/data/*.json` 文件
2. 调用 `reload_rag()` 或 `rag.reload()`
3. 系统自动检测修改并重建索引

## 📝 添加新别墅

编辑 `rag/data/villas.json`:

```json
{
  "id": "NEW001",
  "name": "新别墅名称",
  "region": "城市",
  "room_type": "房型",
  "price_per_night": 1000,
  "bedrooms": 2,
  "bathrooms": 1,
  "max_guests": 4,
  "amenities": ["泳池", "WiFi"],
  "description": "描述",
  "description_en": "English description",
  "description_th": "คำอธิบายภาษาไทย"
}
```

## 🧪 运行测试

```bash
cd villa-booking-bot
python rag/test_rag.py
```

## 📈 性能指标

- **索引构建**: ~52文档/秒
- **检索响应**: <100ms
- **内存占用**: <50MB
- **存储占用**: ~1MB（索引）

## 🔧 部署说明

### Render免费版部署

RAG系统设计为轻量级，适合Render免费版：
- SQLite索引: 无需额外数据库服务
- 文件热更新: 无需重启Bot
- 低内存占用: <50MB

### 环境变量

无需额外环境变量，所有配置在代码中完成。

## 📄 License

MIT
