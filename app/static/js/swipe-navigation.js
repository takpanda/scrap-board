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
 * タッチイベントを監視し、スワイプジェスチャーを検出します。
 * 水平方向のスワイプ距離が垂直方向の2倍以上の場合のみスワイプと判定し、
 * 縦スクロールと区別します。
 */
class SwipeGestureDetector {
  /**
   * コンストラクタ
   *
   * @param {HTMLElement} targetElement - スワイプを検出する対象要素
   * @param {Function} callback - スワイプ検出時のコールバック関数 (event: SwipeEvent) => void
   */
  constructor(targetElement, callback) {
    this.targetElement = targetElement;
    this.callback = callback;
    this.DISTANCE_THRESHOLD = 50; // スワイプとして認識する最小距離（px）
    this.HORIZONTAL_RESTRAINT = 2; // 水平/垂直比率（水平距離が垂直距離の2倍以上でスワイプと判定）
    this.DEBOUNCE_DELAY = 200; // デバウンス遅延時間（ミリ秒）
    
    this.startX = 0;
    this.startY = 0;
    this.startTime = 0;
    this.isEnabled = false;
    this.lastSwipeTime = 0; // 最後のスワイプ発火時刻（デバウンス用）
    
    // イベントハンドラをバインド
    this._handleTouchStart = this.handleTouchStart.bind(this);
    this._handleTouchMove = this.handleTouchMove.bind(this);
    this._handleTouchEnd = this.handleTouchEnd.bind(this);
  }
  
  /**
   * スワイプ検出を有効化
   *
   * タッチイベントリスナーを登録します。
   */
  enable() {
    if (this.isEnabled) return;
    
    this.targetElement.addEventListener('touchstart', this._handleTouchStart, { passive: false });
    this.targetElement.addEventListener('touchmove', this._handleTouchMove, { passive: false });
    this.targetElement.addEventListener('touchend', this._handleTouchEnd, { passive: false });
    
    this.isEnabled = true;
  }
  
  /**
   * スワイプ検出を無効化
   *
   * タッチイベントリスナーを解除します。
   */
  disable() {
    if (!this.isEnabled) return;
    
    this.targetElement.removeEventListener('touchstart', this._handleTouchStart);
    this.targetElement.removeEventListener('touchmove', this._handleTouchMove);
    this.targetElement.removeEventListener('touchend', this._handleTouchEnd);
    
    this.isEnabled = false;
  }
  
  /**
   * タッチ開始イベントハンドラ
   *
   * 初期タッチ位置とタイムスタンプを記録します。
   *
   * @param {TouchEvent} event - タッチイベント
   */
  handleTouchStart(event) {
    if (!this.isEnabled || event.touches.length === 0) return;
    
    const touch = event.touches[0];
    this.startX = touch.clientX;
    this.startY = touch.clientY;
    this.startTime = Date.now();
  }
  
  /**
   * タッチ移動イベントハンドラ
   *
   * 現在のタッチ位置を取得し、スワイプ距離をリアルタイム計算します。
   *
   * @param {TouchEvent} event - タッチイベント
   */
  handleTouchMove(event) {
    if (!this.isEnabled || event.touches.length === 0) return;
    
    // スワイプ検出中は、必要に応じてデフォルト動作をキャンセル
    // （垂直スクロールとの競合を避けるため、水平スワイプの場合のみ）
    const touch = event.touches[0];
    const deltaX = Math.abs(touch.clientX - this.startX);
    const deltaY = Math.abs(touch.clientY - this.startY);
    
    // 水平方向の移動が垂直方向の移動の2倍以上の場合、スワイプと判定
    if (deltaX > deltaY * this.HORIZONTAL_RESTRAINT && deltaX > this.DISTANCE_THRESHOLD) {
      // スワイプジェスチャーと判定された場合、デフォルトの垂直スクロールを防止
      event.preventDefault();
    }
  }
  
  /**
   * タッチ終了イベントハンドラ
   *
   * 最終スワイプ距離を計算し、閾値を超えた場合のみスワイプイベントを発火します。
   *
   * @param {TouchEvent} event - タッチイベント
   */
  handleTouchEnd(event) {
    if (!this.isEnabled || event.changedTouches.length === 0) return;
    
    const touch = event.changedTouches[0];
    const endX = touch.clientX;
    const endY = touch.clientY;
    const endTime = Date.now();
    
    // スワイプ距離と継続時間を計算
    const deltaX = endX - this.startX;
    const deltaY = endY - this.startY;
    const distance = Math.abs(deltaX);
    const duration = endTime - this.startTime;
    
    // 水平方向の移動距離が垂直方向の移動距離の2倍以上かチェック
    const isHorizontal = Math.abs(deltaX) > Math.abs(deltaY) * this.HORIZONTAL_RESTRAINT;
    
    // スワイプ距離が閾値を超え、かつ水平方向の移動である場合のみスワイプイベント発火
    if (distance >= this.DISTANCE_THRESHOLD && isHorizontal) {
      // デバウンス処理: 前回のスワイプから一定時間経過している場合のみ発火
      const now = Date.now();
      if (now - this.lastSwipeTime >= this.DEBOUNCE_DELAY) {
        this.lastSwipeTime = now;
        
        // スワイプ方向を判定
        const direction = deltaX > 0 ? 'right' : 'left';
        
        // SwipeEventオブジェクトを生成してコールバック呼び出し
        const swipeEvent = {
          direction: direction,
          distance: distance,
          duration: duration
        };
        
        if (this.callback) {
          this.callback(swipeEvent);
        }
      }
    }
    
    // 状態をリセット
    this.startX = 0;
    this.startY = 0;
    this.startTime = 0;
  }
}

