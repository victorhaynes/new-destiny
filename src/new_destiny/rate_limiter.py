from urllib.parse import urlparse
from .rate_limit_helpers import derive_riot_service, derive_riot_method_config
from .rate_limit_exceptions import ApplicationRateLimitExceeded, MethodRateLimitExceeded, ServiceRateLimitExceeded, UnspecifiedRateLimitExceeded
from .settings.config import ND_CUSTOM_MINUTES_LIMIT, ND_CUSTOM_MINUTES_WINDOW, ND_CUSTOM_SECONDS_LIMIT, ND_CUSTOM_SECONDS_WINDOW, ND_PRODUCTION

###### Rate Limier Classes ###########
###### Rate Limier Classes ###########
###### Rate Limier Classes ###########
###### All time units are seconds ####
###### ex. minutes_windows = 600 is ##
###### == 10 minutes #################

class BaseRateLimitingLogic:
    """Base class for rate limiting logic using Redis."""
    def __init__(self, riot_endpoint: str, async_redis_client):
        self.riot_endpoint = riot_endpoint
        self.subdomain = self.get_subdomain(riot_endpoint)
        self.redis = async_redis_client

    def get_subdomain(self, riot_endpoint: str):
        parsed_url = urlparse(riot_endpoint)
        hostname = parsed_url.hostname  # Ex. "na1.api.riotgames.com"
        
        if not hostname:
            raise ValueError(f"Invalid URL: No hostname found. Subdomain (what Riot docs inaccurately calls per 'region' for per-region enforcement) cannot be determined from {riot_endpoint}")

        subdomain = hostname.split(".")[0]  # Extracts "na1" from "na1.api.riotgames.com"
        return subdomain.lower()


