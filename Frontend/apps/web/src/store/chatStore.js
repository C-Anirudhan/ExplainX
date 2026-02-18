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
    localStorage.setItem("theme", theme);
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
    try {
        // 1. Create on Backend
        const res = await apiService.createSession();
        const newSessionId = res.session_id;

        // 2. Refresh Sidebar List
        const sessions = await apiService.getSessions();
        set({ sessions });

        // 3. Update State
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
    } catch (err) {
        console.error("Error creating session", err);
    }
  },

  // ============================
  // LOAD SESSION (FIXED MAPPING)
  // ============================
  loadSession: async (sessionId) => {
    set({ isTyping: true });
    try {
        // 1. Fetch real history from Backend
        const history = await apiService.getHistory(sessionId);
        
        // 2. MAP BACKEND DATA TO FRONTEND FORMAT
        // Backend uses 'text' & 'time', Frontend uses 'content' & 'timestamp'
        const cleanMessages = (history.messages || []).map(msg => ({
            role: msg.role,
            content: msg.text || msg.content || "",  // 🔥 FIX: Use 'text' if 'content' is missing
            timestamp: msg.time || msg.timestamp || new Date().toISOString()
        }));

        // 3. Update State
        set({
            currentSessionId: sessionId,
            messages: cleanMessages,
            uploadedFiles: [],
        });
        
        localStorage.setItem("session_id", sessionId);
    } catch (error) {
        console.error("Failed to load session:", error);
    } finally {
        set({ isTyping: false });
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
  initialize: async () => {
    // Load theme
    const theme = localStorage.getItem("theme") || "dark";
    get().setTheme(theme);

    // Load Sidebar List from BACKEND
    try {
        const sessions = await apiService.getSessions();
        set({ sessions });
    } catch (error) {
        console.error("Failed to fetch sessions list:", error);
    }

    // Determine Session ID
    let sessionId = localStorage.getItem("session_id");
    const { sessions } = get();
    
    // Check if the saved session actually exists in our backend list
    const exists = sessions.find(s => s.id === sessionId);

    if (!sessionId || !exists) {
        if (sessions.length > 0) {
            // If we have sessions, load the most recent one
            sessionId = sessions[0].id;
        } else {
            // Only create a new one if the list is totally empty
            const res = await apiService.createSession();
            sessionId = res.session_id;
            // Refresh list
            const newSessions = await apiService.getSessions();
            set({ sessions: newSessions });
        }
        localStorage.setItem("session_id", sessionId);
    }

    // Load the messages for the selected session
    await get().loadSession(sessionId);
  },

  // Empty function to prevent errors if UI calls it
  persistSessions: () => {},
}));

export default useChatStore;