import React, { useState } from 'react';
import { DietPlanFull, DailyPlan, MealOption, Language } from '../types';
import { ChevronDown, ChevronUp, Coffee, Sun, Moon, Utensils, Info, CheckCircle2, RotateCcw } from 'lucide-react';
import { getTranslation } from '../utils/translations';

interface Props {
  plan: DietPlanFull;
  lang: Language;
}

const MealCard: React.FC<{ 
  title: string; 
  icon: React.ReactNode; 
  option: MealOption; 
  altOption: MealOption; 
  colorClass: string;
  lang: Language;
}> = ({ title, icon, option, altOption, colorClass, lang }) => {
  const [showAlt, setShowAlt] = useState(false);

  const current = showAlt ? altOption : option;

  return (
    <div className={`border-l-4 ${colorClass} bg-white rounded-lg shadow-sm p-4 relative group hover:shadow-md transition-shadow`}>
      <div className="flex justify-between items-start">
        <div className="flex items-center gap-2 mb-2">
          {icon}
          <h4 className="font-semibold text-slate-700">{title}</h4>
        </div>
        <button 
          onClick={() => setShowAlt(!showAlt)}
          className="text-xs text-blue-600 hover:underline flex items-center bg-blue-50 px-2 py-1 rounded"
        >
          <RotateCcw size={12} className="mr-1" />
          {showAlt ? getTranslation(lang, 'original') : getTranslation(lang, 'alternative')}
        </button>
      </div>

      <div className="mb-2">
        <p className="text-slate-800 font-medium text-lg">{current.name}</p>
        <p className="text-slate-500 text-sm">{current.calories} {getTranslation(lang, 'calories')}</p>
      </div>

      <div className="bg-slate-50 p-2 rounded text-xs text-slate-600 flex items-start gap-1">
        <Info size={14} className="mt-0.5 text-blue-400 flex-shrink-0" />
        <span className="italic">{getTranslation(lang, 'why')}: {current.why}</span>
      </div>
    </div>
  );
};

const DietPlanView: React.FC<Props> = ({ plan, lang }) => {
  const [openDay, setOpenDay] = useState<number | null>(0);

  const toggleDay = (index: number) => {
    setOpenDay(openDay === index ? null : index);
  };

  return (
    <div className="space-y-8">
      {/* Header Badge */}
      <div className="bg-gradient-to-r from-emerald-600 to-teal-600 p-6 rounded-xl text-white shadow-lg flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold">{getTranslation(lang, 'diet_title')}</h2>
          <p className="text-emerald-100 opacity-90">Tailored to Diabetes & Heart Health profile</p>
        </div>
        <div className="text-center bg-white/20 p-3 rounded-lg backdrop-blur-sm">
          <span className="block text-3xl font-bold">{plan.confidenceScore}%</span>
          <span className="text-xs uppercase tracking-wider">{getTranslation(lang, 'confidence')}</span>
        </div>
      </div>

      {/* General Recommendations */}
      <div className="bg-white p-6 rounded-xl shadow border border-slate-200">
        <h3 className="text-lg font-bold text-slate-800 mb-4">{getTranslation(lang, 'key_guidelines')}</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {plan.recommendations.map((rec, i) => (
            <div key={i} className="flex items-start gap-2">
              <CheckCircle2 className="text-emerald-500 mt-1 flex-shrink-0" size={18} />
              <p className="text-slate-700">{rec}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Daily Accordion */}
      <div className="space-y-4">
        {plan.weeklyPlan.map((dayPlan, index) => (
          <div key={index} className="border border-slate-200 rounded-xl overflow-hidden bg-white shadow-sm">
            <button 
              onClick={() => toggleDay(index)}
              className="w-full flex justify-between items-center p-4 bg-slate-50 hover:bg-slate-100 transition-colors text-left"
            >
              <span className="font-bold text-lg text-slate-800">{dayPlan.day}</span>
              {openDay === index ? <ChevronUp className="text-slate-500" /> : <ChevronDown className="text-slate-500" />}
            </button>

            {openDay === index && (
              <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4 animate-fade-in bg-slate-50/50">
                <MealCard 
                  title={getTranslation(lang, 'breakfast')} 
                  icon={<Coffee className="text-orange-400" size={18} />} 
                  option={dayPlan.breakfast} 
                  altOption={dayPlan.breakfastAlt}
                  colorClass="border-orange-400"
                  lang={lang}
                />
                <MealCard 
                  title={getTranslation(lang, 'lunch')} 
                  icon={<Sun className="text-yellow-500" size={18} />} 
                  option={dayPlan.lunch} 
                  altOption={dayPlan.lunchAlt}
                  colorClass="border-yellow-500"
                  lang={lang}
                />
                <MealCard 
                  title={getTranslation(lang, 'snack')} 
                  icon={<Utensils className="text-pink-400" size={18} />} 
                  option={dayPlan.snack} 
                  altOption={dayPlan.snackAlt}
                  colorClass="border-pink-400"
                  lang={lang}
                />
                <MealCard 
                  title={getTranslation(lang, 'dinner')} 
                  icon={<Moon className="text-indigo-400" size={18} />} 
                  option={dayPlan.dinner} 
                  altOption={dayPlan.dinnerAlt}
                  colorClass="border-indigo-400"
                  lang={lang}
                />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default DietPlanView;