class ApplicationRateLimiter(BaseRateLimitingLogic):
    """Rate limiter for app-wide rate limits per subdomain (what Riot incorrectly calls region)."""
    def __init__(self, riot_endpoint: str, async_redis_client):
        super().__init__(riot_endpoint, async_redis_client)
        if ND_PRODUCTION:
            # Limit / max count for the two types of rate limits
            self.seconds_limit = ND_CUSTOM_SECONDS_LIMIT or 500
            self.minutes_limit = ND_CUSTOM_MINUTES_LIMIT or 30000
            # Validity windows in seconds for the two types of rate limits
            self.seconds_window = ND_CUSTOM_SECONDS_WINDOW or 10
            self.minutes_window = ND_CUSTOM_MINUTES_WINDOW or 600
        else:
            # Limit / max count for the two types of rate limits
            self.seconds_limit = 20
            self.minutes_limit = 100
            # Validity windows in seconds for the two types of rate limits
            self.seconds_window = 1
            self.minutes_window = 120
        # Redis keys that will identify what application rate limit we are checking
        self.seconds_key = self.generate_key("seconds")
        self.minutes_key = self.generate_key("minutes")
        self.blocking_key = self.generate_blocking_key()

        # Initialize script content but don't load yet
        self.check_and_increment_script_content = self.get_check_and_increment_script()
        self.blocking_script_content = self.get_blocking_script()
        
        # SHA values will be set during initialization
        self.check_and_increment_sha = None
        self.blocking_script_sha = None

    def generate_key(self, window_type):
        """
        Generate application rate limit keys.
        This holds an integer count value that gets incremented by 1 per request. One half of what is_allowed() checks.
        """
        return f"nd_application_rate_limit_{self.subdomain}_key_for_{window_type}"
    
    def generate_blocking_key(self):
        """
        Generate a blocking key for the application rate limiter.
        If "leakage" occurs (i.e. my internal counts fail to prevent an inbound 429 from Riot
        either becasue our counts are out of sync or Riot issues a 429 for an unknown reason)
        then we use this blocking key with a TTL set to the "Retry-After" header's integer value so we respect the timeout
        for as long as it is valid whether or not our internal counts hit their limit.
        """
        return f"nd_blocking_key_for_application_rate_limit_{self.subdomain}"


    def get_check_and_increment_script(self):
        """Returns the Lua script content for atomic check and increment operations."""
        return """
        -- Keys: [seconds_key, minutes_key, blocking_key]
        -- Args: [seconds_limit, minutes_limit, seconds_window, minutes_window]
        
        local seconds_key = KEYS[1]
        local minutes_key = KEYS[2]
        local blocking_key = KEYS[3]
        
        local seconds_limit = tonumber(ARGV[1])
        local minutes_limit = tonumber(ARGV[2])
        local seconds_window = tonumber(ARGV[3])
        local minutes_window = tonumber(ARGV[4])
        
        -- Check if blocking key exists (external rate limit was hit)
        local is_blocked = redis.call('EXISTS', blocking_key)
        if is_blocked == 1 then
            local block_ttl = redis.call('TTL', blocking_key)
            return {0, block_ttl, 0, 0, "blocking_key"}
        end
        
        -- Get current counts
        local seconds_count = tonumber(redis.call('GET', seconds_key) or "0")
        local minutes_count = tonumber(redis.call('GET', minutes_key) or "0")
        
        -- Check if limits exceeded
        if seconds_count >= seconds_limit then
            local seconds_ttl = redis.call('TTL', seconds_key)
            return {0, seconds_ttl, seconds_count, minutes_count, "seconds"}
        end
        
        if minutes_count >= minutes_limit then
            local minutes_ttl = redis.call('TTL', minutes_key)
            return {0, minutes_ttl, seconds_count, minutes_count, "minutes"}
        end
        
        -- Increment counts and set expiry if needed
        -- Handle seconds key
        local seconds_exists = redis.call('EXISTS', seconds_key)
        redis.call('INCR', seconds_key)
        if seconds_exists == 0 then
            redis.call('EXPIRE', seconds_key, seconds_window)
        end
        
        -- Handle minutes key
        local minutes_exists = redis.call('EXISTS', minutes_key)
        redis.call('INCR', minutes_key)
        if minutes_exists == 0 then
            redis.call('EXPIRE', minutes_key, minutes_window)
        end
        
        -- Return success and new counts
        return {1, 0, seconds_count + 1, minutes_count + 1, "allowed"}
        """
    
    def get_blocking_script(self):
        """Returns the Lua script content for handling blocking keys."""
        return """
        local blocking_key = KEYS[1]
        local retry_after = tonumber(ARGV[1])
        
        -- Check if key exists and get its TTL
        local exists = redis.call('EXISTS', blocking_key)
        local current_ttl = 0
        
        if exists == 1 then
            current_ttl = redis.call('TTL', blocking_key)
        end
        
        -- Only set the key if it doesn't exist OR if new retry_after is longer than remaining TTL
        if exists == 0 or retry_after > current_ttl then
            redis.call('SET', blocking_key, 1, 'EX', retry_after)
        end
        
        return {exists, current_ttl}
        """
    
    async def initialize_scripts(self):
        """Initialize the Lua scripts and store their SHA values."""
        if self.check_and_increment_sha is None:
            self.check_and_increment_sha = await self.redis.script_load(self.check_and_increment_script_content)
        
        if self.blocking_script_sha is None:
            self.blocking_script_sha = await self.redis.script_load(self.blocking_script_content)
    
    async def check_and_increment(self):
        """
        Atomically check if the request is allowed and increment counters if it is.
        Returns True if allowed, raises exception otherwise.
        """
        # Make sure scripts are initialized
        if self.check_and_increment_sha is None:
            await self.initialize_scripts()
        
        # Execute the Lua script using the stored SHA
        result = await self.redis.evalsha(
            self.check_and_increment_sha,
            3,  # number of keys
            self.seconds_key, 
            self.minutes_key, 
            self.blocking_key,
            self.seconds_limit, 
            self.minutes_limit, 
            self.seconds_window, 
            self.minutes_window
        )
        
        is_allowed, retry_after, seconds_count, minutes_count, reason = result
        
        if is_allowed == 0:  # Request not allowed
            raise ApplicationRateLimitExceeded(
                retry_after=retry_after if retry_after >= 1 else 1,
                minutes_key=self.minutes_key,
                seconds_key=self.seconds_key,
                seconds_window=self.seconds_window,
                minutes_window=self.minutes_window,
                subdomain=self.subdomain,
                enforcement_type="internal",
                riot_endpoint=self.riot_endpoint,
                seconds_count=seconds_count,
                seconds_limit=self.seconds_limit,
                minutes_count=minutes_count,
                minutes_limit=self.minutes_limit,
                reason=f"The '{reason}' key count/limit/existence was violated."
            )
        
        return True

    async def write_inbound_application_rate_limit(self, retry_after: int, offending_context: list):
        """
        Set the application rate limit blocking key in Redis with a TTL.
        This is only for when we actually experience a 429 response with X-Rate-Limit-Type header
        with a value of "application"
        """
        if not retry_after:
            retry_after = 68
            
        # Make sure scripts are initialized
        if self.blocking_script_sha is None:
            await self.initialize_scripts()
        
        # Execute the blocking script using the stored SHA
        result = await self.redis.evalsha(
            self.blocking_script_sha,
            1,  # number of keys
            self.blocking_key,
            retry_after
        )
        
        exists, current_ttl = result
        
        # Use the max of the existing TTL and new retry_after to ensure we respect the longest timeout
        effective_retry_after = max(retry_after, current_ttl) if exists else retry_after
        
        raise ApplicationRateLimitExceeded(
            retry_after=effective_retry_after,
            minutes_key=self.minutes_key,
            seconds_key=self.seconds_key,
            seconds_window=self.seconds_window,
            minutes_window=self.minutes_window,
            enforcement_type="external",
            subdomain=self.subdomain,
            riot_endpoint=self.riot_endpoint,
            offending_context=offending_context,
            seconds_limit=self.seconds_limit,
            minutes_limit=self.minutes_limit,
            reason="Inbound 429 actually experienced. Did not prevent Riot from serving a 429."
        )


