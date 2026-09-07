from rest_framework import serializers


class AIRequestSerializer(serializers.Serializer):
    text = serializers.CharField(
        required=True,
        allow_blank=False,
    )


class AIResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = serializers.JSONField()
