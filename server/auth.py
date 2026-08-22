import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple
import server.config as config

class AuthManager:
    def __init__(self, database):
        self.db = database
        self.sessions = {}
        self.login_attempts = {}
    
    def login(self, username: str, password: str, ip_address: str) -> Optional[Tuple]:
        if self._is_ip_blocked(ip_address):
            self.db.log_audit(None, "LOGIN_BLOCKED", f"IP: {ip_address}", ip_address)
            return None
        
        user = self.db.verify_user(username, password)
        if user is None:
            self._register_failed_attempt(ip_address)
            self.db.log_audit(None, "LOGIN_FAILED", f"User: {username}", ip_address)
            return None
        
        token = secrets.token_hex(32)
        expires_at = datetime.now() + timedelta(seconds=config.SESSION_TIMEOUT)
        self.sessions[token] = (user.id, expires_at)
        self._clear_failed_attempts(ip_address)
        self.db.update_user_status(user.id, True)
        self.db.log_audit(user.id, "LOGIN_SUCCESS", f"User: {username}", ip_address)
        return token, user
    
    def logout(self, token: str, ip_address: str):
        if token in self.sessions:
            user_id, _ = self.sessions[token]
            del self.sessions[token]
            self.db.update_user_status(user_id, False)
            self.db.log_audit(user_id, "LOGOUT", "", ip_address)
    
    def verify_session(self, token: str) -> Optional[int]:
        if token not in self.sessions:
            return None
        user_id, expires_at = self.sessions[token]
        if datetime.now() > expires_at:
            del self.sessions[token]
            self.db.update_user_status(user_id, False)
            return None
        return user_id
    
    def _is_ip_blocked(self, ip_address: str) -> bool:
        if ip_address not in self.login_attempts:
            return False
        attempts, last_attempt = self.login_attempts[ip_address]
        if attempts >= config.MAX_LOGIN_ATTEMPTS:
            time_since_last = (datetime.now() - last_attempt).total_seconds()
            if time_since_last < config.BLOCK_TIME:
                return True
            else:
                del self.login_attempts[ip_address]
        return False
    
    def _register_failed_attempt(self, ip_address: str):
        if ip_address in self.login_attempts:
            attempts, _ = self.login_attempts[ip_address]
            self.login_attempts[ip_address] = (attempts + 1, datetime.now())
        else:
            self.login_attempts[ip_address] = (1, datetime.now())
    
    def _clear_failed_attempts(self, ip_address: str):
        if ip_address in self.login_attempts:
            del self.login_attempts[ip_address]
    
    def cleanup_expired_sessions(self):
        now = datetime.now()
        expired = [token for token, (user_id, expires_at) in self.sessions.items()
                   if now > expires_at]
        for token in expired:
            user_id, _ = self.sessions[token]
            self.db.update_user_status(user_id, False)
            del self.sessions[token]
