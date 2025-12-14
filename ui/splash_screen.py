"""
Splash Screen for PC Workman HCK
Beautiful animated intro with HCK_Labs logo
"""

import tkinter as tk
from tkinter import PhotoImage
import os

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None


class SplashScreen:
    """Animated splash screen with fade-in and fade-out effects"""

    def __init__(self, duration=2.5, on_complete=None):
        """
        Create splash screen with HCK_Labs logo

        Args:
            duration: Total duration in seconds (default 2.5s)
            on_complete: Callback function to call when splash is done
        """
        self.duration = duration
        self.on_complete = on_complete
        self.running = True

        # Create window
        self.root = tk.Tk()
        self.root.overrideredirect(True)  # No window decorations
        self.root.attributes('-topmost', True)  # Always on top

        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Window size (logo will be scaled to fit)
        window_width = 500
        window_height = 500

        # Center window
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2

        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Dark background
        self.root.configure(bg="#0a0e27")

        # Start with alpha = 0 (fully transparent)
        self.root.attributes('-alpha', 0.0)

        # Load and display logo
        self._load_logo()

        # Animation parameters
        self.fade_in_duration = 0.8  # 0.8s fade in
        self.hold_duration = 0.9     # 0.9s hold at full opacity
        self.fade_out_duration = 0.8  # 0.8s fade out

        self.start_time = None
        self.current_alpha = 0.0

        # Start animation after window is ready
        self.root.after(50, self._start_animation)

    def _load_logo(self):
        """Load HCK_Labs logo"""
        logo_path = os.path.join("data", "icons", "HCKintro.png")

        if not os.path.exists(logo_path):
            # Fallback: display text if logo not found
            tk.Label(
                self.root,
                text="HCK_Labs",
                font=("Segoe UI", 48, "bold"),
                bg="#0a0e27",
                fg="#8b5cf6"
            ).pack(expand=True)
            return

        try:
            if Image and ImageTk:
                # Load with PIL for better quality
                img = Image.open(logo_path)

                # Resize to fit window (max 450x450)
                img.thumbnail((450, 450), Image.Resampling.LANCZOS)

                self.logo_image = ImageTk.PhotoImage(img)

                # Display logo
                tk.Label(
                    self.root,
                    image=self.logo_image,
                    bg="#0a0e27"
                ).pack(expand=True)
            else:
                # Fallback to PhotoImage
                self.logo_image = PhotoImage(file=logo_path)
                tk.Label(
                    self.root,
                    image=self.logo_image,
                    bg="#0a0e27"
                ).pack(expand=True)

        except Exception as e:
            print(f"[Splash] Error loading logo: {e}")
            # Fallback text
            tk.Label(
                self.root,
                text="HCK_Labs",
                font=("Segoe UI", 48, "bold"),
                bg="#0a0e27",
                fg="#8b5cf6"
            ).pack(expand=True)

    def _start_animation(self):
        """Start the fade animation"""
        import time
        self.start_time = time.time()
        self._animate()

    def _animate(self):
        """Animate alpha (fade in -> hold -> fade out)"""
        if not self.running:
            return

        import time
        elapsed = time.time() - self.start_time

        if elapsed < self.fade_in_duration:
            # FADE IN (0.0 -> 1.0)
            progress = elapsed / self.fade_in_duration
            self.current_alpha = self._ease_out(progress)

        elif elapsed < self.fade_in_duration + self.hold_duration:
            # HOLD (1.0)
            self.current_alpha = 1.0

        elif elapsed < self.fade_in_duration + self.hold_duration + self.fade_out_duration:
            # FADE OUT (1.0 -> 0.0)
            fade_out_elapsed = elapsed - self.fade_in_duration - self.hold_duration
            progress = fade_out_elapsed / self.fade_out_duration
            self.current_alpha = 1.0 - self._ease_in(progress)

        else:
            # DONE - close splash
            self.running = False
            self.root.destroy()
            if self.on_complete:
                self.on_complete()
            return

        # Update window alpha
        self.root.attributes('-alpha', self.current_alpha)

        # Continue animation (60 FPS)
        self.root.after(16, self._animate)

    def _ease_out(self, t):
        """Ease-out cubic for smooth fade-in"""
        return 1 - pow(1 - t, 3)

    def _ease_in(self, t):
        """Ease-in cubic for smooth fade-out"""
        return pow(t, 3)

    def show(self):
        """Show splash screen and block until done"""
        self.root.mainloop()


def show_splash(duration=2.5, on_complete=None):
    """
    Convenience function to show splash screen

    Args:
        duration: Duration in seconds
        on_complete: Callback when done
    """
    splash = SplashScreen(duration=duration, on_complete=on_complete)
    splash.show()


if __name__ == "__main__":
    # Test splash screen
    def done():
        print("Splash screen done!")

    show_splash(duration=2.5, on_complete=done)
