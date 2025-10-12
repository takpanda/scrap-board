/**
 * Document Detail Modal - State Management
 *
 * モーダルの開閉状態を管理し、背景スクロールの制御とアクセシビリティ対応を提供
 */

(function() {
  'use strict';

  const modalContainer = document.getElementById('modal-container');
  if (!modalContainer) {
    console.warn('Modal container not found');
    return;
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
    modalContainer.classList.remove('hidden');

    // 背景のスクロールを無効化
    document.body.style.overflow = 'hidden';

    // モーダル内の最初のフォーカス可能要素にフォーカスを移動
    const firstFocusable = modalContainer.querySelector(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    if (firstFocusable) {
      firstFocusable.focus();
    }
  }

  /**
   * モーダルを閉じる
   * @param {boolean} skipHistoryUpdate - URL履歴の更新をスキップ（戻るボタンの場合）
   */
  function closeModal(skipHistoryUpdate = false) {
    // モーダルを非表示
    modalContainer.classList.add('hidden');

    // モーダルコンテンツをクリア
    modalContainer.innerHTML = '';

    // 背景のスクロールを復元
    document.body.style.overflow = '';

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
    if (event.target === modalContainer && !event.target.closest('[data-modal-dialog]')) {
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
      }
    }
  }

  // HTMX afterSwap イベントリスナー: モーダルコンテンツが挿入された後に自動的に開く
  document.body.addEventListener('htmx:afterSwap', function(event) {
    if (event.detail.target && event.detail.target.id === 'modal-container') {
      openModal();
      // Lucide iconsの再レンダリング
      if (typeof lucide !== 'undefined' && typeof lucide.createIcons === 'function') {
        lucide.createIcons();
      }
    }
  });

  // HTMX responseError イベントリスナー: ネットワークエラー時の処理
  document.body.addEventListener('htmx:responseError', function(event) {
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

})();
