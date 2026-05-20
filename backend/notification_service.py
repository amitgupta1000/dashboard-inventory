"""
Notification service for sending job updates and reports to users via email.
Includes: insight updates, 12-hour summaries, and 48-hour closure reports.
"""

import os
import logging
import asyncio
from datetime import datetime
from typing import List, Optional, Dict
from .email_utils import send_email_with_attachments
from .database import Job, JobSupplierState, SupplierEmail, Insight

logger = logging.getLogger(__name__)

# Get app base URL from environment
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:3000")


def build_html_email_base(title: str, content: str, footer_text: str = None) -> str:
    """Build HTML email template with base styling."""
    footer = f"<p style='color: #666; font-size: 12px; margin-top: 40px; border-top: 1px solid #ddd; padding-top: 20px;'>{footer_text}</p>" if footer_text else ""
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 28px; }}
        .content {{ background: #f9f9f9; padding: 30px; border: 1px solid #ddd; border-radius: 0 0 8px 8px; }}
        .btn {{ display: inline-block; padding: 12px 24px; background: #667eea; color: white; text-decoration: none; border-radius: 4px; margin: 10px 0; }}
        .btn:hover {{ background: #764ba2; }}
        .stat {{ display: inline-block; margin: 15px 10px; padding: 15px; background: white; border-radius: 4px; border-left: 4px solid #667eea; }}
        .stat-label {{ color: #666; font-size: 12px; text-transform: uppercase; }}
        .stat-value {{ color: #667eea; font-size: 24px; font-weight: bold; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f0f0f0; font-weight: bold; }}
        tr:hover {{ background: #f9f9f9; }}
        .insight-box {{ background: white; padding: 15px; margin: 15px 0; border-left: 4px solid #10b981; border-radius: 4px; }}
        .insight-title {{ color: #10b981; font-weight: bold; font-size: 16px; }}
        .insight-detail {{ color: #666; margin: 5px 0; }}
        {footer}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
        </div>
        <div class="content">
            {content}
        </div>
    </div>
</body>
</html>"""


async def send_insight_notification(job: Job, new_insights_count: int, insights: List[Insight]) -> bool:
    """
    Send notification when new insights are extracted.
    
    Args:
        job: Job object
        new_insights_count: Number of new insights extracted
        insights: List of new Insight objects
    
    Returns:
        True if email sent successfully, False otherwise
    """
    if not job.user_email:
        logger.warning(f"No user email for job {job.id} - skipping notification")
        return False
    
    try:
        # Build insight cards
        insight_cards = ""
        for insight in insights[:5]:  # Show first 5
            insight_cards += f"""
            <div class="insight-box">
                <div class="insight-title">{insight.supplier}</div>
                <div class="insight-detail"><strong>Contact:</strong> {insight.contact_person or 'N/A'}</div>
                <div class="insight-detail"><strong>Product:</strong> {insight.product or 'N/A'}</div>
                <div class="insight-detail"><strong>Quantity:</strong> {insight.quantity or 'N/A'}</div>
                <div class="insight-detail"><strong>Price:</strong> {insight.price or 'N/A'}</div>
                <div class="insight-detail"><strong>Delivery:</strong> {insight.delivery_date or 'N/A'}</div>
            </div>
            """
        
        if len(insights) > 5:
            insight_cards += f"<p><em>... and {len(insights) - 5} more insights. View all in the app.</em></p>"
        
        content = f"""
        <h2>📊 New Insights Extracted!</h2>
        <p><strong>{new_insights_count}</strong> new supplier response(s) have been analyzed and insights extracted.</p>
        
        <h3>Chemical Query: {job.chemical_query}</h3>
        
        <h3>Extracted Data:</h3>
        {insight_cards}
        
        <p>
            <a href="{APP_BASE_URL}/jobs/{job.id}" class="btn">📱 View Full Job Details</a>
            <a href="{APP_BASE_URL}/jobs/{job.id}?tab=insights" class="btn">💡 View All Insights</a>
            <a href="{APP_BASE_URL}/jobs/{job.id}?tab=emails" class="btn">📧 View Email Thread</a>
        </p>
        """
        
        footer_text = f"Job ID: {job.id} | Created: {job.created_at.strftime('%Y-%m-%d %H:%M')} | Status: {job.status}"
        html_content = build_html_email_base("🎉 Crystal Supplier - New Insights", content, footer_text)
        
        success = await send_email_with_attachments(
            subject=f"Crystal: {new_insights_count} new insights for '{job.chemical_query}'",
            body=html_content,
            to_email=job.user_email
        )
        
        if success:
            logger.info(f"Sent insight notification to {job.user_email} for job {job.id}")
        else:
            logger.error(f"Failed to send insight notification to {job.user_email} for job {job.id}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error sending insight notification: {e}")
        return False


async def send_summary_notification(job: Job, supplier_states: List[JobSupplierState], 
                             new_insights_count: int) -> bool:
    """
    Send 12-hour summary report only if there are new updates.
    
    Args:
        job: Job object
        supplier_states: List of supplier states
        new_insights_count: Number of new insights since last summary
    
    Returns:
        True if email sent successfully, False otherwise
    """
    if not job.user_email:
        logger.warning(f"No user email for job {job.id} - skipping summary")
        return False
    
    # Don't send summary if no new updates
    if new_insights_count == 0:
        logger.info(f"No new updates for job {job.id} - skipping 12-hour summary")
        return False
    
    try:
        # Calculate statistics
        total_suppliers = len(supplier_states)
        replied = sum(1 for s in supplier_states if s.replied)
        pending = total_suppliers - replied
        
        # Build supplier status table
        supplier_table = """
        <table>
            <tr>
                <th>Supplier</th>
                <th>Status</th>
                <th>Reply Date</th>
                <th>Reminder Sent</th>
            </tr>
        """
        
        for supplier in supplier_states:
            status = "✅ Replied" if supplier.replied else "⏳ Pending"
            reply_date = supplier.reply_received_at.strftime("%Y-%m-%d %H:%M") if supplier.reply_received_at else "—"
            reminder = "Yes" if supplier.reminder_sent_at else "No"
            supplier_table += f"""
            <tr>
                <td>{supplier.company_name}</td>
                <td>{status}</td>
                <td>{reply_date}</td>
                <td>{reminder}</td>
            </tr>
            """
        
        supplier_table += "</table>"
        
        content = f"""
        <h2>📋 12-Hour Progress Report</h2>
        <p>Here's the latest status on your RFQ campaign.</p>
        
        <h3>Chemical Query: {job.chemical_query}</h3>
        
        <div style="display: flex; justify-content: space-around; margin: 20px 0;">
            <div class="stat">
                <div class="stat-label">Total Suppliers</div>
                <div class="stat-value">{total_suppliers}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Replied</div>
                <div class="stat-value" style="color: #10b981;">{replied}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Pending</div>
                <div class="stat-value" style="color: #f59e0b;">{pending}</div>
            </div>
            <div class="stat">
                <div class="stat-label">New Insights</div>
                <div class="stat-value" style="color: #667eea;">{new_insights_count}</div>
            </div>
        </div>
        
        <h3>Supplier Status:</h3>
        {supplier_table}
        
        <p>
            <a href="{APP_BASE_URL}/jobs/{job.id}" class="btn">📱 View Full Job Details</a>
            <a href="{APP_BASE_URL}/jobs/{job.id}?tab=suppliers" class="btn">👥 View All Suppliers</a>
        </p>
        
        <p style="color: #666; font-size: 14px;">
            💡 <strong>Tip:</strong> Check back in 12 hours for the next update, or check the app anytime for real-time status.
        </p>
        """
        
        footer_text = f"Job ID: {job.id} | Report Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Status: {job.status}"
        html_content = build_html_email_base("📊 Crystal Supplier - 12-Hour Summary", content, footer_text)
        
        success = await send_email_with_attachments(
            subject=f"Crystal: 12-hour summary for '{job.chemical_query}' ({replied}/{total_suppliers} replied)",
            body=html_content,
            to_email=job.user_email
        )
        
        if success:
            logger.info(f"Sent summary notification to {job.user_email} for job {job.id}")
        else:
            logger.error(f"Failed to send summary notification to {job.user_email} for job {job.id}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error sending summary notification: {e}")
        return False


async def send_closure_notification(job: Job, supplier_states: List[JobSupplierState], 
                             insights: List[Insight], emails: List[SupplierEmail]) -> bool:
    """
    Send final 48-hour closure report with complete job summary.
    
    Args:
        job: Job object
        supplier_states: List of supplier states
        insights: List of all insights
        emails: List of all emails (sent and received)
    
    Returns:
        True if email sent successfully, False otherwise
    """
    if not job.user_email:
        logger.warning(f"No user email for job {job.id} - skipping closure notification")
        return False
    
    try:
        # Calculate final statistics
        total_suppliers = len(supplier_states)
        replied = sum(1 for s in supplier_states if s.replied)
        response_rate = f"{(replied / total_suppliers * 100):.1f}%" if total_suppliers > 0 else "N/A"
        
        # Build insights table
        insights_table = """
        <table>
            <tr>
                <th>Supplier</th>
                <th>Contact</th>
                <th>Product</th>
                <th>Quantity</th>
                <th>Price</th>
                <th>Delivery</th>
            </tr>
        """
        
        if insights:
            for insight in insights:
                insights_table += f"""
                <tr>
                    <td>{insight.supplier}</td>
                    <td>{insight.contact_person or '—'}</td>
                    <td>{insight.product or '—'}</td>
                    <td>{insight.quantity or '—'}</td>
                    <td>{insight.price or '—'}</td>
                    <td>{insight.delivery_date or '—'}</td>
                </tr>
                """
        else:
            insights_table += "<tr><td colspan='6' style='text-align: center; color: #999;'>No insights extracted</td></tr>"
        
        insights_table += "</table>"
        
        # Email communication summary
        outbound_emails = sum(1 for e in emails if e.email_type == "outbound")
        inbound_emails = sum(1 for e in emails if e.email_type == "inbound")
        
        duration = (job.closed_at - job.created_at).total_seconds() / 3600 if job.closed_at else 0
        
        content = f"""
        <h2>✅ Job Completed</h2>
        <p>Your RFQ campaign has concluded. Here's the final report.</p>
        
        <h3 style="color: #667eea; border-bottom: 2px solid #667eea; padding-bottom: 10px;">
            {job.chemical_query}
        </h3>
        
        <div style="display: flex; justify-content: space-around; margin: 20px 0; flex-wrap: wrap;">
            <div class="stat">
                <div class="stat-label">Total Suppliers</div>
                <div class="stat-value">{total_suppliers}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Replied</div>
                <div class="stat-value" style="color: #10b981;">{replied}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Response Rate</div>
                <div class="stat-value" style="color: #667eea;">{response_rate}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Duration</div>
                <div class="stat-value" style="color: #8b5cf6;">{duration:.1f}h</div>
            </div>
        </div>
        
        <h3>📧 Communication Summary:</h3>
        <div style="background: white; padding: 15px; border-radius: 4px; margin: 15px 0;">
            <p><strong>Emails Sent:</strong> {outbound_emails} RFQ/reminder emails</p>
            <p><strong>Replies Received:</strong> {inbound_emails} supplier responses</p>
            <p><strong>Insights Generated:</strong> {len(insights)} structured insights</p>
        </div>
        
        <h3>💡 Extracted Insights & Offers:</h3>
        {insights_table}
        
        <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
            <a href="{APP_BASE_URL}/jobs/{job.id}" class="btn">📱 View Complete Job Report</a>
            <a href="{APP_BASE_URL}/jobs" class="btn">➕ Start New RFQ Campaign</a>
        </p>
        
        <p style="color: #666; font-size: 14px; margin-top: 20px;">
            📌 <strong>Next Steps:</strong><br>
            • Review the extracted insights and offers above<br>
            • Contact your preferred suppliers to negotiate<br>
            • Start a new campaign when ready
        </p>
        """
        
        footer_text = f"Job ID: {job.id} | Created: {job.created_at.strftime('%Y-%m-%d %H:%M')} | Closed: {job.closed_at.strftime('%Y-%m-%d %H:%M') if job.closed_at else 'N/A'}"
        html_content = build_html_email_base("🎊 Crystal Supplier - Campaign Complete", content, footer_text)
        
        success = await send_email_with_attachments(
            subject=f"Crystal: RFQ campaign complete - {replied}/{total_suppliers} suppliers replied",
            body=html_content,
            to_email=job.user_email
        )
        
        if success:
            logger.info(f"Sent closure notification to {job.user_email} for job {job.id}")
        else:
            logger.error(f"Failed to send closure notification to {job.user_email} for job {job.id}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error sending closure notification: {e}")
        return False
