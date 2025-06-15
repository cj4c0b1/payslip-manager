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
    
    Args:
        theme: 'light' or 'dark'
        
    Returns:
        bool: True if theme was set successfully, False otherwise
    """
    try:
        logger.debug(f"Attempting to set theme to: {theme}")
        theme_changed = False
        
        # First try the new Streamlit theming API (v1.16.0+)
        try:
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
            logger.debug("Theme set using _config.set_option")
            theme_changed = True
        except Exception as e:
            logger.warning(f"Could not use _config.set_option: {e}")
            # Fall back to direct dictionary access
            try:
                config = st.get_option('theme')
                if theme == 'dark':
                    config.update({
                        'base': 'dark',
                        'backgroundColor': '#1a1a1a',
                        'primaryColor': '#6eb52f',
                        'secondaryBackgroundColor': '#2d2d2d',
                        'textColor': '#ffffff'
                    })
                else:
                    config.update({
                        'base': 'light',
                        'backgroundColor': '#ffffff',
                        'primaryColor': '#4a86e8',
                        'secondaryBackgroundColor': '#f0f2f6',
                        'textColor': '#1a1a1a'
                    })
                st.set_option('theme', config)
                logger.debug("Theme set using st.set_option")
                theme_changed = True
            except Exception as e:
                logger.error(f"Could not set theme using st.set_option: {e}")
                # Continue to fallback theming
        
        # Store in session state
        st.session_state.theme = theme
        logger.debug(f"Theme preference set to: {theme}")
        
        # Only apply fallback if native theming failed
        if not theme_changed:
            logger.warning("Falling back to CSS-based theming")
            _fallback_theme(theme)
            
        return theme_changed
        
    except Exception as e:
        logger.error(f"Error setting theme: {e}", exc_info=True)
        # Fallback to CSS-based theming if native theming fails
        _fallback_theme(theme)
        return False

def _fallback_theme(theme: str) -> None:
    """Fallback CSS-based theming if native theming fails."""
    try:
        st.markdown(
            f"""
            <style>
            .stApp {{
                background-color: {'#1a1a1a' if theme == 'dark' else '#ffffff'};
                color: {'#ffffff' if theme == 'dark' else '#1a1a1a'};
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
        
        # Create a container for the button to isolate it
        with st.sidebar.container():
            # Add some top margin
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            
            # Create a single column for the button
            _, col, _ = st.columns([1, 2, 1])
            
            with col:
                # Add custom CSS to prevent hover effects
                st.markdown(
                    """
                    <style>
                        .stButton>button {
                            width: 100%;
                            transition: none !important;
                        }
                        .stButton>button:hover {
                            transform: none !important;
                            box-shadow: none !important;
                        }
                    </style>
                    """,
                    unsafe_allow_html=True
                )
                
                # Button to toggle theme
                button_text = f"{'☀️ Light Mode' if current_theme == 'dark' else '🌙 Dark Mode'}"
                if st.button(button_text, key='theme_toggle_button', use_container_width=True):
                    # Toggle the theme
                    new_theme = 'dark' if current_theme == 'light' else 'light'
                    # Update theme in session state and apply it
                    st.session_state.theme = new_theme
                    set_theme(new_theme)
                    # Force a rerun to apply the theme
                    st.rerun()
                            
    except Exception as e:
        logger.error(f"Error in theme toggle: {e}", exc_info=True)
        # Ensure theme is set in session state on error
        st.session_state.setdefault('theme', 'light')

def init_theme() -> None:
    """
    Initialize the theme when the app starts.
    This should be called at the beginning of the app.
    """
    if 'theme' not in st.session_state:
        # Default to light theme on first run
        set_theme('light')
    else:
        # Apply the stored theme
        set_theme(st.session_state.theme)
