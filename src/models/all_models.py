@@
 class User(Base):
@@
     created_at = Column(DateTime, default=datetime.utcnow)
@@
 class AuditLog(Base):
     __tablename__ = "audit_logs"
     log_id = Column(BigInteger, primary_key=True)
     user_id = Column(Integer, ForeignKey("users.user_id"))
     action = Column(String(200))
     target_table = Column(String(200))
     target_id = Column(BigInteger)
     details = Column(JSON)
     created_at = Column(DateTime, default=datetime.utcnow)
+
+
+# Refresh tokens for rotation / revocation
+class RefreshToken(Base):
+    __tablename__ = "refresh_tokens"
+    token_id = Column(String(100), primary_key=True)
+    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
+    revoked = Column(Boolean, default=False)
+    created_at = Column(DateTime, default=datetime.utcnow)
+    expires_at = Column(DateTime)
+    replaced_by = Column(String(100))
