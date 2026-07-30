# NOTE: condensed file combining all tables. In production split into modules.
from datetime import datetime, date, time
from sqlalchemy import (
    Column, Integer, SmallInteger, BigInteger, String, Boolean, DateTime, Date, Time,
    ForeignKey, UniqueConstraint, JSON, Float, Numeric, LargeBinary, Text
)
from sqlalchemy.orm import relationship
from .base import Base

# Roles & Users
class Role(Base):
    __tablename__ = "roles"
    role_id = Column(Integer, primary_key=True)
    role_name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)

class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True)
    full_name = Column(String(200))
    email = Column(String(256), unique=True, nullable=False)
    phone = Column(String(40))
    password_hash = Column(String(512), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserRole(Base):
    __tablename__ = "user_roles"
    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.role_id"), primary_key=True)

# Sites & Zones
class Site(Base):
    __tablename__ = "sites"
    site_id = Column(Integer, primary_key=True)
    site_name = Column(String(200), nullable=False)
    address = Column(Text)
    city = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    zones = relationship("Zone", back_populates="site")

class Zone(Base):
    __tablename__ = "zones"
    zone_id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey("sites.site_id"), nullable=False)
    zone_name = Column(String(200))
    zone_type = Column(String(50))
    polygon_geojson = Column(JSON)
    risk_level_default = Column(SmallInteger, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    site = relationship("Site", back_populates="zones")

# Capture devices
class Camera(Base):
    __tablename__ = "cameras"
    camera_id = Column(Integer, primary_key=True)
    zone_id = Column(Integer, ForeignKey("zones.zone_id"))
    camera_code = Column(String(100), unique=True, nullable=False)
    stream_url = Column(String(1024))
    model = Column(String(100))
    status = Column(String(50), default="active")
    installed_at = Column(DateTime)

class NetworkSensor(Base):
    __tablename__ = "network_sensors"
    sensor_id = Column(Integer, primary_key=True)
    zone_id = Column(Integer, ForeignKey("zones.zone_id"))
    sensor_code = Column(String(100), unique=True, nullable=False)
    sensor_type = Column(String(100))
    location_desc = Column(Text)
    status = Column(String(50), default="active")
    installed_at = Column(DateTime)

# Modules & rules
class SystemModule(Base):
    __tablename__ = "system_modules"
    module_id = Column(Integer, primary_key=True)
    module_code = Column(String(100), unique=True, nullable=False)
    module_name = Column(String(200))
    module_type = Column(String(50))
    version = Column(String(50))
    is_enabled = Column(Boolean, default=True)
    config_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class EventType(Base):
    __tablename__ = "event_types"
    event_type_id = Column(Integer, primary_key=True)
    type_code = Column(String(100), unique=True, nullable=False)
    type_name_ar = Column(String(200))
    type_name_en = Column(String(200))
    default_severity = Column(SmallInteger, default=1)

class DetectionRule(Base):
    __tablename__ = "detection_rules"
    rule_id = Column(Integer, primary_key=True)
    module_id = Column(Integer, ForeignKey("system_modules.module_id"))
    event_type_id = Column(Integer, ForeignKey("event_types.event_type_id"))
    zone_id = Column(Integer, ForeignKey("zones.zone_id"))
    min_confidence = Column(Numeric(4,3), default=0.0)
    active_from = Column(Time)
    active_to = Column(Time)
    is_active = Column(Boolean, default=True)
    min_rssi_threshold = Column(Integer)
    min_dwell_seconds = Column(Integer)
    baseline_required = Column(Boolean, default=False)

# Events & evidence
class Event(Base):
    __tablename__ = "events"
    event_id = Column(BigInteger, primary_key=True)
    event_type_id = Column(Integer, ForeignKey("event_types.event_type_id"))
    module_id = Column(Integer, ForeignKey("system_modules.module_id"))
    zone_id = Column(Integer, ForeignKey("zones.zone_id"))
    camera_id = Column(Integer, ForeignKey("cameras.camera_id"))
    sensor_id = Column(Integer, ForeignKey("network_sensors.sensor_id"))
    detected_at = Column(DateTime)
    confidence = Column(Numeric(4,3))
    severity = Column(SmallInteger)
    status = Column(String(50), default="new")
    description = Column(Text)
    raw_payload = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)
    resolved_by = Column(Integer, ForeignKey("users.user_id"))

