"use client";

import { useEffect } from "react";
import { Settings, LogOut } from "lucide-react";
import useChatStore from "@/store/chatStore";
import Sidebar from "@/components/Sidebar";
import ChatWindow from "@/components/ChatWindow";
import InputBar from "@/components/InputBar";
import apiService from "@/services/api";






export default function ChatPage() {
  const { initialize } = useChatStore();

  const { setUser } = useChatStore();

useEffect(() => {
  const loadUser = async () => {
    try {
      const me = await apiService.me();
      setUser(me);
    } catch (err) {
      console.log("User not logged in:", err);
    }
  };

  loadUser();
}, []);

  useEffect(() => {
    // Initialize the chat store
    initialize();
  }, [initialize]);

  const handleLogout = () => {
    // Clear user data and redirect to home
    window.location.href = "/";
  };

  return (
    <div className="h-screen bg-black flex overflow-hidden">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Top Bar */}
        <div className="bg-[#0f0f0f] border-b border-gray-800 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-lg">X</span>
            </div>
            <div>
              <h1 className="text-white font-bold text-lg">ExplainX</h1>
              <p className="text-gray-400 text-xs">Multimodal AI Assistant</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <a href="/settings">
              <button className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-all">
                <Settings size={20} />
              </button>
            </a>
            <button
              onClick={handleLogout}
              className="p-2 text-gray-400 hover:text-red-400 hover:bg-gray-800 rounded-lg transition-all"
              title="Logout"
            >
              <LogOut size={20} />
            </button>
          </div>
        </div>

        {/* Chat Window */}
        <ChatWindow />

        {/* Input Bar */}
        <InputBar />
      </div>
    </div>
  );
}
