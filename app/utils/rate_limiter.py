from fastapi import Request
from fastapi.responses import JSONResponse
import time
from collections import defaultdict
import asyncio
from typing import Dict, Tuple
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class RateLimiter:
    def __init__(self, requests_per_minute: int = None):
        self.requests_per_minute = int(os.getenv("REQUESTS_PER_MINUTE", "60"))
        self.requests: Dict[str, list] = defaultdict(list)
        self.lock = asyncio.Lock()

    async def is_rate_limited(self, client_id: str) -> bool:
        """Check if a client has exceeded the rate limit."""
        async with self.lock:
            now = time.time()
            # Remove requests older than 1 minute
            self.requests[client_id] = [
                req_time for req_time in self.requests[client_id]
                if now - req_time < 60
            ]
            
            if len(self.requests[client_id]) >= self.requests_per_minute:
                return True
            
            self.requests[client_id].append(now)
            return False

    def get_client_id(self, request: Request) -> str:
        """Get client identifier from request."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0]
        return request.client.host

rate_limiter = RateLimiter()

async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware."""
    client_id = rate_limiter.get_client_id(request)
    
    if await rate_limiter.is_rate_limited(client_id):
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Too many requests. Please try again later.",
                "retry_after": 60
            },
            headers={"Retry-After": "60"}
        )
    
    response = await call_next(request)
    return response 