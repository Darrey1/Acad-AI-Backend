from django.contrib import admin
from .models import Exam, Question, Choice, Answer, Submission

admin.site.site_header = "Acad AI Assessment Admin"
admin.site.index_title = "Welcome to the Acad AI"


# Register models.
@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'duration', 'start_at', 'end_at', 'created_by', 'created_at')
    search_fields = ('title', 'course')
    list_filter = ('course', 'start_at', 'end_at', 'created_at')    
    

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('exam', 'type', 'max_score', 'created_at')
    search_fields = ('text',)
    list_filter = ('type', 'created_at')    


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ('question', 'text', 'is_correct')
    search_fields = ('text',)
    list_filter = ('is_correct',)   



@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('submission', 'question', 'score', 'created_at')
    search_fields = ('answer_text',)
    list_filter = ('created_at',)

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('exam', 'student', 'score', 'started_at', 'submitted_at')
    search_fields = ('student__username', 'student__email')
    list_filter = ('started_at', 'submitted_at')