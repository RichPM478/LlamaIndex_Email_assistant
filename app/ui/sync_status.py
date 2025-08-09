# app/ui/sync_status.py
"""
Sync Status UI Component - Phase 3B
Real-time sync status display for Streamlit
"""

import streamlit as st
from datetime import datetime, timedelta
import time

def render_sync_status():
    """Render live sync status in the UI"""
    from app.sync.live_sync import get_sync_engine
    
    sync_engine = get_sync_engine()
    stats = sync_engine.get_statistics()
    
    # Status indicator
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if stats['is_running']:
            st.success("🔄 Live Sync Active")
        else:
            st.info("⏸️ Sync Paused")
    
    with col2:
        st.metric("Connection", stats['connection_state'])
    
    with col3:
        if stats['last_sync']:
            last_sync_time = datetime.fromisoformat(stats['last_sync'])
            time_ago = datetime.now() - last_sync_time
            
            if time_ago < timedelta(minutes=1):
                st.metric("Last Sync", "Just now")
            elif time_ago < timedelta(hours=1):
                st.metric("Last Sync", f"{int(time_ago.total_seconds() / 60)} min ago")
            else:
                st.metric("Last Sync", f"{int(time_ago.total_seconds() / 3600)} hours ago")
        else:
            st.metric("Last Sync", "Never")
    
    # Statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Emails Processed", stats['emails_processed'])
    
    with col2:
        st.metric("Added to Index", stats['emails_added'])
    
    with col3:
        st.metric("Filtered Out", stats['emails_filtered'])
    
    with col4:
        acceptance_rate = (stats['emails_added'] / max(1, stats['emails_processed'])) * 100 if stats['emails_processed'] > 0 else 0
        st.metric("Quality Rate", f"{acceptance_rate:.1f}%")
    
    # Current status
    st.caption(f"Status: {stats['current_status']}")
    
    # Errors
    if stats['errors']:
        with st.expander("⚠️ Recent Issues", expanded=False):
            for error in stats['errors']:
                st.warning(error)
    
    # Control buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if not stats['is_running']:
            if st.button("▶️ Start Sync", use_container_width=True):
                if sync_engine.start():
                    st.success("Live sync started!")
                    st.rerun()
                else:
                    st.error("Failed to start sync. Check settings.")
        else:
            if st.button("⏸️ Pause Sync", use_container_width=True):
                sync_engine.stop()
                st.info("Sync paused")
                st.rerun()
    
    with col2:
        if st.button("🔄 Check Now", use_container_width=True):
            with st.spinner("Checking for new emails..."):
                # Force immediate check
                if not stats['is_running']:
                    # Start temporarily for one check
                    if sync_engine.connect():
                        new_emails = sync_engine.fetch_new_emails()
                        if new_emails:
                            results = sync_engine.process_new_emails(new_emails)
                            sync_engine.update_index_incremental(results['high_quality'])
                            st.success(f"Processed {results['processed']} emails, added {results['accepted']}")
                        else:
                            st.info("No new emails")
                    else:
                        st.error("Connection failed")
                else:
                    st.info("Sync is already running - checking continuously")
    
    with col3:
        if st.button("📊 View Details", use_container_width=True):
            st.session_state.show_sync_details = not st.session_state.get('show_sync_details', False)
            st.rerun()
    
    # Detailed view
    if st.session_state.get('show_sync_details', False):
        st.markdown("### 📊 Sync Details")
        
        # Settings
        st.markdown("**Current Settings:**")
        st.write(f"- Quality threshold: {sync_engine.quality_threshold}/100")
        st.write(f"- Max marketing score: {sync_engine.max_marketing_score}/100")
        st.write(f"- Check interval: {sync_engine.sync_interval}s")
        
        # Statistics
        st.markdown("**Lifetime Statistics:**")
        st.write(f"- Total emails synced: {stats['total_synced_all_time']}")
        st.write(f"- Current session processed: {stats['emails_processed']}")
        st.write(f"- Current session added: {stats['emails_added']}")
        st.write(f"- Current session filtered: {stats['emails_filtered']}")
        
        # Connection info
        if stats['last_check']:
            st.write(f"- Last check: {stats['last_check']}")

def render_sync_controls():
    """Render sync configuration controls"""
    st.markdown("### ⚙️ Sync Configuration")
    
    from app.sync.live_sync import get_sync_engine
    sync_engine = get_sync_engine()
    
    # Quality settings
    col1, col2 = st.columns(2)
    
    with col1:
        quality_threshold = st.slider(
            "Quality Threshold",
            min_value=0,
            max_value=100,
            value=int(sync_engine.quality_threshold),
            help="Minimum quality score to include emails"
        )
        
        if quality_threshold != sync_engine.quality_threshold:
            sync_engine.quality_threshold = quality_threshold
            st.info(f"Quality threshold updated to {quality_threshold}")
    
    with col2:
        max_marketing = st.slider(
            "Max Marketing Score",
            min_value=0,
            max_value=100,
            value=int(sync_engine.max_marketing_score),
            help="Maximum marketing score to allow"
        )
        
        if max_marketing != sync_engine.max_marketing_score:
            sync_engine.max_marketing_score = max_marketing
            st.info(f"Max marketing score updated to {max_marketing}")
    
    # Sync interval
    sync_interval = st.number_input(
        "Check Interval (seconds)",
        min_value=60,
        max_value=3600,
        value=sync_engine.sync_interval,
        step=60,
        help="How often to check for new emails (if IDLE not supported)"
    )
    
    if sync_interval != sync_engine.sync_interval:
        sync_engine.sync_interval = sync_interval
        st.info(f"Check interval updated to {sync_interval}s")
    
    # Clear sync state
    if st.button("🗑️ Reset Sync State", help="Clear all sync tracking data"):
        import os
        if os.path.exists(sync_engine.state_file):
            os.remove(sync_engine.state_file)
            sync_engine.sync_state = sync_engine._load_sync_state()
            st.success("Sync state reset. Next sync will process recent emails.")

def auto_refresh_status():
    """Auto-refresh sync status every 30 seconds"""
    # Add auto-refresh JavaScript
    st.markdown("""
    <script>
    // Auto-refresh every 30 seconds if sync is running
    setTimeout(function() {
        const syncActive = document.querySelector('.stSuccess')?.textContent?.includes('Live Sync Active');
        if (syncActive) {
            window.location.reload();
        }
    }, 30000);
    </script>
    """, unsafe_allow_html=True)