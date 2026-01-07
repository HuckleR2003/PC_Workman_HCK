# Getting Started with PC_Workman

Welcome! This guide covers installation and basic usage.

---

## 🎯 Choose Your Path

### Path 1: "I just want to use it"
→ Go to [Quick Install (Windows .exe)](#quick-install-windows-exe)

### Path 2: "I want to set up from source"
→ Go to [Developer Setup](#developer-setup-from-source)

### Path 3: "I want to understand how it works"
→ Go to [Using PC_Workman](#using-pc_workman)

---

## 🚀 Quick Install (Windows .exe)

**Easiest option. No Python required.**

### Step 1: Download

1. Go to [GitHub Releases](https://github.com/HuckleR2003/PC_Workman_HCK/releases)
2. Find latest release
3. Download `PC_Workman.exe`
4. Wait for download (~100MB)

### Step 2: Run

1. Find downloaded file (usually in Downloads folder)
2. Double-click `PC_Workman.exe`
3. If Windows asks "Allow this app to make changes?" → Click **Yes**
4. PC_Workman opens → **Done!** ✅

### Step 3: First Use

1. Main dashboard appears with empty charts
2. Wait 5-10 seconds for initial data collection
3. CPU/RAM/GPU bars populate
4. Start exploring tabs

**That's it. No setup required.**

---

## 🔧 Developer Setup (From Source)

Use this if you want to:
- Modify the code
- Contribute features
- Run latest development version
- Use custom configurations

### Prerequisites

**Check if you have Python:**
```powershell
python --version
```

Should show: `Python 3.9` or higher

**Don't have Python?**

1. Go to [python.org/downloads](https://www.python.org/downloads)
2. Download "Python 3.12" (latest)
3. **IMPORTANT:** During installation, check "Add Python to PATH"
4. Click Install
5. Restart computer

### Installation Steps

#### 1. Clone Repository
```powershell
git clone https://github.com/HuckleR2003/PC_Workman_HCK.git
cd PC_Workman_HCK
```

(Don't have Git? [Install it](https://git-scm.com/download/win))

#### 2. Create Virtual Environment (Recommended)
```powershell
python -m venv venv
.\venv\Scripts\activate
```

You'll see `(venv)` in terminal = success

#### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

Wait 2-3 minutes for completion.

#### 4. Run Application
```powershell
python startup.py
```

Window opens → **Running!** 🎉

---

## 📖 Using PC_Workman

### Main Dashboard (Default View)

**Top Section:**
- CPU usage bar (blue)
- RAM usage bar (yellow)
- System status indicator
- Current load classification

**Process Lists:**
- **User Processes** (left) - Apps you use
- **System Processes** (right) - Windows background tasks

**Charts:**
- Real-time performance graphs
- Mode selector: NOW, 1H, 4H

### Tabs Explained

#### 📊 Dashboard
Real-time overview. Start here. Shows current metrics and top processes.

#### 💻 Your PC
Hardware health monitoring:
- CPU details (model, cores, speed)
- RAM information (total, available)
- GPU status (if available)
- System temperature and load

#### 🎮 Fan Control
Manual fan curve configuration (advanced users):
1. Click "Custom Curve"
2. Drag points to set temperatures
3. System prevents dangerous settings
4. Save to apply

**For beginners:** Keep default settings.

#### ⚡ Network
Internet usage breakdown:
- See which apps use bandwidth
- Monitor data usage
- Identify resource-heavy applications

#### 🎯 Gaming
Game-specific analytics:
1. Click "Track This Game"
2. PC_Workman records performance while you play
3. View FPS data, thermal impact, bottleneck detection
4. Compare games performance

---

## 🎓 Understanding the Metrics

### CPU (Blue)
- **0-30%** Normal
- **30-60%** Moderate load
- **60-85%** Heavy load
- **85%+** Critical

What to do:
- If consistently high: Close unnecessary apps
- Click process to identify culprit
- Check for background tasks

### RAM (Yellow)
- Similar classifications as CPU
- Shows used vs. available memory
- Includes cached data (often shows as higher than needed)

What to do:
- If near 90%: Consider upgrading or closing apps
- Check Optimize tab for quick fixes
- Restart if very high after reboots

### Temperature
- **Green (<60°C)** Ideal
- **Yellow (60-80°C)** Normal
- **Orange (80-90°C)** Warm
- **Red (>90°C)** Hot - investigate

Normal ranges:
- Idle: 35-50°C
- Gaming: 70-85°C
- If above 95°C: Check fans, thermal paste

---

## ⚙️ Configuration

### Enable Gaming Analytics
```
1. Go to Gaming tab
2. Click "Track This Game"
3. Launch your game
4. PC_Workman records data automatically
```

### Optimize Windows
```
1. Go to Optimization tab
2. Click "Quick Optimize"
3. Or manually select specific optimizations
4. All changes are reversible
```

### Custom Settings

Edit `settings/config.json` for advanced configuration:
- Update intervals
- Data retention periods
- UI preferences
- Alert thresholds

---

## 🆘 Troubleshooting

### "PC_Workman won't start"

**Try:**
1. Close any open instances
2. Restart PC_Workman
3. If still fails: Delete `data/cache/` folder
4. Run again

### "Temperatures showing 0°C"

Normal. Real hardware sensors need admin access.
v1.5.1 adds proper hardware sensor support.

### "GPU not showing data"

Check:
- GPU drivers updated? (NVIDIA/AMD)
- Restart PC_Workman
- Some laptops don't expose GPU data
- Integrated graphics may need special drivers

### "High CPU/RAM with no clear process"

This can happen with:
- System processes (legitimate Windows tasks)
- Short-duration spikes (missed by monitoring)
- Background Windows updates
- Try restarting if excessive

### ".exe won't run"

Try:
1. Run as Administrator (right-click → Run as administrator)
2. Disable antivirus temporarily (some flag new .exe files)
3. Check Windows Defender quarantine
4. Use source installation instead

---

## 📊 Common Tasks

### Task: Check what's using CPU right now
1. Look at "User Processes" list on dashboard
2. Click any process to see details
3. Identify and close if unnecessary

### Task: Monitor while gaming
1. Start game
2. Alt+Tab to PC_Workman (stays running)
3. Watch FPS, temperature, CPU/GPU usage
4. Click "Gaming" tab for game-specific stats

### Task: Find internet hog
1. Go to Network tab
2. See apps sorted by bandwidth
3. Large numbers = heavy usage
4. Can identify streaming/downloading apps

### Task: Optimize startup
1. Go to Optimize tab
2. Click "Startup Programs"
3. Uncheck apps you don't need
4. Restart PC to apply

### Task: Check thermal trends
1. Go to Your PC tab
2. Look at "Temperature History" chart
3. See if temps rising over time
4. If rising: Fans need cleaning, thermal paste drying

---

## 📈 Data Storage

### Where Your Data Lives
```
data/
├── logs/
│   ├── raw_usage.csv          (per-second raw data)
│   ├── minute_avg.csv         (minute averages)
│   ├── hourly_usage.csv       (hourly summary)
│   ├── daily_usage.csv        (daily summary)
│   ├── weekly_usage.csv       (weekly summary)
│   └── monthly_usage.csv      (monthly summary)
└── cache/
    ├── runtime_cache.json     (current session)
    └── process_patterns.json  (identified patterns)
```

### Data Retention
- **Raw data:** Last 7 days
- **Minute averages:** Last 30 days
- **Monthly summaries:** Forever

You can:
- Delete logs anytime
- PC_Workman will start fresh
- Archived data can be backed up

---

## 🔐 Privacy Check

PC_Workman collects:
- ✅ CPU/GPU/RAM usage
- ✅ Process names
- ✅ Temperatures
- ✅ Network usage

PC_Workman does NOT:
- ❌ Send anything to cloud
- ❌ Track user behavior
- ❌ Collect personal data
- ❌ Show ads or telemetry
- ❌ Require account creation

**Everything stays on your computer.** Period.

---

## 🚀 Next Steps

1. **Explore tabs** - Get familiar with interface
2. **Check processes** - See what's actually running
3. **Enable gaming** - If you game, track performance
4. **Customize** - Adjust settings in config.json
5. **Update regularly** - New releases add features

---

## 📚 Need Help?

- **Question?** [Open Discussion](https://github.com/HuckleR2003/PC_Workman_HCK/discussions)
- **Found bug?** [Report Issue](https://github.com/HuckleR2003/PC_Workman_HCK/issues)
- **Want to contribute?** [See CONTRIBUTING.md](./CONTRIBUTING.md)

---

## 📖 Learn More

- **[README.md](./README.md)** - Project overview
- **[CHANGELOG.md](./CHANGELOG.md)** - Version history
- **[docs/TECHNICAL.md](./docs/TECHNICAL.md)** - Architecture details

---

**Happy monitoring!** 💙