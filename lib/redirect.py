"""HTTP Redirect Tracing Module (T13).

Traces redirect chains using strictly HEAD requests with cumulative timeout,
hop limits, loop detection, and safe error handling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger("siaga.redirect")

DEFAULT_MAX_HOPS = 5
DEFAULT_TOTAL_TIMEOUT = 5.0
USER_AGENT = "SIAGA-FraudDetector/0.1 (+https://github.com/idwebhost-pandi/siaga; automated-security-check)"


@dataclass
class HopInfo:
    url: str
    status_code: int
    location: str | None = None


@dataclass
class RedirectTrace:
    start_url: str
    final_url: str
    hops: list[HopInfo] = field(default_factory=list)
    status: str = "ok"  # "ok" | "loop_detected" | "max_hops_exceeded" | "unreachable" | "error"
    error_message: str | None = None


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Custom redirect handler that prevents automatic following of redirects.

    Allows manual step-by-step tracing of each individual hop using HEAD requests.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Return None to stop urllib from automatically executing a GET redirect
        return None


def _get_ssl_context() -> ssl.SSLContext:
    """Create default SSL context with strict certificate and hostname verification."""
    return ssl.create_default_context()


def trace(
    url: str,
    max_hops: int = DEFAULT_MAX_HOPS,
    timeout: float = DEFAULT_TOTAL_TIMEOUT,
) -> RedirectTrace:
    """Trace HTTP redirect chain for a URL using HEAD requests exclusively.

    STRICT CONSTRAINTS:
    - Only sends HTTP HEAD requests.
    - Never issues GET requests, never downloads response payloads, never executes scripts.
    - Limits total hops to max_hops (default: 5).
    - Limits cumulative wall-clock time across all hops to timeout (default: 5.0s).

    Args:
        url: Initial URL to trace.
        max_hops: Maximum number of redirect jumps allowed (default: 5).
        timeout: Total cumulative timeout in seconds across all hops (default: 5.0).

    Returns:
        RedirectTrace containing hop list, final URL reached, and status.
    """
    clean_url = url.strip()
    if not clean_url.startswith(("http://", "https://")):
        clean_url = "https://" + clean_url

    hops: list[HopInfo] = []
    visited: set[str] = set()
    current_url = clean_url
    start_time = time.monotonic()

    # Build custom opener with no automatic redirects and strict TLS
    opener = urllib.request.build_opener(
        _NoRedirectHandler(),
        urllib.request.HTTPSHandler(context=_get_ssl_context()),
    )

    for hop_idx in range(max_hops + 1):
        # 1. Check cumulative timeout
        elapsed = time.monotonic() - start_time
        remaining_timeout = timeout - elapsed
        if remaining_timeout <= 0:
            logger.warning("Cumulative timeout (%.1fs) exceeded while tracing %s", timeout, clean_url)
            return RedirectTrace(
                start_url=clean_url,
                final_url=current_url,
                hops=hops,
                status="unreachable",
                error_message=f"Cumulative timeout of {timeout}s exceeded",
            )

        # 2. Loop detection
        norm_current = current_url.rstrip("/").lower()
        if norm_current in visited:
            logger.info("Redirect loop detected at %s for initial %s", current_url, clean_url)
            return RedirectTrace(
                start_url=clean_url,
                final_url=current_url,
                hops=hops,
                status="loop_detected",
                error_message="Redirect loop detected",
            )
        visited.add(norm_current)

        # 3. Check hop limit before executing next jump
        if hop_idx >= max_hops:
            logger.warning("Max hops (%d) exceeded while tracing %s", max_hops, clean_url)
            return RedirectTrace(
                start_url=clean_url,
                final_url=current_url,
                hops=hops,
                status="max_hops_exceeded",
                error_message=f"Maximum allowed hops ({max_hops}) exceeded",
            )

        # 4. Perform single HEAD request
        req = urllib.request.Request(
            current_url,
            headers={"User-Agent": USER_AGENT},
            method="HEAD",
        )

        try:
            # We enforce min 0.5s timeout for individual socket read if remaining is small
            call_timeout = max(0.5, remaining_timeout)
            resp = opener.open(req, timeout=call_timeout)
            status_code = resp.status
            headers = resp.headers
        except urllib.error.HTTPError as e:
            status_code = e.code
            headers = e.headers
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            logger.warning("Network error reaching %s: %s", current_url, e)
            hops.append(HopInfo(url=current_url, status_code=0, location=None))
            return RedirectTrace(
                start_url=clean_url,
                final_url=current_url,
                hops=hops,
                status="unreachable",
                error_message=str(e),
            )
        except Exception as e:
            logger.warning("Unexpected error tracing %s: %s", current_url, e)
            hops.append(HopInfo(url=current_url, status_code=0, location=None))
            return RedirectTrace(
                start_url=clean_url,
                final_url=current_url,
                hops=hops,
                status="error",
                error_message=str(e),
            )

        # 5. Process redirect status (3xx)
        if status_code in (301, 302, 303, 307, 308):
            location = headers.get("Location")
            if not location:
                # 3xx without location header -> end of trace
                hops.append(HopInfo(url=current_url, status_code=status_code, location=None))
                return RedirectTrace(
                    start_url=clean_url,
                    final_url=current_url,
                    hops=hops,
                    status="ok",
                )

            # Resolve relative redirect URLs against current URL
            next_url = urllib.parse.urljoin(current_url, location.strip())
            hops.append(HopInfo(url=current_url, status_code=status_code, location=next_url))
            current_url = next_url
            continue
        else:
            # Terminal response (2xx, 4xx, 5xx)
            hops.append(HopInfo(url=current_url, status_code=status_code, location=None))
            return RedirectTrace(
                start_url=clean_url,
                final_url=current_url,
                hops=hops,
                status="ok" if status_code < 400 else "unreachable",
            )

    return RedirectTrace(
        start_url=clean_url,
        final_url=current_url,
        hops=hops,
        status="ok",
    )