class EventEvidence(Base):
    __tablename__ = "event_evidence"
    evidence_id = Column(BigInteger, primary_key=True)
    event_id = Column(BigInteger, ForeignKey("events.event_id"))
    evidence_type = Column(String(50))
    file_url = Column(String(1024))
    thumbnail_url = Column(String(1024))
    created_at = Column(DateTime, default=datetime.utcnow)

# Alerts & reports
class NotificationChannel(Base):
    __tablename__ = "notification_channels"
    channel_id = Column(Integer, primary_key=True)
    channel_type = Column(String(50))
    channel_config = Column(JSON)
    is_active = Column(Boolean, default=True)

class Alert(Base):
    __tablename__ = "alerts"
    alert_id = Column(BigInteger, primary_key=True)
    event_id = Column(BigInteger, ForeignKey("events.event_id"))
    channel_id = Column(Integer, ForeignKey("notification_channels.channel_id"))
    sent_to_user_id = Column(Integer, ForeignKey("users.user_id"))
    sent_at = Column(DateTime)
    delivery_status = Column(String(50))
    read_at = Column(DateTime)

class Report(Base):
    __tablename__ = "reports"
    report_id = Column(BigInteger, primary_key=True)
    event_id = Column(BigInteger, ForeignKey("events.event_id"))
    generated_at = Column(DateTime)
    report_format = Column(String(20))
    file_url = Column(String(1024))
    generated_by = Column(Integer, ForeignKey("users.user_id"))

# Network devices & whitelist
class NetworkDevice(Base):
    __tablename__ = "network_devices"
    device_id = Column(BigInteger, primary_key=True)
    mac_address = Column(String(50), unique=True, nullable=False)
    device_type = Column(String(100))
    vendor = Column(String(100))
    first_seen = Column(DateTime)
    last_seen = Column(DateTime)
    sighting_count = Column(Integer, default=0)
    avg_rssi = Column(Numeric(6,2))
    recurring_score = Column(Numeric(4,3))
    classification = Column(String(100))
    updated_at = Column(DateTime)

class WhitelistDevice(Base):
    __tablename__ = "whitelist_devices"
    whitelist_id = Column(Integer, primary_key=True)
    mac_address = Column(String(50), unique=True, nullable=False)
    owner_name = Column(String(200))
    zone_id = Column(Integer, ForeignKey("zones.zone_id"))
    added_by = Column(Integer, ForeignKey("users.user_id"))
    added_at = Column(DateTime, default=datetime.utcnow)
    source = Column(String(50))
    suggestion_id = Column(Integer, ForeignKey("whitelist_suggestions.suggestion_id"))
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime)

class NetworkDeviceSighting(Base):
    __tablename__ = "network_device_sightings"
    sighting_id = Column(BigInteger, primary_key=True)
    device_id = Column(BigInteger, ForeignKey("network_devices.device_id"))
    sensor_id = Column(Integer, ForeignKey("network_sensors.sensor_id"))
    event_id = Column(BigInteger, ForeignKey("events.event_id"))
    signal_strength = Column(Integer)
    seen_at = Column(DateTime)

# Authorized entities
class AuthorizedPerson(Base):
    __tablename__ = "authorized_persons"
    person_id = Column(BigInteger, primary_key=True)
    full_name = Column(String(200))
    national_id = Column(String(100))
    face_embedding = Column(LargeBinary)  # ENCRYPT at application level or db-level pgcrypto
    zone_access = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class AuthorizedVehicle(Base):
    __tablename__ = "authorized_vehicles"
    vehicle_id = Column(BigInteger, primary_key=True)
    plate_number = Column(String(100), unique=True)
    owner_name = Column(String(200))
    zone_access = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

