from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import IsAuthenticated

from forum_app.models import Comment, Post

from .permissions import IsOwnerOrReadOnly
from .serializers import CommentSerializer, PostSerializer


class PostListCreateView(ListCreateAPIView):
    """List posts or create a post as the authenticated user."""

    queryset = Post.objects.order_by("pk")
    serializer_class = PostSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class PostDetailView(RetrieveUpdateDestroyAPIView):
    """Retrieve a post or let its author or staff change or delete it."""

    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)


class CommentListCreateView(ListCreateAPIView):
    """List comments or create a comment as the authenticated user."""

    queryset = Comment.objects.order_by("pk")
    serializer_class = CommentSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class CommentDetailView(RetrieveUpdateDestroyAPIView):
    """Retrieve a comment or let its author or staff change or delete it."""

    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)
