document.querySelectorAll("[data-password-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
        const input = document.getElementById(button.dataset.target);

        if (!input) {
            return;
        }

        const shouldShow = input.type === "password";
        const fieldLabel = button.dataset.label || "password";
        input.type = shouldShow ? "text" : "password";
        button.setAttribute("aria-pressed", String(shouldShow));
        button.setAttribute(
            "aria-label",
            `${shouldShow ? "Hide" : "Show"} ${fieldLabel}`,
        );

        const icon = button.querySelector("i");
        if (icon) {
            icon.classList.toggle("bi-eye", !shouldShow);
            icon.classList.toggle("bi-eye-slash", shouldShow);
        }
    });
});
