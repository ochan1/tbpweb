from django.contrib import admin
from django.urls import path
from django.urls import include

import exams.views

# Will be everything after "exams/"
urlpatterns = [
    path('', exams.views.index),
    path('course/<department>/<number>/', exams.views.exams_for_course),
    
]
