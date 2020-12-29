from django.shortcuts import render
from django.apps import apps

# Create your views here.

Course = apps.get_model("base", "Course")
CourseSemester = apps.get_model("base", "CourseSemester")
Department = apps.get_model("base", "Department")
Instructor = apps.get_model("base", "Instructor")
Semester = apps.get_model("base", "Semester")

CourseSemesterExams = apps.get_model("exams", "CourseSemesterExams")
Exams = apps.get_model("exams", "Exams")

def index(request):
    courses = Course.objects.order_by('name')
    departments = Department.objects.order_by("long_name")

    context = {
        'courses': courses,
        'searchCourses': CourseSemester.objects.all(),
        'departments': departments
    }
    
    return render(request, 'index.html', context)

def exams_for_course(request, department, number):

    specificSemester = request.GET.get('term', '')
    # print(department)
    department = Department.objects.get(abbreviated_name=department)
    # print(department)
    course = Course.objects.filter(department__exact=department.id).get(number__exact=number)
    semesters = CourseSemester.objects.filter(course__exact=course.id)
    # print(semesters)
    semesters = semesters.filter(instructors__exam_permissions=True)
    print(semesters)
    courseSemesterExams = CourseSemesterExams.objects.filter(courseSemester__in=semesters, exam_release=True)
    print("courseSemesterExams:", courseSemesterExams)
    exams = Exams.objects.filter(courseSemester__in=courseSemesterExams)
    
    # if specificSemester:
    # 	subSemesters = semesters.filter(semester__semester__exact=specificSemester)
    # 	if subSemesters:
    # 		semesters = subSemesters
    # 	else:
    # 		specificSemester = ""
    print("HERE 1 --", exams, "--END")
    print("ENDHERE")
    exams = exams.order_by('exams__exam_type', 'exams__exam_number')
    print("HERE 2", exams.count())
    if exams.count() == 0:
        midterms = exams
        quizzes = exams
        finals = exams
        others = exams
    else:
        midterms = exams.filter(exams__exam_type="Midterm")
        quizzes = exams.filter(exams__exam_type="Quiz")
        finals = exams.filter(exams__exam_type="Final")
        others = exams.exclude(exams__exam_type__in=["Midterm", "Quiz", "Final"])
    print("PASS")
    context = {
        'course': course,
        'semesters': semesters,
        'midterms': midterms,
        'quizzes': quizzes,
        'finals': finals,
        'others': others,
        'selectedTerm': specificSemester
    }

    print("READY")

    return render(request, 'exams-course.html', context)

