document.addEventListener("DOMContentLoaded", function () {
    const summary = document.querySelector("[data-form-error-summary]");
    if (!summary) return;

    const form = summary.closest("form");
    const firstInvalid = form && form.querySelector(".is-invalid, [aria-invalid='true']");
    const target = firstInvalid || summary;
    target.scrollIntoView({ behavior: "smooth", block: "center" });
    target.focus({ preventScroll: true });
});
