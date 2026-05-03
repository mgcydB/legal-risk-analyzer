import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import Config
from database import LegalDocumentStore


@dataclass
class UserMemory:
    """用户记忆数据结构"""
    user_id: str
    memory_type: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class UserProfile:
    """用户画像"""
    user_id: str
    preferences: Dict[str, Any] = field(default_factory=dict)
    frequently_analyzed_doc_types: List[str] = field(default_factory=list)
    common_risk_concerns: List[str] = field(default_factory=list)
    analysis_history: List[Dict[str, Any]] = field(default_factory=list)


class MemoryManager:
    """
    用户记忆管理模块
    基于 PowerMem 理念实现：
    - 记住用户上次问了什么
    - 记住用户的偏好和习惯
    - 在有限 token 下，精准投放最相关的历史信息
    """

    def __init__(self):
        self.doc_store = LegalDocumentStore()
        self.config = Config.get_powermem_config()
        self._memory_cache: Dict[str, List[UserMemory]] = {}
        self._profile_cache: Dict[str, UserProfile] = {}

    def _get_memory_collection_name(self, user_id: str) -> str:
        """获取用户记忆 Collection 名称"""
        return f"{self.config.collection_name}_{user_id}"

    def add_memory(
        self,
        user_id: str,
        memory_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        添加用户记忆

        Args:
            user_id: 用户 ID
            memory_type: 记忆类型 (query, preference, analysis, feedback)
            content: 记忆内容
            metadata: 额外元数据
        """
        memory = UserMemory(
            user_id=user_id,
            memory_type=memory_type,
            content=content,
            metadata=metadata or {},
        )

        if user_id not in self._memory_cache:
            self._memory_cache[user_id] = []
        self._memory_cache[user_id].append(memory)

        memory_id = f"memory_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        self.doc_store.legal_collection.add(
            ids=[memory_id],
            documents=[content],
            metadatas=[{
                "user_id": user_id,
                "memory_type": memory_type,
                "created_at": memory.created_at,
                **(metadata or {}),
            }],
        )

    def add_query_memory(self, user_id: str, query: str, doc_type: Optional[str] = None):
        """
        添加查询记忆

        Args:
            user_id: 用户 ID
            query: 查询内容
            doc_type: 文档类型
        """
        self.add_memory(
            user_id=user_id,
            memory_type="query",
            content=query,
            metadata={"doc_type": doc_type} if doc_type else {},
        )

    def add_analysis_memory(
        self,
        user_id: str,
        document_title: str,
        risk_summary: str,
        doc_type: str,
    ):
        """
        添加分析记忆

        Args:
            user_id: 用户 ID
            document_title: 文档标题
            risk_summary: 风险摘要
            doc_type: 文档类型
        """
        content = f"分析了文档《{document_title}》，发现风险：{risk_summary}"
        self.add_memory(
            user_id=user_id,
            memory_type="analysis",
            content=content,
            metadata={
                "document_title": document_title,
                "doc_type": doc_type,
            },
        )

    def add_preference_memory(self, user_id: str, preference: str, value: Any):
        """
        添加偏好记忆

        Args:
            user_id: 用户 ID
            preference: 偏好名称
            value: 偏好值
        """
        content = f"用户偏好：{preference} = {value}"
        self.add_memory(
            user_id=user_id,
            memory_type="preference",
            content=content,
            metadata={
                "preference_key": preference,
                "preference_value": str(value),
            },
        )

    def search_memories(
        self,
        user_id: str,
        query: str,
        n_results: int = 5,
        memory_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        搜索用户记忆

        Args:
            user_id: 用户 ID
            query: 查询文本
            n_results: 返回结果数量
            memory_type: 过滤记忆类型

        Returns:
            搜索结果列表
        """
        where = {"user_id": user_id}
        if memory_type:
            where["memory_type"] = memory_type

        results = self.doc_store.legal_collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        memories = []
        if results and results.get("ids"):
            for i, doc_id in enumerate(results["ids"][0]):
                memories.append({
                    "id": doc_id,
                    "content": results["documents"][0][i] if results.get("documents") else "",
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                    "distance": results["distances"][0][i] if results.get("distances") else 0,
                })

        return memories

    def get_recent_memories(self, user_id: str, limit: int = 10) -> List[UserMemory]:
        """
        获取用户最近的记忆

        Args:
            user_id: 用户 ID
            limit: 返回数量

        Returns:
            记忆列表
        """
        if user_id in self._memory_cache:
            return self._memory_cache[user_id][-limit:]
        return []

    def get_user_profile(self, user_id: str) -> UserProfile:
        """
        获取用户画像

        Args:
            user_id: 用户 ID

        Returns:
            用户画像
        """
        if user_id not in self._profile_cache:
            self._profile_cache[user_id] = UserProfile(user_id=user_id)
            self._update_user_profile(user_id)

        return self._profile_cache[user_id]

    def _update_user_profile(self, user_id: str):
        """
        更新用户画像

        Args:
            user_id: 用户 ID
        """
        memories = self.get_recent_memories(user_id, limit=100)
        profile = self._profile_cache.get(user_id, UserProfile(user_id=user_id))

        doc_types = {}
        risk_concerns = []

        for memory in memories:
            if memory.memory_type == "analysis":
                doc_type = memory.metadata.get("doc_type")
                if doc_type:
                    doc_types[doc_type] = doc_types.get(doc_type, 0) + 1

                if "风险" in memory.content:
                    risk_concerns.append(memory.content)

            elif memory.memory_type == "preference":
                key = memory.metadata.get("preference_key")
                value = memory.metadata.get("preference_value")
                if key and value:
                    profile.preferences[key] = value

        profile.frequently_analyzed_doc_types = sorted(
            doc_types.keys(), key=lambda x: doc_types[x], reverse=True
        )[:5]
        profile.common_risk_concerns = risk_concerns[:10]

    def get_context_for_analysis(self, user_id: str, query: str) -> str:
        """
        获取分析上下文
        在有限 token 下，精准投放最相关的历史信息

        Args:
            user_id: 用户 ID
            query: 当前查询

        Returns:
            上下文字符串
        """
        profile = self.get_user_profile(user_id)
        relevant_memories = self.search_memories(user_id, query, n_results=3)

        context_parts = []

        if profile.preferences:
            context_parts.append(f"用户偏好：{json.dumps(profile.preferences, ensure_ascii=False)}")

        if profile.frequently_analyzed_doc_types:
            context_parts.append(f"常分析的文档类型：{', '.join(profile.frequently_analyzed_doc_types)}")

        if relevant_memories:
            context_parts.append("相关历史记录：")
            for mem in relevant_memories[:3]:
                context_parts.append(f"  - {mem['content'][:100]}...")

        return "\n".join(context_parts)

    def clear_user_memories(self, user_id: str):
        """
        清除用户记忆

        Args:
            user_id: 用户 ID
        """
        if user_id in self._memory_cache:
            del self._memory_cache[user_id]
        if user_id in self._profile_cache:
            del self._profile_cache[user_id]
