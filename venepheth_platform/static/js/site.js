/* Site interactivity — extracted from base.html so the Content-Security-Policy
   needs no per-request nonce (cached pages share it). Loaded with defer.
   Covers: Lucide icons, scroll-reveal, HTMX re-init, delegated UI actions
   ([data-print], [data-reload], [data-copy], form[data-confirm]), header
   toggles, toasts, contact submit state, accordions. No eval. */

// Guarded: a CDN failure must never break scroll-reveal content below.
if (window.lucide) {
    lucide.createIcons();
}

// Intersection Observer for scroll animations
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('animate-fade-in-up');
            entry.target.classList.remove('opacity-0');
            observer.unobserve(entry.target);
        }
    });
}, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

document.querySelectorAll('.reveal').forEach(el => observer.observe(el));

// Re-run after HTMX swaps
document.addEventListener('htmx:afterSwap', () => {
    if (window.lucide) {
        lucide.createIcons();
    }
    document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
});

// Delegated UI actions (CSP-safe replacement for inline onclick/onsubmit).
document.addEventListener('click', (event) => {
    const el = event.target.closest('[data-print],[data-reload],[data-copy]');
    if (!el) {
        return;
    }
    if (el.hasAttribute('data-print')) {
        window.print();
    } else if (el.hasAttribute('data-reload')) {
        window.location.reload();
    } else if (el.hasAttribute('data-copy')) {
        const text = el.getAttribute('data-copy') || '';
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text).catch(() => {});
        }
    }
});
document.addEventListener('submit', (event) => {
    const form = event.target.closest('form[data-confirm]');
    if (!form) {
        return;
    }
    const onlyFor = form.getAttribute('data-confirm-for');
    if (onlyFor) {
        const submitter = event.submitter;
        if (!submitter || submitter.getAttribute('name') !== onlyFor) {
            return;
        }
    }
    if (!window.confirm(form.getAttribute('data-confirm'))) {
        event.preventDefault();
    }
});

// Vanilla UI controller (replaces Alpine.js — no eval, CSP-safe).
(function () {
    const toggleHidden = (el, force) => {
        if (!el) {
            return;
        }
        el.hidden = force !== undefined ? !force : !el.hidden;
    };
    const setExpanded = (btn, open) => {
        if (btn) {
            btn.setAttribute('aria-expanded', open ? 'true' : 'false');
        }
    };
    const langBtn = document.getElementById('lang-btn');
    const langMenu = document.getElementById('lang-menu');
    if (langBtn && langMenu) {
        langBtn.addEventListener('click', (event) => {
            event.stopPropagation();
            const open = langMenu.hidden;
            toggleHidden(langMenu, open);
            setExpanded(langBtn, open);
        });
        document.addEventListener('click', (event) => {
            if (!langMenu.hidden && !document.getElementById('lang-wrap').contains(event.target)) {
                toggleHidden(langMenu, false);
                setExpanded(langBtn, false);
            }
        });
    }
    const searchBtn = document.getElementById('search-btn');
    const searchBar = document.getElementById('search-bar');
    if (searchBtn && searchBar) {
        searchBtn.addEventListener('click', () => {
            const open = searchBar.hidden;
            toggleHidden(searchBar, open);
            setExpanded(searchBtn, open);
            if (open) {
                const input = searchBar.querySelector('input[type="search"]');
                if (input) {
                    input.focus();
                }
            }
        });
    }
    const menuBtn = document.getElementById('menu-btn');
    const mobileNav = document.getElementById('mobile-nav');
    const iconOpen = document.getElementById('menu-icon-open');
    const iconClose = document.getElementById('menu-icon-close');
    if (menuBtn && mobileNav) {
        menuBtn.addEventListener('click', () => {
            const open = mobileNav.hidden;
            toggleHidden(mobileNav, open);
            setExpanded(menuBtn, open);
            toggleHidden(iconOpen, !open);
            toggleHidden(iconClose, open);
        });
    }
    // Toasts: auto-dismiss + manual dismiss.
    document.querySelectorAll('[data-toast]').forEach((toast) => {
        window.setTimeout(() => {
            toast.style.opacity = '0';
            window.setTimeout(() => toast.remove(), 350);
        }, 4000);
    });
    document.addEventListener('click', (event) => {
        const closer = event.target.closest('[data-toast-close]');
        if (closer) {
            const toast = closer.closest('[data-toast]');
            if (toast) {
                toast.remove();
            }
        }
    });
    // Contact form submitting state.
    document.addEventListener('submit', (event) => {
        const form = event.target.closest('form[data-contact-form]');
        if (!form) {
            return;
        }
        const btn = form.querySelector('[data-contact-submit]');
        if (btn) {
            btn.disabled = true;
            const sendIcon = form.querySelector('[data-contact-icon-send]');
            const loadIcon = form.querySelector('[data-contact-icon-loading]');
            const label = form.querySelector('[data-contact-label]');
            if (sendIcon) {
                sendIcon.classList.add('hidden');
            }
            if (loadIcon) {
                loadIcon.classList.remove('hidden');
            }
            if (label) {
                label.textContent = label.getAttribute('data-sending-label') || label.textContent;
            }
        }
    });
    // Accordions (e.g. course modules).
    document.addEventListener('click', (event) => {
        const btn = event.target.closest('[data-accordion-btn]');
        if (!btn) {
            return;
        }
        const panel = document.getElementById(btn.getAttribute('data-accordion-btn'));
        if (panel) {
            panel.hidden = !panel.hidden;
            const chevron = btn.querySelector('[data-accordion-chevron]');
            if (chevron) {
                chevron.classList.toggle('rotate-180');
            }
            btn.setAttribute('aria-expanded', panel.hidden ? 'false' : 'true');
        }
    });
    // Auto-submitting filter forms (replaces CSP-blocked inline onchange).
    document.addEventListener('change', (event) => {
        const el = event.target.closest('[data-auto-submit]');
        if (!el) {
            return;
        }
        const form = el.closest('form');
        if (form) {
            form.submit();
        }
    });
})();
