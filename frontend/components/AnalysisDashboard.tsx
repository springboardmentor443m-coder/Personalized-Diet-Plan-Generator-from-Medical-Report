import React from 'react';
import { HealthMetrics, PredictionResult, Language } from '../types';
import { Activity, Heart, AlertTriangle, TrendingUp } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';
import { getTranslation } from '../utils/translations';

interface Props {
  metrics: HealthMetrics;
  predictions: PredictionResult;
  lang: Language;
}

const AnalysisDashboard: React.FC<Props> = ({ metrics, predictions, lang }) => {
  const chartData = [
    { name: 'Glucose', value: metrics.glucose, limit: 140, unit: 'mg/dL' },
    { name: 'Cholesterol', value: metrics.cholesterol, limit: 200, unit: 'mg/dL' },
    { name: 'BP (Sys)', value: 130, limit: 120, unit: 'mmHg' },
    { name: 'Insulin', value: metrics.insulin, limit: 160, unit: 'mu U/ml' },
  ];

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Alerts Section */}
      {predictions.criticalAlerts.length > 0 && (
        <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-r-lg shadow-sm">
          <div className="flex">
            <AlertTriangle className="h-6 w-6 text-red-500 mr-3" />
            <div>
              <h3 className="text-red-800 font-bold">Medical Attention Required</h3>
              <ul className="list-disc list-inside text-red-700 mt-1 space-y-1">
                {predictions.criticalAlerts.map((alert, idx) => (
                  <li key={idx}>{alert}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* ML Prediction Cards */}
        <div className={`p-6 rounded-xl shadow-md border ${predictions.hasDiabetes ? 'bg-orange-50 border-orange-200' : 'bg-green-50 border-green-200'}`}>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-semibold text-slate-800">Diabetes Prediction</h3>
            <Activity className={predictions.hasDiabetes ? 'text-orange-500' : 'text-green-500'} />
          </div>
          <p className={`text-2xl font-bold ${predictions.hasDiabetes ? 'text-orange-700' : 'text-green-700'}`}>
            {predictions.hasDiabetes ? 'High Risk Detected' : 'Low Risk'}
          </p>
          <p className="text-sm text-slate-600 mt-1">{getTranslation(lang, 'confidence')}: {(predictions.diabetesProbability * 100).toFixed(1)}%</p>
        </div>

        <div className={`p-6 rounded-xl shadow-md border ${predictions.riskHeartDisease ? 'bg-red-50 border-red-200' : 'bg-green-50 border-green-200'}`}>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-semibold text-slate-800">Heart Disease Risk</h3>
            <Heart className={predictions.riskHeartDisease ? 'text-red-500' : 'text-green-500'} />
          </div>
          <p className={`text-2xl font-bold ${predictions.riskHeartDisease ? 'text-red-700' : 'text-green-700'}`}>
            {predictions.riskHeartDisease ? 'Elevated Risk' : 'Normal'}
          </p>
          <p className="text-sm text-slate-600 mt-1">{getTranslation(lang, 'confidence')}: {(predictions.heartRiskProbability * 100).toFixed(1)}%</p>
        </div>
      </div>

      {/* Charts */}
      <div className="bg-white p-6 rounded-xl shadow-lg border border-slate-200">
        <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center">
          <TrendingUp className="mr-2 text-blue-600" /> Extracted Metrics vs. Safe Limits
        </h3>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip 
                contentStyle={{ backgroundColor: '#fff', borderRadius: '8px' }}
                cursor={{ fill: 'transparent' }}
              />
              <Legend />
              <Bar dataKey="value" fill="#3b82f6" name="Patient Value" radius={[4, 4, 0, 0]} barSize={50} />
              <ReferenceLine y={0} stroke="#000" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default AnalysisDashboard;