import os
import subprocess
import threading
import sys
import shutil  # NEW: Needed for copying subtitle files
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
from pathlib import Path

# --- CUSTOM LOG REDIRECTOR ---
class ConsoleRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, string)
            self.text_widget.see(tk.END)
            self.text_widget.configure(state='disabled')
        self.text_widget.after(0, append)

    def flush(self): pass
    def isatty(self): return False

# --- THE GUI APPLICATION ---
class OptimizerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("OpenStream - MKV Auto-Optimizer (Pro)")
        self.root.geometry("700x500")
        self.root.configure(padx=20, pady=20)

        self.target_dir = ""
        self.is_running = False

        tk.Label(root, text="MKV to MP4 Auto-Optimizer", font=("Arial", 16, "bold")).pack(pady=(0, 5))
        tk.Label(
            root, 
            text="Fixes 'No Sound', 'Slow Loading', and auto-extracts Subtitles for Android.", 
            font=("Arial", 10), 
            fg="gray"
        ).pack(pady=(0, 20))

        folder_frame = tk.Frame(root)
        folder_frame.pack(fill="x", pady=10)
        
        self.folder_var = tk.StringVar(value="No folder selected")
        tk.Entry(folder_frame, textvariable=self.folder_var, state="readonly", width=55).pack(side="left", padx=(0, 10))
        tk.Button(folder_frame, text="Browse Library...", command=self.select_folder).pack(side="left")

        self.run_btn = tk.Button(
            root, text="START OPTIMIZATION", bg="#E50914", fg="white", 
            font=("Arial", 12, "bold"), command=self.start_optimization_thread
        )
        self.run_btn.pack(pady=15)

        tk.Label(root, text="Processing Logs:", font=("Arial", 10, "bold")).pack(anchor="w")
        self.console = scrolledtext.ScrolledText(root, state='disabled', bg="#1E1E1E", fg="#D4D4D4", font=("Consolas", 10))
        self.console.pack(fill="both", expand=True)

        sys.stdout = ConsoleRedirector(self.console)
        sys.stderr = ConsoleRedirector(self.console)

        print("[SYSTEM] Optimizer GUI loaded. Awaiting folder selection.")

    def select_folder(self):
        folder = filedialog.askdirectory(title="Select your Media Folder (e.g., T7 SSD)")
        if folder:
            self.target_dir = folder
            self.folder_var.set(folder)
            print(f"[SELECTED] Targeting library: {self.target_dir}")

    def start_optimization_thread(self):
        if not self.target_dir:
            messagebox.showerror("Error", "Please select a media folder first!")
            return
        if self.is_running:
            return

        self.is_running = True
        self.run_btn.config(text="OPTIMIZING... PLEASE WAIT", bg="gray", state="disabled")
        threading.Thread(target=self.run_optimization, daemon=True).start()

    def run_optimization(self):
        directory = Path(self.target_dir)
        print(f"\n[START] Scanning {directory} for unoptimized MKV/MP4 files...\n")
        
        found_files = []
        for root_dir, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(('.mkv', '.mp4')) and not file.endswith("_optimized.mp4"):
                    found_files.append(Path(root_dir) / file)

        if not found_files:
            print("[DONE] Everything is perfect! No files found that need optimization.")
        else:
            print(f"[INFO] Found {len(found_files)} file(s) to optimize.\n")
            for input_path in found_files:
                output_path = input_path.with_name(f"{input_path.stem}_optimized.mp4")
                srt_output_path = output_path.with_suffix(".srt")
                original_srt = input_path.with_suffix(".srt")
                
                print(f"[PROCESSING] {input_path.name} ...")
                
                # 1. Optimize Video and Audio (and explicitly ignore subtitles here to keep the MP4 clean)
                command = [
                    "ffmpeg", "-y", "-i", str(input_path),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-sn",
                    "-movflags", "+faststart", str(output_path)
                ]
                
                try:
                    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print(f"   ↳ [SUCCESS] Video optimized: {output_path.name}")
                    
                    # 2. Handle the Subtitles
                    if original_srt.exists():
                        # If an external file already exists, copy it to match the new video name!
                        shutil.copy(original_srt, srt_output_path)
                        print(f"   ↳ [SUCCESS] Linked external subtitle: {srt_output_path.name}")
                    else:
                        # No external file? Try to extract the embedded subtitles from the MKV!
                        # '-map 0:s:0?' looks for the primary subtitle track.
                        sub_cmd = [
                            "ffmpeg", "-y", "-i", str(input_path),
                            "-map", "0:s:0?", "-c:s", "srt", str(srt_output_path)
                        ]
                        subprocess.run(sub_cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        
                        # Clean up: If no subs existed, FFmpeg creates an empty 0-byte file. We delete it here.
                        if srt_output_path.exists():
                            if srt_output_path.stat().st_size > 0:
                                print(f"   ↳ [SUCCESS] Extracted embedded subtitle: {srt_output_path.name}")
                            else:
                                srt_output_path.unlink()
                                
                except subprocess.CalledProcessError:
                    print(f"   ↳ [ERROR] Failed to process. Is FFmpeg installed?")

        print("\n[FINISHED] All optimization tasks completed.")
        
        def reset_ui():
            self.is_running = False
            self.run_btn.config(text="START OPTIMIZATION", bg="#E50914", state="normal")
        
        self.root.after(0, reset_ui)

if __name__ == "__main__":
    root = tk.Tk()
    app = OptimizerGUI(root)
    root.mainloop()