from typing import Any, Dict, List, Optional, Type

from langchain_core.callbacks import AsyncCallbackManagerForToolRun, CallbackManagerForToolRun
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from analyzer import LegalRiskAnalyzer, AnalysisResult
from config import Config
from knowledge_base import LegalKnowledgeBase
from memory import MemoryManager


class AnalyzeDocumentInput(BaseModel):
    """分析文档工具输入"""
    content: str = Field(description="文档内容")
    doc_type: str = Field(default="contract", description="文档类型，如 contract, law, regulation 等")
    title: str = Field(default="未命名文档", description="文档标题")


class SearchKnowledgeInput(BaseModel):
    """搜索知识库工具输入"""
    query: str = Field(description="搜索查询")
    n_results: int = Field(default=5, description="返回结果数量")
    doc_type: Optional[str] = Field(default=None, description="文档类型过滤")


class AddDocumentInput(BaseModel):
    """添加文档工具输入"""
    content: str = Field(description="文档内容")
    doc_id: str = Field(description="文档唯一标识")
    doc_type: str = Field(default="contract", description="文档类型")
    title: Optional[str] = Field(default=None, description="文档标题")


class AnswerQuestionInput(BaseModel):
    """回答问题工具输入"""
    query: str = Field(description="用户问题")
    doc_type: Optional[str] = Field(default=None, description="文档类型过滤")


class GetUserProfileInput(BaseModel):
    """获取用户画像工具输入"""
    user_id: str = Field(description="用户 ID")


