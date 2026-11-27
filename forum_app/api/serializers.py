from rest_framework import serializers

from forum_app.models import Comment, Post


class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ("id", "title", "content", "author", "created_at")
        read_only_fields = ("id", "author", "created_at")


class CommentSerializer(serializers.ModelSerializer):
    """Accept a parent post on creation and preserve it on update."""

    class Meta:
        model = Comment
        fields = ("id", "post", "text", "author", "created_at")
        read_only_fields = ("id", "author", "created_at")
        extra_kwargs = {"post": {"required": False}}

    def validate_post(self, post):
        if self.instance and post.pk != self.instance.post_id:
            raise serializers.ValidationError(
                "A comment cannot be moved to another post."
            )
        return post

    def validate(self, attrs):
        if self.instance is None and "post" not in attrs:
            raise serializers.ValidationError(
                {"post": "This field is required."}
            )
        return attrs
