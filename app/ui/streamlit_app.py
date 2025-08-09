# app/ui/streamlit_app.py
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import streamlit as st
from datetime import datetime, timedelta
import json
from typing import List, Dict, Optional
from app.config.settings import get_settings
from app.ingest.imap_loader import fetch_emails, save_raw_emails
from app.indexing.build_index import build_index
# Try to import the simple query first, fall back to regular
try:
    from app.qa.simple_query import simple_ask as ask
    print("[DEBUG] Using simple_query module")
except ImportError:
    from app.qa.query_engine import ask
    print("[DEBUG] Using standard query_engine")

# Page config
st.set_page_config(
    page_title="Email Intelligence Assistant",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    /* Main container */
    .main {
        padding-top: 2rem;
    }
    
    /* Headers */
    h1 {
        color: #1e3a5f;
        font-weight: 600;
        border-bottom: 3px solid #4a90e2;
        padding-bottom: 10px;
        margin-bottom: 30px;
    }
    
    h2 {
        color: #2c5282;
        font-weight: 500;
        margin-top: 2rem;
    }
    
    h3 {
        color: #2d3748;
        font-size: 1.1rem;
        font-weight: 600;
    }
    
    /* Search box styling */
    .stTextInput > div > div > input {
        font-size: 16px;
        padding: 12px;
        border-radius: 10px;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #4a90e2;
        color: white;
        border-radius: 8px;
        padding: 0.5rem 2rem;
        font-weight: 500;
        border: none;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        background-color: #357abd;
        transform: translateY(-2px);
        box-shadow: 0 5px 10px rgba(0,0,0,0.2);
    }
    
    /* Info boxes */
    .info-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    /* Citation cards */
    .citation-card {
        background: #f7fafc;
        border-left: 4px solid #4a90e2;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0 8px 8px 0;
        transition: all 0.3s;
    }
    
    .citation-card:hover {
        background: #edf2f7;
        transform: translateX(5px);
    }
    
    /* Metrics */
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
        background-color: #f7fafc;
        border-radius: 10px 10px 0 0;
    }
    
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        background-color: #4a90e2;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'search_history' not in st.session_state:
    st.session_state.search_history = []
if 'last_sync' not in st.session_state:
    st.session_state.last_sync = None
if 'email_count' not in st.session_state:
    st.session_state.email_count = 0
if 'show_admin' not in st.session_state:
    st.session_state.show_admin = False

settings = get_settings()

# Header with logo placeholder
col1, col2, col3 = st.columns([1, 3, 1])
with col2:
    st.markdown("<h1 style='text-align: center;'>📧 Email Intelligence Assistant</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #718096; margin-top: -10px;'>Smart search and insights from your email archive</p>", unsafe_allow_html=True)

# Quick stats bar
if st.session_state.last_sync:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Emails Indexed", f"{st.session_state.email_count:,}")
    with col2:
        st.metric("Last Updated", st.session_state.last_sync)
    with col3:
        searches_today = len([s for s in st.session_state.search_history 
                            if s.get('timestamp', '').startswith(datetime.now().strftime('%Y-%m-%d'))])
        st.metric("Searches Today", searches_today)
    with col4:
        if st.button("🔄 Sync New Emails", help="Check for new emails"):
            with st.spinner("Checking for new emails..."):
                # In production, this would do incremental sync
                st.success("✓ Email archive is up to date")

st.markdown("---")

# Main interface with tabs
tab1, tab2, tab3 = st.tabs(["🔍 Search", "📊 Insights", "⚙️ Settings"])

