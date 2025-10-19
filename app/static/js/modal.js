/**
 * Document Detail Modal - State Management
 *
 * モーダルの開閉状態を管理し、背景スクロールの制御とアクセシビリティ対応を提供
 */

(function() {
  'use strict';

  // Initialize modal manager. Some environments may execute this script
  // before the DOM node is available (race with template rendering). In
  // that case, retry initialization on DOMContentLoaded so we reliably
  // bind handlers.
  let modalContainer = document.getElementById('modal-container');

  function init() {
    modalContainer = document.getElementById('modal-container');
    if (!modalContainer) {
      console.warn('Modal container not found; will retry on DOMContentLoaded if possible');
      return false;
    }
    // proceed with wiring once the container exists
    return true;
  }
  // We delay wiring event listeners until we have a valid modalContainer
  let _modalBound = false;

  function startBindings() {
    if (_modalBound) return;
    if (!modalContainer) {
      // Shouldn't happen if init() returned true, but guard anyway
      console.error('startBindings called without modalContainer');
      return;
    }

    // HTMX afterSwap イベントリスナー: モーダルコンテンツが挿入された後に自動的に開く
    document.body.addEventListener('htmx:afterSwap', function(event) {
      if (event.detail.target && event.detail.target.id === 'modal-container') {
        // Ensure hx bindings are initialized for newly swapped content
        try {
          if (typeof initHxBindings === 'function') {
            initHxBindings();
          }
        } catch (e) {
          console.warn('[modal] initHxBindings failed', e);
        }
        openModal();
        
        // Markdownプレビューのレンダリング
        if (typeof window.scrapMarkdownRenderInline === 'function') {
          try {
            window.scrapMarkdownRenderInline(modalContainer);
          } catch (e) {
            console.warn('[modal] Markdown rendering failed:', e);
          }
        }
        
        // Lucide iconsの再レンダリング
        if (typeof lucide !== 'undefined' && typeof lucide.createIcons === 'function') {
          lucide.createIcons();
        }
        // Read-more トグルの初期化（モーダル内に追加された要素に対して）
        try {
          initModalReadMore(modalContainer);
        } catch (e) {
          console.warn('[modal] initModalReadMore failed', e);
        }
        // 描画タイミングの差で表示が反映されないことがあるため、
        // requestAnimationFrame で次フレームに再保証するフォールバックを追加
        try {
          requestAnimationFrame(function() {
            try {
              if (modalContainer) {
                const html = (modalContainer.innerHTML || '').trim();
                const cs = window.getComputedStyle(modalContainer);
                // innerHTML が存在するのに display/visibility が非表示なら強制的に表示を再保証
                if (html.length > 0 && (cs.display === 'none' || cs.visibility === 'hidden')) {
                  modalContainer.classList.remove('hidden');
                  try { modalContainer.style.display = 'block'; } catch (e) { /* ignore */ }
                }
              }
            } catch (e) {
              console.warn('[modal] afterSwap rAF inner check failed', e);
            }
          });
        } catch (e) {
          console.warn('[modal] unable to schedule rAF visibility check', e);
        }
      }
    });

    // HTMX responseError イベントリスナー: ネットワークエラー時の処理
    document.body.addEventListener('htmx:responseError', function(event) {
      console.error('[modal] htmx:responseError', event && event.detail && event.detail.target && event.detail.target.id, event && event.detail && event.detail.error);
      if (event.detail.target && event.detail.target.id === 'modal-container') {
        console.error('Modal content fetch error:', event.detail);

        // エラートーストを表示（グローバルなshowNotification関数が利用可能な場合）
        if (typeof showNotification === 'function') {
          showNotification('記事の読み込みに失敗しました', 'error');
        }

        // モーダルを閉じる
        closeModal();
      }
    });

    // HTMX responseError イベントリスナー: DOM構造エラー時の処理
    document.body.addEventListener('htmx:beforeSwap', function(event) {
      // 404や500エラーの場合でも、HTMLレスポンスがあればモーダルに表示する
      if (event.detail.xhr && event.detail.xhr.status >= 400 && event.detail.xhr.status < 600) {
        const contentType = event.detail.xhr.getResponseHeader('content-type');
        if (contentType && contentType.includes('text/html')) {
          // HTMLエラーレスポンスの場合は、モーダルに表示を許可
          event.detail.shouldSwap = true;
          event.detail.isError = false;
        }
      }
    });

    // イベントリスナーの登録
    modalContainer.addEventListener('click', handleOverlayClick);
    modalContainer.addEventListener('click', handleCloseClick);
    document.addEventListener('keydown', handleEscapeKey);
    document.addEventListener('keydown', handleFocusTrap);
    window.addEventListener('popstate', handlePopState);

    // DOMContentLoaded: ディープリンク対応
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', handleDeepLink);
    } else {
      // すでに読み込み済みの場合は即座に実行
      handleDeepLink();
    }

    // グローバルに公開（URL履歴管理で使用）
    window.modalManager = {
      open: openModal,
      close: closeModal
    };

    _modalBound = true;
  }

  if (init()) {
    startBindings();
  } else {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function() {
        if (init()) startBindings();
        else console.error('Modal container not found. Falling back to traditional page navigation.');
      });
    } else {
      console.error('Modal container not found. Falling back to traditional page navigation.');
    }
  }

  // 前回のフォーカス位置を保存
  let previousFocusElement = null;

  /**
   * モーダルを開く
   */
  function openModal() {
    // 現在のフォーカス要素を保存
    previousFocusElement = document.activeElement;

    // モーダルを表示
    try {
      // ensure modalContainer is a direct child of document.body so fixed positioning
      // behaves as expected even if templates wrap content in transformed containers
      try {
        if (modalContainer && modalContainer.parentElement !== document.body) {
          document.body.appendChild(modalContainer);
        }
        // Ensure modal overlays any very-high z-index elements (e.g. toast uses z-[2147483000])
        try {
          // Save previous inline z-index to restore later
          modalContainer._prevZIndex = modalContainer.style.zIndex || '';
          modalContainer.style.zIndex = '2147483001';
        } catch (e) {
          console.warn('[modal] openModal: unable to set zIndex', e);
        }
      } catch (e) {
        console.warn('[modal] openModal: failed to move modalContainer to body', e);
      }
      modalContainer.classList.remove('hidden');
      // テストやレンダリングタイミング差を回避するため、ARIA とインライン表示を明示的に設定
      try {
        // Save previous inline style to restore later (capture BEFORE modifications)
        try { modalContainer._prevInlineStyle = modalContainer.getAttribute('style') || ''; } catch (err) {}
        modalContainer.setAttribute('aria-hidden', 'false');
        modalContainer.style.display = 'block';
        // Force fixed offsets to ensure the overlay covers viewport and is visible
        modalContainer.style.top = '0px';
        modalContainer.style.left = '0px';
        modalContainer.style.right = '0px';
        modalContainer.style.bottom = '0px';
        // Force overlay background color (inline) to ensure dimming even if CSS utilities are missing
        try { modalContainer.style.backgroundColor = 'rgba(243,244,246,0.6)'; } catch (e) {}
      } catch (e) {
        console.warn('[modal] openModal: unable to set inline display/aria', e);
      }
        // Ensure modal dialog respects desktop max width even if CSS utilities fail
        try {
          const dialog = modalContainer.querySelector('[data-modal-dialog]');
          if (dialog && window.matchMedia && window.matchMedia('(min-width: 768px)').matches) {
            // Save previous inline styles so we can restore them on close
            dialog._prevInlineStyle = dialog.getAttribute('style') || '';
            dialog.style.maxWidth = dialog.style.maxWidth || '896px';
            dialog.style.width = 'auto';
            dialog.style.marginLeft = dialog.style.marginLeft || 'auto';
            dialog.style.marginRight = dialog.style.marginRight || 'auto';
          }
        } catch (e) {
          console.warn('[modal] openModal: unable to enforce dialog maxWidth', e);
        }
    } catch (e) {
      console.error('[modal] openModal error:', e, 'modalContainer=', modalContainer);
    }

    // 背景のスクロールを無効化
    try {
      // Save previous body inline style and scroll position so we can restore exactly
      try {
        document.body._prevInlineStyle = document.body.getAttribute('style') || '';
        document.body._prevScrollY = window.scrollY || window.pageYOffset || 0;
      } catch (e) {
        // ignore
      }
      // Lock scroll by fixing body position and preserving scroll offset
      document.body.style.position = 'fixed';
      document.body.style.top = `-${document.body._prevScrollY}px`;
      document.body.style.left = '0';
      document.body.style.right = '0';
      document.body.style.overflow = 'hidden';
      document.body.style.width = '100%';
    } catch (e) {
      try { document.body.style.overflow = 'hidden'; } catch (err) {}
    }

    // モーダル内の最初のフォーカス可能要素にフォーカスを移動
    const firstFocusable = modalContainer.querySelector(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    if (firstFocusable) {
      firstFocusable.focus();
    }
    // Portalize modal footer on open to ensure it's always visible on mobile
    try {
      const dialog = modalContainer.querySelector('[data-modal-dialog]');
      const footer = dialog ? dialog.querySelector('[data-modal-footer]') : null;
      if (footer && !footer._portalized) {
        // remember original parent and next sibling so we can restore
        footer._portalParent = footer.parentElement;
        footer._portalNextSibling = footer.nextSibling;
        // Ensure there's a dedicated portal root at end of body
        let root = document.getElementById('modal-footer-portal-root');
        if (!root) {
          root = document.createElement('div');
          root.id = 'modal-footer-portal-root';
          (document.documentElement || document.body).appendChild(root);
        }
        // Move footer into portal root
        root.appendChild(footer);
        footer.classList.add('modal-footer-portal');
        // Force very high inline z-index and enable pointer events
        try {
          footer.style.zIndex = '2147484000';
          footer.style.pointerEvents = 'auto';
        } catch (e) {}
        // Attach close handler because portalized footer is outside modalContainer delegation
        footer._portalCloseHandler = function(ev) {
          const btn = ev.target && ev.target.closest('[data-modal-close]');
          if (btn) {
            ev.preventDefault();
            closeModal();
          }
        };
        footer.addEventListener('click', footer._portalCloseHandler, true);
        footer._portalized = true;
      }
    } catch (e) {
      console.warn('[modal] portalize footer failed', e);
    }
    try { window.__modal_debug_events = window.__modal_debug_events || []; window.__modal_debug_events.push({ t: Date.now(), ev: 'openModal:end', classes: Array.from(modalContainer.classList) }); console.log('[modal:debug] openModal:end'); } catch (e) {}
  }

  /**
   * モーダルを閉じる
   * @param {boolean} skipHistoryUpdate - URL履歴の更新をスキップ（戻るボタンの場合）
   */
  function closeModal(skipHistoryUpdate = false) {
    // モーダルを非表示
    try {
      modalContainer.classList.add('hidden');
      try { window.__modal_debug_events = window.__modal_debug_events || []; window.__modal_debug_events.push({ t: Date.now(), ev: 'closeModal:added-hidden', classes: Array.from(modalContainer.classList) }); console.log('[modal:debug] closeModal:added-hidden'); } catch (e) {}
    } catch (e) {
      console.error('[modal] closeModal error:', e, 'modalContainer=', modalContainer);
    }

    // モーダルコンテンツをクリア
    // 明示的な aria と inline style を復元してからコンテンツをクリア
    try {
      modalContainer.setAttribute('aria-hidden', 'true');
      // Restore previous inline style if present
      if (modalContainer._prevInlineStyle !== undefined) {
        modalContainer.setAttribute('style', modalContainer._prevInlineStyle);
        delete modalContainer._prevInlineStyle;
      } else {
        modalContainer.style.display = '';
        modalContainer.style.top = '';
        modalContainer.style.left = '';
        modalContainer.style.right = '';
        modalContainer.style.bottom = '';
      }
      // Restore previous zIndex if saved
      try {
        if (modalContainer._prevZIndex !== undefined) {
          modalContainer.style.zIndex = modalContainer._prevZIndex;
          delete modalContainer._prevZIndex;
        }
      } catch (e) {
        console.warn('[modal] closeModal: unable to restore zIndex', e);
      }
    } catch (e) {
      console.warn('[modal] closeModal: unable to restore inline display/aria', e);
    }
    // Delay clearing innerHTML slightly to avoid race conditions where tests
    // or other scripts inspect the container immediately after closing.
    try {
      setTimeout(function() {
        try {
          // Before clearing innerHTML, restore any portalized footer back into dialog
          try {
            const portalFooter = document.body.querySelector('.modal-footer-portal');
            if (portalFooter && portalFooter._portalized && portalFooter._portalParent) {
              // insert before stored nextSibling or append if null
              if (portalFooter._portalNextSibling && portalFooter._portalNextSibling.parentNode === portalFooter._portalParent) {
                portalFooter._portalParent.insertBefore(portalFooter, portalFooter._portalNextSibling);
              } else {
                portalFooter._portalParent.appendChild(portalFooter);
              }
              // Remove portal root if empty
              try {
                const root = document.getElementById('modal-footer-portal-root');
                if (root && root.children.length === 0) root.remove();
              } catch (e) {}
              portalFooter.classList.remove('modal-footer-portal');
              // remove any inline zIndex/pointerEvents we added
              try { portalFooter.style.zIndex = ''; portalFooter.style.pointerEvents = ''; portalFooter.style.transform = ''; portalFooter.style.width = ''; } catch (e) {}
              if (portalFooter._portalCloseHandler) {
                try { portalFooter.removeEventListener('click', portalFooter._portalCloseHandler, true); } catch (e) {}
                delete portalFooter._portalCloseHandler;
              }
              delete portalFooter._portalized;
              delete portalFooter._portalParent;
              delete portalFooter._portalNextSibling;
            }
          } catch (e) {
            console.warn('[modal] restore portal footer failed', e);
          }
          modalContainer.innerHTML = '';
          try { window.__modal_debug_events.push({ t: Date.now(), ev: 'closeModal:cleared-innerHTML' }); console.log('[modal:debug] closeModal:cleared-innerHTML'); } catch (e) {}
        } catch (e) {
          console.warn('[modal] closeModal: unable to clear innerHTML', e);
        }
      }, 60);
    } catch (e) {
      // fallback: immediate clear
      try { modalContainer.innerHTML = ''; } catch (err) {}
    }
    // Remove any dialog inline styles we enforced at openModal
    try {
      const dialog = modalContainer.querySelector('[data-modal-dialog]');
      if (dialog && dialog._prevInlineStyle !== undefined) {
        dialog.setAttribute('style', dialog._prevInlineStyle);
        delete dialog._prevInlineStyle;
      }
    } catch (e) {}

    // 背景のスクロールを復元
    try {
      // Restore previous body inline style and scroll position
      if (document.body._prevInlineStyle !== undefined) {
        document.body.setAttribute('style', document.body._prevInlineStyle);
        const prevY = document.body._prevScrollY || 0;
        try { window.scrollTo(0, prevY); } catch (e) {}
        delete document.body._prevInlineStyle;
        delete document.body._prevScrollY;
      } else {
        document.body.style.overflow = '';
        document.body.style.position = '';
        document.body.style.top = '';
        document.body.style.left = '';
        document.body.style.right = '';
        document.body.style.width = '';
      }
    } catch (e) {
      try { document.body.style.overflow = ''; } catch (err) {}
    }

    // 元のフォーカス位置に戻る
    if (previousFocusElement && typeof previousFocusElement.focus === 'function') {
      previousFocusElement.focus();
    }
    previousFocusElement = null;

    // URL履歴から?doc={id}を削除（popstateの場合はスキップ）
    if (!skipHistoryUpdate) {
      const url = new URL(window.location);
      if (url.searchParams.has('doc')) {
        url.searchParams.delete('doc');
        window.history.pushState({}, '', url);
      }
    }
    try { window.__modal_debug_events = window.__modal_debug_events || []; window.__modal_debug_events.push({ t: Date.now(), ev: 'closeModal:end', classes: Array.from(modalContainer.classList) }); console.log('[modal:debug] closeModal:end'); } catch (e) {}
  }

  /**
   * 閉じるボタンのクリックイベント
   */
  function handleCloseClick(event) {
    const target = event.target;
    // data-modal-close属性を持つ要素、またはその親要素
    const closeButton = target.closest('[data-modal-close]');
    if (closeButton) {
      event.preventDefault();
      closeModal();
    }
  }

  /**
   * オーバーレイクリックでモーダルを閉じる
   * モーダルダイアログ内のクリックでは閉じない
   */
  function handleOverlayClick(event) {
    // モーダルコンテナ自体をクリックした場合のみ閉じる
    // ダイアログ内（data-modal-dialog）のクリックは無視
    try {
      // debug
      try { window.__modal_debug_events = window.__modal_debug_events || []; window.__modal_debug_events.push({ t: Date.now(), ev: 'overlay:click', targetTag: event.target && event.target.tagName, isModalContainer: event.target === modalContainer, closestDialog: !!event.target.closest('[data-modal-dialog]') }); console.log('[modal:debug] overlay click', { isModalContainer: event.target === modalContainer, closestDialog: !!event.target.closest('[data-modal-dialog]') }); } catch (e) {}
    } catch (e) {}
    if (event.target === modalContainer && !event.target.closest('[data-modal-dialog]')) {
      try { modalContainer.setAttribute('data-overlay-clicked', 'true'); } catch (e) {}
      closeModal();
    }
  }

  /**
   * ESCキーでモーダルを閉じる
   */
  function handleEscapeKey(event) {
    if (event.key === 'Escape' && !modalContainer.classList.contains('hidden')) {
      event.preventDefault();
      closeModal();
    }
  }

  /**
   * フォーカストラップ: Tabキーでモーダル内をループ
   */
  function handleFocusTrap(event) {
    if (event.key !== 'Tab' || modalContainer.classList.contains('hidden')) {
      return;
    }

    const focusableElements = modalContainer.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );

    if (focusableElements.length === 0) {
      return;
    }

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    if (event.shiftKey && document.activeElement === firstElement) {
      // Shift+Tab で最初の要素 → 最後の要素へ
      event.preventDefault();
      lastElement.focus();
    } else if (!event.shiftKey && document.activeElement === lastElement) {
      // Tab で最後の要素 → 最初の要素へ
      event.preventDefault();
      firstElement.focus();
    }
  }

  /**
   * ブラウザの戻るボタン対応: popstateイベントでモーダルを閉じる
   */
  function handlePopState(event) {
    const url = new URL(window.location);
    const docId = url.searchParams.get('doc');

    if (!docId && !modalContainer.classList.contains('hidden')) {
      // URLに?doc={id}がなく、モーダルが開いている場合は閉じる
      closeModal(true); // skipHistoryUpdate=trueでURL更新をスキップ
    }
  }

  /**
   * ディープリンク対応: ページロード時に?doc={id}があれば自動的にモーダルを開く
   */
  function handleDeepLink() {
    const url = new URL(window.location);
    const docId = url.searchParams.get('doc');

    if (docId && modalContainer) {
      // HTMXでモーダルコンテンツを取得
      if (typeof htmx !== 'undefined') {
        htmx.ajax('GET', `/api/documents/${docId}/modal`, {
          target: '#modal-container',
          swap: 'innerHTML'
        });
      } else {
        console.warn('[modal] htmx is not available; cannot load modal content via AJAX');
      }
    }
  }

  /**
   * モーダル内の "もっと見る" トグルを初期化する
   * @param {HTMLElement} root
   */
  function initModalReadMore(root) {
    if (!root) return;
    try {
      var toggles = root.querySelectorAll('.modal-readmore-toggle');
      toggles.forEach(function(btn) {
        // 二重バインド防止
        if (btn._readmoreBound) return;
        btn._readmoreBound = true;

        btn.addEventListener('click', function(e) {
          var expanded = btn.getAttribute('aria-expanded') === 'true';
          var preview = btn.closest('.modal-content-wrap').querySelector('.modal-content-preview');
          if (!preview) return;

          if (!expanded) {
            // 展開 - setProperty with priority to override CSS !important
            try {
              preview.style.setProperty('max-height', 'none', 'important');
            } catch (e) {
              preview.style.maxHeight = 'none';
            }
            preview.style.overflow = 'visible';
            btn.textContent = '折りたたむ';
            btn.setAttribute('aria-expanded', 'true');
          } else {
            // 折りたたむ
            try {
              preview.style.setProperty('max-height', '40vh', 'important');
            } catch (e) {
              preview.style.maxHeight = '40vh';
            }
            preview.style.overflow = 'hidden';
            btn.textContent = 'もっと見る';
            btn.setAttribute('aria-expanded', 'false');
            // スクロール位置を先頭に戻す
            try { preview.scrollTop = 0; } catch (e) {}
          }
        });
      });
    } catch (e) {
      console.warn('[modal] initModalReadMore error', e);
    }
  }

  // Note: event listeners and window.modalManager are bound in startBindings()

})();
