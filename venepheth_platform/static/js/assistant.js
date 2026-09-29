/* AI Academic Assistant — vanilla JS (no Alpine/eval, CSP-safe).
   Serves both the full chat page ([data-assistant-form]) and the floating
   widget ([data-assistant-widget-form]) included in base.html.
   Anti-bot: posts the honeypot value plus a page-load timestamp; the view
   rejects filled honeypots and sub-2s replies. */

(function () {
    const CHAT_URL = '/assistant/chat/';

    // ─── helpers ────────────────────────────────────────────────────────────
    const getCookie = (name) => {
        const match = document.cookie.match(new RegExp('(^|;\\s*)' + name + '=([^;]*)'));
        return match ? decodeURIComponent(match[2]) : '';
    };

    const csrfToken = (root) => {
        const input = (root || document).querySelector('input[name="csrfmiddlewaretoken"]');
        return (input && input.value) || getCookie('csrftoken');
    };

    const scrollToBottom = (el) => {
        if (el) {
            el.scrollTop = el.scrollHeight;
        }
    };

    const refreshIcons = () => {
        if (window.lucide) {
            lucide.createIcons();
        }
    };

    /* Minimal safe Markdown → HTML.
       Escape raw HTML first (answers echo user input), then allow only
       http(s)/relative link targets. Double quotes MUST be escaped too: link
       URLs land inside href="…", so an unescaped " closes the attribute and
       injects a live event handler. */
    const markdownToHtml = (md) => {
        if (!md) {
            return '';
        }
        return String(md)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;')
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            .replace(/\*([^*]+)\*/g, '<em>$1</em>')
            .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (m, text, url) => {
                const safe = /^(https?:\/\/|\/)/.test(url) ? url : '#';
                return `<a href="${safe}" target="_blank" rel="noopener" class="text-gold-400 underline hover:text-gold-300">${text}</a>`;
            })
            .replace(/^### (.+)$/gm, '<h3 class="text-white font-semibold text-sm mt-3 mb-1">$1</h3>')
            .replace(/^## (.+)$/gm, '<h2 class="text-white font-semibold text-base mt-3 mb-1">$1</h2>')
            .replace(/^- (.+)$/gm, '<li class="text-gray-300 text-sm">$1</li>')
            .replace(/(<li.*<\/li>)/gs, '<ul class="list-disc ml-4 space-y-1 mb-2">$1</ul>')
            .replace(/\n\n/g, '</p><p class="text-gray-200 text-sm leading-relaxed mb-2">')
            .replace(/\n/g, '<br>');
    };

    const esc = (text) => String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');

    // ─── message rendering ──────────────────────────────────────────────────
    const userBubble = (query) => `
        <div class="flex items-start justify-end space-x-3 mb-3">
            <div class="bg-gold-500/20 border border-gold-500/30 rounded-xl rounded-tr-none px-4 py-3 max-w-[80%]">
                <p class="text-white text-sm">${esc(query)}</p>
            </div>
        </div>`;

    const typingBubble = (avatar) => `
        <div class="flex items-start space-x-3" data-typing>
            ${avatar}
            <div class="bg-navy-800/60 border border-white/5 rounded-xl rounded-tl-none px-4 py-3">
                <div class="flex space-x-1 items-center h-4">
                    <span class="w-2 h-2 bg-gold-400 rounded-full animate-bounce" style="animation-delay:-0.3s"></span>
                    <span class="w-2 h-2 bg-gold-400 rounded-full animate-bounce" style="animation-delay:-0.15s"></span>
                    <span class="w-2 h-2 bg-gold-400 rounded-full animate-bounce"></span>
                </div>
            </div>
        </div>`;

    // Avatar is rendered by the template so STATIC_URL is respected; JS only
    // clones the markup.
    const avatarFrom = (root) => {
        const node = (root || document).querySelector('[data-assistant-avatar]');
        return node ? node.innerHTML : '';
    };

    const assistantBubble = (avatar, html, sources, provider) => {
        const chips = (sources || []).map((src) => {
            const title = String(src.title || '').slice(0, 30);
            const label = title.length > 30 ? `${title}...` : title;
            const url = /^(https?:\/\/|\/)/.test(src.url || '') ? src.url : '#';
            return `<a href="${esc(url)}" target="_blank" rel="noopener"
                       class="inline-flex items-center space-x-1 text-xs px-2 py-1 rounded-md bg-white/5 hover:bg-white/10 text-gold-400 border border-white/10 transition-colors">
                       <i data-lucide="external-link" class="w-3 h-3"></i>
                       <span>${esc(label)}</span>
                    </a>`;
        }).join('');
        const sourceBlock = chips
            ? `<div class="mt-3 pt-3 border-t border-white/10">
                   <p class="text-gray-500 text-xs mb-2 font-medium uppercase tracking-wider">Sources</p>
                   <div class="flex flex-wrap gap-2">${chips}</div>
               </div>`
            : '';
        const providerLine = provider
            ? `<p class="text-gray-600 text-xs mt-2 italic">${esc(`Powered by: ${provider}`)}</p>`
            : '';
        return `
            <div class="flex items-start space-x-3">
                ${avatar}
                <div class="bg-navy-800/60 border border-white/5 rounded-xl rounded-tl-none px-4 py-3 max-w-[80%]">
                    <div class="text-gray-200 text-sm leading-relaxed">${html}</div>
                    ${sourceBlock}
                    ${providerLine}
                </div>
            </div>`;
    };

    const errorBubble = (avatar, message) => `
        <div class="flex items-start space-x-3">
            ${avatar}
            <div class="bg-navy-800/60 border border-white/5 rounded-xl rounded-tl-none px-4 py-3 max-w-[80%]">
                <p class="text-red-400 text-sm">${esc(message)}</p>
            </div>
        </div>`;

    // ─── core send routine (shared by page + widget) ────────────────────────
    const send = async (options) => {
        const {
            query, messages, input, honeypot, button, label, spinner,
            loadedAt, avatar, isWidget,
        } = options;

        if (!query || button.disabled) {
            return;
        }
        button.disabled = true;
        if (label) { label.classList.add('hidden'); }
        if (spinner) { spinner.classList.remove('hidden'); }

        messages.insertAdjacentHTML('beforeend', userBubble(query));
        messages.insertAdjacentHTML('beforeend', typingBubble(avatar));
        const typing = messages.querySelector('[data-typing]:last-of-type');
        scrollToBottom(messages);

        try {
            const resp = await fetch(CHAT_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken(document),
                },
                body: JSON.stringify({
                    query: query,
                    language: document.documentElement.lang || 'en',
                    website_url_hp: (honeypot && honeypot.value) || '',
                    loaded_at: loadedAt,
                }),
            });
            const data = await resp.json();
            if (typing) { typing.remove(); }
            if (data.answer) {
                messages.insertAdjacentHTML(
                    'beforeend',
                    assistantBubble(
                        avatar,
                        markdownToHtml(data.answer),
                        isWidget ? [] : data.sources,
                        isWidget ? '' : data.provider
                    )
                );
            } else {
                messages.insertAdjacentHTML(
                    'beforeend',
                    errorBubble(avatar, data.error || 'An error occurred. Please try again.')
                );
            }
        } catch (err) {
            if (typing) { typing.remove(); }
            messages.insertAdjacentHTML('beforeend', errorBubble(avatar, 'Network error. Please check your connection.'));
        } finally {
            button.disabled = false;
            if (label) { label.classList.remove('hidden'); }
            if (spinner) { spinner.classList.add('hidden'); }
            if (input) { input.value = ''; }
            scrollToBottom(messages);
            refreshIcons();
        }
    };

    // ─── full chat page ─────────────────────────────────────────────────────
    const form = document.querySelector('[data-assistant-form]');
    if (form) {
        const messages = document.querySelector('[data-chat-messages]');
        const input = form.querySelector('[data-assistant-input]');
        const honeypot = form.querySelector('input[name="website_url_hp"]');
        const button = form.querySelector('[data-assistant-send]');
        const label = form.querySelector('[data-assistant-send-label]');
        const spinner = form.querySelector('[data-assistant-spinner]');
        const suggestions = document.getElementById('suggested-prompts');
        const avatar = avatarFrom(form.closest('#chat-container') || document);
        const loadedAt = Date.now();

        form.addEventListener('submit', (event) => {
            event.preventDefault();
            const query = (input.value || '').trim();
            if (!query) {
                return;
            }
            if (suggestions) {
                suggestions.hidden = true;
            }
            send({
                query, messages, input, honeypot, button, label, spinner,
                loadedAt, avatar, isWidget: false,
            });
        });

        document.addEventListener('click', (event) => {
            const chip = event.target.closest('[data-assistant-suggest]');
            if (!chip) {
                return;
            }
            input.value = chip.getAttribute('data-assistant-suggest') || '';
            form.dispatchEvent(new Event('submit', { cancelable: true }));
        });

        if (input) {
            input.focus();
        }
    }

    // ─── floating widget (injected in base.html on every page) ─────────────
    const widgetRoot = document.querySelector('[data-assistant-widget]');
    if (widgetRoot) {
        const panel = widgetRoot.querySelector('[data-assistant-widget-panel]');
        const toggle = widgetRoot.querySelector('[data-assistant-widget-toggle]');
        const messages = widgetRoot.querySelector('[data-assistant-widget-messages]');
        const widgetForm = widgetRoot.querySelector('[data-assistant-widget-form]');
        const input = widgetForm && widgetForm.querySelector('[data-assistant-input]');
        const honeypot = widgetForm && widgetForm.querySelector('input[name="website_url_hp"]');
        const button = widgetForm && widgetForm.querySelector('[data-assistant-send]');
        const badge = widgetRoot.querySelector('[data-assistant-widget-badge]');
        const avatar = avatarFrom(widgetRoot);
        const loadedAt = Date.now();

        const setOpen = (open) => {
            panel.hidden = !open;
            const icon = toggle.querySelector('[data-lucide]');
            if (icon) {
                icon.hidden = !open;
            }
            const text = toggle.querySelector('[data-assistant-toggle-text]');
            if (text) {
                text.hidden = open;
            }
            toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
            if (badge) {
                badge.hidden = open;
            }
            if (open) {
                scrollToBottom(messages);
                refreshIcons();
                if (input) {
                    input.focus();
                }
            }
        };

        if (toggle && panel) {
            toggle.addEventListener('click', () => setOpen(panel.hidden));
            document.addEventListener('keydown', (event) => {
                if (event.key === 'Escape' && !panel.hidden) {
                    setOpen(false);
                }
            });
        }

        if (widgetForm && messages) {
            widgetForm.addEventListener('submit', (event) => {
                event.preventDefault();
                const query = (input.value || '').trim();
                if (!query) {
                    return;
                }
                send({
                    query, messages, input, honeypot, button,
                    label: null, spinner: null, loadedAt, avatar, isWidget: true,
                });
            });
        }
    }
})();
