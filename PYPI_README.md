# filesh

Simple and modern LAN file sharing server with a beautiful web UI.

Share files and folders across your local network with ease. Just run `filesh` and access from any device on the same network.

**[Screenshots available on GitHub](https://github.com/kutaykoca/filesh#screenshots)**

## Features

- **Modern Web UI** - Clean, responsive interface with light/dark mode
- **Drag & Drop Upload** - Simply drag files to upload
- **Multi-file Upload** - Upload multiple files at once with progress bar
- **File Preview** - Preview images, videos, audio, and text files
- **QR Code** - Scan to connect from mobile devices instantly
- **Create Folders** - Organize files by creating new folders
- **Delete Files** - Remove files and folders from the web interface
- **File Icons** - Distinct icons for different file types
- **Cross-platform** - Works on Windows, macOS, and Linux

## Installation

```bash
pip install filesh
```

## Usage

```bash
# Share current directory
filesh

# Share on a different port
filesh -p 3000

# Share a specific folder
filesh ~/Downloads

# Show hidden files
filesh --hidden
```

### Options

```
filesh [OPTIONS] [DIRECTORY]

  -p, --port PORT    Port (default: 8080)
  -H, --host HOST    Host (default: 0.0.0.0)
  --hidden           Show hidden files
  -q, --quiet        Quiet mode
  -v, --version      Show version
  -h, --help         Show help
```

## Requirements

- Python 3.8+
- Flask 2.0+

## License

MIT License

## Links

- [GitHub](https://github.com/kutaykoca/filesh)
- [Issues](https://github.com/kutaykoca/filesh/issues)
