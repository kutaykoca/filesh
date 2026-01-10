#!/usr/bin/env python3
"""
filesh - Simple LAN File Sharing Server
Usage: filesh [OPTIONS] [DIRECTORY]
"""

import os
import sys
import socket
import argparse
import mimetypes
import secrets
from datetime import datetime
from urllib.parse import unquote, quote
from flask import Flask, request, send_file, render_template_string, abort, jsonify, session, redirect
import qrcode

app = Flask(__name__)

# Global config
ROOT_DIR = os.getcwd()
SHOW_HIDDEN = False
SESSION_CODE = None

def generate_session_code():
    """Generate a 6-digit session code"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(6)])

def is_localhost():
    """Check if request is from localhost"""
    remote = request.remote_addr
    return remote in ('127.0.0.1', '::1', 'localhost')

def require_auth():
    """Check if user needs authentication"""
    if is_localhost():
        return False
    return not session.get('authenticated')

AUTH_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>filesh - Access Code</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        :root {
            --background: #ffffff;
            --foreground: #09090b;
            --card: #ffffff;
            --primary: #18181b;
            --primary-foreground: #fafafa;
            --secondary: #f4f4f5;
            --muted: #f4f4f5;
            --muted-foreground: #71717a;
            --border: #e4e4e7;
            --ring: #a1a1aa;
            --radius: 0.5rem;
            --destructive: #ef4444;
        }
        .dark {
            --background: #09090b;
            --foreground: #fafafa;
            --card: #09090b;
            --primary: #fafafa;
            --primary-foreground: #18181b;
            --secondary: #27272a;
            --muted: #27272a;
            --muted-foreground: #a1a1aa;
            --border: #27272a;
            --ring: #d4d4d8;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--background);
            color: var(--foreground);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
        }
        .auth-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 32px;
            width: 100%;
            max-width: 360px;
            text-align: center;
        }
        .logo {
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 8px;
        }
        .subtitle {
            color: var(--muted-foreground);
            font-size: 14px;
            margin-bottom: 24px;
        }
        .code-inputs {
            display: flex;
            gap: 8px;
            justify-content: center;
            margin-bottom: 24px;
        }
        .code-input {
            width: 44px;
            height: 52px;
            text-align: center;
            font-size: 20px;
            font-weight: 600;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            background: var(--background);
            color: var(--foreground);
            outline: none;
            transition: border-color 0.15s;
        }
        .code-input:focus {
            border-color: var(--ring);
        }
        .code-input.error {
            border-color: var(--destructive);
            animation: shake 0.3s ease;
        }
        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            25% { transform: translateX(-4px); }
            75% { transform: translateX(4px); }
        }
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            padding: 12px 24px;
            font-size: 14px;
            font-weight: 500;
            border-radius: var(--radius);
            border: none;
            background: var(--primary);
            color: var(--primary-foreground);
            cursor: pointer;
            transition: opacity 0.15s;
        }
        .btn:hover { opacity: 0.9; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .error-msg {
            color: var(--destructive);
            font-size: 13px;
            margin-top: 16px;
            display: none;
        }
        .error-msg.show { display: block; }
    </style>
    <script>
        (function() {
            const theme = localStorage.getItem('theme') || 'light';
            if (theme === 'dark') document.documentElement.classList.add('dark');
        })();
    </script>
</head>
<body>
    <div class="auth-card">
        <div class="logo">filesh</div>
        <p class="subtitle">Enter the access code shown in terminal</p>
        <form id="authForm" onsubmit="return submitCode(event)">
            <div class="code-inputs">
                <input type="text" class="code-input" maxlength="1" inputmode="numeric" pattern="[0-9]" required>
                <input type="text" class="code-input" maxlength="1" inputmode="numeric" pattern="[0-9]" required>
                <input type="text" class="code-input" maxlength="1" inputmode="numeric" pattern="[0-9]" required>
                <input type="text" class="code-input" maxlength="1" inputmode="numeric" pattern="[0-9]" required>
                <input type="text" class="code-input" maxlength="1" inputmode="numeric" pattern="[0-9]" required>
                <input type="text" class="code-input" maxlength="1" inputmode="numeric" pattern="[0-9]" required>
            </div>
            <button type="submit" class="btn">Verify</button>
        </form>
        <p class="error-msg" id="errorMsg">Invalid code. Please try again.</p>
    </div>
    <script>
        const inputs = document.querySelectorAll('.code-input');

        inputs.forEach((input, index) => {
            input.addEventListener('input', (e) => {
                const val = e.target.value.replace(/[^0-9]/g, '');
                e.target.value = val;
                if (val && index < inputs.length - 1) {
                    inputs[index + 1].focus();
                }
            });

            input.addEventListener('keydown', (e) => {
                if (e.key === 'Backspace' && !e.target.value && index > 0) {
                    inputs[index - 1].focus();
                }
            });

            input.addEventListener('paste', (e) => {
                e.preventDefault();
                const paste = (e.clipboardData || window.clipboardData).getData('text');
                const digits = paste.replace(/[^0-9]/g, '').slice(0, 6);
                digits.split('').forEach((d, i) => {
                    if (inputs[i]) inputs[i].value = d;
                });
                if (digits.length > 0) inputs[Math.min(digits.length, 5)].focus();
            });
        });

        inputs[0].focus();

        async function submitCode(e) {
            e.preventDefault();
            const code = Array.from(inputs).map(i => i.value).join('');
            if (code.length !== 6) return false;

            const res = await fetch('/auth', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code: code})
            });

            if (res.ok) {
                window.location.href = '/';
            } else {
                inputs.forEach(i => {
                    i.classList.add('error');
                    i.value = '';
                });
                inputs[0].focus();
                document.getElementById('errorMsg').classList.add('show');
                setTimeout(() => {
                    inputs.forEach(i => i.classList.remove('error'));
                }, 300);
            }
            return false;
        }
    </script>
</body>
</html>
"""

