"""
Alerting System for KSE
Enterprise-Grade Monitoring Alerts

Alert types:
- System health (CPU, memory, disk)
- Search performance degradation
- Crawler failures
- Index corruption
- API errors

Notification channels:
- Email
- Webhook (Slack, Discord, etc.)
- Log file
"""

import smtplib
import requests
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass
from enum import Enum
import logging

from logger_config import setup_logger

logger = setup_logger('kse.alerting')


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alert data structure"""
    title: str
    message: str
    severity: AlertSeverity
    component: str
    timestamp: datetime
    metadata: Dict = None
    
    def to_dict(self) -> Dict:
        return {
            'title': self.title,
            'message': self.message,
            'severity': self.severity.value,
            'component': self.component,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata or {}
        }


class AlertChannel:
    """Base class for alert notification channels"""
    
    def send(self, alert: Alert) -> bool:
        """Send alert through this channel"""
        raise NotImplementedError


class EmailAlertChannel(AlertChannel):
    """Send alerts via email"""
    
    def __init__(self, smtp_host: str, smtp_port: int, username: str, 
                 password: str, from_addr: str, to_addrs: List[str]):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs
    
    def send(self, alert: Alert) -> bool:
        """Send alert email"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_addr
            msg['To'] = ', '.join(self.to_addrs)
            msg['Subject'] = f"[KSE {alert.severity.value.upper()}] {alert.title}"
            
            body = f"""
Klar Search Engine Alert

Severity: {alert.severity.value.upper()}
Component: {alert.component}
Time: {alert.timestamp.isoformat()}

Message:
{alert.message}

Metadata:
{json.dumps(alert.metadata or {}, indent=2)}

---
Klar Search Engine Monitoring System
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Sent email alert: {alert.title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False


class WebhookAlertChannel(AlertChannel):
    """Send alerts via webhook (Slack, Discord, etc.)"""
    
    def __init__(self, webhook_url: str, webhook_type: str = "slack"):
        self.webhook_url = webhook_url
        self.webhook_type = webhook_type
    
    def send(self, alert: Alert) -> bool:
        """Send alert via webhook"""
        try:
            if self.webhook_type == "slack":
                payload = self._format_slack(alert)
            elif self.webhook_type == "discord":
                payload = self._format_discord(alert)
            else:
                payload = alert.to_dict()
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            logger.info(f"Sent webhook alert: {alert.title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
            return False
    
    def _format_slack(self, alert: Alert) -> Dict:
        """Format alert for Slack"""
        color_map = {
            AlertSeverity.INFO: "#36a64f",
            AlertSeverity.WARNING: "#ff9800",
            AlertSeverity.ERROR: "#f44336",
            AlertSeverity.CRITICAL: "#9c27b0"
        }
        
        return {
            "attachments": [{
                "color": color_map.get(alert.severity, "#808080"),
                "title": alert.title,
                "text": alert.message,
                "fields": [
                    {"title": "Severity", "value": alert.severity.value.upper(), "short": True},
                    {"title": "Component", "value": alert.component, "short": True},
                    {"title": "Time", "value": alert.timestamp.isoformat(), "short": False}
                ],
                "footer": "Klar Search Engine",
                "ts": int(alert.timestamp.timestamp())
            }]
        }
    
    def _format_discord(self, alert: Alert) -> Dict:
        """Format alert for Discord"""
        color_map = {
            AlertSeverity.INFO: 3447003,
            AlertSeverity.WARNING: 16761095,
            AlertSeverity.ERROR: 15158332,
            AlertSeverity.CRITICAL: 10181046
        }
        
        return {
            "embeds": [{
                "title": f"🚨 {alert.title}",
                "description": alert.message,
                "color": color_map.get(alert.severity, 8421504),
                "fields": [
                    {"name": "Severity", "value": alert.severity.value.upper(), "inline": True},
                    {"name": "Component", "value": alert.component, "inline": True}
                ],
                "timestamp": alert.timestamp.isoformat(),
                "footer": {"text": "Klar Search Engine"}
            }]
        }


class LogFileAlertChannel(AlertChannel):
    """Write alerts to log file"""
    
    def __init__(self, log_file: str = "alerts.log"):
        self.logger = logging.getLogger('kse.alerts')
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - [%(levelname)s] - %(message)s'
        ))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def send(self, alert: Alert) -> bool:
        """Write alert to log"""
        try:
            log_message = f"{alert.component} - {alert.title}: {alert.message}"
            
            if alert.severity == AlertSeverity.INFO:
                self.logger.info(log_message)
            elif alert.severity == AlertSeverity.WARNING:
                self.logger.warning(log_message)
            elif alert.severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]:
                self.logger.error(log_message)
            
            return True
        except Exception as e:
            logger.error(f"Failed to write alert to log: {e}")
            return False


class AlertManager:
    """Manage alerts and notification channels"""
    
    def __init__(self):
        self.channels: List[AlertChannel] = []
        self.alert_history: List[Alert] = []
        self.max_history = 1000
        
        # Rate limiting: prevent alert spam
        self.alert_cooldown: Dict[str, datetime] = {}
        self.cooldown_duration = timedelta(minutes=5)
    
    def add_channel(self, channel: AlertChannel):
        """Add notification channel"""
        self.channels.append(channel)
        logger.info(f"Added alert channel: {type(channel).__name__}")
    
    def send_alert(self, alert: Alert, force: bool = False) -> bool:
        """
        Send alert through all channels
        
        Args:
            alert: Alert to send
            force: Bypass cooldown (for critical alerts)
        
        Returns:
            True if sent successfully through at least one channel
        """
        # Check cooldown (unless forced)
        if not force:
            alert_key = f"{alert.component}:{alert.title}"
            if alert_key in self.alert_cooldown:
                if datetime.now() - self.alert_cooldown[alert_key] < self.cooldown_duration:
                    logger.debug(f"Alert in cooldown: {alert_key}")
                    return False
            
            self.alert_cooldown[alert_key] = datetime.now()
        
        # Send through all channels
        success = False
        for channel in self.channels:
            try:
                if channel.send(alert):
                    success = True
            except Exception as e:
                logger.error(f"Channel {type(channel).__name__} failed: {e}")
        
        # Store in history
        self.alert_history.append(alert)
        if len(self.alert_history) > self.max_history:
            self.alert_history = self.alert_history[-self.max_history:]
        
        return success
    
    def get_recent_alerts(self, hours: int = 24) -> List[Alert]:
        """Get recent alerts"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [a for a in self.alert_history if a.timestamp > cutoff]


