from django.conf import settings
from django.urls import reverse
from django.db import models
from django.db.models import Sum
from django.db.models.query import QuerySet
from django.template import defaultfilters
from django.utils import timezone
from django.utils.http import urlencode

from base.models import OfficerPosition
from base.models import Term
from project_reports.models import ProjectReport


class EventTypeManager(models.Manager):
    def get_by_natural_key(self, name):
        try:
            return self.get(name=name)
        except EventType.DoesNotExist:
            return None


class EventType(models.Model):
    name = models.CharField(max_length=60, unique=True)
    eligible_elective = models.BooleanField(
        default=True,
        help_text='Determines whether or not an event can be counted '
                  'towards a candidates Elective event requirement.')

    objects = EventTypeManager()

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.name,)


class EventQuerySet(QuerySet):
    def get_upcoming(self, current_term_only=True):
        """Return events that haven't been cancelled and haven't yet ended.

        If current_term_only is True, the method returns only upcoming events
        in the current term. Otherwise, the method returns upcoming events from
        all terms.
        """
        self = self.filter(cancelled=False, end_datetime__gt=timezone.now())
        if current_term_only:
            self = self.filter(term=Term.objects.get_current_term())
        return self

    def get_user_viewable(self, user=None):
        """Return events that the given user can view, or the public events
        if the user is not provided.

        Viewability is based on the "restriction" level for the events.
        """
        user_level = Event.get_user_restriction_level(user)

        # Initialize visible_levels to those that are visible to everyone
        visible_levels = list(Event.VISIBLE_TO_EVERYONE)
        if user_level >= Event.MEMBER:
            visible_levels.append(Event.MEMBER)
        if user_level >= Event.OFFICER:
            visible_levels.append(Event.OFFICER)
        return self.filter(restriction__in=visible_levels)


class EventManager(models.Manager):
    def get_query_set(self):
        return EventQuerySet(self.model, using=self._db)
    
    def get_upcoming(self, current_term_only=True):
        return self.get_query_set().get_upcoming(current_term_only)
    
    def get_user_viewable(self, current_term_only=True):
        return self.get_query_set().get_user_viewable(current_term_only)


