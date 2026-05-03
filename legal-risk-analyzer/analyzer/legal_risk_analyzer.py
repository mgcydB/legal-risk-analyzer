import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from config import Config
from knowledge_base import LegalKnowledgeBase
from memory import MemoryManager


class RiskSeverity(str, Enum):
    """风险严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskPoint:
    """风险点数据结构"""
    risk_type: str
    description: str
    severity: RiskSeverity
    location: str
    legal_basis: str
    suggestions: str
    confidence: float = 0.8


@dataclass
class AnalysisResult:
    """分析结果"""
    document_title: str
    doc_type: str
    risk_points: List[RiskPoint]
    summary: str
    recommendations: List[str]
    analyzed_at: str = field(default_factory=lambda: datetime.now().isoformat())


RISK_ANALYSIS_PROMPT = """你是一位专业的法律风险评估专家。请分析以下法律文档，识别其中的风险点。

文档类型：{doc_type}
文档标题：{title}

文档内容：
{content}

{context}

请按照以下格式输出分析结果（JSON格式）：
{{
    "risk_points": [
        {{
            "risk_type": "风险类型",
            "description": "风险描述",
            "severity": "low/medium/high/critical",
            "location": "风险所在位置（原文引用）",
            "legal_basis": "相关法律依据",
            "suggestions": "修改建议"
        }}
    ],
    "summary": "整体风险评估摘要",
    "recommendations": ["建议1", "建议2"]
}}

请确保：
1. 识别所有潜在的法律风险点
2. 评估每个风险的严重程度
3. 提供具体的法律依据
4. 给出可行的修改建议
"""

LEGAL_QA_PROMPT = """你是一位专业的法律顾问。请根据以下信息回答用户的问题。

用户问题：{query}

相关法律知识：
{legal_knowledge}

{context}

