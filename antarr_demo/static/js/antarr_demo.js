(() => {
    const header = document.querySelector("[data-site-header]");
    const menuToggle = document.querySelector("[data-menu-toggle]");
    const siteNav = document.querySelector("[data-site-nav]");

    if (header) {
        const updateHeader = () => header.classList.toggle("is-scrolled", window.scrollY > 120);
        updateHeader();
        window.addEventListener("scroll", updateHeader, { passive: true });
    }

    if (menuToggle && siteNav) {
        menuToggle.addEventListener("click", () => {
            const open = menuToggle.getAttribute("aria-expanded") !== "true";
            menuToggle.setAttribute("aria-expanded", String(open));
            siteNav.classList.toggle("is-open", open);
            document.body.classList.toggle("nav-open", open);
        });
        siteNav.querySelectorAll("a").forEach((link) => link.addEventListener("click", () => {
            menuToggle.setAttribute("aria-expanded", "false");
            siteNav.classList.remove("is-open");
            document.body.classList.remove("nav-open");
        }));
    }

    const portalToggle = document.querySelector("[data-portal-toggle]");
    const portalSidebar = document.querySelector("[data-portal-sidebar]");
    if (portalToggle && portalSidebar) {
        portalToggle.addEventListener("click", () => {
            const open = portalToggle.getAttribute("aria-expanded") !== "true";
            portalToggle.setAttribute("aria-expanded", String(open));
            portalSidebar.classList.toggle("is-open", open);
        });
    }

    document.querySelectorAll("[data-process-picker]").forEach((picker) => {
        picker.addEventListener("change", () => {
            const url = new URL(window.location.href);
            url.searchParams.set("process", picker.value);
            window.location.assign(url.toString());
        });
    });
})();
