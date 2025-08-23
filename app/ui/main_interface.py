"""
Main interface for Email Intelligence System with Evaluation Dashboard
Combines chat interface with performance monitoring
"""
import streamlit as st
from datetime import datetime
import time
import html
import re
import sys
from pathlib import Path
import asyncio

# Add src to path for new architecture
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import components  
from src.infrastructure.config.settings import get_config
from src.infrastructure.migration.bridge import get_llm, get_embed_model
# Use flexible query bridge for better compatibility
from app.qa.flexible_query_bridge import ask, get_cache_status

# Import evaluation dashboard
from app.ui.evaluation_dashboard import render_evaluation_dashboard

# Import sync functionality
try:
    from app.sync.live_sync import EmailSyncEngine
    SYNC_AVAILABLE = True
except ImportError:
    SYNC_AVAILABLE = False

def sanitize_html_content(text):
    """Sanitize text content for safe HTML display"""
    if not text:
        return ""
    
    # Convert to string and handle None
    text = str(text) if text is not None else ""
    
    # Remove or replace problematic characters
    text = re.sub(r'[<>"\'\\&]', '', text)  # Remove HTML-breaking chars
    text = re.sub(r'[@#%\\{\\}\\[\\]\\\\]', '_', text)  # Replace problematic chars
    text = re.sub(r'\\s+', ' ', text)  # Normalize whitespace
    text = text.strip()
    
    # Limit length to prevent UI issues
    if len(text) > 500:
        text = text[:497] + "..."
    
    return text

def init_session_state():
    """Initialize session state variables"""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    if 'config' not in st.session_state:
        st.session_state.config = get_config()
    
    if 'current_provider' not in st.session_state:
        st.session_state.current_provider = st.session_state.config.get_default_provider("models")
    
    if 'current_embedding_provider' not in st.session_state:
        # Force to sentence-transformers to match the index built with mixedbread embeddings
        st.session_state.current_embedding_provider = "sentence-transformers"

def setup_providers():
    """Setup and initialize providers based on current selection"""
    # Monkey-patch the providers to use new architecture
    import app.llm.provider as llm_provider
    import app.embeddings.provider as embed_provider
    
    llm_provider.configure_llm = lambda settings=None: get_llm(st.session_state.current_provider)
    embed_provider.configure_embeddings = lambda settings=None: get_embed_model(st.session_state.current_embedding_provider)

def render_email_update_progress():
    """Render the email update progress UI"""
    import asyncio
    from app.sync.email_updater import get_email_updater
    
    st.markdown("## 📧 Updating Your Emails")
    
    # Create progress containers
    progress_bar = st.progress(0)
    status_text = st.empty()
    details_container = st.container()
    
    # Initialize updater
    updater = get_email_updater()
    
    # Progress callback
    progress_data = {"message": "", "percentage": 0, "error": False}
    
    def update_progress(data):
        progress_data.update(data)
        progress_bar.progress(data["percentage"] / 100)
        
        if data.get("error"):
            status_text.error(f"❌ {data['message']}")
        else:
            status_text.info(f"⏳ {data['message']}")
    
    # Run the update
    try:
        # Run async update in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(updater.update_emails(update_progress))
        
        # Show results
        if result["success"]:
            status_text.success(f"✅ {result['message']}")
            
            with details_container:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("New Emails", result.get("new_emails", 0))
                with col2:
                    st.metric("Total Emails", result.get("total_emails", 0))
                with col3:
                    duration = result.get("duration", 0)
                    st.metric("Time Taken", f"{duration:.1f}s")
            
            # Add success message to chat
            if result.get("new_emails", 0) > 0:
                st.balloons()
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"🎉 Successfully updated! Found {result['new_emails']} new emails. You can now ask me questions about them!"
                })
        else:
            status_text.error(f"❌ {result.get('message', 'Update failed')}")
            
            # Show error details
            if result.get("action_needed") == "configure_email":
                st.error("Please configure your email settings in the System Configuration tab")
            elif result.get("action_needed") == "retry":
                if st.button("🔄 Retry Update"):
                    st.rerun()
    
    except Exception as e:
        status_text.error(f"❌ Update failed: {str(e)}")
        st.error("An unexpected error occurred. Please check your settings and try again.")
    
    finally:
        # Clear update flag
        st.session_state.update_in_progress = False
        
        # Show continue button
        if st.button("← Back to Chat", type="primary"):
            st.rerun()

