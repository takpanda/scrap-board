(function (window, document) {
    "use strict";

    var STORAGE_KEY = "scrapBoard:documents-sort";
    var DEFAULT_SORT = "recent";
    var PERSONALIZED_SORT = "personalized";
    var FETCH_ENDPOINT = "/api/documents";
    var COMPONENT_ORDER = ["similarity", "category", "domain", "freshness"];
    var COMPONENT_LABELS = {
        similarity: "内容の近さ",
        category: "カテゴリ一致",
        domain: "ドメイン親和性",
        freshness: "鮮度"
    };
    var FEEDBACK_SESSION_KEY = "scrapBoard:feedback-session-id";
    var FEEDBACK_SUBMITTED_KEY = "scrapBoard:feedback-submitted";
    var feedbackSessionMemo = null;
    var feedbackSubmittedMemo = null;

    function generateRandomId() {
        if (window.crypto && typeof window.crypto.randomUUID === "function") {
            return window.crypto.randomUUID();
        }
        try {
            var array = new Uint32Array(4);
            window.crypto.getRandomValues(array);
            return Array.prototype.map.call(array, function (value) {
                return value.toString(16).slice(-4);
            }).join("-");
        } catch (err) {
            return "session-" + Date.now().toString(36);
        }
    }

    function getFeedbackSessionId() {
        if (feedbackSessionMemo) {
            return feedbackSessionMemo;
        }
        var token = null;
        try {
            token = sessionStorage.getItem(FEEDBACK_SESSION_KEY);
        } catch (err) {
            token = null;
        }
        if (!token) {
            if (typeof window.__scrapFeedbackSession === "string") {
                token = window.__scrapFeedbackSession;
            } else {
                token = generateRandomId();
            }
        }
        feedbackSessionMemo = token;
        try {
            sessionStorage.setItem(FEEDBACK_SESSION_KEY, token);
        } catch (err) {
            window.__scrapFeedbackSession = token;
        }
        return token;
    }

    function ensureSessionFieldValue() {
        var field = document.getElementById("personalized-feedback-session");
        if (field) {
            field.value = getFeedbackSessionId() || "";
        }
    }

    function loadSubmittedSet() {
        if (feedbackSubmittedMemo instanceof Set) {
            return feedbackSubmittedMemo;
        }
        var stored = [];
        try {
            var raw = sessionStorage.getItem(FEEDBACK_SUBMITTED_KEY);
            if (raw) {
                stored = JSON.parse(raw);
            }
        } catch (err) {
            stored = Array.isArray(window.__scrapFeedbackSubmitted)
                ? window.__scrapFeedbackSubmitted
                : [];
        }
        if (!Array.isArray(stored)) {
            stored = [];
        }
        feedbackSubmittedMemo = new Set(stored);
        return feedbackSubmittedMemo;
    }

    function persistSubmittedSet() {
        var set = loadSubmittedSet();
        var payload = Array.from(set);
        try {
            sessionStorage.setItem(FEEDBACK_SUBMITTED_KEY, JSON.stringify(payload));
        } catch (err) {
            window.__scrapFeedbackSubmitted = payload;
        }
    }

    function markFeedbackSubmitted(documentId) {
        if (!documentId) {
            return;
        }
        var set = loadSubmittedSet();
        if (!set.has(documentId)) {
            set.add(documentId);
            persistSubmittedSet();
        }
    }

    function hasFeedbackSubmitted(documentId) {
        if (!documentId) {
            return false;
        }
        return loadSubmittedSet().has(documentId);
    }

    function renderFeedbackAsCompleted(container, message, state) {
        if (!container) {
            return;
        }
        var safeMessage = message || "フィードバックを受け付けました。";
        var paletteClasses = state === "submitted"
            ? " bg-emerald/10 text-emerald-700 border border-emerald/30"
            : " bg-mist/70 text-graphite border border-mist";
        container.className = "flex items-center gap-2 text-xs font-medium rounded-lg px-3 py-2" + paletteClasses;
        container.setAttribute("data-feedback-state", state);
        container.setAttribute("data-feedback-message", safeMessage);
        container.innerHTML = '' +
            '<i data-lucide="' + (state === "submitted" ? "smile" : "info") + '" class="w-4 h-4" aria-hidden="true"></i>' +
            '<span>' + safeMessage + '</span>';
        if (typeof window.createIcons === "function") {
            window.createIcons();
        }
    }

    function handleFeedbackFetch(button) {
        if (!button || button.dataset.feedbackLoading === "true") {
            return;
        }
        var container = button.closest("[data-personalized-feedback-container]");
        if (!container) {
            return;
        }
        var documentId = container.getAttribute("data-document-id");
        if (!documentId) {
            return;
        }
        button.dataset.feedbackLoading = "true";
        button.classList.add("opacity-60", "pointer-events-none");

        var sessionId = getFeedbackSessionId();
        var payload = {
            reason: button.getAttribute("data-feedback-reason") || "low_relevance",
            session_token: sessionId
        };

        fetch("/api/documents/" + encodeURIComponent(documentId) + "/personalized-feedback", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Accept: "application/json"
            },
            body: JSON.stringify(payload)
        })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error("feedback request failed");
                }
                return response.json();
            })
            .then(function (data) {
                if (!data || !data.state) {
                    return;
                }
                if (data.state === "submitted" || data.state === "duplicate") {
                    markFeedbackSubmitted(documentId);
                }
                renderFeedbackAsCompleted(container, data.message, data.state);
                if (typeof window.showNotification === "function") {
                    var tone = data.state === "submitted" ? "success" : "info";
                    window.showNotification(data.message || "フィードバックを受け付けました。", tone);
                }
            })
            .catch(function () {
                button.classList.remove("opacity-60", "pointer-events-none");
                if (typeof window.showNotification === "function") {
                    window.showNotification("フィードバックの送信に失敗しました。時間をおいて再試行してください。", "error");
                }
            })
            .finally(function () {
                delete button.dataset.feedbackLoading;
            });
    }

    function initFeedbackUI(root) {
        ensureSessionFieldValue();
        var scope = root && root.querySelectorAll ? root : document;
        var containers = scope.querySelectorAll("[data-personalized-feedback-container]");
        if (!containers || containers.length === 0) {
            return;
        }
        Array.prototype.forEach.call(containers, function (container) {
            var documentId = container.getAttribute("data-document-id");
            if (!documentId) {
                return;
            }
            if (hasFeedbackSubmitted(documentId)) {
                var existingState = container.getAttribute("data-feedback-state");
                if (existingState !== "submitted" && existingState !== "duplicate") {
                    renderFeedbackAsCompleted(container, "フィードバック済みです。", "duplicate");
                }
                return;
            }
            container.setAttribute("data-feedback-state", "pending");
            var button = container.querySelector("[data-personalized-feedback-button]");
            if (!button || button.dataset.feedbackBound === "true") {
                return;
            }
            button.dataset.feedbackBound = "true";
            if (!window.htmx) {
                button.addEventListener("click", function (event) {
                    event.preventDefault();
                    handleFeedbackFetch(button);
                });
            } else {
                button.addEventListener("click", function () {
                    ensureSessionFieldValue();
                });
            }
        });
    }

        function forEachNode(list, callback) {
            if (!list || typeof callback !== "function") {
                return;
            }
            Array.prototype.forEach.call(list, callback);
        }

    function isNumber(value) {
        return typeof value === "number" && !isNaN(value);
    }

    function safeFormatPercent(value) {
        if (!isNumber(value)) {
            return "";
        }
        return Math.round(value * 100);
    }

    function parseIsoTimestamp(isoString) {
        if (typeof isoString !== "string" || !isoString) {
            return null;
        }
        var normalized = isoString.trim();
        // タイムゾーン情報が明示されていない場合はUTCとして解釈する
        if (!/[zZ]|[+-]\d{2}:?\d{2}$/.test(normalized)) {
            normalized = normalized + "Z";
        }
        var date = new Date(normalized);
        if (isNaN(date.getTime())) {
            date = new Date(isoString);
        }
        return isNaN(date.getTime()) ? null : date;
    }

    function formatTimestamp(isoString) {
        if (!isoString) {
            return "";
        }
        try {
            var date = parseIsoTimestamp(isoString);
            if (!date) {
                return "";
            }
            return new Intl.DateTimeFormat("ja-JP", {
                month: "numeric",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
                timeZone: "Asia/Tokyo"
            }).format(date);
        } catch (err) {
            return "";
        }
    }

    function PersonalizedSortController() {
        this.controlsRoot = document.querySelector("[data-sort-controls]");
        this.container = document.getElementById("documents-container");
        this.grid = this.container ? this.container.querySelector("[data-documents-grid]") : null;
        if (!this.controlsRoot || !this.container) {
            return;
        }

        this.statusEl = this.controlsRoot.querySelector("[data-personalized-status]");
        this.toggleGroup = this.controlsRoot.querySelector("[role='group']");
        this.buttons = Array.prototype.slice.call(this.controlsRoot.querySelectorAll("[data-sort-toggle]"));
        this.activeClasses = this.toggleGroup && this.toggleGroup.dataset.sortActiveClass
            ? this.toggleGroup.dataset.sortActiveClass.split(/\s+/).filter(Boolean)
            : ["bg-white", "text-ink", "shadow-sm", "border", "border-emerald"];
        this.inactiveClasses = this.toggleGroup && this.toggleGroup.dataset.sortInactiveClass
            ? this.toggleGroup.dataset.sortInactiveClass.split(/\s+/).filter(Boolean)
            : ["text-graphite/70"];

        this.originalOrderIds = [];
        this.abortController = null;
        this.serverFallbackInFlight = false;
        this.currentSort = this.loadPreference();
        this.refreshStructure({ updateBaseline: true });

        this.bindEvents();
        this.updateToggleUI();

        if (this.currentSort === PERSONALIZED_SORT) {
            this.applyPersonalizedSort();
        } else {
            this.setStatus("default");
        }

        this.observeHtmx();
    }

    PersonalizedSortController.prototype.getArticleElements = function () {
        if (!this.grid) {
            return [];
        }
        var children = this.grid.children;
        if (!children || children.length === 0) {
            return [];
        }
        return Array.prototype.filter.call(children, function (child) {
            return child && child.nodeType === 1 && child.hasAttribute("data-document-id");
        });
    };

    PersonalizedSortController.prototype.refreshStructure = function (options) {
        var opts = options || {};
        var shouldUpdateBaseline = !!opts.updateBaseline;
        this.container = document.getElementById("documents-container");
        this.grid = this.container ? this.container.querySelector("[data-documents-grid]") : null;
        if (!this.grid) {
            if (shouldUpdateBaseline) {
                this.originalOrderIds = [];
            }
            return;
        }
        var articles = this.getArticleElements();
        if (shouldUpdateBaseline || this.originalOrderIds.length === 0) {
            this.originalOrderIds = articles.map(function (article) {
                return article.getAttribute("data-document-id");
            });
        }
    };

    PersonalizedSortController.prototype.bindEvents = function () {
        var self = this;
        this.buttons.forEach(function (button) {
            button.addEventListener("click", function () {
                var sort = button.getAttribute("data-sort-toggle") || DEFAULT_SORT;
                if (sort === self.currentSort) {
                    return;
                }
                self.onSortChange(sort);
            });
        });
    };

    PersonalizedSortController.prototype.observeHtmx = function () {
        var self = this;
        document.addEventListener("htmx:afterSwap", function (event) {
            if (!event || !event.target) {
                return;
            }
            if (event.target.id === "documents-container") {
                self.refreshStructure({ updateBaseline: self.currentSort !== PERSONALIZED_SORT });
                self.updateToggleUI();
                if (self.currentSort === PERSONALIZED_SORT) {
                    self.applyPersonalizedSort();
                } else {
                    self.restoreDefaultOrder();
                }
                initFeedbackUI(event.target);
            }
        });
    };

    PersonalizedSortController.prototype.onSortChange = function (sort) {
        this.currentSort = sort === PERSONALIZED_SORT ? PERSONALIZED_SORT : DEFAULT_SORT;
        this.savePreference(this.currentSort);
        this.updateToggleUI();
        if (this.currentSort === PERSONALIZED_SORT) {
            this.applyPersonalizedSort();
        } else {
            this.restoreDefaultOrder();
        }
    };

    PersonalizedSortController.prototype.updateToggleUI = function () {
        var self = this;
        if (!this.controlsRoot) {
            return;
        }
        this.controlsRoot.setAttribute("data-current-sort", this.currentSort);
        this.buttons.forEach(function (button) {
            var isActive = button.getAttribute("data-sort-toggle") === self.currentSort;
            button.setAttribute("aria-pressed", isActive ? "true" : "false");
            self.activeClasses.forEach(function (cls) {
                button.classList.toggle(cls, isActive);
            });
            self.inactiveClasses.forEach(function (cls) {
                button.classList.toggle(cls, !isActive);
            });
        });
    };

    PersonalizedSortController.prototype.collectFilters = function () {
        var params = {};
        var inputs = document.querySelectorAll("[data-documents-filter]");
        forEachNode(inputs, function (input) {
            var name = input.name;
            if (!name) {
                return;
            }
            var value = (input.value || "").trim();
            if (value) {
                params[name] = value;
            }
        });
        return params;
    };

    PersonalizedSortController.prototype.getLimit = function () {
        if (!this.container) {
            return 50;
        }
        var raw = this.container.getAttribute("data-documents-limit");
        var parsed = parseInt(raw, 10);
        if (!isNaN(parsed) && parsed > 0) {
            return parsed;
        }
        if (this.originalOrderIds.length > 0) {
            return this.originalOrderIds.length;
        }
        return 50;
    };

    PersonalizedSortController.prototype.decorateExistingArticles = function () {
        if (!this.grid) {
            return;
        }
        var articles = this.grid.querySelectorAll("[data-document-id]");
        var self = this;
        var hasPersonalizedData = false;
        forEachNode(articles, function (article) {
            if (article.hasAttribute("data-personalized-score")) {
                hasPersonalizedData = true;
                self.decorateArticle(article, null);
            }
        });
        if (hasPersonalizedData) {
            this.setStatus("ready");
        }
    };

    PersonalizedSortController.prototype.applyPersonalizedSort = function () {
        var _this = this;
        if (!this.container) {
            return;
        }
        
        // First, try to decorate existing articles with server-side rendered data
        this.decorateExistingArticles();
        
        // Then fetch fresh data from API for reordering
        if (this.abortController && typeof this.abortController.abort === "function") {
            this.abortController.abort();
        }
        if (typeof window.AbortController === "function") {
            this.abortController = new window.AbortController();
        } else {
            this.abortController = null;
        }

        var params = new URLSearchParams();
        params.set("sort", PERSONALIZED_SORT);
        params.set("limit", String(this.getLimit()));
        var filters = this.collectFilters();
        Object.keys(filters).forEach(function (key) {
            params.set(key, filters[key]);
        });

        this.setStatus("loading");

        fetch(FETCH_ENDPOINT + "?" + params.toString(), {
            headers: {
                Accept: "application/json"
            },
            signal: this.abortController ? this.abortController.signal : undefined
        })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error("Failed to fetch personalized documents");
                }
                return response.json();
            })
            .then(function (data) {
                if (!data || !Array.isArray(data.documents)) {
                    _this.restoreDefaultOrder("error");
                    return;
                }
                if (data.documents.length === 0) {
                    _this.restoreDefaultOrder("empty");
                    return;
                }
                var reorderResult = _this.reorderWithData(data.documents);
                if (reorderResult && reorderResult.applied) {
                    _this.container.setAttribute("data-documents-limit", String(data.documents.length));
                    _this.reapplyIcons();
                }

                if (reorderResult && reorderResult.missingIds && reorderResult.missingIds.length > 0) {
                    var fallbackParams = new URLSearchParams(params);
                    fallbackParams.delete("limit");
                    _this.requestServerRenderedPersonalized(fallbackParams);
                    return;
                }
                _this.setStatus("ready", data.documents);
            })
            .catch(function (error) {
                if (error && error.name === "AbortError") {
                    return;
                }
                console.warn("personalized sort fetch failed", error);
                _this.restoreDefaultOrder("error");
            });
    };

    PersonalizedSortController.prototype.reorderWithData = function (documents) {
        if (!this.grid) {
            return { missingIds: [], applied: false };
        }
        var articles = this.getArticleElements();
        var byId = new Map();
        articles.forEach(function (article) {
            byId.set(article.getAttribute("data-document-id"), article);
        });

        var orderedArticles = [];
        var self = this;
        var missingIds = [];
        documents.forEach(function (doc) {
            var article = byId.get(doc.id);
            if (!article) {
                missingIds.push(doc.id);
                return;
            }
            self.decorateArticle(article, doc);
            orderedArticles.push(article);
            byId.delete(doc.id);
        });

        byId.forEach(function (article) {
            self.decorateArticle(article, null);
            orderedArticles.push(article);
        });

        var fragment = document.createDocumentFragment();
        orderedArticles.forEach(function (article) {
            fragment.appendChild(article);
        });


        this.grid.innerHTML = "";
        this.grid.appendChild(fragment);
        return { missingIds: missingIds, applied: true };
    };

    PersonalizedSortController.prototype.requestServerRenderedPersonalized = function (params) {
        if (this.serverFallbackInFlight) {
            return;
        }
        this.serverFallbackInFlight = true;
        this.setStatus("loading");

        var query = "";
        if (params instanceof URLSearchParams) {
            query = params.toString();
        } else if (typeof params === "string") {
            query = params;
        }
        if (query.indexOf("sort=") === -1) {
            query = query ? query + "&sort=" + PERSONALIZED_SORT : "sort=" + PERSONALIZED_SORT;
        }
        var url = "/documents" + (query ? "?" + query : "");

        var self = this;
        fetch(url, {
            headers: {
                "HX-Request": "true",
                Accept: "text/html"
            }
        })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error("Failed to fetch server-rendered personalized view");
                }
                return response.text();
            })
            .then(function (html) {
                var parser = new DOMParser();
                var parsed = parser.parseFromString(html, "text/html");
                var newContainer = parsed.getElementById("documents-container");
                if (!newContainer) {
                    throw new Error("documents-container not found in server response");
                }
                var currentContainer = document.getElementById("documents-container");
                if (!currentContainer || !currentContainer.parentNode) {
                    throw new Error("Existing documents container missing");
                }
                currentContainer.parentNode.replaceChild(newContainer, currentContainer);
                self.container = newContainer;
                self.refreshStructure({ updateBaseline: false });
                self.decorateExistingArticles();
                self.reapplyIcons();
                initFeedbackUI(newContainer);
                if (typeof window.scrapMarkdownRefresh === "function") {
                    try {
                        window.scrapMarkdownRefresh(newContainer);
                    } catch (err) {
                        console.warn("Failed to refresh markdown after fallback", err);
                    }
                }
                try {
                    var currentUrl = new URL(window.location.href);
                    currentUrl.searchParams.set("sort", PERSONALIZED_SORT);
                    window.history.replaceState({}, "", currentUrl.toString());
                } catch (err) {
                    console.warn("Failed to update history state", err);
                }
                self.setStatus("ready");
            })
            .catch(function (error) {
                console.error("Server-rendered personalized fallback failed", error);
                self.restoreDefaultOrder("error");
            })
            .finally(function () {
                self.serverFallbackInFlight = false;
            });
    };

    PersonalizedSortController.prototype.restoreDefaultOrder = function (stateOverride) {
        if (!this.grid) {
            this.setStatus(stateOverride || "default");
            return;
        }
        var articles = this.getArticleElements();
        var lookup = new Map();
        var self = this;
        articles.forEach(function (article) {
            self.clearArticle(article);
            lookup.set(article.getAttribute("data-document-id"), article);
        });

        var fragment = document.createDocumentFragment();
        this.originalOrderIds.forEach(function (id) {
            var article = lookup.get(id);
            if (article) {
                fragment.appendChild(article);
                lookup.delete(id);
            }
        });

        lookup.forEach(function (article) {
            fragment.appendChild(article);
        });

        this.grid.innerHTML = "";
        this.grid.appendChild(fragment);
        if (stateOverride) {
            this.setStatus(stateOverride);
        } else if (this.currentSort === PERSONALIZED_SORT) {
            this.setStatus("empty");
        } else {
            this.setStatus("default");
        }
        this.reapplyIcons();
    };

    PersonalizedSortController.prototype.clearArticle = function (article) {
        var block = article.querySelector("[data-personalized-block]");
        if (block) {
            block.classList.add("hidden");
            var rankEl = block.querySelector("[data-personalized-rank]");
            if (rankEl) {
                rankEl.textContent = "";
            }
            var scoreEl = block.querySelector("[data-personalized-score]");
            if (scoreEl) {
                scoreEl.textContent = "";
            }
            var explanationEl = block.querySelector("[data-personalized-explanation]");
            if (explanationEl) {
                explanationEl.textContent = "";
            }
            var componentsEl = block.querySelector("[data-personalized-components]");
            if (componentsEl) {
                componentsEl.innerHTML = "";
                componentsEl.classList.remove("hidden");
            }
            var updatedEl = block.querySelector("[data-personalized-updated]");
            if (updatedEl) {
                updatedEl.textContent = "";
                updatedEl.classList.add("hidden");
            }
            // 詳細エリアも非表示にする
            var detailsEl = block.querySelector("[data-personalized-details]");
            if (detailsEl) {
                detailsEl.classList.add("hidden");
            }
            // トグルボタンの状態をリセット
            var toggleButton = block.querySelector("[data-personalized-toggle]");
            if (toggleButton) {
                toggleButton.setAttribute("aria-expanded", "false");
                var toggleText = toggleButton.querySelector("[data-personalized-toggle-text]");
                if (toggleText) {
                    toggleText.textContent = "詳細を表示";
                }
                var toggleIcon = toggleButton.querySelector("[data-personalized-toggle-icon]");
                if (toggleIcon) {
                    toggleIcon.setAttribute("data-lucide", "chevron-down");
                }
            }
        }
        var fallback = article.querySelector("[data-personalized-fallback]");
        if (fallback) {
            fallback.classList.add("hidden");
            var fallbackText = fallback.querySelector("[data-personalized-fallback-text]");
            if (fallbackText) {
                fallbackText.textContent = "記事をブックマークすると、あなた好みのおすすめ順で表示されます。";
            }
        }
    };

    PersonalizedSortController.prototype.decorateArticle = function (article, doc) {
        this.clearArticle(article);
        var block = article.querySelector("[data-personalized-block]");
        var fallback = article.querySelector("[data-personalized-fallback]");
        if (!block || !fallback) {
            return;
        }
        
        // Try to get personalized data from doc object first, then from data attributes
        var personalized = doc && doc.personalized;
        if (!personalized && article.hasAttribute("data-personalized-score")) {
            // Read from data attributes (server-side rendered data)
            try {
                personalized = {
                    score: parseFloat(article.getAttribute("data-personalized-score")),
                    rank: parseInt(article.getAttribute("data-personalized-rank"), 10),
                    explanation: article.getAttribute("data-personalized-explanation"),
                    components: JSON.parse(article.getAttribute("data-personalized-components") || "{}"),
                    computed_at: article.getAttribute("data-personalized-computed-at"),
                    cold_start: article.getAttribute("data-personalized-cold-start") === "true"
                };
            } catch (e) {
                console.error("Failed to parse personalized data from attributes:", e);
                personalized = null;
            }
        }
        
        if (!personalized) {
            fallback.classList.remove("hidden");
            return;
        }
        if (personalized.cold_start) {
            fallback.classList.remove("hidden");
            var fallbackText = fallback.querySelector("[data-personalized-fallback-text]");
            if (fallbackText) {
                fallbackText.textContent = "ブックマークを追加すると、おすすめ順の精度が向上します。";
            }
            return;
        }

        fallback.classList.add("hidden");
        block.classList.remove("hidden");

        var rankEl = block.querySelector("[data-personalized-rank]");
        if (rankEl) {
            if (typeof personalized.rank === "number") {
                rankEl.textContent = "第" + personalized.rank + "位";
            } else {
                rankEl.textContent = "優先候補";
            }
        }

        var scoreEl = block.querySelector("[data-personalized-score]");
        if (scoreEl) {
            if (isNumber(personalized.score)) {
                scoreEl.textContent = "スコア " + personalized.score.toFixed(2);
                scoreEl.classList.remove("hidden");
            } else {
                scoreEl.textContent = "";
                scoreEl.classList.add("hidden");
            }
        }

        var explanationEl = block.querySelector("[data-personalized-explanation]");
        if (explanationEl) {
            explanationEl.textContent = personalized.explanation || "おすすめの理由を計算しました。";
        }

        var componentsEl = block.querySelector("[data-personalized-components]");
        if (componentsEl) {
            var components = personalized.components || {};
            var entries = [];
            COMPONENT_ORDER.forEach(function (key) {
                if (components.hasOwnProperty(key)) {
                    entries.push([key, components[key]]);
                }
            });
            Object.keys(components).forEach(function (key) {
                if (key === "__cold_start") {
                    return;
                }
                if (COMPONENT_ORDER.indexOf(key) === -1) {
                    entries.push([key, components[key]]);
                }
            });
            if (entries.length === 0) {
                componentsEl.classList.add("hidden");
            } else {
                entries.forEach(function (item) {
                    var label = COMPONENT_LABELS[item[0]] || item[0];
                    var value = item[1];
                    var badge = document.createElement("span");
                    badge.className = "inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald/10 text-emerald-700 border border-emerald/20 text-xs";
                    if (isNumber(value)) {
                        badge.textContent = label + " " + safeFormatPercent(value) + "%";
                    } else {
                        badge.textContent = label;
                    }
                    componentsEl.appendChild(badge);
                });
            }
        }

        var updatedEl = block.querySelector("[data-personalized-updated]");
        if (updatedEl) {
            var stamp = formatTimestamp(personalized.computed_at);
            if (stamp) {
                updatedEl.textContent = "更新: " + stamp;
                updatedEl.classList.remove("hidden");
            } else {
                updatedEl.textContent = "";
                updatedEl.classList.add("hidden");
            }
        }

        // 折り畳み/展開ボタンのイベントリスナーを設定
        this.setupToggleButton(block);
    };

    PersonalizedSortController.prototype.setupToggleButton = function (block) {
        var toggleButton = block.querySelector("[data-personalized-toggle]");
        var detailsEl = block.querySelector("[data-personalized-details]");
        var toggleText = block.querySelector("[data-personalized-toggle-text]");
        var toggleIcon = block.querySelector("[data-personalized-toggle-icon]");
        
        if (!toggleButton || !detailsEl) {
            return;
        }

        // 既存のイベントリスナーを削除
        var newButton = toggleButton.cloneNode(true);
        toggleButton.parentNode.replaceChild(newButton, toggleButton);
        toggleButton = newButton;

        // 新しい参照を取得
        toggleText = toggleButton.querySelector("[data-personalized-toggle-text]");
        toggleIcon = toggleButton.querySelector("[data-personalized-toggle-icon]");

        toggleButton.addEventListener("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            
            var isExpanded = detailsEl.classList.contains("hidden");
            
            if (isExpanded) {
                // 展開
                detailsEl.classList.remove("hidden");
                toggleButton.setAttribute("aria-expanded", "true");
                toggleButton.setAttribute("aria-label", "おすすめの詳細を非表示");
                if (toggleText) {
                    toggleText.textContent = "詳細を非表示";
                }
                if (toggleIcon) {
                    toggleIcon.setAttribute("data-lucide", "chevron-up");
                }
            } else {
                // 折り畳み
                detailsEl.classList.add("hidden");
                toggleButton.setAttribute("aria-expanded", "false");
                toggleButton.setAttribute("aria-label", "おすすめの詳細を表示");
                if (toggleText) {
                    toggleText.textContent = "詳細を表示";
                }
                if (toggleIcon) {
                    toggleIcon.setAttribute("data-lucide", "chevron-down");
                }
            }
            
            // アイコンを再描画
            if (typeof window.createIcons === "function") {
                try {
                    window.createIcons();
                } catch (err) {
                    console.warn("createIcons() failed after toggle", err);
                }
            }
        });
    };

    PersonalizedSortController.prototype.reapplyIcons = function () {
        if (typeof window.createIcons === "function") {
            try {
                window.createIcons();
            } catch (err) {
                console.warn("createIcons() failed after personalized reorder", err);
            }
        }
    };

    PersonalizedSortController.prototype.setStatus = function (state, payload) {
        if (!this.statusEl) {
            return;
        }
        var message = "";
        switch (state) {
            case "loading":
                message = "おすすめ順を読み込んでいます…";
                break;
            case "ready":
                message = "おすすめ順で表示しています";
                if (Array.isArray(payload)) {
                    // Find the most recent computed_at among returned documents and show that.
                    var latestDate = null;
                    for (var i = 0; i < payload.length; i += 1) {
                        var doc = payload[i];
                        if (doc && doc.personalized && doc.personalized.computed_at) {
                            var parsed = parseIsoTimestamp(doc.personalized.computed_at);
                            if (parsed) {
                                if (!latestDate || parsed.getTime() > latestDate.getTime()) {
                                    latestDate = parsed;
                                }
                            }
                        }
                    }
                    if (latestDate) {
                        // formatTimestamp accepts an ISO string, so convert Date -> ISO
                        var stamp = formatTimestamp(latestDate.toISOString());
                        if (stamp) {
                            message += "（更新: " + stamp + "）";
                        }
                    }
                }
                break;
            case "empty":
                message = "おすすめ順の結果が存在しないため、標準順を表示しています";
                break;
            case "error":
                message = "おすすめ順の取得に失敗したため、標準順で表示しています";
                break;
            default:
                message = "";
        }
        if (!message) {
            this.statusEl.textContent = "";
            this.statusEl.classList.add("hidden");
        } else {
            this.statusEl.textContent = message;
            this.statusEl.classList.remove("hidden");
        }
    };

    PersonalizedSortController.prototype.loadPreference = function () {
        try {
            var stored = window.localStorage.getItem(STORAGE_KEY) || window.sessionStorage.getItem(STORAGE_KEY);
            if (stored === PERSONALIZED_SORT || stored === DEFAULT_SORT) {
                return stored;
            }
        } catch (err) {
            /* ignore storage errors */
        }
        return DEFAULT_SORT;
    };

    PersonalizedSortController.prototype.savePreference = function (value) {
        try {
            window.localStorage.setItem(STORAGE_KEY, value);
        } catch (err) {
            try {
                window.sessionStorage.setItem(STORAGE_KEY, value);
            } catch (inner) {
                /* ignore */
            }
        }
    };

    document.addEventListener("htmx:configRequest", function (event) {
        if (!event || !event.detail) {
            return;
        }
        var target = event.detail.elt;
        if (target && target.matches && target.matches("[data-personalized-feedback-button]")) {
            ensureSessionFieldValue();
            var token = getFeedbackSessionId();
            if (token) {
                var headers = event.detail.headers || {};
                headers["X-Feedback-Session"] = token;
                event.detail.headers = headers;
            }
        }
    });

    document.addEventListener("htmx:afterSwap", function (event) {
        if (!event || !event.target) {
            return;
        }
        if (event.target.matches && event.target.matches("[data-personalized-feedback-container]")) {
            ensureSessionFieldValue();
            var state = event.target.getAttribute("data-feedback-state") || "submitted";
            var message = event.target.getAttribute("data-feedback-message") || "";
            var documentId = event.target.getAttribute("data-document-id") || "";
            if (state === "submitted" || state === "duplicate") {
                markFeedbackSubmitted(documentId);
                if (typeof window.showNotification === "function") {
                    var tone = state === "submitted" ? "success" : "info";
                    window.showNotification(message || "フィードバックを受け付けました。", tone);
                }
            }
            if (typeof window.createIcons === "function") {
                window.createIcons();
            }
        }
    });

    document.addEventListener("DOMContentLoaded", function () {
        initFeedbackUI(document);
        new PersonalizedSortController();
    });
})(window, document);
