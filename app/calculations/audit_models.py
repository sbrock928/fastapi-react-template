# app/calculations/audit_models.py
"""Calculation audit trail models with optimized connection management."""

from sqlalchemy import Column, Integer, String, DateTime, JSON, event
from sqlalchemy.sql import func
from sqlalchemy.orm import Session
from app.core.database import Base
from datetime import datetime
from typing import Dict, Any, Optional, List
import threading
from contextlib import contextmanager
import time
import atexit
import queue


# Thread-local storage for audit context
_audit_context = threading.local()

# Global audit logger singleton
_audit_logger = None
_audit_logger_lock = threading.Lock()


# Add these utility functions to app/calculations/audit_models.py or create a separate audit utils file

def flush_pending_audits():
    """Manually flush any pending audit entries. Useful for testing or shutdown."""
    try:
        logger = get_audit_logger()
        logger.flush()
        print("✅ Pending audit entries flushed successfully")
    except Exception as e:
        print(f"⚠️  Warning: Could not flush pending audits: {e}")


def get_audit_stats():
    """Get current audit logger statistics."""
    try:
        logger = get_audit_logger()
        with logger._lock:
            return {
                "pending_count": len(logger._pending_audits),
                "last_commit_time": logger._last_commit_time,
                "commit_interval": logger._commit_interval,
                "session_active": logger._session is not None,
                "deferred_mode": logger._deferred_mode,
                "database_type": "sql_server_optimized"
            }
    except Exception as e:
        print(f"Warning: Could not get audit stats: {e}")
        return {"error": str(e)}


# Optional: Add this to your calculation router for admin purposes
"""
@router.post("/audit/flush")
def flush_audit_logs():
    \"\"\"Manually flush pending audit logs (admin function).\"\"\"
    try:
        from app.calculations.audit_models import flush_pending_audits, get_audit_stats
        
        stats_before = get_audit_stats()
        flush_pending_audits()
        stats_after = get_audit_stats()
        
        return {
            "success": True,
            "message": "Audit logs flushed successfully",
            "stats_before": stats_before,
            "stats_after": stats_after
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error flushing audit logs: {str(e)}")
"""

class CalculationAuditLog(Base):
    """Unified audit log for both UserCalculation and SystemCalculation changes."""
    
    __tablename__ = "calculation_audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    table_name = Column(String(50), nullable=False, index=True)
    record_id = Column(Integer, nullable=False, index=True)
    operation = Column(String(10), nullable=False, index=True)
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    changed_fields = Column(JSON, nullable=True)
    changed_by = Column(String(100), nullable=True, index=True)
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<CalculationAuditLog(id={self.id}, table={self.table_name}, record_id={self.record_id}, operation={self.operation})>"


# ===== AUDIT CONTEXT MANAGEMENT =====

def set_audit_user(user: str) -> None:
    """Set the current user for audit logging."""
    _audit_context.user = user


def get_audit_user() -> Optional[str]:
    """Get the current audit user."""
    return getattr(_audit_context, 'user', None)


def clear_audit_user() -> None:
    """Clear the current audit user."""
    if hasattr(_audit_context, 'user'):
        delattr(_audit_context, 'user')


@contextmanager
def audit_context(user: str):
    """Context manager for setting audit user."""
    set_audit_user(user)
    try:
        yield
    finally:
        clear_audit_user()


# ===== SINGLETON AUDIT LOGGER =====

