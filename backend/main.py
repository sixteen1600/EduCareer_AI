# -*- coding: utf-8 -*-
"""
是的，您也可以使用 `uvicorn` 的命令列工具直接啟動！

如果您想直接透過 `uvicorn` 啟動，
請在虛擬環境下執行以下指令（這樣也具備程式碼修改自動重載 `--reload` 功能，非常方便開發）：

```powershell
.venv\\Scripts\\uvicorn backend.main:app --reload --port 8000
```

*備註：因為我們在最下方寫了 `uvicorn.run(app, host="127.0.0.1", port=8000)`，
 核心邏輯依然可以使用 .venv\\Scripts\\python.exe backend/main.py 執行，它在內部也會自動呼叫 uvicorn 跑起來。
 這兩種啟動方式都是完全可行的！*
"""


import os
from dotenv import load_dotenv

# 主動從 .env 中載入環境變數以防終端機環境插入功能被停用
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    load_dotenv()

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict

from backend.database import init_db, get_db, Department, EnrollmentStat, SalaryTrend
from backend.ingestion import run_ingestion_pipeline, determine_study_field
from backend.forecasting import forecast_salary
from backend.agent import run_agent_analysis, EvidenceData, AgentDecisionResponse

# 初始化 SQLite 資料庫結構
init_db()

# 自動執行資料同步管線 (若資料庫無資料才自動預先載入真實資料，一勞永逸)
db_session = next(get_db())
try:
    # 檢查是否已有科系資料
    if db_session.query(Department).first() is None:
        base_data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        json_path = os.path.join(base_data_dir, "106-112學年大專院校各校科系別學生數(JSON檔).json")
        if not os.path.exists(json_path):
            json_path = os.path.join(base_data_dir, "106-112學年大專院校各校科系別學生數(JSON檔).txt")
        csv_path = os.path.join(base_data_dir, "學12-1.新生(含境外生)註冊率-以「系(所)」統計.csv")
        print(f"資料庫為空，正在自動同步政府開放資料 ({os.path.basename(json_path)}) 與 Student_RPT_19 真實薪資數據至 SQLite 資料庫...")
        synced_records = run_ingestion_pipeline(db_session, json_path, csv_path)
        print(f"成功自動載入並歸一化 {synced_records} 筆資料與起薪成長軌跡！")
    else:
        print("資料庫中已有實體資料，跳過自動同步管線（已實現一勞永逸寫入資料庫）。")
except Exception as e:
    print(f"自動同步時發生錯誤 (仍會啟動系統): {e}")
finally:
    db_session.close()

app = FastAPI(
    title="EduCareer-AI 決策支援系統 API",
    description="提供高教升學與職涯策略量化分析後端",
    version="1.0.0"
)

# 啟用 CORS 供 React 前端存取
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/meta/schools-departments")
def get_meta_schools_departments(db: Session = Depends(get_db)):
    """獲取資料庫中所有的學校名稱以及科系別清單"""
    try:
        # 查詢所有獨特的學校名稱
        schools_query = db.query(Department.school_name).distinct().all()
        schools = sorted([s[0] for s in schools_query if s[0]])
        
        # 查詢所有獨特的科系名稱
        depts_query = db.query(Department.department_name).distinct().all()
        departments = sorted([d[0] for d in depts_query if d[0]])
        
        # 預設 Fallback (防止空庫時為空)
        if not schools:
            schools = ['國立政治大學', '東海大學', '國立臺灣大學', '國立成功大學']
        if not departments:
            departments = ['歷史學系', '中國文學系', '資訊工程學系', '電機工程學系', '企業管理學系']
            
        return {"schools": schools, "departments": departments}
    except Exception as e:
        return {
            "schools": ['國立政治大學', '東海大學', '國立臺灣大學', '國立成功大學'],
            "departments": ['歷史學系', '中國文學系', '資訊工程學系', '電機工程學系', '企業管理學系'],
            "error": str(e)
        }

@app.get("/api/v1/meta/schools/{school_name}/departments")
def get_departments_for_school(school_name: str, db: Session = Depends(get_db)):
    """獲取特定學校的所有科系別清單"""
    try:
        depts_query = db.query(Department.department_name).filter(Department.school_name == school_name).distinct().all()
        departments = sorted([d[0] for d in depts_query if d[0]])
        
        # 預設 Fallback
        if not departments:
            departments = ['歷史學系', '中國文學系', '資訊工程學系', '電機工程學系', '企業管理學系']
            
        return {"departments": departments}
    except Exception as e:
        return {
            "departments": ['歷史學系', '中國文學系', '資訊工程學系', '電機工程學系', '企業管理學系'],
            "error": str(e)
        }

