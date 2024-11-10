import tkinter as tk
from tkinter import messagebox
import json
import time
from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Listener as MouseListener
from pynput.keyboard import Listener as KeyboardListener, KeyCode  # Alias to avoid conflicts

import pygetwindow as gw
from threading import Thread
import os
import psutil
from pynput import mouse, keyboard
import threading

# Global variables
mouse_controller = MouseController()
keyboard_controller = KeyboardController()
mouse_listener = None
keyboard_listener = None
recorded_actions = []
is_recording = False
is_stopped = False  # New flag to stop actions
debug_mode = True  # Debug mode for verbose output

#___________________________________________________________________________________

# Global variables
stop_flag = False  # This flag will indicate when to stop all threads
def stop_all_threads():
    global stop_flag
    stop_flag = True
    for thread in threading.enumerate():
        if thread != threading.main_thread():
            thread.join()

# #_________________________________________________________________________

# Helper functions for window and application management
def check_and_launch_app(executable_path):
    """Check if app is running, launch if not."""
    for process in psutil.process_iter(['pid', 'name', 'exe']):
        if process.info['exe'] == executable_path:
            print(f"Application '{executable_path}' is already running.")
            return True
    try:
        os.startfile(executable_path)
        print(f"Launching application: {executable_path}")
        time.sleep(3)
        return True
    except Exception as e:
        print(f"Error launching application: {e}")
        return False

def is_window_active(window_title):
    """Check if the specified window is active."""
    active_window = gw.getActiveWindow()
    return active_window and window_title in active_window.title

def focus_window(window_title):
    """Activate a window by title if possible."""
    try:
        for window in gw.getWindowsWithTitle(window_title):
            window.activate()
            print(f"Activated window: {window_title}")
            return True
    except Exception as e:
        print(f"Error activating window: {e}")
    return False

# Action handling functions
def perform_action(action):
    """Executes a single action with error handling and debugging."""
    if is_stopped:  # Check if actions should stop
        return

    try:
        if action['type'] == 'click':
            button = Button.left if action['button'] == 'left' else Button.right
            mouse_controller.position = action['position']
            mouse_controller.click(button)
            if debug_mode:
                print(f"Clicked at {action['position']} with {action['button']} button.")

        elif action['type'] == 'keypress':
            key_value = action['key'].replace("'", "")  # Clean up key value
            if hasattr(Key, key_value):  # Handle special keys
                keyboard_controller.press(getattr(Key, key_value))
                time.sleep(0.05)
                keyboard_controller.release(getattr(Key, key_value))
            else:
                keyboard_controller.press(key_value)
                time.sleep(0.05)
                keyboard_controller.release(key_value)

            if debug_mode:
                print(f"Pressed key: {key_value}")

        elif action['type'] == 'move':
            mouse_controller.position = action['position']
            if debug_mode:
                print(f"Moved to position: {action['position']}")

    except Exception as e:
        print(f"Error performing action {action}: {e}")

def replay_with_decision_making(actions, speed=1.0):
    """Replays recorded actions with stop capability and adaptive timing."""
    global is_stopped
    is_stopped = False  # Reset stop flag at the beginning

    previous_timestamp = None
    for action in actions:
        if is_stopped:  # Check if stopped
            print("Execution stopped by user.")
            break

        if previous_timestamp is not None:
            delay = (action["timestamp"] - previous_timestamp) / speed
            if delay > 0:
                time.sleep(delay)

        perform_action(action)
        previous_timestamp = action["timestamp"]


# GUI function to start automation
def start_automation(loop_count):
    """Replays recorded actions with the original timing intervals."""
    try:
        # Load actions from the saved JSON file
        with open("actions.json", "r") as file:
            actions = json.load(file)
        
        # Initialize controllers
        mouse_ctrl = MouseController()
        keyboard_ctrl = KeyboardController()

        for _ in range(loop_count):
            last_timestamp = None

            for action in actions:
                current_timestamp = action.get("timestamp")
                
                # Calculate delay based on recorded time intervals
                if last_timestamp is not None:
                    delay = current_timestamp - last_timestamp
                    time.sleep(delay)
                
                # Execute the action
                if action["type"] == "click":
                    x, y = action["position"]
                    button = Button[action["button"].split('.')[-1]]
                    mouse_ctrl.position = (x, y)
                    mouse_ctrl.press(button)
                    mouse_ctrl.release(button)
                
                elif action["type"] == "move":
                    x, y = action["position"]
                    mouse_ctrl.position = (x, y)
                
                elif action["type"] == "keypress":
                    key = action["key"]
                    if len(key) == 3 and key[0] == "'" and key[2] == "'":
                        keyboard_ctrl.press(key[1])
                        keyboard_ctrl.release(key[1])
                    else:
                        key_name = key.split('.')[-1]
                        if hasattr(Key, key_name):
                            keyboard_ctrl.press(getattr(Key, key_name))
                            keyboard_ctrl.release(getattr(Key, key_name))
                        else:
                            raise ValueError(f"Unsupported key: {key}")
                    
                # Update last_timestamp for next action
                last_timestamp = current_timestamp

                if debug_mode:
                    print(f"Executed action: {action}")

    except Exception as e:
        messagebox.showerror("Error", f"Failed to load or replay actions: {e}")

