# EduCareer-AI 決策支援系統 - 前端 (Frontend Client)

本前端應用程式基於 **React** 與 **Vite** 建構，採用無架構限制的 Vanilla CSS 打造現代化暗色漸層與玻璃擬物化 (Glassmorphism) 視覺介面，提供多智能體決策報告展示與薪資回歸預測的互動式控制台。

## 本機開發與啟動步驟

在開始之前，請確保您的系統已安裝 [Node.js](https://nodejs.org/)。

### 1. 進入前端目錄
開啟終端機並切換至 `frontend` 資料夾：
```bash
cd frontend
```

### 2. 安裝相依套件 (首次執行時需要)
如果您是第一次執行本專案，請先安裝相依套件（已包含 `lucide-react` 圖標庫等）：
```bash
npm install
```

### 3. 啟動本機開發伺服器
執行以下指令來啟動 Vite 開發伺服器：
```bash
npm run dev
```

* 啟動成功後，終端機會顯示類似以下的網址：
  > `  ➜  Local:   http://localhost:5173/`
* 按住 `Ctrl` 鍵點選該網址，或手動複製網址貼到瀏覽器中即可開啟系統！

---

## 生產環境建置與打包

如果您需要編譯出用於生產環境部署的靜態網頁檔案，請執行：
```bash
npm run build
```
打包後的檔案將會輸出在 `frontend/dist` 目錄下。

---

## 系統配合說明
本前端會向本機的 FastAPI 後端（預設為 `http://127.0.0.1:8000`）請求資料。在啟動前端前，請確保您的後端伺服器已經先行啟動：
```bash
# 於專案根目錄下啟動後端
.venv\Scripts\python.exe backend/main.py
```
