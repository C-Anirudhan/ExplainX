"use client";

import { useEffect, useState } from "react";
import { Settings, LogOut, Columns, MessageSquare, Maximize2 } from "lucide-react";
import useChatStore from "@/store/chatStore";
import Sidebar from "@/components/Sidebar";
import ChatWindow from "@/components/ChatWindow";
import InputBar from "@/components/InputBar";
import AttributionViewer from "@/components/AttributionViewer";
import apiService from "@/services/api";

export default function ChatPage() {
  const { initialize, setUser } = useChatStore();
  const [layoutMode, setLayoutMode] = useState("split"); // "split" | "chat" | "viewer"

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
  }, [setUser]);

  useEffect(() => {
    initialize();
  }, [initialize]);

  const handleLogout = () => {
    apiService.logout();
    window.location.href = "/";
  };

  return (
    <div className="h-screen bg-white text-black flex overflow-hidden">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Workspace Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Navigation Bar */}
        <div className="bg-white border-b border-gray-200 px-5 py-2.5 flex items-center justify-between z-10">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 bg-black text-white rounded flex items-center justify-center font-bold text-xs">
              X
            </div>
            <h1 className="text-black font-semibold text-sm tracking-tight">ExplainX</h1>
          </div>

          {/* Layout Controls & Settings */}
          <div className="flex items-center gap-2">
            {/* View Mode Toggle */}
            <div className="flex items-center bg-gray-100 border border-gray-200 rounded p-0.5">
              <button
                onClick={() => setLayoutMode("split")}
                className={`px-2.5 py-1 rounded text-xs flex items-center gap-1.5 transition-all ${
                  layoutMode === "split"
                    ? "bg-black text-white font-medium shadow-sm"
                    : "text-gray-600 hover:text-black"
                }`}
                title="Split Screen"
              >
                <Columns size={13} />
                <span className="hidden sm:inline">Split</span>
              </button>
              <button
                onClick={() => setLayoutMode("chat")}
                className={`px-2.5 py-1 rounded text-xs flex items-center gap-1.5 transition-all ${
                  layoutMode === "chat"
                    ? "bg-black text-white font-medium shadow-sm"
                    : "text-gray-600 hover:text-black"
                }`}
                title="Chat Only"
              >
                <MessageSquare size={13} />
                <span className="hidden sm:inline">Chat</span>
              </button>
              <button
                onClick={() => setLayoutMode("viewer")}
                className={`px-2.5 py-1 rounded text-xs flex items-center gap-1.5 transition-all ${
                  layoutMode === "viewer"
                    ? "bg-black text-white font-medium shadow-sm"
                    : "text-gray-600 hover:text-black"
                }`}
                title="Viewer Only"
              >
                <Maximize2 size={13} />
                <span className="hidden sm:inline">Canvas</span>
              </button>
            </div>

            <a href="/settings">
              <button className="p-1.5 text-gray-500 hover:text-black hover:bg-gray-100 rounded transition-all" title="Settings">
                <Settings size={16} />
              </button>
            </a>
            <button
              onClick={handleLogout}
              className="p-1.5 text-gray-500 hover:text-black hover:bg-gray-100 rounded transition-all"
              title="Logout"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>

        {/* Dual-Pane Workspace */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left Pane: Interactive Document Canvas & Video Player */}
          {(layoutMode === "split" || layoutMode === "viewer") && (
            <div className={`${layoutMode === "viewer" ? "w-full" : "w-1/2"} h-full flex flex-col overflow-hidden bg-gray-50 border-r border-gray-200`}>
              <AttributionViewer />
            </div>
          )}

          {/* Right Pane: AI Chat & Citations */}
          {(layoutMode === "split" || layoutMode === "chat") && (
            <div className={`${layoutMode === "chat" ? "w-full" : "w-1/2"} h-full flex flex-col bg-white overflow-hidden`}>
              <ChatWindow />
              <InputBar />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
