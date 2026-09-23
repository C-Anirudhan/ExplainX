"use client";

import { useState, useEffect } from "react";
import { ArrowLeft, User, Mail, Key, Save, CheckCircle2, Zap, Cpu } from "lucide-react";
import useChatStore from "@/store/chatStore";
import apiService from "@/services/api";

export default function SettingsPage() {
  const { user, setUser } = useChatStore();

  const [username, setUsername] = useState(user?.username || "");
  const [email, setEmail] = useState(user?.email || "");
  const [apiKey, setApiKey] = useState("");
  const [llmStatus, setLlmStatus] = useState({ llm_active: false, provider: null, model: "offline-fallback" });
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingKey, setSavingKey] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  const refreshStatus = () => {
    apiService.getSettingsStatus()
      .then((status) => {
        if (status) setLlmStatus(status);
      })
      .catch((err) => console.log("Failed to fetch settings status:", err));
  };

  useEffect(() => {
    if (user) {
      setUsername(user.username || "");
      setEmail(user.email || "");
    }
    refreshStatus();
  }, [user]);

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    setSavingProfile(true);
    setSuccess("");
    setError("");

    try {
      const response = await apiService.updateProfile({
        username,
        email,
      });

      if (response.user) {
        setUser(response.user);
      }
      setSuccess("Profile updated successfully.");
      setTimeout(() => setSuccess(""), 4000);
    } catch (err) {
      console.error("Error updating profile:", err);
      setError("Failed to update profile.");
    } finally {
      setSavingProfile(false);
    }
  };

  const handleSaveApiKey = async (e) => {
    e.preventDefault();
    if (!apiKey.trim()) {
      setError("Please enter a valid Groq (gsk_...) or Gemini API key.");
      return;
    }

    setSavingKey(true);
    setSuccess("");
    setError("");

    try {
      const response = await apiService.updateProfile({
        apiKey: apiKey.trim(),
      });

      setLlmStatus({
        llm_active: response.llm_active,
        provider: response.provider,
        model: response.model,
      });
      const providerName = response.provider || (apiKey.trim().startsWith("gsk_") ? "Groq" : "Gemini");
      const modelName = response.model || (apiKey.trim().startsWith("gsk_") ? "Llama 3.3 70B" : "Gemini 2.5 Flash");
      setSuccess(`${providerName} activated successfully with ${modelName}!`);
      setApiKey("");
      refreshStatus();
      setTimeout(() => setSuccess(""), 6000);
    } catch (err) {
      console.error("Error saving API key:", err);
      setError("Failed to save API key. Please check backend connection.");
    } finally {
      setSavingKey(false);
    }
  };

  const getEngineBadgeText = () => {
    if (!llmStatus.llm_active) return "Offline Grounded Fallback";
    if (llmStatus.provider === "Groq" || llmStatus.model?.includes("llama")) {
      return `Groq (${llmStatus.model || "Llama 3.3 70B"})`;
    }
    return `Gemini (${llmStatus.model || "2.5 Flash"})`;
  };

  return (
    <div className="min-h-screen bg-white text-black antialiased">
      <div className="max-w-2xl mx-auto px-4 py-12">
        {/* Header */}
        <div className="mb-8">
          <a
            href="/chat"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-600 hover:text-black transition-colors mb-4"
          >
            <ArrowLeft size={14} />
            Back to Chat
          </a>
          <h1 className="text-2xl font-bold tracking-tight text-black">Settings</h1>
          <p className="text-xs text-gray-500 mt-1">
            Manage account and LLM engine configurations
          </p>
        </div>

        {/* Engine Status Banner */}
        <div className="mb-6 p-4 border border-gray-300 rounded-lg flex items-center justify-between bg-gray-50">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-black">Active AI Engine:</span>
              <span className={`text-xs px-2.5 py-0.5 rounded font-mono font-semibold ${
                llmStatus.llm_active
                  ? "bg-black text-white"
                  : "bg-gray-200 text-gray-800"
              }`}>
                {getEngineBadgeText()}
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              {llmStatus.llm_active
                ? `Online generative reasoning with grounded spatial/temporal bounding box citations via ${llmStatus.provider || "LLM"}.`
                : "Deterministic document chunk extraction is active. Add your Groq key below to run Llama 3.3 70B."}
            </p>
          </div>
        </div>

        {success && (
          <div className="mb-6 p-3 bg-gray-100 border border-black rounded text-xs text-black font-medium flex items-center gap-2">
            <CheckCircle2 size={14} />
            {success}
          </div>
        )}

        {error && (
          <div className="mb-6 p-3 bg-red-50 border border-red-500 rounded text-xs text-red-700 font-medium">
            {error}
          </div>
        )}

        <div className="space-y-6">
          {/* LLM API Configuration (Groq & Gemini) */}
          <div className="border border-gray-200 rounded-lg p-6">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-sm font-semibold text-black uppercase tracking-wider flex items-center gap-2">
                <Cpu size={16} />
                AI Engine API Key
              </h2>
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] font-mono px-2 py-0.5 bg-black text-white rounded">Groq Llama 3.3 70B</span>
                <span className="text-[11px] font-mono text-gray-400">or Gemini</span>
              </div>
            </div>
            <p className="text-xs text-gray-600 mb-4 leading-relaxed">
              Paste your <strong>Groq API Key</strong> (starts with <code className="font-mono text-xs bg-gray-100 px-1 py-0.5 rounded">gsk_...</code>) from{" "}
              <a
                href="https://console.groq.com/keys"
                target="_blank"
                rel="noreferrer"
                className="underline font-semibold text-black hover:text-gray-700"
              >
                console.groq.com
              </a>
              . ExplainX will run the ultra-fast <strong>Llama 3.3 70B Versatile</strong> model on Groq LPU with zero latency and full citation grounding.
            </p>

            <form onSubmit={handleSaveApiKey} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1">
                  API Key (Groq or Gemini)
                </label>
                <div className="relative">
                  <Key
                    className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"
                    size={16}
                  />
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="gsk_..."
                    className="w-full pl-9 pr-3 py-2 bg-white border border-gray-300 rounded text-sm text-black placeholder-gray-400 focus:outline-none focus:border-black font-mono transition-colors"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={savingKey}
                className="py-2 px-4 bg-black hover:bg-gray-800 text-white rounded text-xs font-medium transition-colors flex items-center gap-1.5 disabled:opacity-50"
              >
                <Zap size={14} />
                {savingKey ? "Activating AI Engine..." : "Save & Activate API Key"}
              </button>
            </form>
          </div>

          {/* Profile Section */}
          <div className="border border-gray-200 rounded-lg p-6">
            <h2 className="text-sm font-semibold text-black uppercase tracking-wider mb-4">
              Profile
            </h2>

            <form onSubmit={handleSaveProfile} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1">
                  Username
                </label>
                <div className="relative">
                  <User
                    className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"
                    size={16}
                  />
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="Your username"
                    className="w-full pl-9 pr-3 py-2 bg-white border border-gray-300 rounded text-sm text-black placeholder-gray-400 focus:outline-none focus:border-black transition-colors"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1">
                  Email
                </label>
                <div className="relative">
                  <Mail
                    className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"
                    size={16}
                  />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="your@email.com"
                    className="w-full pl-9 pr-3 py-2 bg-white border border-gray-300 rounded text-sm text-black placeholder-gray-400 focus:outline-none focus:border-black transition-colors"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={savingProfile}
                className="py-2 px-4 bg-black hover:bg-gray-800 text-white rounded text-xs font-medium transition-colors flex items-center gap-1.5 disabled:opacity-50"
              >
                <Save size={14} />
                {savingProfile ? "Saving..." : "Save Profile Changes"}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
