from pytz import timezone as tz
from datetime import datetime
from datetime import timedelta
import json
import vobject

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.core.serializers.json import DjangoJSONEncoder
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, FormView, ListView, TemplateView, UpdateView
from accounts.models import APIKey
from base.models import Term
from base.views import TermParameterMixin
from candidates.models import Candidate
from events.forms import EventForm, EventSignUpAnonymousForm, EventSignUpForm, EventCancelForm
from events.models import Event, EventAttendance, EventSignUp
from project_reports.models import ProjectReport
from shortcuts import create_leaderboard
from utils.ajax import AjaxFormResponseMixin, json_response


user_model = get_user_model()


class EventBuilderView(TermParameterMixin, ListView):
    """List events in a particular term (display_term from TermParameterMixin).

    The show_all boolean parameter (default false) is taken from a show_all URL
    get request parameter. When true, the queryset includes all events from the
    display_term. Note that the show_all parameter can be passed as a keyword
    argument to the view in the as_view() method.
    """
    context_object_name = 'events'
    template_name = 'events/builder.html'
    show_all = False

    def get_queryset(self):
        show_all_val = self.request.GET.get('show_all', '')
        events = Event.objects.get_user_viewable(self.request.user)
        if (not self.is_current or self.show_all or
                show_all_val.lower() == 'true'):
            # Show all events in the display_term if the term is not the
            # current term, or if the show_all parameter is "true"
            self.show_all = True
            events = events.filter(term=self.display_term)
        else:
            # Events from the current term that have not yet ended and have not
            # been cancelled
            events = events.get_upcoming()
        return events.select_related('event_type', 'committee')

    def get_context_data(self, **kwargs):
        context = super(EventBuilderView, self).get_context_data(**kwargs)
        context['show_all'] = self.show_all
        all_events = []
        for event in self.get_queryset():
            event_data = {
                "name": event.name,
                "time": event.list_time(),
                "location": event.location,
                "date": event.list_date(),
                "type": event.event_type.name,
                "pk": event.pk
            }
            all_events.append(event_data)
        context['json_data'] = json.dumps(all_events, cls=DjangoJSONEncoder)
        if not self.request.user.is_authenticated:
            login_message = format_html(u'Please <a href="{}">log in</a>! Some '
                                        'events may not be visible.',
                                        reverse('accounts:login'))
            messages.info(self.request, login_message)
        return context


class EventListView(TermParameterMixin, ListView):
    """List events in a particular term (display_term from TermParameterMixin).

    The show_all boolean parameter (default false) is taken from a show_all URL
    get request parameter. When true, the queryset includes all events from the
    display_term. Note that the show_all parameter can be passed as a keyword
    argument to the view in the as_view() method.
    """
    context_object_name = 'events'
    template_name = 'events/list.html'
    show_all = False

    def get_queryset(self):
        show_all_val = self.request.GET.get('show_all', '')
        events = Event.objects.get_user_viewable(self.request.user)
        if (not self.is_current or self.show_all or
                show_all_val.lower() == 'true'):
            # Show all events in the display_term if the term is not the
            # current term, or if the show_all parameter is "true"
            self.show_all = True
            events = events.filter(term=self.display_term)
        else:
            # Events from the current term that have not yet ended and have not
            # been cancelled
            events = events.get_upcoming()
        return events.select_related('event_type', 'committee')

    def get_context_data(self, **kwargs):
        context = super(EventListView, self).get_context_data(**kwargs)
        context['show_all'] = self.show_all
        if not self.request.user.is_authenticated:
            login_message = format_html(u'Please <a href="{}">log in</a>! Some '
                                        'events may not be visible.',
                                        reverse('accounts:login'))
            messages.info(self.request, login_message)
        return context


