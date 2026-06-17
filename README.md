# EduCareer-AI 高教升學與職涯決策支援系統

`EduCareer-AI` 是一款結合政府開放資料、回歸預測模型與 AI 決策分析的「高教升學與職涯決策支援系統」。本系統旨在協助學生與家長在選填志願、升學或進行職涯規劃時，能一站式地整合與查詢學校註冊率、在學人數、就業前景、薪資成長軌跡以及 AI 策略建議。

---

## 🚀 系統核心功能

1. **政府開放資料同步與歸一化管線 (`backend/ingestion.py`)**
   - 支援讀取大專校院學生數 (JSON/TXT)、新生註冊率 (CSV) 與真實畢業生就業薪資資料 (`Student_RPT_19` 真實數據)。
   - **高強健性欄位比對**：採用動態歸一化對應與 `dict.get()`，當政府開放資料變更或新增未知欄位時，系統不會損毀或報錯，具備極佳的適應性。

2. **多模型薪資回歸預測 (`backend/forecasting.py`)**
   - 使用 Scikit-Learn 建立薪資預測模型（包含 Linear Regression、Ridge Regression 等），依據畢業生年資預測未來薪資。
   - **模型穩定性把關 (MAPE)**：自動計算平均絕對百分比誤差 (MAPE)，若 MAPE 超過安全閾值 (15%) 則自動調整超參數或丟出穩定性警示，確保預測品質。

3. **多智能體 AI 決策分析 (`backend/agent.py`)**
   - 藉由 LangChain 與 OpenAI GPT 模型，實作三層式決策架構：
     - **證據層 (Evidence Layer)**：提供科系最新註冊率、在學人數與薪資基準點。
     - **推理層 (Reasoning Layer)**：分析市場需求等級（高/中/低）、競爭力分析與潛在風險。
     - **決策層 (Decision Layer)**：計算適配度評分 (0-100)，並給出客製化的升學與職涯策略建議。
   - **Mock Fallback 機制**：若未填寫或 OpenAI API 金鑰失效，系統會自動切換為 Mock 分析生成器，確保整體系統功能可完整預覽。

4. **現代化前端互動控制台 (`frontend`)**
   - 基於 React、Vite 與 Lucide 圖標庫建構。
   - 提供直觀的學校科系檢索、職涯偏好設定（起薪優先、科技業、公務員學術、跨領域發展、外商外派）、即時 AI 分析報告、薪資預測圖表與後端資料同步介面。

---

## 📂 專案目錄結構

```text
EduCareer_AI/
├── backend/                  # FastAPI 後端
│   ├── agent.py              # 多智能體 AI 分析模組 (LangChain & OpenAI)
│   ├── database.py           # SQLite & SQLAlchemy 資料庫模型與初始化
│   ├── forecasting.py        # 薪資回歸預測與 MAPE 計算
│   ├── ingestion.py          # 資料同步與動態歸一化管線
│   ├── main.py               # FastAPI 應用程式主入口與 API 路由
│   └── test_pipeline.py      # 整合測試腳本 (單元測試與管線強健性驗證)
├── data/                     # 政府開放資料儲存目錄
│   ├── 106-112學年大專院校各校科系別學生數(JSON檔).txt  (或 .json)
│   ├── 學12-1.新生(含境外生)註冊率-以「系(所)」統計.csv
│   └── Student_RPT_19/       # 教育部畢業生流向與薪資真實資料 (學門.csv, 學類.csv)
├── frontend/                 # React + Vite 前端
│   ├── src/
│   │   ├── App.jsx           # 前端主要介面與 API 交互邏輯
│   │   ├── App.css           # 應用程式佈局與組件樣式
│   │   ├── index.css         # 全域設計系統與 CSS Tokens
│   │   └── main.jsx          # 前端渲染入口
│   ├── package.json          # 前端依賴設定
│   └── vite.config.js        # Vite 設定檔
├── requirements.txt          # 後端 Python 套件依賴清單
├── .gitignore                # Git 忽略設定
└── README.md                 # 本說明文件
```

---

## 🛠️ 快速開始與環境建置

### 1. 後端設定與啟動

#### 步驟 A：建立虛擬環境並安裝依賴
建議使用 Python 3.10+。在專案根目錄下執行：
```powershell
# 建立虛擬環境
python -m venv .venv

# 啟用虛擬環境 (Windows)
.venv\Scripts\activate

# 安裝後端所需套件
pip install -r requirements.txt
```

#### 步驟 B：設定環境變數
在專案根目錄下建立 `.env` 檔案（或直接修改已存在的設定）：
```env
# 若需要啟動真實 AI 決策分析，請填入 OpenAI API Key；未填入時系統會自動 Fallback 至 Mock 模式
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
DATABASE_URL=sqlite:///./educareer.db
```

#### 步驟 C：啟動 FastAPI 後端伺服器
可以使用以下兩種方式之一啟動後端（預設運行在 `http://127.0.0.1:8000`）：
```powershell
# 方式 1：直接執行 main.py
python backend/main.py

# 方式 2：使用 uvicorn 指令（支援熱重載，開發推薦）
uvicorn backend.main:app --reload --port 8000
```
*提示：系統啟動時，若偵測到 `educareer.db` 資料庫為空，會自動執行 `backend/ingestion.py` 資料同步管線載入 `data` 資料夾中的政府開放資料與薪資數據。*

---

### 2. 前端設定與啟動

在另一個終端機視窗中，進入 `frontend` 目錄：
```powershell
# 切換至前端目錄
cd frontend

# 安裝 Node 套件
npm install

# 啟動前端開發伺服器
npm run dev
```
啟動後，瀏覽器通常會自動打開或可手動訪問 `http://localhost:5173`。

---

## 🧪 測試驗證

本專案附帶測試腳本，可用於驗證學門推論、資料同步管線的強健性（特別是忽略未知欄位）以及 MAPE 計算的精準度。

在虛擬環境啟用狀態下，於專案根目錄執行：
```powershell
python -m backend.test_pipeline
```
若輸出 `✓` 符號與測試通過訊息，代表核心管線邏輯皆正常運作。

---

## 📊 資料來源與參考

1. **教育部統計處** - 106-112 學年大專院校各校科系別學生數資料。
2. **教育部大專校院校務資訊公開平台** - 學12-1 新生（含境外生）註冊率-以「系（所）」統計。
3. **教育部畢業生流向與就業薪資相關統計資料** - `Student_RPT_19` (學門、學類畢業生起薪與就業追蹤)。
