import numpy as np
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
from sqlalchemy.orm import Session
from backend.database import SalaryTrend

def calculate_mape(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    # 避免分母為零
    mask = y_true != 0
    if not np.any(mask):
        return 0.0
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100

def forecast_salary(db: Session, study_field: str, target_years: int) -> dict:
    """
    進行指定學門與畢業後年資的薪資預測。
    採用 Regression 模型，並計算 MAPE。如果 MAPE > 15%，自動重調超參數（如使用 Ridge 或變更 Degree）。
    """
    # 撈取該學門的歷史薪資趨勢
    records = db.query(SalaryTrend).filter_by(study_field=study_field).all()
    
    if not records:
        #  fallback 如果完全沒有資料
        return {"study_field": study_field, "predicted_salary": 45000.0, "model_mape": 0.0, "warning": "No historical data found"}

    # 特徵: 畢業後年資 (years_after_graduation)
    # 我們先預測指定 target_years 在歷史基準年份的平均薪資
    # X = [[years_after_graduation]]
    X = []
    y = []
    for r in records:
        X.append([r.years_after_graduation])
        y.append(r.average_salary)
        
    X = np.array(X)
    y = np.array(y)
    
    # 嘗試不同的模型與超參數，確保 MAPE < 15%
    best_model = None
    best_mape = float('inf')
    best_pred = 0.0
    
    # 目標特徵 (歷史基準年資)
    target_X = np.array([[target_years]])
    
    # 候選超參數/模型組合
    candidates = [
        {"type": "linear", "degree": 1},
        {"type": "ridge", "degree": 1, "alpha": 1.0},
        {"type": "ridge", "degree": 2, "alpha": 10.0},
        {"type": "ridge", "degree": 2, "alpha": 0.1},
    ]
    
    for cand in candidates:
        if cand["degree"] > 1:
            model = make_pipeline(
                PolynomialFeatures(degree=cand["degree"]),
                Ridge(alpha=cand.get("alpha", 1.0)) if cand["type"] == "ridge" else LinearRegression()
            )
        else:
            model = Ridge(alpha=cand.get("alpha", 1.0)) if cand["type"] == "ridge" else LinearRegression()
            
        model.fit(X, y)
        y_pred = model.predict(X)
        mape = calculate_mape(y, y_pred)
        
        if mape < best_mape:
            best_mape = mape
            best_model = model
            best_pred = model.predict(target_X)[0]
            
    # 將預測結果從歷史基準年調整到目標預測年 (民國 113 年)
    # 採用每年 2.5% 的穩健年化調薪率 (反映通貨膨脹與經濟增長)
    base_year = np.mean([r.record_year for r in records])
    years_diff = 113 - base_year
    adjusted_pred = best_pred * (1.025 ** years_diff)
    
    # 決策安全性把關：設立一個基本的月薪底線，確保絕不低於基本工資
    final_pred = max(adjusted_pred, 30000.0)
            
    # 決策安全性檢查：如果最佳 MAPE 仍然大於 15%，拋出告警
    warning_msg = None
    if best_mape > 15.0:
        warning_msg = f"MAPE ({best_mape:.2f}%) exceeds safety threshold of 15%. Predictions may be unstable."
        
    return {
        "study_field": study_field,
        "predicted_salary": round(float(final_pred), 1),
        "model_mape": round(float(best_mape), 2),
        "warning": warning_msg
    }
