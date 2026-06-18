"""API key authentication middleware."""
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from subdomain_hunter.config import get_settings

security = HTTPBearer(auto_error=False)
settings = get_settings()


async def verify_api_key(credentials: HTTPAuthCredentials = Depends(security)):
    """Verify API key from bearer token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Valid API key required",
        )
    
    if credentials.credentials != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    
    return credentials.credentials
