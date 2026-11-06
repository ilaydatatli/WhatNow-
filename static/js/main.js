// Shelf entry form: show rating, review and finish date only when the status is "done".
// Convenience only — the server ignores these fields for other statuses anyway.
document.querySelectorAll("[data-entry-form]").forEach((form) => {
  const doneOnly = ["finished_at", "rating", "review"]
    .map((name) => form.querySelector(`[name="${name}"]`))
    .filter(Boolean)
    .map((field) => field.closest("p"));

  function refresh() {
    const status = form.querySelector('[name="status"]:checked');
    const isDone = status && status.value === "done";
    doneOnly.forEach((row) => row.classList.toggle("is-hidden", !isDone));
  }

  form.addEventListener("change", refresh);
  refresh();
});

// Add form: after 3 letters, suggest items that already exist so people add those
// instead of creating near-duplicates. Convenience only — the server still blocks exact duplicates.
document.querySelectorAll("[data-item-search]").forEach((form) => {
  const input = form.querySelector('[name="title"]');
  if (!input) return;

  const box = document.createElement("div");
  box.className = "suggestions is-hidden";
  box.setAttribute("aria-live", "polite");
  input.insertAdjacentElement("afterend", box);

  let timer;
  let controller;

  function addToShelf(addUrl) {
    const status = form.querySelector('[name="status"]');
    const post = document.createElement("form");
    post.method = "post";
    post.action = addUrl;
    [
      ["csrfmiddlewaretoken", form.querySelector('[name="csrfmiddlewaretoken"]').value],
      ["status", status ? status.value : "want"],
    ].forEach(([name, value]) => {
      const field = document.createElement("input");
      field.type = "hidden";
      field.name = name;
      field.value = value;
      post.appendChild(field);
    });
    document.body.appendChild(post);
    post.submit();
  }

  function hide() {
    box.replaceChildren();
    box.classList.add("is-hidden");
  }

  function render(results) {
    box.replaceChildren();
    box.classList.remove("is-hidden");
    if (!results.length) {
      const empty = document.createElement("p");
      empty.className = "suggestions-title";
      empty.textContent = "Kayıtlı eşleşme yok — bilgileri doldurup yeni olarak ekleyebilirsin.";
      box.appendChild(empty);
      return;
    }

    const heading = document.createElement("p");
    heading.className = "suggestions-title";
    heading.textContent = "Bunu mu arıyorsun? Zaten kayıtlı:";
    box.appendChild(heading);

    const list = document.createElement("ul");
    results.forEach((item) => {
      const row = document.createElement("li");

      const info = document.createElement("a");
      info.href = item.url;
      info.target = "_blank";
      info.textContent = item.title;
      const meta = document.createElement("span");
      meta.className = "suggestion-meta";
      meta.textContent = ` ${item.kind} · ${item.creator} · ${item.year}`;

      const text = document.createElement("span");
      text.append(info, meta);

      const button = document.createElement("button");
      button.type = "button";
      button.className = "btn btn-ghost btn-small";
      button.textContent = "Rafıma ekle";
      button.addEventListener("click", () => addToShelf(item.add_url));

      row.append(text, button);
      list.appendChild(row);
    });
    box.appendChild(list);
  }

  input.addEventListener("input", () => {
    clearTimeout(timer);
    const query = input.value.trim();
    if (query.length < 3) {
      hide();
      return;
    }
    timer = setTimeout(async () => {
      if (controller) controller.abort();
      controller = new AbortController();
      try {
        const url = `${form.dataset.itemSearch}?q=${encodeURIComponent(query)}`;
        const response = await fetch(url, { signal: controller.signal });
        if (response.ok) render((await response.json()).results);
      } catch (error) {
        if (error.name !== "AbortError") hide();
      }
    }, 250);
  });
});
