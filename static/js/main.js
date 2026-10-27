// Poll creation form: add/remove option inputs (convenience only; the server validates).
document.querySelectorAll("[data-options]").forEach((fieldset) => {
  const min = Number(fieldset.dataset.min);
  const max = Number(fieldset.dataset.max);
  const list = fieldset.querySelector("[data-option-list]");
  const addButton = fieldset.querySelector("[data-add-option]");

  const rows = () => list.querySelectorAll("[data-option-row]");

  function refresh() {
    const count = rows().length;
    addButton.disabled = count >= max;
    list.querySelectorAll("[data-remove-option]").forEach((button) => {
      button.disabled = count <= min;
    });
  }

  addButton.addEventListener("click", () => {
    if (rows().length >= max) return;
    const row = rows()[0].cloneNode(true);
    const input = row.querySelector("input");
    input.value = "";
    list.appendChild(row);
    input.focus();
    refresh();
  });

  list.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove-option]");
    if (!button || rows().length <= min) return;
    button.closest("[data-option-row]").remove();
    refresh();
  });

  refresh();
});
