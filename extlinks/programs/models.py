from django.db import models

from extlinks.links.models import LinkEvent
from extlinks.organisations.models import Organisation


class Program(models.Model):
    class Meta:
        app_label = "programs"
        ordering = ["name"]

    name = models.CharField(max_length=40)

    description = models.TextField(blank=True, null=True)

    organisations = models.ManyToManyField(
        "organisations.Organisation", blank=True, related_name="organisations"
    )

    def __str__(self):
        return self.name

    def get_linkevents(self):
        return LinkEvent.objects.filter(
            url__collection__organisation__program=self
        ).distinct()

    @property
    def any_orgs_user_list(self):
        """
        Returns True if any of this program's organisations limit by user
        """
        program_orgs = Program.objects.prefetch_related(
            models.Prefetch(
                "organisations",
                queryset=Organisation.objects.filter(username_list__isnull=False),
            )
        )

        if program_orgs.count() > 0:
            return True
        else:
            return False
