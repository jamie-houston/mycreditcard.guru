document.addEventListener("DOMContentLoaded", function () {
    // Auto-generate system name from display name
    const displayNameInput = document.getElementById("display_name");
    const nameInput = document.getElementById("name");

    if (displayNameInput && nameInput) {
        displayNameInput.addEventListener("input", function () {
            if (!nameInput.value || nameInput.value === nameInput.dataset.generated) {
                const systemName = this.value
                    .toLowerCase()
                    .replace(/[^a-z0-9\s]/g, "") // Remove special chars
                    .replace(/\s+/g, "_") // Replace spaces with underscores
                    .replace(/_{2,}/g, "_") // Remove multiple underscores
                    .replace(/^_|_$/g, ""); // Remove leading/trailing underscores

                nameInput.value = systemName;
                nameInput.dataset.generated = systemName;
            }
        });
    }

    // Icon preview update
    const iconInput = document.getElementById("icon");
    const iconPreview = document.getElementById("icon-preview");

    if (iconInput && iconPreview) {
        iconInput.addEventListener("input", function () {
            iconPreview.className = this.value || "fas fa-tag";
        });
    }

    // Icon selection buttons
    document.querySelectorAll(".icon-btn").forEach((button) => {
        button.addEventListener("click", function () {
            const iconClass = this.dataset.icon;
            if (iconInput) iconInput.value = iconClass;
            if (iconPreview) iconPreview.className = iconClass;
        });
    });
}); 