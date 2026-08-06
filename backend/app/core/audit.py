import json
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from app.core.context import request_info
from app.modules.system.models import AuditLog


def serialize_model(instance) -> dict:
    """Serialize model instance fields into a dict."""
    d = {}
    for column in instance.__table__.columns:
        val = getattr(instance, column.name)
        if isinstance(val, datetime | date):
            d[column.name] = val.isoformat()
        elif isinstance(val, uuid.UUID):
            d[column.name] = str(val)
        elif isinstance(val, Decimal):
            d[column.name] = float(val)
        else:
            try:
                json.dumps(val)
                d[column.name] = val
            except Exception:
                d[column.name] = str(val)
    return d


def clean_dict(d: dict) -> dict:
    """Clean dictionary values to make them JSON serializable."""
    cleaned = {}
    for k, v in d.items():
        if isinstance(v, datetime | date):
            cleaned[k] = v.isoformat()
        elif isinstance(v, uuid.UUID):
            cleaned[k] = str(v)
        elif isinstance(v, Decimal):
            cleaned[k] = float(v)
        else:
            try:
                json.dumps(v)
                cleaned[k] = v
            except Exception:
                cleaned[k] = str(v)
    return cleaned


@event.listens_for(Session, "before_flush")
def before_flush(session, flush_context, instances):
    # Check if there is any AuditLog in the session already to prevent recursion
    for obj in session.new:
        if isinstance(obj, AuditLog):
            return

    req = request_info.get() or {}
    user_id = req.get("user_id")
    ip_address = req.get("ip_address")
    user_agent = req.get("user_agent")

    audit_logs_to_add = []

    def get_valid_uuid(val) -> uuid.UUID | None:
        if val is None:
            return None
        if isinstance(val, uuid.UUID):
            return val
        if isinstance(val, str):
            try:
                return uuid.UUID(val)
            except ValueError:
                return None
        return None

    def get_object_user_id(obj) -> uuid.UUID | None:
        obj_u_id = get_valid_uuid(getattr(obj, "user_id", None))
        if obj_u_id is not None:
            return obj_u_id
        # For User objects, their own ID is the user_id
        if obj.__class__.__name__ == "User":
            return get_valid_uuid(getattr(obj, "id", None))
        return get_valid_uuid(user_id)

    # Insertions
    for obj in session.new:
        if hasattr(obj, "__tablename__") and obj.__tablename__ != "audit_logs":
            r_id = get_valid_uuid(getattr(obj, "restaurant_id", None))
            u_id = get_object_user_id(obj)
            new_vals = serialize_model(obj)
            audit_logs_to_add.append(AuditLog(
                restaurant_id=r_id,
                user_id=u_id,
                action="insert",
                resource_type=obj.__class__.__name__,
                resource_id=str(getattr(obj, "id", "")),
                new_values=json.dumps(new_vals),
                ip_address=ip_address,
                user_agent=user_agent
            ))

    # Modifications
    for obj in session.dirty:
        if hasattr(obj, "__tablename__") and obj.__tablename__ != "audit_logs":
            r_id = get_valid_uuid(getattr(obj, "restaurant_id", None))
            u_id = get_object_user_id(obj)
            state = inspect(obj)
            old_vals = {}
            new_vals = {}
            for attr in state.attrs:
                hist = attr.load_history()
                if hist.has_changes():
                    old_vals[attr.key] = hist.deleted[0] if hist.deleted else None
                    new_vals[attr.key] = hist.added[0] if hist.added else getattr(obj, attr.key)

            if old_vals or new_vals:
                audit_logs_to_add.append(AuditLog(
                    restaurant_id=r_id,
                    user_id=u_id,
                    action="update",
                    resource_type=obj.__class__.__name__,
                    resource_id=str(getattr(obj, "id", "")),
                    old_values=json.dumps(clean_dict(old_vals)),
                    new_values=json.dumps(clean_dict(new_vals)),
                    ip_address=ip_address,
                    user_agent=user_agent
                ))

    # Deletions
    for obj in session.deleted:
        if hasattr(obj, "__tablename__") and obj.__tablename__ != "audit_logs":
            r_id = get_valid_uuid(getattr(obj, "restaurant_id", None))
            u_id = get_object_user_id(obj)
            old_vals = serialize_model(obj)
            audit_logs_to_add.append(AuditLog(
                restaurant_id=r_id,
                user_id=u_id,
                action="delete",
                resource_type=obj.__class__.__name__,
                resource_id=str(getattr(obj, "id", "")),
                old_values=json.dumps(old_vals),
                ip_address=ip_address,
                user_agent=user_agent
            ))

    for log in audit_logs_to_add:
        session.add(log)
