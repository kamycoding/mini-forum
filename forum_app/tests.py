from django.contrib import admin
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import Comment, Post

User = get_user_model()


class ForumAPITestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user(username="thread_author")
        cls.reader = User.objects.create_user(username="thread_reader")
        cls.author_token = Token.objects.create(user=cls.author)
        cls.reader_token = Token.objects.create(user=cls.reader)
        cls.post = Post.objects.create(
            title="First thread", content="Hello, forum.", author=cls.author
        )
        cls.comment = Comment.objects.create(
            post=cls.post, text="First reply", author=cls.reader
        )

    def authenticate(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")


class ForumAccessTests(ForumAPITestCase):
    def test_anonymous_access_is_rejected(self):
        urls = (
            reverse("post-list"),
            reverse("post-detail", args=[self.post.pk]),
            reverse("comment-list"),
            reverse("comment-detail", args=[self.comment.pk]),
        )
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(
                    response.status_code, status.HTTP_401_UNAUTHORIZED
                )

    def test_anonymous_creation_is_rejected(self):
        for name in ("post-list", "comment-list"):
            with self.subTest(route=name):
                response = self.client.post(reverse(name), {})
                self.assertEqual(
                    response.status_code, status.HTTP_401_UNAUTHORIZED
                )

    def test_invalid_token_is_rejected(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token invalid-test-token")
        response = self.client.get(reverse("post-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_models_are_registered(self):
        self.assertTrue(admin.site.is_registered(Post))
        self.assertTrue(admin.site.is_registered(Comment))


class StaffPermissionTests(ForumAPITestCase):
    def setUp(self):
        staff = User.objects.create_user(username="forum_staff", is_staff=True)
        self.authenticate(Token.objects.create(user=staff))
        self.post_url = reverse("post-detail", args=[self.post.pk])
        self.comment_url = reverse("comment-detail", args=[self.comment.pk])

    def test_staff_can_update_another_users_post(self):
        response = self.client.put(self.post_url, {
            "title": "Staff edit", "content": self.post.content,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, "Staff edit")
        self.assertEqual(self.post.author_id, self.author.pk)

    def test_staff_can_update_another_users_comment(self):
        response = self.client.put(self.comment_url, {"text": "Staff edit"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.text, "Staff edit")
        self.assertEqual(self.comment.author_id, self.reader.pk)

    def test_staff_can_delete_another_users_comment_and_post(self):
        for url in (self.comment_url, self.post_url):
            with self.subTest(url=url):
                response = self.client.delete(url)
                self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Comment.objects.filter(pk=self.comment.pk).exists())
        self.assertFalse(Post.objects.filter(pk=self.post.pk).exists())


class PostAPITests(ForumAPITestCase):
    def setUp(self):
        self.list_url = reverse("post-list")
        self.detail_url = reverse("post-detail", args=[self.post.pk])

    def test_create_post_assigns_author(self):
        """Use the token's user as author even if the body supplies one."""
        self.authenticate(self.reader_token)
        response = self.client.post(self.list_url, {
            "title": "Second thread",
            "content": "New discussion",
            "author": self.author.pk,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        post = Post.objects.get(pk=response.data["id"])
        self.assertEqual(post.author_id, self.reader.pk)
        self.assertEqual(response.data["author"], self.reader.pk)

    def test_list_posts(self):
        self.authenticate(self.reader_token)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [post["id"] for post in response.data], [self.post.pk]
        )

    def test_retrieve_post(self):
        self.authenticate(self.reader_token)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], self.post.title)

    def test_owner_can_update_post(self):
        self.authenticate(self.author_token)
        response = self.client.put(self.detail_url, {
            "title": "Edited", "content": "Updated thread",
            "id": self.post.pk + 100, "author": self.reader.pk,
            "created_at": "2000-01-01T00:00:00Z",
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        post = Post.objects.get(pk=self.post.pk)
        self.assertEqual(post.title, "Edited")
        self.assertEqual(post.author_id, self.author.pk)
        self.assertEqual(post.created_at, self.post.created_at)

    def test_owner_can_patch_post(self):
        self.authenticate(self.author_token)
        response = self.client.patch(self.detail_url, {"title": "Patch"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["content"], self.post.content)

    def test_owner_can_delete_post_and_cascade_comments(self):
        self.authenticate(self.author_token)
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Post.objects.filter(pk=self.post.pk).exists())
        self.assertFalse(Comment.objects.filter(pk=self.comment.pk).exists())

    def test_non_owner_cannot_update_or_delete_post(self):
        self.authenticate(self.reader_token)
        for method in (self.client.put, self.client.patch, self.client.delete):
            with self.subTest(method=method.__name__):
                response = method(self.detail_url, {"title": "Unauthorized"})
                self.assertEqual(
                    response.status_code, status.HTTP_403_FORBIDDEN
                )
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, "First thread")

    def test_missing_post_returns_404(self):
        self.authenticate(self.author_token)
        url = reverse("post-detail", args=[self.post.pk + 1])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_title_limit_is_enforced(self):
        self.authenticate(self.author_token)
        response = self.client.post(self.list_url, {
            "title": "a" * 201, "content": "Thread with a long title",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", response.data)


class CommentAPITests(ForumAPITestCase):
    def setUp(self):
        self.list_url = reverse("comment-list")
        self.detail_url = reverse("comment-detail", args=[self.comment.pk])

    def test_create_comment_assigns_post_and_author(self):
        self.authenticate(self.reader_token)
        response = self.client.post(self.list_url, {
            "post": self.post.pk,
            "text": "New reply",
            "author": self.author.pk,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        comment = Comment.objects.get(pk=response.data["id"])
        self.assertEqual(comment.post_id, self.post.pk)
        self.assertEqual(comment.author_id, self.reader.pk)

    def test_invalid_post_identifier_is_rejected(self):
        self.authenticate(self.reader_token)
        for post_id in (self.post.pk + 1, "unknown"):
            with self.subTest(post_id=post_id):
                response = self.client.post(
                    self.list_url, {"post": post_id, "text": "New reply"}
                )
                self.assertEqual(
                    response.status_code, status.HTTP_400_BAD_REQUEST
                )
                self.assertIn("post", response.data)
        self.assertEqual(Comment.objects.count(), 1)

    def test_post_identifier_is_required_on_create(self):
        self.authenticate(self.reader_token)
        response = self.client.post(self.list_url, {"text": "No parent"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("post", response.data)

    def test_non_owner_can_list_comments(self):
        self.authenticate(self.author_token)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["id"] for item in response.data], [self.comment.pk]
        )

    def test_non_owner_can_retrieve_comment(self):
        self.authenticate(self.author_token)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["text"], self.comment.text)

    def test_owner_can_update_comment_without_changing_author(self):
        self.authenticate(self.reader_token)
        response = self.client.put(self.detail_url, {
            "text": "Edited reply", "author": self.author.pk,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.text, "Edited reply")
        self.assertEqual(self.comment.author_id, self.reader.pk)
        self.assertEqual(self.comment.post_id, self.post.pk)

    def test_owner_can_patch_comment_with_same_post(self):
        self.authenticate(self.reader_token)
        response = self.client.patch(self.detail_url, {
            "post": self.post.pk, "text": "Partially updated reply",
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["text"], "Partially updated reply")

    def test_owner_cannot_move_comment(self):
        self.authenticate(self.reader_token)
        other = Post.objects.create(
            title="Other thread", content="Another topic", author=self.reader
        )
        for method in (self.client.put, self.client.patch):
            with self.subTest(method=method.__name__):
                response = method(
                    self.detail_url, {"post": other.pk, "text": "Move"}
                )
                self.assertEqual(
                    response.status_code, status.HTTP_400_BAD_REQUEST
                )
                self.assertIn("post", response.data)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.post_id, self.post.pk)

    def test_owner_can_delete_comment(self):
        self.authenticate(self.reader_token)
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Comment.objects.filter(pk=self.comment.pk).exists())
        self.assertTrue(Post.objects.filter(pk=self.post.pk).exists())

    def test_non_owner_cannot_update_or_delete_comment(self):
        """Owning the parent post does not grant write access to a comment."""
        self.authenticate(self.author_token)
        for method in (self.client.put, self.client.patch, self.client.delete):
            with self.subTest(method=method.__name__):
                response = method(self.detail_url, {"text": "Unauthorized"})
                self.assertEqual(
                    response.status_code, status.HTTP_403_FORBIDDEN
                )
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.text, "First reply")

    def test_missing_comment_returns_404(self):
        self.authenticate(self.reader_token)
        url = reverse("comment-detail", args=[self.comment.pk + 1])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
