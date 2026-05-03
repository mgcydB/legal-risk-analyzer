from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agent import LegalRiskAgent
from analyzer import AnalysisResult


class AnalyzeRequest(BaseModel):
    """分析请求"""
    content: str
    doc_type: str = "contract"
    title: str = "未命名文档"
    user_id: Optional[str] = None


class AnalyzeResponse(BaseModel):
    """分析响应"""
    document_title: str
    doc_type: str
    risk_points: List[Dict[str, Any]]
    summary: str
    recommendations: List[str]
    analyzed_at: str


class QuestionRequest(BaseModel):
    """问题请求"""
    query: str
    user_id: Optional[str] = None
    doc_type: Optional[str] = None


class AddDocumentRequest(BaseModel):
    """添加文档请求"""
    content: str
    doc_id: str
    doc_type: str = "contract"
    title: Optional[str] = None


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    user_id: Optional[str] = None


class StatsResponse(BaseModel):
    """统计响应"""
    legal_documents: Dict[str, Any]
    risk_knowledge: Dict[str, Any]


app = FastAPI(
    title="法律文件风险点分析系统 API",
    description="基于 SeekDB、PowerRAG 和 PowerMem 的法律风险分析系统",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_agent_cache: Dict[str, LegalRiskAgent] = {}


def get_agent(user_id: Optional[str] = None) -> LegalRiskAgent:
    """获取或创建 Agent 实例"""
    cache_key = user_id or "default"
    if cache_key not in _agent_cache:
        _agent_cache[cache_key] = LegalRiskAgent(user_id=user_id)
    return _agent_cache[cache_key]


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "法律文件风险点分析系统 API",
        "version": "0.1.0",
        "endpoints": {
            "analyze": "/api/analyze",
            "question": "/api/question",
            "chat": "/api/chat",
            "add_document": "/api/document",
            "upload": "/api/upload",
            "stats": "/api/stats",
        },
    }


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_document(request: AnalyzeRequest):
    """
    分析法律文档

    识别文档中的风险点，提供风险评估和修改建议。
    """
    try:
        agent = get_agent(request.user_id)
        result = agent.analyze_document(
            content=request.content,
            doc_type=request.doc_type,
            title=request.title,
        )

        return AnalyzeResponse(
            document_title=result.document_title,
            doc_type=result.doc_type,
            risk_points=[
                {
                    "risk_type": rp.risk_type,
                    "description": rp.description,
                    "severity": rp.severity.value,
                    "location": rp.location,
                    "legal_basis": rp.legal_basis,
                    "suggestions": rp.suggestions,
                    "confidence": rp.confidence,
                }
                for rp in result.risk_points
            ],
            summary=result.summary,
            recommendations=result.recommendations,
            analyzed_at=result.analyzed_at,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/question")
async def answer_question(request: QuestionRequest):
    """
    回答法律问题

    基于知识库检索相关法律知识，生成专业回答。
    """
    try:
        agent = get_agent(request.user_id)
        answer = agent.answer_question(
            query=request.query,
            doc_type=request.doc_type,
        )
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    与 Agent 对话

    支持自然语言交互，自动选择合适的工具完成任务。
    """
    try:
        agent = get_agent(request.user_id)
        response = agent.chat(request.message)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/document")
async def add_document(request: AddDocumentRequest):
    """
    添加文档到知识库

    将法律文档存入知识库，支持后续检索和分析。
    """
    try:
        agent = get_agent()
        count = agent.add_document(
            content=request.content,
            doc_id=request.doc_id,
            doc_type=request.doc_type,
            title=request.title,
        )
        return {"success": True, "chunks_added": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload")
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form("contract"),
    title: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None),
):
    """
    上传文档并分析

    支持 PDF、Word、TXT 等格式的文档上传和分析。
    """
    try:
        content = await file.read()

        suffix = file.filename.split(".")[-1].lower() if file.filename else "txt"

        if suffix == "pdf":
            from pypdf import PdfReader
            import io
            reader = PdfReader(io.BytesIO(content))
            text_content = "\n".join([page.extract_text() for page in reader.pages])
        elif suffix in ["docx", "doc"]:
            from docx import Document
            import io
            doc = Document(io.BytesIO(content))
            text_content = "\n".join([para.text for para in doc.paragraphs])
        else:
            text_content = content.decode("utf-8")

        agent = get_agent(user_id)
        result = agent.analyze_document(
            content=text_content,
            doc_type=doc_type,
            title=title or file.filename,
        )

        return AnalyzeResponse(
            document_title=result.document_title,
            doc_type=result.doc_type,
            risk_points=[
                {
                    "risk_type": rp.risk_type,
                    "description": rp.description,
                    "severity": rp.severity.value,
                    "location": rp.location,
                    "legal_basis": rp.legal_basis,
                    "suggestions": rp.suggestions,
                    "confidence": rp.confidence,
                }
                for rp in result.risk_points
            ],
            summary=result.summary,
            recommendations=result.recommendations,
            analyzed_at=result.analyzed_at,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """
    获取系统统计信息

    返回知识库中的文档数量、风险知识等统计信息。
    """
    try:
        agent = get_agent()
        stats = agent.get_stats()
        return StatsResponse(
            legal_documents=stats.get("legal_documents", {}),
            risk_knowledge=stats.get("risk_knowledge", {}),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/profile/{user_id}")
async def get_user_profile(user_id: str):
    """
    获取用户画像

    返回用户的偏好设置、常分析的文档类型等信息。
    """
    try:
        from memory import MemoryManager
        memory_manager = MemoryManager()
        profile = memory_manager.get_user_profile(user_id)
        return {
            "user_id": profile.user_id,
            "preferences": profile.preferences,
            "frequently_analyzed_doc_types": profile.frequently_analyzed_doc_types,
            "common_risk_concerns": profile.common_risk_concerns,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
