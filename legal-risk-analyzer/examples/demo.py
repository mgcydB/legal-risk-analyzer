"""
法律文件风险点分析系统 - 示例代码

本示例演示如何使用系统进行法律文档风险分析
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import LegalRiskAgent
from analyzer import LegalRiskAnalyzer


def example_analyze_document():
    """示例：分析法律文档"""
    print("=" * 60)
    print("示例 1: 分析法律文档")
    print("=" * 60)
    
    sample_contract = """
    甲方：ABC科技有限公司
    乙方：XYZ咨询公司
    
    技术服务合同
    
    第一条 服务内容
    甲方委托乙方提供技术咨询服务，服务期限为一年。
    
    第二条 服务费用
    甲方应向乙方支付服务费用人民币50万元，于合同签订后三日内支付。
    
    第三条 违约责任
    乙方未按约定提供服务的，应退还全部服务费用。
    
    第四条 争议解决
    本合同发生争议时，双方应友好协商解决。
    """
    
    analyzer = LegalRiskAnalyzer()
    
    result = analyzer.analyze_document(
        content=sample_contract,
        doc_type="contract",
        title="技术服务合同示例",
        user_id="demo_user",
    )
    
    print(f"\n文档标题: {result.document_title}")
    print(f"文档类型: {result.doc_type}")
    print(f"风险点数量: {len(result.risk_points)}")
    
    print("\n识别的风险点:")
    for i, rp in enumerate(result.risk_points, 1):
        print(f"\n风险 {i}: {rp.risk_type}")
        print(f"  严重程度: {rp.severity.value}")
        print(f"  描述: {rp.description}")
        if rp.legal_basis:
            print(f"  法律依据: {rp.legal_basis}")
        if rp.suggestions:
            print(f"  建议: {rp.suggestions}")
    
    print(f"\n风险摘要: {result.summary}")
    print(f"\n总体建议: {result.recommendations}")


def example_answer_question():
    """示例：回答法律问题"""
    print("\n" + "=" * 60)
    print("示例 2: 回答法律问题")
    print("=" * 60)
    
    analyzer = LegalRiskAnalyzer()
    
    question = "合同中违约责任条款应该如何约定？"
    print(f"\n问题: {question}")
    
    answer = analyzer.answer_question(
        query=question,
        user_id="demo_user",
    )
    
    print(f"\n回答:\n{answer}")


def example_add_to_knowledge_base():
    """示例：添加文档到知识库"""
    print("\n" + "=" * 60)
    print("示例 3: 添加文档到知识库")
    print("=" * 60)
    
    analyzer = LegalRiskAnalyzer()
    
    sample_law = """
    中华人民共和国民法典
    
    第四百六十九条 当事人订立合同，可以采用书面形式、口头形式或者其他形式。
    书面形式是合同书、信件、电报、电传、传真等可以有形地表现所载内容的形式。
    以电子数据交换、电子邮件等方式能够有形地表现所载内容，并可以随时调取查用的数据电文，视为书面形式。
    
    第四百七十条 合同的内容由当事人约定，一般包括下列条款：
    （一）当事人的姓名或者名称和住所；
    （二）标的；
    （三）数量；
    （四）质量；
    （五）价款或者报酬；
    （六）履行期限、地点和方式；
    （七）违约责任；
    （八）解决争议的方法。
    当事人可以参照各类合同的示范文本订立合同。
    """
    
    count = analyzer.add_text_to_knowledge_base(
        content=sample_law,
        doc_id="civil_code_contract",
        doc_type="law",
        title="民法典合同编",
    )
    
    print(f"\n成功添加 {count} 个文本块到知识库")


def example_agent_chat():
    """示例：与 Agent 对话"""
    print("\n" + "=" * 60)
    print("示例 4: 与 Agent 对话")
    print("=" * 60)
    
    agent = LegalRiskAgent(user_id="demo_user")
    
    messages = [
        "你好，请介绍一下你能做什么？",
        "帮我分析一份简单的合同风险",
    ]
    
    for msg in messages:
        print(f"\n用户: {msg}")
        response = agent.chat(msg)
        print(f"Agent: {response}")


def example_get_stats():
    """示例：获取系统统计信息"""
    print("\n" + "=" * 60)
    print("示例 5: 获取系统统计信息")
    print("=" * 60)
    
    agent = LegalRiskAgent()
    stats = agent.get_stats()
    
    print(f"\n法律文档统计:")
    print(f"  总块数: {stats.get('legal_documents', {}).get('total_chunks', 0)}")
    print(f"  唯一文件数: {stats.get('legal_documents', {}).get('unique_files', 0)}")
    
    print(f"\n风险知识统计:")
    print(f"  总条数: {stats.get('risk_knowledge', {}).get('total_items', 0)}")
    risk_types = stats.get('risk_knowledge', {}).get('risk_types', [])
    if risk_types:
        print(f"  风险类型: {', '.join(risk_types)}")


def main():
    """运行所有示例"""
    print("法律文件风险点分析系统 - 示例演示")
    print("=" * 60)
    
    try:
        example_analyze_document()
        example_answer_question()
        example_add_to_knowledge_base()
        example_agent_chat()
        example_get_stats()
    except Exception as e:
        print(f"\n错误: {e}")
        print("\n请确保已正确配置 .env 文件中的 API Key")


if __name__ == "__main__":
    main()
