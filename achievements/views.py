from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.urls import reverse
from django.urls import reverse_lazy
from django.db.models import Sum
from django.forms import HiddenInput
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.generic import FormView
from django.views.generic import ListView

from achievements.forms import UserAchievementForm
from achievements.models import Achievement
from achievements.models import UserAchievement
from shortcuts import create_leaderboard


class AchievementDetailView(FormView):
    template_name = 'achievements/achievement_detail.html'
    form_class = UserAchievementForm
    achievement = None

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        self.achievement = get_object_or_404(
            Achievement.objects.select_related(
                'icon', 'icon__creator'),
            short_name=self.kwargs['achievement_short_name'])
        return super(AchievementDetailView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(AchievementDetailView, self).get_context_data(**kwargs)

        context['achievement'] = self.achievement

        # Select the viewer's secret and private achievements so that they
        # can only see the ones they've unlocked.
        viewer_achievements = self.request.user.userachievement_set
        context['viewable_hidden_achievements'] = Achievement.objects.filter(
            userachievement__in=viewer_achievements.values_list('id')).exclude(
            privacy='public')

        # Find all users that have unlocked the achievement
        user_achievements = UserAchievement.objects.filter(
            achievement__short_name=context['achievement'].short_name).exclude(
            acquired=False).select_related('term', 'user', 'user__userprofile')
        context['user_achievements'] = user_achievements.order_by(
            'user__userprofile__preferred_name')

        # Find other achievements in same sequence to display related.
        context['related_achievements'] = Achievement.objects.filter(
            sequence=context['achievement'].sequence).exclude(
            short_name=context['achievement'].short_name).select_related(
            'icon')

        return context

    def get_initial(self):
        initial = super(AchievementDetailView, self).get_initial()
        initial['achievement'] = self.achievement

        return initial

    def get_form(self):
        form = super(AchievementDetailView, self).get_form(self.form_class)
        form.fields['achievement'].widget = HiddenInput()
        return form

    def form_valid(self, form):
        form.save(assigner=self.request.user)
        achievement = form.cleaned_data.get('achievement')
        users = form.cleaned_data.get('users')

        users_namestring = ', '.join(
            [user.userprofile.get_common_name() for user in users])

        messages.success(
            self.request,
            'Achievement {achievement} assigned to {names}'.format(
                achievement=achievement.name, names=users_namestring))
        return super(AchievementDetailView, self).form_valid(form)

    def get_success_url(self):
        return reverse('achievements:detail',
                       args=[self.kwargs['achievement_short_name']])


class LeaderboardListView(ListView):
    # select all users with >0 scores to display on leaderboard
    # and omits all users with 0 or negative scores
    context_object_name = 'leader_list'
    template_name = 'achievements/leaderboard.html'
    paginate_by = 35  # separates leaders into pages of 35 each

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(LeaderboardListView, self).dispatch(*args, **kwargs)

    def get_queryset(self):
        leaders = get_user_model().objects.filter(
            userachievement__acquired=True).select_related(
            'userprofile').annotate(
                score=Sum('userachievement__achievement__points')).filter(
            score__gte=0).order_by('-score')

        return create_leaderboard(leaders, 70)


class UserAchievementAssignView(FormView):
    """Provide an interface for the viewer to assign achievements to users."""
    form_class = UserAchievementForm
    model = UserAchievement
    success_url = reverse_lazy('achievements:assign')
    template_name = 'achievements/assign.html'

    @method_decorator(login_required)
    @method_decorator(
        permission_required('achievements.add_userachievement',
                            raise_exception=True))
    def dispatch(self, *args, **kwargs):
        return super(UserAchievementAssignView, self).dispatch(*args, **kwargs)

    def form_valid(self, form):
        form.save(assigner=self.request.user)
        achievement = form.cleaned_data.get('achievement')
        users = form.cleaned_data.get('users')

        users_namestring = ', '.join(
            [user.userprofile.get_common_name() for user in users])

        messages.success(
            self.request,
            'Achievement {achievement} assigned to {names}'.format(
                achievement=achievement.name, names=users_namestring))
        return super(UserAchievementAssignView, self).form_valid(form)


class UserAchievementListView(ListView):
    context_object_name = 'unlocked_list'
    template_name = 'achievements/user.html'
    display_user = None
    user_achievements = None
    user_points = 0

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        self.display_user = get_object_or_404(get_user_model(),
                                              id=self.kwargs['user_id'])
        self.user_achievements = self.display_user.userachievement_set.exclude(
            acquired=False).select_related(
            'achievement', 'achievement__icon', 'term').order_by(
            'achievement__rank')
        return super(UserAchievementListView, self).dispatch(*args, **kwargs)

    def get_queryset(self):
        queryset = self.user_achievements

        for userachievement in queryset:
            self.user_points += userachievement.achievement.points

        if self.request.user != self.display_user:
            queryset = queryset.exclude(achievement__privacy='private')

        return queryset

    def get_context_data(self, **kwargs):
        context = super(UserAchievementListView, self).get_context_data(
            **kwargs)
        context['display_user'] = self.display_user
        context['user_points'] = self.user_points
        context['user_num_achievements'] = self.user_achievements.count()

        # Select achievements that have ids not found in the list of obtained
        # user achievements (i.e. they have not been acquired yet or don't
        # exist), and obtain progresses from any related user achievements.
        locked_achievements = Achievement.objects.exclude(
            userachievement__in=self.user_achievements).exclude(
            privacy='private').select_related(
            'userachievement', 'icon').order_by('rank')

        # Create a dict relating achievements to the user's progress on that
        # achievement.
        locked_userachievements = UserAchievement.objects.filter(
            user=self.display_user, acquired=False).select_related(
            'achievement')
        locked_progresses = {}
        for locked_ua in locked_userachievements:
            locked_progresses[locked_ua.achievement] = locked_ua.progress

        progresses = []
        for achievement in locked_achievements:
            if achievement in locked_progresses:
                progresses.append(locked_progresses[achievement])
            else:
                progresses.append(0)

        locked_list = [{'achievement': t[0], 'progress': t[1]}
                       for t in zip(locked_achievements, progresses)]
        context['locked_list'] = locked_list

        # Select hidden achievements the viewer has unlocked so that they are
        # visible in other users' pages.
        viewer_achievements = self.request.user.userachievement_set
        context['viewer_secret_achievements'] = Achievement.objects.filter(
            userachievement__in=viewer_achievements.values_list('id'),
            privacy='secret')

        return context
