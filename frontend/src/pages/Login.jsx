import React, { useState, useContext } from "react";
import { useNavigate, Link } from "react-router-dom";
import { AuthContext } from "../context/AuthContext";
import "../App.css";

export default function Login() {
  const navigate = useNavigate();
  const { login } = useContext(AuthContext);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await login(email, password);
      // Directing the user to the Dashboard
      navigate("/dashboard");
    } catch (err) {
      setError(err.response?.data?.detail || "Invalid credentials.");
    }
  };

  return (
    <div className="auth-page">
      <div className="blob-2"></div>
      <div className="auth-card fade-in">
        <div className="auth-header">
          <Link to="/" className="logo" style={{ textDecoration: 'none' }}>
            AI-<span>NutriCare</span>
          </Link>
          <h2>Welcome Back</h2>
          <p>Log in to view your latest health insights.</p>
        </div>

        {error && <p style={{ color: "red", textAlign: "center", marginBottom: "1rem" }}>{error}</p>}

        <form className="auth-form" onSubmit={handleSubmit}>
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
          
          <div className="form-options">
            <label className="checkbox-container">
              <input type="checkbox" /> Remember me
            </label>
            <a href="#forgot" className="forgot-link">Forgot Password?</a>
          </div>

          <button type="submit" className="clay-btn-primary w-100">
            Login to Dashboard
          </button>
        </form>

        <p className="auth-footer">
          New to NutriCare? <Link to="/signup">Sign up for free</Link>
        </p>
      </div>
    </div>
  );
}