class MethodRateLimiter(BaseRateLimitingLogic):
    """
    Rate limiter that respects method (i.e. endpoint) based rate limits per subdomain
    (A subdomain is what Riot incorrectly calls 'region' in their docs or what the 3rd Party Developer community calls a 'platform router').
    """

    def __init__(self, riot_endpoint: str, async_redis_client):
        super().__init__(riot_endpoint, async_redis_client)
        self.service = derive_riot_service(riot_endpoint)
        self.config = derive_riot_method_config(riot_endpoint, self.subdomain, self.service)

        self.method = self.config["method"]
        self.seconds_limit = self.config["seconds"]["limit"]
        self.seconds_window = self.config["seconds"]["window"]

        self.minutes_limit = self.config["minutes"]["limit"]
        self.minutes_window = self.config["minutes"]["window"]

        # Generate Redis keys.
        self.seconds_key = self.generate_key("seconds") if self.seconds_limit is not None else None
        self.minutes_key = self.generate_key("minutes") if self.minutes_limit is not None else None
        self.blocking_key = self.generate_blocking_key()

        # Initialize script content but don't load yet
        self.check_and_increment_script_content = self.get_check_and_increment_script()
        self.blocking_script_content = self.get_blocking_script()
        
        # SHA values will be set during initialization
        self.check_and_increment_sha = None
        self.blocking_script_sha = None


    def generate_key(self, window_type: str) -> str:
        return f"nd_method_rate_limit_key_for_{self.subdomain}_{self.method}_{window_type}"

    def generate_blocking_key(self):
        """
        Generate a blocking key for the method rate limiter.
        If "leakage" occurs (i.e. my internal counts fail to prevent an inbound 429 from Riot
        either becasue our counts are out of sync or Riot issues a 429 for an unknown reason)
        then we use this blocking key with a TTL set to the "Retry-After" header so we respect the timeout
        for as long as it is valid whether or not our internal counts hit their limit.
        """
        return f"nd_blocking_method_rate_limit_key_for_{self.method}_{self.subdomain}"

    def get_check_and_increment_script(self):
        """Returns the Lua script content for atomic check and increment operations."""
        return """
        -- Keys: [seconds_key, minutes_key, blocking_key]
        -- Args: [seconds_limit, minutes_limit, seconds_window, minutes_window, has_seconds, has_minutes]
        
        local seconds_key = KEYS[1]
        local minutes_key = KEYS[2]
        local blocking_key = KEYS[3]
        
        local seconds_limit = tonumber(ARGV[1])
        local minutes_limit = tonumber(ARGV[2])
        local seconds_window = tonumber(ARGV[3])
        local minutes_window = tonumber(ARGV[4])
        local has_seconds = tonumber(ARGV[5])
        local has_minutes = tonumber(ARGV[6])
        
        -- Check if blocking key exists (external rate limit was hit)
        local block_exists = redis.call('EXISTS', blocking_key)
        if block_exists == 1 then
            local block_ttl = redis.call('TTL', blocking_key)
            return {0, block_ttl, 0, 0, "blocking_key"}
        end
        
        -- Check seconds limit if it exists
        local seconds_count = 0
        local seconds_ttl = 0
        if has_seconds == 1 then
            seconds_count = tonumber(redis.call('GET', seconds_key) or "0")
            if seconds_count >= seconds_limit then
                seconds_ttl = redis.call('TTL', seconds_key)
                return {0, seconds_ttl, seconds_count, 0, "seconds"}
            end
        end
        
        -- Check minutes limit if it exists
        local minutes_count = 0
        local minutes_ttl = 0
        if has_minutes == 1 then
            minutes_count = tonumber(redis.call('GET', minutes_key) or "0")
            if minutes_count >= minutes_limit then
                minutes_ttl = redis.call('TTL', minutes_key)
                return {0, minutes_ttl, seconds_count, minutes_count, "minutes"}
            end
        end
        
        -- Increment counts and set expiry if needed
        -- Handle seconds key if it exists
        if has_seconds == 1 then
            local seconds_exists = redis.call('EXISTS', seconds_key)
            redis.call('INCR', seconds_key)
            if seconds_exists == 0 then
                redis.call('EXPIRE', seconds_key, seconds_window)
            end
            seconds_count = seconds_count + 1
        end
        
        -- Handle minutes key if it exists
        if has_minutes == 1 then
            local minutes_exists = redis.call('EXISTS', minutes_key)
            redis.call('INCR', minutes_key)
            if minutes_exists == 0 then
                redis.call('EXPIRE', minutes_key, minutes_window)
            end
            minutes_count = minutes_count + 1
        end
        
        -- Return success and new counts
        return {1, 0, seconds_count, minutes_count, "allowed"}
        """

    def get_blocking_script(self):
        """Returns the Lua script content for handling blocking keys."""
        return """
        local blocking_key = KEYS[1]
        local retry_after = tonumber(ARGV[1])
        
        -- Check if key exists and get its TTL
        local exists = redis.call('EXISTS', blocking_key)
        local current_ttl = 0
        
        if exists == 1 then
            current_ttl = redis.call('TTL', blocking_key)
        end
        
        -- Only set the key if it doesn't exist OR if new retry_after is longer than remaining TTL
        if exists == 0 or retry_after > current_ttl then
            redis.call('SET', blocking_key, 1, 'EX', retry_after)
        end
        
        return {exists, current_ttl}
        """

    async def initialize_scripts(self):
        """Initialize the Lua scripts and store their SHA values."""
        if self.check_and_increment_sha is None:
            self.check_and_increment_sha = await self.redis.script_load(self.check_and_increment_script_content)
        
        if self.blocking_script_sha is None:
            self.blocking_script_sha = await self.redis.script_load(self.blocking_script_content)

    async def check_and_increment(self):
        """
        Atomically check if the request is allowed and increment counters if it is.
        Returns True if allowed, raises exception otherwise.
        """
        if self.seconds_key is None and self.minutes_key is None:
            raise TypeError("Logical mistake was made. A rate limit must have either a seconds key and/or a minutes key. They cannot both be null.")
        
        # Make sure scripts are initialized
        if self.check_and_increment_sha is None:
            await self.initialize_scripts()
        
        # Convert None values to empty strings for Redis keys
        seconds_key = self.seconds_key or ""
        minutes_key = self.minutes_key or ""
        
        # Prepare arguments
        has_seconds = 1 if self.seconds_key is not None else 0
        has_minutes = 1 if self.minutes_key is not None else 0
        
        # Execute the Lua script atomically
        result = await self.redis.evalsha(
            self.check_and_increment_sha,
            3,  # number of keys
            seconds_key, 
            minutes_key, 
            self.blocking_key,
            self.seconds_limit or 0, 
            self.minutes_limit or 0, 
            self.seconds_window or 0, 
            self.minutes_window or 0,
            has_seconds,
            has_minutes
        )
        
        is_allowed, retry_after, seconds_count, minutes_count, reason = result

        if is_allowed == 0:  # Request not allowed
            raise MethodRateLimitExceeded(
                retry_after=retry_after if retry_after >= 1 else 1,
                method=self.method,
                minutes_key=self.minutes_key,
                seconds_key=self.seconds_key,
                seconds_window=self.seconds_window,
                minutes_window=self.minutes_window,
                enforcement_type="internal",
                subdomain=self.subdomain,
                riot_endpoint=self.riot_endpoint,
                seconds_count=seconds_count,
                seconds_limit=self.seconds_limit,
                minutes_count=minutes_count,
                minutes_limit=self.minutes_limit,
                reason=f"The '{reason}' key count/limit/existence was violated."
            )
        
        return True
    
    async def write_inbound_method_rate_limit(self, retry_after: int, offending_context: list):
        """
        Set the method rate limit blocking key in Redis with a TTL. This is only for when we actually experience a
        429 response with X-Rate-Limit-Type header with a value of "method"
        """
        if not retry_after:
            retry_after = 68
        
        # Make sure scripts are initialized
        if self.blocking_script_sha is None:
            await self.initialize_scripts()
        
        # Execute the blocking script using the stored SHA
        result = await self.redis.evalsha(
            self.blocking_script_sha,
            1,  # number of keys
            self.blocking_key,
            retry_after
        )
        
        exists, current_ttl = result
        
        # Use the max of the existing TTL and new retry_after to ensure we respect the longest timeout
        effective_retry_after = max(retry_after, current_ttl) if exists else retry_after
        
        raise MethodRateLimitExceeded(
            retry_after=effective_retry_after,
            minutes_key=self.minutes_key,
            seconds_key=self.seconds_key,
            seconds_window=self.seconds_window,
            minutes_window=self.minutes_window,
            enforcement_type="external",
            method=self.method,
            subdomain=self.subdomain,
            riot_endpoint=self.riot_endpoint,
            offending_context=offending_context,
            seconds_limit=self.seconds_limit,
            minutes_limit=self.minutes_limit,
            reason="Inbound 429 actually experienced. Did not prevent Riot from serving a 429."
        )

