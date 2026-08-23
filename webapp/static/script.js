"use strict";

/* =========================================================
   GLOBAL STATE
========================================================= */

let currentHeadline = "";
let currentChatContext = null;

/* =========================================================
   DOM HELPERS
========================================================= */

function $(id) {
    return document.getElementById(id);
}

function show(element) {
    if (element) {
        element.classList.remove("hidden");
    }
}

function hide(element) {
    if (element) {
        element.classList.add("hidden");
    }
}

/* =========================================================
   ELEMENTS
========================================================= */

const verifyForm = $("verifyForm");
const headlineInput = $("headlineInput");
const charCount = $("charCount");
const clearBtn = $("clearBtn");
const verifyBtn = $("verifyBtn");
const verifyBtnText = $("verifyBtnText");
const verifySpinner = $("verifySpinner");
const verifyLoading = $("verifyLoading");
const resultBox = $("resultBox");
const verdictText = $("verdictText");
const verdictIcon = $("verdictIcon");
const resultHeadline = $("resultHeadline");
const resultMode = $("resultMode");
const resultConfidence = $("resultConfidence");
const confidenceRow = $("confidenceRow");
const publisherRow = $("publisherRow");
const resultPublisher = $("resultPublisher");
const ratingRow = $("ratingRow");
const resultRating = $("resultRating");
const reasonBox = $("reasonBox");
const resultReason = $("resultReason");
const sourcesBox = $("sourcesBox");
const sourcesList = $("sourcesList");

/* =========================================================
   EXPLAINABLE AI
========================================================= */

const explainMethod = $("explainMethod");
const explainBtn = $("explainBtn");
const explainLoading = $("explainLoading");
const explainResult = $("explainResult");
const explainError = $("explainError");
const wordImportance = $("wordImportance");

/* =========================================================
   STATS
========================================================= */

const statTotal = $("statTotal");
const statReal = $("statReal");
const statFake = $("statFake");

/* =========================================================
   FEED
========================================================= */

const liveFeed = $("liveFeed");
const refreshFeedBtn = $("refreshFeedBtn");

/* =========================================================
   HISTORY
========================================================= */

const historyList = $("historyList");

/* =========================================================
   CHAT
========================================================= */

const chatToggle = $("chatToggle");
const chatWindow = $("chatWindow");
const chatClose = $("chatClose");
const chatMessages = $("chatMessages");
const chatForm = $("chatForm");
const chatInput = $("chatInput");

/* =========================================================
   CHARACTER COUNT
========================================================= */

if (headlineInput) {
    headlineInput.addEventListener("input", function() {
        const length = headlineInput.value.length;

        if (charCount) {
            charCount.textContent = `${length} / 1000`;
        }
    });
}

/* =========================================================
   CLEAR
========================================================= */

if (clearBtn) {
    clearBtn.addEventListener("click", function(event) {
        event.preventDefault();

        headlineInput.value = "";
        currentHeadline = "";
        currentChatContext = null;

        if (charCount) {
            charCount.textContent = "0 / 1000";
        }

        hide(resultBox);
        hide(explainResult);
        hide(explainError);
    });
}

/* =========================================================
   VERIFY
========================================================= */

if (verifyForm) {
    verifyForm.addEventListener("submit", async function(event) {
        event.preventDefault();
        event.stopPropagation();

        const headline = headlineInput.value.trim();

        if (!headline) {
            headlineInput.focus();
            return;
        }

        currentHeadline = headline;

        hide(resultBox);
        hide(explainResult);
        hide(explainError);

        verifyBtn.disabled = true;

        if (verifyBtnText) {
            verifyBtnText.textContent = "Verifying...";
        }

        show(verifySpinner);
        show(verifyLoading);

        try {
            const response = await fetch("/api/check", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    headline: headline
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.error || "Verification failed"
                );
            }

            displayVerificationResult(data);

            currentChatContext = buildChatContext(data);

            loadStats();
            loadHistory();

            setTimeout(function() {
                if (resultBox) {
                    resultBox.scrollIntoView({
                        behavior: "smooth",
                        block: "nearest"
                    });
                }
            }, 100);
        } catch (error) {
            console.error("Verification error:", error);
            showErrorResult(error.message);
        } finally {
            verifyBtn.disabled = false;

            if (verifyBtnText) {
                verifyBtnText.textContent = "Verify Headline";
            }

            hide(verifySpinner);
            hide(verifyLoading);
        }
    });
}

