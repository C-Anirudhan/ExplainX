import { User, Bot, FileText, Image as ImageIcon, Film } from "lucide-react";
import ReactMarkdown from "react-markdown";

export default function ChatMessage({ message }) {
  const isUser = message.role === "user";
  const isSystem = message.role === "system";

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const renderContent = () => {
    // If message has images
    if (message.images && message.images.length > 0) {
      return (
        <div className="space-y-3">
          <div className="prose prose-invert max-w-none">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {message.images.map((img, idx) => (
              <img
                key={idx}
                src={img}
                alt={`Frame ${idx + 1}`}
                className="rounded-lg border border-gray-700 w-full h-auto"
              />
            ))}
          </div>
        </div>
      );
    }

    // If message has file preview
    if (message.file) {
      return (
        <div className="space-y-3">
          <div className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg">
            {message.file.type?.startsWith("image/") ? (
              <ImageIcon size={20} className="text-blue-400" />
            ) : message.file.type?.startsWith("video/") ? (
              <Film size={20} className="text-purple-400" />
            ) : (
              <FileText size={20} className="text-green-400" />
            )}
            <div className="flex-1 min-w-0">
              <p className="text-white text-sm font-medium truncate">
                {message.file.name}
              </p>
              <p className="text-gray-400 text-xs">
                {message.file.size
                  ? `${(message.file.size / 1024 / 1024).toFixed(2)} MB`
                  : ""}
              </p>
            </div>
          </div>
          {message.content && (
            <div className="prose prose-invert max-w-none">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>
      );
    }

    // Regular text message
    return (
      <div className="prose prose-invert max-w-none">
        <ReactMarkdown
          components={{
            code({ node, inline, className, children, ...props }) {
              return inline ? (
                <code
                  className="bg-gray-800 text-pink-400 px-1.5 py-0.5 rounded text-sm"
                  {...props}
                >
                  {children}
                </code>
              ) : (
                <pre className="bg-gray-800 p-4 rounded-lg overflow-x-auto">
                  <code className="text-sm" {...props}>
                    {children}
                  </code>
                </pre>
              );
            },
          }}
        >
          {message.content}
        </ReactMarkdown>
      </div>
    );
  };

  if (isSystem) {
    return (
      <div className="flex justify-center py-4">
        <div className="bg-gradient-to-r from-purple-900/30 to-pink-900/30 border border-purple-500/30 rounded-lg px-6 py-3">
          <p className="text-purple-300 font-medium text-center">
            {message.content}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`flex gap-4 p-4 ${isUser ? "justify-end" : "justify-start"}`}
    >
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
          <Bot size={18} className="text-white" />
        </div>
      )}

      <div
        className={`max-w-[70%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-gradient-to-r from-purple-600 to-pink-600 text-white"
            : "bg-gray-800 text-gray-100"
        }`}
      >
        {renderContent()}

        {message.timestamp && (
          <p
            className={`text-xs mt-2 ${isUser ? "text-purple-200" : "text-gray-500"}`}
          >
            {formatTime(message.timestamp)}
          </p>
        )}
      </div>

      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
          <User size={18} className="text-white" />
        </div>
      )}
    </div>
  );
}