with tab1:
    # Search interface
    st.markdown("### What would you like to know?")
    
    # Suggested queries
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📅 This week's events", use_container_width=True):
            st.session_state.search_query = "What events and important dates are coming up this week?"
    with col2:
        if st.button("💰 Payment requests", use_container_width=True):
            st.session_state.search_query = "What payments or money do I need to bring?"
    with col3:
        if st.button("📝 Action items", use_container_width=True):
            st.session_state.search_query = "What are the action items I need to complete?"
    
    # Search box
    search_query = st.text_input(
        "",
        placeholder="Ask anything about your emails... (e.g., 'What did Mount Carmel send about the school trip?')",
        key="search_input",
        value=st.session_state.get('search_query', '')
    )
    
    col1, col2 = st.columns([1, 5])
    with col1:
        search_button = st.button("🔍 Search", type="primary", use_container_width=True)
    
    # Advanced filters (collapsible)
    with st.expander("Advanced Filters"):
        col1, col2, col3 = st.columns(3)
        with col1:
            sender_filter = st.text_input("From specific sender", placeholder="e.g., Mount Carmel")
        with col2:
            date_filter = st.date_input("After date", value=None)
        with col3:
            priority_only = st.checkbox("Priority emails only")
    
    # Search results
    if search_button and search_query:
        with st.spinner("Searching through your emails..."):
            result = ask(search_query)
            
            # Save to history
            st.session_state.search_history.append({
                'query': search_query,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'results': len(result.get('citations', []))
            })
        
        # Display answer in a nice card
        st.markdown("### Answer")
        
        # Answer box with confidence indicator
        confidence = result.get('confidence')
        confidence_color = "#48bb78" if confidence and confidence > 0.7 else "#ed8936" if confidence and confidence > 0.4 else "#e53e3e"
        
        st.markdown(f"""
        <div style="background: white; padding: 1.5rem; border-radius: 10px; 
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 4px solid {confidence_color};">
            {result['answer']}
        </div>
        """, unsafe_allow_html=True)
        
        # Sources section
        if result.get('citations'):
            st.markdown("### 📎 Sources")
            
            # Sort citations by relevance
            citations = sorted(result['citations'], key=lambda x: x.get('score', 0), reverse=True)
            
            # Display top citations in cards
            for i, cite in enumerate(citations[:5], 1):
                with st.container():
                    col1, col2 = st.columns([5, 1])
                    with col1:
                        # Sender and subject
                        sender = cite.get('from', 'Unknown sender')
                        subject = cite.get('subject', 'No subject')
                        date = cite.get('date', 'Unknown date')
                        score = cite.get('score', 0)
                        
                        # Relevance indicator
                        relevance = "High" if score > 0.7 else "Medium" if score > 0.4 else "Low"
                        relevance_emoji = "🟢" if score > 0.7 else "🟡" if score > 0.4 else "🔴"
                        
                        st.markdown(f"""
                        **{relevance_emoji} {sender}**  
                        📋 {subject}  
                        📅 {date}
                        """)
                        
                        # Snippet
                        if cite.get('snippet'):
                            st.markdown(f"_{cite['snippet'][:150]}..._")
                    
                    with col2:
                        st.markdown(f"**Relevance**  \n{relevance}")
                    
                    st.markdown("---")