class Event(models.Model):
    # Restriction constants
    PUBLIC = 0
    CANDIDATE = 1
    MEMBER = 2
    OFFICER = 3
    OPEN = 4

    RESTRICTION_CHOICES = (
        (PUBLIC, 'Public'),
        (CANDIDATE, 'Candidate'),
        (MEMBER, 'Member'),
        (OFFICER, 'Officer'),
        (OPEN, 'Open (No Signups)')
    )

    VISIBLE_TO_EVERYONE = (OPEN, PUBLIC, CANDIDATE)

    name = models.CharField(max_length=80, verbose_name='event name')
    event_type = models.ForeignKey(EventType, null=True, on_delete=models.SET_NULL)

    restriction = models.PositiveSmallIntegerField(
        choices=RESTRICTION_CHOICES,
        default=CANDIDATE,
        db_index=True,
        verbose_name='minimum restriction',
        help_text=(
            'Who can sign up for this? Each restriction level allows users in '
            'that category, as well as users with more permissions (e.g., '
            'setting the restriction as "Candidate" allows candidates, '
            'members, and officers).'))

    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    term = models.ForeignKey(Term, null=True, on_delete=models.SET_NULL)
    tagline = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=80)
    contact = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    committee = models.ForeignKey(OfficerPosition, null=True, on_delete=models.SET_NULL)

    signup_limit = models.PositiveSmallIntegerField(
        default=0,
        help_text='Set as 0 to allow unlimited signups.')
    max_guests_per_person = models.PositiveSmallIntegerField(
        default=0,
        help_text='Maximum number of guests each person is allowed to bring.')
    needs_drivers = models.BooleanField(default=False)
    cancelled = models.BooleanField(default=False)

    # Some events can be worth more than 1 credit for candidates:
    requirements_credit = models.IntegerField(
        default=1,
        help_text='Large events can be worth more than 1 candidate '
                  'requirement credit.',
        choices=((0, 0), (1, 1), (2, 2), (3, 3)))

    project_report = models.ForeignKey(ProjectReport, null=True, blank=True,
                                       related_name='event', default=None,
                                       on_delete=models.SET_NULL)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    objects = EventManager()

    class Meta(object):
        ordering = ('start_datetime',)
        permissions = (
            ('contact_participants', 'Can send email to those signed up'),
        )
        verbose_name = 'event'
        verbose_name_plural = 'events'

    def __str__(self):
        return '{} - {}'.format(self.name, self.term)

    def get_absolute_url(self):
        return reverse('events:detail', args=(self.pk,))

    def is_upcoming(self):
        """Return True if the event is not canceled and has not yet ended."""
        return (not self.cancelled) and (self.end_datetime > timezone.now())

    def is_multiday(self):
        """Return True if the event starts on a different date than it ends.

        Ensures that the multiday check uses the current timezone.
        """
        start_date = timezone.localtime(self.start_datetime).date()
        end_date = timezone.localtime(self.end_datetime).date()
        return start_date != end_date

    def get_num_guests(self):
        """Return the number of guests signed-up users are bringing along.

        This number does not include the signed-up users, themselves; only
        their guests are counted here.
        """
        return (self.eventsignup_set.filter(unsignup=False).aggregate(
                Sum('num_guests'))['num_guests__sum'] or 0)

    def get_num_rsvps(self, include_guests=True):
        """Return the expected number of attendees based on signups.

        This value includes the total number of signed up users. If
        include_guests is True (as default), this count also includes the
        number of guests for each signup.
        """
        count = self.eventsignup_set.filter(unsignup=False).count()
        if include_guests:
            count += self.get_num_guests()
        return count

    def can_user_sign_up(self, user):
        """Return true if the given user is allowed to sign up for this event.

        This method is based on the "restriction" level for the event.
        """
        return Event.get_user_restriction_level(user) >= self.restriction

    def can_user_view(self, user):
        """Return true if the given user is allowed to view this event.

        This method is based on the "restriction" level for the event.
        Note that CANDIDATE-restricted events are publicly visible (though
        still restricting signups).
        """
        if self.restriction in Event.VISIBLE_TO_EVERYONE:
            return True
        return Event.get_user_restriction_level(user) >= self.restriction

    def attendance_submitted(self):
        """Return True if there are any attendance records for this event."""
        return self.eventattendance_set.exists()

    def list_date(self):
        """Return a succinct string representation of the event date.

        An example is 'Sat, Nov 3'. For a multiday event, an example is
        'Mon, Mar 5 - Tue, Mar 6'.
        """
        date = Event.__get_abbrev_date_string(self.start_datetime)
        if self.is_multiday():
            date = '{} - {}'.format(
                date, Event.__get_abbrev_date_string(self.end_datetime))
        return date

    def list_time(self):
        """Return a succinct string representation of the event time.

        An example is '5:30 PM - 7:00 PM'. For a multiday event, the dates are
        included, as well. For instance, '(6/13) 11:15 PM - (6/14) 5:00 AM'.
        """
        start_time = Event.__get_time_string(self.start_datetime)
        end_time = Event.__get_time_string(self.end_datetime)
        if self.is_multiday():
            start_datetime = timezone.localtime(self.start_datetime)
            start_date = defaultfilters.date(start_datetime, 'n/j')
            end_datetime = timezone.localtime(self.end_datetime)
            end_date = defaultfilters.date(end_datetime, 'n/j')
            return '({}) {} - ({}) {}'.format(
                start_date, start_time, end_date, end_time)
        elif start_time == end_time:
            return 'TBA'
        else:
            return '{} - {}'.format(start_time, end_time)

    def view_datetime(self):
        """Return a succinct string representation of the event date and time.

        An example is 'Sat, Nov 3 5:15 PM to 6:45 PM'. For a multiday event,
        an example is 'Mon, Mar 5 11:00 AM to Tue, Mar 6 11:00 AM'.
        """
        start_time = Event.__get_time_string(self.start_datetime)
        start_date = Event.__get_abbrev_date_string(self.start_datetime)
        end_string = Event.__get_time_string(self.end_datetime)
        if self.is_multiday():
            end_string = '{} {}'.format(
                Event.__get_abbrev_date_string(self.end_datetime), end_string)
        elif start_time == end_string:
            return '{} Time TBA'.format(start_date)
        return '{} {} to {}'.format(start_date, start_time, end_string)

    def get_gcal_event_url(self):
        """Used when generating the 'Add to Google Calendar' button for
        a single event.

        Outputs the string for the url link to add a single event to
        Google calendar.
        """
        format_string = '%Y%m%dT%H%M%SZ'
        start_datetime_str = self.start_datetime.strftime(format_string)
        end_datetime_str = self.end_datetime.strftime(format_string)
        url = self.get_absolute_url()
        dates = u'{}/{}'.format(start_datetime_str, end_datetime_str)
        details = u'{}\n\nhttps://{}{}'.format(
            self.description, settings.HOSTNAME, url)
        sprop = u'name:Tau Beta Pi - {}'.format(self.name)
        # Use ASCII byte-string for URL
        gcal_event_str = 'https://www.google.com/calendar/event?{}'.format(
            urlencode({'action': 'TEMPLATE',
                       'dates': dates,
                       'details': details,
                       'location': self.location,
                       'sprop': sprop,
                       'text': self.name,
                       'trp': 'true'}))
        return gcal_event_str

    # TODO(sjdemartini): re-implement attendence_submitted() function

    # TODO(sjdemartini): re-implement sending email to VPs when event saved

    @staticmethod
    def __get_abbrev_date_string(datetime_object):
        """Return a 'weekday, month day#' abbreviated string representation of
        the datetime object.

        Ensures that the time is displayed in the current timezone.

        An example output could be 'Sat, Nov 3'.
        """
        datetime_object = timezone.localtime(datetime_object)
        return defaultfilters.date(datetime_object, 'D, M j')

    @staticmethod
    def __get_time_string(datetime_object):
        """Return the current time in 12-hour AM/PM format.

        Ensures that the time is displayed in the current timezone.

        An example output could be '10:42 PM'.
        """
        datetime_object = timezone.localtime(datetime_object)
        return defaultfilters.date(datetime_object, 'g:i A')

    @staticmethod
    def get_user_restriction_level(user):
        """Return the maximum event restriction level this user can access, or
        the public restriction level if no user is provided.
        """
        if user and user.is_authenticated:
            if user.userprofile.is_officer():
                return Event.OFFICER
            elif user.userprofile.is_member():
                return Event.MEMBER
            elif user.userprofile.is_candidate(False):
                return Event.CANDIDATE
        return Event.PUBLIC


