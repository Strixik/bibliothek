/* Mobiles Navigationsmenü */

const menuToggle = document.querySelector("[data-menu-toggle]");
const navigation = document.querySelector("[data-navigation]");

if (menuToggle && navigation) {
    menuToggle.addEventListener("click", () => {
        const isOpen = menuToggle.getAttribute("aria-expanded") === "true";

        menuToggle.setAttribute("aria-expanded", String(!isOpen));
        menuToggle.setAttribute(
            "aria-label",
            isOpen ? "Menü öffnen" : "Menü schließen"
        );
        navigation.classList.toggle("is-open", !isOpen);
    });

    navigation.addEventListener("click", (event) => {
        if (event.target.closest("a")) {
            menuToggle.setAttribute("aria-expanded", "false");
            menuToggle.setAttribute("aria-label", "Menü öffnen");
            navigation.classList.remove("is-open");
        }
    });
}


/* Hell-Dunkel-Modus */

const themeToggle = document.querySelector("[data-theme-toggle]");
const themeIcon = document.querySelector("[data-theme-icon]");
const root = document.documentElement;

function applyTheme(theme) {
    root.dataset.theme = theme;

    if (themeToggle && themeIcon) {
        const isDark = theme === "dark";
        themeIcon.textContent = isDark ? "☀" : "☾";
        themeToggle.setAttribute(
            "aria-label",
            isDark ? "Helles Design einschalten" : "Dunkles Design einschalten"
        );
    }

    const themeColor = document.querySelector('meta[name="theme-color"]');
    if (themeColor) {
        themeColor.setAttribute(
            "content",
            theme === "dark" ? "#171d1a" : "#f5f7f4"
        );
    }
}

let savedTheme = "light";

try {
    savedTheme = localStorage.getItem("library-theme") || "light";
} catch {
    savedTheme = "light";
}

applyTheme(savedTheme);

themeToggle?.addEventListener("click", () => {
    const nextTheme = root.dataset.theme === "dark" ? "light" : "dark";
    applyTheme(nextTheme);

    try {
        localStorage.setItem("library-theme", nextTheme);
    } catch {
        // Das Farbschema funktioniert auch ohne verfügbaren lokalen Speicher.
    }
});


/* Bestätigungsfenster zum Löschen */

document.addEventListener("click", (event) => {
    const openButton = event.target.closest("[data-open-delete]");
    const cancelButton = event.target.closest("[data-cancel-delete]");

    if (openButton) {
        const container = openButton.closest("[data-delete-control]");
        const dialog = container?.querySelector(".delete-dialog");
        dialog?.showModal();
    }

    if (cancelButton) {
        cancelButton.closest(".delete-dialog")?.close();
    }

    if (
        event.target instanceof HTMLDialogElement
        && event.target.classList.contains("delete-dialog")
    ) {
        event.target.close();
    }
});


/* Katalogsuche und Sortierung ohne vollständiges Neuladen */

let catalogController;
let searchTimer;

async function updateCatalog(form, updateHistory = true) {
    const catalog = document.querySelector("[data-library-content]");

    if (!catalog) {
        form.submit();
        return;
    }

    catalogController?.abort();
    catalogController = new AbortController();

    const formData = new FormData(form);
    const url = new URL(form.action, window.location.href);

    for (const [key, value] of formData.entries()) {
        if (value) {
            url.searchParams.set(key, value);
        } else {
            url.searchParams.delete(key);
        }
    }

    catalog.classList.add("is-loading");
    catalog.setAttribute("aria-busy", "true");

    try {
        const response = await fetch(url, {
            headers: {
                "X-Requested-With": "fetch",
            },
            signal: catalogController.signal,
        });

        if (!response.ok) {
            throw new Error("Der Katalog konnte nicht geladen werden.");
        }

        const page = await response.text();
        const parsedPage = new DOMParser().parseFromString(page, "text/html");
        const newCatalog = parsedPage.querySelector("[data-library-content]");

        if (!newCatalog) {
            throw new Error("Der Katalogbereich wurde nicht gefunden.");
        }

        catalog.innerHTML = newCatalog.innerHTML;

        if (updateHistory) {
            window.history.pushState({}, "", url);
        }

        const searchInput = document.querySelector("#search");
        searchInput?.focus({ preventScroll: true });
    } catch (error) {
        if (error.name !== "AbortError") {
            window.location.assign(url);
        }
    } finally {
        catalog.classList.remove("is-loading");
        catalog.removeAttribute("aria-busy");
    }
}

document.addEventListener("submit", (event) => {
    const form = event.target.closest("[data-catalog-form]");

    if (!form) {
        return;
    }

    event.preventDefault();
    updateCatalog(form);
});

document.addEventListener("change", (event) => {
    if (event.target.matches("#sort")) {
        event.target.form.requestSubmit();
    }
});

document.addEventListener("input", (event) => {
    if (!event.target.matches("#search")) {
        return;
    }

    clearTimeout(searchTimer);

    searchTimer = setTimeout(() => {
        event.target.form.requestSubmit();
    }, 450);
});

document.addEventListener("click", (event) => {
    const clearButton = event.target.closest("[data-clear-search]");

    if (!clearButton) {
        return;
    }

    const searchForm = clearButton.closest("form");
    const searchInput = searchForm?.querySelector("#search");

    if (searchForm && searchInput) {
        searchInput.value = "";
        searchForm.requestSubmit();
    }
});

window.addEventListener("popstate", () => {
    window.location.reload();
});


/* Flash-Nachrichten schließen */

document.addEventListener("click", (event) => {
    const closeButton = event.target.closest("[data-dismiss-alert]");

    if (closeButton) {
        closeButton.closest("[data-alert]")?.remove();
    }
});

document.querySelectorAll("[data-alert]").forEach((alert) => {
    setTimeout(() => {
        alert.classList.add("is-leaving");
        setTimeout(() => alert.remove(), 250);
    }, 6000);
});


/* Zeichenanzahl in Formularen anzeigen */

document.querySelectorAll("[data-character-count]").forEach((input) => {
    const field = input.closest(".field");

    if (!field || !input.maxLength) {
        return;
    }

    const counter = document.createElement("small");
    counter.className = "character-count";
    counter.setAttribute("aria-live", "polite");
    field.append(counter);

    const updateCounter = () => {
        counter.textContent = `${input.value.length} / ${input.maxLength}`;
    };

    input.addEventListener("input", updateCounter);
    updateCounter();
});


/* Doppelte Formularübermittlung verhindern */

document.querySelectorAll(".form-card form").forEach((form) => {
    form.addEventListener("submit", () => {
        const submitButton = form.querySelector('button[type="submit"]');

        if (!submitButton) {
            return;
        }

        submitButton.disabled = true;
        submitButton.classList.add("is-submitting");
        submitButton.setAttribute("aria-busy", "true");
        submitButton.dataset.originalText = submitButton.textContent.trim();
        submitButton.textContent = "Wird gespeichert …";
    });
});