#!/usr/bin/env python3
"""
Email Assistant - WhatsApp Style Chat Interface
"""

import sys
import subprocess

def main():
    print("\n" + "="*60)
    print("EMAIL ASSISTANT - WhatsApp Style Interface")
    print("="*60)
    print("\nLaunching Chat Interface...")
    print("Opening in browser: http://localhost:8501")
    subprocess.run([sys.executable, "-m", "streamlit", "run", "app/ui/chat_interface.py"])

if __name__ == "__main__":
    main()