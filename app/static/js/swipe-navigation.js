/**
 * Mobile Swipe Navigation Module
 *
 * モバイル環境でのスワイプジェスチャーによる記事ナビゲーション機能を提供します。
 */

/**
 * ViewportDetector
 *
 * ビューポート幅を監視し、モバイル環境（768px未満）かデスクトップ環境（768px以上）かを判定します。
 */
class ViewportDetector {
  /**
   * コンストラクタ
   */
  constructor() {
    this.MOBILE_BREAKPOINT = 768; // Tailwind mdブレークポイント
    this.resizeCallback = null;
    this.resizeTimeoutId = null;
    this.DEBOUNCE_DELAY = 200; // デバウンス遅延時間（ミリ秒）
    this.lastIsMobileState = null; // 前回のモバイル判定状態
  }

  /**
   * モバイル環境判定
   *
   * @returns {boolean} ビューポート幅が768px未満の場合true、それ以外false
   */
  isMobile() {
    return window.innerWidth < this.MOBILE_BREAKPOINT;
  }

  /**
   * リサイズ監視開始
   *
   * ウィンドウリサイズ時にコールバックを発火します。
   * デバウンス処理（200ms）を適用し、連続発火を制御します。
   * モバイル⇔デスクトップ環境切り替え時のみコールバックを発火します。
   *
   * @param {Function} callback - (isMobile: boolean) => void 形式のコールバック関数
   */
  startMonitoring(callback) {
    this.resizeCallback = callback;
    this.lastIsMobileState = this.isMobile(); // 初期状態を記録

    // リサイズイベントリスナーを登録（デバウンス適用）
    this._handleResize = () => {
      // 既存のタイムアウトをクリア
      if (this.resizeTimeoutId) {
        clearTimeout(this.resizeTimeoutId);
      }

      // デバウンス: 200ms後にコールバック実行
      this.resizeTimeoutId = setTimeout(() => {
        const currentIsMobile = this.isMobile();

        // モバイル⇔デスクトップ切り替え時のみコールバック発火
        if (currentIsMobile !== this.lastIsMobileState) {
          this.lastIsMobileState = currentIsMobile;
          if (this.resizeCallback) {
            this.resizeCallback(currentIsMobile);
          }
        }
      }, this.DEBOUNCE_DELAY);
    };

    window.addEventListener('resize', this._handleResize);
  }

  /**
   * リサイズ監視停止
   *
   * リサイズイベントリスナーを解除し、タイムアウトをクリアします。
   */
  stopMonitoring() {
    if (this._handleResize) {
      window.removeEventListener('resize', this._handleResize);
    }

    if (this.resizeTimeoutId) {
      clearTimeout(this.resizeTimeoutId);
      this.resizeTimeoutId = null;
    }

    this.resizeCallback = null;
    this.lastIsMobileState = null;
  }
}

/**
 * SwipeGestureDetector
 *
 * タッチイベント（touchstart、touchmove、touchend）を監視し、スワイプジェスチャーを検出します。
 * スワイプ距離が最小閾値（50px）を超え、水平方向の移動が垂直方向の2倍以上の場合のみスワイプと判定します。
 */
class SwipeGestureDetector {
  /**
   * コンストラクタ
   *
   * @param {HTMLElement} targetElement - スワイプ検出対象の要素
   */
  constructor(targetElement = document.body) {
    this.targetElement = targetElement;
    this.MIN_SWIPE_DISTANCE = 50; // 最小スワイプ距離（px）
    this.HORIZONTAL_RESTRAINT = 2; // 水平方向の移動が垂直方向の何倍以上でスワイプと判定するか
    this.DEBOUNCE_DELAY = 200; // デバウンス遅延時間（ミリ秒）

    // スワイプ状態
    this.startX = 0;
    this.startY = 0;
    this.startTime = 0;
    this.isEnabled = false;
    this.swipeCallback = null;
    this.lastSwipeTime = 0; // デバウンス用の最終スワイプ時刻

    // イベントハンドラのバインド
    this._handleTouchStart = this._handleTouchStart.bind(this);
    this._handleTouchMove = this._handleTouchMove.bind(this);
    this._handleTouchEnd = this._handleTouchEnd.bind(this);
  }

  /**
   * スワイプコールバックを登録
   *
   * @param {Function} callback - (event: SwipeEvent) => void 形式のコールバック関数
   */
  onSwipe(callback) {
    this.swipeCallback = callback;
  }

  /**
   * スワイプ検出を有効化
   */
  enable() {
    if (this.isEnabled) return;

    this.targetElement.addEventListener('touchstart', this._handleTouchStart, { passive: true });
    this.targetElement.addEventListener('touchmove', this._handleTouchMove, { passive: true });
    this.targetElement.addEventListener('touchend', this._handleTouchEnd, { passive: true });
    this.isEnabled = true;
  }

