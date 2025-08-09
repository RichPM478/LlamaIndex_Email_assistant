"""
Modern chat-style interface for email queries
"""
import streamlit as st
from datetime import datetime
import time
from app.qa.optimized_query import optimized_ask, get_cache_status

# Configure page
st.set_page_config(
    page_title="Email Assistant",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for chat interface
st.markdown("""
<style>
    /* Main container */
    .main {
        max-width: 900px;
        margin: 0 auto;
    }
    
    /* Chat messages */
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 12px 18px;
        border-radius: 18px 18px 4px 18px;
        margin: 10px 0;
        max-width: 70%;
        margin-left: auto;
        word-wrap: break-word;
    }
    
    .assistant-message {
        background: #f3f4f6;
        color: #1f2937;
        padding: 12px 18px;
        border-radius: 18px 18px 18px 4px;
        margin: 10px 0;
        max-width: 85%;
        word-wrap: break-word;
    }
    
    /* Source cards */
    .source-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 12px;
        margin: 8px 0;
        transition: box-shadow 0.2s;
    }
    
    .source-card:hover {
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    /* Quick action buttons */
    .quick-action {
        background: white;
        border: 2px solid #e5e7eb;
        border-radius: 20px;
        padding: 8px 16px;
        margin: 4px;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .quick-action:hover {
        background: #667eea;
        color: white;
        border-color: #667eea;
    }
    
    /* Header */
    .header {
        text-align: center;
        padding: 20px 0;
        margin-bottom: 30px;
    }
    
    /* Status indicator */
    .status-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 5px;
    }
    
    .status-ready { background: #10b981; }
    .status-loading { background: #f59e0b; }
    .status-error { background: #ef4444; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Add welcome message
    st.session_state.messages.append({
        "role": "assistant",
        "content": "👋 Hi! I'm your email assistant. I can help you find information from your emails. Try asking me about recent emails, payments, events, or specific senders!",
        "timestamp": datetime.now()
    })

if "processing" not in st.session_state:
    st.session_state.processing = False

# Header
st.markdown("""
<div class="header">
    <h1>📧 Email Assistant</h1>
    <p style="color: #6b7280;">Ask questions about your emails in natural language</p>
</div>
""", unsafe_allow_html=True)

# Quick actions
st.markdown("### 💡 Quick Actions")
cols = st.columns(4)
quick_queries = [
    "📅 What events are coming up?",
    "💳 Show me bills and payments",
    "📬 What's my latest email?",
    "🔔 Any important notifications?"
]

for col, query in zip(cols, quick_queries):
    if col.button(query, use_container_width=True):
        st.session_state.messages.append({
            "role": "user",
            "content": query.split(" ", 1)[1],  # Remove emoji
            "timestamp": datetime.now()
        })
        st.session_state.processing = True
        st.rerun()

# Chat container
chat_container = st.container()

# Display chat messages
with chat_container:
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f'<div class="user-message">{message["content"]}</div>', 
                       unsafe_allow_html=True)
        else:
            # Assistant message
            st.markdown(f'<div class="assistant-message">{message["content"]}</div>', 
                       unsafe_allow_html=True)
            
            # Show sources if available
            if "sources" in message:
                with st.expander("📎 Sources", expanded=False):
                    for source in message["sources"]:
                        st.markdown(f"""
                        <div class="source-card">
                            <div style="font-weight: bold; color: #4b5563;">
                                {source['from']}
                            </div>
                            <div style="color: #6b7280; font-size: 0.9em;">
                                {source['subject']}
                            </div>
                            <div style="margin-top: 8px; color: #374151; font-size: 0.85em;">
                                {source['snippet'][:150]}...
                            </div>
                            <div style="color: #9ca3af; font-size: 0.8em; margin-top: 4px;">
                                {source.get('date', '')}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

# Process pending query
if st.session_state.processing:
    with st.spinner("🔍 Searching through your emails..."):
        last_user_msg = st.session_state.messages[-1]["content"]
        
        # Get response
        start_time = time.time()
        result = optimized_ask(last_user_msg, top_k=5)
        response_time = time.time() - start_time
        
        # Add assistant response
        assistant_msg = {
            "role": "assistant",
            "content": result["answer"],
            "sources": result.get("citations", []),
            "timestamp": datetime.now(),
            "response_time": response_time
        }
        st.session_state.messages.append(assistant_msg)
        st.session_state.processing = False
        st.rerun()

# Input area at bottom
st.markdown("---")
col1, col2 = st.columns([6, 1])

with col1:
    user_input = st.text_input(
        "Ask about your emails...",
        key="user_input",
        placeholder="e.g., 'Show me emails from Amazon about orders'",
        label_visibility="collapsed"
    )

with col2:
    send_button = st.button("Send 📤", use_container_width=True)

if (user_input and send_button) or (user_input and st.session_state.get("enter_pressed")):
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "timestamp": datetime.now()
    })
    st.session_state.processing = True
    st.rerun()

# Sidebar with system status
with st.sidebar:
    st.markdown("### 🔧 System Status")
    
    cache_status = get_cache_status()
    
    # Model status
    if cache_status["llm_loaded"]:
        st.markdown('<span class="status-dot status-ready"></span> LLM Ready', 
                   unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-dot status-loading"></span> LLM Loading...', 
                   unsafe_allow_html=True)
    
    if cache_status["index_loaded"]:
        st.markdown('<span class="status-dot status-ready"></span> Index Ready', 
                   unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-dot status-loading"></span> Index Loading...', 
                   unsafe_allow_html=True)
    
    # Stats
    st.markdown("### 📊 Session Stats")
    total_queries = len([m for m in st.session_state.messages if m["role"] == "user"])
    st.metric("Total Queries", total_queries)
    
    if st.session_state.messages and "response_time" in st.session_state.messages[-1]:
        st.metric("Last Response Time", 
                 f"{st.session_state.messages[-1]['response_time']:.2f}s")
    
    # Clear chat button
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = [{
            "role": "assistant",
            "content": "👋 Chat cleared! How can I help you with your emails?",
            "timestamp": datetime.now()
        }]
        st.rerun()
    
    # Tips
    st.markdown("### 💡 Tips")
    st.markdown("""
    - Ask about specific senders: "emails from Amazon"
    - Find by topic: "payment reminders"
    - Time-based: "recent notifications"
    - Multiple criteria: "LinkedIn job alerts this week"
    """)