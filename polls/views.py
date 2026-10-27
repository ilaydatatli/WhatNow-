from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import PollForm
from .models import MAX_OPTIONS, MIN_OPTIONS, Option, Poll, Vote

POLLS_PER_PAGE = 20


def _find_vote(request, poll):
    """Return this visitor's vote on `poll` (by user or voter_token cookie), if any."""
    who = Q(voter_token=request.voter_token)
    if request.user.is_authenticated:
        who |= Q(user=request.user)
    return Vote.objects.filter(who, poll=poll).first()


def poll_list(request):
    polls = Poll.objects.select_related("author").annotate(vote_count=Count("votes"))
    page = Paginator(polls, POLLS_PER_PAGE).get_page(request.GET.get("page"))
    return render(request, "polls/list.html", {"page": page})


def poll_detail(request, pk):
    poll = get_object_or_404(Poll.objects.select_related("author"), pk=pk)
    options = list(
        poll.options.prefetch_related(
            Prefetch("votes", queryset=Vote.objects.select_related("user").order_by("created_at"))
        )
    )
    my_vote = _find_vote(request, poll)

    results = []
    if my_vote:
        total = sum(len(option.votes.all()) for option in options)
        top = max(len(option.votes.all()) for option in options)
        for option in options:
            votes = option.votes.all()
            count = len(votes)
            results.append({
                "option": option,
                "count": count,
                "percent": round(count * 100 / total) if total else 0,
                "is_winner": count == top and count > 0,
                "is_mine": option.pk == my_vote.option_id,
                "usernames": [vote.user.username for vote in votes if vote.user],
                "guest_count": sum(1 for vote in votes if not vote.user),
            })
    else:
        total = None

    return render(request, "polls/detail.html", {
        "poll": poll,
        "options": options,
        "results": results,
        "total": total,
        "has_voted": my_vote is not None,
    })


@require_POST
def vote(request, pk):
    poll = get_object_or_404(Poll, pk=pk)

    if _find_vote(request, poll):
        messages.info(request, "Bu ankete zaten oy verdin.")
        return redirect("polls:detail", pk=poll.pk)

    # Looking the option up through the poll guarantees option.poll == poll.
    option = Option.objects.filter(poll=poll, pk=request.POST.get("option") or 0).first()
    if option is None:
        messages.error(request, "Lütfen bir seçenek seç.")
        return redirect("polls:detail", pk=poll.pk)

    try:
        with transaction.atomic():
            Vote.objects.create(
                poll=poll,
                option=option,
                user=request.user if request.user.is_authenticated else None,
                voter_token=request.voter_token,
            )
    except IntegrityError:
        # A parallel request already stored this visitor's vote.
        messages.info(request, "Bu ankete zaten oy verdin.")
    else:
        messages.success(request, "Oyun kaydedildi, teşekkürler!")
    return redirect("polls:detail", pk=poll.pk)


@login_required
def poll_create(request):
    if request.method == "POST":
        form = PollForm(request.POST)
        if form.is_valid():
            poll = form.save(author=request.user)
            messages.success(request, "Anketin yayında!")
            return redirect("polls:detail", pk=poll.pk)
    else:
        form = PollForm()

    return render(request, "polls/create.html", {
        "form": form,
        "min_options": MIN_OPTIONS,
        "max_options": MAX_OPTIONS,
    })
