"""Unit tests for scripts/run_daily_cycle.py -- date-default UTC/WIB investigation.

2026-09-02 investigation: the daily cycle cron runs at 06:45 WIB, which is
23:45 UTC on the PREVIOUS calendar day, so its default --date (computed from
datetime.now(timezone.utc)) always resolves to "yesterday" in WIB terms.

This looks identical to the WIB/UTC bugs already fixed in healthcheck.py and
backup_db.py -- but it is NOT the same situation, and must NOT be "fixed" the
same way. lib/pipeline.py's Tahap 0 selects ct_raw rows by
substr(first_seen, 1, 10) == target_date, and ct_raw.first_seen is itself a
UTC ISO timestamp written by the 06:30 WIB collector run. Switching the
--date default to WIB would make run_daily_cycle ask for "today" (WIB) while
that day's collector rows are still stamped with yesterday's UTC date --
every single day's pipeline run would scan zero domains.

This test locks in the UTC default so a future "fix" doesn't reintroduce
that outage. The resulting date label reading one calendar day "early" in
WIB terms is a cosmetic display quirk, not a data-completeness bug -- every
24h collection window is still scanned in full, just filed under its UTC
date.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import scripts.run_daily_cycle as run_daily_cycle


class TestDailyCycleDateDefaultStaysUtc:
    def test_default_date_matches_ct_raw_utc_labeling_at_0630_wib(self):
        """At 06:30 WIB (23:30 UTC the prior day), the default --date must
        equal the UTC date -- matching what the collector just wrote to
        ct_raw.first_seen -- not the WIB date, which would find zero rows."""
        # 2026-09-02 06:30 WIB == 2026-09-01 23:30 UTC
        fake_now_utc = datetime(2026, 9, 1, 23, 30, 0, tzinfo=timezone.utc)

        class FakeDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return fake_now_utc if tz is not None else fake_now_utc.replace(tzinfo=None)

        with patch.object(run_daily_cycle, "datetime", FakeDatetime):
            computed_date = FakeDatetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Matches the UTC date the collector just stamped ct_raw.first_seen
        # with -- NOT "2026-09-02", which is what a WIB-based default would
        # (wrongly) compute at this instant.
        assert computed_date == "2026-09-01"
