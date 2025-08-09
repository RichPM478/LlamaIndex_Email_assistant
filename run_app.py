#!/usr/bin/env python3
"""
Email Assistant Launcher
Choose which interface to run
"""

import sys
import subprocess

def main():
    print("\n" + "="*60)
    print("📧 EMAIL ASSISTANT - Choose Interface")
    print("="*60)
    print("\n1. Chat Interface (NEW - WhatsApp-style, modern)")
    print("2. Dashboard Interface (Original - with analytics)")
    print("3. Exit")
    
    choice = input("\nSelect interface (1-3): ").strip()
    
    if choice == "1":
        print("\n🚀 Launching Chat Interface...")
        print("Opening in browser: http://localhost:8501")
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app/ui/chat_interface.py"])
        
    elif choice == "2":
        print("\n🚀 Launching Dashboard Interface...")
        print("Opening in browser: http://localhost:8501")
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app/ui/streamlit_app.py"])
        
    elif choice == "3":
        print("\nGoodbye! 👋")
        sys.exit(0)
        
    else:
        print("\n❌ Invalid choice. Please try again.")
        main()

if __name__ == "__main__":
    main()