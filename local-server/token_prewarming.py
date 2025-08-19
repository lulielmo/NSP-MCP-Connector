"""
Smart Token Pre-warming for NSP MCP Connector
Keeps NSP authentication token warm to eliminate timeout issues
"""

import threading
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TokenSchedule:
    """Information about token refresh scheduling"""
    expires_at: Optional[datetime] = None
    refresh_at: Optional[datetime] = None
    refresh_buffer_minutes: int = 5
    next_refresh_timer: Optional[threading.Timer] = None

class SmartTokenWarmer:
    """Intelligent token pre-warming system"""
    
    def __init__(self, nsp_client):
        self.nsp_client = nsp_client
        self.running = False
        self.schedule = TokenSchedule()
        self.refresh_buffer_minutes = int(os.getenv('PREWARMING_REFRESH_BUFFER', '5'))
        
        logger.info(f"SmartTokenWarmer initialized with {self.refresh_buffer_minutes}min refresh buffer")
    
    def parse_token_expiry(self, expires_str: str) -> Optional[datetime]:
        """Parse NSP token expiry string to datetime"""
        try:
            # Handle NSP format: "2025-08-19T21:54:41.6073688Z"
            if expires_str.endswith('Z'):
                # Remove Z and handle potential microsecond precision issues
                clean_str = expires_str.rstrip('Z')
                
                # NSP sometimes returns 7 digits for microseconds, Python expects max 6
                if '.' in clean_str:
                    date_part, microsec_part = clean_str.split('.')
                    # Truncate microseconds to 6 digits if longer
                    if len(microsec_part) > 6:
                        microsec_part = microsec_part[:6]
                    clean_str = f"{date_part}.{microsec_part}"
                
                # Add UTC timezone
                clean_str += '+00:00'
                return datetime.fromisoformat(clean_str)
            
            # Fallback for other formats
            return datetime.fromisoformat(expires_str)
        except Exception as e:
            logger.error(f"Failed to parse token expiry '{expires_str}': {e}")
            return None
    
    def get_current_token_expiry(self) -> Optional[datetime]:
        """Get expiry time of current token"""
        try:
            token_info = self.nsp_client.get_token_info()
            if token_info['has_token'] and token_info['expires']:
                return self.parse_token_expiry(token_info['expires'])
        except Exception as e:
            logger.error(f"Failed to get token expiry: {e}")
        return None
    
    def calculate_refresh_time(self, expiry_time: datetime) -> datetime:
        """Calculate when to refresh token (buffer minutes before expiry)"""
        return expiry_time - timedelta(minutes=self.refresh_buffer_minutes)
    
    def cancel_scheduled_refresh(self):
        """Cancel any currently scheduled refresh"""
        if self.schedule.next_refresh_timer:
            self.schedule.next_refresh_timer.cancel()
            self.schedule.next_refresh_timer = None
            logger.debug("Cancelled scheduled token refresh")
    
    def schedule_next_refresh(self) -> bool:
        """Schedule next token refresh based on current token expiry"""
        expiry_time = self.get_current_token_expiry()
        
        if not expiry_time:
            logger.warning("Cannot schedule refresh - no valid token expiry found")
            return False
        
        refresh_time = self.calculate_refresh_time(expiry_time)
        now = datetime.now(timezone.utc)
        
        # Ensure refresh time is in the future
        if refresh_time <= now:
            logger.warning(f"Token expires too soon ({expiry_time}), refreshing immediately")
            threading.Thread(target=self.refresh_token, daemon=True).start()
            return True
        
        delay_seconds = (refresh_time - now).total_seconds()
        
        # Cancel any existing timer
        self.cancel_scheduled_refresh()
        
        # Schedule new refresh
        self.schedule.next_refresh_timer = threading.Timer(delay_seconds, self.refresh_token)
        self.schedule.next_refresh_timer.daemon = True
        self.schedule.next_refresh_timer.start()
        
        # Update schedule info
        self.schedule.expires_at = expiry_time
        self.schedule.refresh_at = refresh_time
        
        logger.info(f"🕒 Token refresh scheduled:")
        logger.info(f"   Expires at: {expiry_time}")
        logger.info(f"   Refresh at: {refresh_time} ({delay_seconds/60:.1f} minutes)")
        
        return True
    
    def refresh_token(self):
        """Refresh NSP token and schedule next refresh"""
        if not self.running:
            logger.debug("Token warmer stopped - skipping refresh")
            return
            
        try:
            logger.info("🔥 Pre-warming: Refreshing NSP token...")
            
            # Force new authentication by clearing current token
            old_token_info = self.nsp_client.get_token_info()
            self.nsp_client.auth_token.token = ""
            self.nsp_client.auth_token.expires = ""
            
            # Perform fresh authentication
            success = self.nsp_client.ensure_valid_token()
            
            if success:
                new_token_info = self.nsp_client.get_token_info()
                logger.info("✅ Token successfully refreshed via pre-warming")
                logger.info(f"   New token expires: {new_token_info['expires']}")
                
                # Schedule next refresh based on new token
                if not self.schedule_next_refresh():
                    logger.error("Failed to schedule next refresh after successful token refresh")
                    self._schedule_retry_refresh(300)  # Retry in 5 minutes
            else:
                logger.error("❌ Token refresh failed - scheduling retry")
                self._schedule_retry_refresh(300)  # Retry in 5 minutes
                
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            self._schedule_retry_refresh(300)  # Retry in 5 minutes
    
    def _schedule_retry_refresh(self, delay_seconds: int):
        """Schedule a retry refresh after failure"""
        if not self.running:
            return
            
        self.cancel_scheduled_refresh()
        self.schedule.next_refresh_timer = threading.Timer(delay_seconds, self.refresh_token)
        self.schedule.next_refresh_timer.daemon = True
        self.schedule.next_refresh_timer.start()
        
        logger.info(f"🔄 Token refresh retry scheduled in {delay_seconds/60:.1f} minutes")
    
    def start_prewarming(self) -> bool:
        """Start intelligent token pre-warming"""
        if self.running:
            logger.warning("Token pre-warming already running")
            return True
            
        logger.info("🚀 Starting intelligent token pre-warming...")
        self.running = True
        
        # Check current token status
        token_info = self.nsp_client.get_token_info()
        
        if not token_info['has_token'] or token_info['is_expired']:
            logger.info("No valid token found - performing initial authentication...")
            success = self.nsp_client.ensure_valid_token()
            
            if not success:
                logger.error("❌ Failed to obtain initial token - pre-warming cannot start")
                self.running = False
                return False
                
            logger.info("✅ Initial token obtained successfully")
        else:
            logger.info("✅ Valid token already exists")
        
        # Schedule first refresh
        if self.schedule_next_refresh():
            logger.info("🔥 Token pre-warming system active")
            return True
        else:
            logger.error("❌ Failed to schedule initial token refresh")
            self.running = False
            return False
    
    def stop_prewarming(self):
        """Stop token pre-warming"""
        if not self.running:
            return
            
        logger.info("🛑 Stopping token pre-warming...")
        self.running = False
        self.cancel_scheduled_refresh()
        
        # Clear schedule info
        self.schedule = TokenSchedule()
        
        logger.info("✅ Token pre-warming stopped")
    
    def get_status(self) -> dict:
        """Get current pre-warming status"""
        token_info = self.nsp_client.get_token_info()
        now = datetime.now(timezone.utc)
        
        status = {
            "prewarming_active": self.running,
            "refresh_buffer_minutes": self.refresh_buffer_minutes,
            "token": {
                "has_token": token_info['has_token'],
                "is_expired": token_info['is_expired'],
                "expires_at": token_info['expires'],
                "username": token_info['username']
            },
            "schedule": {
                "expires_at": self.schedule.expires_at.isoformat() if self.schedule.expires_at else None,
                "refresh_at": self.schedule.refresh_at.isoformat() if self.schedule.refresh_at else None,
                "next_refresh_in_minutes": None
            }
        }
        
        # Calculate time until next refresh
        if self.schedule.refresh_at and self.running:
            time_until_refresh = (self.schedule.refresh_at - now).total_seconds() / 60
            status["schedule"]["next_refresh_in_minutes"] = max(0, time_until_refresh)
        
        return status
    
    def force_refresh(self) -> bool:
        """Force immediate token refresh (for testing/manual trigger)"""
        if not self.running:
            logger.warning("Cannot force refresh - pre-warming not active")
            return False
            
        logger.info("🔧 Manual token refresh triggered")
        
        # Cancel scheduled refresh and do immediate refresh
        self.cancel_scheduled_refresh()
        
        # Run refresh in separate thread to avoid blocking
        refresh_thread = threading.Thread(target=self.refresh_token, daemon=True)
        refresh_thread.start()
        
        return True
