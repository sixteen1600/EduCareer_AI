import React, { useState, useEffect } from 'react';
import { 
  Database, 
  TrendingUp, 
  BrainCircuit, 
  RefreshCw, 
  Search, 
  CheckCircle2, 
  AlertTriangle,
  ChevronRight, 
  DollarSign, 
  GraduationCap,
  LineChart
} from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('analyze'); // 'analyze' | 'sync'
  const [schools, setSchools] = useState(['國立政治大學', '東海大學', '國立臺灣大學', '國立成功大學']);
  const [departments, setDepartments] = useState(['歷史學系', '中國文學系', '資訊工程學系', '電機工程學系', '企業管理學系']);
  
  // 查詢與表單欄位
  const [selectedSchool, setSelectedSchool] = useState('國立政治大學');
  const [selectedDept, setSelectedDept] = useState('歷史學系');
  const [preferences, setPreferences] = useState(['起薪優先']);
  
  // 同步面板狀態
  const [syncStatus, setSyncStatus] = useState({ loading: false, records: null, error: null });
  const [syncProgress, setSyncProgress] = useState(0);
  
  // 決策分析結果狀態
  const [analysisResult, setAnalysisResult] = useState(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState(null);
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [analysisStepText, setAnalysisStepText] = useState('');
  
  // 薪資回歸預測狀態
  const [forecastResult, setForecastResult] = useState(null);
  const [forecastLoading, setForecastLoading] = useState(false);
  const [selectedField, setSelectedField] = useState('人文社會');
  const [targetYears, setTargetYears] = useState(5);

  const preferenceOptions = ['起薪優先', '科技業', '公務員學術', '跨領域發展', '外商外派'];

  const togglePreference = (pref) => {
    if (preferences.includes(pref)) {
      setPreferences(preferences.filter(p => p !== pref));
    } else {
      setPreferences([...preferences, pref]);
    }
  };

  // 1. 觸發資料庫同步歸一化
  const handleSync = async () => {
    setSyncStatus({ loading: true, records: null, error: null });
    setSyncProgress(5);
    
    // 模擬進度條增加，提供良好使用者體驗
    const progressInterval = setInterval(() => {
      setSyncProgress((prev) => {
        if (prev >= 90) return prev;
        return prev + Math.floor(Math.random() * 15) + 5;
      });
    }, 400);

    try {
      const response = await fetch('http://127.0.0.1:8000/api/v1/data/sync');
      if (!response.ok) throw new Error('同步失敗，請確認後端已開啟');
      const data = await response.json();
      clearInterval(progressInterval);
      setSyncProgress(100);
      
      // 同步完成後，立刻動態向後端獲取最新的學校與科系清單
      await fetchMetadata();
      
      setTimeout(() => {
        setSyncStatus({ loading: false, records: data.synced_records, error: null });
        setSyncProgress(0);
      }, 500);
    } catch (err) {
      clearInterval(progressInterval);
      setSyncStatus({ loading: false, records: null, error: err.message });
      setSyncProgress(0);
    }
  };

  const fetchMetadata = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8000/api/v1/meta/schools-departments');
      if (response.ok) {
        const data = await response.json();
        if (data.schools && data.schools.length > 0) {
          setSchools(data.schools);
          const initialSchool = data.schools[0];
          setSelectedSchool(initialSchool);
          
          // 動態獲取預設學校的對應科系
          const deptResponse = await fetch(`http://127.0.0.1:8000/api/v1/meta/schools/${encodeURIComponent(initialSchool)}/departments`);
          if (deptResponse.ok) {
            const deptData = await deptResponse.json();
            if (deptData.departments && deptData.departments.length > 0) {
              setDepartments(deptData.departments);
              setSelectedDept(deptData.departments[0]);
              return { schools: data.schools, departments: deptData.departments };
            }
          }
        }
        return data;
      }
    } catch (err) {
      console.error("無法動態載入學校與科系 metadata 清單:", err);
    }
    return null;
  };

  const handleSchoolChange = async (schoolName) => {
    setSelectedSchool(schoolName);
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/v1/meta/schools/${encodeURIComponent(schoolName)}/departments`);
      if (response.ok) {
        const data = await response.json();
        if (data.departments && data.departments.length > 0) {
          setDepartments(data.departments);
          setSelectedDept(data.departments[0]);
        }
      }
    } catch (err) {
      console.error("無法動態載入該校科系清單:", err);
    }
  };

  // 2. 觸發多智能體綜合決策分析
  const handleAnalyze = async (e, schoolOverride = null, deptOverride = null) => {
    if (e) e.preventDefault();
    setAnalysisLoading(true);
    setAnalysisError(null);
    setAnalysisProgress(5);
    setAnalysisStepText('正在啟動多智能體分析系統...');

    const progressInterval = setInterval(() => {
      setAnalysisProgress((prev) => {
        let nextProgress = prev + Math.floor(Math.random() * 8) + 3;
        if (nextProgress >= 98) {
          nextProgress = 98;
        }
        
        // 根據進度更新步驟文字
        if (nextProgress < 30) {
          setAnalysisStepText('Evidence Layer: 正在檢索科系招生註冊率與歷史就業薪資數據...');
        } else if (nextProgress < 60) {
          setAnalysisStepText('Reasoning Layer: 正在推理評估就業市場競爭與少子化風險因素...');
        } else if (nextProgress < 85) {
          setAnalysisStepText('Decision Layer: 正在綜合各智能體意見評估適配度並提供策略建議...');
        } else {
          setAnalysisStepText('正在彙整結構化決策報告...');
        }
        
        return nextProgress;
      });
    }, 250);

    try {
      const response = await fetch('http://127.0.0.1:8000/api/v1/agent/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          school_name: schoolOverride || selectedSchool,
          department_name: deptOverride || selectedDept,
          user_preferences: preferences
        })
      });
      if (!response.ok) throw new Error('分析請求失敗，請確認後端已開啟');
      const data = await response.json();
      
      clearInterval(progressInterval);
      setAnalysisProgress(100);
      setAnalysisStepText('決策報告分析完成！');
      
      setTimeout(() => {
        setAnalysisResult(data);
        setAnalysisLoading(false);
        setAnalysisProgress(0);
        if (data.study_field) {
          setSelectedField(data.study_field);
          handleForecast(null, data.study_field);
        }
      }, 500);
    } catch (err) {
      clearInterval(progressInterval);
      setAnalysisError(err.message);
      setAnalysisLoading(false);
      setAnalysisProgress(0);
    }
  };

  // 3. 觸發薪資預測回歸模型
  const handleForecast = async (e, fieldOverride = null) => {
    if (e && e.preventDefault) e.preventDefault();
    setForecastLoading(true);
    try {
      const response = await fetch('http://127.0.0.1:8000/api/v1/forecast/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          study_field: fieldOverride || selectedField,
          target_years: parseInt(targetYears)
        })
      });
      if (!response.ok) throw new Error('預測請求失敗');
      const data = await response.json();
      setForecastResult(data);
    } catch (err) {
      console.error(err);
    } finally {
      setForecastLoading(false);
    }
  };

  // 頁面初次載入時自動做一次分析以便預覽，並加載後端載入完的動態學校與科系清單
  useEffect(() => {
    fetchMetadata().then((data) => {
      // 確保使用從後端剛撈回來的最新第一個學校與科系，而非未渲染完的狀態機舊值
      const initialSchool = data && data.schools && data.schools.length > 0 ? data.schools[0] : '國立政治大學';
      const initialDept = data && data.departments && data.departments.length > 0 ? data.departments[0] : '歷史學系';
      
      handleAnalyze(null, initialSchool, initialDept);
      handleForecast();
    });
  }, []);

  return (
    <div className="app-container">
      {/* 側邊導航欄 Sidebar */}
      <aside className="sidebar">
        <div>
          <div className="logo-section">
            <div className="logo-icon">
              <BrainCircuit size={24} />
            </div>
            <span className="logo-text">EduCareer-AI</span>
          </div>
          <ul className="nav-links">
            <li 
              className={`nav-item ${activeTab === 'analyze' ? 'active' : ''}`}
              onClick={() => setActiveTab('analyze')}
            >
              <BrainCircuit size={18} />
              決策導航 console
            </li>
            <li 
              className={`nav-item ${activeTab === 'sync' ? 'active' : ''}`}
              onClick={() => setActiveTab('sync')}
            >
              <Database size={18} />
              資料庫同步
            </li>
          </ul>
        </div>
        <div className="sidebar-footer">
          EduCareer-AI Support v1.0.0
        </div>
      </aside>

      {/* 主內容區 Main Content */}
      <main className="main-content">
        <header>
          <div>
            <h1>EduCareer-AI 決策支援系統</h1>
            <p className="header-subtitle">基於政府教育與勞動數據的決策安全升學職涯規劃導航</p>
          </div>
        </header>

        {activeTab === 'analyze' ? (
          <div>
            {/* 使用者輸入面板 Query Console */}
            <div className="glass-card mb-4" style={{ marginBottom: '2rem' }}>
              <h2 style={{ fontSize: '1.25rem', marginBottom: '1.5rem', fontWeight: 600 }}>決策設定主控制台</h2>
              <form onSubmit={handleAnalyze} className="form-grid">
                <div className="form-group">
                  <label>目標學校</label>
                  <select 
                    value={selectedSchool} 
                    onChange={(e) => handleSchoolChange(e.target.value)}
                  >
                    {schools.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>科系名稱</label>
                  <select 
                    value={selectedDept} 
                    onChange={(e) => setSelectedDept(e.target.value)}
                  >
                    {departments.map(d => <option key={d} value={d}>{d}</option>)}
                  </select>
                </div>
                <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                  <label>職涯偏好條件</label>
                  <div className="preference-pool">
                    {preferenceOptions.map(pref => (
                      <button
                        key={pref}
                        type="button"
                        className={`tag-btn ${preferences.includes(pref) ? 'selected' : ''}`}
                        onClick={() => togglePreference(pref)}
                      >
                        {pref}
                      </button>
                    ))}
                  </div>
                </div>
                <div style={{ gridColumn: '1 / -1', textAlign: 'right', marginTop: '0.5rem' }}>
                  <button type="submit" className="btn-primary" disabled={analysisLoading}>
                    {analysisLoading ? <RefreshCw size={16} className="animate-spin" /> : <Search size={16} />}
                    開始多智能體分析
                  </button>
                </div>
                {analysisLoading && (
                  <div style={{ gridColumn: '1 / -1', marginTop: '1.5rem', animation: 'fadeIn 0.3s ease-out' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--primary)' }}>
                        <RefreshCw size={14} className="animate-spin" />
                        {analysisStepText}
                      </span>
                      <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 'bold', color: 'var(--primary)' }}>{analysisProgress}%</span>
                    </div>
                    <div style={{ width: '100%', height: '8px', background: 'rgba(255,255,255,0.05)', borderRadius: '999px', overflow: 'hidden', border: '1px solid var(--border)' }}>
                      <div style={{ width: `${analysisProgress}%`, height: '100%', background: 'linear-gradient(to right, var(--primary), var(--secondary))', transition: 'width 0.3s ease-out', borderRadius: '999px' }} />
                    </div>
                  </div>
                )}
              </form>
            </div>

            {/* AI 決策報告 Viewer */}
            {analysisError && (
              <div className="custom-alert">
                <AlertTriangle size={18} />
                <span>錯誤: {analysisError}。請點選上方「資料庫同步」分頁並同步資料庫，或確認後端啟動中。</span>
              </div>
            )}

            {analysisResult && (
              <div className="agent-report-container">
                <div className="glass-card pulse-glow" style={{ borderLeft: '5px solid var(--accent-green)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <h3 style={{ fontSize: '1.4rem', fontWeight: 700 }}>{analysisResult.school_name} - {analysisResult.department_name}</h3>
                      <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '0.2rem' }}>
                        決策支援分數: <span style={{ color: 'var(--accent-green)', fontWeight: 'bold', fontSize: '1.1rem' }}>{analysisResult.decision_layer.suitability_score} / 100</span>
                      </p>
                    </div>
                    <div className="layer-badge badge-decision" style={{ fontSize: '1rem', padding: '0.5rem 1rem' }}>
                      決策安全指數高
                    </div>
                  </div>
                </div>

                {/* 三層 Agent 架構 */}
                <div className="agent-grid">
                  {/* Layer 1: Evidence Layer */}
                  <div className="glass-card agent-card">
                    <div className="agent-header">
                      <div className="layer-badge badge-evidence">Evidence Layer</div>
                      <span className="agent-title">證據擷取代理</span>
                    </div>
                    <div className="kv-grid">
                      <span className="kv-key">最新新生註冊率</span>
                      <span className="kv-value" style={{ color: 'var(--accent-cyan)' }}>
                        {analysisResult.evidence_layer.registration_rate !== null ? `${analysisResult.evidence_layer.registration_rate}%` : '資料未公佈'}
                      </span>

                      <span className="kv-key">在學學生總人數</span>
                      <span className="kv-value">{analysisResult.evidence_layer.current_student_count} 人</span>
                    </div>
                    <div style={{ marginTop: '0.5rem' }}>
                      <h4 style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>歷史與模擬薪資基準點</h4>
                      <div className="kv-grid">
                        {Object.entries(analysisResult.evidence_layer.historical_salary_points).map(([k, v]) => (
                          <React.Fragment key={k}>
                            <span className="kv-key">{k}</span>
                            <span className="kv-value">${v.toLocaleString()}</span>
                          </React.Fragment>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Layer 2: Reasoning Layer */}
                  <div className="glass-card agent-card">
                    <div className="agent-header">
                      <div className="layer-badge badge-reasoning">Reasoning Layer</div>
                      <span className="agent-title">推理引擎代理</span>
                    </div>
                    <div className="kv-grid" style={{ marginBottom: '0.5rem' }}>
                      <span className="kv-key">市場就業需求級別</span>
                      <span className="kv-value" style={{ 
                        color: analysisResult.reasoning_layer.market_demand_level === '高' ? 'var(--accent-green)' : 'var(--accent-amber)'
                      }}>{analysisResult.reasoning_layer.market_demand_level}</span>
                    </div>
                    <div>
                      <h4 style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>學群競爭態勢</h4>
                      <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                        {analysisResult.reasoning_layer.competition_analysis}
                      </p>
                    </div>
                    <div style={{ marginTop: '0.5rem' }}>
                      <h4 style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>風險示警 (Risk Factors)</h4>
                      <ul className="bullet-list">
                        {analysisResult.reasoning_layer.risk_factors.map((r, i) => (
                          <li key={i} className="bullet-item">{r}</li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {/* Layer 3: Decision Layer */}
                  <div className="glass-card agent-card">
                    <div className="agent-header">
                      <div className="layer-badge badge-decision">Decision Layer</div>
                      <span className="agent-title">終端決策決策</span>
                    </div>
                    <div>
                      <h4 style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>建議職涯方向</h4>
                      <div className="preference-pool" style={{ marginBottom: '1rem' }}>
                        {analysisResult.decision_layer.suggested_career_paths.map((p, i) => (
                          <span key={i} className="tag-btn selected" style={{ pointerEvents: 'none' }}>{p}</span>
                        ))}
                      </div>
                    </div>
                    <div>
                      <h4 style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>升學與職涯策略規劃</h4>
                      <ul className="bullet-list">
                        {analysisResult.decision_layer.strategic_recommendations.map((r, i) => (
                          <li key={i} className="bullet-item" style={{ color: 'var(--text-primary)' }}>{r}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* 薪資回歸預測模組 UI (額外展示) */}
            <div className="glass-card" style={{ marginTop: '2rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem' }}>
                <TrendingUp size={20} style={{ color: 'var(--primary)' }} />
                <h3 style={{ fontSize: '1.25rem', fontWeight: 600 }}>學門薪資連續回歸預測模型</h3>
              </div>
              <div className="form-grid" style={{ marginBottom: '1.5rem' }}>
                <div className="form-group">
                  <label>學門分類</label>
                  <select value={selectedField} onChange={(e) => setSelectedField(e.target.value)}>
                    <option value="資訊工程">資訊工程</option>
                    <option value="電機電子">電機電子</option>
                    <option value="商業管理">商業管理</option>
                    <option value="人文社會">人文社會</option>
                    <option value="基礎科學">基礎科學</option>
                    <option value="其他學門">其他學門</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>目標畢業後預測年資 (1 - 10 年)</label>
                  <input 
                    type="number" 
                    value={targetYears} 
                    onChange={(e) => setTargetYears(e.target.value)}
                    min="1" max="10"
                  />
                </div>
              </div>
              <div style={{ textAlign: 'right', marginBottom: '1.5rem' }}>
                <button type="button" className="btn-primary" onClick={handleForecast} disabled={forecastLoading}>
                  <LineChart size={16} /> 執行回歸預測
                </button>
              </div>

              {forecastResult && (
                <div className="glass-card" style={{ background: 'rgba(0, 0, 0, 0.2)', border: '1px dashed var(--border)' }}>
                  {forecastResult.warning && (
                    <div className="custom-alert">
                      <AlertTriangle size={18} />
                      <span><strong>預測安全性示警:</strong> {forecastResult.warning}</span>
                    </div>
                  )}
                  <div className="kv-grid">
                    <span className="kv-key">指定學門</span>
                    <span className="kv-value">{forecastResult.study_field}</span>

                    <span className="kv-key">畢業 {targetYears} 年薪資預測</span>
                    <span className="kv-value" style={{ color: 'var(--accent-green)', fontWeight: 'bold' }}>
                      ${forecastResult.predicted_salary.toLocaleString()} 元
                    </span>

                    <span className="kv-key">模型驗證誤差 (MAPE)</span>
                    <span className="kv-value">{forecastResult.model_mape}%</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : (
          /* 同步管理控制台 DataSyncPanel */
          <div className="glass-card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
              <Database size={24} style={{ color: 'var(--primary)' }} />
              <h2 style={{ fontSize: '1.25rem', fontWeight: 600 }}>資料動態歸一化狀態監控</h2>
            </div>
            
            <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem', lineHeight: 1.6 }}>
              本系統之動態歸一化管道 (Data Ingestion Pipeline) 能自動推論政府開放資料的 Schema 變化，
              在不使用 Hard-coded Rules 的情況下，動態容錯未知欄位。點擊下方按鈕即可同步。
            </p>

            <div className="dashboard-grid">
              <div className="glass-card stat-card">
                <div className="stat-icon"><GraduationCap size={24} /></div>
                <div>
                  <div className="stat-label">最新科系註冊率資料</div>
                  <div className="stat-value">學12-1.csv</div>
                </div>
              </div>
              <div className="glass-card stat-card">
                <div className="stat-icon"><Database size={24} /></div>
                <div>
                  <div className="stat-label">在學學生數結構</div>
                  <div className="stat-value">106-112學年.json</div>
                </div>
              </div>
            </div>

            {syncStatus.error && (
              <div className="custom-alert">
                <AlertTriangle size={18} />
                <span>錯誤: {syncStatus.error}。請確定 FastAPI 伺服器已正常啟動在埠口 8000。</span>
              </div>
            )}

            {syncStatus.records !== null && (
              <div className="glass-card" style={{ borderColor: 'var(--accent-green)', background: 'rgba(16, 185, 129, 0.05)', marginBottom: '1.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--accent-green)' }}>
                  <CheckCircle2 size={18} />
                  <span>成功歸一化並匯入 {syncStatus.records} 筆學生數與新生註冊率交叉比對紀錄！</span>
                </div>
              </div>
            )}

            {syncStatus.loading && (
              <div style={{ marginBottom: '1.5rem', animation: 'fadeIn 0.3s ease-out' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                  <span>正在解析大專校院各校科系學生與註冊率開放資料...</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 'bold', color: 'var(--primary)' }}>{syncProgress}%</span>
                </div>
                <div style={{ width: '100%', height: '8px', background: 'rgba(255,255,255,0.05)', borderRadius: '999px', overflow: 'hidden', border: '1px solid var(--border)' }}>
                  <div style={{ width: `${syncProgress}%`, height: '100%', background: 'linear-gradient(to right, var(--primary), var(--secondary))', transition: 'width 0.3s ease-out', borderRadius: '999px' }} />
                </div>
              </div>
            )}

            <button 
              className="btn-primary" 
              onClick={handleSync} 
              disabled={syncStatus.loading}
            >
              <RefreshCw size={16} className={syncStatus.loading ? "animate-spin" : ""} />
              {syncStatus.loading ? '進行動態歸一化中...' : '立即觸發 Ingestion Pipeline'}
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
