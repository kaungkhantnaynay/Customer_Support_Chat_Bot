# Phase 2: Knowledge Base

This phase gives the chatbot something useful to search before it tries to answer customers.

## Step 1: Added Sample Support Documents

I created a small fake company knowledge base in:

```text
data/knowledge_base/
```

It includes:

- Refund policy
- Shipping policy
- Account help
- Subscription and billing
- Troubleshooting guide

These documents are the source of truth for future chatbot answers.

## Step 2: Built A Document Loader

I added code that reads Markdown files from the knowledge base folder.

File:

```text
app/rag/documents.py
```

The loader turns each Markdown file into a `SourceDocument` with:

- document id
- title
- file path
- content

## Step 3: Built A Chunker

Long documents are harder to search directly.

The chunker splits documents into smaller pieces called `DocumentChunk`.

Each chunk keeps source information, so later the chatbot can cite where the answer came from.

## Step 4: Added A Local Embedding Interface

File:

```text
app/rag/embeddings.py
```

I added an `EmbeddingService` interface.

For now, the project uses `KeywordEmbeddingService`, a simple local search-friendly embedding.

This is useful because:

- it works without an API key
- it is easy to test
- it lets us build the retrieval flow first
- we can replace it later with OpenAI embeddings

## Step 5: Added Local Vector Search

File:

```text
app/rag/retriever.py
```

The retriever:

1. Loads support documents.
2. Splits them into chunks.
3. Converts chunks into local vectors.
4. Converts the user query into a vector.
5. Compares the query with each chunk.
6. Returns the best matching chunks.

Each result includes:

- score
- title
- source path
- citation
- matching text

## Step 6: Added A Search API Endpoint

Endpoint:

```text
GET /knowledge/search?q=your question
```

Example:

```text
/knowledge/search?q=How long does express shipping take?
```

This endpoint proves that the backend can search company knowledge before we build the real chatbot.

## Step 7: Added Tests

File:

```text
tests/test_knowledge_base.py
```

The tests check that:

- documents load correctly
- documents are split into chunks
- search finds a relevant refund document
- the API returns citations

## Why This Matters

This phase is the beginning of RAG:

```text
Retrieval-Augmented Generation
```

In simple terms:

```text
Search first, answer second.
```

That is important because the final chatbot should answer from trusted support documents, not random model memory.

## Next Phase

Next we can build Phase 3:

```text
Chat API
```

The chatbot will use this retrieval system to find relevant knowledge, then generate a customer-friendly answer with citations.
