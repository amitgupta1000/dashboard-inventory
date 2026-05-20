from apscheduler.schedulers.background import BackgroundScheduler
import logging
import asyncio
import threading
from sqlalchemy import select
from backend.database import SchedulerAsyncSessionLocal, Job, JobSupplierState, Insight, SupplierEmail
from datetime import datetime, timedelta
from backend.gcs_utils import upload_job_summary
from backend.email_utils import send_reminder_email
from backend.notification_service import send_summary_notification, send_closure_notification

logger = logging.getLogger(__name__)

# Thread-local storage for event loops
_loop_lock = threading.Lock()
_thread_loops = {}


def _get_or_create_loop():
    """Get or create an event loop for the current thread (thread-safe)."""
    thread_id = threading.get_ident()
    
    with _loop_lock:
        if thread_id not in _thread_loops:
            try:
                # Try to get existing loop
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    raise RuntimeError("Loop is closed")
            except RuntimeError:
                # No loop or loop is closed, create new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            _thread_loops[thread_id] = loop
        else:
            loop = _thread_loops[thread_id]
            if loop.is_closed():
                # Loop was closed, create new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                _thread_loops[thread_id] = loop
    
    return loop

async def process_active_jobs_async():
    """Async function to process active jobs: send summaries, reminders, and close stale jobs.
    
    Uses SchedulerAsyncSessionLocal which has a separate engine without pool_pre_ping
    to avoid event loop conflicts when running in a background thread.
    """
    logger.info("Running scheduled task to process active jobs...")
    
    db = None
    try:
        # Use scheduler-specific session factory to avoid event loop issues
        db = SchedulerAsyncSessionLocal()
        
        # Query all active jobs
        result = await db.execute(select(Job).where(Job.status == "active"))
        active_jobs = result.scalars().all()
        now = datetime.utcnow()
        
        for job in active_jobs:
            try:
                # Production timings:
                # Reminders at T+6H and T+12H, Close at T+48h
                time_since_creation = now - job.created_at
                
                # Check if job should be closed (T+48h)
                if time_since_creation > timedelta(hours=48):
                    if not job.closure_notification_sent:
                        logger.info(f"Job {job.id} has reached T+48h. Sending closure report...")
                        
                        # Get all job details
                        suppliers_result = await db.execute(select(JobSupplierState).where(JobSupplierState.job_id == job.id))
                        suppliers = suppliers_result.scalars().all()
                        
                        insights_result = await db.execute(select(Insight).where(Insight.job_id == job.id))
                        insights = insights_result.scalars().all()
                        
                        emails_result = await db.execute(select(SupplierEmail).where(SupplierEmail.job_id == job.id))
                        emails = emails_result.scalars().all()
                        
                        # Send closure notification
                        await send_closure_notification(job, suppliers, insights, emails)
                        job.closure_notification_sent = True
                    
                    # Close the job
                    logger.info(f"Job {job.id} - Closing job and archiving to GCS.")
                    job.status = "closed"
                    job.closed_at = now
                    
                    # Get job details for archival
                    suppliers_result = await db.execute(select(JobSupplierState).where(JobSupplierState.job_id == job.id))
                    suppliers = suppliers_result.scalars().all()
                    
                    insights_result = await db.execute(select(Insight).where(Insight.job_id == job.id))
                    insights = insights_result.scalars().all()
                    
                    # Prepare summary
                    summary = {
                        "job_id": job.id,
                        "chemical_query": job.chemical_query,
                        "created_at": job.created_at.isoformat(),
                        "closed_at": now.isoformat(),
                        "status": "closed",
                        "total_suppliers": len(suppliers),
                        "responded_suppliers": sum(1 for s in suppliers if s.replied),
                        "insights_extracted": len(insights)
                    }
                    
                    # Format insights for CSV
                    insights_list = [
                        {
                            "Supplier": i.supplier,
                            "Contact_Person": i.contact_person or "",
                            "Product": i.product or "",
                            "Quantity": i.quantity or "",
                            "Price": i.price or "",
                            "Delivery_Date": i.delivery_date or ""
                        }
                        for i in insights
                    ]
                    
                    # Upload to GCS
                    upload_job_summary(job.id, summary, insights_list)
                    
                # Check if 12-hour summary should be sent (every 12h)
                elif time_since_creation > timedelta(hours=12):
                    if not job.last_summary_sent_at or (now - job.last_summary_sent_at) >= timedelta(hours=12):
                        logger.info(f"Job {job.id} - Sending 12-hour summary report...")
                        
                        suppliers_result = await db.execute(select(JobSupplierState).where(JobSupplierState.job_id == job.id))
                        suppliers = suppliers_result.scalars().all()
                        
                        # Count new insights since last summary
                        if job.last_summary_sent_at:
                            new_insights_result = await db.execute(
                                select(Insight).where(
                                    Insight.job_id == job.id,
                                    Insight.extracted_at > job.last_summary_sent_at
                                )
                            )
                            new_insights_count = len(new_insights_result.scalars().all())
                        else:
                            new_insights_result = await db.execute(select(Insight).where(Insight.job_id == job.id))
                            new_insights_count = len(new_insights_result.scalars().all())
                        
                        # Send summary only if there are new updates
                        if new_insights_count > 0 or not job.last_summary_sent_at:
                            await send_summary_notification(job, suppliers, new_insights_count)
                            job.last_summary_sent_at = now
                
                # Check if 6-hour summary should be sent (every 6h)
                elif time_since_creation > timedelta(hours=6):
                    if not job.last_summary_sent_at:
                        logger.info(f"Job {job.id} - Sending initial 6-hour summary report...")
                        
                        suppliers_result = await db.execute(select(JobSupplierState).where(JobSupplierState.job_id == job.id))
                        suppliers = suppliers_result.scalars().all()
                        
                        new_insights_result = await db.execute(select(Insight).where(Insight.job_id == job.id))
                        new_insights_count = len(new_insights_result.scalars().all())
                        
                        # Send summary only if there are updates
                        if new_insights_count > 0:
                            await send_summary_notification(job, suppliers, new_insights_count)
                            job.last_summary_sent_at = now
                
                # Check if reminders should be sent (T+6H and T+12H)
                elif time_since_creation > timedelta(hours=12) and not job.reminders_sent:
                    logger.info(f"Job {job.id} has reached T+12H. Sending final reminders...")
                    
                    # Get suppliers who haven't replied
                    suppliers_result = await db.execute(select(JobSupplierState).where(
                        JobSupplierState.job_id == job.id,
                        JobSupplierState.replied == False
                    ))
                    suppliers = suppliers_result.scalars().all()
                    
                    for supplier in suppliers:
                        try:
                            success = await send_reminder_email(
                                supplier.email_id,
                                supplier.company_name,
                                job.chemical_query
                            )
                            if success:
                                supplier.reminder_sent_at = now
                                logger.info(f"Sent final reminder to {supplier.email_id}")
                        except Exception as e:
                            logger.error(f"Error sending reminder to {supplier.email_id}: {e}")
                    
                    job.reminders_sent = True
                
                # Check if first reminders should be sent (T+6H)
                elif time_since_creation > timedelta(hours=6) and not hasattr(job, '_first_reminder_sent'):
                    logger.info(f"Job {job.id} has reached T+6H. Sending first reminders...")
                    
                    # Get suppliers who haven't replied
                    suppliers_result = await db.execute(select(JobSupplierState).where(
                        JobSupplierState.job_id == job.id,
                        JobSupplierState.replied == False
                    ))
                    suppliers = suppliers_result.scalars().all()
                    
                    for supplier in suppliers:
                        try:
                            success = await send_reminder_email(
                                supplier.email_id,
                                supplier.company_name,
                                job.chemical_query
                            )
                            if success:
                                supplier.reminder_sent_at = now
                                logger.info(f"Sent first reminder to {supplier.email_id}")
                        except Exception as e:
                            logger.error(f"Error sending reminder to {supplier.email_id}: {e}")
                    
            except Exception as e:
                logger.error(f"Error processing job {job.id}: {e}", exc_info=True)
                # Continue with next job instead of failing the entire batch
                continue
        
        # Commit all changes in one transaction
        await db.commit()
        logger.info("Scheduled task completed successfully")
        
    except Exception as e:
        logger.error(f"Error in scheduled task: {e}", exc_info=True)
        if db:
            try:
                await db.rollback()
            except Exception as rollback_error:
                logger.error(f"Error rolling back transaction: {rollback_error}")
    finally:
        # Always close the session
        if db:
            try:
                await db.close()
            except Exception as close_error:
                logger.error(f"Error closing database session: {close_error}")


def process_active_jobs():
    """Sync wrapper for the async process_active_jobs_async function.
    
    Safely executes async code in a background thread by managing event loops
    to avoid "attached to a different loop" errors.
    """
    try:
        loop = _get_or_create_loop()
        
        # If loop is running, we can't use run_until_complete
        # This shouldn't happen in a background scheduler thread, but handle it anyway
        if loop.is_running():
            logger.warning("Event loop is already running, skipping scheduler task")
            return
        
        loop.run_until_complete(process_active_jobs_async())
    except Exception as e:
        logger.error(f"Error in process_active_jobs wrapper: {e}", exc_info=True)


def start_scheduler():
    """Start the background job scheduler."""
    scheduler = BackgroundScheduler()
    # Check every minute
    scheduler.add_job(process_active_jobs, 'interval', minutes=1)
    scheduler.start()
    logger.info("Background scheduler started")
