from datetime import datetime
import re

from django.db.models import Count, Sum
from django.views.generic import ListView, DetailView
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator

from extlinks.common.forms import FilterForm
from extlinks.common.helpers import (
    filter_queryset,
    get_linkevent_context,
    annotate_top,
    get_linksearchtotal_data_by_time,
    filter_linksearchtotals,
)
from extlinks.aggregates.models import (
    LinkAggregate,
    PageAggregate,
    ProjectAggregate,
    UserAggregate,
)
from extlinks.links.models import LinkSearchTotal, URLPattern
from .models import Organisation, Collection


class OrganisationListView(ListView):
    model = Organisation

    def get_queryset(self, **kwargs):
        queryset = Organisation.objects.all().annotate(
            collection_count=Count("collection")
        )
        return queryset


class OrganisationDetailView(DetailView):
    model = Organisation
    form_class = FilterForm
    queryset = Organisation.objects.prefetch_related(
        "collection_set", "collection_set__url"
    )

    # This is almost, but not exactly, the same as the program view.
    # As such, most context gathering is split out to a helper.
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = self.form_class(self.request.GET)
        context["form"] = form

        form = self.form_class(self.request.GET)

        if form.is_valid():
            form_data = form.cleaned_data

        organisation_collections = self.object.collection_set.all()

        context["collections"] = {}
        for collection in organisation_collections:
            collection_key = re.sub("[^0-9a-zA-Z]+", "_", collection.name)
            context["collections"][collection_key] = {}
            context["collections"][collection_key]["object"] = collection
            context["collections"][collection_key]["urls"] = collection.url.all()

            context["collections"][collection_key] = self._get_collection_stats(
                collection, context["collections"][collection_key]
            )

        org_links_added_removed = LinkAggregate.objects.filter(
            organisation=self.object
        ).aggregate(Sum("total_links_added"), Sum("total_links_removed"))

        context["organisation_link_changes"] = (
            org_links_added_removed["total_links_added__sum"]
            - org_links_added_removed["total_links_removed__sum"]
        )
        context["organisation_links_added"] = org_links_added_removed[
            "total_links_added__sum"
        ]
        context["organisation_links_removed"] = org_links_added_removed[
            "total_links_removed__sum"
        ]
        context["organisation_total_editors"] = UserAggregate.objects.filter(
            organisation=self.object
        ).aggregate(Count("username", distinct=True))["username__count"]
        context["organisation_total_projects"] = ProjectAggregate.objects.filter(
            organisation=self.object
        ).aggregate(Count("project_name", distinct=True))["project_name__count"]

        return context

    def _get_collection_stats(self, collection, col_context):
        """
        This function gets relevant statistics for a specific collection

        Parameters
        ----------
        collection : Collection
            The collection that the aggregates table will filter fromç
        col_context: dict
            A dictionary that contains the stats for a collection

        Returns
        -------
        col_context: dict
            The dictionary now filled with the information
        """
        links_added_removed = LinkAggregate.objects.filter(
            collection=collection
        ).aggregate(Sum("total_links_added"), Sum("total_links_removed"))

        col_context["total_added"] = links_added_removed["total_links_added__sum"]
        col_context["total_removed"] = links_added_removed["total_links_removed__sum"]
        col_context["total_diff"] = (
            col_context["total_added"] - col_context["total_removed"]
        )

        col_context["total_editors"] = UserAggregate.objects.filter(
            collection=collection
        ).aggregate(Count("username", distinct=True))["username__count"]
        col_context["total_projects"] = ProjectAggregate.objects.filter(
            collection=collection
        ).aggregate(Count("project_name", distinct=True))["project_name__count"]

        return col_context


class CollectionDetailView(DetailView):
    model = Collection
    form_class = FilterForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = self.form_class(self.request.GET)
        context["form"] = form
        collection = kwargs["object"]

        context["top_projects"] = (
            ProjectAggregate.objects.filter(
                collection=collection, organisation=collection.organisation
            )
            .values("project_name")
            .annotate(Sum("total_links_added"), Sum("total_links_removed"))
            .order_by("-total_links_added__sum", "-total_links_removed__sum")
        )[:5]

        context["top_users"] = (
            UserAggregate.objects.filter(collection=collection)
            .values("username")
            .annotate(Sum("total_links_added"), Sum("total_links_removed"))
            .order_by("-total_links_added__sum", "-total_links_removed__sum")[:5]
        )

        context["top_pages"] = (
            PageAggregate.objects.filter(collection=collection)
            .values("page_name")
            .annotate(Sum("total_links_added"), Sum("total_links_removed"))
            .order_by("-total_links_added__sum", "-total_links_removed__sum")[:5]
        )


