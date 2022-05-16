from django.urls import re_path

from resumes.views import ResumeListView, ResumeCritiqueView, ResumeDownloadView, \
                          ResumeEditView, ResumeVerifyView, ResumeReviewCritiqueView


urlpatterns = [
    re_path(r'^$', ResumeListView.as_view(), name='list'),
    re_path(r'^edit/$', ResumeEditView.as_view(), name='edit'),
    re_path(r'^download/$', ResumeDownloadView.as_view(), name='download'),
    re_path(r'^download/(?P<user_pk>\d+)/$',
        ResumeDownloadView.as_view(), name='download'),
    re_path(r'^critique/$', ResumeCritiqueView.as_view(), name='critique'),
    re_path(r'^verify/$', ResumeVerifyView.as_view(), name='verify'),
    re_path(r'^critique/review_critique/(?P<user_pk>\d+)/$',
        ResumeReviewCritiqueView.as_view(), name='review_critique'),
]