class AuditLogger:
    """Singleton audit logger optimized for SQL Server with simplified concurrency handling."""
    
    def __init__(self):
        self._session = None
        self._lock = threading.Lock()
        self._pending_audits = []
        self._last_commit_time = time.time()
        self._commit_interval = 2.0  # Reduced for SQL Server (can handle more frequent commits)
        self._max_batch_size = 25  # Smaller batches work better with SQL Server
        # For SQL Server, we can use simpler immediate mode since it handles concurrency well
        self._deferred_mode = False  # SQL Server doesn't need deferred processing
        
    def _get_session(self):
        """Get or create audit session."""
        if self._session is None:
            from app.core.database import SessionLocal
            self._session = SessionLocal()
        return self._session
    
    def _should_commit(self) -> bool:
        """Check if we should commit pending audits."""
        return (
            len(self._pending_audits) >= self._max_batch_size or
            time.time() - self._last_commit_time >= self._commit_interval
        )
    
    def add_audit(self, audit_data: Dict[str, Any]) -> None:
        """Add an audit entry (thread-safe, optimized for SQL Server)."""
        try:
            with self._lock:
                self._pending_audits.append(audit_data)
                
                # SQL Server handles concurrent writes well, so we can commit more aggressively
                if self._should_commit():
                    self._commit_pending()
                    
        except Exception as e:
            print(f"Warning: Could not add audit entry: {e}")
    
    def _commit_pending(self) -> None:
        """Commit pending audits immediately (SQL Server optimized)."""
        if not self._pending_audits:
            return
            
        try:
            session = self._get_session()
            
            # Create audit log entries
            for audit_data in self._pending_audits:
                audit_log = CalculationAuditLog(**audit_data)
                session.add(audit_log)
            
            session.commit()
            self._pending_audits.clear()
            self._last_commit_time = time.time()
            
        except Exception as e:
            print(f"Warning: Audit commit failed: {e}")
            try:
                if self._session:
                    self._session.rollback()
                    self._session.close()
                    self._session = None
                self._pending_audits.clear()
            except:
                pass
    
    def flush(self) -> None:
        """Force commit all pending audits."""
        try:
            with self._lock:
                if self._pending_audits:
                    self._commit_pending()
        except Exception as e:
            print(f"Warning: Audit flush failed: {e}")
    
    def close(self) -> None:
        """Close the audit logger and commit any pending entries."""
        try:
            self.flush()
            if self._session:
                self._session.close()
                self._session = None
        except Exception as e:
            print(f"Warning: Audit logger close failed: {e}")


def get_audit_logger() -> AuditLogger:
    """Get the singleton audit logger."""
    global _audit_logger
    if _audit_logger is None:
        with _audit_logger_lock:
            if _audit_logger is None:
                _audit_logger = AuditLogger()
                # Register cleanup on exit
                atexit.register(_audit_logger.close)
    return _audit_logger


# ===== HELPER FUNCTIONS =====

def serialize_model_instance(instance) -> Dict[str, Any]:
    """Serialize a SQLAlchemy model instance to a dictionary."""
    result = {}
    for column in instance.__table__.columns:
        value = getattr(instance, column.name)
        
        # Handle datetime objects
        if isinstance(value, datetime):
            result[column.name] = value.isoformat()
        # Handle enum objects
        elif hasattr(value, 'value'):
            result[column.name] = value.value
        else:
            result[column.name] = value
    
    return result


def get_changed_fields(old_values: Dict[str, Any], new_values: Dict[str, Any]) -> List[str]:
    """Get list of fields that changed between old and new values."""
    changed = []
    
    # Check for modified fields
    for key, new_value in new_values.items():
        old_value = old_values.get(key)
        if old_value != new_value:
            changed.append(key)
    
    # Check for deleted fields (shouldn't happen in normal updates but just in case)
    for key in old_values.keys():
        if key not in new_values:
            changed.append(key)
    
    return changed


def log_audit_entry(table_name: str, record_id: int, operation: str, 
                   old_values: Optional[Dict] = None, new_values: Optional[Dict] = None) -> None:
    """Log an audit entry using the singleton logger."""
    try:
        # Determine changed fields for updates
        changed_fields = None
        if operation == 'UPDATE' and old_values and new_values:
            changed_fields = get_changed_fields(old_values, new_values)
            # If nothing actually changed, don't log
            if not changed_fields:
                return
        
        audit_data = {
            'table_name': table_name,
            'record_id': record_id,
            'operation': operation,
            'old_values': old_values,
            'new_values': new_values,
            'changed_fields': changed_fields,
            'changed_by': get_audit_user(),
            'changed_at': datetime.now()
        }
        
        logger = get_audit_logger()
        logger.add_audit(audit_data)
        
    except Exception as e:
        print(f"Warning: Could not log audit entry: {e}")


# ===== SIMPLIFIED EVENT LISTENERS =====