/* =========================================================
   DISPLAY VERIFICATION RESULT
========================================================= */

function displayVerificationResult(data) {
    if (!resultBox) return;

    resultBox.classList.remove("real", "fake");

    const verdict = String(data.verdict || "").toUpperCase();

    if (verdict === "REAL") {
        resultBox.classList.add("real");
        verdictText.textContent = "REAL NEWS";
        verdictIcon.textContent = "✓";
    } else if (verdict === "FAKE") {
        resultBox.classList.add("fake");
        verdictText.textContent = "FAKE NEWS";
        verdictIcon.textContent = "✕";
    } else {
        verdictText.textContent = verdict || "UNKNOWN";
        verdictIcon.textContent = "?";
    }

    resultHeadline.textContent = data.headline || currentHeadline;

    resultMode.textContent = formatMode(data.mode);

    if (data.confidence !== undefined && data.confidence !== null) {
        show(confidenceRow);
        resultConfidence.textContent = formatConfidence(data.confidence);
    } else {
        hide(confidenceRow);
    }

    if (data.publisher) {
        show(publisherRow);
        resultPublisher.textContent = data.publisher;
    } else {
        hide(publisherRow);
    }

    if (data.rating) {
        show(ratingRow);
        resultRating.textContent = data.rating;
    } else {
        hide(ratingRow);
    }

    if (data.reason) {
        show(reasonBox);
        resultReason.textContent = data.reason;
    } else {
        hide(reasonBox);
    }

    if (Array.isArray(data.sources) && data.sources.length > 0) {
        show(sourcesBox);
        sourcesList.innerHTML = "";

        data.sources.forEach(function(source) {
            const li = document.createElement("li");
            li.textContent = source;
            sourcesList.appendChild(li);
        });
    } else {
        hide(sourcesBox);
    }

    show(resultBox);
}

/* =========================================================
   ERROR RESULT
========================================================= */

function showErrorResult(message) {
    resultBox.classList.remove("real", "fake");

    show(resultBox);

    verdictText.textContent = "ERROR";
    verdictIcon.textContent = "!";

    resultHeadline.textContent = currentHeadline;
    resultMode.textContent = "Error";

    hide(confidenceRow);
    hide(publisherRow);
    hide(ratingRow);

    show(reasonBox);

    resultReason.textContent = message || "Something went wrong.";

    hide(sourcesBox);
}

/* =========================================================
   FORMAT MODE
========================================================= */

function formatMode(mode) {
    if (!mode) {
        return "Unknown";
    }

    const map = {
        verified: "Trusted Source Verified",
        fact_checked: "Fact Checked",
        flagged: "Rule-Based Detection",
        llm_flagged: "AI Plausibility Check",
        unverified: "ML Model Prediction"
    };

    return (
        map[mode] ||
        String(mode)
            .replaceAll("_", " ")
            .replace(/\b\w/g, c => c.toUpperCase())
    );
}

/* =========================================================
   CONFIDENCE
========================================================= */

function formatConfidence(value) {
    let number = Number(value);

    if (Number.isNaN(number)) {
        return String(value);
    }

    if (number <= 1) {
        number = number * 100;
    }

    return number.toFixed(1) + "%";
}

/* =========================================================
   CHAT CONTEXT
========================================================= */

