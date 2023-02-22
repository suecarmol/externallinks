import hashlib
import logging
from datetime import date

from django.db import models
from django.core.cache import cache
from django.utils.functional import cached_property

logger = logging.getLogger("django")

class URLPatternManager(models.Manager):
    cached_patterns = cache.get('url_pattern_cache')

    def cached(self):
        if not self.cached_patterns:
            self.cached_patterns = self.all()
            logger.info('set url_pattern_cache')
            cache.set('url_pattern_cache', self.cached_patterns, None)
        return self.cached_patterns

    def matches(self, link):
        # All URL patterns matching this link
        tracked_urls = self.cached()
        return [
            pattern
            for pattern in tracked_urls
            if pattern.url in link or pattern.get_proxied_url in link
        ]

class URLPattern(models.Model):
    class Meta:
        app_label = "links"
        verbose_name = "URL pattern"
        verbose_name_plural = "URL patterns"

    objects = URLPatternManager()
    # This doesn't have to look like a 'real' URL so we'll use a CharField.
    url = models.CharField(max_length=150)

    collection = models.ForeignKey(
        "organisations.Collection",
        null=True,
        on_delete=models.SET_NULL,
        related_name="url",
    )

    def __str__(self):
        return self.url

    def save(self, *args, **kwargs):
        cache.delete('url_pattern_cache')
        super(URLPattern, self).save(*args, **kwargs)

    @cached_property
    def get_proxied_url(self):
        # This isn't everything that happens, but it's good enough
        # for us to make a decision about whether we have a match.
        return self.url.replace(".", "-")


class LinkSearchTotal(models.Model):
    class Meta:
        app_label = "links"
        verbose_name = "LinkSearch total"
        verbose_name_plural = "LinkSearch totals"
        # We only want one record for each URL on any particular date
        constraints = [
            models.UniqueConstraint(fields=["url", "date"], name="unique_date_total")
        ]

    url = models.ForeignKey(URLPattern, null=True, on_delete=models.SET_NULL)

    date = models.DateField(default=date.today)
    total = models.PositiveIntegerField()


class LinkEvent(models.Model):
    """
    Stores data from the page-links-change EventStream

    https://stream.wikimedia.org/?doc#!/Streams/get_v2_stream_page_links_change
    """

    class Meta:
        app_label = "links"
        get_latest_by = "timestamp"
        indexes = [
            models.Index(fields=["hash_link_event_id",]),
            models.Index(fields=["timestamp",]),
        ]

    url = models.ManyToManyField(URLPattern, related_name="linkevent")

    # URLs should have a max length of 2083
    link = models.CharField(max_length=2083)
    timestamp = models.DateTimeField()
    domain = models.CharField(max_length=32, db_index=True)
    username = models.ForeignKey(
        "organisations.User", null=True, on_delete=models.SET_NULL
    )
    # rev_id has null=True because some tracked revisions don't have a
    # revision ID, like page moves.
    rev_id = models.PositiveIntegerField(null=True)
    # IPs have no user_id, so this can be blank too.
    user_id = models.PositiveIntegerField(null=True)
    page_title = models.CharField(max_length=255)
    page_namespace = models.IntegerField()
    event_id = models.CharField(max_length=36)
    user_is_bot = models.BooleanField(default=False)
    hash_link_event_id = models.CharField(max_length=256, blank=True)

    # Were links added or removed?
    REMOVED = 0
    ADDED = 1

    CHANGE_CHOICES = (
        (REMOVED, "Removed"),
        (ADDED, "Added"),
    )

    change = models.IntegerField(choices=CHANGE_CHOICES, db_index=True)

    # Flags whether this event was from a user on the user list for the
    # organisation tracking its URL.
    on_user_list = models.BooleanField(default=False)

    @property
    def get_organisation(self):
        url_patterns = self.url.all()
        return url_patterns[0].collection.organisation

    def save(self, **kwargs):
        link_event_id = self.link + self.event_id
        hash = hashlib.sha256()
        hash.update(link_event_id.encode("utf-8"))
        self.hash_link_event_id = hash.hexdigest()
        super().save(**kwargs)
