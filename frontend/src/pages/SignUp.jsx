import React, { useState, useContext } from "react";
import { useNavigate, Link } from "react-router-dom";
import { AuthContext } from "../context/AuthContext";
import "../App.css";

export default function SignUp() {
  const navigate = useNavigate();
  const { signup } = useContext(AuthContext);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await signup(fullName, email, password);
      navigate("/login");
    } catch (err) {
      setError(err.response?.data?.detail || "An error occurred during signup.");
    }
  };

  return (
    <div className="auth-page">
      <div className="blob-1"></div>
      <div className="auth-card fade-in">
        <div className="auth-header">
          <Link to="/" className="logo" style={{ textDecoration: 'none' }}>
            AI-<span>NutriCare</span>
          </Link>
          <h2>Create Your Account</h2>
          <p>Start your journey to biomarker-driven nutrition.</p>
        </div>

        {error && <p style={{ color: "red", textAlign: "center", marginBottom: "1rem" }}>{error}</p>}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="input-group">
            <label>Full Name</label>
            <input 
              type="text" 
              placeholder="Enter your full name" 
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required 
            />
          </div>
          <div className="input-group">
            <label>Email Address</label>
            <input 
              type="email" 
              placeholder="name@example.com" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required 
            />
          </div>
          <div className="input-group">
            <label>Password</label>
            <input 
              type="password" 
              placeholder="••••••••" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required 
            />
          </div>
          
          <button type="submit" className="clay-btn-primary w-100">
            Create Free Account
          </button>
        </form>

        <p className="auth-footer">
          Already have an account? <Link to="/login">Login here</Link>
        </p>
      </div>
    </div>
  );
}