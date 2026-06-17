import os
import json
from dotenv import load_dotenv

# 主動載入環境變數
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    load_dotenv()

from pydantic import BaseModel, Field
from typing import List, Dict, Optional

# LangChain / OpenAI Imports
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

# Pydantic Schemas matching the spec
class EvidenceData(BaseModel):
    registration_rate: Optional[float] = Field(description="新生註冊率，若無則傳回 0.0")
    current_student_count: int = Field(description="最新年度在學學生人數")
    historical_salary_points: Dict[str, float] = Field(description="該系所學門在畢業 1年, 3年, 5年的歷史/模擬平均薪資點")

class ReasoningInsight(BaseModel):
    market_demand_level: str = Field(description="市場需求等級，必須為 '高'、'中' 或 '低'")
    competition_analysis: str = Field(description="競爭力分析描述")
    risk_factors: List[str] = Field(description="潛在風險因素清單")

class FinalDecision(BaseModel):
    suitability_score: float = Field(description="適配度評分 (0-100)")
    strategic_recommendations: List[str] = Field(description="客製化升學與職涯策略建議")
    suggested_career_paths: List[str] = Field(description="建議的職涯發展路徑")

class AgentDecisionResponse(BaseModel):
    school_name: str
    department_name: str
    study_field: str
    evidence_layer: EvidenceData
    reasoning_layer: ReasoningInsight
    decision_layer: FinalDecision

def get_mock_decision_response(school_name: str, department_name: str, study_field: str, evidence: EvidenceData, user_preferences: List[str]) -> AgentDecisionResponse:
    """當 OpenAI 金鑰未提供或失效時的 Mock 回應，確保回傳完全符合 Pydantic schema"""
    pref_str = "、".join(user_preferences)
    
    # 計算簡單分數
    reg_rate = evidence.registration_rate or 90.0
    score = 50.0 + (reg_rate * 0.4)
    if "起薪優先" in user_preferences:
        score += 5.0
    score = min(100.0, max(0.0, score))
    
    demand = "高" if score > 80 else "中"
    
    return AgentDecisionResponse(
        school_name=school_name,
        department_name=department_name,
        study_field=study_field,
        evidence_layer=evidence,
        reasoning_layer=ReasoningInsight(
            market_demand_level=demand,
            competition_analysis=f"針對偏好【{pref_str}】，該系所的招生註冊率為 {reg_rate}%。市場上有一定競爭強度，需多加修習跨領域科目以提升優勢。",
            risk_factors=[
                "高教少子化可能影響後續系所資源配置。",
                "若缺乏實習經驗，初入職場的薪資溢價空間可能受限。"
            ]
        ),
        decision_layer=FinalDecision(
            suitability_score=round(score, 1),
            strategic_recommendations=[
                "建議在學期間爭取企業實習機會，積累專案實務經驗。",
                "可選修跨領域學程，特別是與資料科學或商業經營相關的科目。"
            ],
            suggested_career_paths=[
                "研發工程師 (R&D Engineer)",
                "系統分析師 (System Analyst)",
                "技術專案經理 (Technical PM)"
            ]
        )
    )

def run_agent_analysis(
    school_name: str,
    department_name: str,
    study_field: str,
    evidence: EvidenceData,
    user_preferences: List[str]
) -> AgentDecisionResponse:
    """
    使用 LangChain 與 OpenAI API 動態生成決策分析。
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or "your_openai_api_key" in api_key or api_key == "":
        # 沒有金鑰時，自動 fallback 到 mock 產生器，確保系統可以被完整預覽
        return get_mock_decision_response(school_name, department_name, study_field, evidence, user_preferences)

    try:
        # 1. 建立 Output Parser
        parser = PydanticOutputParser(pydantic_object=AgentDecisionResponse)

        # 2. 建立 Prompt Template
        prompt = PromptTemplate(
            template="""你是一個專業的高教職涯與系所導航 AI 顧問。
請根據以下提供的分析目標、量化數據以及使用者的職涯偏好，進行深度多智能體分析，並回傳嚴格符合 JSON Schema 的結果。

【分析目標】:
- 學校名稱: {school_name}
- 科系名稱: {department_name}

【量化數據 (Evidence Layer)】:
- 新生註冊率: {registration_rate}%
- 在學學生人數: {student_count}
- 畢業後平均薪資 (1/3/5年): {salaries}

【使用者職涯偏好】:
- {preferences}

{format_instructions}

請確保你的回覆不包含 any 自由文本，只包含正確的 JSON 字串。""",
            input_variables=["school_name", "department_name", "registration_rate", "student_count", "salaries", "preferences"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )

        # 3. 初始化 LLM
        model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        model = ChatOpenAI(
            model=model_name,
            temperature=0.2,
            openai_api_key=api_key
        )

        # 4. 建立 Chain
        chain = prompt | model | parser

        # 5. 執行分析
        result = chain.invoke({
            "school_name": school_name,
            "department_name": department_name,
            "registration_rate": evidence.registration_rate or 0.0,
            "student_count": evidence.current_student_count,
            "salaries": json.dumps(evidence.historical_salary_points, ensure_ascii=False),
            "preferences": ", ".join(user_preferences)
        })

        # 強制覆蓋，確保輸出之學校與科系與使用者輸入完全一致
        result.school_name = school_name
        result.department_name = department_name
        result.study_field = study_field
        return result

    except Exception as e:
        print(f"Error in running LangChain LLM analysis: {e}. Fallback to mock generator.")
        return get_mock_decision_response(school_name, department_name, study_field, evidence, user_preferences)