function buildChatContext(data) {
    let context = `The user just checked a news headline.
Headline: "${data.headline || currentHeadline}".
Verdict: ${data.verdict || "UNKNOWN"}.
Detection mode: ${formatMode(data.mode)}.`;

    if (data.confidence !== undefined) {
        context += ` Confidence: ${formatConfidence(data.confidence)}.`;
    }

    if (data.publisher) {
        context += ` Publisher/fact checker: ${data.publisher}.`;
    }

    if (data.rating) {
        context += ` Rating: ${data.rating}.`;
    }

    if (data.reason) {
        context += ` Reason: ${data.reason}.`;
    }

    return context;
}

/* =========================================================
   EXPLAINABLE AI
========================================================= */

if (explainBtn) {
    explainBtn.addEventListener("click", async function(event) {
        event.preventDefault();
        event.stopPropagation();

        if (!currentHeadline) {
            showExplainError("Please verify a headline first.");
            return;
        }

        hide(explainError);
        hide(explainResult);
        show(explainLoading);

        explainBtn.disabled = true;

        try {
            const method = explainMethod
                ? explainMethod.value
                : "lime";

            const response = await fetch("/api/explain", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    headline: currentHeadline,
                    method: method
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.error || "Explanation failed"
                );
            }

            renderExplanation(data);
        } catch (error) {
            console.error("Explain error:", error);
            showExplainError(error.message);
        } finally {
            hide(explainLoading);
            explainBtn.disabled = false;
        }
    });
}

/* =========================================================
   RENDER EXPLANATION
========================================================= */

function renderExplanation(data) {
    if (!wordImportance) return;

    wordImportance.innerHTML = "";

    const words = Array.isArray(data.words)
        ? data.words
        : [];

    if (words.length === 0) {
        wordImportance.textContent =
            "No word-level explanation was returned.";

        show(explainResult);
        return;
    }

    words.forEach(function(item) {
        const word = document.createElement("div");

        const weight = Number(item.weight);

        word.className =
            "word-chip " +
            (weight >= 0 ? "real-word" : "fake-word");

        const wordText = document.createElement("span");
        wordText.textContent = item.word;

        const weightText = document.createElement("small");

        weightText.textContent =
            (weight >= 0 ? "REAL +" : "FAKE ") +
            Math.abs(weight).toFixed(4);

        word.appendChild(wordText);
        word.appendChild(weightText);

        wordImportance.appendChild(word);
    });

    show(explainResult);
}

/* =========================================================
   EXPLAIN ERROR
========================================================= */

function showExplainError(message) {
    if (!explainError) return;

    explainError.textContent = message;
    show(explainError);
}

/* =========================================================
   CHATBOT OPEN
========================================================= */

if (chatToggle) {
    chatToggle.addEventListener("click", function(event) {
        event.preventDefault();
        event.stopPropagation();

        if (!chatWindow) return;

        chatWindow.classList.toggle("hidden");

        if (!chatWindow.classList.contains("hidden")) {
            setTimeout(function() {
                if (chatInput) {
                    chatInput.focus();
                }
            }, 100);
        }
    });
}

/* =========================================================
   CHATBOT CLOSE
========================================================= */

if (chatClose) {
    chatClose.addEventListener("click", function(event) {
        event.preventDefault();
        event.stopPropagation();

        hide(chatWindow);
    });
}

/* =========================================================
   CHAT MESSAGE
========================================================= */