# Global alert manager
alert_manager = AlertManager()


# Convenience functions
def alert_info(title: str, message: str, component: str = "system", **metadata):
    """Send info alert"""
    alert = Alert(
        title=title,
        message=message,
        severity=AlertSeverity.INFO,
        component=component,
        timestamp=datetime.now(),
        metadata=metadata
    )
    alert_manager.send_alert(alert)


def alert_warning(title: str, message: str, component: str = "system", **metadata):
    """Send warning alert"""
    alert = Alert(
        title=title,
        message=message,
        severity=AlertSeverity.WARNING,
        component=component,
        timestamp=datetime.now(),
        metadata=metadata
    )
    alert_manager.send_alert(alert)


def alert_error(title: str, message: str, component: str = "system", **metadata):
    """Send error alert"""
    alert = Alert(
        title=title,
        message=message,
        severity=AlertSeverity.ERROR,
        component=component,
        timestamp=datetime.now(),
        metadata=metadata
    )
    alert_manager.send_alert(alert)


def alert_critical(title: str, message: str, component: str = "system", force: bool = True, **metadata):
    """Send critical alert (bypasses cooldown)"""
    alert = Alert(
        title=title,
        message=message,
        severity=AlertSeverity.CRITICAL,
        component=component,
        timestamp=datetime.now(),
        metadata=metadata
    )
    alert_manager.send_alert(alert, force=force)


if __name__ == '__main__':
    print("Testing alerting system...")
    
    # Add log channel
    alert_manager.add_channel(LogFileAlertChannel())
    
    # Send test alerts
    alert_info("System Started", "KSE started successfully", component="api")
    alert_warning("High CPU Usage", "CPU usage at 85%", component="system", cpu=85)
    alert_error("Index Load Failed", "Failed to load index file", component="indexer")
    
    # Get recent alerts
    recent = alert_manager.get_recent_alerts(hours=1)
    print(f"\nRecent alerts: {len(recent)}")
    for alert in recent:
        print(f"  - [{alert.severity.value}] {alert.title}")
    
    print("\nAlerting system test completed")
