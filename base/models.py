from django.db import models

# Create your models here.
class Department(models.Model):
    abbreviated_name = models.CharField(unique=True, max_length=10)
    long_name = models.CharField(max_length=255)

    def __str__(self):
        return "{} ({})".format(self.long_name, self.abbreviated_name)

class Instructor(models.Model):
    first_name       = models.CharField(max_length=255)
    middle_name      = models.CharField(max_length=255, default="")
    last_name        = models.CharField(max_length=255, default="")
    department       = models.ForeignKey(Department, on_delete=models.CASCADE, null=True)

    # Instructor allowing exams (Exams are Copyrighted)
    exam_permissions = models.BooleanField(default=False)

    def getFullName(self):
        return self.first_name + ((" " + self.middle_name) if len(self.middle_name) != 0 else "") + \
            ((" " + self.last_name) if len(self.last_name) != 0 else "")

    def __str__(self):
        return "{} (Department: {})".format(self.getFullName(), self.department)

class Course(models.Model):
    name       = models.CharField(max_length=255, null=False)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=False)
    number     = models.CharField(max_length=10, null=False)

    def __str__(self):
        return "{} {}".format(self.department.abbreviated_name, self.number)

class Semester(models.Model):
    semester = models.CharField(max_length=255)

    def __str__(self):
         return "{}".format(self.semester)

class CourseSemester(models.Model):
    course      = models.ForeignKey(Course, on_delete=models.CASCADE, null=True)
    semester    = models.ForeignKey(Semester, on_delete=models.CASCADE)

    # instructor  = models.ForeignKey(Instructor, on_delete=models.CASCADE, null=False)
    instructors = models.ManyToManyField(Instructor, blank=False)
    
    def __str__(self):
        return "CourseSemester(course={}, semester={})".format(self.course, self.semester)