# @method_decorator(cache_page(60 * 60), name='dispatch')
# class OrganisationDetailView(DetailView):
#     model = Organisation
#     form_class = FilterForm
#
#     # This is almost, but not exactly, the same as the program view.
#     # As such, most context gathering is split out to a helper.
#     def get_context_data(self, **kwargs):
#         context = super(OrganisationDetailView, self).get_context_data(**kwargs)
#         form = self.form_class(self.request.GET)
#         context["form"] = form
#
#         organisation_collections = Collection.objects.filter(organisation=self.object)
#
#         # Here we have a slightly more complex context dictionary setup, where
#         # each collection has its own dictionary of data.
#         context["collections"] = {}
#         for collection in organisation_collections:
#             this_collection_linkevents = collection.get_linkevents()
#             this_collection_linksearchtotals = LinkSearchTotal.objects.filter(
#                 url__collection=collection
#             )
#
#             if form.is_valid():
#                 form_data = form.cleaned_data
#                 this_collection_linkevents = filter_queryset(
#                     this_collection_linkevents, form_data
#                 )
#                 this_collection_linksearchtotals = filter_linksearchtotals(
#                     this_collection_linksearchtotals, form_data
#                 )
#
#             # Replace all special characters that might confuse JS with an
#             # underscore.
#             collection_key = re.sub("[^0-9a-zA-Z]+", "_", collection.name)
#
#             context["collections"][collection_key] = {}
#             context["collections"][collection_key]["object"] = collection
#             context["collections"][collection_key]["urls"] = URLPattern.objects.filter(
#                 collection=collection
#             )
#             context["collections"][collection_key] = get_linkevent_context(
#                 context["collections"][collection_key], this_collection_linkevents
#             )
#
#             context["collections"][collection_key]["top_projects"] = (
#                 ProjectAggregate.objects.filter(collection=collection)
#                 .values("project_name")
#                 .annotate(Sum("total_links_added"), Sum("total_links_removed"))
#                 .order_by("-total_links_added__sum", "-total_links_removed__sum")
#             )[:5]
#
#             context["collections"][collection_key]["top_users"] = (
#                 UserAggregate.objects.filter(collection=collection)
#                 .values("username")
#                 .annotate(Sum("total_links_added"), Sum("total_links_removed"))
#                 .order_by("-total_links_added__sum", "-total_links_removed__sum")[:5]
#             )
#
#             context["collections"][collection_key]["top_pages"] = (
#                 PageAggregate.objects.filter(collection=collection)
#                 .values("page_name")
#                 .annotate(Sum("total_links_added"), Sum("total_links_removed"))
#                 .order_by("-total_links_added__sum", "-total_links_removed__sum")[:5]
#             )
#
#             # Stat block
#
#             links_added_removed = LinkAggregate.objects.filter(
#                 collection=collection
#             ).aggregate(Sum("total_links_added"), Sum("total_links_removed"))
#
#             context["collections"][collection_key]["total_added"] = links_added_removed[
#                 "total_links_added__sum"
#             ]
#             context["collections"][collection_key][
#                 "total_removed"
#             ] = links_added_removed["total_links_removed__sum"]
#             context["collections"][collection_key]["total_diff"] = (
#                 context["collections"][collection_key]["total_added"]
#                 - context["collections"][collection_key]["total_removed"]
#             )
#
#             context["collections"][collection_key][
#                 "total_editors"
#             ] = UserAggregate.objects.filter(collection=collection).aggregate(
#                 Count("username", distinct=True)
#             )[
#                 "username__count"
#             ]
#             context["collections"][collection_key][
#                 "total_projects"
#             ] = ProjectAggregate.objects.filter(collection=collection).aggregate(
#                 Count("project_name", distinct=True)
#             )[
#                 "project_name__count"
#             ]
#
#             # LinkSearchTotal chart data
#             dates, linksearch_data = get_linksearchtotal_data_by_time(
#                 this_collection_linksearchtotals
#             )
#
#             context["collections"][collection_key]["linksearch_dates"] = dates
#             context["collections"][collection_key]["linksearch_data"] = linksearch_data
#
#             # Statistics
#             if linksearch_data:
#                 total_start = linksearch_data[0]
#                 total_current = linksearch_data[-1]
#                 total_diff = total_current - total_start
#                 start_date_object = datetime.strptime(dates[0], "%Y-%m-%d")
#                 start_date = start_date_object.strftime("%B %Y")
#             # If we haven't collected any LinkSearchTotals yet, then set
#             # these variables to None so we don't show them in the statistics
#             # box
#             else:
#                 total_start = None
#                 total_current = None
#                 total_diff = None
#                 start_date = None
#             context["collections"][collection_key][
#                 "linksearch_total_start"
#             ] = total_start
#             context["collections"][collection_key][
#                 "linksearch_total_current"
#             ] = total_current
#             context["collections"][collection_key]["linksearch_total_diff"] = total_diff
#             context["collections"][collection_key]["linksearch_start_date"] = start_date
#
#             context["query_string"] = self.request.META["QUERY_STRING"]
#
#         return context