function addChatMessage(text, type) {
    if (!chatMessages) return;

    const message = document.createElement("div");

    message.className =
        "chat-message " +
        (type === "user" ? "user" : "bot");

    message.textContent = text;

    chatMessages.appendChild(message);

    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/* =========================================================
   CHATBOT SEND
========================================================= */

if (chatForm) {
    chatForm.addEventListener("submit", async function(event) {
        event.preventDefault();
        event.stopPropagation();

        const message = chatInput.value.trim();

        if (!message) return;

        addChatMessage(message, "user");

        chatInput.value = "";
        chatInput.disabled = true;

        addChatMessage("Thinking...", "bot");

        const thinking = chatMessages.lastElementChild;

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    messages: [
                        {
                            role: "user",
                            content: message
                        }
                    ],
                    context: currentChatContext
                })
            });

            const data = await response.json();

            if (thinking) {
                thinking.remove();
            }

            if (data && data.reply) {
                addChatMessage(data.reply, "bot");
            } else {
                addChatMessage(
                    "Sorry, I couldn't generate a response.",
                    "bot"
                );
            }
        } catch (error) {
            console.error("Chat error:", error);

            if (thinking) {
                thinking.remove();
            }

            addChatMessage(
                "Chat service is unavailable right now. Please try again.",
                "bot"
            );
        } finally {
            chatInput.disabled = false;
            chatInput.focus();
        }
    });
}

/* =========================================================
   LOAD STATS
========================================================= */

async function loadStats() {
    try {
        const response = await fetch("/api/stats");
        const data = await response.json();

        const total =
            data.total ??
            data.total_checks ??
            data.count ??
            0;

        const real =
            data.real ??
            data.real_count ??
            (
                data.by_verdict
                    ? data.by_verdict.REAL ?? 0
                    : 0
            );

        const fake =
            data.fake ??
            data.fake_count ??
            (
                data.by_verdict
                    ? data.by_verdict.FAKE ?? 0
                    : 0
            );

        if (statTotal) {
            statTotal.textContent = total;
        }

        if (statReal) {
            statReal.textContent = real;
        }

        if (statFake) {
            statFake.textContent = fake;
        }
    } catch (error) {
        console.error("Stats error:", error);
    }
}

/* =========================================================
   LOAD LIVE FEED
========================================================= */

async function loadLiveFeed() {
    if (!liveFeed) return;

    liveFeed.innerHTML = `
        <div class="feed-empty">
            Loading live headlines...
        </div>`;

    try {
        const response = await fetch("/api/live-feed");
        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error || "Could not load live feed"
            );
        }

        renderLiveFeed(data.results || []);
    } catch (error) {
        console.error("Live feed error:", error);

        liveFeed.innerHTML = `
            <div class="feed-empty">
                Could not load live news.
            </div>`;
    }
}

/* =========================================================
   RENDER LIVE FEED
========================================================= */

function renderLiveFeed(results) {
    if (!liveFeed) return;

    liveFeed.innerHTML = "";

    if (!results.length) {
        liveFeed.innerHTML = `
            <div class="feed-empty">
                No live headlines available.
            </div>`;

        return;
    }

    results.forEach(function(item) {
        const row = document.createElement("div");
        row.className = "feed-item";

        const top = document.createElement("div");
        top.className = "feed-top";

        const title = document.createElement("div");
        title.className = "feed-title";

        title.textContent =
            item.headline ||
            item.title ||
            "Unknown headline";

        const verdict = String(
            item.prediction ||
            item.verdict ||
            "UNKNOWN"
        ).toUpperCase();

        const badge = document.createElement("div");

        badge.className =
            "feed-verdict " +
            (
                verdict === "REAL"
                    ? "real"
                    : verdict === "FAKE"
                        ? "fake"
                        : ""
            );

        badge.textContent = verdict;

        top.appendChild(title);
        top.appendChild(badge);

        row.appendChild(top);

        const confidence = item.confidence;

        if (
            confidence !== undefined &&
            confidence !== null
        ) {
            const meta = document.createElement("div");

            meta.className = "feed-meta";

            meta.textContent =
                "Model confidence: " +
                formatConfidence(confidence);

            row.appendChild(meta);
        }

        liveFeed.appendChild(row);
    });
}

/* =========================================================
   LOAD HISTORY
========================================================= */