/**
 * DocumentListCache
 *
 * ドキュメント一覧ページの記事IDリストをセッションストレージにキャッシュし、
 * 現在の記事IDから隣接する記事IDを取得する機能を提供します。
 */
class DocumentListCache {
  /**
   * コンストラクタ
   */
  constructor() {
    this.STORAGE_KEY = 'scrapboard:document_list';
  }
  
  /**
   * 記事IDリストをセッションストレージに保存
   *
   * @param {number[]} documentIds - 記事IDの配列
   * @param {Object} filterParams - フィルタパラメータ（オプション）
   * @param {string} filterParams.category - カテゴリフィルタ
   * @param {string} filterParams.tag - タグフィルタ
   * @param {string} filterParams.query - 検索クエリ
   * @param {string} filterParams.sort - ソート順
   * @throws {Error} 空配列、重複ID、非数値IDが含まれる場合
   */
  saveDocumentList(documentIds, filterParams = {}) {
    // 検証: 空配列禁止
    if (!Array.isArray(documentIds) || documentIds.length === 0) {
      throw new Error('記事IDリストは空配列禁止です (Document ID list cannot be empty)');
    }
    
    // 検証: 数値型チェック
    for (const id of documentIds) {
      if (typeof id !== 'number' || !Number.isInteger(id)) {
        throw new Error(`記事IDは数値型である必要があります (Document ID must be a number): ${id}`);
      }
    }
    
    // 検証: 重複ID禁止
    const uniqueIds = new Set(documentIds);
    if (uniqueIds.size !== documentIds.length) {
      throw new Error('記事IDリストに重複があります (Duplicate document IDs found)');
    }
    
    // キャッシュオブジェクトを生成
    const cacheData = {
      documentIds: documentIds,
      timestamp: Date.now(),
      filterParams: filterParams
    };
    
    // セッションストレージに保存
    try {
      sessionStorage.setItem(this.STORAGE_KEY, JSON.stringify(cacheData));
    } catch (error) {
      console.error('セッションストレージへの保存に失敗:', error);
      throw new Error('Failed to save document list to session storage');
    }
  }
  
  /**
   * 現在の記事IDから次/前の記事IDを取得
   *
   * @param {number} currentId - 現在の記事ID
   * @param {'next'|'prev'} direction - 取得方向（next: 次、prev: 前）
   * @returns {number|null} 隣接記事ID、存在しない場合はnull
   */
  getAdjacentDocumentId(currentId, direction) {
    // キャッシュデータを取得
    const cacheData = this._getCacheData();
    if (!cacheData) {
      return null;
    }
    
    const { documentIds } = cacheData;
    
    // 現在の記事IDのインデックスを取得
    const currentIndex = documentIds.indexOf(currentId);
    
    // 現在の記事IDがリスト内に存在しない場合
    if (currentIndex === -1) {
      return null;
    }
    
    // 隣接記事のインデックスを計算
    let adjacentIndex;
    if (direction === 'next') {
      adjacentIndex = currentIndex + 1;
    } else if (direction === 'prev') {
      adjacentIndex = currentIndex - 1;
    } else {
      throw new Error(`Invalid direction: ${direction}. Must be 'next' or 'prev'.`);
    }
    
    // インデックスが範囲外の場合はnullを返す
    if (adjacentIndex < 0 || adjacentIndex >= documentIds.length) {
      return null;
    }
    
    // 隣接記事IDを返す
    return documentIds[adjacentIndex];
  }
  
  /**
   * キャッシュの存在確認
   *
   * @returns {boolean} キャッシュが存在する場合true、それ以外false
   */
  hasCachedList() {
    const cacheData = this._getCacheData();
    return cacheData !== null;
  }
  
  /**
   * キャッシュクリア
   *
   * セッションストレージから記事リストキャッシュを削除します。
   */
  clearCache() {
    try {
      sessionStorage.removeItem(this.STORAGE_KEY);
    } catch (error) {
      console.error('セッションストレージからの削除に失敗:', error);
    }
  }
  
