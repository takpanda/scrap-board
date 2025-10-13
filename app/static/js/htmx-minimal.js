/**
 * Minimal HTMX-like implementation for similar documents loading and modal functionality
 */

// Create a global htmx object for compatibility with modal.js
window.htmx = window.htmx || {};
window.htmx.ajax = function(method, url, options) {
    const target = options.target ? document.querySelector(options.target) : document.body;
    const swap = options.swap || 'innerHTML';

    fetch(url, {
        method: method,
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
        if (swap === 'innerHTML' && target) {
            target.innerHTML = html;
        } else if (swap === 'outerHTML' && target) {
            target.outerHTML = html;
        }

        // Trigger afterSwap event
        const afterSwapEvent = new CustomEvent('htmx:afterSwap', {
            detail: {
                target: target,
                xhr: null
            }
        });
        document.body.dispatchEvent(afterSwapEvent);

        // Re-initialize icons
        if (window.lucide) {
            window.lucide.createIcons();
        } else if (window.createIcons) {
            window.createIcons();
        }

        // Re-bind hx handlers
        if (typeof initHxBindings === 'function') {
            initHxBindings();
        }
    })
    .catch(error => {
        console.error('htmx.ajax error:', error);

        // Trigger responseError event
        const errorEvent = new CustomEvent('htmx:responseError', {
            detail: {
                target: target,
                error: error
            }
        });
        document.body.dispatchEvent(errorEvent);
    });
};

document.addEventListener('DOMContentLoaded', function() {
    initHxBindings();
    // Trigger initial hx-get loads
    const hxElements = document.querySelectorAll('[hx-get][hx-trigger="load"]');
    hxElements.forEach(element => {
        const url = element.getAttribute('hx-get');
        const target = element.getAttribute('hx-target');

        if (url) {
            loadHxContent(url, target || element);
        }
    });
});

