from django.test import TestCase
from base.models import *

"""
import base.tests
setUpInstance = base.tests.setUpTest()
setUpInstance.refresh()
setUpInstance.setUp()
setUpInstance.addInstructors()
setUpInstance.showData()
setUpInstance.refresh()

"""

# Create your tests here.
class setUpTest(TestCase):
    def setUp(self):
        eecs = Department(abbreviated_name="Test-EECS", long_name="Electrical Engineering and Computer Science")
        print(eecs)
        eecs.save()
        
        anantGireeja = Instructor(first_name="Test-Anant", middle_name="", last_name="Gireeja", department=eecs, exam_permissions=True)
        print(anantGireeja)
        anantGireeja.save()

        eecs61a = Course(department=eecs, name="Test-Structure and Interpretations of MaThEmAtIcAl MaTuRiTy", number="61A")
        print(eecs61a)
        eecs61a.save()

        autumn2020 = Semester(semester="Test-Autumn 2020")
        print(autumn2020)
        autumn2020.save()

        autumn2020_eecs61a = CourseSemester(semester=autumn2020, course=eecs61a)
        print(autumn2020_eecs61a)
        autumn2020_eecs61a.save()
    
    def addInstructors(self):
        autumn2020_eecs61a = CourseSemester.objects.filter(course__department__abbreviated_name="Test-EECS").first()
        anantGireeja = Instructor.objects.filter(first_name="Test-Anant").first()
        autumn2020_eecs61a.instructors.add(anantGireeja)
    
    def refresh(self):
        Department.objects.filter(abbreviated_name__startswith="Test-").delete()
        Instructor.objects.filter(first_name__startswith="Test-").delete()
        Course.objects.filter(name__startswith="Test-").delete()
        Semester.objects.filter(semester__startswith="Test-").delete()
    
    def showData(self):
        items_to_show = [Department, Instructor, Course, Semester, CourseSemester]
        for item in items_to_show:
            print(item.objects.all())
        autumn2020_eecs61a = CourseSemester.objects.filter(course__department__abbreviated_name="Test-EECS").first()
        print("Instructors of the test course:", autumn2020_eecs61a.instructors.all())