async function loadHistory() {
    if (!historyList) return;

    historyList.innerHTML = `
        <div class="history-empty">
            Loading history...
        </div>`;

    try {
        const response = await fetch("/api/history");
        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error || "Could not load history."
            );
        }

        renderHistory(data.history || []);
    } catch (error) {
        console.error("History error:", error);

        historyList.innerHTML = `
            <div class="history-empty">
                Could not load history.
            </div>`;
    }
}

/* =========================================================
   RENDER HISTORY
========================================================= */

function renderHistory(history) {
    if (!historyList) return;

    historyList.innerHTML = "";

    if (!history.length) {
        historyList.innerHTML = `
            <div class="history-empty">
                No verification history yet.
            </div>`;

        return;
    }

    history.forEach(function(item) {
        const row = document.createElement("div");
        row.className = "history-item";

        const head = document.createElement("div");
        head.className = "history-head";

        const headline = document.createElement("div");
        headline.className = "history-headline";

        headline.textContent =
            item.headline ||
            "Unknown headline";

        const actions = document.createElement("div");
        actions.className = "history-actions";

        const verdict = String(
            item.verdict || "UNKNOWN"
        ).toUpperCase();

        const verdictElement = document.createElement("div");

        verdictElement.className =
            "history-verdict " +
            (
                verdict === "REAL"
                    ? "real"
                    : verdict === "FAKE"
                        ? "fake"
                        : ""
            );

        verdictElement.textContent = verdict;

        const deleteButton = document.createElement("button");

        deleteButton.type = "button";
        deleteButton.className = "delete-history-btn";
        deleteButton.textContent = "Delete";
        deleteButton.title = "Delete this history item";
        deleteButton.dataset.id = item.id;

        deleteButton.addEventListener(
            "click",
            async function(event) {
                event.preventDefault();
                event.stopPropagation();

                const checkId = deleteButton.dataset.id;

                if (!checkId) {
                    alert("History record ID is missing.");
                    return;
                }

                const confirmed = window.confirm(
                    "Are you sure you want to delete this history item?"
                );

                if (!confirmed) {
                    return;
                }

                deleteButton.disabled = true;
                deleteButton.textContent = "Deleting...";

                try {
                    const response = await fetch(
                        `/api/history/${encodeURIComponent(checkId)}`,
                        {
                            method: "DELETE"
                        }
                    );

                    const data = await response.json();

                    if (!response.ok) {
                        throw new Error(
                            data.error ||
                            "Could not delete history item."
                        );
                    }

                    row.remove();

                    loadStats();

                    const remaining =
                        historyList.querySelectorAll(
                            ".history-item"
                        );

                    if (remaining.length === 0) {
                        historyList.innerHTML = `
                            <div class="history-empty">
                                No verification history yet.
                            </div>`;
                    }
                } catch (error) {
                    console.error(
                        "Delete history error:",
                        error
                    );

                    deleteButton.disabled = false;
                    deleteButton.textContent = "Delete";

                    alert(
                        error.message ||
                        "Could not delete history item."
                    );
                }
            }
        );

        actions.appendChild(verdictElement);
        actions.appendChild(deleteButton);

        head.appendChild(headline);
        head.appendChild(actions);

        row.appendChild(head);

        const meta = document.createElement("div");
        meta.className = "history-meta";

        const mode = item.mode || "unknown";

        const timestamp =
            item.checked_at ||
            item.timestamp ||
            item.created_at ||
            "";

        meta.textContent =
            formatMode(mode) +
            (
                timestamp
                    ? " • " + timestamp
                    : ""
            );

        row.appendChild(meta);

        historyList.appendChild(row);
    });
}

/* =========================================================
   REFRESH FEED
========================================================= */

if (refreshFeedBtn) {
    refreshFeedBtn.addEventListener("click", function(event) {
        event.preventDefault();
        loadLiveFeed();
    });
}

/* =========================================================
   INITIAL LOAD
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    function() {
        loadStats();
        loadHistory();
        loadLiveFeed();
    }
);