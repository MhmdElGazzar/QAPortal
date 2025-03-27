from rest_framework import serializers

class HomePageSerializer(serializers.Serializer):
    title = serializers.CharField()
    message = serializers.CharField()

class AzureTaskSerializer(serializers.Serializer):
    title = serializers.CharField()
    description = serializers.CharField()
    activity = serializers.CharField(default="Testing")
    original_estimate = serializers.IntegerField(default=2)
    remaining_work = serializers.IntegerField(default=1)
    assigned_to = serializers.CharField()
    iteration_path = serializers.CharField()
    user_story_id = serializers.IntegerField()
