// Lightweight initializer for Lucide icons
// This script expects `lucide` to be available globally (via CDN or bundle).
document.addEventListener('DOMContentLoaded', function () {
    try {
        if (typeof lucide !== 'undefined' && lucide && typeof lucide.replace === 'function') {
            lucide.replace({ 'stroke-width': 1.5 });
        } else {
            // If lucide isn't loaded yet, try loading via CDN dynamically
            var script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/lucide@0.259.0/dist/lucide.min.js';
            script.defer = true;
            script.onload = function () {
                try { lucide.replace({ 'stroke-width': 1.5 }); } catch (e) { console.warn('lucide init failed', e); }
            };
            script.onerror = function () { console.warn('Failed to load lucide from CDN'); };
            document.head.appendChild(script);
        }
    } catch (err) {
        console.warn('icons init error', err);
    }
});

// Provide a global createIcons() for existing code compatibility
window.createIcons = function() {
    try {
        if (typeof lucide !== 'undefined' && lucide && typeof lucide.replace === 'function') {
            lucide.replace({ 'stroke-width': 1.5 });
        } else if (typeof window.lucide === 'undefined') {
            // Load lucide dynamically if not present
            var script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/lucide@0.259.0/dist/lucide.min.js';
            script.defer = true;
            script.onload = function () { try { lucide.replace({ 'stroke-width': 1.5 }); } catch(e){} };
            document.head.appendChild(script);
        }
    } catch (e) {
        console.warn('createIcons error', e);
    }
};

