"""
Theme utilities for managing light/dark mode in the Streamlit app.
"""
import os
import streamlit as st
from typing import Literal, Optional, Dict, Any
import logging
import json

# Configure logger
logger = logging.getLogger(__name__)

def setup_logging():
    """Ensure logging is configured."""
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        # Create logs directory if it doesn't exist
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # Create file handler which logs debug messages
        log_file = os.path.join(log_dir, 'theme_utils.log')
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.DEBUG)
        
        # Create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(logging.WARNING)
        
        # Create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        # Add the handlers to the logger
        logger.addHandler(fh)
        logger.addHandler(ch)
        
        logger.debug("Theme utilities logging configured")

# Initialize logging
setup_logging()



def get_theme() -> Literal["light", "dark"]:
    """
    Get the current theme from session state or browser's localStorage.
    Defaults to system preference if not set.
    
    Returns:
        str: 'light' or 'dark'
    """
    logger.debug("Getting current theme")
    
    try:
        # First check if we have a theme in session state
        if 'theme' in st.session_state and st.session_state.theme in ['light', 'dark']:
            logger.debug(f"Found theme in session state: {st.session_state.theme}")
            return st.session_state.theme
            
        # Check URL parameters
        if 'theme' in st.query_params and st.query_params['theme'] in ['light', 'dark']:
            theme = st.query_params['theme']
            st.session_state.theme = theme
            logger.debug(f"Found theme in URL params: {theme}")
            return theme
            
        js = """
        (function() {
            try {
                // Check localStorage first
                const savedTheme = localStorage.getItem('theme');
                if (savedTheme) return savedTheme;
                
                // Fall back to system preference
                const isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
                return isDark ? 'dark' : 'light';
            } catch (e) {
                console.error('Error getting theme:', e);
                return 'light';
            }
        })();
        """
        
        # This will be updated by the JavaScript callback
        st.components.v1.html(
            f"<script>{js}</script>",
            height=0,
            width=0,
            key="theme_script"
        )
        
        # Default to light theme if we can't determine the system preference
        return 'light'
        
    except Exception as e:
        logger.error(f"Error getting theme: {e}", exc_info=True)
        return 'light'  # Default fallback

def set_theme(theme: Literal["light", "dark"]) -> bool:
    """
    Set the theme using Streamlit's native theming.
    
    This implementation uses a more reliable approach by directly modifying the theme config
    and using st._config.set_option for better compatibility.
    
    Args:
        theme: 'light' or 'dark'
        
    Returns:
        bool: True if theme was set successfully, False otherwise
    """
    try:
        logger.debug(f"Attempting to set theme to: {theme}")
        import streamlit as st
        
        # Store in session state first to ensure it's available immediately
        st.session_state.theme = theme
        
        # Save to browser's localStorage for persistence
        js = f"""
        <script>
        try {{
            localStorage.setItem('theme', '{theme}');
            document.documentElement.setAttribute('data-theme', '{theme}');
            console.log('Theme set to: {theme}');
        }} catch (e) {{
            console.error('Error setting theme in localStorage:', e);
        }}
        </script>
        """
        st.components.v1.html(js, height=0, width=0)
        
        # Apply theme using Streamlit's internal _config
        try:
            import streamlit as st
            from streamlit import _config
            
            if theme == 'dark':
                _config.set_option('theme.base', 'dark')
                _config.set_option('theme.backgroundColor', '#1a1a1a')
                _config.set_option('theme.primaryColor', '#6eb52f')
                _config.set_option('theme.secondaryBackgroundColor', '#2d2d2d')
                _config.set_option('theme.textColor', '#ffffff')
            else:
                _config.set_option('theme.base', 'light')
                _config.set_option('theme.backgroundColor', '#ffffff')
                _config.set_option('theme.primaryColor', '#4a86e8')
                _config.set_option('theme.secondaryBackgroundColor', '#f0f2f6')
                _config.set_option('theme.textColor', '#1a1a1a')
                
            logger.debug(f"Theme set using _config.set_option: {theme}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting theme with _config: {e}")
            _fallback_theme(theme)
            return False
            
    except Exception as e:
        logger.error(f"Error in set_theme: {e}", exc_info=True)
        _fallback_theme(theme)
        return False
        return False

