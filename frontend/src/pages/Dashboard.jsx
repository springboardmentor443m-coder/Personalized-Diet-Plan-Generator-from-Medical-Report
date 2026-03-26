import { useState, useContext, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { uploadReport, downloadStructuredPdf, sendChatMessage } from "../api/reportApi";
import { AuthContext } from "../context/AuthContext";
import "../App.css";

export default function Dashboard() {
  const navigate = useNavigate();
  const { user, logout } = useContext(AuthContext);
  const [file, setFile] = useState(null);
  
  // Need metrics for BMI and Diet generation
  const [formData, setFormData] = useState({
    patientName: "",
    age: "",
    gender: "Male",
    weight: "",
    height: "",
    dietaryPreference: "Non-Vegetarian"
  });

  const [loading, setLoading] = useState(false);
  const [uploadStep, setUploadStep] = useState(0); 
  const [result, setResult] = useState(null);
  
  // --- CHATBOT STATE ---
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [isChatLoading, setIsChatLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (user === null && !localStorage.getItem("token")) {
      navigate("/login");
    }
  }, [user, navigate]);

  // Auto-scroll chat
  useEffect(() => {
     if (messagesEndRef.current) {
        messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
     }
  }, [chatMessages, isChatOpen]);

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleUpload = async () => {
    if (!file) {
      alert("Please selected a scanned medical document.");
      return;
    }
    if (!formData.age || !formData.weight || !formData.height) {
      alert("Please provide Age, Weight, and Height to power the Nutritional BMI Synthesis.");
      return;
    }

    setLoading(true);
    setUploadStep(1);
    setResult(null);

    // Fake pipeline staging for UX
    const timer = setInterval(() => {
      setUploadStep((prev) => (prev < 3 ? prev + 1 : prev));
    }, 2500);

    // API Execution
    const data = await uploadReport(file, formData);
    console.log("Analysis Output:", data);
    
    clearInterval(timer);
    
    if (!data) {
       setUploadStep(0);
       setLoading(false);
       setResult(null);
       alert("Failed to connect to the server. Please try again.");
       return;
    }
    
    setUploadStep(4);
    setResult(data);
    
    // Clear Chat History on new upload
    setChatMessages([{ sender: 'bot', text: 'Hello! I have embedded your medical report into my cognitive database. What would you like to know about your biomarkers or diet plan?' }]);
    setLoading(false);
  };

  const handleSendMessage = async () => {
     if (!chatInput.trim() || !result) return;

     const userMsg = { sender: 'user', text: chatInput };
     setChatMessages(prev => [...prev, userMsg]);
     setChatInput("");
     setIsChatLoading(true);

     const reply = await sendChatMessage(userMsg.text, result.structured_data, result.diet, chatMessages);
     
     const botMsg = { sender: 'bot', text: reply };
     setChatMessages(prev => [...prev, botMsg]);
     setIsChatLoading(false);
  };

  // Pipeline Stepper Messages
  const stepMessages = [
    "",
    "Extracting OCR layers...",
    "Structuring deep biomarker data...",
    "Synthesizing BMI & generating nutritional matrix..."
  ];

  return (
    <div className="dashboard-wrapper">
      <nav className="navbar">
        <div className="nav-container">
          <div className="logo">AI-<span>NutriCare</span></div>
          <div className="user-nav-info">
            <div className="user-details">
              <strong>{user?.full_name || "Guest"}</strong>
              <span>{user?.email || ""}</span>
            </div>
            <button className="btn-logout" onClick={handleLogout}>Logout</button>
          </div>
        </div>
      </nav>

      <div className="main-container dashboard-content section-padding">
        
        {/* Dynamic Header */}
        <div className="dashboard-header-box fade-in">
          {result ? (
            <>
              <h2 className="dashboard-title">Clinical <span className="metallic-gradient-text">Diagnostics</span></h2>
              <p>Your blood work mapped and analyzed by our medical intelligence engine.</p>
            </>
          ) : (
            <>
              <h2 className="dashboard-title">System <span className="metallic-gradient-text">Intake</span></h2>
              <p>Upload a lab report and baseline metrics to generate your actionable profile.</p>
            </>
          )}
        </div>

        {/* INTAKE FORM */}
        {!result && !loading && (
          <div className="bento-card fade-in" style={{ maxWidth: '800px', margin: '0 auto', padding: '40px' }}>
            <h3 style={{ fontFamily: 'Outfit, sans-serif', color: 'var(--deep-slate)', marginBottom: '25px', textAlign: 'center' }}>Step 1: Metric Baseline</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '20px', marginBottom: '20px' }}>
              <div className="input-group">
                <label>Patient Name</label>
                <input type="text" name="patientName" value={formData.patientName} onChange={handleChange} className="glass-input" placeholder="Name on report" />
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '30px' }}>
              <div className="input-group">
                <label>Age</label>
                <input type="number" name="age" value={formData.age} onChange={handleChange} className="glass-input" placeholder="Years" />
              </div>
              <div className="input-group">
                <label>Gender</label>
                <select name="gender" value={formData.gender} onChange={handleChange} className="glass-input">
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                  <option value="Other">Other</option>
                </select>
              </div>
              <div className="input-group">
                <label>Weight (kg)</label>
                <input type="number" name="weight" value={formData.weight} onChange={handleChange} className="glass-input" placeholder="Kilograms" />
              </div>
              <div className="input-group">
                <label>Height (cm)</label>
                <input type="number" name="height" value={formData.height} onChange={handleChange} className="glass-input" placeholder="Centimeters" />
              </div>
              <div className="input-group">
                <label>Dietary Preference</label>
                <select name="dietaryPreference" value={formData.dietaryPreference} onChange={handleChange} className="glass-input">
                  <option value="Vegetarian">Vegetarian</option>
                  <option value="Non-Vegetarian">Non-Vegetarian</option>
                </select>
              </div>
            </div>

            <h3 style={{ fontFamily: 'Outfit, sans-serif', color: 'var(--deep-slate)', marginBottom: '25px', textAlign: 'center' }}>Step 2: Medical Document Upload</h3>
            <div className="upload-section-card clay-card" style={{ background: 'var(--bg-light)' }}>
              <div className="file-input-wrapper">
                <input type="file" id="report-upload" onChange={(e) => setFile(e.target.files[0])} className="hidden-input" accept=".pdf,.png,.jpg,.jpeg"/>
                <label htmlFor="report-upload" className="file-label" style={{ background: 'var(--white)' }}>
                  {file ? file.name : "Select Document (PDF/JPG)"}
                </label>
              </div>
              <button className="clay-btn-primary" onClick={handleUpload}>Run Full Analysis</button>
            </div>
          </div>
        )}

        {/* DYNAMIC PIPELINE LOADER */}
        {loading && (
          <div className="bento-card slide-up-stagger-1" style={{ maxWidth: '600px', margin: '0 auto', textAlign: 'center', padding: '60px' }}>
             <div className="floating-loader" style={{ width: '60px', height: '60px', border: '4px solid var(--lavender-light)', borderTop: '4px solid var(--lavender)', borderRadius: '50%', animation: 'spin 1s linear infinite', margin: '0 auto 30px' }} />
             <h3 style={{ fontFamily: 'Outfit, sans-serif', color: 'var(--lavender)', fontSize: '1.5rem', marginBottom: '10px' }}>System Working</h3>
             <p style={{ color: 'var(--text-gray)', fontSize: '1.1rem' }}>{stepMessages[uploadStep] || "Processing..."}</p>
          </div>
        )}

        {/* RESULTS BENTO GRID (NEW STRUCTURE SCHEMA MAP) */}
        {result && result.success && (
          <div className="result-container fade-in">
             
                <>
                   <div className="result-grid">
                    
                    {/* Patient Context Bento */}
                    <div className="clay-card slide-up-stagger-1">
                      <h3 style={{ borderBottom: '1px solid rgba(0,0,0,0.05)', paddingBottom: '15px' }}>Patient Intel</h3>
                      <div style={{ marginTop: '15px', display: 'flex', flexDirection: 'column', gap: '8px', color: 'var(--text-gray)' }}>
                        <p><strong>Name:</strong> {result.structured_data.patient_information?.patient_name || 'Anonymous'}</p>
                        <p><strong>Age:</strong> {result.structured_data.patient_information?.age_years || '--'} Years</p>
                        <p><strong>Gender:</strong> {result.structured_data.patient_information?.gender || '--'}</p>
                        <p><strong>Physicals:</strong> {result.structured_data.patient_information?.weight_kg}kg | {result.structured_data.patient_information?.height_cm}cm</p>
                        <p><strong>BMI:</strong> {result.structured_data.patient_information?.calculated_bmi || '--'} ({result.structured_data.patient_information?.bmi_category || 'N/A'})</p>
                        <p><strong>Preference:</strong> {result.structured_data.patient_information?.dietary_preference || '--'}</p>
                      </div>
                    </div>

                    {/* Critical Findings Bento */}
                    <div className="clay-card slide-up-stagger-2" style={{ background: 'linear-gradient(145deg, #fffafa, #fff0f0)' }}>
                      <h3 style={{ borderBottom: '1px solid rgba(255,0,0,0.1)', paddingBottom: '15px', color: '#e63946' }}>Abnormal Findings</h3>
                      <div style={{ marginTop: '15px' }}>
                        {result.structured_data.abnormal_findings?.length > 0 ? (
                           result.structured_data.abnormal_findings.map((ab, idx) => {
                             const isCritical = ab.severity?.toLowerCase() === 'critical';
                             return (
                               <div key={idx} style={{ 
                                 padding: '16px', 
                                 background: isCritical ? '#ffe3e3' : '#fff4e6', 
                                 borderRadius: '12px', 
                                 marginBottom: '15px', 
                                 border: isCritical ? '1px solid #ffccd5' : '1px solid #ffd8a8',
                                 color: isCritical ? '#c1121f' : '#854d0e' 
                               }}>
                                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                                    <strong style={{ fontSize: '1.05rem' }}>{ab.test_name || ab.canonical_test_key.replace(/_/g, ' ')}</strong>
                                    <span style={{ 
                                      fontSize: '0.75rem', 
                                      textTransform: 'uppercase', 
                                      fontWeight: 'bold',
                                      background: isCritical ? '#e63946' : '#f59e0b',
                                      color: 'white',
                                      padding: '2px 8px',
                                      borderRadius: '4px'
                                    }}>{ab.severity}</span>
                                  </div>
                                  <p style={{ margin: '0 0 10px', fontSize: '0.95rem' }}>
                                    <strong>Value:</strong> {ab.observed_value} <span style={{ opacity: 0.7 }}>(Ref: {ab.expected_range})</span>
                                  </p>
                                  {ab.insight && (
                                    <div style={{ fontSize: '0.85rem', lineHeight: '1.4', padding: '8px', background: 'rgba(0,0,0,0.03)', borderRadius: '6px' }}>
                                      💡 <em>{ab.insight}</em>
                                    </div>
                                  )}
                               </div>
                             );
                           })
                        ) : (
                           <p style={{ color: 'var(--text-gray)' }}>No critical abnormalities detected.</p>
                        )}
                      </div>
                    </div>

                  </div>

                  {/* Comprehensive Biomarker Layout */}
                  <div className="bento-card slide-up-stagger-3" style={{ marginTop: '40px', padding: '40px', textAlign: 'left' }}>
                     <h3 style={{ fontFamily: 'Outfit, sans-serif', color: 'var(--deep-slate)', marginBottom: '30px' }}>Comprehensive Biomarker Map</h3>
                     
                     {Object.entries(result.structured_data.tests_by_category || {}).map(([category, keys]) => {
                        if (!keys || keys.length === 0) return null;
                        
                        return (
                          <div key={category} style={{ marginBottom: '40px' }}>
                             <h4 style={{ textTransform: 'capitalize', color: 'var(--lavender)', borderBottom: '2px solid var(--lavender-light)', paddingBottom: '10px', marginBottom: '20px' }}>
                                {category.replace(/_/g, ' ')}
                             </h4>
                             <div className="metrics-grid">
                                {keys.map(key => {
                                   const testData = result.structured_data.tests_index?.[key];
                                   if (!testData) return null;
                                   
                                   const isWarning = testData.interpretation === 'high' || testData.interpretation === 'low';
                                   return (
                                     <div key={key} className="metric-pill" style={{ background: isWarning ? '#fff5f5' : 'var(--bg-light)', border: isWarning ? '1px solid #ffccd5' : '1px solid rgba(0,0,0,0.05)' }}>
                                        <strong style={{ fontSize: '0.9rem', color: 'var(--deep-slate)' }}>{testData.test_name}</strong>
                                        <p style={{ margin: '5px 0', fontSize: '1.2rem', color: isWarning ? '#e63946' : 'var(--lavender)' }}>
                                           {testData.value} <span style={{fontSize:'0.8rem', color:'var(--text-gray)'}}>{testData.units}</span>
                                        </p>
                                        <small style={{ color: 'var(--text-gray)' }}>Ref: {testData.reference_range || '--'}</small>
                                     </div>
                                   );
                                })}
                             </div>
                          </div>
                        );
                     })}
                  </div>

                  {/* Diet Engine - Professional Layout */}
                  {result.diet && (
                     <div className="bento-card slide-up-stagger-4" style={{ marginTop: '40px', padding: '40px', background: 'linear-gradient(135deg, rgba(124, 58, 237, 0.05), rgba(0, 0, 0, 0.02))', border: '1px solid rgba(124, 58, 237, 0.1)' }}>
                        
                        {/* Header */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px', flexWrap: 'wrap', gap: '15px' }}>
                           <div>
                              <h3 style={{ fontFamily: 'Outfit, sans-serif', color: 'var(--deep-slate)', fontSize: '1.8rem', margin: 0 }}>🥗 Nutritional Protocol</h3>
                              <p style={{ color: 'var(--text-gray)', margin: '6px 0 0', fontSize: '0.95rem' }}>AI-generated personalized diet plan based on your biomarkers & BMI</p>
                           </div>
                           <button className="clay-btn-secondary" onClick={() => downloadStructuredPdf(result.structured_data, result.diet, user)} style={{ padding: '10px 20px', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                              📄 Download PDF Report
                           </button>
                        </div>

                        {/* Executive Summary Banner */}
                        <div style={{ background: 'linear-gradient(135deg, #7c3aed, #4f46e5)', borderRadius: '16px', padding: '24px 28px', marginBottom: '32px', color: 'white' }}>
                           <p style={{ margin: 0, fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '2px', opacity: 0.75, marginBottom: '8px' }}>Clinical Summary</p>
                           <p style={{ margin: 0, fontSize: '1.15rem', lineHeight: '1.7', fontWeight: '400' }}>
                              {result.diet.executive_summary || 'Baseline nutritional maintenance recommended based on your current biomarker profile.'}
                           </p>
                        </div>

                        {/* Daily Meal Blueprint */}
                        <h4 style={{ fontFamily: 'Outfit, sans-serif', color: 'var(--deep-slate)', fontSize: '1.2rem', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                           <span style={{ background: 'var(--lavender)', color: 'white', borderRadius: '8px', padding: '4px 12px', fontSize: '0.85rem' }}>DAILY PLAN</span> Meal Blueprint
                        </h4>

                        {(() => {
                           const mealMeta = {
                              breakfast: { icon: '🌅', label: 'Breakfast', color: '#fff7ed', border: '#fed7aa', accent: '#ea580c' },
                              lunch:     { icon: '☀️', label: 'Lunch',     color: '#f0fdf4', border: '#bbf7d0', accent: '#16a34a' },
                              dinner:    { icon: '🌙', label: 'Dinner',    color: '#eff6ff', border: '#bfdbfe', accent: '#2563eb' },
                              snacks:    { icon: '🍎', label: 'Snacks',    color: '#fdf4ff', border: '#e9d5ff', accent: '#9333ea' }
                           };
                           return (
                              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '20px', marginBottom: '32px' }}>
                                 {Object.entries(result.diet.daily_plan || {}).map(([meal, desc]) => {
                                    const meta = mealMeta[meal.toLowerCase()] || { icon: '🍽️', label: meal, color: '#f8fafc', border: '#e2e8f0', accent: '#64748b' };
                                    return (
                                       <div key={meal} style={{ background: meta.color, border: `1px solid ${meta.border}`, borderRadius: '16px', padding: '22px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                             <span style={{ fontSize: '1.6rem' }}>{meta.icon}</span>
                                             <div>
                                                <strong style={{ display: 'block', color: meta.accent, fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '1.5px' }}>{meta.label}</strong>
                                             </div>
                                          </div>
                                          <p style={{ margin: 0, color: 'var(--deep-slate)', fontSize: '0.95rem', lineHeight: '1.65', fontWeight: '400', whiteSpace: 'pre-wrap' }}>{desc}</p>
                                       </div>
                                    );
                                 })}
                              </div>
                           );
                        })()}

                        {/* Superfoods + Avoid Row */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
                           
                           {/* Superfoods */}
                           <div style={{ background: 'white', borderRadius: '16px', padding: '24px', border: '1px solid #d1fae5' }}>
                              <h4 style={{ color: '#059669', fontFamily: 'Outfit, sans-serif', fontSize: '1rem', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                 🌿 Focus Superfoods
                              </h4>
                              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                                 {(result.diet.superfoods || []).map((food, idx) => (
                                    <span key={idx} style={{ background: '#d1fae5', color: '#065f46', padding: '6px 14px', borderRadius: '50px', fontSize: '0.85rem', fontWeight: '500' }}>
                                       ✓ {food}
                                    </span>
                                 ))}
                              </div>
                           </div>

                           {/* Foods to Avoid */}
                           <div style={{ background: 'white', borderRadius: '16px', padding: '24px', border: '1px solid #fecdd3' }}>
                              <h4 style={{ color: '#dc2626', fontFamily: 'Outfit, sans-serif', fontSize: '1rem', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                 ⚠️ Foods to Minimize
                              </h4>
                              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                                 {(result.diet.foods_to_avoid || []).map((food, idx) => (
                                    <span key={idx} style={{ background: '#fee2e2', color: '#991b1b', padding: '6px 14px', borderRadius: '50px', fontSize: '0.85rem', fontWeight: '500' }}>
                                       ✗ {food}
                                    </span>
                                 ))}
                              </div>
                           </div>

                        </div>
                     </div>
                  )}
                </>
          </div>
        )}
      </div>

      {/* RAG FLOATING CHAT WIDGET */}
      {result && result.success && (
         <div className="rag-chat-wrapper">
            {isChatOpen ? (
               <div className="chat-window clay-card fade-in" style={{ padding: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                  <div className="chat-header" style={{ background: 'var(--lavender)', color: 'white', padding: '15px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                     <h4 style={{ margin: 0, fontSize: '1.1rem', fontFamily: 'Outfit, sans-serif' }}>AI Clinical Assistant</h4>
                     <button onClick={() => setIsChatOpen(false)} style={{ background: 'transparent', border: 'none', color: 'white', fontSize: '1.2rem', cursor: 'pointer' }}>✖</button>
                  </div>
                  
                  <div className="chat-messages" style={{ flex: 1, padding: '20px', overflowY: 'auto', background: '#f8fafc', display: 'flex', flexDirection: 'column', gap: '15px' }}>
                     {chatMessages.map((msg, idx) => (
                        <div key={idx} style={{ alignSelf: msg.sender === 'user' ? 'flex-end' : 'flex-start', maxWidth: '80%' }}>
                           <div style={{ 
                              background: msg.sender === 'user' ? 'var(--lavender)' : 'white', 
                              color: msg.sender === 'user' ? 'white' : 'var(--deep-slate)', 
                              padding: '12px 18px', 
                              borderRadius: msg.sender === 'user' ? '20px 20px 0 20px' : '20px 20px 20px 0',
                              boxShadow: '0 4px 6px rgba(0,0,0,0.05)',
                              lineHeight: '1.5',
                              fontSize: '0.95rem'
                           }}>
                              {msg.text}
                           </div>
                        </div>
                     ))}
                     {isChatLoading && (
                        <div style={{ alignSelf: 'flex-start' }}>
                           <div style={{ background: 'white', padding: '12px 18px', borderRadius: '20px 20px 20px 0', color: 'var(--text-gray)' }}>
                              Thinking...
                           </div>
                        </div>
                     )}
                     <div ref={messagesEndRef} />
                  </div>

                  <div className="chat-input-area" style={{ padding: '15px', background: 'white', borderTop: '1px solid rgba(0,0,0,0.05)', display: 'flex', gap: '10px' }}>
                     <input 
                        type="text" 
                        value={chatInput}
                        onChange={(e) => setChatInput(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                        placeholder="Ask about your test results..." 
                        style={{ flex: 1, padding: '10px 15px', borderRadius: '20px', border: '1px solid #e2e8f0', outline: 'none' }}
                     />
                     <button className="clay-btn-primary" onClick={handleSendMessage} style={{ padding: '10px 20px', borderRadius: '20px' }}>Send</button>
                  </div>
               </div>
            ) : (
               <button className="chat-fab heartbeat" onClick={() => setIsChatOpen(true)}>
                  💬 Ask AI
               </button>
            )}
         </div>
      )}

    </div>
  );
}