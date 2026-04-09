import React, { useState } from 'react';
import { Upload, FileText, CheckCircle, Loader2 } from 'lucide-react';
import { Language } from '../types';
import { getTranslation } from '../utils/translations';

interface FileUploadProps {
  onAnalyze: (file: File) => void;
  isAnalyzing: boolean;
  lang: Language;
}

const FileUpload: React.FC<FileUploadProps> = ({ onAnalyze, isAnalyzing, lang }) => {
  const [file, setFile] = useState<File | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="max-w-2xl mx-auto mt-10 p-6 bg-white rounded-xl shadow-lg border border-slate-200">
      <div className="text-center mb-6">
        <h2 className="text-2xl font-bold text-slate-800">{getTranslation(lang, 'upload_title')}</h2>
        <p className="text-slate-500">{getTranslation(lang, 'upload_desc')}</p>
      </div>

      <div 
        className={`border-2 border-dashed rounded-xl p-10 flex flex-col items-center justify-center transition-colors cursor-pointer
          ${file ? 'border-emerald-500 bg-emerald-50' : 'border-slate-300 hover:border-blue-500 hover:bg-slate-50'}`}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        onClick={() => document.getElementById('fileInput')?.click()}
      >
        <input 
          type="file" 
          id="fileInput" 
          className="hidden" 
          onChange={handleFileChange} 
          accept=".pdf,.png,.jpg,.jpeg"
        />
        
        {file ? (
          <div className="flex flex-col items-center text-emerald-600">
            <CheckCircle size={48} className="mb-2" />
            <p className="font-medium text-lg">{file.name}</p>
            <p className="text-sm text-emerald-500">{(file.size / 1024).toFixed(2)} KB</p>
          </div>
        ) : (
          <div className="flex flex-col items-center text-slate-400">
            <Upload size={48} className="mb-2" />
            <p className="font-medium text-lg text-slate-600">{getTranslation(lang, 'upload_btn')}</p>
          </div>
        )}
      </div>

      <button
        onClick={() => file && onAnalyze(file)}
        disabled={!file || isAnalyzing}
        className={`w-full mt-6 py-3 rounded-lg flex items-center justify-center text-white font-semibold transition-all
          ${!file || isAnalyzing ? 'bg-slate-300 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 shadow-md hover:shadow-lg'}`}
      >
        {isAnalyzing ? (
          <>
            <Loader2 className="animate-spin mr-2" />
            {getTranslation(lang, 'analyzing')}
          </>
        ) : (
          <>
            <FileText className="mr-2" />
            {getTranslation(lang, 'analyze_btn')}
          </>
        )}
      </button>

      {isAnalyzing && (
        <div className="mt-4 space-y-2">
          <div className="text-xs text-slate-500 flex justify-between">
            <span>Extracting Text (OCR)...</span>
            <span>25%</span>
          </div>
          <div className="h-1.5 w-full bg-slate-200 rounded-full overflow-hidden">
            <div className="h-full bg-blue-500 animate-[width_2s_ease-in-out_infinite]" style={{width: '60%'}}></div>
          </div>
          <p className="text-xs text-center text-slate-400">Running ML Classifiers (XGBoost)...</p>
        </div>
      )}
    </div>
  );
};

export default FileUpload;