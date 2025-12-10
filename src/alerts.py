import queue
import time

class AlertManager:
    """Manages a queue of alerts to be displayed."""
    def __init__(self, display_duration=3):
        self.alerts = queue.Queue()
        self.display_duration = display_duration

    def add_alert(self, message, icon=""):
        """Adds an alert to the queue with a timestamp."""
        alert_time = time.time()
        self.alerts.put({"message": message, "icon": icon, "time": alert_time})

    def get_alerts(self):
        """Gets current alerts that should be displayed."""
        current_alerts = []
        while not self.alerts.empty():
            alert = self.alerts.get()
            # Keep alert if it's not expired
            if time.time() - alert["time"] < self.display_duration:
                current_alerts.append(alert)
        
        # Add unexpired alerts back to a new queue to maintain them
        for alert in current_alerts:
            self.alerts.put(alert)
            
        return [f'{a["icon"]} {a["message"]}' for a in current_alerts]