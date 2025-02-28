from django.contrib.auth.models import Permission
from django.http import HttpRequest, HttpResponse
from django.test import TestCase
from django.urls import reverse

from wagtail.snippets.bulk_actions.delete import DeleteBulkAction
from wagtail.test.snippets.models import StandardSnippet
from wagtail.test.utils import WagtailTestUtils


class TestSnippetDeleteView(WagtailTestUtils, TestCase):
    def setUp(self):
        self.snippet_model = StandardSnippet

        # create a set of test snippets
        self.test_snippets = [
            self.snippet_model.objects.create(
                text=f"Title-{i}",
            )
            for i in range(1, 6)
        ]

        self.user = self.login()
        self.url = (
            reverse(
                "wagtail_bulk_action",
                args=(
                    self.snippet_model._meta.app_label,
                    self.snippet_model._meta.model_name,
                    "delete",
                ),
            )
            + "?"
        )
        for snippet in self.test_snippets:
            self.url += f"id={snippet.pk}&"

    def test_simple(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "wagtailsnippets/bulk_actions/confirm_bulk_delete.html"
        )

    def test_bulk_delete(self):
        response = self.client.post(self.url)

        # Should redirect back to index
        self.assertEqual(response.status_code, 302)

        # Check that the users were deleted
        for snippet in self.test_snippets:
            self.assertFalse(self.snippet_model.objects.filter(pk=snippet.pk).exists())

    def test_delete_with_limited_permissions(self):
        self.user.is_superuser = False
        self.user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="wagtailadmin", codename="access_admin"
            )
        )
        self.user.save()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        html = response.content.decode()
        self.assertInHTML(
            "<p>You don't have permission to delete these standard snippets</p>",
            html,
        )

        for snippet in self.test_snippets:
            self.assertInHTML(f"<li>{snippet.text}</li>", html)

        response = self.client.post(self.url)
        # User should be redirected back to the index
        self.assertEqual(response.status_code, 302)

        # Snippets should not be deleted
        for snippet in self.test_snippets:
            self.assertTrue(self.snippet_model.objects.filter(pk=snippet.pk).exists())

    def test_before_bulk_action_hook_get(self):
        with self.register_hook(
            "before_bulk_action", lambda *args: HttpResponse("Overridden!")
        ):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        # The hook was not called
        self.assertNotEqual(response.content, b"Overridden!")

        # The instances were not deleted
        self.assertQuerysetEqual(
            self.snippet_model.objects.filter(
                pk__in=[snippet.pk for snippet in self.test_snippets]
            ),
            self.test_snippets,
            ordered=False,
        )

    def test_before_bulk_action_hook_post(self):
        def hook_func(request, action_type, instances, action_class_instance):
            self.assertIsInstance(request, HttpRequest)
            self.assertEqual(action_type, "delete")
            self.assertQuerysetEqual(instances, self.test_snippets)
            self.assertIsInstance(action_class_instance, DeleteBulkAction)
            return HttpResponse("Overridden!")

        with self.register_hook("before_bulk_action", hook_func):
            response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Overridden!")

        # Request intercepted before the snippets were deleted
        self.assertQuerysetEqual(
            self.snippet_model.objects.filter(
                pk__in=[snippet.pk for snippet in self.test_snippets]
            ),
            self.test_snippets,
            ordered=False,
        )

    def test_after_bulk_action_hook(self):
        def hook_func(request, action_type, instances, action_class_instance):
            self.assertIsInstance(request, HttpRequest)
            self.assertEqual(action_type, "delete")
            self.assertQuerysetEqual(instances, self.test_snippets)
            self.assertIsInstance(action_class_instance, DeleteBulkAction)
            return HttpResponse("Overridden!")

        with self.register_hook("after_bulk_action", hook_func):
            response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Overridden!")

        # Request intercepted after the snippets were deleted
        self.assertFalse(
            self.snippet_model.objects.filter(
                pk__in=[snippet.pk for snippet in self.test_snippets]
            ).exists()
        )

    # Also tests that the {before,after}_delete_snippet hooks are called.
    # These hooks have existed since before bulk actions were introduced,
    # so we need to make sure they still work.

    def test_before_delete_snippet_hook_get(self):
        def hook_func(request, instances):
            self.assertIsInstance(request, HttpRequest)
            self.assertQuerysetEqual(instances, self.test_snippets)
            return HttpResponse("Overridden!")

        with self.register_hook("before_delete_snippet", hook_func):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Overridden!")

        # Request intercepted before the snippets were deleted
        self.assertQuerysetEqual(
            self.snippet_model.objects.filter(
                pk__in=[snippet.pk for snippet in self.test_snippets]
            ),
            self.test_snippets,
            ordered=False,
        )

    def test_before_delete_snippet_hook_post(self):
        def hook_func(request, instances):
            self.assertIsInstance(request, HttpRequest)
            self.assertQuerysetEqual(instances, self.test_snippets)
            return HttpResponse("Overridden!")

        with self.register_hook("before_delete_snippet", hook_func):
            response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Overridden!")

        # Request intercepted before the snippets were deleted
        self.assertQuerysetEqual(
            self.snippet_model.objects.filter(
                pk__in=[snippet.pk for snippet in self.test_snippets]
            ),
            self.test_snippets,
            ordered=False,
        )

    def test_after_delete_snippet_hook(self):
        def hook_func(request, instances):
            self.assertIsInstance(request, HttpRequest)
            self.assertQuerysetEqual(instances, self.test_snippets)
            return HttpResponse("Overridden!")

        with self.register_hook("after_delete_snippet", hook_func):
            response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Overridden!")

        # Request intercepted after the snippets were deleted
        self.assertFalse(
            self.snippet_model.objects.filter(
                pk__in=[snippet.pk for snippet in self.test_snippets]
            ).exists()
        )
