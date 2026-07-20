# core/process_definitions.py
"""
Process Definitions Database
Contains descriptions and information about common processes
"""

PROCESS_DEFINITIONS = {
    # Browsers
    'chrome.exe': {
        'full_name': 'Google Chrome',
        'category': 'Web Browser',
        'description': 'Google Chrome is a cross-platform web browser developed by Google. Known for high RAM usage due to multi-process architecture.',
        'purpose': 'Web browsing, running web applications',
        'normal_behavior': 'High RAM usage (200-2000MB), moderate CPU usage',
        'warning': 'Each tab runs as separate process. Mocny Rywal - consumes significant RAM!',
        'developer': 'Google LLC'
    },
    'firefox.exe': {
        'full_name': 'Mozilla Firefox',
        'category': 'Web Browser',
        'description': 'Mozilla Firefox is a free and open-source web browser developed by the Mozilla Foundation.',
        'purpose': 'Web browsing with focus on privacy',
        'normal_behavior': 'Moderate RAM usage (150-1000MB), low-moderate CPU',
        'warning': 'Mocny Rywal - multiple processes for tabs and extensions',
        'developer': 'Mozilla Foundation'
    },
    'msedge.exe': {
        'full_name': 'Microsoft Edge',
        'category': 'Web Browser',
        'description': 'Microsoft Edge is a Chromium-based web browser developed by Microsoft.',
        'purpose': 'Web browsing, integrated with Windows',
        'normal_behavior': 'High RAM usage (similar to Chrome)',
        'warning': 'Mocny Rywal - Chromium-based architecture',
        'developer': 'Microsoft Corporation'
    },

    # Development Tools
    'code.exe': {
        'full_name': 'Visual Studio Code',
        'category': 'Development Tool',
        'description': 'VS Code is a source-code editor developed by Microsoft. Built on Electron framework.',
        'purpose': 'Code editing, development, debugging',
        'normal_behavior': 'Moderate RAM (200-800MB), low-moderate CPU',
        'warning': 'Can use significant RAM with many extensions',
        'developer': 'Microsoft Corporation'
    },
    'devenv.exe': {
        'full_name': 'Visual Studio IDE',
        'category': 'Development Tool',
        'description': 'Microsoft Visual Studio integrated development environment.',
        'purpose': 'Full-featured IDE for .NET and C++ development',
        'normal_behavior': 'High RAM usage (500-2000MB), moderate CPU',
        'warning': 'Resource-intensive application',
        'developer': 'Microsoft Corporation'
    },

    # System Processes
    'explorer.exe': {
        'full_name': 'Windows Explorer',
        'category': 'System Process',
        'description': 'Windows Explorer provides the Windows desktop environment, taskbar, and file management.',
        'purpose': 'Desktop shell and file explorer',
        'normal_behavior': 'Low RAM (50-200MB), minimal CPU',
        'warning': 'CRITICAL PROCESS - Do not terminate!',
        'developer': 'Microsoft Corporation'
    },
    'dwm.exe': {
        'full_name': 'Desktop Window Manager',
        'category': 'System Process',
        'description': 'DWM manages visual effects, animations, and desktop composition in Windows.',
        'purpose': 'Graphics rendering and window management',
        'normal_behavior': 'Low-moderate RAM (50-150MB), low CPU (0-5%)',
        'warning': 'CRITICAL - Handles Aero effects and transparency',
        'developer': 'Microsoft Corporation'
    },
    'system': {
        'full_name': 'System',
        'category': 'System Process',
        'description': 'Core Windows system process managing kernel-mode drivers and system threads.',
        'purpose': 'System-level operations',
        'normal_behavior': 'Low RAM, very low CPU unless I/O operations',
        'warning': 'CRITICAL SYSTEM PROCESS - Never terminate!',
        'developer': 'Microsoft Corporation'
    },
    'svchost.exe': {
        'full_name': 'Service Host',
        'category': 'System Process',
        'description': 'Generic host process for Windows services. Multiple instances normal.',
        'purpose': 'Hosts multiple Windows services',
        'normal_behavior': 'Variable - depends on hosted services',
        'warning': 'CRITICAL - Multiple instances are normal',
        'developer': 'Microsoft Corporation'
    },

    # Communication
    'discord.exe': {
        'full_name': 'Discord',
        'category': 'Communication',
        'description': 'Discord is a VoIP and instant messaging platform. Built on Electron.',
        'purpose': 'Voice chat, messaging, streaming',
        'normal_behavior': 'Moderate RAM (150-400MB), low-moderate CPU',
        'warning': 'Can use significant resources during voice/video calls',
        'developer': 'Discord Inc.'
    },
    'teams.exe': {
        'full_name': 'Microsoft Teams',
        'category': 'Communication',
        'description': 'Microsoft Teams is a collaboration and communication platform.',
        'purpose': 'Video meetings, chat, collaboration',
        'normal_behavior': 'High RAM (300-800MB), moderate CPU',
        'warning': 'Resource-intensive, especially during video calls',
        'developer': 'Microsoft Corporation'
    },

    # Gaming
    'steam.exe': {
        'full_name': 'Steam Client',
        'category': 'Gaming Platform',
        'description': 'Steam is a digital distribution platform for video games.',
        'purpose': 'Game library, downloads, community features',
        'normal_behavior': 'Moderate RAM (100-400MB), low CPU',
        'warning': 'Can use significant bandwidth when downloading',
        'developer': 'Valve Corporation'
    },

    # ── Additional browsers ───────────────────────────────────────────────────
    'brave.exe': {
        'full_name': 'Brave Browser',
        'category': 'Web Browser',
        'description': 'Chromium-based browser with built-in ad and tracker blocking. Fast and privacy-focused.',
        'purpose': 'Privacy-first web browsing',
        'normal_behavior': 'Moderate RAM (150-600MB), lower than Chrome due to less tracking',
        'warning': 'Chromium-based - still RAM-hungry with many tabs',
        'developer': 'Brave Software Inc.'
    },
    'vivaldi.exe': {
        'full_name': 'Vivaldi Browser',
        'category': 'Web Browser',
        'description': 'Feature-rich Chromium browser with tab stacking, split view, and extensive customization.',
        'purpose': 'Power-user web browsing with advanced tab management',
        'normal_behavior': 'Moderate-high RAM (200-700MB)',
        'warning': 'Slightly more RAM than Chrome due to extra UI features',
        'developer': 'Vivaldi Technologies'
    },
    'opera.exe': {
        'full_name': 'Opera Browser',
        'category': 'Web Browser',
        'description': 'Chromium-based browser with a built-in VPN, ad blocker, and sidebar apps.',
        'purpose': 'Web browsing with integrated tools',
        'normal_behavior': 'Moderate RAM (150-500MB)',
        'warning': 'Free built-in VPN is limited - not a full privacy solution',
        'developer': 'Opera Software AS'
    },
    # ── Communication (extended) ──────────────────────────────────────────────
    'slack.exe': {
        'full_name': 'Slack',
        'category': 'Communication',
        'description': 'Team messaging and collaboration platform built on Electron. Popular in workplaces.',
        'purpose': 'Team communication, channels, file sharing',
        'normal_behavior': 'High RAM (200-600MB), low-moderate CPU',
        'warning': 'Electron-based - high RAM usage. Can slow down on older machines.',
        'developer': 'Salesforce (Slack Technologies)'
    },
    'zoom.exe': {
        'full_name': 'Zoom',
        'category': 'Communication',
        'description': 'Video conferencing platform. Became dominant during the pandemic era.',
        'purpose': 'Video meetings, webinars, screen sharing',
        'normal_behavior': 'Moderate-high RAM (150-500MB), CPU spikes during video',
        'warning': 'High CPU usage during video calls, especially with virtual backgrounds',
        'developer': 'Zoom Video Communications'
    },
    'telegram.exe': {
        'full_name': 'Telegram Desktop',
        'category': 'Communication',
        'description': 'Fast cloud-based messaging app with large group support and file sharing.',
        'purpose': 'Secure messaging, channels, bots',
        'normal_behavior': 'Low-moderate RAM (80-200MB), low CPU',
        'warning': 'Default chats are NOT end-to-end encrypted. Use Secret Chats for E2E.',
        'developer': 'Telegram FZ-LLC'
    },
    'whatsapp.exe': {
        'full_name': 'WhatsApp Desktop',
        'category': 'Communication',
        'description': 'Official WhatsApp desktop client. Mirrors your phone account.',
        'purpose': 'Personal and group messaging, calls',
        'normal_behavior': 'Moderate RAM (100-300MB)',
        'warning': 'Requires active phone connection',
        'developer': 'Meta Platforms Inc.'
    },
    'skype.exe': {
        'full_name': 'Skype',
        'category': 'Communication',
        'description': 'Veteran video and voice calling application. Mostly superseded by Teams.',
        'purpose': 'Video calls, messaging',
        'normal_behavior': 'Moderate RAM (150-400MB)',
        'warning': 'Being phased out in favor of Microsoft Teams for business',
        'developer': 'Microsoft Corporation'
    },
    'signal.exe': {
        'full_name': 'Signal Desktop',
        'category': 'Communication',
        'description': 'End-to-end encrypted instant messenger. Gold standard for private communications.',
        'purpose': 'Secure private messaging and calls',
        'normal_behavior': 'Low RAM (80-200MB), low CPU',
        'warning': None,
        'developer': 'Signal Foundation (non-profit)'
    },
    # ── Security / Antivirus ──────────────────────────────────────────────────
    'msmpeng.exe': {
        'full_name': 'Microsoft Defender Antimalware Service',
        'category': 'Security',
        'description': 'Core process of Windows Defender antivirus. Scans files in real-time.',
        'purpose': 'Real-time malware protection',
        'normal_behavior': 'Low idle CPU, spikes during scans (10-60%)',
        'warning': 'Scheduled scans can cause high CPU spikes. Exclude game/dev folders if needed.',
        'developer': 'Microsoft Corporation'
    },
    'securityhealthsystray.exe': {
        'full_name': 'Windows Security Health Tray',
        'category': 'Security',
        'description': 'Windows Security Center tray icon and notification process.',
        'purpose': 'Security status monitoring and alerts',
        'normal_behavior': 'Very low resource usage',
        'warning': None,
        'developer': 'Microsoft Corporation'
    },
    'malwarebytes.exe': {
        'full_name': 'Malwarebytes',
        'category': 'Security',
        'description': 'Anti-malware tool complementing Windows Defender. Specializes in PUPs and adware.',
        'purpose': 'Malware detection and removal',
        'normal_behavior': 'Low idle, moderate CPU during scans',
        'warning': 'Free version does not offer real-time protection',
        'developer': 'Malwarebytes Inc.'
    },
    'bitwarden.exe': {
        'full_name': 'Bitwarden',
        'category': 'Security',
        'description': 'Open-source password manager. Stores credentials securely with end-to-end encryption.',
        'purpose': 'Password management and autofill',
        'normal_behavior': 'Very low RAM (80-160MB) and CPU',
        'warning': None,
        'developer': 'Bitwarden Inc.'
    },
    # ── Development (extended) ────────────────────────────────────────────────
    'python.exe': {
        'full_name': 'Python Interpreter',
        'category': 'Development Tool',
        'description': 'Python programming language interpreter running scripts and applications.',
        'purpose': 'Running Python scripts, applications, automation',
        'normal_behavior': 'Variable - depends entirely on the script being run',
        'warning': 'Multiple instances indicate multiple scripts running simultaneously',
        'developer': 'Python Software Foundation'
    },
    'node.exe': {
        'full_name': 'Node.js',
        'category': 'Development Tool',
        'description': 'Node.js JavaScript runtime. Powers many web development tools and servers.',
        'purpose': 'Running JavaScript outside the browser',
        'normal_behavior': 'Variable RAM (50-500MB depending on app)',
        'warning': 'Multiple instances are normal for development workflows',
        'developer': 'OpenJS Foundation'
    },
    'git.exe': {
        'full_name': 'Git Version Control',
        'category': 'Development Tool',
        'description': 'Git is the most widely used distributed version control system.',
        'purpose': 'Source code versioning and collaboration',
        'normal_behavior': 'Short-lived processes, very low resource usage',
        'warning': 'Rebase/merge on large repos can spike CPU briefly',
        'developer': 'Linus Torvalds / Git SCM'
    },
    'godot.exe': {
        'full_name': 'Godot Engine 3',
        'category': 'Development Tool',
        'description': 'Open-source 2D/3D game engine editor. Free alternative to Unity/Unreal.',
        'purpose': 'Game development and prototyping',
        'normal_behavior': 'Moderate RAM (200-800MB), CPU spikes during export',
        'warning': None,
        'developer': 'Godot Engine Community'
    },
    'godot4.exe': {
        'full_name': 'Godot Engine 4',
        'category': 'Development Tool',
        'description': 'Godot 4.x with Vulkan rendering, improved 3D, and new scripting system.',
        'purpose': 'Modern game development with Vulkan graphics',
        'normal_behavior': 'High RAM (300-1200MB), high GPU usage in editor',
        'warning': 'Vulkan-only - requires modern GPU with updated drivers',
        'developer': 'Godot Engine Community'
    },
    'unreal.exe': {
        'full_name': 'Unreal Editor',
        'category': 'Development Tool',
        'description': 'Unreal Engine full editor. Used for AAA games, films and virtual production.',
        'purpose': 'Professional game and real-time 3D development',
        'normal_behavior': 'Very high RAM (4-16GB), high CPU+GPU during builds',
        'warning': 'Shader compilation on first run can take hours and max out CPU',
        'developer': 'Epic Games'
    },
    # ── Media & Creative ──────────────────────────────────────────────────────
    'vlc.exe': {
        'full_name': 'VLC Media Player',
        'category': 'Media Player',
        'description': 'Free and open-source cross-platform multimedia player. Plays almost any format.',
        'purpose': 'Video and audio playback',
        'normal_behavior': 'Low-moderate RAM (50-250MB), depends on codec/resolution',
        'warning': None,
        'developer': 'VideoLAN'
    },
    'obs64.exe': {
        'full_name': 'OBS Studio',
        'category': 'Media Creation',
        'description': 'Free open-source screen recording and live streaming software.',
        'purpose': 'Game/screen streaming and recording',
        'normal_behavior': 'High CPU (10-40%+), significant GPU usage during encoding',
        'warning': 'Use GPU encoding (NVENC/AMF) instead of x264 to reduce CPU load',
        'developer': 'OBS Project'
    },
    'gimp-2.10.exe': {
        'full_name': 'GIMP - GNU Image Manipulation Program',
        'category': 'Image Editing',
        'description': 'Free and open-source raster image editor. Alternative to Photoshop.',
        'purpose': 'Photo editing, retouching, compositing',
        'normal_behavior': 'Moderate RAM (100-500MB), high CPU during filters',
        'warning': 'Single-threaded for most operations - can feel slow on large files',
        'developer': 'GNOME Project'
    },
    'photoshop.exe': {
        'full_name': 'Adobe Photoshop',
        'category': 'Image Editing',
        'description': 'Industry-standard raster image editor by Adobe.',
        'purpose': 'Professional photo editing and graphic design',
        'normal_behavior': 'High RAM (500-2000MB), moderate-high CPU',
        'warning': 'Allocates large scratch disk space - ensure sufficient free storage',
        'developer': 'Adobe Inc.'
    },
    'krita.exe': {
        'full_name': 'Krita',
        'category': 'Image Editing',
        'description': 'Professional free and open-source digital painting application. Great for concept art.',
        'purpose': 'Digital painting, concept art, comic creation',
        'normal_behavior': 'Moderate RAM (100-600MB), GPU-accelerated canvas',
        'warning': None,
        'developer': 'Krita Foundation'
    },
    'blender.exe': {
        'full_name': 'Blender',
        'category': '3D/Animation',
        'description': 'Free open-source 3D creation suite for modeling, animation, VFX and game assets.',
        'purpose': '3D modeling, animation, rendering, video editing',
        'normal_behavior': 'High RAM (500-4000MB), very high CPU/GPU during rendering',
        'warning': 'Rendering can max out CPU and GPU for extended periods',
        'developer': 'Blender Foundation'
    },
    'premiere.exe': {
        'full_name': 'Adobe Premiere Pro',
        'category': 'Video Editing',
        'description': 'Industry-standard professional video editing software.',
        'purpose': 'Professional video editing and color grading',
        'normal_behavior': 'Very high RAM (1-4GB), high GPU for preview rendering',
        'warning': 'Media cache can grow very large - clear periodically',
        'developer': 'Adobe Inc.'
    },
    'resolve.exe': {
        'full_name': 'DaVinci Resolve',
        'category': 'Video Editing',
        'description': 'Professional color grading and video editing software. Free version is powerful.',
        'purpose': 'Video editing, color correction, audio post-production',
        'normal_behavior': 'Very high RAM (2-8GB), GPU-intensive',
        'warning': 'Requires dedicated GPU for smooth performance - integrated graphics not ideal',
        'developer': 'Blackmagic Design'
    },
    'audacity.exe': {
        'full_name': 'Audacity',
        'category': 'Audio Editing',
        'description': 'Free open-source audio editor for recording and post-production.',
        'purpose': 'Audio recording, editing, effects processing',
        'normal_behavior': 'Low-moderate RAM (50-300MB), moderate CPU during effects',
        'warning': None,
        'developer': 'Audacity Community'
    },
    # ── Cloud & Storage ───────────────────────────────────────────────────────
    'onedrive.exe': {
        'full_name': 'Microsoft OneDrive',
        'category': 'Cloud Storage',
        'description': 'Microsoft cloud storage client syncing files between PC and cloud.',
        'purpose': 'File sync and backup to Microsoft cloud',
        'normal_behavior': 'Low idle RAM (50-150MB), CPU spikes during sync',
        'warning': 'Can slow down PC significantly when syncing large files in background',
        'developer': 'Microsoft Corporation'
    },
    'dropbox.exe': {
        'full_name': 'Dropbox',
        'category': 'Cloud Storage',
        'description': 'Cross-platform cloud file storage and sharing service.',
        'purpose': 'File sync and sharing',
        'normal_behavior': 'Moderate RAM (100-300MB)',
        'warning': 'Can consume significant bandwidth during sync',
        'developer': 'Dropbox Inc.'
    },
    'googledrivefs.exe': {
        'full_name': 'Google Drive File Stream',
        'category': 'Cloud Storage',
        'description': 'Google Drive client that streams files on demand.',
        'purpose': 'Access Google Drive files locally',
        'normal_behavior': 'Moderate RAM (100-300MB)',
        'warning': 'Requires internet connection for non-cached files',
        'developer': 'Google LLC'
    },
    # ── Productivity ──────────────────────────────────────────────────────────
    'outlook.exe': {
        'full_name': 'Microsoft Outlook',
        'category': 'Productivity',
        'description': 'Microsoft email client and personal information manager.',
        'purpose': 'Email, calendar, contacts, tasks',
        'normal_behavior': 'High RAM (300-800MB), moderate CPU during indexing',
        'warning': 'OST file can grow very large - can slow down if over 20GB',
        'developer': 'Microsoft Corporation'
    },
    'winword.exe': {
        'full_name': 'Microsoft Word',
        'category': 'Productivity',
        'description': 'Microsoft Word word processing application.',
        'purpose': 'Document creation, editing, formatting',
        'normal_behavior': 'Moderate RAM (100-500MB)',
        'warning': 'Large documents with many images can be RAM-intensive',
        'developer': 'Microsoft Corporation'
    },
    'excel.exe': {
        'full_name': 'Microsoft Excel',
        'category': 'Productivity',
        'description': 'Microsoft Excel spreadsheet application. Used for data analysis and modeling.',
        'purpose': 'Spreadsheets, data analysis, charts',
        'normal_behavior': 'Moderate RAM (100-500MB), CPU spikes on complex formulas',
        'warning': 'Complex macros and pivot tables on large datasets can be very CPU intensive',
        'developer': 'Microsoft Corporation'
    },
    'powerpnt.exe': {
        'full_name': 'Microsoft PowerPoint',
        'category': 'Productivity',
        'description': 'Microsoft PowerPoint presentation software.',
        'purpose': 'Creating and presenting slide decks',
        'normal_behavior': 'Moderate RAM (100-400MB)',
        'warning': 'Presentations with many animations and embedded videos use more RAM',
        'developer': 'Microsoft Corporation'
    },
    'notion.exe': {
        'full_name': 'Notion',
        'category': 'Productivity',
        'description': 'All-in-one workspace for notes, databases, tasks, and wikis. Electron-based.',
        'purpose': 'Note-taking, project management, knowledge base',
        'normal_behavior': 'Moderate RAM (200-500MB)',
        'warning': 'Electron-based - higher RAM than a native app. Slow to load with many pages.',
        'developer': 'Notion Labs Inc.'
    },
    'obsidian.exe': {
        'full_name': 'Obsidian',
        'category': 'Productivity',
        'description': 'Knowledge base app using linked Markdown files stored locally. Fast and private.',
        'purpose': 'Personal knowledge management and note-taking',
        'normal_behavior': 'Low-moderate RAM (80-300MB)',
        'warning': None,
        'developer': 'Obsidian.md'
    },
    # ── System monitoring & utilities ─────────────────────────────────────────
    'taskmgr.exe': {
        'full_name': 'Task Manager',
        'category': 'System Utility',
        'description': 'Windows built-in process and performance monitoring tool.',
        'purpose': 'Monitoring processes, ending tasks, viewing performance',
        'normal_behavior': 'Low resource usage',
        'warning': None,
        'developer': 'Microsoft Corporation'
    },
    'powershell.exe': {
        'full_name': 'Windows PowerShell',
        'category': 'System Utility',
        'description': 'Advanced command-line shell and scripting language for Windows.',
        'purpose': 'System administration, scripting, automation',
        'normal_behavior': 'Low idle RAM (30-100MB), variable CPU during scripts',
        'warning': 'Malware sometimes uses PowerShell. Obfuscated commands are a red flag.',
        'developer': 'Microsoft Corporation'
    },
    'cmd.exe': {
        'full_name': 'Command Prompt',
        'category': 'System Utility',
        'description': 'Windows classic command-line interpreter.',
        'purpose': 'Running commands and batch scripts',
        'normal_behavior': 'Very low resources',
        'warning': None,
        'developer': 'Microsoft Corporation'
    },
    'windowsterminal.exe': {
        'full_name': 'Windows Terminal',
        'category': 'System Utility',
        'description': 'Modern terminal app supporting CMD, PowerShell, WSL and SSH in tabs.',
        'purpose': 'Multi-tab command-line environment',
        'normal_behavior': 'Low-moderate RAM (50-150MB)',
        'warning': None,
        'developer': 'Microsoft Corporation'
    },
    # ── Gaming platforms (extended) ───────────────────────────────────────────
    'epicgameslauncher.exe': {
        'full_name': 'Epic Games Launcher',
        'category': 'Gaming Platform',
        'description': 'Epic Games digital storefront and game launcher. Offers free games weekly.',
        'purpose': 'Game library management and launching',
        'normal_behavior': 'Moderate RAM (200-500MB)',
        'warning': 'Known for slower game launches than Steam. Background resource use.',
        'developer': 'Epic Games Inc.'
    },
    'battlenetlauncher.exe': {
        'full_name': 'Battle.net Launcher',
        'category': 'Gaming Platform',
        'description': 'Blizzard Entertainment game launcher for WoW, Diablo, Overwatch, CoD.',
        'purpose': 'Blizzard game library and updates',
        'normal_behavior': 'Moderate RAM (150-400MB)',
        'warning': None,
        'developer': 'Blizzard Entertainment'
    },
    'valorant-win64-shipping.exe': {
        'full_name': 'Valorant (Game Process)',
        'category': 'Gaming',
        'description': 'Main Valorant game process. Tactical FPS by Riot Games.',
        'purpose': 'Game executable',
        'normal_behavior': 'High GPU, moderate CPU (20-50%), 4-6GB RAM',
        'warning': 'Vanguard anti-cheat runs at kernel level. Starts on boot.',
        'developer': 'Riot Games'
    },
    'cs2.exe': {
        'full_name': 'Counter-Strike 2',
        'category': 'Gaming',
        'description': 'Counter-Strike 2 game process. Rebuilt from scratch on Source 2 engine.',
        'purpose': 'Competitive tactical FPS',
        'normal_behavior': 'Moderate-high GPU, moderate CPU (15-40%), 2-6GB RAM',
        'warning': 'VAC anti-cheat always active. High CPU usage reported in crowded servers.',
        'developer': 'Valve Corporation'
    },
    # ── Default/Unknown ───────────────────────────────────────────────────────
    '_default': {
        'full_name': 'Unknown Process',
        'category': 'Unknown',
        'description': 'This process is not in our database yet.',
        'purpose': 'Unknown - Research recommended',
        'normal_behavior': 'Variable',
        'warning': "If you don't recognize this process, research it online",
        'developer': 'Unknown'
    }
}


def get_process_definition(process_name):
    """
    Get definition for a process

    Args:
        process_name: Process name (e.g., 'chrome.exe')

    Returns:
        dict: Process definition
    """
    process_name = process_name.lower()

    if process_name in PROCESS_DEFINITIONS:
        return PROCESS_DEFINITIONS[process_name]
    else:
        return PROCESS_DEFINITIONS['_default']
