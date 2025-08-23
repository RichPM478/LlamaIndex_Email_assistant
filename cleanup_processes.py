#!/usr/bin/env python3
"""
Utility script to clean up hanging Email Intelligence System processes
"""
import subprocess
import sys
import re

def run_command(cmd):
    """Run a system command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

def find_python_processes():
    """Find all Python processes related to our application"""
    stdout, stderr, _ = run_command("tasklist /FO CSV | findstr python.exe")
    processes = []
    
    for line in stdout.split('\n'):
        if 'python.exe' in line:
            # Parse CSV format: "Image Name","PID","Session Name","Session#","Mem Usage"
            parts = [p.strip('"') for p in line.split('","')]
            if len(parts) >= 2:
                try:
                    pid = int(parts[1])
                    processes.append(pid)
                except ValueError:
                    continue
    
    return processes

def find_streamlit_processes():
    """Find processes running our UI scripts"""
    stdout, stderr, _ = run_command('wmic process where "commandline like \'%run_ui.py%\' or commandline like \'%main_interface.py%\'" get processid,commandline /format:csv')
    
    pids = []
    for line in stdout.split('\n'):
        if 'run_ui.py' in line or 'main_interface.py' in line:
            # Extract PID from CSV format
            parts = line.split(',')
            if len(parts) >= 2:
                try:
                    pid = int(parts[-1].strip())
                    if pid > 0:
                        pids.append(pid)
                except (ValueError, IndexError):
                    continue
    
    return pids

def kill_processes(pids):
    """Kill processes by PID"""
    if not pids:
        print("No processes to kill")
        return
    
    print(f"Killing processes: {pids}")
    for pid in pids:
        stdout, stderr, code = run_command(f"taskkill /F /PID {pid}")
        if code == 0:
            print(f"Killed process {pid}")
        else:
            print(f"Failed to kill process {pid}: {stderr}")

def check_ports():
    """Check which ports are in use"""
    stdout, stderr, _ = run_command("netstat -ano | findstr :850")
    if stdout:
        print("Ports in use:")
        for line in stdout.split('\n'):
            if ':850' in line:
                print(f"  {line.strip()}")
    else:
        print("No ports 8500-8509 in use")

def main():
    print("Email Intelligence System Process Cleanup")
    print("=" * 50)
    
    # Find and kill Streamlit processes
    streamlit_pids = find_streamlit_processes()
    if streamlit_pids:
        print(f"Found Streamlit processes: {streamlit_pids}")
        kill_processes(streamlit_pids)
    else:
        print("No Streamlit processes found")
    
    print("\nPort Status:")
    check_ports()
    
    print("\nRemaining Python processes:")
    python_pids = find_python_processes()
    if python_pids:
        print(f"Python processes still running: {python_pids}")
        print("(These may be legitimate processes - not killing automatically)")
    else:
        print("No Python processes found")
    
    print("\nCleanup complete!")

if __name__ == "__main__":
    main()