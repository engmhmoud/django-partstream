"""
Clear cache management command for django-partstream.
"""

import time
from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.utils import timezone


class Command(BaseCommand):
    """
    Clear django-partstream related cache data.

    Usage:
        python manage.py partstream_clear_cache
        python manage.py partstream_clear_cache --pattern=user_123
    """

    help = "Clear django-partstream cache data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--pattern", type=str, help="Clear cache keys matching this pattern"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be cleared without actually clearing",
        )

    def handle(self, *args, **options):
        """Clear cache data."""
        pattern = options.get("pattern")
        dry_run = options.get("dry_run", False)

        if pattern:
            self._clear_pattern(pattern, dry_run)
        else:
            self._clear_all_partstream_cache(dry_run)

    def _clear_pattern(self, pattern: str, dry_run: bool):
        """Clear cache keys matching pattern."""
        # Get all cache keys (this depends on cache backend)
        try:
            cache_keys = cache.keys(f"*{pattern}*")

            if not cache_keys:
                self.stdout.write(
                    self.style.WARNING(
                        f"No cache keys found matching pattern: {pattern}"
                    )
                )
                return

            if dry_run:
                self.stdout.write(f"Would clear {len(cache_keys)} cache keys:")
                for key in cache_keys:
                    self.stdout.write(f"  - {key}")
            else:
                cleared_count = 0
                for key in cache_keys:
                    cache.delete(key)
                    cleared_count += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Cleared {cleared_count} cache keys matching pattern: {pattern}"
                    )
                )

        except AttributeError:
            self.stdout.write(
                self.style.ERROR("Cache backend does not support key listing")
            )

    def _clear_all_partstream_cache(self, dry_run: bool):
        """Clear all partstream-related cache."""
        partstream_patterns = ["partstream_*", "progressive_*", "django_partstream_*"]

        total_cleared = 0

        for pattern in partstream_patterns:
            try:
                cache_keys = cache.keys(pattern)

                if cache_keys:
                    if dry_run:
                        self.stdout.write(
                            f"Would clear {len(cache_keys)} keys for pattern: {pattern}"
                        )
                        for key in cache_keys:
                            self.stdout.write(f"  - {key}")
                    else:
                        for key in cache_keys:
                            cache.delete(key)
                            total_cleared += 1

            except AttributeError:
                # Cache backend doesn't support key listing
                pass

        if dry_run:
            self.stdout.write("Dry run completed. No cache was actually cleared.")
        else:
            if total_cleared > 0:
                self.stdout.write(
                    self.style.SUCCESS(f"Cleared {total_cleared} partstream cache keys")
                )
            else:
                self.stdout.write(
                    self.style.WARNING("No partstream cache keys found to clear")
                )