请提供专业、准确的回答，并在必要时引用相关法律条文。
"""


class LegalRiskAnalyzer:
    """
    法律风险点分析核心模块
    整合 SeekDB、PowerRAG 和 PowerMem 的能力
    """

    def __init__(self):
        config = Config.get_llm_config()
        self.llm = ChatOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model_name,
            temperature=0.1,
        )

        self.knowledge_base = LegalKnowledgeBase()
        self.memory_manager = MemoryManager()

    def analyze_document(
        self,
        content: str,
        doc_type: str = "contract",
        title: str = "未命名文档",
        user_id: Optional[str] = None,
    ) -> AnalysisResult:
        """
        分析法律文档，识别风险点

        Args:
            content: 文档内容
            doc_type: 文档类型
            title: 文档标题
            user_id: 用户 ID（用于记忆管理）

        Returns:
            分析结果
        """
        context = ""
        if user_id:
            context = self.memory_manager.get_context_for_analysis(user_id, f"分析{doc_type}风险")

        pattern_risks = self.knowledge_base.detect_risks_by_patterns(content)

        relevant_laws = self.knowledge_base.search(f"{doc_type} 法律风险", n_results=3)
        legal_knowledge = "\n".join([law["content"] for law in relevant_laws])

        prompt = RISK_ANALYSIS_PROMPT.format(
            doc_type=doc_type,
            title=title,
            content=content[:4000],
            context=f"\n用户上下文：{context}\n" if context else "",
        )

        response = self.llm.invoke([
            SystemMessage(content="你是一位专业的法律风险评估专家，请用中文回答。"),
            HumanMessage(content=prompt),
        ])

        try:
            result_text = response.content
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]

            result_json = json.loads(result_text.strip())
        except (json.JSONDecodeError, IndexError):
            result_json = {
                "risk_points": [],
                "summary": response.content,
                "recommendations": [],
            }

        risk_points = []
        for rp in result_json.get("risk_points", []):
            severity = RiskSeverity.MEDIUM
            if rp.get("severity", "").lower() in ["low", "medium", "high", "critical"]:
                severity = RiskSeverity(rp["severity"].lower())

            risk_points.append(RiskPoint(
                risk_type=rp.get("risk_type", "未知风险"),
                description=rp.get("description", ""),
                severity=severity,
                location=rp.get("location", ""),
                legal_basis=rp.get("legal_basis", ""),
                suggestions=rp.get("suggestions", ""),
            ))

        for pr in pattern_risks:
            risk_points.append(RiskPoint(
                risk_type=pr["risk_type"],
                description=f"检测到潜在风险：{pr['matched_text']}",
                severity=RiskSeverity.MEDIUM,
                location=pr["context"],
                legal_basis="",
                suggestions="建议进一步审查相关条款",
                confidence=0.7,
            ))

        analysis_result = AnalysisResult(
            document_title=title,
            doc_type=doc_type,
            risk_points=risk_points,
            summary=result_json.get("summary", ""),
            recommendations=result_json.get("recommendations", []),
        )

        if user_id:
            risk_summary = f"共发现 {len(risk_points)} 个风险点"
            self.memory_manager.add_analysis_memory(
                user_id=user_id,
                document_title=title,
                risk_summary=risk_summary,
                doc_type=doc_type,
            )

        return analysis_result

    def analyze_file(
        self,
        file_path: str,
        doc_type: str = "contract",
        title: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> AnalysisResult:
        """
        分析法律文件

        Args:
            file_path: 文件路径
            doc_type: 文档类型
            title: 文档标题
            user_id: 用户 ID

        Returns:
            分析结果
        """
        parsed = self.knowledge_base.parse_document(file_path)

        doc_title = title or parsed.metadata.get("source_file", "未命名文档")

        return self.analyze_document(
            content=parsed.content,
            doc_type=doc_type,
            title=doc_title,
            user_id=user_id,
        )

    def answer_question(
        self,
        query: str,
        user_id: Optional[str] = None,
        doc_type: Optional[str] = None,
    ) -> str:
        """
        回答法律问题

        Args:
            query: 用户问题
            user_id: 用户 ID
            doc_type: 文档类型过滤

        Returns:
            回答内容
        """
        legal_knowledge_results = self.knowledge_base.search(
            query, n_results=5, doc_type=doc_type
        )
        legal_knowledge = "\n\n".join([
            f"【{r['metadata'].get('title', '相关法律知识')}】\n{r['content']}"
            for r in legal_knowledge_results
        ])

        context = ""
        if user_id:
            context = self.memory_manager.get_context_for_analysis(user_id, query)
            self.memory_manager.add_query_memory(user_id, query, doc_type)

        prompt = LEGAL_QA_PROMPT.format(
            query=query,
            legal_knowledge=legal_knowledge[:3000],
            context=f"\n用户上下文：{context}\n" if context else "",
        )

        response = self.llm.invoke([
            SystemMessage(content="你是一位专业的法律顾问，请用中文回答。"),
            HumanMessage(content=prompt),
        ])

        return response.content

    def add_document_to_knowledge_base(
        self,
        file_path: str,
        doc_type: str = "contract",
        title: Optional[str] = None,
    ) -> int:
        """
        添加文档到知识库

        Args:
            file_path: 文件路径
            doc_type: 文档类型
            title: 文档标题

        Returns:
            添加的文档块数量
        """
        return self.knowledge_base.add_document(
            file_path=file_path,
            doc_type=doc_type,
            title=title,
        )

    def add_text_to_knowledge_base(
        self,
        content: str,
        doc_id: str,
        doc_type: str = "contract",
        title: Optional[str] = None,
    ) -> int:
        """
        添加文本到知识库

        Args:
            content: 文本内容
            doc_id: 文档 ID
            doc_type: 文档类型
            title: 文档标题

        Returns:
            添加的文档块数量
        """
        return self.knowledge_base.add_text_content(
            content=content,
            doc_id=doc_id,
            doc_type=doc_type,
            title=title,
        )

    def add_risk_knowledge(
        self,
        risk_type: str,
        description: str,
        legal_basis: str,
        severity: str = "medium",
        suggestions: Optional[str] = None,
    ):
        """
        添加风险知识

        Args:
            risk_type: 风险类型
            description: 风险描述
            legal_basis: 法律依据
            severity: 严重程度
            suggestions: 建议措施
        """
        self.knowledge_base.add_risk_knowledge(
            risk_type=risk_type,
            description=description,
            legal_basis=legal_basis,
            severity=severity,
            suggestions=suggestions,
        )

    def get_user_profile(self, user_id: str):
        """
        获取用户画像

        Args:
            user_id: 用户 ID

        Returns:
            用户画像
        """
        return self.memory_manager.get_user_profile(user_id)

    def get_stats(self) -> Dict[str, Any]:
        """
        获取系统统计信息

        Returns:
            统计信息
        """
        return self.knowledge_base.get_stats()
