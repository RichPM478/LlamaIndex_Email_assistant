"""
Modern chat-style interface for email queries
"""
import streamlit as st
from datetime import datetime
import time
import html
import re
from app.qa.lazy_query import lazy_optimized_ask
from app.qa.lazy_query import get_cache_status

def sanitize_html_content(text):
    """Sanitize text content for safe HTML display"""
    if not text:
        return ""
    
    # Convert to string and handle None
    text = str(text) if text is not None else ""
    
    # Remove or replace problematic characters
    text = re.sub(r'[<>"\'\&]', '', text)  # Remove HTML-breaking chars
    text = re.sub(r'[@#%\{\}\[\]\\]', '_', text)  # Replace problematic chars
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    text = text.strip()
    
    # Limit length to prevent UI issues
    if len(text) > 500:
        text = text[:497] + "..."
    
    return text

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
    
    /* Enhanced assistant message container for markdown */
    .assistant-message-container {
        background: #f9fafb;
        border-left: 3px solid #667eea;
        padding: 16px;
        border-radius: 8px;
        margin: 10px 0;
        max-width: 85%;
    }
    
    .assistant-message-container h2 {
        color: #1f2937;
        font-size: 1.3em;
        margin-top: 0;
        margin-bottom: 12px;
    }
    
    .assistant-message-container h3 {
        color: #4b5563;
        font-size: 1.1em;
        margin-top: 16px;
        margin-bottom: 8px;
    }
    
    .assistant-message-container ul {
        margin: 8px 0;
        padding-left: 20px;
    }
    
    .assistant-message-container li {
        margin: 4px 0;
        color: #374151;
    }
    
    .assistant-message-container hr {
        border: none;
        border-top: 1px solid #e5e7eb;
        margin: 16px 0;
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
        "content": "👋 Hi! I'm your simplified email assistant. I can help you find information from your emails using the enhanced ingest pipeline. Try asking me about recent emails, payments, events, or specific senders!",
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
    "💳 What do I need to pay?",
    "🚨 Any urgent emails?",
    "📋 What tasks do I have?"
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
            # Assistant message - use markdown for rich formatting
            # Check if content has markdown formatting
            content = message["content"]
            if '##' in content or '**' in content or '•' in content or '###' in content:
                # Display as markdown with custom styling
                st.markdown(f'<div class="assistant-message-container">', unsafe_allow_html=True)
                st.markdown(content)  # Let Streamlit handle markdown rendering
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                # Fallback for plain text
                safe_content = sanitize_html_content(content)
                st.markdown(f'<div class="assistant-message">{safe_content}</div>', 
                           unsafe_allow_html=True)
            
            
            # Show sources if available
            if "sources" in message:
                with st.expander("📎 Sources", expanded=False):
                    for source in message["sources"]:
                        # Sanitize all source data
                        safe_from = sanitize_html_content(source.get('from', 'Unknown'))
                        safe_subject = sanitize_html_content(source.get('subject', 'No subject'))
                        safe_snippet = sanitize_html_content(source.get('snippet', ''))[:150]
                        safe_date = sanitize_html_content(source.get('date', ''))
                        
                        st.markdown(f"""
                        <div class="source-card">
                            <div style="font-weight: bold; color: #4b5563;">
                                {safe_from}
                            </div>
                            <div style="color: #6b7280; font-size: 0.9em;">
                                {safe_subject}
                            </div>
                            <div style="margin-top: 8px; color: #374151; font-size: 0.85em;">
                                {safe_snippet}...
                            </div>
                            <div style="color: #9ca3af; font-size: 0.8em; margin-top: 4px;">
                                {safe_date}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

# Process pending query
if st.session_state.processing:
    with st.spinner("🔍 Searching through your emails..."):
        last_user_msg = st.session_state.messages[-1]["content"]
        
        # Get response using enhanced ingest pipeline
        start_time = time.time()
        result = lazy_optimized_ask(last_user_msg, top_k=5, include_sources=False)  # Sources shown separately
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
    
    # Email Sync Section
    st.markdown("### 🔄 Email Sync")
    
    # Import sync engine
    from app.sync.live_sync import get_sync_engine
    sync_engine = get_sync_engine()
    sync_stats = sync_engine.get_statistics()
    
    # Live Sync Status with auto-refresh
    if sync_stats['is_running']:
        st.success("🟢 Live Sync Active")
        
        # Show current status with emoji
        status_text = sync_stats['current_status']
        st.info(f"📡 {status_text}")
        
        # Show stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Processed", sync_stats['emails_processed'])
        with col2:
            st.metric("Added", sync_stats['emails_added'])
        with col3:
            st.metric("Filtered", sync_stats['emails_filtered'])
        
        # Auto-refresh every 5 seconds when sync is running
        st.markdown("*Auto-refreshing every 5 seconds...*")
        time.sleep(5)
        st.rerun()
        
        # Stop button
        if st.button("⏹️ Stop Live Sync", use_container_width=True):
            sync_engine.stop()
            st.success("Live sync stopped")
            st.rerun()
    else:
        st.info("🔴 Live Sync Inactive")
        
        # Start live sync
        if st.button("🚀 Start Live Sync", use_container_width=True):
            with st.spinner("Starting live sync..."):
                if sync_engine.start():
                    st.success("✅ Live sync started!")
                    st.rerun()
                else:
                    st.error("❌ Failed to start sync")
        
        # Manual sync
        if st.button("📥 Manual Sync", use_container_width=True):
            with st.spinner("Syncing emails..."):
                try:
                    if sync_engine.connect():
                        new_emails = sync_engine.fetch_new_emails()
                        if new_emails:
                            results = sync_engine.process_new_emails(new_emails)
                            if results['high_quality']:
                                sync_engine.update_index_incremental(results['high_quality'])
                            st.success(f"✅ Synced {results['accepted']} emails")
                            st.info(f"Filtered: {results['rejected']}")
                        else:
                            st.info("📭 No new emails")
                        sync_engine.imap_connection = None
                    else:
                        st.error("Connection failed")
                except Exception as e:
                    st.error(f"Sync error: {str(e)[:50]}...")
    
    # Sync Configuration (collapsible)
    with st.expander("⚙️ Sync Settings"):
        quality_threshold = st.slider(
            "Quality Threshold", 0, 100, 
            int(sync_engine.quality_threshold),
            help="Minimum quality to accept emails"
        )
        if quality_threshold != sync_engine.quality_threshold:
            sync_engine.quality_threshold = quality_threshold
            st.info(f"Quality updated to {quality_threshold}")
        
        max_marketing = st.slider(
            "Max Marketing", 0, 100,
            int(sync_engine.max_marketing_score),
            help="Reject emails above this marketing score"  
        )
        if max_marketing != sync_engine.max_marketing_score:
            sync_engine.max_marketing_score = max_marketing
            st.info(f"Marketing limit updated to {max_marketing}")
    
    st.markdown("---")
    
    # Clear chat button
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = [{
            "role": "assistant",
            "content": "👋 Chat cleared! How can I help you with your emails using the enhanced pipeline?",
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