import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pypdf import PdfReader
from docx import Document

from database.seekdb_client import get_or_create_legal_collection, get_seekdb_client
from config import Config


@dataclass
class LegalDocument:
    """法律文档数据结构"""
    id: str
    title: str
    content: str
    doc_type: str
    source_file: str
    chunk_index: int
    metadata: Dict[str, Any]
    created_at: str


class LegalDocumentStore:
    """
    法律文档存储和检索模块
    使用 SeekDB 存储和检索法律文件
    """

    def __init__(self):
        self.client = get_seekdb_client()
        config = Config.get_legal_analyzer_config()
        self.legal_collection = get_or_create_legal_collection(
            self.client, config.legal_collection_name
        )
        self.risk_collection = get_or_create_legal_collection(
            self.client, config.risk_collection_name
        )

    def parse_pdf(self, file_path: str) -> List[str]:
        """解析 PDF 文件"""
        reader = PdfReader(file_path)
        texts = []
        for page in reader.pages:
            text = page.extract_text()
            if text.strip():
                texts.append(text.strip())
        return texts

    def parse_docx(self, file_path: str) -> List[str]:
        """解析 Word 文件"""
        doc = Document(file_path)
        texts = []
        for para in doc.paragraphs:
            if para.text.strip():
                texts.append(para.text.strip())
        return texts

    def parse_txt(self, file_path: str) -> List[str]:
        """解析文本文件"""
        with open(file_path, "r", encoding="utf-8") as f:
            return [f.read().strip()]

    def parse_document(self, file_path: str) -> List[str]:
        """根据文件类型解析文档"""
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            return self.parse_pdf(file_path)
        elif suffix in [".docx", ".doc"]:
            return self.parse_docx(file_path)
        elif suffix == ".txt":
            return self.parse_txt(file_path)
        else:
            raise ValueError(f"Unsupported file type: {suffix}")

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        将文本切分成块

        Args:
            text: 原始文本
            chunk_size: 每块大小
            overlap: 重叠大小

        Returns:
            文本块列表
        """
        sentences = re.split(r"[。！？\n]", text)
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if not sentence.strip():
                continue

            if len(current_chunk) + len(sentence) > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += sentence + "。"

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def add_document(
        self,
        file_path: str,
        doc_type: str = "contract",
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        添加法律文档到知识库

        Args:
            file_path: 文件路径
            doc_type: 文档类型 (contract, law, regulation, judgment, etc.)
            title: 文档标题
            metadata: 额外元数据

        Returns:
            添加的文档块数量
        """
        path = Path(file_path)
        if title is None:
            title = path.stem

        texts = self.parse_document(file_path)
        all_chunks = []

        for text in texts:
            chunks = self.chunk_text(text)
            all_chunks.extend(chunks)

        ids = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(all_chunks):
            chunk_id = f"{path.stem}_{i}"
            ids.append(chunk_id)
            documents.append(chunk)
            metadatas.append({
                "source_file": path.name,
                "chunk_index": i,
                "doc_type": doc_type,
                "title": title,
                "created_at": datetime.now().isoformat(),
                **(metadata or {}),
            })

        self.legal_collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

        print(f"Added {len(ids)} chunks from {file_path}")
        return len(ids)

    def add_text(
        self,
        text: str,
        doc_id: str,
        doc_type: str = "contract",
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        直接添加文本内容

        Args:
            text: 文本内容
            doc_id: 文档 ID
            doc_type: 文档类型
            title: 文档标题
            metadata: 额外元数据

        Returns:
            添加的文档块数量
        """
        chunks = self.chunk_text(text)
        ids = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_{i}"
            ids.append(chunk_id)
            documents.append(chunk)
            metadatas.append({
                "source_file": doc_id,
                "chunk_index": i,
                "doc_type": doc_type,
                "title": title or doc_id,
                "created_at": datetime.now().isoformat(),
                **(metadata or {}),
            })

        self.legal_collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

        print(f"Added {len(ids)} chunks for document {doc_id}")
        return len(ids)

    def search(
        self,
        query: str,
        n_results: int = 5,
        doc_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        语义搜索法律文档

        Args:
            query: 查询文本
            n_results: 返回结果数量
            doc_type: 过滤文档类型

        Returns:
            搜索结果列表
        """
        where = None
        if doc_type:
            where = {"doc_type": doc_type}

        results = self.legal_collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        search_results = []
        if results and results.get("ids"):
            for i, doc_id in enumerate(results["ids"][0]):
                search_results.append({
                    "id": doc_id,
                    "content": results["documents"][0][i] if results.get("documents") else "",
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                    "distance": results["distances"][0][i] if results.get("distances") else 0,
                })

        return search_results

    def add_risk_knowledge(
        self,
        risk_type: str,
        description: str,
        legal_basis: str,
        severity: str = "medium",
        suggestions: Optional[str] = None,
    ):
        """
        添加风险知识到知识库

        Args:
            risk_type: 风险类型
            description: 风险描述
            legal_basis: 法律依据
            severity: 严重程度 (low, medium, high, critical)
            suggestions: 建议措施
        """
        risk_id = f"risk_{risk_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        content = f"风险类型: {risk_type}\n描述: {description}\n法律依据: {legal_basis}"
        if suggestions:
            content += f"\n建议措施: {suggestions}"

        self.risk_collection.add(
            ids=[risk_id],
            documents=[content],
            metadatas=[{
                "risk_type": risk_type,
                "severity": severity,
                "legal_basis": legal_basis,
                "created_at": datetime.now().isoformat(),
            }],
        )

    def search_risk_knowledge(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        搜索风险知识

        Args:
            query: 查询文本
            n_results: 返回结果数量

        Returns:
            搜索结果列表
        """
        results = self.risk_collection.query(
            query_texts=[query],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

        search_results = []
        if results and results.get("ids"):
            for i, doc_id in enumerate(results["ids"][0]):
                search_results.append({
                    "id": doc_id,
                    "content": results["documents"][0][i] if results.get("documents") else "",
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                    "distance": results["distances"][0][i] if results.get("distances") else 0,
                })

        return search_results

    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        legal_results = self.legal_collection.get(limit=10000, include=["metadatas"])
        risk_results = self.risk_collection.get(limit=10000, include=["metadatas"])

        legal_metadatas = legal_results.get("metadatas", []) if isinstance(legal_results, dict) else []
        risk_metadatas = risk_results.get("metadatas", []) if isinstance(risk_results, dict) else []

        unique_legal_files = {m.get("source_file") for m in legal_metadatas if m and m.get("source_file")}
        risk_types = {m.get("risk_type") for m in risk_metadatas if m and m.get("risk_type")}

        return {
            "legal_documents": {
                "total_chunks": len(legal_metadatas),
                "unique_files": len(unique_legal_files),
            },
            "risk_knowledge": {
                "total_items": len(risk_metadatas),
                "risk_types": list(risk_types),
            },
        }