def render_chat_interface():
    """Render the main chat interface."""
    
    # Handle email update if in progress
    if st.session_state.get("update_in_progress", False):
        render_email_update_progress()
        return
    
    # Welcome message
    if not st.session_state.messages:
        st.markdown("""
        <div class="assistant-message-container">
            <h3>👋 Welcome to your Email Assistant!</h3>
            <p>I can help you search and analyze your emails. Try asking:</p>
            <ul>
                <li>"What important emails did I receive today?"</li>
                <li>"Summarize emails from John about the project"</li>
                <li>"Find all meeting invitations this week"</li>
                <li>"Show me emails that need a response"</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Display chat history
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f'<div class="user-message">{html.escape(message["content"])}</div>', unsafe_allow_html=True)
        else:
            # Format assistant response
            response_html = f"""
            <div class="assistant-message-container">
                {message["content"]}
            </div>
            """
            st.markdown(response_html, unsafe_allow_html=True)
            
            # Show citations if available
            if "citations" in message and message["citations"]:
                with st.expander(f"📚 View {len(message['citations'])} Citations"):
                    for i, citation in enumerate(message["citations"], 1):
                        st.markdown(f"""
                        <div style="background: #e0e7ff; padding: 10px; margin: 8px 0; border-radius: 4px;">
                            <strong>Source {i}:</strong><br>
                            {html.escape(sanitize_html_content(str(citation)))}
                        </div>
                        """, unsafe_allow_html=True)
    
    # Chat input
    if prompt := st.chat_input("Ask about your emails..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.markdown(f'<div class="user-message">{html.escape(prompt)}</div>', unsafe_allow_html=True)
        
        # Setup providers before querying
        setup_providers()
        
        # Generate response
        with st.spinner(f"Thinking with {st.session_state.current_provider}..."):
            try:
                result = ask(prompt)
                
                answer = result.get('answer', 'I could not find an answer to your question.')
                confidence = result.get('confidence', 0)
                citations = result.get('citations', [])
                
                # Add confidence badge
                if confidence >= 0.8:
                    confidence_class = "background: #10b981; color: white; padding: 4px 12px; border-radius: 12px; font-size: 0.85em;"
                    confidence_label = "High Confidence"
                elif confidence >= 0.5:
                    confidence_class = "background: #f59e0b; color: white; padding: 4px 12px; border-radius: 12px; font-size: 0.85em;"
                    confidence_label = "Medium Confidence"
                else:
                    confidence_class = "background: #ef4444; color: white; padding: 4px 12px; border-radius: 12px; font-size: 0.85em;"
                    confidence_label = "Low Confidence"
                
                response_content = f"""
                <div style="margin-bottom: 10px;">
                    <span style="{confidence_class}">{confidence_label}</span>
                </div>
                <div style="margin-top: 10px;">
                    {answer.replace('\\n', '<br>')}
                </div>
                """
                
                message_data = {
                    "role": "assistant",
                    "content": response_content,
                    "citations": citations,
                    "confidence": confidence
                }
                st.session_state.messages.append(message_data)
                
                # Display response
                st.markdown(f"""
                <div class="assistant-message-container">
                    {response_content}
                </div>
                """, unsafe_allow_html=True)
                
                # Show citations
                if citations:
                    with st.expander(f"📚 View {len(citations)} Citations"):
                        for i, citation in enumerate(citations, 1):
                            st.markdown(f"""
                            <div style="background: #e0e7ff; padding: 10px; margin: 8px 0; border-radius: 4px;">
                                <strong>Source {i}:</strong><br>
                                {html.escape(sanitize_html_content(str(citation)))}
                            </div>
                            """, unsafe_allow_html=True)
            
            except Exception as e:
                error_message = f"Sorry, I encountered an error: {str(e)}"
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f'<div style="color: #ef4444;">{html.escape(error_message)}</div>'
                })
                st.error(error_message)

def render_configuration():
    """Render system configuration interface."""
    
    st.subheader("⚙️ System Configuration")
    
    config = get_config()
    
    # Model Configuration
    st.markdown("### 🤖 Model Providers")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Available Models:**")
        model_providers = config.get_enabled_providers("models")
        for provider in model_providers:
            status = "🟢" if provider.get("enabled") else "🔴"
            st.write(f"{status} {provider['type'].upper()}")
    
    with col2:
        st.markdown("**Available Embeddings:**")
        embed_providers = config.get_enabled_providers("embeddings")
        for provider in embed_providers:
            status = "🟢" if provider.get("enabled") else "🔴"
            st.write(f"{status} {provider['type'].upper()}")
    
    # Performance Settings
    st.markdown("### ⚡ Performance Settings")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        chunk_size = st.number_input(
            "Chunk Size",
            value=config.get("processing.chunking.max_chunk_size", 512),
            min_value=128,
            max_value=2048,
            help="Size of text chunks for processing"
        )
    
    with col2:
        batch_size = st.number_input(
            "Batch Size",
            value=config.get("processing.batch.size", 100),
            min_value=10,
            max_value=500,
            help="Number of items to process in parallel"
        )
    
    with col3:
        quality_threshold = st.slider(
            "Quality Threshold",
            value=config.get("processing.quality.min_quality_score", 40.0),
            min_value=0.0,
            max_value=100.0,
            help="Minimum quality score for emails"
        )
    
    # Feature Flags
    st.markdown("### 🎛️ Feature Flags")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        cache_enabled = st.checkbox(
            "Enable Caching",
            value=config.is_feature_enabled("cache"),
            help="Cache responses for faster performance"
        )
    
    with col2:
        security_enabled = st.checkbox(
            "Enable Security",
            value=config.is_feature_enabled("security.encryption"),
            help="Encrypt sensitive data"
        )
    
    with col3:
        monitoring_enabled = st.checkbox(
            "Enable Monitoring",
            value=config.is_feature_enabled("monitoring"),
            help="Track system performance"
        )
    
    # Save configuration
    if st.button("💾 Save Configuration", type="primary"):
        # Update configuration
        config.update("processing.chunking.max_chunk_size", chunk_size)
        config.update("processing.batch.size", batch_size)
        config.update("processing.quality.min_quality_score", quality_threshold)
        config.update("cache.enabled", cache_enabled)
        config.update("security.encryption.enabled", security_enabled)
        config.update("monitoring.enabled", monitoring_enabled)
        
        st.success("✅ Configuration saved successfully!")
        st.balloons()

# Configure page
st.set_page_config(
    page_title="Email Intelligence System - Powered by Gemini 2.5",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
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
    
    .assistant-message-container {
        background: #f9fafb;
        border-left: 3px solid #667eea;
        padding: 16px;
        border-radius: 8px;
        margin: 10px 0;
        max-width: 85%;
    }
    
    .provider-badge {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.8em;
        font-weight: 500;
        display: inline-block;
        margin-left: 8px;
    }
    
    .provider-badge-gemini {
        background: linear-gradient(135deg, #4285f4 0%, #ea4335 100%);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
init_session_state()

# Main interface with tabs
st.title("📧 Email Intelligence System v2.0")

# Provider indicator
provider_class = f"provider-badge-{st.session_state.current_provider}"
st.markdown(
    f'<div>Powered by <span class="provider-badge {provider_class}">{st.session_state.current_provider.upper()}</span></div>',
    unsafe_allow_html=True
)

# Create tabs for different functionalities
tab1, tab2, tab3 = st.tabs([
    "💬 Chat Assistant",
    "🎯 Performance Dashboard", 
    "⚙️ System Configuration"
])

with tab1:
    render_chat_interface()

with tab2:
    render_evaluation_dashboard()

with tab3:
    render_configuration()

# Sidebar for quick controls
with st.sidebar:
    st.title("⚙️ Quick Controls")
    
    # Email Update Section - PROMINENT PLACEMENT
    st.subheader("📧 Email Updates")
    
    from app.sync.email_updater import get_email_updater
    updater = get_email_updater()
    
    # Get last update info
    last_update_info = updater.get_last_update_info()
    
    # Update button with status
    col1, col2 = st.columns([2, 1])
    with col1:
        if st.button("🔄 Update Emails", type="primary", use_container_width=True, key="update_sidebar"):
            st.session_state.update_in_progress = True
            st.rerun()
    
    with col2:
        if last_update_info["status"] == "never":
            st.caption("Never")
        else:
            st.caption(last_update_info["time_ago"])
    
    # Show email count
    if last_update_info["email_count"] > 0:
        st.metric("Total Emails", f"{last_update_info['email_count']:,}")
    
    # Show update recommendation
    if updater.needs_update():
        st.info("💡 Update recommended", icon="ℹ️")
    
    st.divider()
    
    # Provider selection
    st.subheader("🤖 AI Provider")
    
    config = st.session_state.config
    model_providers = [p["type"] for p in config.get_enabled_providers("models")]
    
    selected_model = st.selectbox(
        "Language Model",
        options=model_providers,
        index=model_providers.index(st.session_state.current_provider) if st.session_state.current_provider in model_providers else 0,
        help="Select the AI model for generating responses"
    )
    
    if selected_model != st.session_state.current_provider:
        st.session_state.current_provider = selected_model
        st.session_state.config.update("providers.models.default", selected_model)
        setup_providers()
        st.rerun()
    
    # Quick status
    st.divider()
    st.subheader("📊 Quick Status")
    
    # Provider status indicator
    try:
        llm = get_llm(st.session_state.current_provider)
        st.success(f"✅ {st.session_state.current_provider.upper()} Ready")
    except Exception:
        st.error(f"❌ {st.session_state.current_provider.upper()} Error")
    
    # Cache status
    cache_status = get_cache_status()
    loaded_count = sum([
        cache_status.get('llm_loaded', False),
        cache_status.get('embed_model_loaded', False), 
        cache_status.get('index_loaded', False),
        cache_status.get('imports_loaded', False)
    ])
    st.metric("Cache", f"{loaded_count}/4 loaded")
    
    # Quick actions
    st.divider()
    st.subheader("⚡ Quick Actions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Sync", use_container_width=True):
            st.info("Syncing emails...")
    
    with col2:
        if st.button("🧹 Clear", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    
    # Add rebuild index button
    if st.button("🔨 Rebuild Index", use_container_width=True, help="Rebuild the email search index with new embeddings"):
        with st.spinner("Rebuilding index with Gemini embeddings..."):
            try:
                # Simple approach: delete the index directory if it exists
                import shutil
                import os
                from pathlib import Path
                
                index_dir = Path("data/index")
                if index_dir.exists():
                    shutil.rmtree(index_dir)
                
                st.success("Index cleared! Please ingest emails again to rebuild with Gemini.")
                st.info("Use 'Fetch New Emails' or run: python -m app.ingest.main")
                
            except Exception as e:
                st.error(f"Error rebuilding index: {e}")
                st.info("Try manually deleting the data/index folder and re-ingesting emails.")

# Footer
st.divider()
st.caption(f"Email Intelligence System v2.0 | {st.session_state.current_provider.upper()} Model | RAGAS Evaluation | {datetime.now().strftime('%Y-%m-%d %H:%M')}")

if __name__ == "__main__":
    # This file is meant to be run with: streamlit run app/ui/main_interface.py
    pass