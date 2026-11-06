"""Mini quiz built from the catalog: "Who wrote X?" or "Which year did X come out?"."""
import random

from .models import Item

OPTION_COUNT = 3


def _random_item():
    count = Item.objects.count()
    if not count:
        return None
    return Item.objects.all()[random.randrange(count)]


def _creator_question(item):
    """Needs two other creators of the same kind; returns None otherwise."""
    others = list(
        Item.objects.filter(kind=item.kind)
        .exclude(creator__iexact=item.creator)
        .values_list("creator", flat=True)
        .distinct()[:50]
    )
    # Different spellings of the same name must not appear twice.
    unique = list({name.casefold(): name for name in others}.values())
    if len(unique) < OPTION_COUNT - 1:
        return None
    if item.kind == Item.Kind.BOOK:
        question = f"“{item.title}” kitabını kim yazdı?"
    else:
        question = f"“{item.title}” filmini kim yönetti?"
    return question, item.creator, random.sample(unique, OPTION_COUNT - 1)


def _year_question(item):
    wrong = set()
    while len(wrong) < OPTION_COUNT - 1:
        year = item.year + random.choice([-1, 1]) * random.randint(1, 12)
        if year != item.year:
            wrong.add(year)
    if item.kind == Item.Kind.BOOK:
        question = f"“{item.title}” kitabı hangi yıl yayımlandı?"
    else:
        question = f"“{item.title}” filmi hangi yıl vizyona girdi?"
    return question, str(item.year), [str(year) for year in wrong]


def make_question():
    item = _random_item()
    if item is None:
        return None
    built = None
    if random.random() < 0.6:
        built = _creator_question(item)
    question, answer, wrong = built or _year_question(item)
    options = [answer, *wrong]
    random.shuffle(options)
    return {
        "question": question,
        "options": options,
        "answer": answer,
        "item_title": item.title,
        "item_url": item.get_absolute_url(),
    }
