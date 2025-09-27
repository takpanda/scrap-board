(function(){
    var CDN = 'https://cdn.jsdelivr.net/npm/markdown-it@13.0.1/dist/markdown-it.min.js';

    function log(){
        try { console.log.apply(console, arguments); } catch(e){}
    }

    function renderAllWith(md){
        log('markdown-preview: rendering with markdown-it', !!md);
        // Process autostart nodes first
        var autostarts = document.querySelectorAll('[data-md-autostart]');
        log('markdown-preview: autostart count', autostarts.length);
        autostarts.forEach(function(node){
            // Prefer node.textContent when available to preserve newlines and unescaped markdown
            var content = (node.textContent && node.textContent.trim()) || node.getAttribute('data-md') || node.getAttribute('data-md-autostart') || '';
            var title = node.getAttribute('data-title') || '';
            // find nearest data-md-inline in parent
            var parent = node.parentElement;
            var target = null;
            if (parent) {
                target = parent.querySelector('[data-md-inline]');
            }
            if (!target) {
                // try siblings
                var s = node.previousElementSibling;
                while(s){ if (s.hasAttribute && s.hasAttribute('data-md-inline')){ target = s; break; } s = s.previousElementSibling; }
                if (!target){ s = node.nextElementSibling; while(s){ if (s.hasAttribute && s.hasAttribute('data-md-inline')){ target = s; break; } s = s.nextElementSibling; } }
            }
            if (!target){ target = document.querySelector('[data-md-inline]'); }
            if (!target) { log('markdown-preview: no target for autostart'); return; }
            try{
                if (md) target.innerHTML = md.render(content);
                else target.textContent = content;
                node.removeAttribute('data-md-autostart');
                log('markdown-preview: rendered autostart for', title || '[no-title]');
            }catch(e){ console.warn('markdown-preview render error', e); }
        });

        // Render inline blocks that are empty
        var inlines = document.querySelectorAll('[data-md-inline]');
        log('markdown-preview: inline count', inlines.length);
        inlines.forEach(function(el){
            if (el.innerHTML && el.innerHTML.trim().length > 0) return;
            var raw = el.getAttribute('data-md-inline') || el.dataset.mdInline || '';
            if (!raw) return;
            try{
                if (md) el.innerHTML = md.render(raw);
                else el.textContent = raw;
            }catch(e){ console.warn('markdown-preview inline render error', e); }
        });
    }

    function initMarkdownPreview(){
        log('markdown-preview: init');
        var md = null;
        try { if (window.markdownit) md = window.markdownit({ html:true, linkify:true }); } catch(e){ log('markdown-preview: markdownit init failed', e); md = null; }
        if (md){ renderAllWith(md); return; }

        // If markdown-it not present, dynamically load it and then render
        log('markdown-preview: markdown-it not present, loading from CDN', CDN);
        var s = document.createElement('script');
        s.src = CDN;
        s.async = true;
        s.onload = function(){
            try{ md = window.markdownit ? window.markdownit({ html:true, linkify:true }) : null; }
            catch(e){ console.warn('markdown-preview: markdownit init after load failed', e); md = null; }
            renderAllWith(md);
        };
        s.onerror = function(e){ console.warn('markdown-preview: failed to load markdown-it', e); renderAllWith(null); };
        document.head.appendChild(s);
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initMarkdownPreview);
    else initMarkdownPreview();
})();
