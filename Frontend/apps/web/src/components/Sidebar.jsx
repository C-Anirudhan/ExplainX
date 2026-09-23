import { MessageSquarePlus, Menu, X, Clock } from "lucide-react";
import useChatStore from "@/store/chatStore";

export default function Sidebar() {
  const {
    sidebarOpen,
    toggleSidebar,
    sessions,
    currentSessionId,
    loadSession,
    startNewConversation,
    user,
  } = useChatStore();

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) {
      return "Today";
    } else if (days === 1) {
      return "Yesterday";
    } else if (days < 7) {
      return `${days} days ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  const handleNewConversation = () => {
    startNewConversation();
  };

  const handleLoadSession = (sessionId) => {
    loadSession(sessionId);
  };

  return (
    <>
      {/* Mobile toggle button */}
      <button
        onClick={toggleSidebar}
        className="fixed top-4 left-4 z-50 md:hidden bg-[#1a1a1a] text-white p-2 rounded-lg shadow-lg hover:bg-[#2a2a2a] transition-colors"
      >
        {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-30 md:hidden"
          onClick={toggleSidebar}
        />
      )}

      {/* Sidebar */}
      <div
        className={`fixed md:relative top-0 left-0 h-full bg-white border-r border-gray-200 transition-all duration-300 z-40 flex flex-col ${
          sidebarOpen ? "w-72" : "w-0 md:w-0"
        } overflow-hidden`}
      >
        {/* User info */}
        <div className="p-3.5 border-b border-gray-200">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded bg-black text-white flex items-center justify-center text-xs font-semibold">
              {user?.name?.[0]?.toUpperCase() || "U"}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-black text-xs font-semibold truncate">
                {user?.name || "User"}
              </p>
              <p className="text-gray-400 text-[10px] font-mono truncate">
                {user?.email || "user@explainx.ai"}
              </p>
            </div>
          </div>
        </div>

        {/* New Conversation Button */}
        <div className="p-3">
          <button
            onClick={handleNewConversation}
            className="w-full bg-black hover:bg-gray-800 text-white py-2 px-3 rounded text-xs flex items-center justify-center gap-2 transition-all font-medium"
          >
            <MessageSquarePlus size={15} />
            New Chat
          </button>
        </div>

        {/* History Section */}
        <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
          <h3 className="text-gray-500 text-[11px] font-mono uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <Clock size={12} />
            History
          </h3>

          {sessions.length === 0 ? (
            <div className="text-gray-400 text-xs text-center py-6 font-mono">
              No history
            </div>
          ) : (
            sessions.map((session) => (
              <button
                key={session.id}
                onClick={() => handleLoadSession(session.id)}
                className={`w-full text-left p-2.5 rounded transition-all text-xs ${
                  currentSessionId === session.id
                    ? "bg-gray-100 border border-gray-300 text-black font-medium"
                    : "text-gray-600 hover:bg-gray-50 hover:text-black border border-transparent"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="truncate mb-0.5">
                      {session.title}
                    </p>
                    <p className="text-gray-400 text-[10px] font-mono">
                      {formatTimestamp(session.timestamp)}
                    </p>
                  </div>
                </div>
              </button>
            ))
          )}
        </div>

        {/* Desktop toggle */}
        <div className="hidden md:block p-3 border-t border-gray-200">
          <button
            onClick={toggleSidebar}
            className="w-full text-gray-500 hover:text-black py-1.5 px-3 rounded hover:bg-gray-100 transition-all text-xs flex items-center justify-center gap-2"
          >
            <Menu size={14} />
            Collapse
          </button>
        </div>
      </div>
    </>
  );
}
