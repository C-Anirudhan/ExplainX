import { useState, useRef } from "react";
import { Plus, Send, Loader2, X, FileUp, Link2 } from "lucide-react";
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

  // We only pull actions from the hook. 
  // We will read currentSessionId directly from state when needed to avoid stale closures.
  const { addMessage, setTyping, addFile, persistSessions } = useChatStore();

  // Helper to get the REAL current session ID
  const getActiveSessionId = () => {
    return useChatStore.getState().currentSessionId || localStorage.getItem("session_id");
  };

  // ---------- FILE UPLOAD ----------
  const handleFileSelect = async (event) => {
    const files = Array.from(event.target.files || []);
    if (files.length === 0) return;

    setSelectedFiles(files);
    setUploading(true);

    try {
      // 1. Optimistic UI Update
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

      // 2. Upload Logic
      for (const file of files) {
        const sessionId = getActiveSessionId(); // GET LATEST ID

        if (!sessionId) {
          addMessage({
            role: "assistant",
            content: "No active session. Please start a new conversation.",
          });
          break;
        }

        const response = await apiService.uploadFile(sessionId, file);

        if (response?.uuid) {
          useChatStore.getState().updateFileUuid(file.name, response.uuid);
        }

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
      const sessionId = getActiveSessionId(); // GET LATEST ID

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

  // ---------- CHAT SUBMIT ----------
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!inputValue.trim() || uploading) return;

    const question = inputValue.trim();
    setInputValue("");

    // 1. Optimistic Update
    addMessage({ role: "user", content: question });
    setTyping(true);

    try {
      const sessionId = getActiveSessionId(); // GET LATEST ID

      if (!sessionId) {
        addMessage({
          role: "assistant",
          content: "No active session. Please upload a video first.",
        });
        setTyping(false);
        return;
      }

      // 2. Send Request
      const response = await apiService.askQuestion(sessionId, question);

      if (!response || !response.answer) {
        addMessage({
          role: "assistant",
          content:
            "Unable to generate an answer from the retrieved content.",
        });
      } else {
        addMessage({
          role: "assistant",
          content: response.answer,
          citations: response.citations || [],
          verified: response.verified || false,
          refusal: response.refusal || false,
          images: response.images || [],
        });
      }

      persistSessions();
    } catch (error) {
      addMessage({
        role: "assistant",
        content:
          "Encountered an error processing your query. Please retry.",
      });
    } finally {
      setTyping(false);
    }
  };

  return (
    <div className="border-t border-gray-200 bg-white p-3 relative">
      <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
        <div className="flex items-center gap-2 bg-gray-50 rounded-lg px-2 py-1.5 border border-gray-300 focus-within:border-black transition-colors">

          {/* Upload Button */}
          <button
            type="button"
            onClick={() => setShowPicker(!showPicker)}
            disabled={uploading}
            className="flex-shrink-0 p-1.5 text-gray-500 hover:text-black hover:bg-gray-200 rounded transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            title="Attach file or link"
          >
            {uploading ? <Loader2 size={18} className="animate-spin" /> : <Plus size={18} />}
          </button>

          {/* Picker */}
          {showPicker && (
            <div className="absolute bottom-16 left-6 bg-white border border-gray-300 rounded-lg shadow-lg w-36 z-50 py-1 text-xs">
              <button
                onClick={() => {
                  setShowPicker(false);
                  fileInputRef.current.click();
                }}
                className="w-full px-3 py-2 hover:bg-gray-100 text-left text-gray-900 flex items-center gap-2"
              >
                <FileUp size={14} /> File
              </button>
              <button
                onClick={() => {
                  setShowPicker(false);
                  setShowLinkModal(true);
                }}
                className="w-full px-3 py-2 hover:bg-gray-100 text-left text-gray-900 flex items-center gap-2"
              >
                <Link2 size={14} /> Link
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
            placeholder="Ask a question..."
            disabled={uploading}
            className="flex-1 bg-transparent text-black placeholder-gray-400 outline-none text-sm py-1 disabled:opacity-50"
          />

          <button
            type="submit"
            disabled={!inputValue.trim() || uploading}
            className="flex-shrink-0 p-1.5 bg-black hover:bg-gray-800 text-white rounded transition-all disabled:opacity-30 disabled:cursor-not-allowed"
            title="Send"
          >
            <Send size={16} />
          </button>
        </div>
      </form>

      {/* Link Modal */}
      {showLinkModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white p-5 rounded-lg border border-gray-300 w-80 shadow-xl">
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-black font-semibold text-sm">Add Link</h3>
              <button onClick={() => setShowLinkModal(false)} className="text-gray-400 hover:text-black">
                <X size={16} />
              </button>
            </div>
            <input
              value={linkInput}
              onChange={(e) => setLinkInput(e.target.value)}
              placeholder="https://..."
              className="w-full px-3 py-2 rounded bg-gray-50 border border-gray-300 text-black text-sm outline-none focus:border-black"
            />
            <button
              onClick={handleLinkUpload}
              className="mt-3 w-full bg-black hover:bg-gray-800 text-white text-xs font-medium py-2 rounded transition-all"
            >
              Add
            </button>
          </div>
        </div>
      )}
    </div>
  );
}