class EventCreateView(CreateView):
    """View for adding new events."""
    form_class = EventForm
    template_name = 'events/add.html'

    @method_decorator(login_required)
    @method_decorator(
        permission_required('events.add_event', raise_exception=True))
    def dispatch(self, *args, **kwargs):
        return super(EventCreateView, self).dispatch(*args, **kwargs)

    def get_initial(self):
        start_time = timezone.now().replace(minute=0, second=0)
        end_time = start_time + timedelta(hours=1)
        current_term = Term.objects.get_current_term()
        return {'start_datetime': start_time,
                'end_datetime': end_time,
                'term': current_term.id if current_term else None,
                'contact': self.request.user,  # usable since login_required
                'needs_pr': True}

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct your input fields.')
        return super(EventCreateView, self).form_invalid(form)

    def form_valid(self, form):
        messages.success(self.request, 'Event Successfully Created!')
        return super(EventCreateView, self).form_valid(form)


class EventUpdateView(UpdateView):
    """View for editing a previously-created event."""
    form_class = EventForm
    model = Event
    pk_url_kwarg = 'event_pk'
    template_name = 'events/edit.html'

    @method_decorator(login_required)
    @method_decorator(
        permission_required('events.change_event', raise_exception=True))
    def dispatch(self, *args, **kwargs):
        return super(EventUpdateView, self).dispatch(*args, **kwargs)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct your input fields.')
        return super(EventUpdateView, self).form_invalid(form)

    def form_valid(self, form):
        messages.success(self.request, 'Event Successfully Updated!')
        return super(EventUpdateView, self).form_valid(form)


