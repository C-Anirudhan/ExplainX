import { User, Bot, FileText, Image as ImageIcon, Film, CheckCircle2, ShieldAlert } from "lucide-react";
import ReactMarkdown from "react-markdown";
import useChatStore from "@/store/chatStore";

export default function ChatMessage({ message }) {
  const isUser = message.role === "user";
  const isSystem = message.role === "system";
  const { highlightCitation } = useChatStore();

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const citations = message.citations || [];
  const isVerified = message.verified;
  const isRefusal = message.refusal;

  const renderContent = () => {
    // If message has images
    if (message.images && message.images.length > 0) {
      return (
        <div className="space-y-3">
          <div className="prose max-w-none text-sm text-gray-900">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {message.images.map((img, idx) => (
              <img
                key={idx}
                src={img}
                alt={`Frame ${idx + 1}`}
                className="rounded border border-gray-200 w-full h-auto"
              />
            ))}
          </div>
        </div>
      );
    }

    // If message has file preview
    if (message.file) {
      return (
        <div className="space-y-2">
          <div className="flex items-center gap-2.5 p-2.5 bg-white border border-gray-200 rounded">
            {message.file.type?.startsWith("image/") ? (
              <ImageIcon size={18} className="text-gray-600" />
            ) : message.file.type?.startsWith("video/") ? (
              <Film size={18} className="text-gray-600" />
            ) : (
              <FileText size={18} className="text-gray-600" />
            )}
            <div className="flex-1 min-w-0">
              <p className="text-black text-xs font-medium truncate">
                {message.file.name}
              </p>
              <p className="text-gray-500 text-[10px] font-mono">
                {message.file.size
                  ? `${(message.file.size / 1024 / 1024).toFixed(2)} MB`
                  : ""}
              </p>
            </div>
          </div>
          {message.content && (
            <div className="prose max-w-none text-sm text-gray-900">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>
      );
    }

    // Regular text message
    return (
      <div className={`prose max-w-none text-sm leading-relaxed ${isUser ? "text-white" : "text-gray-900"}`}>
        <ReactMarkdown
          components={{
            code({ node, inline, className, children, ...props }) {
              return inline ? (
                <code
                  className={`px-1.5 py-0.5 rounded text-xs font-mono ${isUser ? "bg-gray-800 text-gray-100" : "bg-gray-100 text-gray-800 border border-gray-200"}`}
                  {...props}
                >
                  {children}
                </code>
              ) : (
                <pre className="bg-gray-100 p-2.5 rounded overflow-x-auto border border-gray-200 my-2 text-gray-800">
                  <code className="text-xs font-mono" {...props}>
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
      <div className="flex justify-center py-2">
        <div className="bg-gray-100 border border-gray-200 rounded px-4 py-1.5">
          <p className="text-gray-600 text-xs font-mono text-center">
            {message.content}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`flex gap-2.5 p-2.5 transition-all ${
        isUser ? "justify-end" : "justify-start"
      }`}
    >
      {!isUser && (
        <div className="flex-shrink-0 w-7 h-7 rounded bg-gray-100 border border-gray-300 flex items-center justify-center text-black">
          <Bot size={15} />
        </div>
      )}

      <div
        className={`max-w-[85%] rounded-xl px-4 py-2.5 shadow-xs ${
          isUser
            ? "bg-black text-white"
            : "bg-gray-50 border border-gray-200 text-gray-900"
        }`}
      >
        {renderContent()}

        {/* Verification Status Tag */}
        {!isUser && (isVerified || isRefusal) && (
          <div className="mt-2.5 pt-2 border-t border-gray-200 flex items-center gap-1.5">
            {isVerified && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-white text-black border border-gray-300">
                <CheckCircle2 size={10} />
                Verified
              </span>
            )}
            {isRefusal && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-gray-150 text-gray-700 border border-gray-300">
                <ShieldAlert size={10} />
                Refusal Gate
              </span>
            )}
          </div>
        )}

        {/* Sources Section */}
        {!isUser && citations.length > 0 && (
          <div className="mt-2.5 pt-2 border-t border-gray-200">
            <p className="text-[10px] font-mono text-gray-500 mb-1">
              Sources:
            </p>
            <div className="flex flex-wrap gap-1.5">
              {citations.map((cit, idx) => {
                const isDoc = cit.type === "document";

                return (
                  <button
                    key={idx}
                    onClick={() => highlightCitation(cit)}
                    title={isDoc ? `Jump to Page ${cit.page}` : `Seek to ${cit.timestamp}`}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-mono transition-all border border-gray-300 bg-white hover:bg-black hover:text-white text-black cursor-pointer shadow-xs"
                  >
                    {isDoc ? <FileText size={11} /> : <Film size={11} />}
                    <span>{cit.label || (isDoc ? `Page ${cit.page}` : cit.timestamp)}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {message.timestamp && (
          <p
            className={`text-[9px] mt-1.5 font-mono ${
              isUser ? "text-gray-400" : "text-gray-400"
            }`}
          >
            {formatTime(message.timestamp)}
          </p>
        )}
      </div>

      {isUser && (
        <div className="flex-shrink-0 w-7 h-7 rounded bg-black text-white flex items-center justify-center">
          <User size={15} />
        </div>
      )}
    </div>
  );
}
