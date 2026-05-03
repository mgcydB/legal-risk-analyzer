import streamlit as st
import httpx
from typing import Optional
import time

API_BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="法律文件风险点分析系统",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A5F;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #2C5282;
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
    .risk-card {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .risk-critical {
        background-color: #FED7D7;
        border-left: 4px solid #E53E3E;
    }
    .risk-high {
        background-color: #FEEBC8;
        border-left: 4px solid #DD6B20;
    }
    .risk-medium {
        background-color: #FEFCBF;
        border-left: 4px solid #D69E2E;
    }
    .risk-low {
        background-color: #C6F6D5;
        border-left: 4px solid #38A169;
    }
    .stTextArea textarea {
        font-family: monospace;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    if "user_id" not in st.session_state:
        st.session_state.user_id = "default_user"
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None


def api_request(method: str, endpoint: str, data: Optional[dict] = None, files: Optional[dict] = None):
    try:
        url = f"{API_BASE_URL}{endpoint}"
        if method == "GET":
            response = httpx.get(url)
        elif method == "POST":
            if files:
                response = httpx.post(url, data=data, files=files)
            else:
                response = httpx.post(url, json=data)
        else:
            return None

        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API 错误: {response.text}")
            return None
    except Exception as e:
        st.error(f"连接错误: {str(e)}")
        return None


def render_sidebar():
    with st.sidebar:
        st.markdown("### ⚙️ 系统设置")
        
        user_id = st.text_input(
            "用户 ID",
            value=st.session_state.user_id,
            key="user_id_input",
        )
        if user_id != st.session_state.user_id:
            st.session_state.user_id = user_id
            st.session_state.chat_history = []
        
        st.markdown("---")
        
        st.markdown("### 📊 系统状态")
        if st.button("刷新统计信息"):
            stats = api_request("GET", "/api/stats")
            if stats:
                st.json(stats)
        
        st.markdown("---")
        
        st.markdown("### 📖 使用说明")
        st.markdown("""
        1. **文档分析**: 上传或粘贴法律文档，系统将自动识别风险点
        2. **智能问答**: 输入法律问题，获取专业解答
        3. **知识库管理**: 添加法律文档到知识库
        4. **Agent 对话**: 自然语言交互，自动选择合适工具
        """)


def render_document_analysis():
    st.markdown('<p class="sub-header">📄 文档分析</p>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["粘贴文本", "上传文件"])
    
    with tab1:
        doc_content = st.text_area(
            "文档内容",
            height=300,
            placeholder="请粘贴法律文档内容...",
        )
        
        col1, col2, col3 = st.columns(3)
        with col1:
            doc_type = st.selectbox(
                "文档类型",
                ["contract", "law", "regulation", "judgment", "other"],
                format_func=lambda x: {
                    "contract": "合同",
                    "law": "法律",
                    "regulation": "法规",
                    "judgment": "判决书",
                    "other": "其他",
                }.get(x, x),
            )
        with col2:
            doc_title = st.text_input("文档标题", value="未命名文档")
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            analyze_btn = st.button("🔍 开始分析", type="primary", use_container_width=True)
        
        if analyze_btn and doc_content:
            with st.spinner("正在分析文档..."):
                result = api_request("POST", "/api/analyze", {
                    "content": doc_content,
                    "doc_type": doc_type,
                    "title": doc_title,
                    "user_id": st.session_state.user_id,
                })
                
                if result:
                    st.session_state.analysis_result = result
                    st.success("分析完成！")
    
    with tab2:
        uploaded_file = st.file_uploader(
            "上传文档",
            type=["pdf", "docx", "doc", "txt"],
        )
        
        col1, col2 = st.columns(2)
        with col1:
            upload_doc_type = st.selectbox(
                "文档类型",
                ["contract", "law", "regulation", "judgment", "other"],
                key="upload_doc_type",
            )
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            upload_btn = st.button("📤 上传并分析", type="primary", use_container_width=True)
        
        if upload_btn and uploaded_file:
            with st.spinner("正在上传和分析..."):
                files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
                data = {
                    "doc_type": upload_doc_type,
                    "user_id": st.session_state.user_id,
                }
                result = api_request("POST", "/api/upload", data=data, files=files)
                
                if result:
                    st.session_state.analysis_result = result
                    st.success("分析完成！")


def render_analysis_result():
    if not st.session_state.analysis_result:
        return
    
    result = st.session_state.analysis_result
    
    st.markdown('<p class="sub-header">📋 分析结果</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("文档标题", result.get("document_title", "-"))
    with col2:
        st.metric("文档类型", result.get("doc_type", "-"))
    with col3:
        st.metric("风险点数量", len(result.get("risk_points", [])))
    
    st.markdown("---")
    
    risk_points = result.get("risk_points", [])
    if risk_points:
        st.markdown("### ⚠️ 识别的风险点")
        
        for i, rp in enumerate(risk_points, 1):
            severity = rp.get("severity", "medium")
            severity_class = f"risk-{severity}"
            severity_label = {
                "critical": "🔴 严重",
                "high": "🟠 高",
                "medium": "🟡 中",
                "low": "🟢 低",
            }.get(severity, severity)
            
            st.markdown(f"""
            <div class="risk-card {severity_class}">
                <h4>风险 {i}: {rp.get('risk_type', '未知风险')} ({severity_label})</h4>
                <p><strong>描述:</strong> {rp.get('description', '-')}</p>
                <p><strong>位置:</strong> {rp.get('location', '-')}</p>
                {f'<p><strong>法律依据:</strong> {rp.get("legal_basis", "-")}</p>' if rp.get('legal_basis') else ''}
                {f'<p><strong>建议:</strong> {rp.get("suggestions", "-")}</p>' if rp.get('suggestions') else ''}
            </div>
            """, unsafe_allow_html=True)
    
    if result.get("summary"):
        st.markdown("### 📝 风险摘要")
        st.info(result["summary"])
    
    if result.get("recommendations"):
        st.markdown("### 💡 总体建议")
        for rec in result["recommendations"]:
            st.markdown(f"- {rec}")


def render_qa():
    st.markdown('<p class="sub-header">💬 智能问答</p>', unsafe_allow_html=True)
    
    question = st.text_input(
        "输入您的法律问题",
        placeholder="例如：合同中违约责任条款如何约定？",
    )
    
    col1, col2 = st.columns([3, 1])
    with col1:
        qa_doc_type = st.selectbox(
            "文档类型过滤（可选）",
            [None, "contract", "law", "regulation", "judgment"],
            format_func=lambda x: {
                None: "全部",
                "contract": "合同",
                "law": "法律",
                "regulation": "法规",
                "judgment": "判决书",
            }.get(x, x),
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        ask_btn = st.button("❓ 提问", type="primary", use_container_width=True)
    
    if ask_btn and question:
        with st.spinner("正在思考..."):
            result = api_request("POST", "/api/question", {
                "query": question,
                "user_id": st.session_state.user_id,
                "doc_type": qa_doc_type,
            })
            
            if result:
                st.markdown("### 📖 回答")
                st.markdown(result.get("answer", "无法获取回答"))


def render_agent_chat():
    st.markdown('<p class="sub-header">🤖 Agent 对话</p>', unsafe_allow_html=True)
    
    chat_container = st.container()
    
    with chat_container:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
    
    user_input = st.chat_input("输入消息...")
    
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        
        with st.chat_message("user"):
            st.markdown(user_input)
        
        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                result = api_request("POST", "/api/chat", {
                    "message": user_input,
                    "user_id": st.session_state.user_id,
                })
                
                if result:
                    response = result.get("response", "抱歉，我无法处理您的请求。")
                    st.markdown(response)
                    st.session_state.chat_history.append({"role": "assistant", "content": response})


def render_knowledge_base():
    st.markdown('<p class="sub-header">📚 知识库管理</p>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["添加文档", "查看统计"])
    
    with tab1:
        kb_content = st.text_area(
            "文档内容",
            height=200,
            placeholder="输入要添加到知识库的法律文档内容...",
        )
        
        col1, col2, col3 = st.columns(3)
        with col1:
            kb_doc_id = st.text_input("文档 ID", value=f"doc_{int(time.time())}")
        with col2:
            kb_doc_type = st.selectbox(
                "文档类型",
                ["contract", "law", "regulation", "judgment"],
                key="kb_doc_type",
            )
        with col3:
            kb_title = st.text_input("文档标题", value="未命名文档")
        
        if st.button("➕ 添加到知识库", type="primary"):
            if kb_content:
                result = api_request("POST", "/api/document", {
                    "content": kb_content,
                    "doc_id": kb_doc_id,
                    "doc_type": kb_doc_type,
                    "title": kb_title,
                })
                
                if result:
                    st.success(f"成功添加 {result.get('chunks_added', 0)} 个文本块到知识库！")
            else:
                st.warning("请输入文档内容")
    
    with tab2:
        if st.button("🔄 刷新统计"):
            stats = api_request("GET", "/api/stats")
            if stats:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(
                        "法律文档块数",
                        stats.get("legal_documents", {}).get("total_chunks", 0),
                    )
                    st.metric(
                        "唯一文件数",
                        stats.get("legal_documents", {}).get("unique_files", 0),
                    )
                with col2:
                    st.metric(
                        "风险知识条数",
                        stats.get("risk_knowledge", {}).get("total_items", 0),
                    )
                    risk_types = stats.get("risk_knowledge", {}).get("risk_types", [])
                    if risk_types:
                        st.write("风险类型:", ", ".join(risk_types))


def main():
    init_session_state()
    
    st.markdown('<h1 class="main-header">⚖️ 法律文件风险点分析系统</h1>', unsafe_allow_html=True)
    
    render_sidebar()
    
    tab1, tab2, tab3, tab4 = st.tabs(["📄 文档分析", "💬 智能问答", "🤖 Agent 对话", "📚 知识库"])
    
    with tab1:
        render_document_analysis()
        st.markdown("---")
        render_analysis_result()
    
    with tab2:
        render_qa()
    
    with tab3:
        render_agent_chat()
    
    with tab4:
        render_knowledge_base()


if __name__ == "__main__":
    main()