def _fallback_theme(theme: str) -> None:
    """Fallback CSS-based theming if native theming fails."""
    try:
        import streamlit as st
        
        # Set data-theme attribute on html element for CSS theming
        st.markdown(
            f"""
            <script>
            document.documentElement.setAttribute('data-theme', '{theme}');
            </script>
            """,
            unsafe_allow_html=True
        )
        
        # Apply fallback CSS theming
        st.markdown(
            f"""
            <style>
            :root {{
                --primary: {'#6eb52f' if theme == 'dark' else '#4a86e8'};
                --background: {'#1a1a1a' if theme == 'dark' else '#ffffff'};
                --secondary-background: {'#2d2d2d' if theme == 'dark' else '#f0f2f6'};
                --text: {'#ffffff' if theme == 'dark' else '#1a1a1a'};
            }}
            
            .stApp, .stApp > div[data-testid="stAppViewContainer"] {{
                background-color: var(--background);
                color: var(--text);
            }}
            
            .stTextInput > div > div > input,
            .stSelectbox > div > div > div,
            .stTextArea > div > div > textarea {{
                background-color: var(--secondary-background);
                color: var(--text);
                border-color: var(--primary);
            }}
            
            .stButton > button {{
                background-color: var(--primary);
                color: {'#000000' if theme == 'dark' else '#ffffff'};
                border: 1px solid var(--primary);
            }}
            
            .stButton > button:hover {{
                opacity: 0.9;
                border-color: var(--primary) !important;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )
    except Exception as e:
        logger.error(f"Fallback theming failed: {e}", exc_info=True)

def render_theme_toggle() -> None:
    """
    Render a theme toggle button in the sidebar.
    This version uses a more reliable approach to theme switching.
    """
    try:
        # Ensure theme is in session state
        if 'theme' not in st.session_state:
            st.session_state.theme = 'light'
            
        current_theme = st.session_state.theme
        
        # Add custom CSS for the toggle button
        st.markdown(
            """
            <style>
                .theme-toggle {
                    display: flex;
                    justify-content: center;
                    margin: 10px 0;
                }
                .theme-toggle button {
                    background: none;
                    border: 1px solid var(--primary-color, #4a86e8);
                    color: var(--text-color, #1a1a1a);
                    padding: 8px 16px;
                    border-radius: 4px;
                    cursor: pointer;
                    transition: none !important;
                    width: 100%;
                }
                .theme-toggle button:hover {
                    opacity: 0.9;
                    transform: none !important;
                    box-shadow: none !important;
                }
                [data-theme="dark"] .theme-toggle button {
                    border-color: var(--primary-color, #6eb52f);
                    color: var(--text-color, #ffffff);
                }
            </style>
            """,
            unsafe_allow_html=True
        )
        
        # Create the toggle button with a form to prevent rerun issues
        with st.sidebar.form("theme_toggle_form"):
            # Button to toggle theme
            button_text = f"{'☀️ Light Mode' if current_theme == 'dark' else '🌙 Dark Mode'}"
            
            # Use a form submit button for better reliability
            if st.form_submit_button(
                button_text,
                use_container_width=True
            ):
                # Toggle the theme
                new_theme = 'dark' if current_theme == 'light' else 'light'
                # Update theme in session state and apply it
                set_theme(new_theme)
                # Force a rerun to apply the theme
                st.rerun()
                
    except Exception as e:
        logger.error(f"Error in theme toggle: {e}", exc_info=True)
        # Ensure theme is set in session state on error
        if 'theme' not in st.session_state:
            st.session_state.theme = 'light'
        st.session_state.setdefault('theme', 'light')

def init_theme() -> None:
    """
    Initialize the theme when the app starts.
    This should be called at the beginning of the app.
    """
    try:
        # Initialize theme from session state or browser storage
        if 'theme' not in st.session_state:
            # Try to get theme from URL parameters first
            if 'theme' in st.query_params and st.query_params['theme'] in ['light', 'dark']:
                st.session_state.theme = st.query_params['theme']
            else:
                # Default to light theme if not specified
                st.session_state.theme = 'light'
        
        # Apply the theme
        set_theme(st.session_state.theme)
        
        # Add a script to handle theme changes from other tabs/windows
        st.components.v1.html("""
        <script>
        // Listen for storage events to sync theme across tabs
        window.addEventListener('storage', function(event) {
            if (event.key === 'theme') {
                document.documentElement.setAttribute('data-theme', event.newValue);
            }
        });
        
        // Set initial theme attribute
        document.documentElement.setAttribute('data-theme', '""" + st.session_state.theme + """');
        </script>
        """, height=0, width=0)
        
    except Exception as e:
        logger.error(f"Error initializing theme: {e}", exc_info=True)
        # Ensure theme is set in session state on error
        st.session_state.theme = 'light'
        _fallback_theme('light')
