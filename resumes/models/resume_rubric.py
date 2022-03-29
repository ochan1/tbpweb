from django.db import models
from resumes.models.resume import Resume

class ResumeCriteriaCategory(models.Model):
    category_text = models.TextField()
    visible_user = models.BooleanField(default=False, help_text="Whether to show this criteria to users")
    visible_grader = models.BooleanField(default=False, help_text="Whether to show this criteria to graders")

    def __str__(self):
        return self.category_text

class ResumeCriteria(models.Model):
    category = models.ForeignKey(ResumeCriteriaCategory, blank=True, null=True, on_delete=models.SET_NULL)
    choice_text = models.TextField()
    visible_user = models.BooleanField(default=False, help_text="Whether to show this criteria to users")
    visible_grader = models.BooleanField(default=False, help_text="Whether to show this criteria to graders")

    def get_label(self):
        text = self.choice_text
        if self.category is not None:
            text = "{} - {}".format(self.category, self.choice_text)
        return text

    def __str__(self):
        return self.get_label()

class ResumeReview(models.Model):
    resume = models.ForeignKey(Resume,
                                help_text="Resume related to this review.",
                                on_delete=models.CASCADE)
    criterias = models.ManyToManyField(ResumeCriteria, blank=True)
    comments = models.TextField(blank=True)
    email_sent = models.BooleanField(default=False)

    def resume_email_sent(self):
        self.email_sent = True
    
    def __str__(self):
        return "{} Resume Review - Email Sent: {}".format(self.resume.user, self.email_sent)
