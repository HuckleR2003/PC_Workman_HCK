"""ui.dialogs
Dialogs (Online/Offline prompt etc.)"""
from import_core import register_component

class Dialogs:
    def __init__(self):
        register_component('ui.dialogs', self)

    def show_online_choice(self):
        # in real UI show switch; here return default
        return True

dialogs = Dialogs()