# Baseline learning & stats
class BaselineLearningSession(Base):
    __tablename__ = "baseline_learning_sessions"
    session_id = Column(BigInteger, primary_key=True)
    zone_id = Column(Integer, ForeignKey("zones.zone_id"))
    sensor_id = Column(Integer, ForeignKey("network_sensors.sensor_id"))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    status = Column(String(50))
    created_by = Column(Integer, ForeignKey("users.user_id"))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class DeviceZoneDailyStat(Base):
    __tablename__ = "device_zone_daily_stats"
    stat_id = Column(BigInteger, primary_key=True)
    device_id = Column(BigInteger, ForeignKey("network_devices.device_id"))
    zone_id = Column(Integer, ForeignKey("zones.zone_id"))
    stat_date = Column(Date)
    first_seen_time = Column(Time)
    last_seen_time = Column(Time)
    total_dwell_seconds = Column(Integer)
    sighting_count = Column(Integer)
    avg_rssi = Column(Numeric(6,2))
    __table_args__ = (UniqueConstraint('device_id', 'zone_id', 'stat_date', name='uq_device_zone_date'),)

class WhitelistSuggestion(Base):
    __tablename__ = "whitelist_suggestions"
    suggestion_id = Column(BigInteger, primary_key=True)
    device_id = Column(BigInteger, ForeignKey("network_devices.device_id"))
    zone_id = Column(Integer, ForeignKey("zones.zone_id"))
    sensor_id = Column(Integer, ForeignKey("network_sensors.sensor_id"))
    reason = Column(Text)
    recurring_score = Column(Numeric(4,3))
    suggested_at = Column(DateTime)
    status = Column(String(50))
    reviewed_by = Column(Integer, ForeignKey("users.user_id"))
    reviewed_at = Column(DateTime)

# Feedback & retraining
class ModelFeedbackLog(Base):
    __tablename__ = "model_feedback_log"
    feedback_id = Column(BigInteger, primary_key=True)
    event_id = Column(BigInteger, ForeignKey("events.event_id"))
    module_id = Column(Integer, ForeignKey("system_modules.module_id"))
    original_confidence = Column(Numeric(4,3))
    original_severity = Column(SmallInteger)
    human_classification = Column(String(100))
    corrected_event_type_id = Column(Integer, ForeignKey("event_types.event_type_id"))
    notes = Column(Text)
    reviewed_by = Column(Integer, ForeignKey("users.user_id"))
    reviewed_at = Column(DateTime)
    used_in_retraining = Column(Boolean, default=False)
    retraining_batch_id = Column(Integer, ForeignKey("model_retraining_batches.batch_id"))

class ModelRetrainingBatch(Base):
    __tablename__ = "model_retraining_batches"
    batch_id = Column(BigInteger, primary_key=True)
    module_id = Column(Integer, ForeignKey("system_modules.module_id"))
    batch_started_at = Column(DateTime)
    batch_completed_at = Column(DateTime)
    sample_count = Column(Integer)
    previous_model_version = Column(String(100))
    new_model_version = Column(String(100))
    precision_before = Column(Numeric(4,3))
    precision_after = Column(Numeric(4,3))
    recall_before = Column(Numeric(4,3))
    recall_after = Column(Numeric(4,3))
    performance_notes = Column(Text)
    created_by = Column(Integer, ForeignKey("users.user_id"))
    created_at = Column(DateTime, default=datetime.utcnow)

# Audit logs
class AuditLog(Base):
    __tablename__ = "audit_logs"
    log_id = Column(BigInteger, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    action = Column(String(200))
    target_table = Column(String(200))
    target_id = Column(BigInteger)
    details = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