def get_local_ip():
    """Get local IP address for LAN sharing"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def format_size(size):
    """Format file size to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.1f} {unit}" if unit != 'B' else f"{size} {unit}"
        size /= 1024
    return f"{size:.1f} PB"

def get_file_icon(filename, is_dir=False):
    """Get icon for file type"""
    if is_dir:
        return "folder"

    ext = os.path.splitext(filename)[1].lower()
    icons = {
        '.jpg': 'image', '.jpeg': 'image', '.png': 'image', '.gif': 'image',
        '.bmp': 'image', '.svg': 'image', '.webp': 'image', '.ico': 'image',
        '.mp4': 'video', '.avi': 'video', '.mkv': 'video', '.mov': 'video',
        '.wmv': 'video', '.flv': 'video', '.webm': 'video',
        '.mp3': 'audio', '.wav': 'audio', '.flac': 'audio', '.aac': 'audio',
        '.ogg': 'audio', '.m4a': 'audio',
        '.pdf': 'pdf',
        '.doc': 'doc', '.docx': 'doc', '.xls': 'doc', '.xlsx': 'doc',
        '.ppt': 'doc', '.pptx': 'doc',
        '.txt': 'text', '.md': 'text', '.log': 'text',
        '.json': 'code', '.xml': 'code', '.csv': 'code',
        '.py': 'python', '.js': 'js', '.ts': 'js',
        '.html': 'html', '.css': 'css',
        '.java': 'code', '.cpp': 'code', '.c': 'code', '.h': 'code',
        '.go': 'code', '.rs': 'code', '.rb': 'code', '.php': 'code',
        '.sh': 'terminal', '.bat': 'terminal', '.ps1': 'terminal',
        '.zip': 'archive', '.rar': 'archive', '.7z': 'archive',
        '.tar': 'archive', '.gz': 'archive', '.bz2': 'archive',
        '.exe': 'binary', '.msi': 'binary', '.dmg': 'binary',
        '.app': 'binary', '.deb': 'binary', '.rpm': 'binary',
    }
    return icons.get(ext, 'file')

