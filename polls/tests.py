from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import Option, Poll, Vote


def make_poll(author, options=("Makarna", "Pilav")):
    poll = Poll.objects.create(author=author, question="Bugün ne pişirsem?")
    for index, text in enumerate(options):
        Option.objects.create(poll=poll, text=text, order=index)
    return poll


class PollCreateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ayse", email="ayse@example.com", password="kahve-fincani-42"
        )
        self.url = reverse("polls:create")

    def post(self, options, question="Makarna mı pilav mı?"):
        return self.client.post(self.url, {"question": question, "options": list(options)})

    def test_guest_is_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")

        self.post(["A", "B"])
        self.assertEqual(Poll.objects.count(), 0)

    def test_option_count_limits(self):
        self.client.force_login(self.user)

        for options in (["Tek"], ["1", "2", "3", "4", "5", "6"]):
            response = self.post(options)
            self.assertContains(response, "en az 2, en fazla 5")
        self.assertEqual(Poll.objects.count(), 0)

        for options in (["A", "B"], ["1", "2", "3", "4", "5"]):
            response = self.post(options)
            poll = Poll.objects.latest("created_at")
            self.assertRedirects(response, reverse("polls:detail", args=[poll.pk]))
            self.assertEqual(poll.options.count(), len(options))

    def test_empty_and_duplicate_options_rejected(self):
        self.client.force_login(self.user)
        self.assertContains(self.post(["Makarna", "  "]), "boş bırakılamaz")
        self.assertContains(self.post(["Makarna", "MAKARNA "]), "iki kez")
        self.assertEqual(Poll.objects.count(), 0)


class VoteTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ayse", email="ayse@example.com", password="kahve-fincani-42"
        )
        self.poll = make_poll(self.user)
        self.makarna, self.pilav = self.poll.options.all()
        self.vote_url = reverse("polls:vote", args=[self.poll.pk])
        self.detail_url = reverse("polls:detail", args=[self.poll.pk])

    def test_guest_can_vote_once(self):
        self.client.get(self.detail_url)  # receives voter_token cookie
        self.client.post(self.vote_url, {"option": self.makarna.pk})
        self.client.post(self.vote_url, {"option": self.pilav.pk})

        self.assertEqual(Vote.objects.count(), 1)
        vote = Vote.objects.get()
        self.assertIsNone(vote.user)
        self.assertEqual(vote.option, self.makarna)

        response = self.client.get(self.detail_url)
        self.assertContains(response, "Sonuçlar")
        self.assertContains(response, "1 misafir")

    def test_user_can_vote_once_across_browsers(self):
        self.client.force_login(self.user)
        self.client.post(self.vote_url, {"option": self.makarna.pk})

        other_browser = self.client_class()
        other_browser.force_login(self.user)
        other_browser.post(self.vote_url, {"option": self.pilav.pk})

        self.assertEqual(Vote.objects.filter(user=self.user).count(), 1)
        self.assertContains(other_browser.get(self.detail_url), "ayse")

    def test_option_from_another_poll_rejected(self):
        other_poll = make_poll(self.user, options=("Çay", "Kahve"))
        self.client.post(self.vote_url, {"option": other_poll.options.first().pk})
        self.assertEqual(Vote.objects.count(), 0)

    def test_results_hidden_before_voting(self):
        response = self.client.get(self.detail_url)
        self.assertContains(response, "Oy ver")
        self.assertNotContains(response, "Sonuçlar")


class PollListTests(TestCase):
    def test_empty_state(self):
        self.assertContains(self.client.get("/"), "Henüz anket yok")

    def test_lists_polls_with_vote_counts(self):
        user = User.objects.create_user(username="ayse", email="a@example.com", password="x")
        poll = make_poll(user)
        Vote.objects.create(poll=poll, option=poll.options.first(), voter_token="t1")
        response = self.client.get("/")
        self.assertContains(response, poll.question)
        self.assertContains(response, "1 oy")


class PollDeleteTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="ayse", email="ayse@example.com", password="kahve-fincani-42"
        )
        self.other = User.objects.create_user(
            username="mehmet", email="mehmet@example.com", password="cay-bardagi-42"
        )
        self.poll = make_poll(self.owner)
        self.url = reverse("polls:delete", args=[self.poll.pk])

    def test_get_shows_confirmation_without_deleting(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertContains(response, "emin misin")
        self.assertTrue(Poll.objects.filter(pk=self.poll.pk).exists())

    def test_owner_can_delete(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse("accounts:profile"))
        self.assertFalse(Poll.objects.filter(pk=self.poll.pk).exists())

    def test_other_user_cannot_delete(self):
        self.client.force_login(self.other)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Poll.objects.filter(pk=self.poll.pk).exists())
