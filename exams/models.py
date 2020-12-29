from django.db import models

# Create your models here.
class CourseSemesterExams(models.Model):
    courseSemester      = models.ForeignKey("base.CourseSemester", on_delete=models.CASCADE, null=True)
    
    # Specific Course revokes exam permissions
    exam_release = models.BooleanField(default=False)

    def __str__(self):
        return "CourseSemesterExams(courseSemester={}, exam_release={})".format(self.courseSemester, self.exam_release)

class ExamTypes(models.Model):
    exam_type = models.CharField(max_length=10)

    def __str__(self):
        return self.exam_type

class Exams(models.Model):
    courseSemester = models.ForeignKey(CourseSemesterExams, on_delete=models.CASCADE, null=False)
    exam_type      = models.ForeignKey(ExamTypes, on_delete=models.CASCADE)
    exam_number    = models.IntegerField(default=-1)
    exam           = models.FileField(blank=True)
    exam_sol       = models.FileField(blank=True)

    def __str__(self):
        return "{} {} - {}".format(self.exam_type, self.exam_number, self.exam)

    # Style to AVOID:
    # midterm1    = models.FileField(blank=True)
    # midterm1_sol = models.FileField(blank=True)
    # midterm2    = models.FileField(blank=True)
    # midterm2_sol = models.FileField(blank=True)
    # midterm3    = models.FileField(blank=True)
    # midterm3_sol = models.FileField(blank=True)
    # final       = models.FileField(blank=True)
    # final_sol   = models.FileField(blank=True)