def is_previewable(filename):
    """Check if file can be previewed"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp',
                   '.mp4', '.webm', '.ogg', '.mp3', '.wav',
                   '.txt', '.md', '.json', '.xml', '.csv', '.log', '.py',
                   '.js', '.html', '.css', '.sh', '.yaml', '.yml', '.ini', '.cfg']

def get_preview_type(filename):
    """Get preview type for file"""
    ext = os.path.splitext(filename)[1].lower()
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp']:
        return 'image'
    if ext in ['.mp4', '.webm', '.ogg']:
        return 'video'
    if ext in ['.mp3', '.wav', '.ogg', '.m4a']:
        return 'audio'
    return 'text'

# SVG Icons (Lucide-style)
ICONS = {
    'folder': '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"/></svg>',
    'folder-open': '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 14 1.45-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.55 6a2 2 0 0 1-1.94 1.5H4a2 2 0 0 1-2-2V5c0-1.1.9-2 2-2h3.93a2 2 0 0 1 1.66.9l.82 1.2a2 2 0 0 0 1.66.9H18a2 2 0 0 1 2 2v2"/></svg>',
    'file': '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/></svg>',
    'image': '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/></svg>',
    'video': '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m16 13 5.223 3.482a.5.5 0 0 0 .777-.416V7.87a.5.5 0 0 0-.752-.432L16 10.5"/><rect x="2" y="6" width="14" height="12" rx="2"/></svg>',
    'audio': '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>',
    'text': '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/></svg>',
    'code': '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
    'python': '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 9H5a2 2 0 0 0-2 2v4a2 2 0 0 0 2 2h3"/><path d="M12 15h7a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3"/><path d="M8 9V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-4a2 2 0 0 0-2 2v5a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2v-4"/><circle cx="7.5" cy="6.5" r=".5" fill="currentColor"/><circle cx="16.5" cy="17.5" r=".5" fill="currentColor"/></svg>',
    'js': '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="m10 14-2 2 2 2"/><path d="m14 14 2 2-2 2"/></svg>',
    'html': '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m4 6 8-4 8 4"/><path d="m4 6v12l8 4"/><path d="m20 6v12l-8 4"/><path d="M4 6l8 4"/><path d="m20 6-8 4"/><path d="m12 10v10"/></svg>',
    'css': '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/><line x1="21.17" y1="8" x2="12" y2="8"/><line x1="3.95" y1="6.06" x2="8.54" y2="14"/><line x1="10.88" y1="21.94" x2="15.46" y2="14"/></svg>',
    'pdf': '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 12a1 1 0 0 0-1 1v1a1 1 0 0 1-1 1 1 1 0 0 1 1 1v1a1 1 0 0 0 1 1"/><path d="M14 18a1 1 0 0 0 1-1v-1a1 1 0 0 1 1-1 1 1 0 0 1-1-1v-1a1 1 0 0 0-1-1"/></svg>',
    'doc': '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/></svg>',
    'archive': '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="5" rx="2"/><path d="M4 9v9a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9"/><path d="M10 13h4"/></svg>',
    'terminal': '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>',
    'binary': '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="14" y="14" width="4" height="6" rx="2"/><rect x="6" y="4" width="4" height="6" rx="2"/><path d="M6 20h4"/><path d="M14 10h4"/><path d="M6 14h2v6"/><path d="M14 4h2v6"/></svg>',
    'upload': '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>',
    'download': '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>',
    'trash': '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>',
    'eye': '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>',
    'chevron-up': '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m18 15-6-6-6 6"/></svg>',
    'chevron-right': '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg>',
    'home': '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
    'qr': '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="5" height="5" x="3" y="3" rx="1"/><rect width="5" height="5" x="16" y="3" rx="1"/><rect width="5" height="5" x="3" y="16" rx="1"/><path d="M21 16h-3a2 2 0 0 0-2 2v3"/><path d="M21 21v.01"/><path d="M12 7v3a2 2 0 0 1-2 2H7"/><path d="M3 12h.01"/><path d="M12 3h.01"/><path d="M12 16v.01"/><path d="M16 12h1"/><path d="M21 12v.01"/><path d="M12 21v-1"/></svg>',
    'folder-plus': '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"/><line x1="12" y1="10" x2="12" y2="16"/><line x1="9" y1="13" x2="15" y2="13"/></svg>',
    'x': '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>',
    'sun': '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></svg>',
    'moon': '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>',
}

TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>filesh{{ ' - ' + current if current != '/' else '' }}</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }

        :root {
            --background: #ffffff;
            --foreground: #09090b;
            --card: #ffffff;
            --card-foreground: #09090b;
            --primary: #18181b;
            --primary-foreground: #fafafa;
            --secondary: #f4f4f5;
            --secondary-foreground: #18181b;
            --muted: #f4f4f5;
            --muted-foreground: #71717a;
            --accent: #f4f4f5;
            --accent-foreground: #18181b;
            --border: #e4e4e7;
            --input: #e4e4e7;
            --ring: #a1a1aa;
            --radius: 0.5rem;
        }

        .dark {
            --background: #09090b;
            --foreground: #fafafa;
            --card: #09090b;
            --card-foreground: #fafafa;
            --primary: #fafafa;
            --primary-foreground: #18181b;
            --secondary: #27272a;
            --secondary-foreground: #fafafa;
            --muted: #27272a;
            --muted-foreground: #a1a1aa;
            --accent: #27272a;
            --accent-foreground: #fafafa;
            --border: #27272a;
            --input: #27272a;
            --ring: #d4d4d8;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
            background: var(--background);
            color: var(--foreground);
            min-height: 100vh;
            line-height: 1.5;
            font-size: 14px;
        }

        .container {
            max-width: 1000px;
            margin: 0 auto;
            padding: 24px;
        }

        /* Header */
        header {
            border-bottom: 1px solid var(--border);
            padding: 16px 24px;
            position: sticky;
            top: 0;
            background: var(--background);
            z-index: 100;
        }

        .header-content {
            max-width: 1000px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 16px;
        }

        .logo {
            font-size: 15px;
            font-weight: 600;
            color: var(--foreground);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .logo svg {
            color: var(--muted-foreground);
        }

        /* Breadcrumb */
        .breadcrumb {
            display: flex;
            align-items: center;
            gap: 4px;
            font-size: 13px;
            color: var(--muted-foreground);
        }

        .breadcrumb a {
            color: var(--muted-foreground);
            text-decoration: none;
            padding: 4px 8px;
            border-radius: var(--radius);
            transition: all 0.15s;
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .breadcrumb a:hover {
            color: var(--foreground);
            background: var(--secondary);
        }

        .breadcrumb-sep {
            color: var(--muted-foreground);
            opacity: 0.5;
        }

        /* Buttons */
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 500;
            border-radius: var(--radius);
            border: 1px solid var(--border);
            background: var(--background);
            color: var(--foreground);
            cursor: pointer;
            transition: all 0.15s;
            white-space: nowrap;
        }

        .btn:hover {
            background: var(--secondary);
        }

        .btn-primary {
            background: var(--primary);
            color: var(--primary-foreground);
            border-color: var(--primary);
        }

        .btn-primary:hover {
            opacity: 0.9;
        }

        .btn-ghost {
            border: none;
            background: transparent;
        }

        .btn-ghost:hover {
            background: var(--secondary);
        }

        .btn-sm {
            padding: 6px 10px;
            font-size: 12px;
        }

        .btn-icon {
            padding: 8px;
            border: none;
            background: transparent;
        }

        .btn-icon:hover {
            background: var(--secondary);
        }

        .actions {
            display: flex;
            gap: 8px;
        }

        /* Upload Zone */
        .upload-zone {
            border: 1px dashed var(--border);
            border-radius: var(--radius);
            padding: 32px;
            text-align: center;
            margin-bottom: 24px;
            transition: all 0.2s;
            background: var(--card);
        }

        .upload-zone.dragover {
            border-color: var(--ring);
            background: var(--secondary);
        }

        .upload-zone h3 {
            font-size: 14px;
            font-weight: 500;
            margin-bottom: 4px;
        }

        .upload-zone p {
            color: var(--muted-foreground);
            font-size: 13px;
            margin-bottom: 16px;
        }

        .upload-zone input[type="file"] {
            display: none;
        }

        .progress-bar {
            width: 100%;
            max-width: 300px;
            height: 4px;
            background: var(--secondary);
            border-radius: 2px;
            margin: 16px auto 0;
            overflow: hidden;
            display: none;
        }

        .progress-bar.active { display: block; }

        .progress-fill {
            height: 100%;
            background: var(--foreground);
            width: 0%;
            transition: width 0.3s;
        }

        /* Parent directory link */
        .parent-link {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 16px;
            margin-bottom: 8px;
            border-radius: var(--radius);
            color: var(--muted-foreground);
            text-decoration: none;
            transition: all 0.15s;
            font-size: 13px;
        }

        .parent-link:hover {
            background: var(--secondary);
            color: var(--foreground);
        }

        .parent-link svg {
            opacity: 0.7;
        }

        /* File List */
        .file-list {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        .file-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 16px;
            border-radius: var(--radius);
            color: var(--foreground);
            text-decoration: none;
            transition: all 0.15s;
            cursor: pointer;
        }

        .file-item:hover {
            background: var(--secondary);
        }

        .file-icon {
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 6px;
            background: var(--secondary);
            color: var(--muted-foreground);
            flex-shrink: 0;
        }

        .file-item:hover .file-icon {
            color: var(--foreground);
        }

        .file-info {
            flex: 1;
            min-width: 0;
        }

        .file-name {
            font-size: 13px;
            font-weight: 500;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .file-meta {
            font-size: 12px;
            color: var(--muted-foreground);
            display: flex;
            gap: 12px;
            margin-top: 2px;
        }

        .file-actions {
            display: flex;
            gap: 4px;
            opacity: 0;
            transition: opacity 0.15s;
        }

        .file-item:hover .file-actions {
            opacity: 1;
        }

        /* Modal */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 1000;
            justify-content: center;
            align-items: center;
            padding: 24px;
        }

        .modal.active { display: flex; }

        .modal-content {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 24px;
            max-width: 400px;
            width: 100%;
            max-height: 90vh;
            overflow: auto;
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }

        .modal-header h3 {
            font-size: 15px;
            font-weight: 600;
        }

        /* Form */
        .form-group {
            margin-bottom: 16px;
        }

        .form-group label {
            display: block;
            font-size: 13px;
            font-weight: 500;
            margin-bottom: 6px;
        }

        .form-group input {
            width: 100%;
            padding: 8px 12px;
            font-size: 13px;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            background: var(--background);
            color: var(--foreground);
            outline: none;
            transition: border-color 0.15s;
        }

        .form-group input:focus {
            border-color: var(--ring);
        }

        /* QR */
        .qr-container {
            text-align: center;
        }

        .qr-container img {
            background: white;
            padding: 12px;
            border-radius: var(--radius);
            margin-bottom: 16px;
        }

        .qr-url {
            padding: 10px 12px;
            background: var(--secondary);
            border-radius: var(--radius);
            font-family: monospace;
            font-size: 12px;
            word-break: break-all;
            color: var(--muted-foreground);
        }

        /* Preview */
        .preview-modal .modal-content {
            max-width: 800px;
        }

        .preview-content img,
        .preview-content video {
            max-width: 100%;
            max-height: 60vh;
            border-radius: var(--radius);
        }

        .preview-content pre {
            background: var(--secondary);
            padding: 16px;
            border-radius: var(--radius);
            overflow: auto;
            max-height: 60vh;
            font-size: 12px;
            font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
        }

        /* Empty state */
        .empty-state {
            text-align: center;
            padding: 48px 24px;
            color: var(--muted-foreground);
        }

        .empty-state p {
            font-size: 13px;
        }

        /* Toast */
        .toast-container {
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 2000;
        }

        .toast {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 12px 16px;
            margin-top: 8px;
            font-size: 13px;
            animation: slideIn 0.2s ease;
        }

        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }

        /* Theme toggle */
        .sun-icon { display: none; }
        .moon-icon { display: block; }
        .dark .sun-icon { display: block; }
        .dark .moon-icon { display: none; }

        /* Responsive */
        @media (max-width: 640px) {
            .container { padding: 16px; }
            .header-content { flex-wrap: wrap; }
            .file-actions { opacity: 1; }
            .upload-zone { padding: 24px 16px; }
            .actions { width: 100%; justify-content: flex-end; }
        }
    </style>
    <script>
        (function() {
            const theme = localStorage.getItem('theme') || 'light';
            if (theme === 'dark') document.documentElement.classList.add('dark');
        })();
    </script>
</head>
<body>
    <header>
        <div class="header-content">
            <div class="logo">
                {{ icons.folder_open|safe }}
                <span>filesh</span>
            </div>
            <nav class="breadcrumb">
                <a href="/">{{ icons.home|safe }} root</a>
                {% for crumb in breadcrumbs %}
                <span class="breadcrumb-sep">{{ icons.chevron_right|safe }}</span>
                <a href="/browse/{{ crumb.path }}">{{ crumb.name }}</a>
                {% endfor %}
            </nav>
            <div class="actions">
                <button class="btn btn-icon btn-sm" onclick="toggleTheme()" id="themeToggle" title="Toggle theme">
                    <span class="sun-icon">{{ icons.sun|safe }}</span>
                    <span class="moon-icon">{{ icons.moon|safe }}</span>
                </button>
                <button class="btn btn-ghost btn-sm" onclick="showQR()">
                    {{ icons.qr|safe }}
                    <span>QR</span>
                </button>
                <button class="btn btn-sm" onclick="showNewFolder()">
                    {{ icons.folder_plus|safe }}
                    <span>New Folder</span>
                </button>
            </div>
        </div>
    </header>

    <div class="container">
        <div class="upload-zone" id="uploadZone">
            <h3>Upload Files</h3>
            <p>Drag and drop or click to select</p>
            <input type="file" id="fileInput" multiple>
            <button class="btn btn-primary" onclick="document.getElementById('fileInput').click()">
                {{ icons.upload|safe }}
                Select Files
            </button>
            <div class="progress-bar" id="progressBar">
                <div class="progress-fill" id="progressFill"></div>
            </div>
        </div>

        {% if parent is not none %}
        <a href="{% if parent %}/browse/{{ parent }}{% else %}/{% endif %}" class="parent-link">
            {{ icons.chevron_up|safe }}
            <span>Parent Directory</span>
        </a>
        {% endif %}

        {% if not dirs and not files %}
        <div class="empty-state">
            <p>This folder is empty</p>
        </div>
        {% else %}
        <div class="file-list">
            {% for d in dirs %}
            <div class="file-item" onclick="location.href='/browse/{{ d.path }}'">
                <div class="file-icon">{{ icons[d.icon]|safe }}</div>
                <div class="file-info">
                    <div class="file-name">{{ d.name }}</div>
                    <div class="file-meta">
                        <span>Folder</span>
                        <span>{{ d.date }}</span>
                    </div>
                </div>
            </div>
            {% endfor %}

            {% for f in files %}
            <div class="file-item" onclick="{% if f.previewable %}previewFile('{{ f.path }}', '{{ f.preview_type }}'){% endif %}">
                <div class="file-icon">{{ icons[f.icon]|safe }}</div>
                <div class="file-info">
                    <div class="file-name">{{ f.name }}</div>
                    <div class="file-meta">
                        <span>{{ f.size }}</span>
                        <span>{{ f.date }}</span>
                    </div>
                </div>
                <div class="file-actions">
                    {% if f.previewable %}
                    <button class="btn btn-icon btn-sm" onclick="event.stopPropagation(); previewFile('{{ f.path }}', '{{ f.preview_type }}')" title="Preview">
                        {{ icons.eye|safe }}
                    </button>
                    {% endif %}
                    <a class="btn btn-icon btn-sm" href="/download/{{ f.path }}" onclick="event.stopPropagation()" title="Download">
                        {{ icons.download|safe }}
                    </a>
                </div>
            </div>
            {% endfor %}
        </div>
        {% endif %}
    </div>

    <!-- QR Modal -->
    <div class="modal" id="qrModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>Connect via QR</h3>
                <button class="btn btn-icon btn-sm" onclick="closeModal('qrModal')">{{ icons.x|safe }}</button>
            </div>
            <div class="qr-container">
                <img src="https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={{ server_url }}" alt="QR Code">
                <div class="qr-url">{{ server_url }}</div>
            </div>
        </div>
    </div>

    <!-- New Folder Modal -->
    <div class="modal" id="folderModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>New Folder</h3>
                <button class="btn btn-icon btn-sm" onclick="closeModal('folderModal')">{{ icons.x|safe }}</button>
            </div>
            <form onsubmit="createFolder(event)">
                <div class="form-group">
                    <label>Folder Name</label>
                    <input type="text" id="folderName" placeholder="Enter folder name..." required autocomplete="off">
                </div>
                <button type="submit" class="btn btn-primary" style="width: 100%;">Create</button>
            </form>
        </div>
    </div>

    <!-- Preview Modal -->
    <div class="modal preview-modal" id="previewModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3 id="previewTitle">Preview</h3>
                <button class="btn btn-icon btn-sm" onclick="closeModal('previewModal')">{{ icons.x|safe }}</button>
            </div>
            <div class="preview-content" id="previewContainer"></div>
        </div>
    </div>

    <div class="toast-container" id="toastContainer"></div>

    <script>
        const currentPath = "{{ current_raw }}";

        function toggleTheme() {
            const html = document.documentElement;
            const isDark = html.classList.toggle('dark');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
        }

        function showToast(message) {
            const container = document.getElementById('toastContainer');
            const toast = document.createElement('div');
            toast.className = 'toast';
            toast.textContent = message;
            container.appendChild(toast);
            setTimeout(() => toast.remove(), 3000);
        }

        function showQR() { document.getElementById('qrModal').classList.add('active'); }
        function showNewFolder() {
            document.getElementById('folderModal').classList.add('active');
            document.getElementById('folderName').focus();
        }
        function closeModal(id) { document.getElementById(id).classList.remove('active'); }

        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(modal.id); });
        });

        async function createFolder(e) {
            e.preventDefault();
            const name = document.getElementById('folderName').value;
            const res = await fetch('/api/mkdir', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({path: currentPath, name: name})
            });
            if (res.ok) {
                showToast('Folder created');
                setTimeout(() => location.reload(), 300);
            } else {
                const data = await res.json();
                showToast(data.error || 'Error');
            }
            closeModal('folderModal');
        }

        async function previewFile(path, type) {
            const modal = document.getElementById('previewModal');
            const container = document.getElementById('previewContainer');
            const title = document.getElementById('previewTitle');
            title.textContent = decodeURIComponent(path.split('/').pop());

            if (type === 'image') {
                container.innerHTML = '<img src="/raw/' + path + '" alt="preview">';
            } else if (type === 'video') {
                container.innerHTML = '<video controls autoplay><source src="/raw/' + path + '"></video>';
            } else if (type === 'audio') {
                container.innerHTML = '<audio controls autoplay style="width:100%"><source src="/raw/' + path + '"></audio>';
            } else {
                const res = await fetch('/raw/' + path);
                const text = await res.text();
                container.innerHTML = '<pre>' + escapeHtml(text.substring(0, 50000)) + '</pre>';
            }
            modal.classList.add('active');
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Upload
        const uploadZone = document.getElementById('uploadZone');
        const fileInput = document.getElementById('fileInput');
        const progressBar = document.getElementById('progressBar');
        const progressFill = document.getElementById('progressFill');

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(e => {
            uploadZone.addEventListener(e, (ev) => { ev.preventDefault(); ev.stopPropagation(); });
        });
        ['dragenter', 'dragover'].forEach(e => {
            uploadZone.addEventListener(e, () => uploadZone.classList.add('dragover'));
        });
        ['dragleave', 'drop'].forEach(e => {
            uploadZone.addEventListener(e, () => uploadZone.classList.remove('dragover'));
        });

        uploadZone.addEventListener('drop', (e) => uploadFiles(e.dataTransfer.files));
        fileInput.addEventListener('change', (e) => uploadFiles(e.target.files));

        async function uploadFiles(files) {
            if (files.length === 0) return;
            progressBar.classList.add('active');
            let uploaded = 0;

            for (const file of files) {
                const formData = new FormData();
                formData.append('file', file);
                formData.append('path', currentPath);
                try {
                    await fetch('/upload', { method: 'POST', body: formData });
                    uploaded++;
                    progressFill.style.width = (uploaded / files.length * 100) + '%';
                } catch (err) {
                    showToast('Failed: ' + file.name);
                }
            }
            showToast(uploaded + ' file(s) uploaded');
            setTimeout(() => {
                progressBar.classList.remove('active');
                progressFill.style.width = '0%';
                location.reload();
            }, 500);
        }

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') document.querySelectorAll('.modal.active').forEach(m => m.classList.remove('active'));
        });
    </script>
</body>
</html>
"""

