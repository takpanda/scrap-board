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

// グローバルスコープにViewportDetectorインスタンスを公開（テスト用）
window.viewportDetector = new ViewportDetector();

console.log('ViewportDetector initialized');