  /**
   * セッションストレージからキャッシュデータを取得（内部用）
   *
   * @returns {Object|null} キャッシュデータ、存在しない場合はnull
   * @private
   */
  _getCacheData() {
    try {
      const cachedJson = sessionStorage.getItem(this.STORAGE_KEY);
      if (!cachedJson) {
        return null;
      }
      
      const cacheData = JSON.parse(cachedJson);
      
      // キャッシュデータの妥当性チェック
      if (!cacheData.documentIds || !Array.isArray(cacheData.documentIds)) {
        console.warn('無効なキャッシュデータが検出されました');
        return null;
      }
      
      return cacheData;
    } catch (error) {
      console.error('セッションストレージからの読み込みに失敗:', error);
      return null;
    }
  }
}

/**
 * CardFocusManager
 *
 * ドキュメント一覧ページでの記事カードフォーカス状態を管理し、
 * スワイプによるフォーカス移動を制御します。
 */
class CardFocusManager {
  /**
   * コンストラクタ
   */
  constructor() {
    this.cardElements = [];
    this.currentFocusIndex = 0;
    this.FOCUS_HIGHLIGHT_CLASS = 'focus-highlight';
  }
  
  /**
   * 初期化
   *
   * ドキュメント一覧ページの記事カード要素を取得し、先頭カードにフォーカスを設定します。
   */
  initialize() {
    // ドキュメントカード要素を取得
    this.cardElements = Array.from(document.querySelectorAll('.document-card'));
    
    if (this.cardElements.length === 0) {
      console.warn('記事カードが見つかりません');
      return;
    }
    
    // 先頭カードに初期フォーカスを設定
    this.currentFocusIndex = 0;
    this.setFocus(0);
  }
  
  /**
   * スワイプ方向に応じてフォーカス移動
   *
   * @param {'next'|'prev'} direction - フォーカス移動方向（next: 次、prev: 前）
   * @returns {boolean} フォーカス移動が成功した場合true、失敗した場合false
   */
  moveFocus(direction) {
    if (this.cardElements.length === 0) {
      return false;
    }
    
    let newIndex;
    if (direction === 'next') {
      newIndex = this.currentFocusIndex + 1;
    } else if (direction === 'prev') {
      newIndex = this.currentFocusIndex - 1;
    } else {
      console.error(`Invalid direction: ${direction}`);
      return false;
    }
    
    // インデックスが範囲外の場合は移動失敗
    if (newIndex < 0 || newIndex >= this.cardElements.length) {
      return false;
    }
    
    // フォーカスを移動
    this.setFocus(newIndex);
    return true;
  }
  
  /**
   * 指定インデックスのカードにフォーカスを設定
   *
   * @param {number} index - フォーカスを設定するカードのインデックス
   */
  setFocus(index) {
    if (index < 0 || index >= this.cardElements.length) {
      console.error(`Invalid index: ${index}`);
      return;
    }
    
    // 前のカードからフォーカスハイライトを削除
    if (this.currentFocusIndex >= 0 && this.currentFocusIndex < this.cardElements.length) {
      const previousCard = this.cardElements[this.currentFocusIndex];
      if (previousCard) {
        previousCard.classList.remove(this.FOCUS_HIGHLIGHT_CLASS);
      }
    }
    
    // 新しいカードにフォーカスハイライトを追加
    const newCard = this.cardElements[index];
    if (newCard) {
      newCard.classList.add(this.FOCUS_HIGHLIGHT_CLASS);
      
      // カードをビューポート内にスクロール
      this._scrollCardIntoView(newCard);
    }
    
    // 現在のフォーカスインデックスを更新
    this.currentFocusIndex = index;
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
   * フォーカスカードをビューポート内にスクロール（内部用）
   *
   * @param {HTMLElement} cardElement - スクロール対象のカード要素
   * @private
   */
  _scrollCardIntoView(cardElement) {
    if (!cardElement) {
      return;
    }
    
    try {
      cardElement.scrollIntoView({
        behavior: 'smooth',
        block: 'center'
      });
    } catch (error) {
      // scrollIntoViewがサポートされていない環境のフォールバック
      try {
        cardElement.scrollIntoView();
      } catch (fallbackError) {
        console.warn('scrollIntoViewの実行に失敗:', fallbackError);
      }
    }
  }
  
  /**
   * フォーカスされたカードをタップして詳細モーダルを開く
   *
   * 現在フォーカスされているカードをクリックしてモーダルを開きます。
   */
  openFocusedCard() {
    if (this.currentFocusIndex < 0 || this.currentFocusIndex >= this.cardElements.length) {
      console.warn('フォーカスされたカードが存在しません');
      return;
    }
    
    const focusedCard = this.cardElements[this.currentFocusIndex];
    if (focusedCard) {
      // カード内のリンク要素をクリック
      const linkElement = focusedCard.querySelector('a');
      if (linkElement) {
        linkElement.click();
      } else {
        // リンクが見つからない場合、カード自体をクリック
        focusedCard.click();
      }
    }
  }
}

// グローバルスコープにViewportDetectorインスタンスを公開（テスト用）
window.viewportDetector = new ViewportDetector();

console.log('ViewportDetector initialized');