# Function to handle GUI setup and event bindings
def start_gui():
    window = tk.Tk()
    window.title("Intelligent Automation Tool")

    def start_recording():
        global is_recording, mouse_listener, keyboard_listener
        is_recording = True
        recorded_actions.clear()
        start_time = time.time()
        window.iconify()  # Minimize the window

        def on_click(x, y, button, pressed):
            if is_recording:
                recorded_actions.append({
                    "action": "click",
                    "pos": (x, y),
                    "button": str(button),
                    "pressed": pressed,
                    "timestamp": time.time() - start_time
                })

        def on_move(x, y):
            if is_recording:
                recorded_actions.append({
                    "action": "move",
                    "pos": (x, y),
                    "timestamp": time.time() - start_time
                })

        def on_press(key):
            if is_recording:
                recorded_actions.append({
                    "action": "press",
                    "key": str(key),
                    "timestamp": time.time() - start_time
                })

        # Start listeners for mouse and keyboard with event functions
        mouse_listener = MouseListener(on_click=on_click, on_move=on_move)
        keyboard_listener = KeyboardListener(on_press=on_press)
        mouse_listener.start()
        keyboard_listener.start()

    def stop_recording():
        global is_recording
        is_recording = False
        if mouse_listener:
            mouse_listener.stop()
        if keyboard_listener:
            keyboard_listener.stop()
        with open("actions.json", "w") as file:
            json.dump(recorded_actions, file)
        if debug_mode:
            print("Recording stopped and actions saved.")

    def close_program(event=None):
        global stop_flag
        stop_flag = True
        if is_recording:
            stop_recording()
        stop_all_threads()
        window.quit()
        window.destroy()

    def replay_actions():
        try:
            loop_count = int(loop_count_entry.get())
            if loop_count < 1:
                raise ValueError("Loop count must be a positive integer.")
            window.iconify()  # Minimize the window
            threading.Thread(target=start_automation, args=(loop_count,)).start()
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid positive integer for the loop count.")

    window.bind('<Control-q>', close_program)
    tk.Button(window, text="Start Recording", command=start_recording).pack(pady=10)
    tk.Button(window, text="Stop Recording", command=stop_recording).pack(pady=10)
    tk.Label(window, text="Enter Loop Count:").pack()
    loop_count_entry = tk.Entry(window)
    loop_count_entry.pack()
    tk.Button(window, text="Replay Actions", command=replay_actions).pack(pady=10)
    window.protocol("WM_DELETE_WINDOW", close_program)
    window.mainloop()

def start_automation(loop_count):
    global stop_flag
    for i in range(loop_count):
        if stop_flag:
            print("Automation stopping...")
            break
        print(f"Replaying actions - loop {i + 1}")
        prev_timestamp = 0
        for action in recorded_actions:
            if stop_flag:
                break

            # Calculate the delay based on timestamp difference
            delay = action["timestamp"] - prev_timestamp
            time.sleep(delay)
            prev_timestamp = action["timestamp"]
            
            try:
                # Execute each action
                if action["action"] == "move":
                    x, y = action["pos"]
                    mouse_controller.position = (x, y)
                elif action["action"] == "click" and action["pressed"]:
                    x, y = action["pos"]
                    mouse_controller.position = (x, y)
                    button = Button.left if action["button"] == "Button.left" else Button.right
                    mouse_controller.click(button)
                elif action["action"] == "press":
                    key = action["key"]
                    if "Key." in key:
                        key = getattr(Key, key.split(".")[1], None)
                    else:
                        key = key.replace("'", "")
                    
                    # Skip unsupported keys
                    if key:
                        keyboard_controller.press(key)
                        keyboard_controller.release(key)
            except ValueError as e:
                print(f"Skipping unsupported key: {e}")
    print("Automation completed.")


start_gui()