from typing import List
from ..database.models import Alert


class AlertEmailTemplate:
    """Templates for formatting alert emails"""

    def format_alert(self, alert: Alert) -> str:
        """Format a single alert for email"""

        alert_type_descriptions = {
            "win_odds_low": "Low Win Odds Alert",
            "win_odds_high": "High Win Odds Alert",
            "odds_change": "Significant Odds Change",
            "exacta_low": "Low Exacta Payout",
            "exacta_high": "High Exacta Payout",
            "discrepancy": "Pool Discrepancy Detected",
        }

        description = alert_type_descriptions.get(alert.alert_type, "Odds Alert")

        body = f"""
Horse Racing {description}
{'=' * 50}

Alert Details:
• Time: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S')
         if alert.triggered_at else 'N/A'}
• Message: {alert.message}
"""

        if alert.threshold_value is not None:
            body += f"• Threshold: {alert.threshold_value:.2f}\n"

        if alert.actual_value is not None:
            body += f"• Actual Value: {alert.actual_value:.2f}\n"

        body += f"""
• Race ID: {alert.race_id}
• Entry ID: {alert.entry_id if alert.entry_id else 'N/A'}

{'=' * 50}
This is an automated alert from your Horse Racing Odds Tracking System.
        """

        return body.strip()

    def format_batch(self, alerts: List[Alert]) -> str:
        """Format multiple alerts for batch email"""

        body = f"""
Multiple Alerts Triggered
{'=' * 50}

You have {len(alerts)} new alerts:

"""

        # Group alerts by type
        alerts_by_type = {}
        for alert in alerts:
            alert_type = alert.alert_type
            if alert_type not in alerts_by_type:
                alerts_by_type[alert_type] = []
            alerts_by_type[alert_type].append(alert)

        # Format each group
        for alert_type, type_alerts in alerts_by_type.items():
            type_name = alert_type.replace("_", " ").title()
            body += f"\n{type_name} ({len(type_alerts)} alerts):\n"
            body += "-" * 30 + "\n"

            # Limit to first 5 of each type
            for alert in type_alerts[:5]:
                time_str = (
                    alert.triggered_at.strftime("%H:%M:%S")
                    if alert.triggered_at
                    else "N/A"
                )
                body += f"  • {time_str} - {alert.message}\n"

            if len(type_alerts) > 5:
                body += f"  ... and {len(type_alerts) - 5} more\n"

        if alerts:
            first_time = (
                alerts[0].triggered_at.strftime("%H:%M")
                if alerts[0].triggered_at
                else "N/A"
            )
            last_time = (
                alerts[-1].triggered_at.strftime("%H:%M")
                if alerts[-1].triggered_at
                else "N/A"
            )

            body += f"""

{'=' * 50}
Summary:
• Total Alerts: {len(alerts)}
• Time Range: {first_time} - {last_time}
• Alert Types: {', '.join(alerts_by_type.keys())}
"""

        body += (
            "\nThis is an automated alert from your Horse Racing "
            "Odds Tracking System."
        )

        return body.strip()
