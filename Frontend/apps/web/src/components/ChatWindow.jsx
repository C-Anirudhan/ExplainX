import { useEffect, useRef } from "react";
import useChatStore from "@/store/chatStore";
import ChatMessage from "@/components/ChatMessage";
import { Loader2, MessageSquare } from "lucide-react";

export default function ChatWindow() {
  const { messages, isTyping } = useChatStore();
  const messagesEndRef = useRef(null);
  const containerRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-y-auto p-4 space-y-2 bg-white"
      style={{ scrollBehavior: "smooth" }}
    >
      {messages.length === 0 ? (
        <div className="flex items-center justify-center h-full">
          <div className="text-center space-y-2">
            <MessageSquare size={28} className="text-gray-300 stroke-1 mx-auto" />
            <p className="text-gray-400 text-xs font-mono">
              Ready. Upload a document or enter a query.
            </p>
          </div>
        </div>
      ) : (
        <>
          {messages.map((message, index) => (
            <ChatMessage key={index} message={message} />
          ))}

          {isTyping && (
            <div className="flex gap-3 p-3 justify-start">
              <div className="flex-shrink-0 w-7 h-7 rounded bg-black flex items-center justify-center">
                <Loader2 size={14} className="text-white animate-spin" />
              </div>
              <div className="bg-gray-100 border border-gray-200 rounded-xl px-4 py-2.5">
                <div className="flex gap-1 items-center h-4">
                  <div
                    className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"
                    style={{ animationDelay: "0ms" }}
                  ></div>
                  <div
                    className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"
                    style={{ animationDelay: "150ms" }}
                  ></div>
                  <div
                    className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"
                    style={{ animationDelay: "300ms" }}
                  ></div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </>
      )}
    </div>
  );
}
