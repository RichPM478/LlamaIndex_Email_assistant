# app/ui/streamlit_app.py
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import streamlit as st
from datetime import datetime
import time
from app.config.settings import get_settings
from app.ingest.imap_loader import fetch_emails, save_raw_emails
from app.indexing.incremental_indexer import incremental_indexer
from app.intelligence.email_analyzer import email_analyzer
from app.ui.theme_manager import theme_manager
from app.security.auth import auth

# Use intelligent query engine for enhanced search (Phase 3C)
from app.qa.intelligent_query import intelligent_ask as ask

# Page config
st.set_page_config(
    page_title="Email Intelligence Assistant",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Apply theme and get CSS
st.markdown(theme_manager.get_css_theme(), unsafe_allow_html=True)

# Apply keyboard shortcuts
st.markdown(theme_manager.get_keyboard_shortcuts_js(), unsafe_allow_html=True)

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

# Header with theme toggle and logo
col1, col2, col3 = st.columns([1, 2, 1])
with col1:
    theme_manager.render_theme_toggle()

with col2:
    st.markdown("# 📧 Email Intelligence Assistant")
    st.markdown("*Smart search and insights from your email archive*")

with col3:
    # Quick stats or notifications could go here
    pass

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
        # Import sync engine
        from app.sync.live_sync import get_sync_engine
        sync_engine = get_sync_engine()
        sync_stats = sync_engine.get_statistics()
        
        if sync_stats['is_running']:
            st.success("🟢 Live Sync Active")
        else:
            if st.button("🔄 Quick Sync", help="Manually check for new emails"):
                with st.spinner("Checking for new emails..."):
                    try:
                        if sync_engine.connect():
                            new_emails = sync_engine.fetch_new_emails()
                            if new_emails:
                                results = sync_engine.process_new_emails(new_emails)
                                if results['high_quality']:
                                    sync_engine.update_index_incremental(results['high_quality'])
                                st.success(f"✓ Synced {results['accepted']} new emails")
                                st.session_state.email_count += results['accepted']
                                st.session_state.last_sync = datetime.now().strftime('%Y-%m-%d %H:%M')
                            else:
                                st.info("✓ Email archive is up to date")
                            sync_engine.imap_connection = None
                        else:
                            st.error("Failed to connect to email server")
                    except Exception as e:
                        st.error(f"Sync error: {e}")

st.markdown("---")

# Main interface with tabs
tab1, tab2, tab3 = st.tabs(["🔍 Search", "📊 Insights", "⚙️ Settings"])

with tab1:
    # Search interface
    st.markdown("### What would you like to know?")
    
    # Smart suggested queries (Phase 3C)
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📅 This week's events", use_container_width=True):
            st.session_state.search_query = "events and meetings this week"
    with col2:
        if st.button("💰 Bills and payments", use_container_width=True):
            st.session_state.search_query = "what do I need to pay this month?"
    with col3:
        if st.button("🚨 Urgent items", use_container_width=True):
            st.session_state.search_query = "urgent and important emails from last week"
    
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
        search_start_time = time.time()
        
        with st.spinner("🔍 Searching through your emails..."):
            result = ask(search_query)
            
        search_duration = time.time() - search_start_time
            
        # Save to history with enhanced metadata
        st.session_state.search_history.append({
            'query': search_query,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'results': len(result.get('citations', [])),
            'duration': search_duration,
            'confidence': result.get('confidence', 0)
        })
        
        # Enhanced Answer Display
        st.markdown("### 🎯 Answer")
        
        # Answer statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Response Time", f"{search_duration:.2f}s")
        with col2:
            confidence = result.get('confidence', 0)
            if confidence:
                st.metric("Confidence", f"{confidence:.2%}")
        with col3:
            st.metric("Sources", len(result.get('citations', [])))
        with col4:
            filters_applied = "Yes" if result.get('metadata_filters_applied', False) else "No"
            st.metric("Filters Used", filters_applied)
        
        # Answer box with enhanced styling
        confidence_color = "#48bb78" if confidence and confidence > 0.7 else "#ed8936" if confidence and confidence > 0.4 else "#e53e3e"
        confidence_label = "High" if confidence and confidence > 0.7 else "Medium" if confidence and confidence > 0.4 else "Low"
        
        # Use theme-aware styling
        colors = theme_manager.get_theme_colors()
        
        answer_html = f"""
        <div class="search-result" style="
            background: {colors['card_bg']}; 
            border-left: 4px solid {confidence_color};
            padding: 1.5rem; 
            border-radius: 10px; 
            box-shadow: {colors['shadow']};
            border: 1px solid {colors['border_color']};
            margin: 1rem 0;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                <div style="color: {colors['text_primary']};">
                    <strong>AI Response</strong>
                </div>
                <div style="
                    background: {confidence_color}; 
                    color: white; 
                    padding: 0.3rem 0.8rem; 
                    border-radius: 15px; 
                    font-size: 0.8rem;">
                    {confidence_label} Confidence
                </div>
            </div>
            <div style="color: {colors['text_primary']}; line-height: 1.6;">
                {result['answer']}
            </div>
        </div>
        """
        st.markdown(answer_html, unsafe_allow_html=True)
        
        # Enhanced Sources section
        if result.get('citations'):
            st.markdown("### 📎 Email Sources")
            
            # Sort citations by relevance and add intelligence
            citations = sorted(result['citations'], key=lambda x: x.get('score', 0), reverse=True)
            
            # Display citations with enhanced information
            for i, cite in enumerate(citations[:5], 1):
                # Try to get additional intelligence for this email
                email_insights = None
                try:
                    email_data = {
                        'from': cite.get('from', ''),
                        'subject': cite.get('subject', ''),
                        'body': cite.get('snippet', ''),
                        'date': cite.get('date', '')
                    }
                    email_insights = email_analyzer.analyze_email(email_data)
                except Exception as e:
                    pass
                
                with st.container():
                    # Create enhanced citation card with clean data
                    sender = cite.get('sender') or cite.get('from', 'Unknown sender')
                    subject = cite.get('subject', 'No subject')
                    date = cite.get('date', 'Unknown date')
                    score = cite.get('score', 0)
                    
                    # Clean up sender display - remove email formatting artifacts
                    if '<' in sender and '>' in sender:
                        # Extract just the name part if it's in format "Name" <email>
                        name_part = sender.split('<')[0].strip().strip('"\'')
                        if name_part:
                            sender = name_part
                        else:
                            # Use email username part
                            email_part = sender[sender.find('<')+1:sender.find('>')]
                            sender = email_part.split('@')[0] if '@' in email_part else sender
                    
                    # Clean up date display
                    if date and len(date) > 50:
                        # Try to extract just date part from long date strings
                        import re
                        date_match = re.search(r'\d{1,2}\s+\w{3}\s+\d{4}', date)
                        if date_match:
                            date = date_match.group()
                        else:
                            date = date[:20] + "..."
                    
                    # Relevance and importance indicators
                    relevance = "High" if score > 0.7 else "Medium" if score > 0.4 else "Low"
                    relevance_emoji = "🟢" if score > 0.7 else "🟡" if score > 0.4 else "🔴"
                    
                    # Add importance and category badges
                    badges = [f"Relevance: {relevance}"]
                    
                    if email_insights:
                        importance_emoji = {
                            'CRITICAL': '🔥',
                            'HIGH': '⚠️',
                            'MEDIUM': '📄',
                            'LOW': '📝',
                            'MINIMAL': '💭'
                        }.get(email_insights.importance_level.name, '📄')
                        
                        badges.append(f"Importance: {importance_emoji} {email_insights.importance_level.name.title()}")
                        
                        if email_insights.categories:
                            category_emojis = {
                                'urgent': '🚨', 'meeting': '📅', 'payment': '💰',
                                'task': '✅', 'social': '👥', 'work': '💼'
                            }
                            main_category = email_insights.categories[0].value
                            category_emoji = category_emojis.get(main_category, '📋')
                            badges.append(f"Type: {category_emoji} {main_category.title()}")
                    
                    # Create citation card HTML
                    citation_html = f"""
                    <div class="citation-card" style="
                        background: {colors['accent_bg']}; 
                        border-left: 4px solid {confidence_color};
                        padding: 1rem; 
                        margin: 1rem 0; 
                        border-radius: 0 8px 8px 0;
                        border: 1px solid {colors['border_color']};
                        transition: all 0.3s ease;">
                        
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
                            <div>
                                <div style="font-weight: 600; color: {colors['text_primary']}; margin-bottom: 0.3rem;">
                                    {relevance_emoji} {sender}
                                </div>
                                <div style="color: {colors['text_secondary']}; font-size: 0.9rem;">
                                    📋 {subject}
                                </div>
                                <div style="color: {colors['text_secondary']}; font-size: 0.8rem; margin-top: 0.2rem;">
                                    📅 {date}
                                </div>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-size: 0.8rem; color: {colors['text_secondary']};">
                                    Score: {score:.3f}
                                </div>
                            </div>
                        </div>
                        
                        <div style="margin: 0.8rem 0;">
                    """
                    
                    # Add badges
                    for badge in badges:
                        citation_html += f"""
                            <span style="
                                background: {colors['secondary_bg']}; 
                                color: {colors['text_secondary']}; 
                                padding: 0.2rem 0.5rem; 
                                border-radius: 10px; 
                                font-size: 0.7rem; 
                                margin-right: 0.5rem;">
                                {badge}
                            </span>
                        """
                    
                    citation_html += "</div>"
                    
                    # Add snippet with cleaning
                    if cite.get('snippet'):
                        snippet = cite['snippet']
                        
                        # Clean up snippet - remove redundant "From:" lines and email headers
                        lines = snippet.split('\n')
                        clean_lines = []
                        
                        for line in lines:
                            line = line.strip()
                            # Skip lines that start with email headers
                            if (line.startswith('From:') or 
                                line.startswith('Subject:') or 
                                line.startswith('Date:') or
                                line.startswith('To:') or
                                line.startswith('CC:') or
                                '<' in line and '>' in line and '@' in line):  # Email addresses
                                continue
                            if line:
                                clean_lines.append(line)
                        
                        snippet = ' '.join(clean_lines)
                        
                        # Truncate if too long
                        if len(snippet) > 200:
                            snippet = snippet[:200] + "..."
                        
                        if snippet.strip():  # Only show if there's actual content
                            citation_html += f"""
                                <div style="
                                    color: {colors['text_secondary']}; 
                                    font-style: italic; 
                                    line-height: 1.4;
                                    margin-top: 0.8rem;
                                    padding: 0.5rem;
                                    background: {colors['primary_bg']};
                                    border-radius: 5px;">
                                    "{snippet}"
                                </div>
                            """
                    
                    citation_html += "</div>"
                    
                    st.markdown(citation_html, unsafe_allow_html=True)

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
    
    # Theme preferences (always visible)
    theme_manager.render_ui_preferences()
    
    st.markdown("---")
    
    # Secure admin authentication
    if not auth.is_admin_authenticated():
        st.markdown("#### 🔐 Admin Authentication")
        with st.form("admin_login"):
            admin_password = st.text_input("Admin password", type="password", help="Enter your secure admin password")
            login_button = st.form_submit_button("Login")
            
            if login_button and admin_password:
                if auth.authenticate_admin(admin_password):
                    st.success("✅ Admin access granted!")
                    st.rerun()
    else:
        # Extend session on activity
        auth.extend_session()
        
        col1, col2 = st.columns([5, 1])
        with col1:
            st.success("✅ Admin mode enabled")
        with col2:
            if st.button("Logout", type="secondary"):
                auth.logout_admin()
                st.rerun()
        
        # Admin functionality
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🔄 Email Synchronization")
            
            # Import sync components
            from app.sync.live_sync import get_sync_engine
            from app.ui.sync_status import render_sync_status
            
            sync_engine = get_sync_engine()
            sync_stats = sync_engine.get_statistics()
            
            # Sync status display
            st.markdown("**📡 Live Sync Status:**")
            
            if sync_stats['is_running']:
                st.success(f"🟢 Live sync is ACTIVE - {sync_stats['current_status']}")
                st.write(f"- Connection: {sync_stats['connection_state']}")
                st.write(f"- Emails processed: {sync_stats['emails_processed']}")
                st.write(f"- Added to index: {sync_stats['emails_added']}")
                st.write(f"- Filtered out: {sync_stats['emails_filtered']}")
                if sync_stats['last_sync']:
                    st.write(f"- Last sync: {sync_stats['last_sync']}")
                
                # Stop button
                if st.button("⏹️ Stop Live Sync", use_container_width=True, type="secondary"):
                    sync_engine.stop()
                    st.info("Live sync stopped")
                    st.rerun()
            else:
                st.info("🔴 Live sync is INACTIVE")
                
                # Start live sync button
                if st.button("🚀 Activate Live Email Sync", use_container_width=True, type="primary"):
                    with st.spinner("Starting live sync..."):
                        if sync_engine.start():
                            st.success("✅ Live sync activated! New emails will be automatically synced and filtered.")
                            st.info(f"Quality threshold: {sync_engine.quality_threshold}/100")
                            st.rerun()
                        else:
                            st.error("❌ Failed to start live sync. Check your email settings.")
                            if sync_stats['errors']:
                                st.error(f"Error: {sync_stats['errors'][-1]}")
            
            st.markdown("---")
            
            # Manual sync option
            st.markdown("**🔄 Manual Sync:**")
            
            if st.button("📥 Manually Sync Latest Emails", use_container_width=True):
                with st.spinner("Checking for new emails..."):
                    try:
                        # Connect if not connected
                        if not sync_stats['is_running']:
                            if not sync_engine.connect():
                                st.error("❌ Failed to connect to email server")
                                if sync_stats['errors']:
                                    st.error(f"Error: {sync_stats['errors'][-1]}")
                                st.stop()
                        
                        # Fetch new emails
                        new_emails = sync_engine.fetch_new_emails()
                        
                        if new_emails:
                            st.info(f"Found {len(new_emails)} new emails")
                            
                            # Process with quality filtering
                            with st.spinner("Processing emails with quality filtering..."):
                                results = sync_engine.process_new_emails(new_emails)
                            
                            # Update index
                            if results['high_quality']:
                                with st.spinner("Updating search index..."):
                                    sync_engine.update_index_incremental(results['high_quality'])
                            
                            # Show results
                            st.success(f"✅ Sync complete!")
                            col_a, col_b, col_c = st.columns(3)
                            with col_a:
                                st.metric("Processed", results['processed'])
                            with col_b:
                                st.metric("Added", results['accepted'])
                            with col_c:
                                st.metric("Filtered", results['rejected'])
                            
                            # Update session state
                            st.session_state.email_count += results['accepted']
                            st.session_state.last_sync = datetime.now().strftime('%Y-%m-%d %H:%M')
                            
                            # Show sample of accepted emails
                            if results['high_quality']:
                                with st.expander(f"✅ {len(results['high_quality'])} high-quality emails added"):
                                    for email in results['high_quality'][:5]:
                                        st.write(f"• **{email['clean_subject'][:60]}** (from {email['clean_sender']})")
                                        st.caption(f"  Quality: {email['quality_score']:.1f}/100")
                            
                            # Show rejected emails
                            if results['low_quality']:
                                with st.expander(f"❌ {len(results['low_quality'])} emails filtered out"):
                                    for email in results['low_quality'][:5]:
                                        st.write(f"• {email['subject'][:60]}")
                                        st.caption(f"  Reason: {email['rejection_reason']}")
                        else:
                            st.info("📭 No new emails found")
                        
                        # Disconnect if we connected just for manual sync
                        if not sync_stats['is_running']:
                            sync_engine.imap_connection = None
                            
                    except Exception as e:
                        st.error(f"❌ Error during manual sync: {e}")
            
            st.markdown("---")
            
            # Index statistics
            st.markdown("**📊 Index Statistics:**")
            index_stats = incremental_indexer.get_index_stats()
            st.write(f"- Last updated: {index_stats['last_update'] or 'Never'}")
            st.write(f"- Total emails indexed: {index_stats['total_emails_indexed']:,}")
            st.write(f"- Total search nodes: {index_stats['total_nodes']:,}")
            st.write(f"- Index exists: {'✅' if index_stats['index_exists'] else '❌'}")
            
            # Incremental indexing
            if st.button("Update Search Index", use_container_width=True):
                with st.spinner("🔄 Updating search index..."):
                    try:
                        idx = incremental_indexer.build_incremental_index()
                        if idx:
                            st.success("✅ Search index updated successfully!")
                        else:
                            st.info("ℹ️ Index is already up to date")
                        
                        # Refresh stats
                        updated_stats = incremental_indexer.get_index_stats()
                        st.write(f"**Updated stats:** {updated_stats['total_emails_indexed']:,} emails indexed")
                        
                    except Exception as e:
                        st.error(f"❌ Error updating index: {e}")
            
            # Full rebuild option
            if st.button("🔄 Rebuild Full Index", use_container_width=True, help="Rebuild the entire search index from scratch"):
                if st.button("⚠️ Confirm Full Rebuild", type="secondary"):
                    with st.spinner("🔄 Rebuilding entire search index..."):
                        try:
                            idx = incremental_indexer.rebuild_full_index()
                            st.success("✅ Full index rebuild completed!")
                        except Exception as e:
                            st.error(f"❌ Error rebuilding index: {e}")
        
        with col2:
            st.markdown("#### ⚙️ Sync Configuration")
            
            # Quality settings for sync
            st.markdown("**Quality Filtering:**")
            
            quality_threshold = st.slider(
                "Minimum Quality Score",
                min_value=0,
                max_value=100,
                value=int(sync_engine.quality_threshold),
                help="Only sync emails with quality score above this threshold"
            )
            
            if quality_threshold != sync_engine.quality_threshold:
                sync_engine.quality_threshold = quality_threshold
                st.info(f"Quality threshold updated to {quality_threshold}/100")
            
            max_marketing = st.slider(
                "Maximum Marketing Score",
                min_value=0,
                max_value=100,
                value=int(sync_engine.max_marketing_score),
                help="Reject emails with marketing score above this"
            )
            
            if max_marketing != sync_engine.max_marketing_score:
                sync_engine.max_marketing_score = max_marketing
                st.info(f"Max marketing score updated to {max_marketing}/100")
            
            # Sync interval
            sync_interval = st.number_input(
                "Check Interval (seconds)",
                min_value=60,
                max_value=3600,
                value=sync_engine.sync_interval,
                step=60,
                help="How often to check for new emails when IDLE not supported"
            )
            
            if sync_interval != sync_engine.sync_interval:
                sync_engine.sync_interval = sync_interval
                st.info(f"Check interval updated to {sync_interval}s")
            
            st.markdown("---")
            
            st.markdown("#### 📧 Email Settings")
            st.text_input("IMAP Server", value=settings.imap_host, disabled=True)
            st.text_input("Email Account", value=settings.imap_user, disabled=True)
            st.text_input("Folder", value=settings.imap_folder, disabled=True)
            
            st.markdown("#### 🤖 AI Settings")
            st.text_input("LLM Provider", value=settings.llm_provider, disabled=True)
            if settings.llm_provider == "ollama":
                st.text_input("Model", value=settings.ollama_model, disabled=True)
            st.text_input("Embeddings", value=settings.embeddings_provider, disabled=True)
            
            st.markdown("#### 🔒 Security Status")
            
            # Check security features
            security_status = []
            
            # Check if data is encrypted
            import glob
            encrypted_files = glob.glob("data/raw/*.json.enc")
            if encrypted_files:
                security_status.append("✅ Email data encrypted")
            else:
                security_status.append("⚠️ Email data not encrypted")
            
            # Check SSL settings
            if settings.imap_ssl:
                security_status.append("✅ IMAP SSL enabled")
            else:
                security_status.append("❌ IMAP SSL disabled")
            
            for status in security_status:
                st.write(status)
    
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