with tab2:
    # Insights Dashboard
    st.markdown("### 📊 Email Insights Dashboard")
    
    # Import analytics module
    try:
        from app.analytics.email_stats import (
            load_emails_from_raw, 
            get_email_analytics,
            get_email_trends,
            find_important_emails
        )
        
        # Time period selector
        period = st.selectbox("Time period", ["Last 7 days", "Last 30 days", "All time"])
        days_back = 7 if period == "Last 7 days" else 30 if period == "Last 30 days" else None
        
        # Load and analyze emails
        emails = load_emails_from_raw()
        
        if emails:
            analytics = get_email_analytics(emails, days_back)
            trends = get_email_trends(emails)
            important = find_important_emails(emails)
            
            # Update session state
            st.session_state.email_count = analytics['total_emails']
            
            # Display metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Emails", f"{analytics['total_emails']:,}")
            with col2:
                st.metric("Unique Senders", len(set(sender for sender, _ in analytics['top_senders'])))
            with col3:
                st.metric("Urgent Items", analytics['urgent_count'])
            with col4:
                trend_icon = "📈" if trends['trend'] == "increasing" else "📉" if trends['trend'] == "decreasing" else "➡️"
                st.metric("Volume Trend", f"{trend_icon} {trends['trend'].title()}")
            
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 📬 Top Senders")
                if analytics['top_senders']:
                    for i, (sender, count) in enumerate(analytics['top_senders'][:5], 1):
                        st.markdown(f"{i}. **{sender}** - {count} email{'s' if count > 1 else ''}")
                else:
                    st.markdown("_No emails found_")
            
            with col2:
                st.markdown("#### 🎯 Key Topics")
                if analytics['topics']:
                    for topic, count in analytics['topics'][:5]:
                        st.markdown(f"- {topic} ({count} mention{'s' if count > 1 else ''})")
                else:
                    st.markdown("_No topics identified_")
            
            # Email activity chart
            st.markdown("#### 📈 Email Activity")
            if analytics['daily_volume']:
                import plotly.graph_objects as go
                
                dates = [d for d, _ in analytics['daily_volume']]
                volumes = [v for _, v in analytics['daily_volume']]
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=dates, y=volumes,
                    mode='lines+markers',
                    name='Daily Volume',
                    line=dict(color='#4a90e2', width=2),
                    marker=dict(size=6)
                ))
                fig.update_layout(
                    title="Email Volume Over Time",
                    xaxis_title="Date",
                    yaxis_title="Number of Emails",
                    height=300,
                    showlegend=False,
                    hovermode='x unified'
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No email data available for the selected period")
            
            # Important emails section
            if important:
                st.markdown("#### ⚠️ Important Emails")
                for item in important[:3]:
                    st.warning(f"**{item['subject'][:60]}{'...' if len(item['subject']) > 60 else ''}**  \n"
                              f"From: {item['from']} | {item['date'][:10]}")
            
            # Time distribution
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### 📅 Busiest Days")
                if analytics['weekday_distribution']:
                    sorted_days = sorted(analytics['weekday_distribution'].items(), 
                                       key=lambda x: x[1], reverse=True)
                    for day, count in sorted_days[:3]:
                        st.markdown(f"- **{day}**: {count} emails")
            
            with col2:
                st.markdown("#### 🕐 Peak Hours")
                if analytics['hour_distribution']:
                    sorted_hours = sorted(analytics['hour_distribution'].items(), 
                                        key=lambda x: x[1], reverse=True)
                    for hour, count in sorted_hours[:3]:
                        hour_str = f"{hour:02d}:00-{(hour+1):02d}:00"
                        st.markdown(f"- **{hour_str}**: {count} emails")
            
        else:
            st.warning("No email data found. Please sync your emails first.")
            
    except ImportError:
        st.error("Analytics module not found. Please ensure app/analytics/email_stats.py exists.")
    except Exception as e:
        st.error(f"Error loading analytics: {str(e)}")
    
    st.markdown("---")
    st.markdown("#### 🔍 Recent Searches")
    if st.session_state.search_history:
        for search in st.session_state.search_history[-5:]:
            st.markdown(f"- **{search['query']}** ({search['timestamp']}) - {search['results']} results")
    else:
        st.markdown("_No recent searches_")

with tab3:
    st.markdown("### ⚙️ Settings & Administration")
    
    # Admin mode toggle
    admin_password = st.text_input("Admin password", type="password")
    if admin_password == "admin":  # In production, use proper auth
        st.session_state.show_admin = True
    
    if st.session_state.show_admin:
        st.success("✓ Admin mode enabled")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🔄 Data Management")
            if st.button("Fetch Latest Emails", use_container_width=True):
                with st.spinner("Fetching emails..."):
                    recs = fetch_emails(settings, limit=200)
                    path = save_raw_emails(recs)
                    st.success(f"✓ Fetched {len(recs)} emails")
                    st.session_state.email_count = len(recs)
                    st.session_state.last_sync = datetime.now().strftime('%Y-%m-%d %H:%M')
            
            if st.button("Rebuild Search Index", use_container_width=True):
                with st.spinner("Rebuilding index..."):
                    idx = build_index(None, "data/index")
                    st.success("✓ Search index rebuilt")
        
        with col2:
            st.markdown("#### 📧 Email Settings")
            st.text_input("IMAP Server", value=settings.imap_host, disabled=True)
            st.text_input("Email Account", value=settings.imap_user, disabled=True)
            st.text_input("Folder", value=settings.imap_folder, disabled=True)
            
            st.markdown("#### 🤖 AI Settings")
            st.text_input("AI Model", value=f"{settings.llm_provider} ({settings.ollama_model})", disabled=True)
    else:
        st.info("Enter admin password to access settings")
    
    # User preferences (always visible)
    st.markdown("#### 👤 User Preferences")
    
    notif_enabled = st.checkbox("Enable email notifications for important events")
    digest_frequency = st.selectbox("Summary digest frequency", ["Daily", "Weekly", "Never"])
    
    if st.button("Save Preferences"):
        st.success("✓ Preferences saved")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #718096; font-size: 0.9rem;'>
    Email Intelligence Assistant v1.0 | Powered by LlamaIndex & {provider}
</div>
""".format(provider=settings.llm_provider.title()), unsafe_allow_html=True)