import subprocess
import os
import time
import sys

def test_game_startup(game_path, timeout=30):
    game_dir = os.path.dirname(game_path)
    traceback_path = os.path.join(game_dir, "traceback.txt")
    
    # Remove existing traceback
    if os.path.exists(traceback_path):
        try: os.remove(traceback_path)
        except: pass
        
    print(f"Starting game: {game_path}")
    try:
        # Start game in background
        proc = subprocess.Popen([game_path], cwd=game_dir)
        
        # Monitor for a short period
        start_time = time.time()
        while time.time() - start_time < timeout:
            if os.path.exists(traceback_path):
                print("CRASH DETECTED: traceback.txt found!")
                with open(traceback_path, "r", encoding="utf-8", errors="replace") as f:
                    return False, f.read()
            
            if proc.poll() is not None:
                # If it closed quickly without traceback, it might still be a crash
                time.sleep(2)
                if os.path.exists(traceback_path):
                    with open(traceback_path, "r", encoding="utf-8", errors="replace") as f:
                        return False, f.read()
                print("Game closed unexpectedly without traceback.")
                return False, "Process exited without traceback.txt"
                
            time.sleep(1)
            
        print("Game seems to be running fine (no crash detected after timeout).")
        proc.terminate()
        return True, None
        
    except Exception as e:
        return False, str(e)

if __name__ == "__main__":
    game_exe = r"Jogo atual\Being_Super_Chapter_1-0.29.LIGHT-pc\Being_Super_Chapter_1-0.29.LIGHT-pc\Being_Super_Chapter_1.exe"
    success, log = test_game_startup(game_exe)
    
    if not success:
        print("\n--- TRACEBACK ---")
        print(log)
        sys.exit(1)
    else:
        sys.exit(0)
