import os
import json
import csv
from sqlalchemy.orm import Session
from backend.database import Department, EnrollmentStat, SalaryTrend
from tqdm import tqdm

# 簡易學門分類關鍵字映射規則
STUDY_FIELD_KEYWORDS = {
    "資訊工程": ["資訊", "資工", "軟體", "電腦", "計算機", "網路學"],
    "電機電子": ["電機", "電子", "光電", "通訊", "半導體"],
    "商業管理": ["企業管理", "企管", "財務", "金融", "會計", "國貿", "管理", "商業"],
    "人文社會": ["歷史", "哲學", "宗教", "文學", "中文", "外文", "社會", "心理"],
    "基礎科學": ["數學", "物理", "化學", "生物", "太空"]
}

def determine_study_field(dept_name: str) -> str:
    """根據系所名稱動態推論學門"""
    for field, keywords in STUDY_FIELD_KEYWORDS.items():
        if any(kw in dept_name for kw in keywords):
            return field
    return "其他學門"

def run_ingestion_pipeline(db: Session, json_path: str, csv_path: str) -> int:
    """
    動態歸一化管道:
    1. 載入 106-112學年大專院校各校科系別學生數 (JSON)
    2. 載入 新生註冊率 (CSV)
    3. 動態對應與建立關聯，且對未知隨機欄位有高度強健性 (使用 dict.get)
    """
    # 1. 建立或讀取 Department 暫存快取以加速寫入
    # 為了簡化，我們先載入 JSON 資料來填充基本 Department 和 EnrollmentStat 中的學生數
    synced_count = 0
    dept_cache = {} # key: (school_name, dept_name) -> ID
    
    # 預先載入已有科系
    existing_depts = db.query(Department).all()
    for d in existing_depts:
        dept_cache[(d.school_name, d.department_name)] = d.id

    # 解析學生數 JSON
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            try:
                # 兼容格式：如果 JSON 是開頭有逗號的 JSONL 或 Array，我們用 json.load 讀取
                # 開放資料常常是一個大 Array
                data = json.load(f)
            except Exception as e:
                # 容錯處理：若是 JSONL 格式
                f.seek(0)
                data = []
                for line in f:
                    line = line.strip()
                    if line.startswith(','):
                        line = line[1:]
                    if not line:
                        continue
                    try:
                        data.append(json.loads(line))
                    except:
                        pass
            
            # 遍歷資料並加上 tqdm 進度條
            print("正在匯入各校科系別學生數資料...")
            enrollment_agg = {} # key: (dept_id, year) -> student_count

            for idx, item in enumerate(tqdm(data, desc="匯入科系學生數", unit="筆")):
                # 這裡使用 dict.get()，動態 schema 推論以防未來欄位改名或新增未知欄位
                school_name = item.get("學校名稱") or item.get("學校")
                dept_name = item.get("科系名稱") or item.get("系所名稱") or item.get("科系")
                year_val = item.get("學年度")
                total_students = item.get("總計")
                
                if not school_name or not dept_name or year_val is None:
                    continue
                
                try:
                    year = int(year_val)
                    total_students = int(total_students) if total_students is not None else 0
                except ValueError:
                    continue

                # 取得或建立 Department
                key = (school_name, dept_name)
                if key not in dept_cache:
                    study_field = determine_study_field(dept_name)
                    new_dept = Department(
                        school_name=school_name,
                        department_name=dept_name,
                        study_field=study_field
                    )
                    db.add(new_dept)
                    db.flush() # 取得 ID
                    dept_cache[key] = new_dept.id
                
                dept_id = dept_cache[key]
                stat_key = (dept_id, year)
                enrollment_agg[stat_key] = enrollment_agg.get(stat_key, 0) + total_students
                synced_count += 1
                if idx % 5000 == 0:
                    db.commit()

            print("正在寫入學生數統計至資料庫...")
            for (dept_id, year), student_count in tqdm(enrollment_agg.items(), desc="寫入學生數", unit="筆"):
                stat = db.query(EnrollmentStat).filter_by(department_id=dept_id, academic_year=year).first()
                if not stat:
                    stat = EnrollmentStat(
                        department_id=dept_id,
                        academic_year=year,
                        student_count=student_count,
                        freshman_registration_rate=None
                    )
                    db.add(stat)
                else:
                    stat.student_count = student_count
            db.commit()

    # 2. 解析新生註冊率 CSV 並動態對應
    if os.path.exists(csv_path):
        with open(csv_path, 'r', encoding='utf-8') as f:
            # 獲取總行數以方便 tqdm 計算進度百分比
            total_lines = sum(1 for _ in f) - 1
            f.seek(0)
            
            # 使用 DictReader 支援動態欄位推論
            reader = csv.DictReader(f)
            
            # 清理可能的 BOM 頭或空白
            fieldnames = [fn.strip() for fn in reader.fieldnames] if reader.fieldnames else []
            
            # 動態比對可能代表「註冊率」的欄位名稱
            reg_rate_col = None
            school_col = None
            dept_col = None
            year_col = None
            
            for fn in fieldnames:
                # 優先完全符合，其次模糊比對且避免錯誤欄位
                if fn == "當學年度新生註冊率(%)D=〔(C+E)/(A-B+E)〕＊100％" or ("註冊率" in fn and not reg_rate_col):
                    reg_rate_col = fn
                if fn == "學校名稱" or fn == "學校" or ("學校名稱" in fn and not school_col):
                    school_col = fn
                if fn == "系所名稱" or fn == "系所" or ("系所名稱" in fn and not dept_col):
                    dept_col = fn
                # 排除含有 "資訊網" 或 "特色說明" 等 URL/說明欄位，確保精準比對學年度
                if fn == "學年度" or fn == "學年" or ("學年度" in fn and "資訊網" not in fn and "特色說明" not in fn and not year_col):
                    year_col = fn

            if reg_rate_col and school_col and dept_col and year_col:
                print("正在配對各科系新生註冊率資料...")
                # 記憶體聚合，避免頻繁與資料庫交涉
                rate_agg = {}

                for idx, row in enumerate(tqdm(reader, total=total_lines, desc="交叉比對註冊率", unit="筆")):
                    s_name = row.get(school_col)
                    d_name = row.get(dept_col)
                    y_val = row.get(year_col)
                    rate_str = row.get(reg_rate_col)
                    
                    if not s_name or not d_name or not y_val or not rate_str:
                        continue
                    
                    try:
                        rate_str = rate_str.replace('%', '').strip()
                        if rate_str == "..." or not rate_str:
                            rate = None
                        else:
                            rate = float(rate_str)
                        year = int(y_val)
                    except ValueError:
                        continue
                    
                    key = (s_name, d_name)
                    if key in dept_cache and rate is not None:
                        dept_id = dept_cache[key]
                        stat_key = (dept_id, year)
                        
                        if stat_key not in rate_agg:
                            rate_agg[stat_key] = []
                        
                        # 學制班別包含學士班，或者日間部則提高權重
                        class_type = row.get("學制班別") or ""
                        if "學士" in class_type or "日" in (row.get("日間/進修") or ""):
                            rate_agg[stat_key].append(rate)
                            rate_agg[stat_key].append(rate)
                        else:
                            rate_agg[stat_key].append(rate)

                print("正在更新資料庫中註冊率...")
                for (dept_id, year), rates in tqdm(rate_agg.items(), desc="更新註冊率", unit="筆"):
                    if rates:
                        avg_rate = sum(rates) / len(rates)
                        # 尋找已有的 EnrollmentStat
                        stat = db.query(EnrollmentStat).filter_by(department_id=dept_id, academic_year=year).first()
                        if stat:
                            stat.freshman_registration_rate = round(avg_rate, 2)
                        else:
                            stat = EnrollmentStat(
                                department_id=dept_id,
                                academic_year=year,
                                student_count=0,
                                freshman_registration_rate=round(avg_rate, 2)
                            )
                            db.add(stat)
                db.commit()
    
    # 3. 產生與寫入模擬的薪資趨勢 (為了後續回歸預測)
    generate_mock_salary_trends(db)
    
    return synced_count

