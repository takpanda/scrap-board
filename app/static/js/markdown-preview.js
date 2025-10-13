// Robust markdown preview for inline summaries and modal preview
(function(){
    var CDN = 'https://cdn.jsdelivr.net/npm/markdown-it@13.0.1/dist/markdown-it.min.js';
    var md = null;

    function log(){ try { console.log.apply(console, arguments); } catch(e){} }

    function escapeHtml(str){
        return String(str).replace(/[&<>"]+/g, function(match){
            switch(match){
                case '&': return '&amp;';
                case '<': return '&lt;';
                case '>': return '&gt;';
                case '"': return '&quot;';
                default: return match;
            }
        });
    }

    function initParser(){
        try {
            if (!window.markdownit) return (md = null);
            var opts = {
                html: false,
                linkify: true,
                typographer: true,
                // highlight code blocks if highlight.js is available
                highlight: function(str, lang){
                    try{
                        if (window.hljs && lang && window.hljs.getLanguage && window.hljs.getLanguage(lang)){
                            return '<pre class="hljs"><code>' + window.hljs.highlight(str, { language: lang }).value + '</code></pre>';
                        }
                    }catch(e){ /* ignore and fallback */ }
                    return '<pre class="hljs"><code>' + escapeHtml(str) + '</code></pre>';
                }
            };
            md = window.markdownit(opts);
        } catch(e){ log('markdown-preview: parser init failed', e); md = null; }
        return md;
    }

    function renderInlineMarkdown(root=document){
        try{
            var parser = md || (window.markdownit ? initParser() : null);
            (root.querySelectorAll ? root.querySelectorAll('[data-md-inline]') : []).forEach(function(el){
                if (el.innerHTML && el.innerHTML.trim().length > 0) return; // already rendered
                var raw = el.getAttribute('data-md-inline') || el.dataset.mdInline || '';
                if (!raw) return;
                try{
                    if (parser) el.innerHTML = parser.render(raw);
                    else el.textContent = raw;
                }catch(e){ console.warn('markdown-preview render inline error', e); el.textContent = raw; }
            });
        }catch(e){ console.warn('markdown-preview renderInlineMarkdown failed', e); }
    }

    function openMarkdownPreview(content, title){
        var modal = document.getElementById('md-preview-modal');
        var body = document.getElementById('md-preview-body');
        var header = document.getElementById('md-preview-title');
        if (header) header.textContent = title || 'Markdown プレビュー';
        try{
            var parser = md || (window.markdownit ? initParser() : null);
            if (parser) body.innerHTML = parser.render(content || '');
            else body.textContent = content || '';
        }catch(e){ body.textContent = content || ''; }
        if (body) body.querySelectorAll && body.querySelectorAll('a').forEach(function(a){ a.setAttribute('target','_blank'); a.setAttribute('rel','noopener'); });
        if (modal) modal.classList.remove('hidden');
    }

    function processAutostarts(root){
        var scope = (root && root.querySelectorAll) ? root : document;
        var nodes = scope.querySelectorAll('[data-md-autostart]');
        if (!nodes || nodes.length === 0) return;
        nodes.forEach(function(node){
            // prefer textContent to preserve newlines and avoid attribute escaping
            var content = (node.textContent && node.textContent.trim()) || node.getAttribute('data-md') || node.getAttribute('data-md-autostart') || '';
            var title = node.getAttribute('data-title') || '';
            // find inline target nearby
            var target = null;
            if (node.parentElement) target = node.parentElement.querySelector('[data-md-inline]');
            if (!target){ var s = node.previousElementSibling; while(s){ if (s.hasAttribute && s.hasAttribute('data-md-inline')){ target = s; break; } s = s.previousElementSibling; } }
            if (!target){ var n = node.nextElementSibling; while(n){ if (n.hasAttribute && n.hasAttribute('data-md-inline')){ target = n; break; } n = n.nextElementSibling; } }
            if (!target) target = scope.querySelector('[data-md-inline]');
            if (target){
                try{
                    var parser = md || (window.markdownit ? initParser() : null);
                    if (parser) target.innerHTML = parser.render(content);
                    else target.textContent = content;
                }catch(e){ target.textContent = content; }
            }
            // open modal for the first autostart only
            try{ openMarkdownPreview(content, title); }catch(e){}
            node.removeAttribute('data-md-autostart');
        });
    }

    function loadAndInit(){
        try{
            if (window.markdownit) { initParser(); renderInlineMarkdown(); processAutostarts(); return; }
        }catch(e){ log('markdown-preview:init check failed', e); }

        // dynamically load markdown-it (and optionally highlight.js) then render
        var s = document.createElement('script');
        s.src = CDN;
        s.async = true;

        // optional highlight.js CDN (load in parallel); if present we'll use it for code highlighting
        var HL_CSS = 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/styles/github.min.css';
        var HL_JS = 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/highlight.min.js';
        var hlLoaded = false;
        try{
            if (!window.hljs){
                var hlcss = document.createElement('link');
                hlcss.rel = 'stylesheet';
                hlcss.href = HL_CSS;
                hlcss.crossOrigin = '';
                document.head.appendChild(hlcss);

                var hls = document.createElement('script');
                hls.src = HL_JS;
                hls.async = true;
                hls.onload = function(){ hlLoaded = true; try{ if (window.hljs && window.hljs.highlightAll) { /* ready */ } }catch(e){} };
                hls.onerror = function(){ hlLoaded = false; };
                document.head.appendChild(hls);
            } else {
                hlLoaded = true;
            }
        }catch(e){ hlLoaded = false; }

        s.onload = function(){
            try{
                initParser();
                // If highlight.js loaded, initialize languages (if available)
                try{ if (window.hljs && typeof window.hljs.highlightAll === 'function') window.hljs.highlightAll(); }catch(e){}
                renderInlineMarkdown();
                processAutostarts();
            }catch(e){ console.warn('markdown-preview after load err', e); }
        };
        s.onerror = function(e){ console.warn('markdown-preview failed to load CDN', e); renderInlineMarkdown(); processAutostarts(); };
        document.head.appendChild(s);
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', loadAndInit);
    else loadAndInit();

    // Re-render after HTMX swaps if present
    if (window && window.htmx) {
        document.body.addEventListener('htmx:afterSwap', function(evt){ renderInlineMarkdown(evt.target); processAutostarts(evt.target); if (window.createIcons) createIcons(); });
    }

    try {
        window.scrapMarkdownRenderInline = renderInlineMarkdown;
        window.scrapMarkdownProcessAutostarts = processAutostarts;
        window.scrapMarkdownRefresh = function(root){
            renderInlineMarkdown(root || document);
            processAutostarts(root || document);
            if (typeof window.createIcons === 'function') {
                try { window.createIcons(); } catch (err) { console.warn('markdown-preview: createIcons failed after refresh', err); }
            }
        };
    } catch (ex) {
        log('markdown-preview: failed to expose helpers', ex);
    }

})();