def setup_calculation_audit_listeners():
    """Set up SQLAlchemy event listeners for automatic audit logging."""
    
    # Import here to avoid circular imports
    from app.calculations.models import UserCalculation, SystemCalculation
    
    # Store original values before updates - simplified approach
    _original_values = {}
    
    # ===== USER CALCULATION LISTENERS =====
    
    @event.listens_for(UserCalculation, 'after_insert')
    def user_calc_after_insert(mapper, connection, target):
        """Log insert operation immediately."""
        if target.id:
            try:
                new_values = serialize_model_instance(target)
                log_audit_entry('user_calculations', target.id, 'INSERT', None, new_values)
            except Exception as e:
                print(f"Warning: User calculation insert audit failed: {e}")
    
    @event.listens_for(UserCalculation, 'before_update')
    def user_calc_before_update(mapper, connection, target):
        """Capture old values before update using SQLAlchemy history."""
        if target.id:
            try:
                # Use SQLAlchemy's built-in history tracking
                from sqlalchemy import inspect
                state = inspect(target)
                
                old_values = {}
                for attr in state.attrs:
                    hist = attr.history
                    if hist.has_changes():
                        # Get the old value (before change)
                        if hist.deleted:
                            old_val = hist.deleted[0]
                            if isinstance(old_val, datetime):
                                old_values[attr.key] = old_val.isoformat()
                            elif hasattr(old_val, 'value'):
                                old_values[attr.key] = old_val.value
                            else:
                                old_values[attr.key] = old_val
                
                # If no history available, fall back to current state
                if not old_values:
                    old_values = serialize_model_instance(target)
                
                _original_values[f"user_calc_{target.id}"] = old_values
                
            except Exception as e:
                print(f"Warning: Could not capture user calculation history: {e}")
                # Fallback to current state
                _original_values[f"user_calc_{target.id}"] = serialize_model_instance(target)
    
    @event.listens_for(UserCalculation, 'after_update')
    def user_calc_after_update(mapper, connection, target):
        """Log update operation."""
        if target.id:
            try:
                old_values = _original_values.pop(f"user_calc_{target.id}", None)
                new_values = serialize_model_instance(target)
                
                if old_values:
                    log_audit_entry('user_calculations', target.id, 'UPDATE', old_values, new_values)
            except Exception as e:
                print(f"Warning: User calculation update audit failed: {e}")
    
    @event.listens_for(UserCalculation, 'before_delete')
    def user_calc_before_delete(mapper, connection, target):
        """Log delete operation."""
        if target.id:
            try:
                old_values = serialize_model_instance(target)
                log_audit_entry('user_calculations', target.id, 'DELETE', old_values, None)
            except Exception as e:
                print(f"Warning: User calculation delete audit failed: {e}")
    
    # ===== SYSTEM CALCULATION LISTENERS =====
    
    @event.listens_for(SystemCalculation, 'after_insert')
    def system_calc_after_insert(mapper, connection, target):
        """Log insert operation."""
        if target.id:
            try:
                new_values = serialize_model_instance(target)
                log_audit_entry('system_calculations', target.id, 'INSERT', None, new_values)
            except Exception as e:
                print(f"Warning: System calculation insert audit failed: {e}")
    
    @event.listens_for(SystemCalculation, 'before_update')
    def system_calc_before_update(mapper, connection, target):
        """Capture old values before update."""
        if target.id:
            try:
                # Use SQLAlchemy's built-in history tracking
                from sqlalchemy import inspect
                state = inspect(target)
                
                old_values = {}
                for attr in state.attrs:
                    hist = attr.history
                    if hist.has_changes():
                        if hist.deleted:
                            old_val = hist.deleted[0]
                            if isinstance(old_val, datetime):
                                old_values[attr.key] = old_val.isoformat()
                            elif hasattr(old_val, 'value'):
                                old_values[attr.key] = old_val.value
                            else:
                                old_values[attr.key] = old_val
                
                # Fallback if no history
                if not old_values:
                    old_values = serialize_model_instance(target)
                
                _original_values[f"system_calc_{target.id}"] = old_values
                
            except Exception as e:
                print(f"Warning: Could not capture system calculation history: {e}")
                _original_values[f"system_calc_{target.id}"] = serialize_model_instance(target)
    
    @event.listens_for(SystemCalculation, 'after_update')
    def system_calc_after_update(mapper, connection, target):
        """Log update operation."""
        if target.id:
            try:
                old_values = _original_values.pop(f"system_calc_{target.id}", None)
                new_values = serialize_model_instance(target)
                
                if old_values:
                    log_audit_entry('system_calculations', target.id, 'UPDATE', old_values, new_values)
            except Exception as e:
                print(f"Warning: System calculation update audit failed: {e}")
    
    @event.listens_for(SystemCalculation, 'before_delete')
    def system_calc_before_delete(mapper, connection, target):
        """Log delete operation."""
        if target.id:
            try:
                old_values = serialize_model_instance(target)
                log_audit_entry('system_calculations', target.id, 'DELETE', old_values, None)
            except Exception as e:
                print(f"Warning: System calculation delete audit failed: {e}")


# Initialize the event listeners when this module is imported
setup_calculation_audit_listeners()


