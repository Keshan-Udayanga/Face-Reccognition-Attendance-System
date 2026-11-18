import { useEffect, useRef, useState } from "react";
import { Bot, Send, X } from "lucide-react";
import { sendChatMessage } from "../services/chatbotService.js";
import "./ChatWidget.css";

export default function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [messages, setMessages] = useState([
    {
      id: 1,
      sender: "bot",
      text: "Hi! I'm your SmartFace assistant. How can I help you today?",
    },
  ]);
  const messageEndRef = useRef(null);

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    function closeOnEscape(event) {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    }

    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, []);

  async function sendMessage(event) {
    event.preventDefault();
    const text = message.trim();
    if (!text || isSending) return;

    const userMessage = { id: Date.now(), sender: "user", text };
    const conversation = [
      ...messages.slice(1),
      userMessage,
    ]
      .map((item) => ({
        role: item.sender === "user" ? "user" : "model",
        text: item.text,
      }))
      .slice(-20);
    setMessages((current) => [...current, userMessage]);
    setMessage("");
    setIsSending(true);

    try {
      const result = await sendChatMessage(conversation);
      setMessages((current) => [
        ...current,
        { id: Date.now(), sender: "bot", text: result.reply },
      ]);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          id: Date.now(),
          sender: "bot",
          text: `Sorry, I couldn't get a reply: ${error.message}`,
        },
      ]);
    } finally {
      setIsSending(false);
    }
  }

  return (
    <div className="chat-widget">
      {isOpen && (
        <section
          aria-label="SmartFace chat"
          aria-live="polite"
          className="chat-panel"
        >
          <header className="chat-header">
            <div className="chat-header-icon">
              <Bot aria-hidden="true" size={21} strokeWidth={2} />
            </div>
            <div className="chat-header-copy">
              <strong>SmartFace Assistant</strong>
              <span>
                <i aria-hidden="true" />
                Online
              </span>
            </div>
            <button
              aria-label="Close chat"
              className="chat-close"
              onClick={() => setIsOpen(false)}
              type="button"
            >
              <X aria-hidden="true" size={18} />
            </button>
          </header>

          <div className="chat-messages">
            <div className="chat-date">Today</div>
            {messages.map((item) => (
              <div
                className={`chat-message-row chat-message-${item.sender}`}
                key={item.id}
              >
                {item.sender === "bot" && (
                  <div className="chat-avatar">
                    <Bot aria-hidden="true" size={15} />
                  </div>
                )}
                <div className="chat-bubble">{item.text}</div>
              </div>
            ))}
            <div ref={messageEndRef} />
          </div>

          <form className="chat-composer" onSubmit={sendMessage}>
            <input
              aria-label="Chat message"
              disabled={isSending}
              maxLength={2000}
              onChange={(event) => setMessage(event.target.value)}
              placeholder={isSending ? "Waiting for a reply..." : "Type a message..."}
              value={message}
            />
            <button
              aria-label="Send message"
              className="chat-send"
              disabled={!message.trim() || isSending}
              type="submit"
            >
              <Send aria-hidden="true" size={17} fill="currentColor" />
            </button>
          </form>
        </section>
      )}

      <button
        aria-expanded={isOpen}
        aria-label={isOpen ? "Close SmartFace assistant" : "Open SmartFace assistant"}
        className={`chat-launcher ${isOpen ? "chat-launcher-active" : ""}`}
        onClick={() => setIsOpen((current) => !current)}
        type="button"
      >
        {isOpen ? (
          <X aria-hidden="true" size={26} />
        ) : (
          <Bot aria-hidden="true" size={27} strokeWidth={2} />
        )}
        {!isOpen && <span className="chat-launcher-dot" />}
      </button>
    </div>
  );
}
