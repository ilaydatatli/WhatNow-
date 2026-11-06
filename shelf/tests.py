from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import Item, ShelfEntry

PASSWORD = "kahve-fincani-42"


def item_data(**overrides):
    data = {
        "kind": "book",
        "title": "Dune",
        "creator": "Frank Herbert",
        "year": "1965",
        "genre": "bilim kurgu",
        "status": "want",
    }
    data.update(overrides)
    return data


class ShelfTestCase(TestCase):
    def setUp(self):
        self.ayse = User.objects.create_user(username="ayse", email="ayse@example.com", password=PASSWORD)
        self.mert = User.objects.create_user(username="mert", email="mert@example.com", password=PASSWORD)

    def login(self, user):
        self.client.login(username=user.email, password=PASSWORD)


class ItemCreateTests(ShelfTestCase):
    def test_login_required(self):
        url = reverse("shelf:item_create")
        response = self.client.get(url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={url}")
        self.client.post(url, item_data())
        self.assertEqual(Item.objects.count(), 0)

    def test_create_adds_item_to_own_shelf(self):
        self.login(self.ayse)
        response = self.client.post(reverse("shelf:item_create"), item_data(status="current"))
        item = Item.objects.get()
        self.assertRedirects(response, item.get_absolute_url())
        self.assertEqual(item.added_by, self.ayse)
        self.assertEqual(self.ayse.shelf.get().status, ShelfEntry.Status.CURRENT)

    def test_duplicate_is_case_insensitive_and_redirects_to_existing(self):
        self.login(self.ayse)
        self.client.post(reverse("shelf:item_create"), item_data(title="Dune"))
        item = Item.objects.get()

        self.login(self.mert)
        for title in ("dune", "  DUNE "):
            response = self.client.post(reverse("shelf:item_create"), item_data(title=title))
            self.assertRedirects(response, item.get_absolute_url())
        self.assertEqual(Item.objects.count(), 1)
        self.assertTrue(self.mert.shelf.filter(item=item).exists())

    def test_duplicate_shows_warning_on_item_page(self):
        self.login(self.ayse)
        self.client.post(reverse("shelf:item_create"), item_data())
        response = self.client.post(
            reverse("shelf:item_create"), item_data(title="DUNE", genre="psikolojik gerilim"), follow=True
        )
        self.assertContains(response, "zaten rafında")
        self.assertEqual(Item.objects.get().genre, "bilim kurgu")

    def test_same_title_different_year_or_kind_is_allowed(self):
        self.login(self.ayse)
        self.client.post(reverse("shelf:item_create"), item_data())
        self.client.post(reverse("shelf:item_create"), item_data(year="1984"))
        self.client.post(reverse("shelf:item_create"), item_data(kind="film", year="1984"))
        self.assertEqual(Item.objects.count(), 3)

    def test_invalid_year_rejected(self):
        self.login(self.ayse)
        for year in ("999", str(date.today().year + 2), ""):
            response = self.client.post(reverse("shelf:item_create"), item_data(year=year))
            self.assertEqual(response.status_code, 200, year)
        self.assertEqual(Item.objects.count(), 0)


class ShelfEntryTests(ShelfTestCase):
    def setUp(self):
        super().setUp()
        self.item = Item.objects.create(kind="film", title="Amélie", creator="Jean-Pierre Jeunet", year=2001)

    def test_add_to_shelf_twice_keeps_one_entry(self):
        self.login(self.mert)
        url = reverse("shelf:item_add", args=[self.item.pk])
        self.client.post(url)
        response = self.client.post(url, {"next": "/"})
        self.assertRedirects(response, "/")
        self.assertEqual(ShelfEntry.objects.filter(user=self.mert, item=self.item).count(), 1)

    def test_add_to_shelf_requires_login_and_post(self):
        url = reverse("shelf:item_add", args=[self.item.pk])
        self.client.post(url)
        self.assertEqual(ShelfEntry.objects.count(), 0)
        self.login(self.mert)
        self.assertEqual(self.client.get(url).status_code, 405)

    def test_unsafe_next_is_ignored(self):
        self.login(self.mert)
        response = self.client.post(
            reverse("shelf:item_add", args=[self.item.pk]), {"next": "https://evil.example.com/"}
        )
        self.assertRedirects(response, self.item.get_absolute_url())

    def test_rating_and_review_only_kept_when_done(self):
        entry = ShelfEntry.objects.create(user=self.ayse, item=self.item)
        self.login(self.ayse)
        url = reverse("shelf:entry_edit", args=[entry.pk])

        self.client.post(url, {"status": "done", "rating": "4", "review": "Çok tatlı.", "finished_at": ""})
        entry.refresh_from_db()
        self.assertEqual((entry.rating, entry.review, entry.finished_at), (4, "Çok tatlı.", date.today()))

        self.client.post(url, {"status": "want", "rating": "4", "review": "Çok tatlı."})
        entry.refresh_from_db()
        self.assertEqual((entry.rating, entry.review, entry.finished_at), (None, "", None))

    def test_finished_at_can_be_set_but_not_in_future(self):
        entry = ShelfEntry.objects.create(user=self.ayse, item=self.item)
        self.login(self.ayse)
        url = reverse("shelf:entry_edit", args=[entry.pk])
        last_week = date.today() - timedelta(days=7)

        self.client.post(url, {"status": "done", "finished_at": last_week.isoformat()})
        entry.refresh_from_db()
        self.assertEqual(entry.finished_at, last_week)

        tomorrow = date.today() + timedelta(days=1)
        response = self.client.post(url, {"status": "done", "finished_at": tomorrow.isoformat()})
        self.assertContains(response, "Bitirme tarihi gelecekte olamaz.")
        entry.refresh_from_db()
        self.assertEqual(entry.finished_at, last_week)

    def test_rating_out_of_range_rejected(self):
        entry = ShelfEntry.objects.create(user=self.ayse, item=self.item)
        self.login(self.ayse)
        response = self.client.post(reverse("shelf:entry_edit", args=[entry.pk]), {"status": "done", "rating": "6"})
        self.assertEqual(response.status_code, 200)
        entry.refresh_from_db()
        self.assertEqual(entry.status, ShelfEntry.Status.WANT)

    def test_cannot_edit_or_remove_someone_elses_entry(self):
        entry = ShelfEntry.objects.create(user=self.ayse, item=self.item)
        self.login(self.mert)
        self.assertEqual(self.client.get(reverse("shelf:entry_edit", args=[entry.pk])).status_code, 404)
        response = self.client.post(reverse("shelf:entry_edit", args=[entry.pk]), {"status": "done"})
        self.assertEqual(response.status_code, 404)
        response = self.client.post(reverse("shelf:entry_remove", args=[entry.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(ShelfEntry.objects.filter(pk=entry.pk, status="want").exists())

    def test_remove_keeps_item(self):
        entry = ShelfEntry.objects.create(user=self.ayse, item=self.item)
        self.login(self.ayse)
        response = self.client.post(reverse("shelf:entry_remove", args=[entry.pk]))
        self.assertRedirects(response, reverse("accounts:profile"))
        self.assertFalse(ShelfEntry.objects.exists())
        self.assertTrue(Item.objects.filter(pk=self.item.pk).exists())


class PageTests(ShelfTestCase):
    def test_guest_can_browse(self):
        item = Item.objects.create(kind="book", title="Kürk Mantolu Madonna", creator="Sabahattin Ali", year=1943)
        ShelfEntry.objects.create(user=self.ayse, item=item, status="done", rating=5)
        self.assertContains(self.client.get("/"), "Kürk Mantolu Madonna")
        response = self.client.get(item.get_absolute_url())
        self.assertContains(response, "Sabahattin Ali")
        self.assertContains(response, "Rafına eklemek için giriş yap")

    def test_profile_groups_shelf_by_status(self):
        book = Item.objects.create(kind="book", title="Tutunamayanlar", creator="Oğuz Atay", year=1972)
        film = Item.objects.create(kind="film", title="Babam ve Oğlum", creator="Çağan Irmak", year=2005)
        ShelfEntry.objects.create(user=self.ayse, item=book, status="current")
        ShelfEntry.objects.create(user=self.ayse, item=film, status="done", rating=5, review="Ağladım.")
        self.login(self.ayse)
        response = self.client.get(reverse("accounts:profile"))
        sections = {status: entries for status, _, entries in response.context["sections"]}
        self.assertEqual([e.item for e in sections["current"]], [book])
        self.assertEqual([e.item for e in sections["done"]], [film])
        self.assertEqual(sections["want"], [])
        self.assertContains(response, "Ağladım.")


class ItemSearchTests(ShelfTestCase):
    def setUp(self):
        super().setUp()
        self.dune = Item.objects.create(kind="book", title="Dune", creator="Frank Herbert", year=1965)
        Item.objects.create(kind="film", title="Dune", creator="Denis Villeneuve", year=2021)
        Item.objects.create(kind="book", title="Dünyanın Merkezine Yolculuk", creator="Jules Verne", year=1864)

    def search(self, q):
        return self.client.get(reverse("shelf:item_search"), {"q": q}).json()["results"]

    def test_needs_three_characters(self):
        self.assertEqual(self.search("Du"), [])
        self.assertEqual(self.search("  du  "), [])

    def test_matches_part_of_title_case_insensitively(self):
        results = self.search("UNE")
        self.assertEqual([(r["title"], r["year"]) for r in results], [("Dune", 1965), ("Dune", 2021)])
        self.assertEqual(results[0]["kind"], "Kitap")
        self.assertEqual(results[0]["add_url"], reverse("shelf:item_add", args=[self.dune.pk]))

    def test_add_from_suggestion_uses_chosen_status(self):
        self.login(self.mert)
        url = reverse("shelf:item_add", args=[self.dune.pk])
        self.client.post(url, {"status": "current"})
        self.assertEqual(self.mert.shelf.get(item=self.dune).status, ShelfEntry.Status.CURRENT)

    def test_add_with_unknown_status_falls_back_to_want(self):
        self.login(self.mert)
        self.client.post(reverse("shelf:item_add", args=[self.dune.pk]), {"status": "hacked"})
        self.assertEqual(self.mert.shelf.get(item=self.dune).status, ShelfEntry.Status.WANT)