class ServiceRateLimiter(BaseRateLimitingLogic):
    """
    Rate limiter for service-wide rate limits per subdomain (what Riot incorrectly calls region).
    Note: that Riot does not provide the 'Retry-After' (and thus no retry after time integer) header when service rate limits are experienced.
    """

    SERVICE_BLOCK_DURATION = 68
    def __init__(self, riot_endpoint: str, async_redis_client):
        super().__init__(riot_endpoint, async_redis_client)
        self.service = derive_riot_service(riot_endpoint)
        self.service_key = self.generate_key()

    def generate_key(self) -> str:
        """Generate a unique key for the service rate limit."""
        return f"nd_blocking_key_for_service_rate_limit_{self.service}_{self.subdomain}"

    async def is_allowed(self):
        """Check if the request is allowed under the service rate limit."""
        if await self.redis.exists(self.service_key):
            raise ServiceRateLimitExceeded(
                retry_after=self.__class__.SERVICE_BLOCK_DURATION,
                service=self.service,
                enforcement_type="internal",
                subdomain=self.subdomain,
                riot_endpoint=self.riot_endpoint
                )
        return True
    
    async def write_inbound_service_rate_limit(self, offending_context):
        """Set the service rate limit key in Redis with a TTL."""
        # Create the key with a 68-second TTL if it doesn't already exist (NX)
        await self.redis.set(self.service_key, 1, ex=self.__class__.SERVICE_BLOCK_DURATION, nx=True)

        raise ServiceRateLimitExceeded(
            retry_after=self.__class__.SERVICE_BLOCK_DURATION, # this will always be a default value for Service limits because Riot does not provide a time
            service=self.service,
            subdomain=self.subdomain,
            riot_endpoint=self.riot_endpoint,
            offending_context=offending_context,
            enforcement_type="external"
        )
    