def safe_join(path):
    """Safely join path to prevent directory traversal"""
    full = os.path.realpath(os.path.join(ROOT_DIR, path))
    if not full.startswith(os.path.realpath(ROOT_DIR)):
        abort(403)
    return full

def get_breadcrumbs(path):
    """Generate breadcrumb navigation"""
    if not path:
        return []
    parts = path.split('/')
    breadcrumbs = []
    for i, part in enumerate(parts):
        if part:
            breadcrumbs.append({
                'name': part,
                'path': quote('/'.join(parts[:i+1]), safe='')
            })
    return breadcrumbs

@app.route("/login", methods=["GET"])
def login():
    if not require_auth():
        return redirect('/')
    return render_template_string(AUTH_TEMPLATE)

@app.route("/auth", methods=["POST"])
def auth():
    data = request.get_json()
    code = data.get('code', '')
    if code == SESSION_CODE:
        session['authenticated'] = True
        return jsonify({"success": True})
    return jsonify({"error": "Invalid code"}), 401

@app.route("/", methods=["GET"])
def home():
    if require_auth():
        return redirect('/login')
    return browse("")

@app.route("/browse/<path:path>", methods=["GET"])
@app.route("/browse", defaults={"path": ""}, methods=["GET"])
def browse(path):
    if require_auth():
        return redirect('/login')
    path = unquote(path)
    full = safe_join(path)

    if not os.path.isdir(full):
        abort(404)

    items = os.listdir(full)
    dirs = []
    files = []

    for item in items:
        if not SHOW_HIDDEN and item.startswith('.'):
            continue

        item_path = os.path.join(full, item)
        rel_path = os.path.join(path, item) if path else item

        try:
            stat = os.stat(item_path)
            date = datetime.fromtimestamp(stat.st_mtime).strftime('%b %d, %Y')

            if os.path.isdir(item_path):
                dirs.append({
                    "name": item,
                    "path": quote(rel_path, safe=''),
                    "icon": get_file_icon(item, is_dir=True),
                    "date": date
                })
            else:
                files.append({
                    "name": item,
                    "path": quote(rel_path, safe=''),
                    "icon": get_file_icon(item),
                    "size": format_size(stat.st_size),
                    "date": date,
                    "previewable": is_previewable(item),
                    "preview_type": get_preview_type(item)
                })
        except OSError:
            continue

    dirs.sort(key=lambda x: x['name'].lower())
    files.sort(key=lambda x: x['name'].lower())

    parent = os.path.dirname(path) if path else None

    local_ip = get_local_ip()
    port = request.host.split(':')[-1] if ':' in request.host else '80'
    server_url = f"http://{local_ip}:{port}"

    # Prepare icons dict for template
    icons_dict = {k.replace('-', '_'): v for k, v in ICONS.items()}

    return render_template_string(
        TEMPLATE,
        current=path if path else "/",
        current_raw=path,
        parent=quote(parent, safe='') if parent is not None else None,
        breadcrumbs=get_breadcrumbs(path),
        dirs=dirs,
        files=files,
        server_url=server_url,
        icons=icons_dict
    )

