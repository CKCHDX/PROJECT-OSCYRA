#!/usr/bin/env python3
"""
Upsum Desktop Application
A privacy-focused Qt WebEngine browser for accessing Upsum.

Features:
- No tracking, no cookies, no session persistence
- Clean, minimal interface
- Direct access to upsum.oscyra.solutions
- Incognito mode by default
"""

import sys
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, 
    QWidget, QLineEdit, QPushButton, QHBoxLayout
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings

class UpsumBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Upsum — Svensk Kunskap")
        self.setGeometry(100, 100, 1200, 800)
        
        # Set dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #05070b;
            }
            QLineEdit {
                background-color: #0b1118;
                color: #e5e9f0;
                border: 1px solid #1a2330;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #88c0d0;
                color: #05070b;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #a3be8c;
            }
        """)
        
        # Create privacy-focused profile (incognito mode)
        self.profile = QWebEngineProfile()
        self.profile.setHttpCacheType(QWebEngineProfile.CacheType.NoCache)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create toolbar
        toolbar = QWidget()
        toolbar.setStyleSheet("background-color: #0b1118; padding: 8px;")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(8, 8, 8, 8)
        
        # URL bar
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("https://upsum.oscyra.solutions")
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        toolbar_layout.addWidget(self.url_bar)
        
        # Home button
        home_button = QPushButton("⌂ Hem")
        home_button.clicked.connect(self.go_home)
        toolbar_layout.addWidget(home_button)
        
        layout.addWidget(toolbar)
        
        # Create web view with privacy profile
        self.browser = QWebEngineView()
        self.browser.setPage(self.profile.defaultProfile().page())
        
        # Configure privacy settings
        settings = self.browser.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowGeolocationOnInsecureOrigins, False)
        
        # Connect signals
        self.browser.urlChanged.connect(self.update_url_bar)
        self.browser.loadFinished.connect(self.on_load_finished)
        
        layout.addWidget(self.browser)
        
        # Load Upsum homepage
        self.go_home()
    
    def go_home(self):
        """Navigate to Upsum homepage."""
        url = QUrl("https://upsum.oscyra.solutions")
        self.browser.setUrl(url)
    
    def navigate_to_url(self):
        """Navigate to URL in address bar."""
        url_text = self.url_bar.text().strip()
        
        # Add https:// if missing
        if not url_text.startswith(('http://', 'https://')):
            url_text = 'https://' + url_text
        
        url = QUrl(url_text)
        self.browser.setUrl(url)
    
    def update_url_bar(self, url):
        """Update URL bar when page changes."""
        self.url_bar.setText(url.toString())
    
    def on_load_finished(self, success):
        """Handle page load completion."""
        if success:
            print(f"Loaded: {self.browser.url().toString()}")
        else:
            print(f"Failed to load: {self.browser.url().toString()}")

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Upsum")
    app.setOrganizationName("Oscyra Solutions")
    
    window = UpsumBrowser()
    window.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
