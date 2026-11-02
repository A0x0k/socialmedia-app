from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Comment, Post


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['id', 'content', 'created_at', 'author']
        read_only_fields = ['author']

class PostSerializer(serializers.ModelSerializer):
    comments = CommentSerializer(many=True, read_only=True)
    reactions_count = serializers.SerializerMethodField()
    author = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Post
        fields = ['id', 'content', 'image', 'created_at', 'author', 'comments', 'reactions_count']

    @extend_schema_field(int)
    def get_reactions_count(self, obj):
        return obj.reactions.count()