function initHxBindings() {
    // initialize bindings
    // Attach form handlers for hx-post
    const hxPostForms = document.querySelectorAll('form[hx-post]');
    hxPostForms.forEach(form => {
        if (form._hxBound) return;
        form._hxBound = true;
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const url = form.getAttribute('hx-post');
            const hxSwap = form.getAttribute('hx-swap') || '';

            const formData = new FormData(form);

            fetch(url, {
                method: 'POST',
                body: formData,
                headers: {
                    'HX-Request': 'true'
                }
            })
            .then(response => response.text())
            .then(html => {
                performSwap(html, hxSwap, form);
                initHxBindings();
            })
            .catch(err => console.error('hx-post error', err));
        });
    });

    // Attach form handlers for hx-put
    const hxPutForms = document.querySelectorAll('form[hx-put]');
    hxPutForms.forEach(form => {
        if (form._hxBound) return;
        form._hxBound = true;
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const url = form.getAttribute('hx-put');
            const hxSwap = form.getAttribute('hx-swap') || '';

            const formData = new FormData(form);

            // Convert FormData to URLSearchParams for proper form-encoded body
            const params = new URLSearchParams();
            for (const pair of formData.entries()) {
                params.append(pair[0], pair[1]);
            }

            fetch(url, {
                method: 'PUT',
                body: params,
                headers: {
                    'HX-Request': 'true',
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            })
            .then(response => response.text())
            .then(html => {
                performSwap(html, hxSwap, form);
                initHxBindings();
            })
            .catch(err => console.error('hx-put error', err));
        });
    });

    // Attach click handlers for hx-get (links, buttons)
    const hxGetElems = document.querySelectorAll('a[hx-get], button[hx-get]');
    hxGetElems.forEach(elem => {
        if (elem._hxGetBound) return;
        elem._hxGetBound = true;
        elem.addEventListener('click', function(e) {
            e.preventDefault();
            const url = elem.getAttribute('hx-get');
            const target = elem.getAttribute('hx-target');
            const hxSwap = elem.getAttribute('hx-swap') || 'innerHTML';
            const hxPushUrl = elem.getAttribute('hx-push-url');

            if (!url) return;

            // Find target element
            let targetElement = target ? document.querySelector(target) : elem;
            if (!targetElement) {
                console.error('Target element not found:', target);
                return;
            }

            // Update URL history if hx-push-url is set
            if (hxPushUrl) {
                window.history.pushState({}, '', hxPushUrl);
            }

            // Fetch content
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
                // Perform swap
                if (hxSwap === 'innerHTML') {
                    targetElement.innerHTML = html;
                } else if (hxSwap === 'outerHTML') {
                    targetElement.outerHTML = html;
                }

                // Trigger HTMX afterSwap event
                const afterSwapEvent = new CustomEvent('htmx:afterSwap', {
                    detail: {
                        target: targetElement,
                        xhr: null
                    }
                });
                document.body.dispatchEvent(afterSwapEvent);

                // Re-initialize icons
                if (window.lucide) {
                    window.lucide.createIcons();
                } else if (window.createIcons) {
                    window.createIcons();
                }

                // Re-bind hx handlers
                initHxBindings();
            })
            .catch(error => {
                console.error('hx-get error:', error);

                // Trigger HTMX responseError event
                const errorEvent = new CustomEvent('htmx:responseError', {
                    detail: {
                        target: targetElement,
                        error: error
                    }
                });
                document.body.dispatchEvent(errorEvent);
            });
        });
    });

    // Attach click handlers for hx-post on non-form elements (buttons/links)
    const hxPostElems = document.querySelectorAll('[hx-post]');
    hxPostElems.forEach(elem => {
        // skip forms (handled separately)
        if (elem.tagName.toLowerCase() === 'form') return;
        if (elem._hxPostBound) return;
        elem._hxPostBound = true;
        elem.addEventListener('click', function(e) {
            e.preventDefault();
            const url = elem.getAttribute('hx-post');
            const hxSwap = elem.getAttribute('hx-swap') || '';

            // hx-vals may contain small JSON to send as body
            const vals = elem.getAttribute('hx-vals');
            let body = null;
            let headers = { 'HX-Request': 'true' };
            if (vals) {
                try {
                    body = JSON.stringify(JSON.parse(vals));
                    headers['Content-Type'] = 'application/json';
                } catch (err) {
                    body = vals;
                }
            }

            fetch(url, { method: 'POST', body: body, headers: headers })
            .then(response => response.text())
            .then(html => {
                // Response received - process OOB fragments and swaps

                // Parse response and apply OOB fragments first.
                // Then perform the normal swap only for any remaining non-OOB HTML.
                try {
                    const container = document.createElement('div');
                    container.innerHTML = html;

                    // Find OOB nodes in the response
                    const oobNodes = container.querySelectorAll('[hx-swap-oob]');
                    if (oobNodes.length > 0) {
                        // Apply OOB using the raw response so applyOob's logic is reused.
                        try { applyOob(html); } catch (e) { console.warn('applyOob failed', e); }

                        // Remove the OOB nodes from the container so remaining HTML can be swapped into place
                        oobNodes.forEach(n => n.remove());
                    }

                    const remaining = container.innerHTML.trim();
                    if (remaining) {
                        performSwap(remaining, hxSwap, elem);
                    }
                } catch (e) {
                    console.warn('hx-post: parse/apply error', e);
                    // fallback: perform swap with raw html
                    try { performSwap(html, hxSwap, elem); } catch (ee) { console.warn('performSwap fallback failed', ee); }
                }

                // Defer binding re-init to next microtask so DOM replacements settle
                try { Promise.resolve().then(() => initHxBindings()); } catch (e) { try { initHxBindings(); } catch (ee) {} }
            })
            .catch(err => console.error('hx-post error', err));
        });
    });

    // Attach click handlers for hx-put and hx-delete (buttons, links)
    const hxActionElems = document.querySelectorAll('[hx-put],[hx-delete]');
    hxActionElems.forEach(elem => {
        if (elem._hxBound) return;
        elem._hxBound = true;
        elem.addEventListener('click', function(e) {
            e.preventDefault();
            const putUrl = elem.getAttribute('hx-put');
            const delUrl = elem.getAttribute('hx-delete');
            const url = putUrl || delUrl;
            const method = putUrl ? 'PUT' : 'DELETE';
            const hxSwap = elem.getAttribute('hx-swap') || '';

            // hx-vals may contain small JSON to send as body
            const vals = elem.getAttribute('hx-vals');
            let body = null;
            let headers = { 'HX-Request': 'true' };
            if (vals) {
                try {
                    body = JSON.stringify(JSON.parse(vals));
                    headers['Content-Type'] = 'application/json';
                } catch (err) {
                    // If parsing fails, try to interpret as simple key:value
                    body = vals;
                }
            }

            fetch(url, { method: method, body: body, headers: headers })
            .then(response => response.text())
            .then(html => {
                performSwap(html, hxSwap, elem);
                initHxBindings();
            })
            .catch(err => console.error('hx-action error', err));
        });
    });
    // Attach edit/cancel buttons within sources list (if present)
    const editBtns = document.querySelectorAll('#sources-list .edit-btn');
    editBtns.forEach(btn => {
        if (btn._editBound) return;
        btn._editBound = true;
        btn.addEventListener('click', function(e){
            // Support table rows and card containers (data-source-id)
            const container = e.target.closest('tr') || e.target.closest('[data-source-id]');
            if (!container) return;
            const display = container.querySelector('.cron-display');
            const form = container.querySelector('.cron-form');
            if (display) display.style.display = 'none';
            if (form) form.style.display = 'block';
        });
    });

    const cancelBtns = document.querySelectorAll('#sources-list .cancel-edit');
    cancelBtns.forEach(btn => {
        if (btn._cancelBound) return;
        btn._cancelBound = true;
        btn.addEventListener('click', function(e){
            const container = e.target.closest('tr') || e.target.closest('[data-source-id]');
            if (!container) return;
            const display = container.querySelector('.cron-display');
            const form = container.querySelector('.cron-form');
            if (form) form.style.display = 'none';
            if (display) display.style.display = 'block';
        });
    });

}