class EventDetailView(DetailView):
    """View for event details and signing up for events (GET requests)."""
    pk_url_kwarg = 'event_pk'
    model = Event
    template_name = 'events/detail.html'
    object = None  # The event object being fetched for the DetailView

    @method_decorator(require_GET)
    def dispatch(self, *args, **kwargs):
        self.object = self.get_object()
        # If this user can't view the current event, redirect to login if they
        # aren't already logged in; otherwise raise PermissionDenied
        if not self.object.can_user_view(self.request.user):
            if self.request.user.is_authenticated:
                raise PermissionDenied
            else:
                return redirect_to_login(self.request.path)
        return super(EventDetailView, self).dispatch(*args, **kwargs)

    def get_object(self, *args, **kwargs):
        """Return the event object for the detail view.

        Use the cached copy of the object if it exists, otherwise call the
        superclass method. This is useful because get_object is called early
        by the dispatch method.
        """
        return self.object or super(EventDetailView, self).get_object(
            *args, **kwargs)

    def post(self, *args, **kwargs):
        # Enable the view to perform the same action on post as for get
        return self.get(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(EventDetailView, self).get_context_data(**kwargs)

        context['signup_list'] = self.object.eventsignup_set.filter(
            unsignup=False).select_related('user', 'user__userprofile')

        signup = None

        if (not self.object.is_upcoming()
                or not self.object.can_user_sign_up(self.request.user)):
            # If the event is no longer upcoming or the user isn't allowed to
            # sign up, don't supply a signup form.
            context['form'] = None
        else:
            if self.request.user.is_authenticated:
                try:
                    signup = EventSignUp.objects.get(
                        event=self.object, user=self.request.user)
                    if signup.unsignup:
                        # If the user has unsigned up, provide a new signup
                        # form
                        context['form'] = EventSignUpForm(self.object)
                    else:
                        context['form'] = EventSignUpForm(
                            self.object, instance=signup)
                except EventSignUp.DoesNotExist:
                    context['form'] = EventSignUpForm(
                        self.object,
                        initial={'name': self.request.user.get_full_name()})
            else:
                context['form'] = EventSignUpAnonymousForm(self.object)

        context['user_signed_up'] = signup is not None and not signup.unsignup

        context['num_signups'] = len(context['signup_list'])
        context['num_guests'] = self.object.get_num_guests()
        total_rsvps = context['num_signups'] + context['num_guests']

        context['total_seats'] = context['signup_list'].aggregate(
            Sum('driving'))['driving__sum'] or 0

        context['available_seats'] = context['total_seats'] - total_rsvps

        def signup_sort_key(signup):
            if signup.user:
                return signup.user.userprofile.get_common_name()
            else:
                return signup.name

        # Sort the signup list using the user's common name or the name used
        # in signup (if anonymous signup)
        context['signup_list'] = sorted(context['signup_list'],
                                        key=signup_sort_key)
        return context


class EventSignUpView(AjaxFormResponseMixin, FormView):
    """Handles the form action for signing up for events (POST requests)."""
    # TODO(sjdemartini): Handle various scenarios for failed signups. For
    # instance, no more spots left, not allowed to bring x number of guests,
    # etc.
    event = None  # The event that this sign-up corresponds to
    object = None  # The event signup object

    @method_decorator(require_POST)
    def dispatch(self, *args, **kwargs):
        self.event = get_object_or_404(Event, pk=self.kwargs['event_pk'])
        # A user cannot sign up unless they have permission to do so
        if not self.event.can_user_sign_up(self.request.user):
            return json_response(status=403)
        return super(EventSignUpView, self).dispatch(*args, **kwargs)

    def get_form_class(self):
        if self.request.user.is_authenticated:
            return EventSignUpForm
        else:
            return EventSignUpAnonymousForm

    def get_form_kwargs(self, **kwargs):
        """Set the event and the user in the form."""
        kwargs = super(EventSignUpView, self).get_form_kwargs(**kwargs)
        kwargs['event'] = self.event
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        """Check whether the signup was created or updated."""
        self.object = form.save(commit=False)
        created = self.object.pk is None
        self.object.save()

        if created:
            msg = 'Signup successful!'
        else:
            msg = 'Signup updated!'

        messages.success(self.request, msg)
        return self.render_to_json_response()

    def get_success_url(self):
        return self.event.get_absolute_url()


class EventCancelView(FormView):
    """Handle cancelling events. If an event also has a project report,
    give the option to delete that as well.
    """
    success_url = reverse_lazy('events:list')
    form_class = EventCancelForm
    template_name = 'events/cancel.html'
    event = None

    @method_decorator(login_required)
    @method_decorator(
        permission_required('events.delete_event', raise_exception=True))
    def dispatch(self, *args, **kwargs):
        self.event = get_object_or_404(Event, pk=self.kwargs['event_pk'])
        return super(EventCancelView, self).dispatch(*args, **kwargs)

    def get_form(self, form_class=form_class):
        form = super(EventCancelView, self).get_form(form_class)
        form.event = self.event
        return form

    def form_valid(self, form):
        """Don't delete events, just cancel them.
        Also delete the associated project report if requested.
        """
        messages.success(self.request, 'Event successfully canceled.')
        return super(EventCancelView, self).form_valid(form)


@login_required
@permission_required('events.delete_event', raise_exception=True)
def event_revive(request, event_pk):
    """Revive a previously cancelled event."""
    try:
        event = Event.objects.get(pk=event_pk)
    except:
        return json_response(status=404)
    event.cancelled = False
    event.save()
    if event.project_report is None:
        project_report = ProjectReport()
    else:
        project_report = event.project_report
    project_report.term = event.term
    project_report.date = event.end_datetime.date()
    project_report.title = event.name
    project_report.author = event.contact
    project_report.committee = event.committee
    project_report.save()
    event.project_report = project_report
    event.save(update_fields=['project_report'])
    return redirect('events:detail', event_pk=event.pk)


@require_POST
def event_unsignup(request, event_pk):
    """Handles the action of un-signing up for events."""
    try:
        event = Event.objects.get(pk=event_pk)
    except:
        return json_response(status=400)
    success_msg = 'Unsignup successful.'
    if request.user.is_authenticated:
        try:
            # Try to get a signup object for this user
            signup = EventSignUp.objects.get(event=event, user=request.user)
            signup.user = request.user

            # Set the signup as "unsigned up"
            signup.unsignup = True
            signup.save()

            messages.success(request, success_msg)
        except EventSignUp.DoesNotExist:
            # If a signup could not be found, ignore this, since the user
            # is not signed up for the event
            pass
    else:
        email = request.POST.get('email')
        if email:
            try:
                signup = EventSignUp.objects.get(event=event, email=email)
                signup.unsignup = True
                signup.save()
                messages.success(request, success_msg)
            except:
                errors = {'email': ('The email address you entered was not '
                                    'used to sign up.')}
                return json_response(status=400, data=errors)
        else:
            errors = {
                'email': 'Please enter the email address you used to sign up.'
            }
            return json_response(status=400, data=errors)
    return json_response()


class AttendanceRecordView(DetailView):
    """View for recording attendance for a given event."""
    model = Event
    context_object_name = 'event'
    pk_url_kwarg = 'event_pk'
    template_name = 'events/attendance.html'

    @method_decorator(login_required)
    @method_decorator(
        permission_required('events.add_eventattendance', raise_exception=True))
    def dispatch(self, *args, **kwargs):
        return super(AttendanceRecordView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(AttendanceRecordView, self).get_context_data(**kwargs)
        current_term = Term.objects.get_current_term()

        officers = user_model.objects.filter(
            officer__term=current_term).select_related(
            'userprofile').order_by('userprofile').distinct()
        context['officers'] = officers

        candidates = user_model.objects.filter(
            candidate__term=current_term).select_related(
            'userprofile').order_by('userprofile').distinct()
        context['candidates'] = candidates

        # Get all other users (not including officers or candidates) who either
        # signed up or received attendance for this event:
        context['members'] = user_model.objects.filter(
            Q(eventsignup__event=self.object, eventsignup__unsignup=False) |
            Q(eventattendance__event=self.object)).distinct().exclude(
            Q(pk__in=officers) | Q(pk__in=candidates)).select_related(
            'userprofile').order_by('userprofile')

        # Create a set of the pk's of attendees', useful for checking (in
        # constant time) whether a given user is an attendee:
        context['attendees'] = set(user_model.objects.filter(
            eventattendance__event=self.object).values_list('pk', flat=True))

        # Similarly create a set of the pk's of people who have signed up:
        context['signed_up'] = set(user_model.objects.filter(
            eventsignup__event=self.object,
            eventsignup__unsignup=False).values_list('pk', flat=True))

        return context


@require_POST
@permission_required('events.add_eventattendance', raise_exception=True)
def attendance_submit(request):
    """Record attendance for a given user at a given event.

    The user is specified by a userPK post parameter, and the event is
    specified by an eventPK post parameter.
    """
    event_pk = request.POST['eventPK']
    event = Event.objects.get(pk=event_pk)
    user_pk = request.POST['userPK']
    user = user_model.objects.get(pk=user_pk)
    # Record attendance for this user at this event
    EventAttendance.objects.get_or_create(user=user, event=event)
    return json_response()


@require_POST
@permission_required('events.delete_eventattendance', raise_exception=True)
def attendance_delete(request):
    """Remove attendance for a given user at a given event.

    The user is specified by a userPK post parameter, and the event is
    specified by an eventPK post parameter.
    """
    event_pk = request.POST['eventPK']
    event = Event.objects.get(pk=event_pk)
    user_pk = request.POST['userPK']
    # Delete this user's attendance for the event if it exists:
    try:
        EventAttendance.objects.get(user__pk=user_pk, event=event).delete()
    except EventAttendance.DoesNotExist:
        # Fine if the attendance does not exist, since we wanted to remove it
        pass
    return json_response()


def attendance_search(request, max_results=20):
    """Return a JSON response of members based on search for name.

    The search uses the "searchTerm" post parameter. Return up to max_results
    number of results. The results only include people who have not attended
    the event specified by the post parameter eventPK.
    """
    search_query = request.GET['searchTerm']
    event_pk = request.GET['eventPK']
    event = Event.objects.get(pk=event_pk)

    # Get all users who did not attend this event:
    # TODO(sjdemartini): Properly filter for members, instead of just getting
    # all users who are not officers or candidates (as these other users may
    # include company users, etc.)
    members = user_model.objects.exclude(
        eventattendance__event=event).select_related(
        'userprofile')

    # A list of entries for each member that matches the search query:
    member_matches = []

    # Parse the search query into separate pieces if the query includes
    # whitespace
    search_terms = search_query.lower().split()
    for member in members:
        name = member.userprofile.get_verbose_full_name()
        name_lower = name.lower()
        if all(search_term in name_lower for search_term in search_terms):
            pic_html = render_to_string(
                '_user_thumbnail.html',
                {'user_profile': member.userprofile})
            entry = {
                'label': name,
                'value': member.pk,
                'picture': pic_html
            }
            member_matches.append(entry)
        if len(member_matches) >= max_results:
            break
    return json_response(data=member_matches)


class IndividualAttendanceListView(TermParameterMixin, TemplateView):
    template_name = 'events/individual_attendance.html'
    attendance_user = None

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        self.attendance_user = get_object_or_404(
            user_model, username=self.kwargs['username'])
        return super(IndividualAttendanceListView, self).dispatch(
            *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(
            IndividualAttendanceListView, self).get_context_data(**kwargs)
        context['attendance_user'] = self.attendance_user

        # Get non-cancelled events from the given term, and select_related for
        # event_type, since it is used in the template for each event:
        events = Event.objects.get_user_viewable(self.request.user).filter(
            term=self.display_term, cancelled=False).order_by(
            'end_datetime').select_related('event_type')

        current_time = timezone.now()
        past_events = events.filter(end_datetime__lte=current_time)
        future_events = events.filter(end_datetime__gt=current_time)

        context['attended'] = past_events.filter(
            eventattendance__user=self.attendance_user)

        # Get future events that the user has either signed up for or already
        # received attendance for:
        signup_filter = Q(eventsignup__user=self.attendance_user,
                          eventsignup__unsignup=False)
        attendance_filter = Q(eventattendance__user=self.attendance_user)
        participation_filter = signup_filter | attendance_filter
        context['future_participating'] = future_events.filter(
            participation_filter).distinct()

        # Get past events that don't have attendance recorded:
        context['past_not_recorded'] = past_events.filter(
            eventattendance__isnull=True)

        # Get past events (that had attendance recorded) that the user did not
        # attend:
        context['not_attended'] = past_events.exclude(
            eventattendance__isnull=True).exclude(pk__in=context['attended'])

        # Get future events for which the user has not signed up or received
        # attendance:
        context['future_not_participating'] = future_events.exclude(
            pk__in=context['future_participating'])

        return context


class LeaderboardListView(TermParameterMixin, ListView):
    """View for selecting all users who have attended an event in a
    particular term (display_term from TermParameterMixin).

    The view omits all users with no attendance.
    """
    context_object_name = 'leader_list'
    paginate_by = 75
    template_name = 'events/leaderboard.html'
    candidate_aggregate = None
    member_aggregate = None
    officer_aggregate = None
    top_officer = None
    top_candidate = None
    top_member = None

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        # Create dicts of aggregates for officers, candidates, and members
        # (including advisors), with the total number of users of that category
        # who have attended events this semester and the total number of events
        # that group has attended.
        self.candidate_aggregate = {'attendees': 0,
                                    'attendance': 0,
                                    'ratio': 0}
        self.member_aggregate = {'attendees': 0,
                                 'attendance': 0,
                                 'ratio': 0}
        self.officer_aggregate = {'attendees': 0,
                                  'attendance': 0,
                                  'ratio': 0}

        return super(LeaderboardListView, self).dispatch(*args, **kwargs)

    def get_queryset(self):
        leaders = get_user_model().objects.filter(
            eventattendance__event__term=self.display_term,
            eventattendance__event__cancelled=False).select_related(
            'studentorguserprofile').annotate(
            score=Count('eventattendance')).order_by('-score')

        backup = get_user_model().objects.filter(
            eventattendance__event__term=self.display_term,
            eventattendance__event__cancelled=False).select_related(
            'userprofile').annotate(
            score=Count('eventattendance')).order_by('-score')

        if len(leaders) > 0:
            max_events = leaders[0].score or 0
        else:
            max_events = 0

        # Create a list of "leader" entries, where each entry is a dictionary
        # that includes the user, their rank on the leaderboard (1st, 2nd,
        # etc.), and their leaderboard width "factor" (see below for details).
        leader_list = []
        if max_events > 0:  # make sure there's no divide by zero
            prev_value = -1
            prev_rank = 1

            for i, leader in enumerate(leaders, start=prev_rank):
                # factor used for CSS width property (percentage). Use 70 as
                # the max width (i.e. the user who attended the most events has
                # width 70%), including adding 2.5 to every factor to make sure
                # that there is enough room for text to be displayed.
                factor = 2.5 + leader.score * 67.5 / max_events

                # Determine the position of the leader for use in CSS styling
                # as well as updating the position aggregates and checking if
                # this user is at the top of their position group
                try:
                    profile = leader.studentorguserprofile
                except:
                    temp_profile = backup[i].userprofile
                    profile = temp_profile.get_student_org_user_profile()
                officer_positions = profile.get_officer_positions(
                    term=self.display_term).exclude(auxiliary=True)
                is_term_officer = officer_positions.exists()

                is_term_candidate = Candidate.objects.filter(
                    user=leader, term=self.display_term).exists()

                if is_term_officer:
                    position = 'officer'
                    self.officer_aggregate['attendees'] += 1
                    self.officer_aggregate['attendance'] += leader.score

                    if self.officer_aggregate['attendees'] == 1:
                        self.top_officer = leader

                elif is_term_candidate:
                    position = 'candidate'
                    self.candidate_aggregate['attendees'] += 1
                    self.candidate_aggregate['attendance'] += leader.score

                    if self.candidate_aggregate['attendees'] == 1:
                        self.top_candidate = leader

                else:
                    position = 'member'
                    self.member_aggregate['attendees'] += 1
                    self.member_aggregate['attendance'] += leader.score

                    if self.member_aggregate['attendees'] == 1:
                        self.top_member = leader

                if leader.score == prev_value:
                    rank = prev_rank
                else:
                    rank = i
                prev_rank = rank
                prev_value = leader.score

                # Add the leader entry to the list
                leader_list.append({'user': leader,
                                    'position': position,
                                    'factor': factor,
                                    'rank': rank})
        return leader_list

    def get_context_data(self, **kwargs):
        context = super(LeaderboardListView, self).get_context_data(**kwargs)

        # Obtain the number of events per user in each position category
        self.candidate_aggregate['ratio'] = (
            self.get_average_attendance(self.candidate_aggregate['attendees'],
                                        self.candidate_aggregate['attendance']))
        self.member_aggregate['ratio'] = (
            self.get_average_attendance(self.member_aggregate['attendees'],
                                        self.member_aggregate['attendance']))
        self.officer_aggregate['ratio'] = (
            self.get_average_attendance(self.officer_aggregate['attendees'],
                                        self.officer_aggregate['attendance']))

        context['candidate_aggregate'] = self.candidate_aggregate
        context['member_aggregate'] = self.member_aggregate
        context['officer_aggregate'] = self.officer_aggregate
        context['top_candidate'] = self.top_candidate
        context['top_member'] = self.top_member
        context['top_officer'] = self.top_officer

        return context

    def get_average_attendance(self, attendees, attendance):
        """Returns the average attendance for a group on the leaderboard."""
        return attendance / float(attendees) if attendees > 0 else 0


class AllTimeLeaderboardListView(TermParameterMixin, ListView):
    """View for selecting all users who have attended TBP events.

    The view omits all users with no attendance.
    """
    context_object_name = 'leader_list'
    paginate_by = 100
    template_name = 'events/leaderboard.html'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(AllTimeLeaderboardListView, self).dispatch(*args, **kwargs)

    def get_queryset(self):
        leaders = get_user_model().objects.filter(
            eventattendance__event__cancelled=False).select_related(
            'userprofile').annotate(score=Count('eventattendance')).order_by(
            '-score')

        return create_leaderboard(leaders, 70)

    def get_context_data(self, **kwargs):
        context = super(AllTimeLeaderboardListView, self).get_context_data(
            **kwargs)
        context['is_all_time'] = True

        return context


def ical(request, event_pk=None):
    """Return an ICS file for the given event, or for all events if no event
    primary key is provided.

    If a "term" URL parameter is given and no event pk is given, the view
    returns all events for that term.

    The view only shows events that the user is allowed to see, based on the
    "user" and "key" URL parameters (which correspond to the user's PK and API
    key, respectively). If the "user" and "key" parameters are not valid or are
    not provided, only publicly visible events are included.
    """
    cal = vobject.iCalendar()

    cal.add('calscale').value = 'Gregorian'
    cal.add('X-WR-TIMEZONE').value = 'America/Los_Angeles'
    calendar_name = '{} Events'.format(settings.SITE_TAG)
    cal.add('X-WR-CALNAME').value = calendar_name
    cal.add('X-WR-CALDESC').value = calendar_name

    vtimezone = cal.add('vtimezone')
    vtimezone.add('tzid').value = 'America/Los_Angeles'
    vtimezone.add('X-LIC-LOCATION').value = 'America/Los_Angeles'
    dst = vtimezone.add('daylight')
    dst.add('tzoffsetfrom').value = '-0800'
    dst.add('tzoffsetto').value = '-0700'
    dst.add('tzname').value = 'PDT'
    dst.add('dtstart').value = datetime(
        1970, 3, 8, 2, 0, 0, 0, tz('US/Pacific'))  # '19700308T020000'
    dst.add('rrule').value = 'FREQ=YEARLY;BYMONTH=3;BYDAY=2SU'
    std = vtimezone.add('standard')
    std.add('tzoffsetfrom').value = '-0700'
    std.add('tzoffsetto').value = '-0800'
    std.add('tzname').value = 'PST'
    std.add('dtstart').value = datetime(
        1970, 11, 1, 2, 0, 0, 0, tz('US/Pacific'))  # '19701101T020000'
    std.add('rrule').value = 'FREQ=YEARLY;BYMONTH=11;BYDAY=1SU'

    user = None
    user_pk = request.GET.get('user', None)
    key = request.GET.get('key', None)
    if user_pk and key:
        try:
            api_key = APIKey.objects.get(user__pk=user_pk, key=key)
            user = api_key.user
        except APIKey.DoesNotExist:
            pass

    if event_pk is None:
        # We want multiple events
        filename = 'events.ics'
        term = request.GET.get('term', '')
        selected_events = request.GET.get('selected', '[]')
        selected_events = json.loads(selected_events)
        events = Event.objects.get_user_viewable(user).filter(cancelled=False)
        if term:
            # Filter by the given term
            term_obj = Term.objects.get_by_url_name(term)
            events = events.filter(term=term_obj)
        for event in events:
            if len(selected_events) == 0 or event.pk in selected_events:
                add_event_to_ical(event, cal)
    else:
        # We want a specific event
        event = get_object_or_404(Event, pk=event_pk)
        if not event.can_user_view(user):
            raise PermissionDenied
        filename = 'event.ics'
        add_event_to_ical(event, cal)

    response = HttpResponse(cal.serialize(), content_type='text/calendar')
    response['Filename'] = filename  # IE needs this
    response['Content-Disposition'] = 'attachment; filename={}'.format(filename)
    return response


def add_event_to_ical(event, cal):
    """Helper method used by the ical view for adding an event to an ICS
    calendar object.

    Takes in "event" and "cal", where "event" is the actual event object and
    "cal" is the ical object.
    """
    ical_event = cal.add('vevent')
    name = event.name
    if event.restriction == Event.MEMBER:
        name += " (Members Only)"
    elif event.restriction == Event.OFFICER:
        name += " (Officers Only)"
    ical_event.add('summary').value = name
    ical_event.add('location').value = event.location
    event_url = 'https://{}{}'.format(settings.HOSTNAME,
                                      event.get_absolute_url())
    if event.description:
        description = u'{}\n\n{}'.format(event.description,
                                         event_url)
    else:
        description = event_url
    ical_event.add('description').value = description
    ical_event.add('dtstart').value = event.start_datetime
    ical_event.add('dtend').value = event.end_datetime
    ical_event.add('uid').value = str(event.id)
