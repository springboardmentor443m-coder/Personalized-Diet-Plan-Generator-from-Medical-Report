import React from 'react';
import { Camera, ShoppingCart, Languages, Download, Check } from 'lucide-react';
import { Language } from '../types';

export const SnapTrackMock: React.FC = () => {
  const [active, setActive] = React.useState(false);

  const handleClick = () => {
    setActive(true);
    setTimeout(() => {
        alert("📸 Camera access simulated!\nIn a real deployment, this opens the webcam to scan food.");
        setActive(false);
    }, 500);
  }

  return (
    <div className="bg-white p-6 rounded-xl shadow border border-slate-200 text-center">
      <div className="mx-auto w-16 h-16 bg-purple-100 text-purple-600 rounded-full flex items-center justify-center mb-4">
        <Camera size={32} />
      </div>
      <h3 className="text-lg font-bold text-slate-800">Snap & Track (Beta)</h3>
      <p className="text-sm text-slate-500 mb-4">Take a photo of your food to check if it matches your diet plan.</p>
      <button 
        onClick={handleClick}
        className="bg-purple-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-purple-700 transition flex items-center justify-center gap-2 w-full"
      >
        {active ? "Opening..." : "Open Camera"}
      </button>
    </div>
  );
};

export const GroceryListMock: React.FC = () => {
    const [exported, setExported] = React.useState(false);

    const handleExport = () => {
        setExported(true);
        setTimeout(() => {
            alert("🛒 Grocery List Exported to JSON!\nCheck your console or download folder in a real app.");
            setExported(false);
        }, 800);
    };

    return (
      <div className="bg-white p-6 rounded-xl shadow border border-slate-200">
        <div className="flex items-center gap-2 mb-4">
          <ShoppingCart className="text-emerald-600" />
          <h3 className="text-lg font-bold text-slate-800">Auto-Grocery List</h3>
        </div>
        <ul className="space-y-2 text-sm text-slate-700">
          <li className="flex items-center"><input type="checkbox" className="mr-2 accent-emerald-600"/> Rolled Oats (500g)</li>
          <li className="flex items-center"><input type="checkbox" className="mr-2 accent-emerald-600"/> Multigrain Atta (1kg)</li>
          <li className="flex items-center"><input type="checkbox" className="mr-2 accent-emerald-600"/> Olive Oil / Ghee</li>
          <li className="flex items-center"><input type="checkbox" className="mr-2 accent-emerald-600"/> Chia Seeds</li>
        </ul>
        <button 
            onClick={handleExport}
            className="mt-4 w-full text-emerald-600 border border-emerald-600 rounded py-1 text-xs hover:bg-emerald-50 flex items-center justify-center gap-2"
        >
          {exported ? <><Check size={14}/> List Saved</> : "Export List"}
        </button>
      </div>
    );
};

interface LangSelectorProps {
    currentLang: Language;
    onLanguageChange: (lang: Language) => void;
}

export const LanguageSelector: React.FC<LangSelectorProps> = ({ currentLang, onLanguageChange }) => (
  <div className="flex items-center gap-2 bg-slate-100 px-3 py-1.5 rounded-full border border-slate-200">
    <Languages size={16} className="text-slate-600" />
    <select 
        value={currentLang}
        onChange={(e) => onLanguageChange(e.target.value as Language)}
        className="bg-transparent border-none text-sm text-slate-700 focus:outline-none cursor-pointer w-24"
    >
      <option value="en">English</option>
      <option value="hi">हिंदी</option>
      <option value="gu">ગુજરાતી</option>
      <option value="te">తెలుగు</option>
    </select>
  </div>
);

interface DownloadProps {
    onDownload: () => void;
    label: string;
}

export const DownloadPDF: React.FC<DownloadProps> = ({ onDownload, label }) => (
    <button 
        onClick={onDownload}
        className="flex items-center gap-2 bg-slate-800 text-white px-4 py-2 rounded-lg text-sm hover:bg-slate-900 transition shadow"
    >
        <Download size={16} />
        {label}
    </button>
);