def generate_mock_salary_trends(db: Session):
    """
    從 C:\\Users\\PARALELL\\Desktop\\code6\\data\\Student_RPT_19 讀取實體資料，
    當作提供各學門/學科畢業生投入職場的起薪與後續薪資成長軌跡的真實資料基礎。
    學士/日間學制 -> 畢業 1 年，碩士/日間學制 -> 畢業 3 年，博士/未滿35歲 -> 畢業 5 年，
    """
    # 如果已經有真實資料庫記錄，先刪除，以便重新同步時導入真實資料
    db.query(SalaryTrend).delete()
    db.commit()

    base_rpt_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "Student_RPT_19")
    dept_file = os.path.join(base_rpt_dir, "學門.csv")
    class_file = os.path.join(base_rpt_dir, "學類.csv")

    # 定義如何將 RPT_19 的學門名稱對應到我們的系統學門 study_field
    field_mapping = {
        "電算機學門": "資訊工程",
        "工程學門": "電機電子",
        "商業及管理學門": "商業管理",
        "人文學門": "人文社會",
        "社會及行為科學學門": "人文社會",
        "藝術學門": "人文社會",
        "數學及統計學門": "基礎科學",
        "生命科學學門": "基礎科學",
        "物理、化學及地球科學學門": "基礎科學",
    }

    # 1. 首先讀取學門.csv作為薪資基礎資料庫
    if os.path.exists(dept_file):
        with open(dept_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw_field = row.get("學門名稱") or ""
                study_field = field_mapping.get(raw_field, "其他學門")
                
                # 博士未滿35歲 -> 對應畢業 5 年起薪
                sal_5_str = row.get("99學年度畢業生102薪資年博士未滿35歲平均薪資") or row.get("99學年度畢業生103薪資年博士未滿35歲平均薪資")
                
                try:
                    if sal_5_str and sal_5_str.strip():
                        val_5 = float(sal_5_str.strip())
                        # 寫入畢業後 5 年薪資記錄
                        for yr in [102, 103]:
                            trend = SalaryTrend(
                                study_field=study_field,
                                years_after_graduation=5,
                                average_salary=val_5,
                                record_year=yr
                            )
                            db.add(trend)
                except ValueError:
                    pass

    # 2. 接著讀取學類.csv以獲取學士(畢業1年)、碩士(畢業3年)的真實薪資起薪與成長軌跡
    if os.path.exists(class_file):
        with open(class_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw_class = row.get("學門學類") or ""
                # 使用簡單關鍵字對應至我們系統內的學門
                study_field = determine_study_field(raw_class)

                # 學士日間學制平均月薪 -> 對應畢業 1 年
                sal_1_str = row.get("99學年度畢業生102年已投入職場比率_學士_日間學制_平均月薪")
                # 碩士日間學制平均月薪 -> 對應畢業 3 年
                sal_3_str = row.get("99學年度畢業生102年已投入職場比率_碩士_日間學制_平均月薪")

                try:
                    if sal_1_str and sal_1_str.strip():
                        val_1 = float(sal_1_str.strip())
                        trend1 = SalaryTrend(
                            study_field=study_field,
                            years_after_graduation=1,
                            average_salary=val_1,
                            record_year=102
                        )
                        db.add(trend1)
                except ValueError:
                    pass

                try:
                    if sal_3_str and sal_3_str.strip():
                        val_3 = float(sal_3_str.strip())
                        trend3 = SalaryTrend(
                            study_field=study_field,
                            years_after_graduation=3,
                            average_salary=val_3,
                            record_year=102
                        )
                        db.add(trend3)
                except ValueError:
                    pass

    db.commit()

    # 3. 補齊沒有對應到的基礎數據，確保回歸預測模型有足夠數據點可做預測
    # 如果某個學門完全沒有資料，則以合理的初始值作為 fallback
    for field in ["資訊工程", "電機電子", "商業管理", "人文社會", "基礎科學", "其他學門"]:
        for yrs in [1, 3, 5]:
            exists = db.query(SalaryTrend).filter_by(study_field=field, years_after_graduation=yrs).first()
            if not exists:
                fallback_salaries = {
                    "資訊工程": {1: 44000.0, 3: 55000.0, 5: 70000.0},
                    "電機電子": {1: 48000.0, 3: 60000.0, 5: 78000.0},
                    "商業管理": {1: 36000.0, 3: 45000.0, 5: 55000.0},
                    "人文社會": {1: 31000.0, 3: 36000.0, 5: 42000.0},
                    "基礎科學": {1: 38000.0, 3: 46000.0, 5: 56000.0},
                    "其他學門": {1: 32000.0, 3: 38000.0, 5: 45000.0}
                }
                trend = SalaryTrend(
                    study_field=field,
                    years_after_graduation=yrs,
                    average_salary=fallback_salaries[field][yrs],
                    record_year=102
                )
                db.add(trend)
                
                # 同時多建一年的點以便回歸擬合 (擬合需要多個時間點)
                trend2 = SalaryTrend(
                    study_field=field,
                    years_after_graduation=yrs,
                    average_salary=fallback_salaries[field][yrs] * 1.03,
                    record_year=103
                )
                db.add(trend2)
    db.commit()