@app.route("/upload", methods=["POST"])
def upload():
    if require_auth():
        return jsonify({"error": "Unauthorized"}), 401
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400

    file = request.files["file"]
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    rel = request.form.get("path", "")
    full = safe_join(rel)

    filename = os.path.basename(file.filename)
    save_path = os.path.join(full, filename)
    file.save(save_path)
    return jsonify({"success": True, "filename": filename})

@app.route("/download/<path:path>")
def download(path):
    if require_auth():
        return redirect('/login')
    path = unquote(path)
    full = safe_join(path)
    if not os.path.isfile(full):
        abort(404)
    return send_file(full, as_attachment=True)

@app.route("/raw/<path:path>")
def raw(path):
    if require_auth():
        return redirect('/login')
    path = unquote(path)
    full = safe_join(path)
    if not os.path.isfile(full):
        abort(404)
    mime = mimetypes.guess_type(full)[0] or 'application/octet-stream'
    return send_file(full, mimetype=mime)

@app.route("/api/mkdir", methods=["POST"])
def mkdir():
    if require_auth():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    path = data.get('path', '')
    name = data.get('name', '')

    if not name:
        return jsonify({"error": "Name required"}), 400
    if '/' in name or '\\' in name or '..' in name:
        return jsonify({"error": "Invalid name"}), 400

    full = safe_join(os.path.join(path, name))
    if os.path.exists(full):
        return jsonify({"error": "Already exists"}), 400

    try:
        os.makedirs(full)
        return jsonify({"success": True})
    except OSError as e:
        return jsonify({"error": str(e)}), 500


