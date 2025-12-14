# ui/page_all_stats.py
"""
All Stats Page - Complete Statistics Overview
Shows lifetime statistics with process definitions
"""

import tkinter as tk
from tkinter import ttk, messagebox
from ui.theme import THEME
from core.process_definitions import get_process_definition


class AllStatsPage:
    """Professional All Stats page with process definitions"""

    def __init__(self, parent, data_manager, classifier):
        self.parent = parent
        self.data_manager = data_manager
        self.classifier = classifier
        self.selected_process = None

        # Main frame
        self.frame = tk.Frame(parent, bg=THEME["bg_main"])

        # Build UI
        self._build_ui()

    def _build_ui(self):
        """Build All Stats UI"""
        # Title
        title = tk.Label(
            self.frame,
            text="All-Time Statistics",
            font=("Segoe UI", 16, "bold"),
            bg=THEME["bg_main"],
            fg=THEME["text"],
            anchor="w"
        )
        title.pack(fill="x", padx=20, pady=(15, 5))

        subtitle = tk.Label(
            self.frame,
            text="Lifetime resource usage since first use",
            font=("Segoe UI", 9),
            bg=THEME["bg_main"],
            fg=THEME["muted"],
            anchor="w"
        )
        subtitle.pack(fill="x", padx=20, pady=(0, 15))

        # Content container
        content = tk.Frame(self.frame, bg=THEME["bg_main"])
        content.pack(fill="both", expand=True, padx=20, pady=10)

        # Top section - Summary
        top_section = tk.Frame(content, bg=THEME["bg_panel"], height=100)
        top_section.pack(fill="x", pady=(0, 15))
        top_section.pack_propagate(False)

        self._build_summary(top_section)

        # Bottom section - Process list and details
        bottom_section = tk.Frame(content, bg=THEME["bg_main"])
        bottom_section.pack(fill="both", expand=True)

        # Left - Process list
        left_frame = tk.Frame(bottom_section, bg=THEME["bg_panel"])
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self._build_process_list(left_frame)

        # Right - Process details
        right_frame = tk.Frame(bottom_section, bg=THEME["bg_panel"])
        right_frame.pack(side="right", fill="both", expand=True, padx=(10, 0))

        self._build_process_details(right_frame)

    def _build_summary(self, parent):
        """Build summary statistics"""
        stats_frame = tk.Frame(parent, bg=THEME["bg_panel"])
        stats_frame.pack(fill="both", expand=True, padx=20, pady=15)

        # Total Runtime
        runtime_lbl = tk.Label(
            stats_frame,
            text="Total Monitoring Time:",
            font=("Segoe UI", 10),
            bg=THEME["bg_panel"],
            fg=THEME["text"],
            anchor="w"
        )
        runtime_lbl.grid(row=0, column=0, sticky="w", padx=(0, 20))

        self.runtime_value = tk.Label(
            stats_frame,
            text="0h 0m",
            font=("Segoe UI", 12, "bold"),
            bg=THEME["bg_panel"],
            fg=THEME["accent"],
            anchor="w"
        )
        self.runtime_value.grid(row=0, column=1, sticky="w")

        # Total Processes Tracked
        procs_lbl = tk.Label(
            stats_frame,
            text="Processes Tracked:",
            font=("Segoe UI", 10),
            bg=THEME["bg_panel"],
            fg=THEME["text"],
            anchor="w"
        )
        procs_lbl.grid(row=1, column=0, sticky="w", padx=(0, 20), pady=(10, 0))

        self.procs_value = tk.Label(
            stats_frame,
            text="0",
            font=("Segoe UI", 12, "bold"),
            bg=THEME["bg_panel"],
            fg=THEME["accent"],
            anchor="w"
        )
        self.procs_value.grid(row=1, column=1, sticky="w", pady=(10, 0))

    def _build_process_list(self, parent):
        """Build TOP processes list"""
        header = tk.Label(
            parent,
            text="TOP Resource Consumers (All Time)",
            font=("Segoe UI", 11, "bold"),
            bg=THEME["accent2"],
            fg=THEME["bg_panel"],
            anchor="w"
        )
        header.pack(fill="x", padx=0, pady=0)

        # List frame
        list_frame = tk.Frame(parent, bg=THEME["bg_panel"])
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Scrollbar
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        # Process list
        self.process_listbox = tk.Listbox(
            list_frame,
            bg=THEME["bg_panel"],
            fg=THEME["text"],
            font=("Consolas", 9),
            bd=0,
            selectmode="single",
            highlightthickness=0,
            yscrollcommand=scrollbar.set,
            selectbackground=THEME["accent"],
            selectforeground=THEME["bg_panel"]
        )
        self.process_listbox.pack(side="left", fill="both", expand=True)
        self.process_listbox.bind("<<ListboxSelect>>", self._on_process_select)

        scrollbar.config(command=self.process_listbox.yview)

    def _build_process_details(self, parent):
        """Build process details panel"""
        header = tk.Label(
            parent,
            text="Process Information",
            font=("Segoe UI", 11, "bold"),
            bg=THEME["accent"],
            fg=THEME["bg_panel"],
            anchor="w"
        )
        header.pack(fill="x", padx=0, pady=0)

        # Details text
        details_frame = tk.Frame(parent, bg=THEME["bg_panel"])
        details_frame.pack(fill="both", expand=True, padx=15, pady=15)

        self.details_text = tk.Text(
            details_frame,
            bg=THEME["bg_panel"],
            fg=THEME["text"],
            font=("Segoe UI", 9),
            bd=0,
            wrap="word",
            state="disabled"
        )
        self.details_text.pack(fill="both", expand=True)

        # Configure tags
        self.details_text.tag_config("title", foreground=THEME["text"], font=("Segoe UI", 11, "bold"))
        self.details_text.tag_config("header", foreground=THEME["accent"], font=("Segoe UI", 9, "bold"))
        self.details_text.tag_config("normal", foreground=THEME["text"], font=("Segoe UI", 9))
        self.details_text.tag_config("warning", foreground="#FF6B35", font=("Segoe UI", 9, "bold"))
        self.details_text.tag_config("muted", foreground=THEME["muted"], font=("Segoe UI", 8))

        # "More about this process" button
        self.more_btn = tk.Button(
            parent,
            text="More About This Process",
            font=("Segoe UI", 10, "bold"),
            bg=THEME["accent"],
            fg=THEME["bg_panel"],
            relief="flat",
            cursor="hand2",
            command=self._show_process_definition,
            state="disabled"
        )
        self.more_btn.pack(fill="x", padx=15, pady=(0, 15))

    def _on_process_select(self, event):
        """Handle process selection"""
        selection = self.process_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        process_line = self.process_listbox.get(index)

        # Extract process name from line
        # Format: "#1  chrome.exe              450.2%  2048MB  ..."
        parts = process_line.split()
        if len(parts) >= 2:
            self.selected_process = parts[1]  # Process name
            self._update_process_details()
            self.more_btn.config(state="normal")

    def _update_process_details(self):
        """Update process details panel"""
        if not self.selected_process:
            return

        # Get process definition
        definition = get_process_definition(self.selected_process)

        self.details_text.config(state="normal")
        self.details_text.delete("1.0", "end")

        # Title
        self.details_text.insert("end", f"{definition['full_name']}\n", ("title",))
        self.details_text.insert("end", f"{self.selected_process}\n\n", ("muted",))

        # Category
        self.details_text.insert("end", "Category: ", ("header",))
        self.details_text.insert("end", f"{definition['category']}\n\n", ("normal",))

        # Description
        self.details_text.insert("end", "Description:\n", ("header",))
        self.details_text.insert("end", f"{definition['description']}\n\n", ("normal",))

        # Purpose
        self.details_text.insert("end", "Purpose:\n", ("header",))
        self.details_text.insert("end", f"{definition['purpose']}\n\n", ("normal",))

        # Normal Behavior
        self.details_text.insert("end", "Normal Behavior:\n", ("header",))
        self.details_text.insert("end", f"{definition['normal_behavior']}\n\n", ("normal",))

        # Warning
        if definition.get('warning'):
            self.details_text.insert("end", "Note: ", ("warning",))
            self.details_text.insert("end", f"{definition['warning']}\n\n", ("normal",))

        # Developer
        self.details_text.insert("end", "Developer: ", ("muted",))
        self.details_text.insert("end", f"{definition['developer']}\n", ("muted",))

        self.details_text.config(state="disabled")

    def _show_process_definition(self):
        """Show detailed process definition in popup"""
        if not self.selected_process:
            return

        definition = get_process_definition(self.selected_process)

        # Create popup window
        popup = tk.Toplevel(self.frame)
        popup.title(f"About {definition['full_name']}")
        popup.geometry("500x400")
        popup.configure(bg=THEME["bg_main"])
        popup.resizable(False, False)

        # Title
        title = tk.Label(
            popup,
            text=definition['full_name'],
            font=("Segoe UI", 14, "bold"),
            bg=THEME["bg_main"],
            fg=THEME["text"]
        )
        title.pack(pady=(15, 5))

        subtitle = tk.Label(
            popup,
            text=self.selected_process,
            font=("Segoe UI", 9),
            bg=THEME["bg_main"],
            fg=THEME["muted"]
        )
        subtitle.pack()

        # Content frame
        content = tk.Frame(popup, bg=THEME["bg_panel"])
        content.pack(fill="both", expand=True, padx=20, pady=15)

        # Scrollable text
        text = tk.Text(
            content,
            bg=THEME["bg_panel"],
            fg=THEME["text"],
            font=("Segoe UI", 9),
            bd=0,
            wrap="word",
            padx=15,
            pady=15
        )
        text.pack(fill="both", expand=True)

        # Fill content
        text.insert("end", f"Category: {definition['category']}\n\n", "bold")
        text.insert("end", f"{definition['description']}\n\n")
        text.insert("end", f"Purpose:\n{definition['purpose']}\n\n", "bold")
        text.insert("end", f"Normal Behavior:\n{definition['normal_behavior']}\n\n")
        if definition.get('warning'):
            text.insert("end", f"WARNING:\n{definition['warning']}\n\n", "warning")
        text.insert("end", f"\nDeveloper: {definition['developer']}")

        text.tag_config("bold", font=("Segoe UI", 9, "bold"))
        text.tag_config("warning", foreground="#FF6B35", font=("Segoe UI", 9, "bold"))
        text.config(state="disabled")

        # Close button
        close_btn = tk.Button(
            popup,
            text="Close",
            font=("Segoe UI", 10),
            bg=THEME["accent"],
            fg=THEME["bg_panel"],
            relief="flat",
            command=popup.destroy
        )
        close_btn.pack(pady=(0, 15))

    def update(self):
        """Update All Stats data"""
        if not self.data_manager:
            return

        try:
            # Get statistics
            stats = self.data_manager.statistics

            # Update runtime
            total_runtime = stats.get('total_runtime_seconds', 0)
            hours = int(total_runtime // 3600)
            minutes = int((total_runtime % 3600) // 60)
            self.runtime_value.config(text=f"{hours}h {minutes}m")

            # Update process count
            proc_count = len(stats.get('processes', {}))
            self.procs_value.config(text=f"{proc_count}")

            # Update process list
            self._update_process_list()

        except Exception as e:
            print(f"[AllStats] Error updating: {e}")

    def _update_process_list(self):
        """Update TOP processes list"""
        if not self.data_manager:
            return

        try:
            self.process_listbox.delete(0, tk.END)

            stats = self.data_manager.statistics
            processes = stats.get('processes', {})

            # Convert to list and sort by total CPU time
            proc_list = []
            for proc_name, data in processes.items():
                total_cpu = data.get('total_cpu_time', 0)
                total_ram = data.get('total_ram_time', 0)
                peak_cpu = data.get('peak_cpu', 0)
                samples = data.get('total_samples', 0)

                if samples > 0:
                    avg_cpu = total_cpu / samples
                    avg_ram = total_ram / samples
                else:
                    avg_cpu = 0
                    avg_ram = 0

                proc_list.append({
                    'name': proc_name,
                    'avg_cpu': avg_cpu,
                    'avg_ram': avg_ram,
                    'peak_cpu': peak_cpu,
                    'total_cpu': total_cpu,
                    'samples': samples
                })

            # Sort by total CPU time
            proc_list.sort(key=lambda x: x['total_cpu'], reverse=True)

            # Display TOP 20
            for i, proc in enumerate(proc_list[:20], start=1):
                name = proc['name'][:20]
                avg_cpu = proc['avg_cpu']
                avg_ram = proc['avg_ram']
                peak_cpu = proc['peak_cpu']

                line = f"#{i:<3} {name:<20} {avg_cpu:>6.1f}%  {avg_ram:>6.0f}MB  Peak: {peak_cpu:>5.1f}%"
                self.process_listbox.insert(tk.END, line)

        except Exception as e:
            print(f"[AllStats] Error updating process list: {e}")

    def show(self):
        """Show the page"""
        self.frame.pack(fill="both", expand=True)
        self.update()

    def hide(self):
        """Hide the page"""
        self.frame.pack_forget()
