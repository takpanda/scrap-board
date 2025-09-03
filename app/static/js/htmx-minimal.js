/**
 * Minimal HTMX-like implementation for similar documents loading
 */
document.addEventListener('DOMContentLoaded', function() {
    // Find all elements with hx-get and hx-trigger="load"
    const hxElements = document.querySelectorAll('[hx-get][hx-trigger="load"]');
    
    hxElements.forEach(element => {
        const url = element.getAttribute('hx-get');
        const target = element.getAttribute('hx-target');
        
        if (url && target) {
            loadHxContent(url, target);
        }
    });
});

function loadHxContent(url, targetSelector) {
    const targetElement = document.querySelector(targetSelector);
    if (!targetElement) {
        console.error('Target element not found:', targetSelector);
        return;
    }
    
    // Add loading indicator
    targetElement.innerHTML = `
        <div class="text-center py-8 text-graphite">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald mx-auto mb-2"></div>
            <p class="text-sm">関連ドキュメントを読み込み中...</p>
        </div>
    `;
    
    // Make request with HX-Request header
    fetch(url, {
        headers: {
            'HX-Request': 'true'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.text();
    })
    .then(html => {
        targetElement.innerHTML = html;
        
        // Trigger lucide icon loading if available
        if (window.lucide) {
            window.lucide.createIcons();
        }
    })
    .catch(error => {
        console.error('Error loading HTMX content:', error);
        targetElement.innerHTML = `
            <div class="text-center py-8 text-red-500">
                <i data-lucide="alert-circle" class="w-8 h-8 mx-auto mb-2 opacity-50"></i>
                <p class="text-sm">関連ドキュメントの読み込みに失敗しました</p>
            </div>
        `;
        
        // Trigger lucide icon loading if available
        if (window.lucide) {
            window.lucide.createIcons();
        }
    });
}