# REST Request/Response Models
class ForecastRequest(BaseModel):
    study_field: str
    target_years: int

class AnalysisRequest(BaseModel):
    school_name: str
    department_name: str
    user_preferences: List[str]

@app.get("/api/v1/data/sync")
def sync_data(db: Session = Depends(get_db)):
    """
    GET /api/v1/data/sync
    觸發政府開放資料同步與動態歸一化
    """
    base_data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    json_path = os.path.join(base_data_dir, "106-112學年大專院校各校科系別學生數(JSON檔).json")
    if not os.path.exists(json_path):
        json_path = os.path.join(base_data_dir, "106-112學年大專院校各校科系別學生數(JSON檔).txt")
    csv_path = os.path.join(base_data_dir, "學12-1.新生(含境外生)註冊率-以「系(所)」統計.csv")

    if not os.path.exists(json_path) and not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="政府開放資料實體檔案未找到，請確認位於 data 目錄。")

    try:
        synced_records = run_ingestion_pipeline(db, json_path, csv_path)
        return {"status": "success", "synced_records": synced_records}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion pipeline failed: {str(e)}")

@app.post("/api/v1/forecast/predict")
def predict_salary(req: ForecastRequest, db: Session = Depends(get_db)):
    """
    POST /api/v1/forecast/predict
    進行指定學門與年資的薪資回歸預測
    """
    try:
        res = forecast_salary(db, req.study_field, req.target_years)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forecasting module failed: {str(e)}")

@app.post("/api/v1/agent/analyze", response_model=AgentDecisionResponse)
def analyze_department_agent(req: AnalysisRequest, db: Session = Depends(get_db)):
    """
    POST /api/v1/agent/analyze
    觸發多智能體進行系所與職涯綜合決策
    """
    # 1. 查詢該科系
    dept = db.query(Department).filter_by(
        school_name=req.school_name,
        department_name=req.department_name
    ).first()
    
    if not dept:
        # 如果資料庫尚未同步該科系，動態建立一個以防系統報錯，提高強健性
        study_field = determine_study_field(req.department_name)
        dept = Department(
            school_name=req.school_name,
            department_name=req.department_name,
            study_field=study_field
        )
        db.add(dept)
        db.flush()
        db.commit()

    # 2. 獲取該科系的量化證據
    # 取得最新一年度的註冊率與人數
    stats = db.query(EnrollmentStat).filter_by(department_id=dept.id).order_by(EnrollmentStat.academic_year.desc()).all()
    
    current_student_count = 0
    registration_rate = None
    if stats:
        # 尋找最近非零的學生數 (防範部分年份僅有註冊率而無學生數資料)
        for s in stats:
            if s.student_count > 0:
                current_student_count = s.student_count
                break
        # 尋找最近非空的註冊率
        for s in stats:
            if s.freshman_registration_rate is not None:
                registration_rate = s.freshman_registration_rate
                break

    # 3. 獲取該學門畢業後的歷史平均薪資
    trends = db.query(SalaryTrend).filter_by(study_field=dept.study_field).order_by(SalaryTrend.years_after_graduation.asc()).all()
    historical_salary_points = {}
    for t in trends:
        key = f"畢業後 {t.years_after_graduation} 年"
        historical_salary_points[key] = t.average_salary
        
    # 如果完全沒有薪資趨勢資料（如尚未觸發 sync 建立 mock data），給予基礎值
    if not historical_salary_points:
        historical_salary_points = {
            "畢業後 1 年": 36000.0,
            "畢業後 3 年": 44000.0,
            "畢業後 5 年": 53000.0
        }

    evidence = EvidenceData(
        registration_rate=registration_rate,
        current_student_count=current_student_count,
        historical_salary_points=historical_salary_points
    )

    # 4. 跑 LLM / Mock Multi-Agent 決策
    decision_response = run_agent_analysis(
        school_name=req.school_name,
        department_name=req.department_name,
        study_field=dept.study_field,
        evidence=evidence,
        user_preferences=req.user_preferences
    )

    return decision_response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
