# app/ui/theme_manager.py
import streamlit as st
from typing import Dict, Any

class ThemeManager:
    """Manage dark/light theme and UI preferences"""
    
    def __init__(self):
        # Initialize session state for theme
        if 'theme_mode' not in st.session_state:
            st.session_state.theme_mode = 'light'  # default to light mode
        
        if 'ui_preferences' not in st.session_state:
            st.session_state.ui_preferences = {
                'compact_view': False,
                'show_confidence': True,
                'auto_scroll': True,
                'keyboard_shortcuts': True
            }
    
    def get_theme_colors(self) -> Dict[str, str]:
        """Get color scheme for current theme"""
        if st.session_state.theme_mode == 'dark':
            return {
                'primary_bg': '#0E1117',
                'secondary_bg': '#262730',
                'accent_bg': '#1F1F2E',
                'text_primary': '#FAFAFA',
                'text_secondary': '#B8B8B8',
                'accent_color': '#6366F1',
                'success_color': '#10B981',
                'warning_color': '#F59E0B',
                'error_color': '#EF4444',
                'border_color': '#404040',
                'card_bg': '#1A1A2E',
                'input_bg': '#262730',
                'shadow': '0 4px 6px rgba(0, 0, 0, 0.3)'
            }
        else:
            return {
                'primary_bg': '#FFFFFF',
                'secondary_bg': '#F3F2EF',
                'accent_bg': '#F8F9FA',
                'text_primary': '#191919',
                'text_secondary': '#5A5A5A',
                'accent_color': '#4A90E2',
                'success_color': '#48BB78',
                'warning_color': '#ED8936',
                'error_color': '#E53E3E',
                'border_color': '#E2E8F0',
                'card_bg': '#FFFFFF',
                'input_bg': '#FFFFFF',
                'shadow': '0 2px 4px rgba(0, 0, 0, 0.1)'
            }
    
    def get_css_theme(self) -> str:
        """Generate CSS for current theme"""
        colors = self.get_theme_colors()
        
        return f"""
        <style>
            /* Theme Variables */
            :root {{
                --primary-bg: {colors['primary_bg']};
                --secondary-bg: {colors['secondary_bg']};
                --accent-bg: {colors['accent_bg']};
                --text-primary: {colors['text_primary']};
                --text-secondary: {colors['text_secondary']};
                --accent-color: {colors['accent_color']};
                --success-color: {colors['success_color']};
                --warning-color: {colors['warning_color']};
                --error-color: {colors['error_color']};
                --border-color: {colors['border_color']};
                --card-bg: {colors['card_bg']};
                --input-bg: {colors['input_bg']};
                --shadow: {colors['shadow']};
            }}
            
            /* Main App Background */
            .stApp {{
                background-color: var(--primary-bg);
                color: var(--text-primary);
            }}
            
            /* Sidebar */
            .css-1d391kg {{
                background-color: var(--secondary-bg);
            }}
            
            /* Headers */
            h1, h2, h3, h4, h5, h6 {{
                color: var(--text-primary);
                font-weight: 600;
            }}
            
            h1 {{
                border-bottom: 3px solid var(--accent-color);
                padding-bottom: 10px;
                margin-bottom: 30px;
            }}
            
            /* Input Fields */
            .stTextInput > div > div > input {{
                background-color: var(--input-bg);
                color: var(--text-primary);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 12px;
                font-size: 16px;
            }}
            
            .stTextInput > div > div > input:focus {{
                border-color: var(--accent-color);
                box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
            }}
            
            /* Buttons */
            .stButton > button {{
                background: linear-gradient(135deg, var(--accent-color) 0%, #5B6BCF 100%);
                color: white;
                border-radius: 8px;
                padding: 0.6rem 2rem;
                font-weight: 500;
                border: none;
                transition: all 0.3s ease;
                box-shadow: var(--shadow);
            }}
            
            .stButton > button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 12px rgba(0,0,0,0.2);
            }}
            
            /* Cards and Containers */
            .element-container {{
                background-color: var(--card-bg);
                border-radius: 10px;
                padding: 1rem;
                margin: 0.5rem 0;
                box-shadow: var(--shadow);
                border: 1px solid var(--border-color);
            }}
            
            /* Metrics */
            .metric-card {{
                background: var(--card-bg);
                padding: 1.5rem;
                border-radius: 12px;
                box-shadow: var(--shadow);
                text-align: center;
                border: 1px solid var(--border-color);
                transition: transform 0.2s ease;
            }}
            
            .metric-card:hover {{
                transform: translateY(-2px);
            }}
            
            /* Citations */
            .citation-card {{
                background: var(--accent-bg);
                border-left: 4px solid var(--accent-color);
                padding: 1rem;
                margin: 1rem 0;
                border-radius: 0 8px 8px 0;
                transition: all 0.3s ease;
                border: 1px solid var(--border-color);
            }}
            
            .citation-card:hover {{
                background: var(--secondary-bg);
                transform: translateX(5px);
            }}
            
            /* Tabs */
            .stTabs [data-baseweb="tab-list"] {{
                gap: 8px;
                background-color: var(--secondary-bg);
                padding: 0.5rem;
                border-radius: 10px;
            }}
            
            .stTabs [data-baseweb="tab"] {{
                height: 50px;
                padding: 0 20px;
                background-color: var(--card-bg);
                border-radius: 8px;
                color: var(--text-secondary);
                transition: all 0.3s ease;
            }}
            
            .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{
                background: var(--accent-color);
                color: white !important;
                box-shadow: var(--shadow);
            }}
            
            /* Search Results */
            .search-result {{
                background: var(--card-bg);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 1rem;
                margin: 0.5rem 0;
                transition: all 0.3s ease;
            }}
            
            .search-result:hover {{
                border-color: var(--accent-color);
                box-shadow: var(--shadow);
            }}
            
            /* Success/Warning/Error Messages */
            .stSuccess {{
                background-color: rgba(16, 185, 129, 0.1);
                border-left: 4px solid var(--success-color);
                color: var(--text-primary);
            }}
            
            .stWarning {{
                background-color: rgba(245, 158, 11, 0.1);
                border-left: 4px solid var(--warning-color);
                color: var(--text-primary);
            }}
            
            .stError {{
                background-color: rgba(239, 68, 68, 0.1);
                border-left: 4px solid var(--error-color);
                color: var(--text-primary);
            }}
            
            /* Hide Streamlit branding */
            #MainMenu {{visibility: hidden;}}
            footer {{visibility: hidden;}}
            header {{visibility: hidden;}}
            
            /* Custom scrollbar */
            ::-webkit-scrollbar {{
                width: 8px;
            }}
            
            ::-webkit-scrollbar-track {{
                background: var(--secondary-bg);
            }}
            
            ::-webkit-scrollbar-thumb {{
                background: var(--accent-color);
                border-radius: 4px;
            }}
            
            /* Responsive Design */
            @media (max-width: 768px) {{
                .stButton > button {{
                    width: 100%;
                    margin: 0.2rem 0;
                }}
                
                .metric-card {{
                    padding: 1rem;
                }}
                
                h1 {{
                    font-size: 1.5rem;
                }}
                
                .citation-card {{
                    padding: 0.8rem;
                }}
            }}
            
            /* Dark mode specific adjustments */
            {self._get_dark_mode_adjustments() if st.session_state.theme_mode == 'dark' else ''}
            
            /* Accessibility improvements */
            button:focus, input:focus {{
                outline: 2px solid var(--accent-color);
                outline-offset: 2px;
            }}
            
            /* Animation for theme transitions */
            * {{
                transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease;
            }}
        </style>
        """
    
    def _get_dark_mode_adjustments(self) -> str:
        """Additional CSS adjustments for dark mode"""
        return """
            /* Dark mode specific styles */
            .stMarkdown {{
                color: var(--text-primary);
            }}
            
            .stSelectbox > div > div {{
                background-color: var(--input-bg);
                color: var(--text-primary);
            }}
            
            .stDateInput > div > div > input {{
                background-color: var(--input-bg);
                color: var(--text-primary);
            }}
            
            /* Chart adjustments for dark mode */
            .js-plotly-plot .plotly .modebar {{
                background-color: var(--secondary-bg);
            }}
        """
    
    def render_theme_toggle(self):
        """Render theme toggle button"""
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col2:
            current_icon = "🌙" if st.session_state.theme_mode == "light" else "☀️"
            new_theme = "dark" if st.session_state.theme_mode == "light" else "light"
            
            if st.button(f"{current_icon} Switch to {new_theme.title()} Mode", 
                        use_container_width=True,
                        help=f"Switch to {new_theme} theme"):
                st.session_state.theme_mode = new_theme
                st.rerun()
    
    def render_ui_preferences(self):
        """Render UI preference controls"""
        st.subheader("🎨 Display Preferences")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.session_state.ui_preferences['compact_view'] = st.checkbox(
                "Compact View", 
                value=st.session_state.ui_preferences['compact_view'],
                help="Show more items in less space"
            )
            
            st.session_state.ui_preferences['show_confidence'] = st.checkbox(
                "Show Confidence Scores", 
                value=st.session_state.ui_preferences['show_confidence'],
                help="Display AI confidence levels"
            )
        
        with col2:
            st.session_state.ui_preferences['auto_scroll'] = st.checkbox(
                "Auto-scroll Results", 
                value=st.session_state.ui_preferences['auto_scroll'],
                help="Automatically scroll to new results"
            )
            
            st.session_state.ui_preferences['keyboard_shortcuts'] = st.checkbox(
                "Enable Keyboard Shortcuts", 
                value=st.session_state.ui_preferences['keyboard_shortcuts'],
                help="Enable keyboard navigation (Ctrl+K for search)"
            )
    
    def get_keyboard_shortcuts_js(self) -> str:
        """Generate JavaScript for keyboard shortcuts"""
        if not st.session_state.ui_preferences.get('keyboard_shortcuts', True):
            return ""
        
        return """
        <script>
        document.addEventListener('keydown', function(event) {
            // Ctrl+K or Cmd+K for search
            if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
                event.preventDefault();
                const searchInput = document.querySelector('input[placeholder*="Ask anything"]');
                if (searchInput) {
                    searchInput.focus();
                }
            }
            
            // Escape to clear search
            if (event.key === 'Escape') {
                const searchInput = document.querySelector('input[placeholder*="Ask anything"]');
                if (searchInput && searchInput === document.activeElement) {
                    searchInput.value = '';
                    searchInput.blur();
                }
            }
            
            // Ctrl+Enter or Cmd+Enter to submit search
            if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
                const searchButton = document.querySelector('button[kind="primary"]');
                if (searchButton) {
                    searchButton.click();
                }
            }
        });
        </script>
        """

# Global theme manager instance
theme_manager = ThemeManager()