import { create } from "zustand";
import apiService from "@/services/api";

const useChatStore = create((set, get) => ({
  currentSessionId: null,
  messages: [],
  uploadedFiles: [],
  sessions: [],
  sidebarOpen: true,
  theme: "dark",
  isTyping: false,
  user: null,

  // ============================
  // USER
  // ============================
  setUser: (user) => set({ user }),

  // ============================
  // THEME
  // ============================
  setTheme: (theme) => {
    set({ theme });
    if (theme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  },

  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setTyping: (isTyping) => set({ isTyping }),

  // ============================
  // MESSAGES
  // ============================
  addMessage: (message) =>
    set((state) => ({
      messages: [
        ...state.messages,
        { ...message, timestamp: new Date().toISOString() },
      ],
    })),

  addFile: (file) =>
    set((state) => ({
      uploadedFiles: [...state.uploadedFiles, file],
    })),

  // ============================
  // CREATE NEW SESSION (BACKEND)
  // ============================
  startNewConversation: async () => {
    const current = get();

    // Save previous session if needed
    if (current.currentSessionId && current.messages.length > 0) {
      const sessionToSave = {
        id: current.currentSessionId,
        messages: current.messages,
        files: current.uploadedFiles,
        timestamp: new Date().toISOString(),
        title: current.uploadedFiles[0]?.name || "Conversation",
      };

      set((state) => ({
        sessions: [sessionToSave, ...state.sessions],
      }));
    }

    // GET REAL SESSION ID FROM BACKEND
    const res = await apiService.createSession();
    const newSessionId = res.session_id;

    // 🔥 UPDATE LOCAL STORAGE
    localStorage.setItem("session_id", newSessionId);


    set({
      currentSessionId: newSessionId,
      messages: [
        {
          role: "system",
          content: "Welcome To ExplainX",
          timestamp: new Date().toISOString(),
        },
      ],
      uploadedFiles: [],
    });

    return newSessionId;
  },

  // ============================
  // LOAD SESSION
  // ============================
  loadSession: (sessionId) => {
    const current = get();

    // Save current session before switching
    if (current.currentSessionId && current.messages.length > 0) {
      const saved = {
        id: current.currentSessionId,
        messages: current.messages,
        files: current.uploadedFiles,
        timestamp: new Date().toISOString(),
      };

      set((state) => ({
        sessions: state.sessions.map((s) =>
          s.id === current.currentSessionId ? saved : s
        ),
      }));
    }

    const session = current.sessions.find((s) => s.id === sessionId);
    if (session) {
      set({
        currentSessionId: session.id,
        messages: session.messages,
        uploadedFiles: session.files || [],
      });
    }
  },

  addSession: (session) =>
    set((state) => ({
      sessions: [session, ...state.sessions],
    })),

  clearMessages: () => set({ messages: [], uploadedFiles: [] }),

  // ============================
  // INITIALIZE APP
  // ============================
  // ============================
// INITIALIZE APP (🔥 FIXED)
// ============================
initialize: async () => {
  // Load theme
  const theme = localStorage.getItem("theme") || "dark";
  get().setTheme(theme);

  // Load sidebar/chat history (optional UI history)
  const saved = localStorage.getItem("explainx_sessions");
  if (saved) {
    try {
      set({ sessions: JSON.parse(saved) });
    } catch {}
  }

  // 🔥 SESSION FIX STARTS HERE
  let sessionId = localStorage.getItem("session_id");

  if (!sessionId) {
    // Create session ONLY ONCE
    const res = await apiService.createSession();
    sessionId = res.session_id;
    localStorage.setItem("session_id", sessionId);
  }

  // Load backend chat history
  try {
    const history = await apiService.getHistory(sessionId);
    set({
      currentSessionId: sessionId,
      messages:
        history.messages?.length > 0
          ? history.messages
          : [
              {
                role: "system",
                content: "Welcome To ExplainX",
                timestamp: new Date().toISOString(),
              },
            ],
      uploadedFiles: [],
    });
  } catch {
    set({
      currentSessionId: sessionId,
      messages: [
        {
          role: "system",
          content: "Welcome To ExplainX",
          timestamp: new Date().toISOString(),
        },
      ],
      uploadedFiles: [],
    });
  }
},

  // Save history
  persistSessions: () => {
    const { sessions } = get();
    localStorage.setItem("explainx_sessions", JSON.stringify(sessions));
  },
}));

export default useChatStore;