  /**
   * スワイプ検出を無効化
   */
  disable() {
    if (!this.isEnabled) return;

    this.targetElement.removeEventListener('touchstart', this._handleTouchStart);
    this.targetElement.removeEventListener('touchmove', this._handleTouchMove);
    this.targetElement.removeEventListener('touchend', this._handleTouchEnd);
    this.isEnabled = false;
  }

  /**
   * touchstartイベントハンドラ
   *
   * @param {TouchEvent} event - タッチイベント
   * @private
   */
  _handleTouchStart(event) {
    if (!this.isEnabled || event.touches.length === 0) return;

    const touch = event.touches[0];
    this.startX = touch.clientX;
    this.startY = touch.clientY;
    this.startTime = Date.now();
  }

  /**
   * touchmoveイベントハンドラ
   *
   * @param {TouchEvent} event - タッチイベント
   * @private
   */
  _handleTouchMove(event) {
    if (!this.isEnabled) return;
    // touchmoveでは特別な処理は不要（将来的にインジケーター更新に使用）
  }

  /**
   * touchendイベントハンドラ
   *
   * @param {TouchEvent} event - タッチイベント
   * @private
   */
  _handleTouchEnd(event) {
    if (!this.isEnabled || event.changedTouches.length === 0) return;

    const touch = event.changedTouches[0];
    const endX = touch.clientX;
    const endY = touch.clientY;
    const endTime = Date.now();

    // スワイプ距離と方向を計算
    const deltaX = endX - this.startX;
    const deltaY = endY - this.startY;
    const distance = Math.abs(deltaX);
    const verticalDistance = Math.abs(deltaY);
    const duration = endTime - this.startTime;

    // デバウンス処理: 前回のスワイプから200ms以内の場合は無視
    if (endTime - this.lastSwipeTime < this.DEBOUNCE_DELAY) {
      return;
    }

    // 水平方向の移動が垂直方向の2倍以上かチェック（horizontal restraint）
    if (distance < verticalDistance * this.HORIZONTAL_RESTRAINT) {
      return; // 垂直方向の移動が大きい場合はスワイプと判定しない
    }

    // スワイプ距離が最小閾値を超えているかチェック
    if (distance < this.MIN_SWIPE_DISTANCE) {
      return; // 閾値未満のスワイプは無視
    }

    // スワイプ方向を決定
    const direction = deltaX > 0 ? 'right' : 'left';

    // スワイプイベントオブジェクトを生成
    const swipeEvent = {
      direction: direction,
      distance: distance,
      duration: duration
    };

    // デバウンス用に最終スワイプ時刻を更新
    this.lastSwipeTime = endTime;

    // コールバックを発火
    if (this.swipeCallback) {
      this.swipeCallback(swipeEvent);
    }
  }
}

/**
 * DocumentListCache
 *
 * ドキュメント一覧ページから記事IDリストを取得し、セッションストレージでキャッシュします。
 * 現在の記事IDから次/前の記事IDを取得する機能を提供します。
 */
class DocumentListCache {
  /**
   * コンストラクタ
   */
  constructor() {
    this.CACHE_KEY = 'scrapboard:document_list';
  }

  /**
   * ドキュメント一覧ページの記事IDリストをセッションストレージに保存
   *
   * @param {number[]} documentIds - 記事IDリスト
   * @param {Object} filterParams - フィルタパラメータ（category, tag, query, sort）
   * @throws {Error} 空配列、不正な型、重複IDの場合はエラーをスロー
   */
  saveDocumentList(documentIds, filterParams = {}) {
    // 空配列禁止
    if (!Array.isArray(documentIds) || documentIds.length === 0) {
      throw new Error('documentIds must be a non-empty array');
    }

    // 数値型チェック（正の整数のみ）
    if (!documentIds.every(id => Number.isInteger(id) && id > 0)) {
      throw new Error('All document IDs must be positive integers');
    }

    // 重複ID禁止
    const uniqueIds = new Set(documentIds);
    if (uniqueIds.size !== documentIds.length) {
      throw new Error('Duplicate document IDs are not allowed');
    }

    // キャッシュデータを作成
    const cacheData = {
      documentIds: documentIds,
      timestamp: Date.now(),
      filterParams: filterParams
    };

    // セッションストレージに保存
    sessionStorage.setItem(this.CACHE_KEY, JSON.stringify(cacheData));
  }

  /**
   * 現在の記事IDとスワイプ方向から隣接記事IDを取得
   *
   * @param {number} currentId - 現在の記事ID
   * @param {string} direction - スワイプ方向（'next' または 'prev'）
   * @returns {number|null} 隣接記事ID。存在しない場合はnull
   */
  getAdjacentDocumentId(currentId, direction) {
    // キャッシュが存在しない場合はnullを返す
    const cached = sessionStorage.getItem(this.CACHE_KEY);
    if (!cached) {
      return null;
    }

    // キャッシュデータをパース
    const { documentIds } = JSON.parse(cached);

    // 現在の記事IDがリスト内に存在するかチェック
    const currentIndex = documentIds.indexOf(currentId);
    if (currentIndex === -1) {
      return null;
    }

    // 次/前のインデックスを計算
    const nextIndex = direction === 'next' ? currentIndex + 1 : currentIndex - 1;

    // リスト端チェック
    if (nextIndex < 0 || nextIndex >= documentIds.length) {
      return null;
    }

    // 隣接記事IDを返す
    return documentIds[nextIndex];
  }

