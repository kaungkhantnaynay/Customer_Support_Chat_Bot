from pydantic import BaseModel, Field


class KnowledgeSearchResponse(BaseModel):
    query: str
    results: list["KnowledgeSearchResult"]


class KnowledgeSearchResult(BaseModel):
    score: float = Field(ge=0)
    title: str
    source_path: str
    citation: str
    text: str
