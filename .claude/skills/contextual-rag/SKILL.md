---
name: contextual-rag
description: >
  Паттерны улучшенного RAG (Retrieval-Augmented Generation): Contextual Retrieval
  от Anthropic (-49% ошибок), Hybrid Search (+15-30% точности), Reranking,
  GraphRAG для связанных данных. Применять при создании систем поиска по документам,
  1С базе знаний, или любому корпусу текстов.
user-invocable: true
---

# Contextual RAG — Паттерны улучшенного поиска

## Проблема стандартного RAG

Стандартный RAG теряет контекст при разбивке на чанки:
```
Документ: "Закупки в 1С:ERP УСО..."
Чанк 5:   "Поставщик выбирается на основе..."  ← непонятно о чём
```

Решение: **Contextual Retrieval** (Anthropic) — добавить контекст к каждому чанку.

---

## Паттерн 1: Contextual Retrieval (−49% ошибок)

### Алгоритм

1. Для каждого чанка сгенерировать контекст:
```python
CONTEXT_PROMPT = """
Документ: {full_document}

Вот небольшой фрагмент из этого документа:
<chunk>
{chunk}
</chunk>

Напиши краткий контекст (2-3 предложения) для этого фрагмента
в контексте всего документа. Отвечай только контекстом, без преамбулы.
"""
```

2. Prepend контекст к чанку перед embedding:
```python
contextualized_chunk = f"{context}\n\n{chunk}"
embedding = embed(contextualized_chunk)
```

### Для 1С базы знаний (пример)

```python
# Вместо:
chunk = "Документ РасходнаяНакладная используется для..."
# Стало:
chunk = """Этот фрагмент описывает документ РасходнаяНакладная из подсистемы
Закупки 1С:ERP УСО 2.5. Документ является основным для оформления расхода МТР.

Документ РасходнаяНакладная используется для..."""
```

### Стоимость

Используй **prompt caching** — полный документ кешируется, только чанк меняется:
- Без кеша: ~$20 на 1000 документов
- С кешем: ~$2 на 1000 документов (90% экономия)

---

## Паттерн 2: Hybrid Search (+15-30% точности)

Комбинирует dense (semantic) и sparse (keyword) поиск:

```python
from rank_bm25 import BM25Okapi  # sparse
import numpy as np

def hybrid_search(query, chunks, embeddings, k=10, alpha=0.5):
    """
    alpha = 0.5: равный вес dense и sparse
    alpha = 0.7: больше веса semantic (для концептуальных запросов)
    alpha = 0.3: больше веса keyword (для точных терминов)
    """
    # Dense search (semantic)
    query_embedding = embed(query)
    dense_scores = cosine_similarity(query_embedding, embeddings)

    # Sparse search (BM25)
    tokenized = [c.split() for c in chunks]
    bm25 = BM25Okapi(tokenized)
    sparse_scores = bm25.get_scores(query.split())

    # Normalize to [0,1]
    dense_norm = (dense_scores - dense_scores.min()) / (dense_scores.max() - dense_scores.min())
    sparse_norm = (sparse_scores - sparse_scores.min()) / (sparse_scores.max() - sparse_scores.min())

    # Combine
    final_scores = alpha * dense_norm + (1 - alpha) * sparse_norm
    return np.argsort(final_scores)[-k:][::-1]
```

**Когда использовать какой режим:**
| Тип запроса | alpha | Пример |
|-------------|-------|--------|
| Концептуальный | 0.7 | "Как работает закрытие месяца?" |
| Точный термин | 0.3 | "РасходнаяНакладная реквизит Склад" |
| Смешанный | 0.5 | "ошибки при проведении закупки" |

---

## Паттерн 3: Reranking (+20% precision)

После первичного поиска (top-20) → cross-encoder переранжирует:

```python
# pip install sentence-transformers
from sentence_transformers import CrossEncoder

reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

def rerank(query, candidates, top_k=5):
    pairs = [(query, doc) for doc in candidates]
    scores = reranker.predict(pairs)
    ranked = sorted(zip(scores, candidates), reverse=True)
    return [doc for _, doc in ranked[:top_k]]
```

**Пайплайн:**
```
Query → Hybrid Search (top-20) → Reranker → top-5 → LLM
```

---

## Паттерн 4: GraphRAG (для связанных данных)

Когда нужны multi-hop запросы: "Какие модули связаны с Закупками И Финансами?"

```python
# Данные как граф (networkx)
import networkx as nx

G = nx.DiGraph()
# Узлы: подсистемы, модули, документы
G.add_node("Закупки", type="subsystem")
G.add_node("ПоступлениеТоваров", type="document")
G.add_edge("Закупки", "ПоступлениеТоваров", relation="contains")

# Multi-hop запрос
def graph_rag_search(query_entities, hops=2):
    relevant = set()
    for entity in query_entities:
        neighbors = nx.ego_graph(G, entity, radius=hops)
        relevant.update(neighbors.nodes())
    return list(relevant)
```

**Когда использовать GraphRAG для 1С:**
- Запросы о связях подсистем: "что затрагивает изменение в Закупках?"
- Поиск зависимостей: "какие модули вызывают ОбщийМодуль.Метод?"
- Анализ влияния: "что сломается если изменить документ?"

---

## Паттерн 5: Agentic RAG (итеративный)

Агент сам решает когда и что искать:

```python
# Псевдокод
def agentic_rag(question):
    retrieved = []
    for iteration in range(3):  # max 3 итерации
        # Оценить достаточность текущих данных
        assessment = llm(f"Question: {question}\nData: {retrieved}\nSufficient? Yes/No. If No, what query?")

        if assessment.sufficient:
            break

        # Поиск с уточнённым запросом
        new_results = search(assessment.next_query)
        retrieved.extend(new_results)

    return llm(f"Answer based on: {retrieved}")
```

---

## Применение к 1С базе знаний

### Текущий стек (memory файлы → flat search)

```
memory/1c-uso-index.md
memory/1c-uso-procurement.md  ← линейный поиск
memory/1c-uso-finance.md
```

### Улучшенный стек (Contextual + Hybrid)

```python
# Шаг 1: Индексация с контекстом
for doc_file in glob("memory/1c-uso-*.md"):
    full_doc = read(doc_file)
    for chunk in split_by_heading(full_doc):
        context = generate_context(full_doc, chunk)
        indexed_chunk = f"{context}\n\n{chunk}"
        store_with_embedding(indexed_chunk)

# Шаг 2: Поиск
results = hybrid_search(
    query="закрытие месяца ошибки",
    alpha=0.5  # balanced
)
reranked = reranker.predict(query, results[:20])
```

### Векторная БД для локального использования (Windows)

**LanceDB** — лучший выбор: embedded, нет сервера, Python, быстро:
```bash
pip install lancedb anthropic sentence-transformers rank_bm25
```

```python
import lancedb
db = lancedb.connect("~/.claude/rag-index")
table = db.create_table("1c_knowledge", schema=...)
```

---

## Чеклист внедрения RAG

- [ ] Разбивка документов по заголовкам (не фиксированный размер)
- [ ] Contextual Retrieval — prepend контекст к каждому чанку
- [ ] Prompt caching включён (экономия 90%)
- [ ] Hybrid Search (dense + BM25)
- [ ] Reranker на top-20 → top-5
- [ ] Тест качества: precision@5 > 80%

## Метрики качества

| Метрика | Хорошо | Плохо |
|---------|-------|-------|
| Retrieval recall | > 85% | < 70% |
| Answer faithfulness | > 90% | < 80% |
| Answer relevancy | > 85% | < 75% |
| Context precision | > 80% | < 65% |
