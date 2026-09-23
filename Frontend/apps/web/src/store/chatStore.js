import { create } from "zustand";
import apiService from "@/services/api";

const useChatStore = create((set, get) => ({
  currentSessionId: null,
  messages: [],
  uploadedFiles: [],
  sessions: [],
  sidebarOpen: true,
  theme: "light",
  isTyping: false,
  user: null,

  // ============================
  // WORKSPACE VIEWER STATE
  // ============================
  activeFile: null,          // { name, uuid, ext, type: 'document'|'video' }
  viewerTab: "document",     // "document" | "video"
  activeHighlight: null,     // { page: 1, bbox: [x0, y0, x1, y1], label: "...", chunk_type: "table" }
  activeVideoSeek: null,     // { seconds: 134, timestamp: "02:14" }
  pdfPage: 1,
  pdfTotalPages: 1,
  zoom: 1.0,

  setViewerTab: (viewerTab) => set({ viewerTab }),
  setActiveFile: (activeFile) => set({ activeFile, activeHighlight: null }),
  setPdfPage: (pdfPage) => set({ pdfPage }),
  setPdfTotalPages: (pdfTotalPages) => set({ pdfTotalPages }),
  setZoom: (zoom) => set({ zoom }),

  // HIGHLIGHT CITATION ACTION
  highlightCitation: (citation) => {
    if (!citation) return;

    if (citation.type === "document") {
      const page = citation.page || 1;
      set({
        viewerTab: "document",
        pdfPage: page,
        activeHighlight: {
          page: page,
          bbox: citation.bbox || [0, 0, 0, 0],
          label: citation.label || `Page ${page}`,
          chunk_type: citation.chunk_type || "text",
          doc_name: citation.doc_name || ""
        }
      });
      // Match activeFile if available
      const { uploadedFiles } = get();
      if (citation.doc_name && uploadedFiles.length > 0) {
        const found = uploadedFiles.find(f => 
          f.name === citation.doc_name || f.real_name === citation.doc_name
        );
        if (found) {
          set({ activeFile: found });
        }
      }
    } else if (citation.type === "video") {
      set({
        viewerTab: "video",
        activeVideoSeek: {
          seconds: citation.seconds || 0,
          timestamp: citation.timestamp || "00:00",
          video_name: citation.video_name || ""
        }
      });
      const { uploadedFiles } = get();
      if (uploadedFiles && uploadedFiles.length > 0) {
        const found = uploadedFiles.find(f => 
          f.name === citation.video_name || 
          f.real_name === citation.video_name ||
          f.uuid === citation.video_name ||
          (f.source_url && f.source_url === citation.video_name)
        ) || uploadedFiles.find(f => 
          f.type === "video" || 
          (f.ext && [".mp4", ".mov", ".webm", ".avi", ".mkv"].includes(f.ext.toLowerCase())) ||
          (f.name && (f.name.includes("youtube.com") || f.name.includes("youtu.be")))
        );
        if (found) {
          set({ activeFile: found });
        }
      }
    }
  },

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
    set((state) => {
      const isVideo = file.name.match(/\.(mp4|mov|avi|mkv|webm)$/i);
      const fileObj = {
        name: file.name,
        ext: isVideo ? ".mp4" : ".pdf",
        type: isVideo ? "video" : "document",
        size: file.size
      };
      return {
        uploadedFiles: [...state.uploadedFiles, fileObj],
        activeFile: state.activeFile || fileObj,
        viewerTab: isVideo ? "video" : "document"
      };
    }),

  updateFileUuid: (fileName, uuid) =>
    set((state) => {
      const updated = state.uploadedFiles.map((f) =>
        f.name === fileName ? { ...f, uuid } : f
      );
      const active = state.activeFile?.name === fileName
        ? { ...state.activeFile, uuid }
        : state.activeFile;
      return { uploadedFiles: updated, activeFile: active };
    }),

  // ============================
  // CREATE NEW SESSION (BACKEND)
  // ============================
  startNewConversation: async () => {
    try {
        const res = await apiService.createSession();
        const newSessionId = res.session_id;

        const sessions = await apiService.getSessions();
        set({ sessions });

        localStorage.setItem("session_id", newSessionId);

        set({
            currentSessionId: newSessionId,
            messages: [
                {
                    role: "system",
                    content: "Welcome to ExplainX Multimodal Truth Engine.",
                    timestamp: new Date().toISOString(),
                },
            ],
            uploadedFiles: [],
            activeFile: null,
            activeHighlight: null,
            activeVideoSeek: null,
        });

        return newSessionId;
    } catch (err) {
        console.error("Error creating session", err);
    }
  },

  // ============================
  // LOAD SESSION
  // ============================
  loadSession: async (sessionId) => {
    set({ isTyping: true });
    try {
        const history = await apiService.getHistory(sessionId);
        const { sessions } = get();
        const currentSess = sessions.find(s => s.id === sessionId);
        const sessFiles = (currentSess?.files || []).map(f => ({
          ...f,
          type: f.ext?.match(/\.(mp4|mov|avi|mkv|webm)$/i) ? "video" : "document"
        }));

        const cleanMessages = (history.messages || []).map(msg => ({
            role: msg.role,
            content: msg.text || msg.content || "",
            citations: msg.citations || [],
            verified: msg.verified || false,
            refusal: msg.refusal || false,
            timestamp: msg.time || msg.timestamp || new Date().toISOString()
        }));

        const initialFile = sessFiles.length > 0 ? sessFiles[0] : null;

        set({
            currentSessionId: sessionId,
            messages: cleanMessages,
            uploadedFiles: sessFiles,
            activeFile: initialFile,
            viewerTab: initialFile?.type === "video" ? "video" : "document",
            activeHighlight: null,
            activeVideoSeek: null,
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

  clearMessages: () => set({ messages: [], uploadedFiles: [], activeFile: null }),

  // ============================
  // INITIALIZE APP
  // ============================
  initialize: async () => {
    const theme = localStorage.getItem("theme") || "dark";
    get().setTheme(theme);

    try {
        const sessions = await apiService.getSessions();
        set({ sessions });
    } catch (error) {
        console.error("Failed to fetch sessions list:", error);
    }

    let sessionId = localStorage.getItem("session_id");
    const { sessions } = get();
    const exists = sessions.find(s => s.id === sessionId);

    if (!sessionId || !exists) {
        if (sessions.length > 0) {
            sessionId = sessions[0].id;
        } else {
            const res = await apiService.createSession();
            sessionId = res.session_id;
            const newSessions = await apiService.getSessions();
            set({ sessions: newSessions });
        }
        localStorage.setItem("session_id", sessionId);
    }

    await get().loadSession(sessionId);
  },

  persistSessions: () => {},
}));

export default useChatStore;