import hashlib
from django.core.cache import cache

def hash_identifier(value):
    """
    Hash an identifier before using it in a cache key.
    This prevents sensitive identifiers such as email addresses
    from appearing directly in cache keys.
    """
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()

def allow_request(prefix, identifier, limit, period):
    """
    Allow a request if the identifier has not exceeded the limit.

    Example:
        allow_request(
            prefix="otp_email_register",
            identifier="user@example.com",
            limit=5,
            period=900,
        )
    """

    identifier = hash_identifier(identifier)
    key = f"rate:{prefix}:{identifier}"
    current = cache.get(key)
    if current is None:
        created = cache.add(key, 1, timeout=period)

        if created:
            return True

        # Another request may have created the key between
        # cache.get() and cache.add().
        current = cache.get(key)

    if current is None:
        # Extremely defensive fallback.
        return True

    if current >= limit:
        return False

    try:
        new_value = cache.incr(key)
    except ValueError:
        # Cache key disappeared between get/incr.
        cache.set(
            key,
            1,
            timeout=period,
        )
        return True

    return new_value <= limit

def get_client_ip(request):
    """
    Return the client's IP address.

    IMPORTANT:
    REMOTE_ADDR is used deliberately.

    Do not blindly trust X-Forwarded-For because clients can
    spoof that header. If the application is behind a trusted
    reverse proxy/load balancer, configure trusted proxy handling
    separately.
    """
    return request.META.get(
        "REMOTE_ADDR",
        "unknown",
    )

def allow_email_otp_request(
    email,
    purpose,
    limit=5,
    period=900,
    ):
    """
    Rate limit OTP generation by email address.
    """
    prefix = f"otp_email_{purpose.lower()}"

    return allow_request(
        prefix=prefix,
        identifier=email.lower().strip(),
        limit=limit,
        period=period,
    )

def allow_ip_otp_request(ip_address, purpose, limit=10, period=900,):
    """
    Rate limit OTP generation by IP address.
    """

    prefix = f"otp_ip_{purpose.lower()}"

    return allow_request(
        prefix=prefix,
        identifier=ip_address,
        limit=limit,
        period=period,
    )

def allow_global_otp_request(
    purpose,
    limit=1000,
    period=60,
    ):
    """
    Global/system-level OTP generation protection.

    This protects the email provider and application even when
    attackers distribute requests across many email addresses
    and IP addresses.
    """

    key = f"rate:otp_global:{purpose.lower()}"

    current = cache.get(key)

    if current is None:
        created = cache.add(
            key,
            1,
            timeout=period,
        )

        if created:
            return True

        current = cache.get(key)

    if current is None:
        return True

    if current >= limit:
        return False

    try:
        new_value = cache.incr(key)
    except ValueError:
        cache.set(
            key,
            1,
            timeout=period,
        )
        return True

    return new_value <= limit

class OTPRateLimitExceeded(Exception):
    """
    Raised when an OTP request exceeds a configured rate limit.
    """
    pass

def check_otp_request_allowed(email, ip_address, purpose,):
    """
    Apply email, IP and global rate limits to an OTP request.

    Raises:
        OTPRateLimitExceeded
    """

    # ---------------------------------------------------------
    # Email limit
    # ---------------------------------------------------------

    if not allow_email_otp_request(
        email=email,
        purpose=purpose,
        limit=5,
        period=900,
    ):
        raise OTPRateLimitExceeded(
            "OTP email rate limit exceeded."
        )

    # ---------------------------------------------------------
    # IP limit
    # ---------------------------------------------------------

    if not allow_ip_otp_request(
        ip_address=ip_address,
        purpose=purpose,
        limit=10,
        period=900,
    ):
        raise OTPRateLimitExceeded(
            "OTP IP rate limit exceeded."
        )

    # ---------------------------------------------------------
    # Global/system limit
    # ---------------------------------------------------------

    if not allow_global_otp_request(
        purpose=purpose,
        limit=1000,
        period=60,
    ):
        raise OTPRateLimitExceeded(
            "Global OTP rate limit exceeded."
        )

    return True