/**
 * Apply out-of-band swaps contained in an HTML fragment.
 * The server may return fragments wrapped with ids and attribute hx-swap-oob="true".
 * This function will parse the fragment and for each element with an id
 * attempt to replace the corresponding element in the current document
 * with the fragment's innerHTML (preserving outer id where appropriate).
 */
function applyOob(html) {
    if (!html) return;
    try {
        const container = document.createElement('div');
        container.innerHTML = html;

        // Only consider elements that explicitly request OOB swaps
        const candidates = container.querySelectorAll('[hx-swap-oob]');
        candidates.forEach(node => {
            const id = node.id;
            // If there is no id on the OOB node, skip — server should provide ids for OOB targets
            if (!id) return;

            const target = document.getElementById(id);
            if (target) {
                try {
                    const nodeHasSameIdDescendant = !!node.querySelector(`#${id}`);
                    const tagMismatch = target.tagName.toLowerCase() !== node.tagName.toLowerCase();

                    // If the response node contains a descendant with the same id (or the wrapper tag differs),
                    // replace the entire target element with the inner HTML from the response. This avoids
                    // nesting elements with identical ids (which breaks strict selectors in Playwright).
                    if (nodeHasSameIdDescendant || tagMismatch) {
                        try {
                            target.outerHTML = node.innerHTML || node.outerHTML;
                        } catch (e) {
                            console.warn('applyOob: outerHTML replace failed for', id, e);
                            // fallback: set innerHTML
                            try { target.innerHTML = node.innerHTML; } catch (ee) { console.warn('applyOob fallback innerHTML failed for', id, ee); }
                        }
                    } else {
                        // Otherwise, preserve the wrapper and replace its inner content
                        try {
                            target.innerHTML = node.innerHTML;
                        } catch (e) {
                            console.warn('applyOob: innerHTML replace failed for', id, e);
                            try { target.outerHTML = node.outerHTML || node.innerHTML; } catch (ee) { console.warn('applyOob fallback outerHTML failed for', id, ee); }
                        }
                    }
                } catch (e) {
                    console.warn('applyOob: error applying node for', id, e);
                }
            } else {
                    // Target not found in current document; append the node to body as a last resort
                try {
                    const imported = document.importNode(node, true);
                    document.body.appendChild(imported);
                } catch (e) {
                    console.warn('applyOob: failed to append missing target', id, e);
                }
            }
        });

        // After applying OOB swaps, re-init icons and bindings in next microtask
        try { if (window.lucide) Promise.resolve().then(() => { try { window.lucide.createIcons(); } catch(e){} }); } catch (e) {}
        try { Promise.resolve().then(() => { try { initHxBindings(); } catch(e){} }); } catch (e) {}
    } catch (e) {
        console.warn('applyOob parse error', e);
    }
}

