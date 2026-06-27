# Privacy Policy

**PC Workman** is a local-first Windows system monitor. Almost everything it does — reading your sensors, learning your hardware's normal behaviour, the hck_GPT assistant, your entire history — happens **on your own machine and never leaves it**.

This page is the complete, honest account of the one thing that *can* leave your device, exactly what it is, why it exists, and how to turn it off. No legalese padding, no hidden clauses.

**Last updated:** June 26, 2026 · **Applies to:** PC Workman v1.8.0 and later

---

## The short version

- **Your data stays local.** System metrics, temperatures, voltages, the process list, learned baselines, chat history and settings live in a SQLite database and JSON files **on your PC**. There is no account, no login, no cloud sync.
- **One optional thing can be sent:** an anonymous **hardware & usage snapshot** — so I can test PC Workman on hardware like yours and fix incompatibilities.
- **It is anonymous:** a random ID, your component *models*, your Windows version, your region (from your language setting, never your IP), the app version, and how long the app was open. **Never** your name, your files, your IP address, or anything you do.
- **You control it.** It can be switched off in **Settings**. With Network Access off, the app makes **zero** outbound connections — you can verify that yourself with a firewall or Wireshark.

---

## What stays on your device (all of it)

None of the following is ever uploaded:

- **System monitoring data** — CPU / GPU / RAM usage, temperatures, voltages, fan speeds.
- **The process list** and everything PC Workman knows about your running programs.
- **Learned data** — thermal baselines per workload, voltage anomaly history, long-term statistics.
- **hck_GPT** — the assistant runs entirely on your machine. There is no external AI API; your questions and conversations are never sent anywhere.
- **Your settings and preferences.**

This data is stored locally (for example the statistics database at `…/data/logs/hck_stats.db`) and is yours alone.

---

## What can be sent: the telemetry snapshot

PC Workman can send a single, small, anonymous snapshot — at most **once per session**, through one network gate. This is the **entire** payload, and nothing else is ever transmitted:

| Field | What it is | Example |
|-------|------------|---------|
| `install_id` | A random ID generated once on your machine. Not linked to you, your name, or any account. | `a1b2c3…` |
| `app_version` | Which version of PC Workman you run | `1.8.0` |
| `os` | Your Windows version and build | `Windows 10 (build 19045)` |
| `country` | A 2-letter region read from your **Windows language setting** — **never** from your IP address | `PL` |
| `cpu`, `cpu_cores` | Your processor **model** and core count | `Intel Core i7-4710HQ`, `4` |
| `gpu` | Your graphics card **model** | `NVIDIA GeForce RTX 3050` |
| `ram_gb`, `ram_mhz` | RAM size and speed | `16`, `2667` |
| `motherboard` | Motherboard make and model | `ASUS PRIME B450M` |
| `disks` | Up to 4 drives: model, size, type (SSD/HDD) | — |
| `session_min` | How many minutes the app was open this run | `42` |
| `ts` | A timestamp | — |

You can see this exact snapshot **verbatim in Settings** before you agree to anything — the same dialog that lets you turn it off.

---

## What is never collected

To be unambiguous, PC Workman **never** collects, sends, or stores any of the following:

- Your name, username, or computer name
- Your email address or any contact details
- Your **IP address** (it is not logged on the receiving end)
- File names, file paths, or file contents
- The names of the **processes or programs** you run
- Keystrokes, screen contents, clipboard, or browsing activity

There are no advertising networks, no third-party analytics SDKs, no tracking pixels, and no fingerprinting beyond the hardware-model fields listed above.

---

## Why the hardware snapshot exists

I build PC Workman alone. As downloads grow, I increasingly get reports of bugs and incompatibilities on hardware I do not own. The component **models** in the snapshot tell me which CPUs, GPUs, RAM kits, motherboards and drives real people actually run PC Workman on — from the oldest machines to the newest — so I can reproduce problems, fix them, and test against real-world configurations.

That is the only purpose. The data is **never sold, never shared for advertising, and never used to build a profile of you.**

---

## Where it goes and who can see it

When sent, the snapshot goes to a **private Cloudflare Worker and storage that only I (Marcin Firmuga / HCK_Labs) can access.** It is not shared with any third party and is used solely for the compatibility and bug-fixing purpose described above.

---

## Your control

- **Default state:** In v1.8.0 the network/telemetry switch is **on by default**. The first time you open the relevant Settings control it explains exactly what is sent and lets you decide.
- **Turning it off:** Open **Settings** and switch **Network Access** off. With it off, PC Workman makes **zero** outbound connections — verifiable with a firewall or Wireshark.
- **Resetting your random ID:** delete `settings/network.json`. A fresh random `install_id` is generated next time (or none at all, if telemetry stays off).
- **Deletion requests:** because the data is anonymous, there is no account to look you up by. If you send me your `install_id`, I can delete the records tied to it.

---

## Data retention

Snapshots are kept only as long as they are useful for compatibility and bug analysis, and are used in aggregate (e.g. "how many users run a given GPU"). No long-term per-user profile is ever built — there is no identity to attach one to.

---

## Children

PC Workman is a developer/enthusiast tool and is not directed at children under 13.

## Changes to this policy

If this policy changes, the updated version will be published here with a new "Last updated" date. Material changes will also be noted in project communications.

## Contact

- **GitHub:** [@HuckleR2003](https://github.com/HuckleR2003) — open an issue or discussion
- **Email:** `firmuga.marcin.s@gmail.com`

---

*PC Workman is open source (MIT). You don't have to take my word for any of this — the code that builds and sends the snapshot lives in `core/telemetry.py` and `core/network.py`, and you can read exactly what it does.*
