import os
import json
import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base, Department, EnrollmentStat, SalaryTrend
from backend.ingestion import run_ingestion_pipeline, determine_study_field
from backend.forecasting import calculate_mape, forecast_salary

def run_tests():
    print("--- 1. Testing Dynamic Field Determination ---")
    assert determine_study_field("資訊工程學系") == "資訊工程"
    assert determine_study_field("電機工程學系") == "電機電子"
    assert determine_study_field("企業管理學系") == "商業管理"
    assert determine_study_field("歷史學系") == "人文社會"
    assert determine_study_field("物理學系") == "基礎科學"
    assert determine_study_field("神祕魔法學系") == "其他學門"
    print("✓ determine_study_field tests passed.")

    print("\n--- 2. Testing Ingestion Pipeline Robustness with Unknown Columns ---")
    # 建立記憶體 SQLite 進行測試
    engine = create_engine("sqlite:///:memory:")
    SessionClass = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    db = SessionClass()

    # 模擬包含隨機未知欄位及新型態的資料
    mock_json = [
        {
            "學年度": 106,
            "學校名稱": "國立政治大學",
            "科系名稱": "歷史學系",
            "總計": 173,
            "未知新增欄位一": "future_data_state",
            "隨機未來設定": 9999
        }
    ]
    
    mock_csv_headers = ["學年度", "設立別", "學校名稱", "系所名稱", "當學年度新生註冊率(%)D=〔(C+E)/(A-B+E)〕＊100％", "未來新增測試欄位"]
    mock_csv_rows = [
        ["106", "公立", "國立政治大學", "歷史學系", "97.73", "extra_value"]
    ]

    json_file = "test_students.json"
    csv_file = "test_registration.csv"

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(mock_json, f, ensure_ascii=False)

    with open(csv_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(mock_csv_headers)
        writer.writerows(mock_csv_rows)

    try:
        records_synced = run_ingestion_pipeline(db, json_file, csv_file)
        print(f"Synced records count: {records_synced}")
        
        # 驗證是否寫入 Department
        dept = db.query(Department).filter_by(school_name="國立政治大學", department_name="歷史學系").first()
        assert dept is not None
        assert dept.study_field == "人文社會"

        # 驗證是否寫入 EnrollmentStat
        stat = db.query(EnrollmentStat).filter_by(department_id=dept.id, academic_year=106).first()
        assert stat is not None
        assert stat.student_count == 173
        assert stat.freshman_registration_rate == 97.73
        print("✓ Ingestion Pipeline successfully ignored unknown columns and imported correctly.")
    finally:
        if os.path.exists(json_file):
            os.remove(json_file)
        if os.path.exists(csv_file):
            os.remove(csv_file)
        db.close()

    print("\n--- 3. Testing MAPE Calculations ---")
    y_true = [100, 200, 300]
    y_pred = [90, 220, 270]
    # (10% + 10% + 10%) / 3 = 10%
    mape = calculate_mape(y_true, y_pred)
    assert abs(mape - 10.0) < 1e-5
    print(f"✓ MAPE calculation passed (Calculated: {mape:.2f}%).")

if __name__ == "__main__":
    run_tests()
