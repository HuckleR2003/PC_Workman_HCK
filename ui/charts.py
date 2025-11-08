"""ui.charts
Placeholder for charting utilities (matplotlib / pyqtgraph wrappers)."""

from import_core import register_component

class Charts:
    def __init__(self):
        register_component('ui.charts', self)

    def plot_bar(self, data):
        # implement plotting later
        return True

charts = Charts()
