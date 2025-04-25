# notification_service.py
import os
import subprocess
import threading
import pygame

from logger_module import logger
import config

class NotificationService:
    """Handles system notifications and sound alerts."""

    def __init__(self):
        self.sound_enabled = config.SOUND_ACTIVE
        self.sound_path = config.SOUND_PATH
        self.notifications_enabled = config.NOTIFICATIONS_ACTIVE
        self.notification_timeout = config.NOTIFICATION_TIMEOUT
        self._pygame_initialized = False
        self._zenity_failed = False # Track if zenity failed once

        if self.sound_enabled:
            self._initialize_sound()

    def _initialize_sound(self):
        """Initializes pygame mixer if sound is enabled."""
        if not self.sound_path or not os.path.exists(self.sound_path):
            logger.log_message(f"Warning: Sound path invalid or not found: {self.sound_path}. Disabling sound.", "RED")
            self.sound_enabled = False
            return

        try:
            pygame.mixer.init()
            pygame.mixer.music.load(self.sound_path)
            self._pygame_initialized = True
            logger.log_message("Pygame mixer initialized for sound alerts.", "GREEN")
        except Exception as e:
            logger.log_message(f"Error initializing pygame mixer: {e}. Disabling sound.", "RED")
            self.sound_enabled = False
            self._pygame_initialized = False

    def play_alert_sound(self):
        """Plays the configured alert sound if enabled and initialized."""
        if self.sound_enabled and self._pygame_initialized:
            try:
                pygame.mixer.music.play()
            except Exception as e:
                logger.log_message(f"Error playing sound: {e}", "RED")
        elif self.sound_enabled and not self._pygame_initialized:
            logger.log_message("Attempted to play sound, but pygame mixer is not initialized.", "RED")


    def show_notification(self, title, message):
        """Shows a system notification in a separate thread if enabled."""
        if self.notifications_enabled and not self._zenity_failed:
            # Run in a separate thread to avoid blocking
            thread = threading.Thread(target=self._show_notification_thread, args=(title, message), daemon=True)
            thread.start()
        elif self._zenity_failed:
            # Log only once that notifications are disabled due to zenity issue
            pass # Already logged in the thread

    def _show_notification_thread(self, title, message):
        """Thread function to display notification using zenity."""
        try:
            # Use subprocess.run for simplicity
            subprocess.run(
                ["zenity", "--info", f"--title={title}", f"--text={message}", f'--timeout={self.notification_timeout}'],
                stdout=subprocess.DEVNULL, # Hide output
                stderr=subprocess.DEVNULL, # Hide errors
                check=False # Don't raise exception on non-zero exit code
            )
        except FileNotFoundError:
            if not self._zenity_failed: # Log only the first time
                logger.log_message("Error: 'zenity' command not found. System notifications disabled.", "RED")
                self._zenity_failed = True # Prevent further attempts/logs
                self.notifications_enabled = False # Disable notifications functionally
        except Exception as e:
            if not self._zenity_failed: # Log other errors only the first time
                logger.log_message(f"Error showing notification via zenity: {e}. System notifications disabled.", "RED")
                self._zenity_failed = True
                self.notifications_enabled = False


# --- Create a global instance for easy import ---
notification_service = NotificationService()
