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
   */
  function closeModal() {
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

  // イベントリスナーの登録
  modalContainer.addEventListener('click', handleOverlayClick);
  modalContainer.addEventListener('click', handleCloseClick);
  document.addEventListener('keydown', handleEscapeKey);
  document.addEventListener('keydown', handleFocusTrap);

  // グローバルに公開（URL履歴管理で使用）
  window.modalManager = {
    open: openModal,
    close: closeModal
  };

})();
