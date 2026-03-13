#!/usr/bin/env python3
"""
SLP Client GUI - Windows Application

Graphical client for connecting to SLP servers.
Can be compiled to .exe using PyInstaller.
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import webbrowser
import tempfile
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from slp.client.simple_client import SimpleSLPClient


class SLPClientGUI:
    """SLP Client GUI Application."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("🔒 SLP Client v1.0")
        self.root.geometry("900x700")
        self.root.configure(bg='#1a1a1a')
        
        self.last_html = None
        self.setup_ui()
    
    def setup_ui(self):
        """Setup user interface."""
        # Style configuration
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TLabel', background='#1a1a1a', foreground='#00e5ff', font=('Arial', 10))
        style.configure('TButton', background='#00e5ff', foreground='#000000', font=('Arial', 10, 'bold'))
        
        # Main container
        main_frame = tk.Frame(self.root, bg='#1a1a1a')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text="🔒 Secure Line Protocol Client",
            font=('Arial', 18, 'bold'),
            bg='#1a1a1a',
            fg='#00e5ff'
        )
        title_label.pack(pady=(0, 20))
        
        # URL input section
        url_frame = tk.Frame(main_frame, bg='#1a1a1a')
        url_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(
            url_frame,
            text="SLP Address:",
            font=('Arial', 11, 'bold'),
            bg='#1a1a1a',
            fg='#00ffa3'
        ).pack(anchor=tk.W)
        
        self.url_entry = tk.Entry(
            url_frame,
            width=70,
            font=('Consolas', 11),
            bg='#0a0a0a',
            fg='#00e5ff',
            insertbackground='#00e5ff',
            relief=tk.FLAT,
            bd=2
        )
        self.url_entry.insert(0, "slp://localhost:4270/")
        self.url_entry.pack(fill=tk.X, pady=5, ipady=8)
        self.url_entry.bind('<Return>', lambda e: self.connect())
        
        # Button section
        button_frame = tk.Frame(main_frame, bg='#1a1a1a')
        button_frame.pack(pady=10)
        
        self.connect_btn = tk.Button(
            button_frame,
            text="🔌 Connect",
            command=self.connect,
            font=('Arial', 11, 'bold'),
            bg='#00e5ff',
            fg='#000000',
            relief=tk.FLAT,
            padx=20,
            pady=8,
            cursor='hand2'
        )
        self.connect_btn.pack(side=tk.LEFT, padx=5)
        
        self.browser_btn = tk.Button(
            button_frame,
            text="🌐 Open in Browser",
            command=self.open_browser,
            font=('Arial', 11, 'bold'),
            bg='#00ffa3',
            fg='#000000',
            relief=tk.FLAT,
            padx=20,
            pady=8,
            state=tk.DISABLED,
            cursor='hand2'
        )
        self.browser_btn.pack(side=tk.LEFT, padx=5)
        
        clear_btn = tk.Button(
            button_frame,
            text="🗑️ Clear",
            command=self.clear_response,
            font=('Arial', 11, 'bold'),
            bg='#555555',
            fg='#ffffff',
            relief=tk.FLAT,
            padx=20,
            pady=8,
            cursor='hand2'
        )
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        # Status section
        self.status_label = tk.Label(
            main_frame,
            text="✅ Ready",
            font=('Arial', 10, 'bold'),
            bg='#1a1a1a',
            fg='#00ffa3'
        )
        self.status_label.pack(pady=10)
        
        # Response display
        tk.Label(
            main_frame,
            text="Response:",
            font=('Arial', 11, 'bold'),
            bg='#1a1a1a',
            fg='#00ffa3'
        ).pack(anchor=tk.W)
        
        self.response_text = scrolledtext.ScrolledText(
            main_frame,
            height=25,
            width=95,
            font=('Consolas', 9),
            bg='#0a0a0a',
            fg='#00e5ff',
            insertbackground='#00e5ff',
            relief=tk.FLAT,
            bd=2,
            wrap=tk.WORD
        )
        self.response_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Footer
        footer = tk.Label(
            main_frame,
            text="Oscyra Solutions | Secure Line Protocol v1.0",
            font=('Arial', 8),
            bg='#1a1a1a',
            fg='#666666'
        )
        footer.pack(pady=(10, 0))
    
    def log(self, message, level='info'):
        """Add log message to response text."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        color_codes = {
            'info': '',
            'success': '✅',
            'error': '❌',
            'warning': '⚠️ '
        }
        icon = color_codes.get(level, '')
        self.response_text.insert(tk.END, f"[{timestamp}] {icon} {message}\n")
        self.response_text.see(tk.END)
        self.root.update()
    
    def connect(self):
        """Connect to SLP server."""
        url = self.url_entry.get().strip()
        
        if not url:
            messagebox.showwarning("Invalid URL", "Please enter a valid SLP address.")
            return
        
        self.status_label.config(text="⏳ Connecting...", fg="#ffa500")
        self.response_text.delete(1.0, tk.END)
        self.browser_btn.config(state=tk.DISABLED)
        self.connect_btn.config(state=tk.DISABLED)
        self.root.update()
        
        self.log(f"Connecting to {url}...")
        
        try:
            client = SimpleSLPClient(timeout=5.0)
            self.log("Sending request...")
            
            response = client.connect(url)
            
            self.log(f"Received {len(response)} bytes", 'success')
            self.response_text.insert(tk.END, "\n" + "="*80 + "\n")
            self.response_text.insert(tk.END, response)
            self.response_text.insert(tk.END, "\n" + "="*80 + "\n")
            
            self.status_label.config(text="✅ Connected successfully!", fg="#00ffa3")
            self.last_html = response
            self.browser_btn.config(state=tk.NORMAL)
            
            self.log("Connection complete", 'success')
            
        except Exception as e:
            self.log(f"Error: {str(e)}", 'error')
            self.status_label.config(text=f"❌ Error: {str(e)}", fg="#ff4444")
            messagebox.showerror("Connection Error", str(e))
        
        finally:
            self.connect_btn.config(state=tk.NORMAL)
    
    def open_browser(self):
        """Open response in web browser."""
        if not self.last_html:
            messagebox.showwarning("No Content", "No HTML content to display.")
            return
        
        try:
            # Save HTML to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                # Extract HTML from HTTP response if present
                html_content = self.last_html
                if '\r\n\r\n' in html_content:
                    html_content = html_content.split('\r\n\r\n', 1)[1]
                
                f.write(html_content)
                temp_path = f.name
            
            # Open in browser
            webbrowser.open(f'file:///{temp_path}')
            self.log("Opened in browser", 'success')
            
        except Exception as e:
            messagebox.showerror("Browser Error", f"Failed to open browser: {str(e)}")
            self.log(f"Browser error: {str(e)}", 'error')
    
    def clear_response(self):
        """Clear response text."""
        self.response_text.delete(1.0, tk.END)
        self.status_label.config(text="✅ Ready", fg="#00ffa3")
        self.browser_btn.config(state=tk.DISABLED)
        self.last_html = None


def main():
    """Main entry point."""
    root = tk.Tk()
    app = SLPClientGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
