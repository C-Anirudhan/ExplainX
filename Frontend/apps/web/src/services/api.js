// API service for ExplainX backend communication

import { API_BASE } from "@/config";

class ApiService {
  async request(endpoint, options = {}) {
    const token = localStorage.getItem("token");

    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...options.headers,
        },
        ...options,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "API Error");
      }

      return data;
    } catch (error) {
      console.error("API request failed:", error);
      throw error;
    }
  }

  // ====================================================
  // AUTHENTICATION
  // ====================================================

  async signup(email, username, password) {
    return this.request("/api/signup", {
      method: "POST",
      body: JSON.stringify({ email, username, password }),
    });
  }

  async login(email, password) {
    const res = await this.request("/api/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });

    if (res.access_token) {
      localStorage.setItem("token", res.access_token);
    }

    return res;
  }

  async me() {
  return this.request("/api/me", {
    method: "POST",
  });
}


  logout() {
    localStorage.removeItem("token");
  }

  // ====================================================
  // SESSIONS
  // ====================================================

  async createSession() {
    return this.request("/api/new-session", {
      method: "POST",
    });
  }

  async getHistory(sessionId) {
    return this.request(`/api/history?session_id=${sessionId}`, {
      method: "GET",
    });
  }

  // ====================================================
  // FILE UPLOAD
  // ====================================================

  // UI calls: apiService.uploadFile(sessionId, file)
  async uploadFile(sessionId, file) {
  const formData = new FormData();
  formData.append("session_id", sessionId);   // ✔ Correct key
  formData.append("file", file);              // ✔ Correct key

  const token = localStorage.getItem("token");

  const response = await fetch(`${API_BASE}/api/upload/file`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData
  });

  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Upload failed");
  return data;
}




  // Upload YouTube link
  async uploadLink(sessionId, videoLink) {
    return this.request("/api/upload/link", {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId,
        video_link: videoLink,
      }),
    });
  }

  // ====================================================
  // ASK QUESTION (RAG + LLM)
  // ====================================================

  async askQuestion(sessionId, question) {
    return this.request("/api/ask", {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId,
        question,
      }),
    });
  }

  async getSessions() {
    return this.request("/api/sessions", {
      method: "GET",
    });
  }
}

export default new ApiService();
