import React, { useState, useEffect } from 'react';
import { Activity, LayoutDashboard, Utensils, Settings, LogOut } from 'lucide-react';
import FileUpload from './components/FileUpload';
import AnalysisDashboard from './components/AnalysisDashboard';
import DietPlanView from './components/DietPlanView';
import { SnapTrackMock, GroceryListMock, LanguageSelector, DownloadPDF } from './components/ExtraFeatures';
import { analyzeMedicalReport, generateDietPlan } from './services/mockBackend';
import { HealthMetrics, PredictionResult, DietPlanFull, Language } from './types';
import { getTranslation } from './utils/translations';
import { generatePDF } from './utils/pdfGenerator';

enum AppStep {
  UPLOAD,
  DASHBOARD,
  DIET_PLAN
}

const App: React.FC = () => {
  const [currentStep, setCurrentStep] = useState<AppStep>(AppStep.UPLOAD);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [healthData, setHealthData] = useState<{ metrics: HealthMetrics; predictions: PredictionResult } | null>(null);
  const [dietPlan, setDietPlan] = useState<DietPlanFull | null>(null);
  const [language, setLanguage] = useState<Language>('en');

  // Re-generate plan if language changes
  useEffect(() => {
    const updatePlanLang = async () => {
        if (dietPlan && healthData) {
            const newPlan = await generateDietPlan(healthData.metrics, language);
            setDietPlan(newPlan);
        }
    };
    updatePlanLang();
  }, [language]);

  const handleAnalyze = async (file: File) => {
    setIsAnalyzing(true);
    try {
      const data = await analyzeMedicalReport(file);
      setHealthData(data);
      
      const plan = await generateDietPlan(data.metrics, language);
      setDietPlan(plan);
      
      setCurrentStep(AppStep.DASHBOARD);
    } catch (error) {
      console.error("Analysis failed", error);
      alert("Error processing file. Please try again.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleDownloadPDF = () => {
    if (dietPlan && healthData) {
        generatePDF(dietPlan, healthData.metrics, "John Doe");
    } else {
        alert("Please generate a diet plan first.");
    }
  };

  return (
    <div className="min-h-screen flex bg-slate-50">
      {/* Sidebar Navigation */}
      <aside className="w-64 bg-slate-900 text-white hidden md:flex flex-col fixed h-full z-10">
        <div className="p-6 border-b border-slate-700">
          <div className="flex items-center gap-2 text-emerald-400 font-bold text-xl">
            <Activity />
            <span>AI-NutriCare</span>
          </div>
          <p className="text-xs text-slate-400 mt-1">Infosys Internship Project</p>
        </div>
        
        <nav className="flex-1 p-4 space-y-2">
          <button 
            onClick={() => setCurrentStep(AppStep.UPLOAD)}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${currentStep === AppStep.UPLOAD ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'}`}
          >
            <Settings size={20} /> {getTranslation(language, 'nav_upload')}
          </button>
          <button 
             onClick={() => healthData && setCurrentStep(AppStep.DASHBOARD)}
             disabled={!healthData}
             className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${currentStep === AppStep.DASHBOARD ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed'}`}
          >
            <LayoutDashboard size={20} /> {getTranslation(language, 'nav_analysis')}
          </button>
          <button 
             onClick={() => dietPlan && setCurrentStep(AppStep.DIET_PLAN)}
             disabled={!dietPlan}
             className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${currentStep === AppStep.DIET_PLAN ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed'}`}
          >
            <Utensils size={20} /> {getTranslation(language, 'nav_diet')}
          </button>
        </nav>

        <div className="p-4 border-t border-slate-700">
          <button className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors">
            <LogOut size={18} /> {getTranslation(language, 'logout')}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 md:ml-64 p-4 md:p-8 overflow-y-auto">
        {/* Top Header */}
        <header className="flex justify-between items-center mb-8 bg-white p-4 rounded-xl shadow-sm border border-slate-100 sticky top-0 z-20">
          <h1 className="text-xl font-bold text-slate-800">
            {currentStep === AppStep.UPLOAD && getTranslation(language, 'upload_title')}
            {currentStep === AppStep.DASHBOARD && getTranslation(language, 'dashboard_title')}
            {currentStep === AppStep.DIET_PLAN && getTranslation(language, 'diet_title')}
          </h1>
          <div className="flex items-center gap-4">
            <LanguageSelector currentLang={language} onLanguageChange={setLanguage} />
            {currentStep !== AppStep.UPLOAD && <DownloadPDF onDownload={handleDownloadPDF} label={getTranslation(language, 'download_pdf')} />}
            <div className="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold border border-blue-200">
              JD
            </div>
          </div>
        </header>

        {/* Content Area */}
        <div className="max-w-5xl mx-auto">
          {currentStep === AppStep.UPLOAD && (
            <div className="animate-fade-in">
                <div className="mb-8">
                    <h2 className="text-3xl font-bold text-slate-800 text-center">{getTranslation(language, 'welcome')}</h2>
                    <p className="text-center text-slate-500 mt-2">{getTranslation(language, 'welcome_sub')}</p>
                </div>
                <FileUpload onAnalyze={handleAnalyze} isAnalyzing={isAnalyzing} lang={language} />
            </div>
          )}

          {currentStep === AppStep.DASHBOARD && healthData && (
            <AnalysisDashboard metrics={healthData.metrics} predictions={healthData.predictions} lang={language} />
          )}

          {currentStep === AppStep.DIET_PLAN && dietPlan && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 animate-fade-in">
              <div className="lg:col-span-2">
                <DietPlanView plan={dietPlan} lang={language} />
              </div>
              <div className="space-y-6">
                <SnapTrackMock />
                <GroceryListMock />
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default App;