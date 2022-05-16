from django.contrib import admin
from django.db import models

from resumes.models.resume import Resume
from resumes.models.resume_rubric import ResumeCriteria, ResumeCriteriaCategory, ResumeReview

class ResumeAdmin(admin.ModelAdmin):
    list_display = ('user', 'created', 'updated', 'verified', 'critique',
                    'release')
    list_filter = ('verified', 'critique', 'release')

class ResumeCriteriaCategoryAdmin(admin.ModelAdmin):
    list_display = ('category_text', 'visible_user', 'visible_grader')

class ResumeCriteriaAdmin(admin.ModelAdmin):
    list_display = ('category', 'choice_text', 'visible_user', 'visible_grader')

class ResumeReviewAdmin(admin.ModelAdmin):
    filter_horizontal = ('criterias',)

admin.site.register(Resume, ResumeAdmin)
admin.site.register(ResumeCriteriaCategory, ResumeCriteriaCategoryAdmin)
admin.site.register(ResumeCriteria, ResumeCriteriaAdmin)
admin.site.register(ResumeReview, ResumeReviewAdmin)
