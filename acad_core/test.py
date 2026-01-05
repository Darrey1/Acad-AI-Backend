# class NextQuestionAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request, exam_id):
#         exam = get_object_or_404(Exam, id=exam_id)

#         submission, _ = Submission.objects.get_or_create(
#             student=request.user,
#             exam=exam,
#             defaults={"started_at": timezone.now()},
#         )

#         # TIME ENFORCEMENT
#         if exam.duration:
#             elapsed = timezone.now() - submission.started_at
#             if elapsed > exam.duration:
#                 submission.status = Submission.Status.SUBMITTED
#                 submission.submitted_at = timezone.now()
#                 submission.save()
#                 return Response(
#                     {"detail": "Exam time elapsed. Exam auto-submitted."},
#                     status=status.HTTP_403_FORBIDDEN,
#                 )

#         # SAVE ANSWER (if provided)
#         question_id = request.data.get("question_id")
#         if question_id:
#             question = get_object_or_404(
#                 Question,
#                 id=question_id,
#                 exam=exam,
#             )

#             # Prevent re-answering
#             if Answer.objects.filter(
#                 submission=submission,
#                 question=question,
#             ).exists():
#                 return Response(
#                     {"detail": "Question already answered."},
#                     status=status.HTTP_400_BAD_REQUEST,
#                 )

#             Answer.objects.create(
#                 submission=submission,
#                 question=question,
#                 selected_choice_id=request.data.get("selected_choice"),
#                 answer_text=request.data.get("answer_text"),
#             )

#         # FETCH NEXT QUESTION
#         answered_ids = Answer.objects.filter(
#             submission=submission
#         ).values_list("question_id", flat=True)

#         next_question = (
#             Question.objects
#             .filter(exam=exam)
#             .exclude(id__in=answered_ids)
#             .order_by("id")
#             .first()
#         )

#         if not next_question:
#             submission.status = Submission.Status.PENDING
#             submission.save()
#             return Response(
#                 {"detail": "All questions answered. Please submit your exam."},
#                 status=status.HTTP_200_OK,
#             )

#         serializer = ExamPlayQuestionSerializer(next_question)
#         return Response(serializer.data)




# class SubmitExamAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request, exam_id):
#         submission = get_object_or_404(
#             Submission,
#             student=request.user,
#             exam_id=exam_id,
#         )

#         submission.status = Submission.Status.SUBMITTED
#         submission.submitted_at = timezone.now()
#         submission.save()

#         return Response({"message": "Exam submitted successfully, your score will be available soon."})