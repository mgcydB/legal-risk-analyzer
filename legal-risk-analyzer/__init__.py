"""
法律文件风险点分析系统
基于 SeekDB、PowerRAG 和 PowerMem 构建
"""

from agent import LegalRiskAgent
from analyzer import LegalRiskAnalyzer, AnalysisResult, RiskPoint, RiskSeverity
from database import LegalDocumentStore
from knowledge_base import LegalKnowledgeBase
from memory import MemoryManager

__version__ = "0.1.0"

__all__ = [
    "LegalRiskAgent",
    "LegalRiskAnalyzer",
    "AnalysisResult",
    "RiskPoint",
    "RiskSeverity",
    "LegalDocumentStore",
    "LegalKnowledgeBase",
    "MemoryManager",
]