class AnalyzeDocumentTool(BaseTool):
    """分析法律文档工具"""
    name: str = "analyze_document"
    description: str = "分析法律文档，识别风险点。输入文档内容和类型，返回风险分析结果。"
    args_schema: Type[BaseModel] = AnalyzeDocumentInput

    analyzer: LegalRiskAnalyzer = Field(default_factory=LegalRiskAnalyzer)
    user_id: Optional[str] = None

    def _run(
        self,
        content: str,
        doc_type: str = "contract",
        title: str = "未命名文档",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """执行文档分析"""
        result = self.analyzer.analyze_document(
            content=content,
            doc_type=doc_type,
            title=title,
            user_id=self.user_id,
        )

        output = f"## 文档分析结果\n\n"
        output += f"**文档标题**: {result.document_title}\n"
        output += f"**文档类型**: {result.doc_type}\n"
        output += f"**风险点数量**: {len(result.risk_points)}\n\n"

        if result.risk_points:
            output += "### 识别的风险点\n\n"
            for i, rp in enumerate(result.risk_points, 1):
                output += f"**风险 {i}**: {rp.risk_type}\n"
                output += f"- 严重程度: {rp.severity.value}\n"
                output += f"- 描述: {rp.description}\n"
                output += f"- 位置: {rp.location}\n"
                if rp.legal_basis:
                    output += f"- 法律依据: {rp.legal_basis}\n"
                if rp.suggestions:
                    output += f"- 建议: {rp.suggestions}\n"
                output += "\n"

        if result.summary:
            output += f"### 风险摘要\n\n{result.summary}\n\n"

        if result.recommendations:
            output += "### 总体建议\n\n"
            for rec in result.recommendations:
                output += f"- {rec}\n"

        return output


class SearchKnowledgeTool(BaseTool):
    """搜索知识库工具"""
    name: str = "search_knowledge"
    description: str = "搜索法律知识库。输入查询内容，返回相关的法律知识。"
    args_schema: Type[BaseModel] = SearchKnowledgeInput

    knowledge_base: LegalKnowledgeBase = Field(default_factory=LegalKnowledgeBase)

    def _run(
        self,
        query: str,
        n_results: int = 5,
        doc_type: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """执行知识库搜索"""
        results = self.knowledge_base.search(query, n_results, doc_type)

        if not results:
            return "未找到相关的法律知识。"

        output = "## 搜索结果\n\n"
        for i, r in enumerate(results, 1):
            output += f"**结果 {i}**\n"
            output += f"- 来源: {r['metadata'].get('source_file', '未知')}\n"
            output += f"- 类型: {r['metadata'].get('doc_type', '未知')}\n"
            output += f"- 内容: {r['content'][:500]}...\n\n"

        return output


class AddDocumentTool(BaseTool):
    """添加文档到知识库工具"""
    name: str = "add_document"
    description: str = "将法律文档添加到知识库。输入文档内容和元数据。"
    args_schema: Type[BaseModel] = AddDocumentInput

    knowledge_base: LegalKnowledgeBase = Field(default_factory=LegalKnowledgeBase)

    def _run(
        self,
        content: str,
        doc_id: str,
        doc_type: str = "contract",
        title: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """执行添加文档"""
        count = self.knowledge_base.add_text_content(
            content=content,
            doc_id=doc_id,
            doc_type=doc_type,
            title=title,
        )
        return f"成功添加文档，共 {count} 个文本块已存入知识库。"


class AnswerQuestionTool(BaseTool):
    """回答法律问题工具"""
    name: str = "answer_question"
    description: str = "回答法律相关问题。输入问题，返回专业解答。"
    args_schema: Type[BaseModel] = AnswerQuestionInput

    analyzer: LegalRiskAnalyzer = Field(default_factory=LegalRiskAnalyzer)
    user_id: Optional[str] = None

    def _run(
        self,
        query: str,
        doc_type: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """执行问题回答"""
        return self.analyzer.answer_question(
            query=query,
            user_id=self.user_id,
            doc_type=doc_type,
        )


class GetUserProfileTool(BaseTool):
    """获取用户画像工具"""
    name: str = "get_user_profile"
    description: str = "获取用户的画像和历史偏好信息。"
    args_schema: Type[BaseModel] = GetUserProfileInput

    memory_manager: MemoryManager = Field(default_factory=MemoryManager)

    def _run(
        self,
        user_id: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """执行获取用户画像"""
        profile = self.memory_manager.get_user_profile(user_id)

        output = f"## 用户画像\n\n"
        output += f"**用户 ID**: {profile.user_id}\n"

        if profile.preferences:
            output += f"**偏好设置**: {profile.preferences}\n"

        if profile.frequently_analyzed_doc_types:
            output += f"**常分析的文档类型**: {', '.join(profile.frequently_analyzed_doc_types)}\n"

        if profile.common_risk_concerns:
            output += f"**关注的风险类型**: {len(profile.common_risk_concerns)} 条记录\n"

        return output


class LegalRiskAgent:
    """
    法律风险分析 Agent
    基于 LangChain 框架整合所有模块
    """

    def __init__(self, user_id: Optional[str] = None):
        config = Config.get_llm_config()
        self.llm = ChatOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model_name,
            temperature=0.1,
        )

        self.user_id = user_id
        self.analyzer = LegalRiskAnalyzer()

        self.tools = [
            AnalyzeDocumentTool(analyzer=self.analyzer, user_id=user_id),
            SearchKnowledgeTool(),
            AddDocumentTool(),
            AnswerQuestionTool(analyzer=self.analyzer, user_id=user_id),
            GetUserProfileTool(),
        ]

        self.llm_with_tools = self.llm.bind_tools(self.tools)

        self.system_prompt = """你是一位专业的法律风险分析助手。你可以帮助用户：

1. **分析法律文档**：识别合同、法规等文档中的风险点
2. **搜索法律知识**：从知识库中检索相关法律知识
3. **添加文档到知识库**：将新的法律文档存入知识库
4. **回答法律问题**：提供专业的法律咨询
5. **查看用户画像**：了解用户的偏好和历史记录

请根据用户的需求，选择合适的工具来完成任务。回答时请使用中文，保持专业和准确。"""

    def chat(self, message: str) -> str:
        """
        与 Agent 对话

        Args:
            message: 用户消息

        Returns:
            Agent 回复
        """
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=message),
        ]

        response = self.llm_with_tools.invoke(messages)

        if response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                for tool in self.tools:
                    if tool.name == tool_name:
                        try:
                            tool_result = tool._run(**tool_args)
                            messages.append(response)
                            messages.append(HumanMessage(content=tool_result))
                        except Exception as e:
                            messages.append(HumanMessage(content=f"工具执行错误: {str(e)}"))
                        break

            final_response = self.llm.invoke(messages)
            return final_response.content

        return response.content

    def analyze_document(
        self,
        content: str,
        doc_type: str = "contract",
        title: str = "未命名文档",
    ) -> AnalysisResult:
        """
        直接分析文档

        Args:
            content: 文档内容
            doc_type: 文档类型
            title: 文档标题

        Returns:
            分析结果
        """
        return self.analyzer.analyze_document(
            content=content,
            doc_type=doc_type,
            title=title,
            user_id=self.user_id,
        )

    def answer_question(self, query: str, doc_type: Optional[str] = None) -> str:
        """
        回答法律问题

        Args:
            query: 用户问题
            doc_type: 文档类型过滤

        Returns:
            回答内容
        """
        return self.analyzer.answer_question(
            query=query,
            user_id=self.user_id,
            doc_type=doc_type,
        )

    def add_document(
        self,
        content: str,
        doc_id: str,
        doc_type: str = "contract",
        title: Optional[str] = None,
    ) -> int:
        """
        添加文档到知识库

        Args:
            content: 文档内容
            doc_id: 文档 ID
            doc_type: 文档类型
            title: 文档标题

        Returns:
            添加的文档块数量
        """
        return self.analyzer.add_text_to_knowledge_base(
            content=content,
            doc_id=doc_id,
            doc_type=doc_type,
            title=title,
        )

    def get_stats(self) -> Dict[str, Any]:
        """
        获取系统统计信息

        Returns:
            统计信息
        """
        return self.analyzer.get_stats()