  /**
   * キャッシュの存在確認
   *
   * @returns {boolean} キャッシュが存在する場合true、それ以外false
   */
  hasCachedList() {
    return sessionStorage.getItem(this.CACHE_KEY) !== null;
  }

  /**
   * キャッシュクリア
   */
  clearCache() {
    sessionStorage.removeItem(this.CACHE_KEY);
  }

  /**
   * キャッシュデータ全体を取得（デバッグ・テスト用）
   *
   * @returns {Object|null} キャッシュデータ。存在しない場合はnull
   */
  getCachedData() {
    const cached = sessionStorage.getItem(this.CACHE_KEY);
    return cached ? JSON.parse(cached) : null;
  }
}

/**
 * CardFocusManager
 *
 * ドキュメント一覧ページでの記事カードフォーカス状態を管理し、スワイプによるフォーカス移動を制御します。
 */
class CardFocusManager {
  /**
   * コンストラクタ
   */
  constructor() {
    this.currentFocusIndex = -1;
    this.cards = [];
    this.FOCUS_CLASS = 'focus-highlight';
  }

  /**
   * 初期化
   *
   * ドキュメント一覧ページの記事カード要素を取得し、先頭カードにフォーカスを設定します。
   */
  initialize() {
    // 記事カード要素を取得（data-document-id属性を持つ要素）
    this.cards = Array.from(document.querySelectorAll('[data-document-id]'));

    if (this.cards.length === 0) {
      console.warn('No document cards found for focus management');
      return;
    }

    // 先頭カードにフォーカス設定
    this.setFocus(0);
  }

  /**
   * 指定インデックスのカードにフォーカス設定
   *
   * @param {number} index - フォーカスを設定するカードのインデックス
   */
  setFocus(index) {
    // 範囲チェック
    if (index < 0 || index >= this.cards.length) {
      return;
    }

    // 前のカードからハイライトクラスを削除
    if (this.currentFocusIndex >= 0 && this.currentFocusIndex < this.cards.length) {
      this.cards[this.currentFocusIndex].classList.remove(this.FOCUS_CLASS);
    }

    // 新しいカードにハイライトクラスを追加
    this.currentFocusIndex = index;
    this.cards[index].classList.add(this.FOCUS_CLASS);

    // スクロール（スムーズスクロール、画面中央に配置）
    this.cards[index].scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  /**
   * 現在フォーカスされているカードのインデックスを取得
   *
   * @returns {number} 現在のフォーカスインデックス
   */
  getCurrentFocusIndex() {
    return this.currentFocusIndex;
  }

  /**
   * スワイプ方向に応じてフォーカス移動
   *
   * @param {string} direction - スワイプ方向（'next' または 'prev'）
   * @returns {boolean} フォーカス移動成功時true、リスト端で移動できない場合false
   */
  moveFocus(direction) {
    const nextIndex = direction === 'next' ? this.currentFocusIndex + 1 : this.currentFocusIndex - 1;

    // リスト端チェック
    if (nextIndex < 0 || nextIndex >= this.cards.length) {
      // リスト端到達時、フォーカスは移動しない
      return false;
    }

    this.setFocus(nextIndex);
    return true;
  }

  /**
   * フォーカスカードをタップして詳細モーダルを開く（将来的な拡張用）
   */
  openFocusedCard() {
    if (this.currentFocusIndex < 0 || this.currentFocusIndex >= this.cards.length) {
      return;
    }

    const focusedCard = this.cards[this.currentFocusIndex];
    // カード内のリンク要素をクリック
    const link = focusedCard.querySelector('a');
    if (link) {
      link.click();
    }
  }
}

// グローバルスコープにViewportDetectorインスタンスを公開（テスト用）
window.viewportDetector = new ViewportDetector();

// グローバルスコープにSwipeGestureDetectorインスタンスを公開（テスト用）
window.swipeDetector = new SwipeGestureDetector();
window.swipeDetector.enable(); // デフォルトで有効化

// グローバルスコープにDocumentListCacheインスタンスを公開（テスト用）
window.documentListCache = new DocumentListCache();

// グローバルスコープにCardFocusManagerインスタンスを公開（テスト用）
window.cardFocusManager = new CardFocusManager();

console.log('ViewportDetector initialized');
console.log('SwipeGestureDetector initialized');
console.log('DocumentListCache initialized');
console.log('CardFocusManager initialized');
