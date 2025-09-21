// Use markdown-it for rendering full-featured Markdown
let mdParser = null;

function ensureParser() {
    if (!mdParser) {
        // Enable HTML disabled for safety, but allow linkify and typographer
        mdParser = window.markdownit({ html: false, linkify: true, typographer: true });
    }
    return mdParser;
}

function renderMarkdown(md) {
    if (!md) return '';
    const p = ensureParser();
    // Render markdown to HTML
    const html = p.render(md);
    return html;
}

function openMarkdownPreview(content, title) {
    const modal = document.getElementById('md-preview-modal');
    const body = document.getElementById('md-preview-body');
    const header = document.getElementById('md-preview-title');
    header.textContent = title || 'Markdown プレビュー';
    body.innerHTML = renderMarkdown(content || '');
    // Make all links open in new tab and safe
    body.querySelectorAll('a').forEach(a => {
        a.setAttribute('target', '_blank');
        a.setAttribute('rel', 'noopener');
    });
    modal.classList.remove('hidden');
}

function closeMarkdownPreview() {
    const modal = document.getElementById('md-preview-modal');
    modal.classList.add('hidden');
}

function renderInlineMarkdown(root=document) {
    const p = ensureParser();
    (root.querySelectorAll ? root.querySelectorAll('[data-md-inline]') : []).forEach(el => {
        const md = el.getAttribute('data-md-inline') || '';
        el.innerHTML = p.renderInline(md);
    });
}

document.addEventListener('DOMContentLoaded', function() {
    // Render inline markdown in cards
    renderInlineMarkdown();

    // Auto-open preview if an element with data-md-autostart exists
    const auto = document.querySelector('[data-md-autostart]');
    if (auto) {
        const md = auto.getAttribute('data-md') || '';
        const title = auto.getAttribute('data-title') || '';
        // small timeout to allow UI to settle
        setTimeout(() => openMarkdownPreview(md, title), 200);
    }

    // Close modal handlers
    const closeBtn = document.getElementById('md-preview-close');
    if (closeBtn) closeBtn.addEventListener('click', closeMarkdownPreview);
    const modal = document.getElementById('md-preview-modal');
    if (modal) modal.addEventListener('click', function(e) { if (e.target === this) closeMarkdownPreview(); });

    // If HTMX is used and swaps content, re-render inline markdown after swap
    if (window.htmx) {
        document.body.addEventListener('htmx:afterSwap', function(evt) {
            renderInlineMarkdown(evt.target);
            if (window.createIcons) createIcons();
        });
    }
});