function loadHxContent(url, targetSelectorOrElement) {
    let targetElement = null;
    if (typeof targetSelectorOrElement === 'string') {
        targetElement = document.querySelector(targetSelectorOrElement);
    } else if (targetSelectorOrElement instanceof Element) {
        targetElement = targetSelectorOrElement;
    }

    if (!targetElement) {
        console.error('Target element not found:', targetSelectorOrElement);
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
            console.log('Triggering lucide.createIcons() after load');
            window.lucide.createIcons();
        } else if (window.createIcons) {
            console.log('Triggering createIcons() after load');
            window.createIcons();
        } else {
            console.warn('No icon creation function available after load');
        }

        // Re-bind hx handlers for newly injected content
        if (typeof initHxBindings === 'function') {
            try {
                initHxBindings();
            } catch (e) {
                console.error('initHxBindings error after load:', e);
            }
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
            console.log('Triggering lucide.createIcons() after error');
            window.lucide.createIcons();
        } else if (window.createIcons) {
            console.log('Triggering createIcons() after error');
            window.createIcons();
        } else {
            console.warn('No icon creation function available after error');
        }
    });
}

function performSwap(html, hxSwap, sourceElement) {
    // hxSwap examples: "outerHTML", "outerHTML:closest #sources-list"
    if (!hxSwap) {
        // Default: replace source element innerHTML
        sourceElement.innerHTML = html;
        // Re-initialize icons after swap
        if (window.lucide) {
            console.log('Triggering lucide.createIcons() after default swap');
            window.lucide.createIcons();
        } else if (window.createIcons) {
            console.log('Triggering createIcons() after default swap');
            window.createIcons();
        }
        return;
    }

    const parts = hxSwap.split(':');
    const swapType = parts[0];
    const swapTarget = parts[1] ? parts[1].trim() : null;

    if (swapType === 'outerHTML' && swapTarget && swapTarget.startsWith('closest')) {
        // format: "outerHTML:closest #selector"
        const selector = swapTarget.replace('closest', '').trim();
        const target = sourceElement.closest(selector);
        if (target) {
            // Replace the INNER HTML of the closest container instead of replacing
            // the element itself. This preserves attributes like `id` and any
            // event hooks attached to the container, preventing accidental
            // removal of the wrapper element (which broke subsequent bindings).
            target.innerHTML = html;
            
            // Re-initialize icons after swap
            if (window.lucide) {
                console.log('Triggering lucide.createIcons() after closest swap');
                window.lucide.createIcons();
            } else if (window.createIcons) {
                console.log('Triggering createIcons() after closest swap');
                window.createIcons();
            }
        } else {
            console.error('performSwap: closest target not found for', selector);
        }
        return;
    }

    if (swapType === 'outerHTML') {
        // replace the source element entirely
        sourceElement.outerHTML = html;
        // Re-initialize icons after outer HTML replacement
        if (window.lucide) {
            console.log('Triggering lucide.createIcons() after outerHTML swap');
            window.lucide.createIcons();
        } else if (window.createIcons) {
            console.log('Triggering createIcons() after outerHTML swap');
            window.createIcons();
        }
        return;
    }

    // fallback: inject into source element
    sourceElement.innerHTML = html;
    // Re-initialize icons after fallback swap
    if (window.lucide) {
        console.log('Triggering lucide.createIcons() after fallback swap');
        window.lucide.createIcons();
    } else if (window.createIcons) {
        console.log('Triggering createIcons() after fallback swap');
        window.createIcons();
    }
}