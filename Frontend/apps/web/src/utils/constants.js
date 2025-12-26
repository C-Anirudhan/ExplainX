export const WELCOME_MESSAGE = "Welcome To ExplainX";

export const SUPPORTED_FILE_TYPES = {
  video: [".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv"],
  document: [".pdf", ".pptx", ".ppt", ".docx", ".doc", ".txt"],
  image: [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"],
  archive: [".zip", ".rar", ".7z"],
};

export const ALL_SUPPORTED_EXTENSIONS = [
  ...SUPPORTED_FILE_TYPES.video,
  ...SUPPORTED_FILE_TYPES.document,
  ...SUPPORTED_FILE_TYPES.image,
  ...SUPPORTED_FILE_TYPES.archive,
];

export const FILE_ACCEPT_STRING = "*/*"; // Accept all file types

export const MAX_FILE_SIZE = 500 * 1024 * 1024; // 500MB

export const ROUTES = {
  HOME: "/",
  LOGIN: "/login",
  SIGNUP: "/signup",
  CHAT: "/chat",
  SETTINGS: "/settings",
};
