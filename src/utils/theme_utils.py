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
            
        # Check if we have a saved preference in the browser's localStorage
        js = """
        try {
            const savedTheme = localStorage.getItem('theme');
            if (savedTheme === 'light' || savedTheme === 'dark') {
                window.parent.postMessage({
                    type: 'setTheme',
                    theme: savedTheme
                }, '*');
                return savedTheme;
            }
            
            // If no saved preference, use system preference
            const isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
            const theme = isDark ? 'dark' : 'light';
            window.parent.postMessage({
                type: 'setTheme',
                theme: theme
            }, '*');
            return theme;
        } catch (e) {
            console.error('Error getting theme:', e);
            return 'light';
        }
        """
        
        # This will be updated by the JavaScript callback
        result = st.components.v1.html(
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
    
    return st.session_state.theme

def set_theme(theme: Literal["light", "dark"]) -> None:
    """
    Set the theme and update the session state.
    
    Args:
        theme: 'light' or 'dark'
    """
    logger.debug(f"Setting theme to: {theme}")
    
    if theme not in ['light', 'dark']:
        logger.warning(f"Invalid theme: {theme}. Must be 'light' or 'dark'.")
        return
    
    try:
        # Update session state
        st.session_state.theme = theme
        
        # Save to URL query params
        st.query_params['theme'] = theme
        
        # Apply theme via JavaScript
        apply_theme(theme)
        
        logger.debug(f"Successfully set theme to: {theme}")
        
    except Exception as e:
        logger.error(f"Error setting theme: {e}", exc_info=True)
        # Try to apply the theme anyway, as the error might be with logging
        apply_theme(theme)

def apply_theme(theme: str) -> None:
    """
    Apply the theme by injecting CSS variables and updating the HTML data-theme attribute.
    
    Args:
        theme: 'light' or 'dark'
    """
    logger.debug(f"Applying theme: {theme}")
    
    try:
        # Create a simple JavaScript function to apply the theme
        # Using string concatenation to avoid formatting issues
        js = """
        <script>
        (function() {
            try {
                // Set the theme attribute on the HTML element
                const theme = '""" + theme + """';
                const html = document.documentElement;
                html.setAttribute('data-theme', theme);
                
                // Save preference to localStorage
                try {
                    localStorage.setItem('theme', theme);
                } catch (e) {
                    console.warn('Could not save theme preference to localStorage:', e);
                }
                
                // Update any existing Streamlit components
                if (window.parent && window.parent.document) {
                    // Update the root element
                    const root = window.parent.document.documentElement;
                    if (root) {
                        root.setAttribute('data-theme', theme);
                    }
                    
                    // Update all iframes if possible
                    const iframes = window.parent.document.querySelectorAll('iframe');
                    iframes.forEach(iframe => {
                        try {
                            if (iframe.contentDocument && iframe.contentDocument.documentElement) {
                                iframe.contentDocument.documentElement.setAttribute('data-theme', theme);
                            }
                        } catch (e) {
                            // Cross-origin iframe, can't access contentDocument
                            console.log('Could not set theme on iframe:', e);
                        }
                    });
                }
                
                console.log('Theme applied:', theme);
            } catch (e) {
                console.error('Error applying theme:', e);
            }
        })();
        </script>
        """
        
        # Inject the JavaScript to apply the theme
        st.components.v1.html(
            js, 
            height=0, 
            width=0
        )
        
        logger.debug(f"Successfully applied theme: {theme}")
        
    except Exception as e:
        logger.error(f"Error applying theme {theme}: {e}", exc_info=True)

def init_theme() -> None:
    """
    Initialize the theme by applying the current theme from session state.
    This should be called at the start of the app.
    """
    logger.debug("Initializing theme")
    try:
        theme = get_theme()
        logger.debug(f"Initial theme: {theme}")
        apply_theme(theme)
        
        # Add a message handler for theme changes from the client
        js = """
        <script>
        // Listen for theme change messages from the client
        window.addEventListener('message', function(event) {
            if (event.data && event.data.type === 'setTheme') {
                const html = document.documentElement;
                html.setAttribute('data-theme', event.data.theme);
                
                // Update any iframes
                document.querySelectorAll('iframe').forEach(iframe => {
                    try {
                        if (iframe.contentWindow) {
                            iframe.contentWindow.postMessage({
                                type: 'setTheme',
                                theme: event.data.theme
                            }, '*');
                        }
                    } catch (e) {
                        console.warn('Could not update iframe theme:', e);
                    }
                });
                
                console.log('Theme updated via message:', event.data.theme);
            }
        });
        </script>
        """
        st.components.v1.html(js, height=0, width=0)
        
        logger.debug("Theme initialization complete")
        
    except Exception as e:
        logger.error(f"Error initializing theme: {e}", exc_info=True)
        # Try to apply light theme as fallback
        apply_theme('light')

def render_theme_toggle() -> None:
    """
    Render a theme toggle button in the sidebar.
    """
    try:
        logger.debug("Rendering theme toggle")
        current_theme = get_theme()
        
        # Toggle button with appropriate icon
        button_text = f"{'☀️ Light' if current_theme == 'dark' else '🌙 Dark'} Mode"
        button_help = f"Switch to {'light' if current_theme == 'dark' else 'dark'} theme"
        
        # Use columns to center the button
        col1, col2, col3 = st.sidebar.columns([1, 2, 1])
        
        with col2:
            if st.button(
                button_text,
                key="theme_toggle",
                help=button_help,
                use_container_width=True,
                type="secondary"  # Ensure consistent button styling
            ):
                new_theme = 'dark' if current_theme == 'light' else 'light'
                logger.debug(f"Toggling theme from {current_theme} to {new_theme}")
                set_theme(new_theme)
                # Force a rerun to ensure all components update
                st.rerun()
                
        # Enhanced button styles with proper z-index and pointer-events
        st.sidebar.markdown("""
        <style>
        /* Specific selector for theme toggle button */
        div[data-testid="stButton"] > button[kind="secondary"] {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 8px;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            transition: all 0.3s ease;
            position: relative;
            z-index: 1002;  /* Higher than other elements */
            pointer-events: auto !important;
            background-color: var(--secondary-background-color, #f0f2f6);
            color: var(--text-color, #1a1a1a);
            border: 1px solid var(--border-color, #d3d3d3);
        }
        
        /* Hover state */
        div[data-testid="stButton"] > button[kind="secondary"]:hover {
            background-color: var(--hover-color, #e0e0e0);
            transform: translateY(-1px);
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        /* Active state */
        div[data-testid="stButton"] > button[kind="secondary"]:active {
            transform: translateY(0);
            box-shadow: none;
        }
        
        /* Ensure button is clickable */
        div[data-testid="stButton"] {
            position: relative;
            z-index: 1001;
            pointer-events: auto !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        logger.debug("Theme toggle rendered")
        
    except Exception as e:
        logger.error(f"Error rendering theme toggle: {e}", exc_info=True)
        # If there's an error, don't show the toggle to avoid breaking the UI
        pass
