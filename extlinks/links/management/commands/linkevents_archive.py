import gzip, logging, datetime, os

from swiftclient import ClientException

from typing import List, Optional

from django.core import serializers
from extlinks.common import swift
from extlinks.common.management.commands import BaseCommand
from django.core.management import call_command
from django.db import close_old_connections

from extlinks.links.models import LinkEvent
from extlinks.aggregates.models import (
    LinkAggregate,
    UserAggregate,
    PageProjectAggregate,
)

logger = logging.getLogger("django")

CHUNK_SIZE = 10_000
SWIFT_CONTAINER_NAME = os.environ.get("SWIFT_CONTAINER_NAME", "archive-linkevents")


class Command(BaseCommand):
    help = "dump & delete or load LinkEvents"

    def log_msg(self, msg, *args, level="info"):
        """
        Logs and prints messages so they are visible in both Docker
        logs and cron job logs

        Parameters
        ----------
        msg : str
            The message to log

        *args : tuple
            Arguments to be lazily formatted into msg.

        level : str
            The log level ('info' or 'error'), defaults to 'info'

        Returns
        -------
        None
        """
        if level == "error":
            logger.error(msg, *args)
            formatted_msg = msg % args if args else msg
            self.stderr.write(formatted_msg)
            self.stderr.flush()
        else:
            logger.info(msg, *args)
            formatted_msg = msg % args if args else msg
            self.stdout.write(formatted_msg)
            self.stdout.flush()

    def get_most_recent(self):
        most_recent = []
        for aggregate in [LinkAggregate, UserAggregate, PageProjectAggregate]:
            try:
                most_recent.append(aggregate.objects.latest("full_date").full_date)
            except aggregate.DoesNotExist:
                pass
        return most_recent

    def get_most_early(self):
        most_recent = []
        for aggregate in [LinkAggregate, UserAggregate, PageProjectAggregate]:
            try:
                most_recent.append(aggregate.objects.earliest("full_date").full_date)
            except aggregate.DoesNotExist:
                pass
        return most_recent

    def dump(
        self,
        date: Optional[datetime.date] = None,
        output: Optional[str] = None,
        object_storage_only=False,
    ):
        """
        Export LinkEvents to gzipped JSON files that are grouped by day, and
        then delete them from the database.

        This command only archives LinkEvents that have been aggregated by
        checking the cron job log. Optionally a date (YYYY-MM-DD) can be passed
        as a parameter to override this behavior.
        """

        output_dir = output if output and os.path.isdir(output) else "backup"

        if date is None:
            # We don't want to archive link events that haven't been processed by
            # the aggregate jobs yet. Find the start time for the most recent
            # aggregates.

            most_recent_aggregates = self.get_most_recent()

            if len(most_recent_aggregates) != 3:
                self.log_msg("All of the aggregate jobs have not been run yet")
                return

            # Find the oldest start time of the 3 jobs start datetimes we have. All
            # link events before this date have already been aggregated and are
            # safe to be archived.
            archive_start_time = min(
                most_recent_aggregates,
            )
            most_early_aggregates = self.get_most_early()
            earliest_date = min(most_early_aggregates)
        else:
            archive_start_time = date + datetime.timedelta(days=1)
            earliest_date = None

        start = archive_start_time - datetime.timedelta(days=1)
        total = 0
        iteration = 0

        # Page through LinkEvents for all days prior to the day that all of the
        # most recent aggregation jobs have started. This should be yesterday's
        # date, but if the jobs haven't all been completed yet then it will
        # probably be the day before yesterday.
        while True:
            limit = (iteration + 1) * CHUNK_SIZE
            offset = iteration * CHUNK_SIZE

            # Paginate through LinkEvents in chunks of 10k at a time. Overfetch
            # an extra record so we can determine if we need to paginate more.
            results = list(
                LinkEvent.objects.filter(
                    timestamp__gte=start,
                    timestamp__lt=start + datetime.timedelta(days=1),
                ).all()[offset : limit + 1]
            )

            # For scenario when a date is not given in the command and one day has no results:
            # if there are more days remaining to be processed, decrease the start date and continue
            if (
                date is None
                and len(results) == 0
                and earliest_date is not None
                and earliest_date < start
            ):
                start -= datetime.timedelta(days=1)
                continue

            if len(results) == 0:
                break

            # Remove the overfetched record before saving the archive.
            linkevents_by_date = results[:CHUNK_SIZE]

            filename = f"links_linkevent_{start.strftime('%Y%m%d')}_{iteration}.json.gz"
            local_filepath = os.path.join(output_dir, filename)
            self.log_msg(
                "Dumping %d LinkEvents into %s", len(linkevents_by_date), local_filepath
            )

            # Serialize the records directly in the writer to conserve memory.
            with gzip.open(local_filepath, "wt", encoding="utf-8") as archive:
                archive.write(serializers.serialize("json", linkevents_by_date))

            # Try to upload to Swift, remove local archive if flag is on and upload was successful
            if (
                self.upload_to_swift(local_filepath, SWIFT_CONTAINER_NAME)
                and object_storage_only
            ):
                os.remove(local_filepath)
                self.log_msg(f"Deleted local file {local_filepath} after upload")

            if len(results) > CHUNK_SIZE:
                iteration += 1
            else:
                start -= datetime.timedelta(days=1)
                iteration = 0

            total += len(linkevents_by_date)

        self.log_msg(
            "Deleting %d LinkEvents before %s from the database",
            total,
            archive_start_time.strftime("%Y-%m-%d"),
        )

        # Delete the objects from the database after all passes are complete.
        # Do this in batches of 10k as well as this has the possibility of
        # failing when dealing with a lot of records.
        query_set = LinkEvent.objects.filter(timestamp__lt=archive_start_time)
        while query_set.exists():
            delete_query_set = query_set.values_list("id", flat=True)[:CHUNK_SIZE]
            LinkEvent.objects.filter(pk__in=list(delete_query_set)).delete()

    def load(self, filenames: List[str]):
        """
        Import LinkEvents from gzipped JSON files.
        """

        if not filenames:
            self.log_msg("No link event archives specified")
            return

        for filename in sorted(filenames):
            self.log_msg("Loading " + filename)
            # loaddata supports gzipped fixtures and handles relationships properly
            call_command("loaddata", filename)

    def upload_to_swift(self, local_filepath, container_name):
        """
        Upload a file to Swift object storage, ensuring the container exists.

        Reference: https://docs.openstack.org/python-swiftclient/latest/client-api.html

        Parameters
        ----------
        local_file_path : str
            The backup file path to be uploaded to Swift

        container_name : str
            The Swift container to upload the file

        Returns
        -------
        None
        """

        try:
            conn = swift.swift_connection()
        except RuntimeError:
            self.log_msg("Swift credentials not provided. Skipping upload.")
            return False

        try:
            # Ensure the container exists before uploading.
            try:
                was_created = swift.ensure_container_exists(conn, container_name)
                if was_created:
                    self.log_msg(f"Created new container: {container_name}")
            except RuntimeError as e:
                self.log_msg(str(e), level="error")
                return False

            # Skip uploading the file if it already exists in Swift.
            object_name = os.path.basename(local_filepath)
            try:
                if swift.file_exists(conn, container_name, object_name):
                    self.log_msg(f"Skipping upload {object_name} - already uploaded")
                    return True
            except ClientException as e:
                self.log_msg(
                    f"Failed to locate {object_name} in Swift container "
                    f"{container_name} due to an unexpected error: {e}"
                )
                return False

            swift.upload_file(
                conn,
                container_name,
                local_filepath,
                content_type="application/gzip",
            )

            self.log_msg(
                f"Successfully uploaded {local_filepath} to Swift container {container_name}"
            )
            return True
        except Exception as e:
            self.log_msg(
                f"Failed to upload {local_filepath} to Swift: {e}", level="error"
            )
            return False

    def upload(self, filenames: List[str]):
        """
        Upload existing LinkEvent archives to Swift.

        Parameters
        ----------
        filenames : List[str]
            List of archive file paths to upload.

        Returns
        -------
        None
        """
        if not filenames:
            self.log_msg("No link event archives specified for upload.")
            return

        for filepath in sorted(filenames):
            if not os.path.isfile(filepath):
                self.log_msg(
                    f"File {filepath} does not exist. Skipping.", level="error"
                )
                continue

            filename = os.path.basename(filepath)

            self.log_msg(
                f"Uploading {filepath} to Swift container {SWIFT_CONTAINER_NAME}"
            )

            if self.upload_to_swift(filepath, SWIFT_CONTAINER_NAME):
                self.log_msg(f"Successfully uploaded {filename} to Swift.")
            else:
                self.log_msg(f"Failed to upload {filename} to Swift.", level="error")

    def add_arguments(self, parser):
        parser.add_argument(
            "action",
            nargs=1,
            type=str,
            choices=["dump", "load", "upload"],
            help="dump: Export LinkEvents to gzipped JSON files, then delete them from the database. "
            "load: Import LinkEvents from gzipped JSON files. "
            "upload: Upload existing LinkEvents archives to Swift.",
        )
        parser.add_argument(
            "filenames",
            nargs="*",
            type=str,
            help="LinkEvent archive filenames to load.",
        )
        parser.add_argument(
            "-d",
            "--date",
            nargs="?",
            type=lambda arg: datetime.datetime.strptime(arg, "%Y-%m-%d").date(),
            help="A maximum date formatted as YYYY-MM-DD to begin archiving from.",
        )
        parser.add_argument(
            "-o",
            "--output",
            nargs="?",
            type=str,
            help="The directory that the archives containing the LinkEvents should be written to.",
        )
        parser.add_argument(
            "--object-storage-only",
            action="store_true",
            help="If enabled, archives will only be stored in Swift and deleted from local storage after upload.",
        )

    def _handle(self, *args, **options):
        action = options["action"][0]
        if action == "dump":
            self.dump(
                date=options["date"],
                output=options["output"],
                object_storage_only=options["object_storage_only"],
            )
        if action == "load":
            self.load(filenames=options["filenames"])
        if action == "upload":
            self.upload(filenames=options["filenames"])

        close_old_connections()