class UnspecifiedRiotRateLimiter(BaseRateLimitingLogic):
    """Rate limiter for unspecified rate limit type. Enforced per subdomain (what Riot incorrectly calls region)."""
    def __init__(self, riot_endpoint, async_redis_client):
        super().__init__(riot_endpoint, async_redis_client)
        self.service = derive_riot_service(riot_endpoint)
        self.config = derive_riot_method_config(riot_endpoint, self.subdomain, self.service)
        self.method = self.config["method"]
        self.blocking_key = f"blocking_key_for_unspecified_rate_limit_for_{self.subdomain}"

    async def is_allowed(self):
        """Check if the request is allowed under the experienced but unspecified rate limit."""
        # Use a pipeline to execute both commands in a single transaction
        async with self.redis.pipeline() as pipe:
            # Queue both commands
            await pipe.exists(self.blocking_key)
            await pipe.ttl(self.blocking_key)
            # Execute the pipeline and get results
            exists, remaining_ttl = await pipe.execute()
        
        if exists:
            # Ensure non-negative TTL value
            remaining_ttl = max(1, remaining_ttl)
            
            raise UnspecifiedRateLimitExceeded(
                retry_after=remaining_ttl,
                service=self.service,
                method=self.method,
                enforcement_type="internal",
                subdomain=self.subdomain,
                riot_endpoint=self.riot_endpoint,
                offending_context=None
            )
        return True
    
    async def write_inbound_unspecified_rate_limit(self, retry_after: int, offending_context: list):
        """
        Set the unspecified rate limit blocking key in Redis with a TTL. This is only for when we actually expereince a
        429 response with a missing X-Rate-Limit-Type header or unknown value. 
        """
        if not retry_after:
            retry_after = 68
        # Create the key with a 68-second TTL if it doesn't already exist (NX)
        await self.redis.set(self.blocking_key, 1, ex=retry_after, nx=True)
        raise UnspecifiedRateLimitExceeded(
            retry_after=retry_after,
            enforcement_type="external",
            subdomain=self.subdomain,
            riot_endpoint=self.riot_endpoint,
            offending_context=offending_context,
            service=self.service,
            method=self.method
        )