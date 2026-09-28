from rest_framework import serializers

from .models import AcademicInterest, Education, Experience, Language, Profile


class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = [
            "id",
            "degree",
            "field",
            "institution",
            "country",
            "year_start",
            "year_end",
            "is_current",
            "description",
        ]


class ExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experience
        fields = [
            "id",
            "position",
            "organization",
            "department",
            "country",
            "year_start",
            "year_end",
            "is_current",
            "description",
        ]


class LanguageSerializer(serializers.ModelSerializer):
    proficiency_display = serializers.CharField(source="get_proficiency_display", read_only=True)

    class Meta:
        model = Language
        fields = ["id", "name", "proficiency", "proficiency_display"]


class AcademicInterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicInterest
        fields = ["id", "name"]


class ProfileSerializer(serializers.ModelSerializer):
    educations = EducationSerializer(many=True, read_only=True)
    experiences = ExperienceSerializer(many=True, read_only=True)
    languages = LanguageSerializer(many=True, read_only=True)
    interests = AcademicInterestSerializer(many=True, read_only=True)

    class Meta:
        model = Profile
        fields = [
            "id",
            "title",
            "full_name",
            "short_bio",
            "bio",
            "office",
            "email",
            "phone",
            "website",
            "photo",
            "google_scholar_url",
            "researchgate_url",
            "linkedin_url",
            "orcid",
            "educations",
            "experiences",
            "languages",
            "interests",
        ]
