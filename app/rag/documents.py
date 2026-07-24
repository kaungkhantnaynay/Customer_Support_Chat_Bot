from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceDocument:
    id: str
    title: str
    path: str
    content: str


@dataclass(frozen=True)
class DocumentChunk:
    id: str
    document_id: str
    title: str
    source_path: str
    text: str

    @property
    def citation(self) -> str:
        return f"{self.title} ({self.source_path})"


def load_markdown_documents(directory: Path) -> list[SourceDocument]:
    if not directory.exists():
        return []

    documents: list[SourceDocument] = []
    for path in sorted(directory.glob("*.md")):
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            continue

        title = _extract_title(content, path)
        document_id = path.stem
        documents.append(
            SourceDocument(
                id=document_id,
                title=title,
                path=str(path),
                content=content,
            )
        )

    return documents


def chunk_document(document: SourceDocument, max_words: int = 90) -> list[DocumentChunk]:
    paragraphs = _content_paragraphs(document.content)
    chunks: list[DocumentChunk] = []
    current: list[str] = []
    current_word_count = 0

    for paragraph in paragraphs:
        word_count = len(paragraph.split())
        if current and current_word_count + word_count > max_words:
            chunks.append(_make_chunk(document, chunks, current))
            current = []
            current_word_count = 0

        current.append(paragraph)
        current_word_count += word_count

    if current:
        chunks.append(_make_chunk(document, chunks, current))

    return chunks


def chunk_documents(documents: list[SourceDocument], max_words: int = 90) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    for document in documents:
        chunks.extend(chunk_document(document, max_words=max_words))
    return chunks


def _extract_title(content: str, path: Path) -> str:
    first_line = content.splitlines()[0].strip()
    if first_line.startswith("# "):
        return first_line.removeprefix("# ").strip()
    return path.stem.replace("_", " ").title()


def _content_paragraphs(content: str) -> list[str]:
    return [
        paragraph.strip()
        for paragraph in content.split("\n\n")
        if paragraph.strip() and not paragraph.strip().startswith("# ")
    ]


def _make_chunk(
    document: SourceDocument,
    existing_chunks: list[DocumentChunk],
    paragraphs: list[str],
) -> DocumentChunk:
    chunk_number = len(existing_chunks) + 1
    return DocumentChunk(
        id=f"{document.id}::chunk-{chunk_number}",
        document_id=document.id,
        title=document.title,
        source_path=document.path,
        text="\n\n".join(paragraphs),
    )
