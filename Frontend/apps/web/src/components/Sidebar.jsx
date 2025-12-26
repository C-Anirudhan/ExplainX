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
        className={`fixed md:relative top-0 left-0 h-full bg-[#0f0f0f] border-r border-gray-800 transition-all duration-300 z-40 flex flex-col ${
          sidebarOpen ? "w-80" : "w-0 md:w-0"
        } overflow-hidden`}
      >
        {/* User info */}
        <div className="p-4 border-b border-gray-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white font-semibold">
              {user?.name?.[0]?.toUpperCase() || "U"}

            </div>
            <div className="flex-1 min-w-0">
              <p className="text-white font-medium truncate">
                {user?.name || "Guest User"}

              </p>
              <p className="text-gray-400 text-sm truncate">
                {user?.email || "guest@explainx.ai"}
              </p>
            </div>
          </div>
        </div>

        {/* New Conversation Button */}
        <div className="p-4">
          <button
            onClick={handleNewConversation}
            className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-all font-medium shadow-lg"
          >
            <MessageSquarePlus size={20} />
            New Conversation
          </button>
        </div>

        {/* History Section */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          <h3 className="text-gray-400 text-sm font-semibold mb-3 flex items-center gap-2">
            <Clock size={16} />
            History
          </h3>

          {sessions.length === 0 ? (
            <div className="text-gray-500 text-sm text-center py-8">
              No previous conversations
            </div>
          ) : (
            sessions.map((session) => (
              <button
                key={session.id}
                onClick={() => handleLoadSession(session.id)}
                className={`w-full text-left p-3 rounded-lg transition-all ${
                  currentSessionId === session.id
                    ? "bg-gray-800 border border-purple-500"
                    : "bg-gray-900 hover:bg-gray-800 border border-transparent"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-white text-sm font-medium truncate mb-1">
                      {session.title}
                    </p>
                    <p className="text-gray-400 text-xs">
                      {formatTimestamp(session.timestamp)}
                    </p>
                    {session.files && session.files.length > 0 && (
                      <p className="text-gray-500 text-xs mt-1">
                        {session.files.length} file
                        {session.files.length > 1 ? "s" : ""}
                      </p>
                    )}
                  </div>
                </div>
              </button>
            ))
          )}
        </div>

        {/* Desktop toggle */}
        <div className="hidden md:block p-4 border-t border-gray-800">
          <button
            onClick={toggleSidebar}
            className="w-full text-gray-400 hover:text-white py-2 px-4 rounded-lg hover:bg-gray-800 transition-all text-sm flex items-center justify-center gap-2"
          >
            <Menu size={16} />
            Collapse
          </button>
        </div>
      </div>
    </>
  );
}
