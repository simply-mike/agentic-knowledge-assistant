from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas import ChatRequest, ChatResponse, SourceSchema
from app.config import get_settings
from app.db.session import get_db
from app.permissions.policies import PermissionPolicyError
from app.retrieval.embeddings import build_embedding_provider
from app.retrieval.rag import BaselineRAGService
from app.retrieval.retriever import KnowledgeRetriever
from app.retrieval.vector_store import PGVectorStore

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    settings = get_settings()
    embedding_provider = build_embedding_provider(settings)
    vector_store = PGVectorStore(db)
    retriever = KnowledgeRetriever(vector_store, embedding_provider)
    rag_service = BaselineRAGService(retriever)

    try:
        response = rag_service.answer(
            query=request.message,
            role=request.role,
            top_k=request.top_k,
            filters=request.filters,
        )
    except PermissionPolicyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ChatResponse(
        answer=response.answer,
        sources=[
            SourceSchema(
                title=citation.title,
                url=citation.url,
                chunk_id=citation.chunk_id,
                source=citation.source,
            )
            for citation in response.citations
        ],
        tool_calls=response.tool_calls,
        trace_id=response.trace_id,
    )
