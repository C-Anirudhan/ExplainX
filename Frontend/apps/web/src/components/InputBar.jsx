import { useState, useRef } from "react";
import { Plus, Send, Loader2, X } from "lucide-react";
import useChatStore from "@/store/chatStore";
import apiService from "@/services/api";
import { FILE_ACCEPT_STRING } from "@/utils/constants";

export default function InputBar() {
  const [inputValue, setInputValue] = useState("");
  const [uploading, setUploading] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [showPicker, setShowPicker] = useState(false);
  const [showLinkModal, setShowLinkModal] = useState(false);
  const [linkInput, setLinkInput] = useState("");
  const fileInputRef = useRef(null);

  const { addMessage, setTyping, currentSessionId, addFile, persistSessions } =
    useChatStore();

  console.log("first_sessionId", currentSessionId);

  // ---------- FILE UPLOAD (UNCHANGED LOGIC) ----------
  const handleFileSelect = async (event) => {
    const files = Array.from(event.target.files || []);
    if (files.length === 0) return;

    setSelectedFiles(files);
    setUploading(true);

    try {
      files.forEach((file) => {
        addMessage({
          role: "user",
          content: `Uploaded: ${file.name}`,
          file: {
            name: file.name,
            size: file.size,
            type: file.type,
          },
        });
        addFile(file);
      });

      for (const file of files) {
        const sessionId = currentSessionId || localStorage.getItem("session_id");

        if (!sessionId) {
          addMessage({
            role: "assistant",
            content: "No active session. Please start a new conversation.",
          });
          break;
        }

        const response = await apiService.uploadFile(sessionId, file);

        if (response?.summary) {
          addMessage({
            role: "assistant",
            content: response.summary,
            timestamp: new Date().toISOString(),
          });
        }
      }

      setTyping(false);
      persistSessions();
    } catch (error) {
      console.error("Upload error:", error);
      addMessage({
        role: "assistant",
        content: `Sorry, there was an error uploading your file: ${error.message}`,
      });
    } finally {
      setUploading(false);
      setSelectedFiles([]);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  // ---------- LINK UPLOAD ----------
  const handleLinkUpload = async () => {
    if (!linkInput.trim()) return;

    setUploading(true);
    setShowLinkModal(false);

    try {
      const sessionId = currentSessionId || localStorage.getItem("session_id");

      addMessage({ role: "user", content: `Uploaded link: ${linkInput}` });

      const response = await apiService.uploadLink(sessionId, linkInput);

      if (response?.summary) {
        addMessage({
          role: "assistant",
          content: response.summary,
          timestamp: new Date().toISOString(),
        });
      }

      persistSessions();
    } catch (error) {
      addMessage({
        role: "assistant",
        content: "Sorry, there was an error uploading your link.",
      });
    } finally {
      setUploading(false);
      setLinkInput("");
    }
  };

  // ---------- CHAT SUBMIT (UNCHANGED) ----------
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!inputValue.trim() || uploading) return;

    const question = inputValue.trim();
    setInputValue("");

    addMessage({ role: "user", content: question });
    setTyping(true);

    try {
      const sessionId = currentSessionId || localStorage.getItem("session_id");

      if (!sessionId) {
        addMessage({
          role: "assistant",
          content: "No active session. Please upload a video first.",
        });
        setTyping(false);
        return;
      }

      const response = await apiService.askQuestion(sessionId, question);

      if (!response || !response.answer) {
        addMessage({
          role: "assistant",
          content:
            "⚠️ I couldn't generate an answer. This usually means no relevant data was retrieved from the video.",
        });
      } else {
        addMessage({
          role: "assistant",
          content: response.answer,
          images: response.images || [],
        });
      }

      persistSessions();
    } catch (error) {
      addMessage({
        role: "assistant",
        content:
          "Sorry, I encountered an error processing your question. Please try again.",
      });
    } finally {
      setTyping(false);
    }
  };

  return (
    <div className="border-t border-gray-800 bg-[#0f0f0f] p-4 relative">
      <form onSubmit={handleSubmit} className="max-w-5xl mx-auto">
        <div className="flex items-center gap-3 bg-gray-900 rounded-xl p-2 border border-gray-800 focus-within:border-purple-500 transition-colors">

          {/* Upload Button */}
          <button
            type="button"
            onClick={() => setShowPicker(!showPicker)}
            disabled={uploading}
            className="flex-shrink-0 p-2 text-gray-400 hover:text-purple-400 hover:bg-gray-800 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {uploading ? <Loader2 size={24} className="animate-spin" /> : <Plus size={24} />}
          </button>

          {/* Picker */}
          {showPicker && (
            <div className="absolute bottom-20 left-6 bg-[#0b1220] border border-white/10 rounded-xl shadow-xl w-44 z-50">
              <button
                onClick={() => {
                  setShowPicker(false);
                  fileInputRef.current.click();
                }}
                className="w-full p-3 hover:bg-white/10 text-left text-white"
              >
                📁 Upload File
              </button>
              <button
                onClick={() => {
                  setShowPicker(false);
                  setShowLinkModal(true);
                }}
                className="w-full p-3 hover:bg-white/10 text-left text-white"
              >
                🔗 Paste Link
              </button>
            </div>
          )}

          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept={FILE_ACCEPT_STRING}
            onChange={handleFileSelect}
            className="hidden"
          />

          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Ask a question about your uploaded content..."
            disabled={uploading}
            className="flex-1 bg-transparent text-white placeholder-gray-500 outline-none py-2 disabled:opacity-50"
          />

          <button
            type="submit"
            disabled={!inputValue.trim() || uploading}
            className="flex-shrink-0 p-2 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send size={24} />
          </button>
        </div>

        <p className="text-gray-500 text-xs mt-2 text-center">
          Supports: Videos, PDFs, PPTs, Documents, Images, and more
        </p>
      </form>

      {/* Link Modal */}
      {showLinkModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-[#0b1220] p-6 rounded-xl w-96">
            <div className="flex justify-between mb-3">
              <h3 className="text-white">Paste Link</h3>
              <button onClick={() => setShowLinkModal(false)}>
                <X />
              </button>
            </div>
            <input
              value={linkInput}
              onChange={(e) => setLinkInput(e.target.value)}
              placeholder="https://..."
              className="w-full p-3 rounded bg-black/40 border border-white/10 text-white"
            />
            <button
              onClick={handleLinkUpload}
              className="mt-4 w-full bg-purple-600 p-2 rounded-lg"
            >
              Upload
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