__version__ = "1.2.0"

def main():
    global ROOT_DIR, SHOW_HIDDEN, SESSION_CODE

    parser = argparse.ArgumentParser(
        prog='filesh',
        description='Simple and modern LAN file sharing server with web UI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  filesh                    Share current directory on port 8080
  filesh -p 3000            Use port 3000
  filesh ~/Downloads        Share Downloads folder
  filesh -p 3000 ~/Music    Share Music on port 3000
  filesh --hidden           Show hidden files

"""
    )

    parser.add_argument('directory', nargs='?', default=os.getcwd(),
                        help='Directory to share (default: current directory)')
    parser.add_argument('-p', '--port', type=int, default=8080,
                        help='Port to run server on (default: 8080)')
    parser.add_argument('-H', '--host', default='0.0.0.0',
                        help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--hidden', action='store_true',
                        help='Show hidden files')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Quiet mode - minimal output')
    parser.add_argument('-v', '--version', action='version',
                        version=f'%(prog)s {__version__}')

    args = parser.parse_args()

    ROOT_DIR = os.path.realpath(os.path.expanduser(args.directory))
    SHOW_HIDDEN = args.hidden

    if not os.path.isdir(ROOT_DIR):
        print(f"Error: '{ROOT_DIR}' is not a valid directory")
        sys.exit(1)

    # Generate session code and set secret key
    SESSION_CODE = generate_session_code()
    app.secret_key = secrets.token_hex(32)

    local_ip = get_local_ip()

    if not args.quiet:
        network_url = f"http://{local_ip}:{args.port}"

        print()
        print(f"  filesh v{__version__}")
        print()
        print(f"  Local:   http://127.0.0.1:{args.port}")
        print(f"  Network: {network_url}")
        print()
        print(f"  Access Code: {SESSION_CODE}")
        print()

        # Generate QR code for terminal
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=1
        )
        qr.add_data(network_url)
        qr.make(fit=True)

        # Print QR code
        print("  Scan to connect:")
        qr.print_ascii(invert=True)
        print()
        print(f"  Ctrl+C to stop")
        print()

    # Suppress Flask's default output
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    app.run(host=args.host, port=args.port, debug=False, threaded=True)

if __name__ == "__main__":
    main()
