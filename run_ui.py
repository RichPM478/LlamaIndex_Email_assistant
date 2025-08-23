"""
Main entry point for the Email Intelligence System UI
Uses the new modular architecture with Gemini 2.5 support
"""
import sys
import os
import signal
import socket
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent))

# Set environment encoding for Windows
os.environ['PYTHONIOENCODING'] = 'utf-8'

def find_free_port(start_port=8502, max_attempts=10):
    """Find a free port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"No free ports found in range {start_port}-{start_port + max_attempts}")

def signal_handler(signum, frame):
    """Handle interrupt signals for graceful shutdown"""
    print("\n[SHUTDOWN] Received interrupt signal, shutting down gracefully...")
    sys.exit(0)

def main():
    """Run the Streamlit UI with new architecture and evaluation dashboard"""
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        import streamlit.web.cli as stcli
        
        # Find a free port
        port = find_free_port()
        print(f"Using port: {port}")
        
        # Use the integrated UI with chat + evaluation dashboard
        ui_script = str(Path(__file__).parent / "app" / "ui" / "main_interface.py")
        
        # Run Streamlit with better configuration
        sys.argv = ["streamlit", "run", ui_script, 
                    "--server.port", str(port),
                    "--server.headless", "true",
                    "--browser.gatherUsageStats", "false",
                    "--server.enableCORS", "false",
                    "--server.enableXsrfProtection", "false"]
        
        # Run with proper exit handling
        stcli.main()
        
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Interrupted by user")
    except Exception as e:
        print(f"[ERROR] Failed to start UI: {e}")
        sys.exit(1)
    finally:
        print("[SHUTDOWN] UI shutdown complete")

if __name__ == "__main__":
    print("Starting Email Intelligence System v2.0...")
    print("Using new modular architecture with Gemini 2.5")
    print("-" * 50)
    main()