class EventSignUp(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)

    num_guests = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='number of guests you are bringing')
    driving = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=('how many people fit in your car, including yourself '
                      '(0 if not driving)'))
    comments = models.TextField(
        blank=True, verbose_name='comments (optional)')

    # Name and email are necessary for anonymous signups (when user is null)
    # Name of the person signing up:
    name = models.CharField(max_length=255, blank=True)
    # The person's email address:
    email = models.EmailField(
        blank=True, verbose_name='email address',
        help_text='Your email address will be used to later update your signup '
                  'or to unsign up.')

    timestamp = models.DateTimeField(auto_now=True)

    unsignup = models.BooleanField(default=False)

    class Meta(object):
        ordering = ('timestamp',)
        unique_together = ('event', 'user')
        permissions = (
            ('view_signups', 'Can view who has signed up for events'),
            ('view_comments', 'Can view sign-up comments'),
            ('view_driving_numbers', 'Can view driving number details'),
        )

    def __str__(self):
        action = 'unsigned' if self.unsignup else 'signed'
        if self.user is None:
            name = self.name
        else:
            name = self.user.get_full_name()
        guest_string = (
            u' (+{})'.format(self.num_guests) if self.num_guests > 0 else '')
        return u'{person}{guests} has {action} up for {event_name}'.format(
            person=name,
            guests=guest_string,
            action=action,
            event_name=self.event.name)


class EventAttendance(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    # TODO(sjdemartini): Deal with the pre-noiro attendance importing? Note
    # that noiro added a separate field here to handle pre-noiro attendance
    # imports, as well as ImportedAttendance objects

    def __str__(self):
        return '{} attended {}'.format(self.user.get_full_name(),
                                       self.event.name)

    def save(self, *args, **kwargs):
        """If a project report is required for the corresponding event, add the
        user to the appropriate attendance list.
        """
        if self.event.project_report:
            project_report = self.event.project_report
            user_profile = self.user.userprofile
            if user_profile.is_officer(current=True):
                project_report.officer_list.add(self.user)
            elif user_profile.is_candidate():
                project_report.candidate_list.add(self.user)
            elif user_profile.is_member():
                project_report.member_list.add(self.user)
        super(EventAttendance, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """If a project report is required for the corresponding event, remove
        the user from all attendance lists.
        """
        if self.event.project_report:
            project_report = self.event.project_report
            project_report.officer_list.remove(self.user)
            project_report.candidate_list.remove(self.user)
            project_report.member_list.remove(self.user)
        super(EventAttendance, self).delete(*args, **kwargs)

    class Meta(object):
        unique_together = ('event', 'user')
