from rest_framework import serializers
from .models import Course, CourseCategory, CourseModule, LearningOutcome

class CourseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseCategory
        fields = ["id", "name", "slug"]

class CourseModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseModule
        fields = ["id", "title", "description", "order"]

class LearningOutcomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningOutcome
        fields = ["id", "description", "order"]

class CourseListSerializer(serializers.ModelSerializer):
    category = CourseCategorySerializer(read_only=True)
    
    class Meta:
        model = Course
        fields = [
            "id", "code", "name", "slug", "short_description", "category",
            "credits", "semester", "academic_year", "level", "language",
            "featured", "published_at"
        ]

class CourseDetailSerializer(serializers.ModelSerializer):
    category = CourseCategorySerializer(read_only=True)
    modules = CourseModuleSerializer(many=True, read_only=True)
    outcomes = LearningOutcomeSerializer(many=True, read_only=True)
    
    class Meta:
        model = Course
        fields = [
            "id", "code", "name", "slug", "description", "short_description", 
            "category", "credits", "semester", "academic_year", "level", 
            "language", "featured", "thumbnail", "published_at",
            "modules", "outcomes"
        ]
