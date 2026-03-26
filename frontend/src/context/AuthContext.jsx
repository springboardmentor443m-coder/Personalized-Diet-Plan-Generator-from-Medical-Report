import React, { createContext, useState, useEffect } from "react";
import axios from "axios";

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem("token") || "");

  // Axios instance with base URL
  const api = axios.create({
    baseURL: "http://127.0.0.1:8001" // backend API url
  });

  // Attach token to requests if exists
  api.interceptors.request.use((config) => {
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  useEffect(() => {
    if (token) {
      localStorage.setItem("token", token);
      fetchUser();
    } else {
      localStorage.removeItem("token");
      setUser(null);
    }
  }, [token]);

  const fetchUser = async () => {
    try {
      const response = await api.get("/me");
      setUser(response.data);
    } catch (error) {
      console.error("Error fetching user data", error);
      setToken(""); // if token is invalid, clear it
    }
  };

  const login = async (email, password) => {
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);
    const response = await api.post("/login", formData, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" }
    });
    setToken(response.data.access_token);
    return response.data;
  };

  const signup = async (fullName, email, password) => {
    const response = await api.post("/signup", {
      full_name: fullName,
      email: email,
      password: password
    });
    return response.data;
  };

  const logout = () => {
    setToken("");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, api, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
