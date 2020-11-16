from django.contrib import admin

from .models import LinkAggregate, PageAggregate, ProjectAggregate, UserAggregate


class LinkAggregateAdmin(admin.ModelAdmin):
    list_display = (
        "organisation",
        "collection",
        "full_date",
        "total_links_added",
        "total_links_removed",
    )
    list_filter = ("organisation", "collection", "month", "year")


admin.site.register(LinkAggregate, LinkAggregateAdmin)


class PageAggregateAdmin(admin.ModelAdmin):
    list_display = (
        "organisation",
        "collection",
        "page_name",
        "full_date",
        "total_links_added",
        "total_links_removed",
    )
    list_filter = ("organisation", "collection", "month", "year")


admin.site.register(PageAggregate, PageAggregateAdmin)


class ProjectAggregateAdmin(admin.ModelAdmin):
    list_display = (
        "organisation",
        "collection",
        "project_name",
        "full_date",
        "total_links_added",
        "total_links_removed",
    )
    list_filter = ("organisation", "collection", "month", "year")


admin.site.register(ProjectAggregate, ProjectAggregateAdmin)


class UserAggregateAdmin(admin.ModelAdmin):
    list_display = (
        "organisation",
        "collection",
        "username",
        "full_date",
        "total_links_added",
        "total_links_removed",
    )
    list_filter = ("organisation", "collection", "month", "year")


admin.site.register(UserAggregate, UserAggregateAdmin)
