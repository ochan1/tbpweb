from django.db import models
from resumes.models.resume import Resume

class ResumeCriteriaCategory(models.Model):
    category_text = models.TextField()
    visible_user = models.BooleanField(default=False, help_text="Whether to show this criteria to users")
    visible_grader = models.BooleanField(default=False, help_text="Whether to show this criteria to graders")

class ResumeCriteria(models.Model):
    category = models.ForeignKey(ResumeCriteriaCategory, null=True)
    choice_text = models.TextField()
    visible_user = models.BooleanField(default=False, help_text="Whether to show this criteria to users")
    visible_grader = models.BooleanField(default=False, help_text="Whether to show this criteria to graders")

class ResumeReview(models.Model):
    resume = models.ForeignKey(Resume,
                                help_text="Resume related to this review.",
                                on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    resume_update_date = models.DateTimeField(help_text="The date of the last resume update date, to make sure this review is for the current resume version")
    criterias = models.ManyToManyField(ResumeCriteria)
    other_texts = models.TextField()
    email_sent = models.BooleanField(default=False)

    def resume_email_sent(self):
        self.email_sent = True
