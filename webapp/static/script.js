"use strict";


/* =========================================================
   GLOBAL STATE
========================================================= */

let currentHeadline = "";
let currentChatContext = null;


/* =========================================================
   HELPERS
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


function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}


function escapeText(value) {
    return value === null || value === undefined
        ? ""
        : String(value);
}


/* =========================================================
   DOM
========================================================= */

const verifyForm = $("verifyForm");
const headlineInput = $("headlineInput");
const charCount = $("charCount");
const clearBtn = $("clearBtn");

const verifyBtn = $("verifyBtn");
const verifyBtnText = $("verifyBtnText");
const verifySpinner = $("verifySpinner");

const verifyLoading = $("verifyLoading");
const verificationSteps =
    document.querySelectorAll(".verification-step");

const loadingTitle = $("loadingTitle");
const loadingSubtitle = $("loadingSubtitle");

const resultBox = $("resultBox");

const verdictText = $("verdictText");
const verdictIcon = $("verdictIcon");

const resultHeadline = $("resultHeadline");

const resultMode = $("resultMode");
const resultConfidenceTop = $("resultConfidenceTop");
const resultModeTop = $("resultModeTop");
const resultTime = $("resultTime");
const receiptTime = $("receiptTime");
const signalScore = $("signalScore");

const publisherRow = $("publisherRow");
const resultPublisher = $("resultPublisher");

const ratingRow = $("ratingRow");
const resultRating = $("resultRating");

const reasonBox = $("reasonBox");
const resultReason = $("resultReason");

const sourcesBox = $("sourcesBox");
const sourcesList = $("sourcesList");

const verifiedBox = $("verifiedBox");
const verifiedList = $("verifiedList");

const disputedBox = $("disputedBox");
const disputedList = $("disputedList");


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

const liveFeedPanel = $("liveFeedPanel");
const liveFeedToggle = $("liveFeedToggle");
const closeLiveFeed = $("closeLiveFeed");
const verifyNavBtn = $("verifyNavBtn");


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
   CHARACTER COUNTER
========================================================= */

if (headlineInput) {

    headlineInput.addEventListener(
        "input",
        function () {

            const length =
                headlineInput.value.length;

            if (charCount) {
                charCount.textContent =
                    `${length} / 1000`;
            }
        }
    );
}


/* =========================================================
   CLEAR BUTTON
========================================================= */

if (clearBtn) {

    clearBtn.addEventListener(
        "click",
        function (event) {

            event.preventDefault();

            headlineInput.value = "";

            currentHeadline = "";
            currentChatContext = null;

            if (charCount) {
                charCount.textContent =
                    "0 / 1000";
            }

            hide(resultBox);
            hide(explainResult);
            hide(explainError);
        }
    );
}


/* =========================================================
   VERIFY FORM
========================================================= */

if (verifyForm) {

    verifyForm.addEventListener(
        "submit",
        async function (event) {

            event.preventDefault();
            event.stopPropagation();

            const headline =
                headlineInput.value.trim();

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
                verifyBtnText.textContent =
                    "Verifying...";
            }

            show(verifySpinner);
            show(verifyLoading);

            resetVerificationSteps();

            /*
             * Animation starts immediately while
             * backend verification runs.
             */
            const animationPromise =
                runVerificationAnimation();

            try {

                const response =
                    await fetch(
                        "/api/check",
                        {
                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body: JSON.stringify({
                                headline: headline
                            })
                        }
                    );


                const data =
                    await response.json();


                if (!response.ok) {

                    throw new Error(
                        data.error ||
                        "Verification failed."
                    );
                }


                /*
                 * Don't show the result until
                 * all five animations complete.
                 */
                await animationPromise;


                displayVerificationResult(data);

                currentChatContext =
                    buildChatContext(data);

                loadStats();
                loadHistory();


                setTimeout(
                    function () {

                        if (resultBox) {

                            resultBox.scrollIntoView({
                                behavior: "smooth",
                                block: "nearest"
                            });

                        }

                    },
                    150
                );

            } catch (error) {

                console.error(
                    "Verification error:",
                    error
                );

                try {
                    await animationPromise;
                } catch (_) {}

                showErrorResult(
                    error.message ||
                    "Something went wrong."
                );

            } finally {

                verifyBtn.disabled = false;

                if (verifyBtnText) {
                    verifyBtnText.textContent =
                        "Verify Headline";
                }

                hide(verifySpinner);
                hide(verifyLoading);
            }

        }
    );
}


/* =========================================================
   RESET ANIMATION
========================================================= */

function resetVerificationSteps() {

    verificationSteps.forEach(
        function (step) {

            step.classList.remove(
                "active",
                "done"
            );

            const status =
                step.querySelector(
                    ".step-status"
                );

            if (status) {
                status.textContent = "";
            }
        }
    );


    if (loadingTitle) {

        loadingTitle.textContent =
            "Reading sources...";
    }


    if (loadingSubtitle) {

        loadingSubtitle.textContent =
            "We are checking the live web before generating the verdict.";
    }
}


/* =========================================================
   5 STEP ANIMATION
========================================================= */

async function runVerificationAnimation() {

    const titles = [

        "Searching the live web...",

        "Cross-referencing sources...",

        "Checking trusted news sources...",

        "Running AI reasoning...",

        "Running ML prediction..."
    ];


    for (
        let i = 0;
        i < verificationSteps.length;
        i++
    ) {

        const step =
            verificationSteps[i];


        step.classList.add("active");


        if (loadingTitle) {

            loadingTitle.textContent =
                titles[i];
        }


        if (loadingSubtitle) {

            loadingSubtitle.textContent =
                `Verification layer ${i + 1} of 5`;
        }


        await sleep(700);


        step.classList.remove("active");

        step.classList.add("done");

    }


    if (loadingTitle) {

        loadingTitle.textContent =
            "Verification complete";
    }


    if (loadingSubtitle) {

        loadingSubtitle.textContent =
            "Building your verification receipt...";
    }


    await sleep(350);
}


/* =========================================================
   DISPLAY RESULT
========================================================= */

function displayVerificationResult(data) {

    if (!resultBox) {
        return;
    }


    resultBox.classList.remove(
        "real",
        "fake",
        "misleading"
    );


    const verdict =
        String(
            data.verdict ||
            data.prediction ||
            "UNKNOWN"
        ).toUpperCase();


    const confidence =
        data.confidence !== undefined &&
        data.confidence !== null

            ? formatConfidence(
                data.confidence
            )

            : "—";


    const mode =
        formatMode(data.mode);


    const scoreValue =
        data.score ??
        data.signal_score ??
        data.signalScore ??
        data.confidence;


    let scoreNumber = "—";


    if (
        scoreValue !== undefined &&
        scoreValue !== null
    ) {

        const number =
            Number(scoreValue);


        if (!Number.isNaN(number)) {

            scoreNumber =
                Math.round(
                    number <= 1
                        ? number * 100
                        : number
                );
        }
    }


    /* =====================================================
       VERDICT
    ====================================================== */

    if (verdict === "REAL") {

        resultBox.classList.add("real");

        verdictText.textContent =
            "REAL NEWS";

        verdictIcon.textContent =
            "✓";

    } else if (verdict === "FAKE") {

        resultBox.classList.add("fake");

        verdictText.textContent =
            "FAKE NEWS";

        verdictIcon.textContent =
            "✕";

    } else if (
        verdict === "MISLEADING"
    ) {

        resultBox.classList.add(
            "misleading"
        );

        verdictText.textContent =
            "MISLEADING";

        verdictIcon.textContent =
            "!";

    } else {

        verdictText.textContent =
            verdict;

        verdictIcon.textContent =
            "?";
    }


    /* =====================================================
       BASIC DATA
    ====================================================== */

    if (resultHeadline) {

        resultHeadline.textContent =
            data.headline ||
            currentHeadline;
    }


    if (resultMode) {

        resultMode.textContent =
            mode;
    }


    if (signalScore) {

        signalScore.textContent =
            scoreNumber;
    }


    if (resultConfidenceTop) {

        resultConfidenceTop.textContent =
            confidence;
    }


    if (resultModeTop) {

        resultModeTop.textContent =
            mode;
    }


    if (resultTime) {

        resultTime.textContent =
            data.time ||
            data.verification_time ||
            data.elapsed ||
            "Completed";
    }


    if (receiptTime) {

        receiptTime.textContent =
            data.checked_at ||
            data.timestamp ||
            new Date().toLocaleString();
    }


    /* =====================================================
       PUBLISHER
    ====================================================== */

    if (data.publisher) {

        show(publisherRow);

        if (resultPublisher) {

            resultPublisher.textContent =
                data.publisher;
        }

    } else {

        hide(publisherRow);
    }


    /* =====================================================
       RATING
    ====================================================== */

    if (data.rating) {

        show(ratingRow);

        if (resultRating) {

            resultRating.textContent =
                data.rating;
        }

    } else {

        hide(ratingRow);
    }


    /* =====================================================
       REASON
    ====================================================== */

    const reason =
        data.reason ||
        data.explanation ||
        data.details ||
        data.analysis;


    if (reason) {

        show(reasonBox);

        if (resultReason) {

            resultReason.textContent =
                reason;
        }

    } else {

        hide(reasonBox);
    }


    /* =====================================================
       SOURCES
    ====================================================== */

    if (
        Array.isArray(data.sources) &&
        data.sources.length > 0
    ) {

        show(sourcesBox);

        sourcesList.innerHTML = "";


        data.sources.forEach(
            function (source) {

                const li =
                    document.createElement(
                        "li"
                    );


                if (
                    source &&
                    typeof source === "object"
                ) {

                    const title =
                        source.title ||
                        source.name ||
                        source.source ||
                        source.url ||
                        JSON.stringify(
                            source
                        );


                    li.textContent =
                        title;

                } else {

                    li.textContent =
                        source;
                }


                sourcesList.appendChild(li);
            }
        );

    } else {

        hide(sourcesBox);
    }


    /* =====================================================
       VERIFIED / DISPUTED
    ====================================================== */

    renderInsightList(
        verifiedBox,
        verifiedList,
        data.verified ||
        data.verified_points ||
        data.confirmed
    );


    renderInsightList(
        disputedBox,
        disputedList,
        data.disputed ||
        data.disputed_points ||
        data.contradictions
    );


    show(resultBox);
}


/* =========================================================
   INSIGHT LIST
========================================================= */

function renderInsightList(
    box,
    list,
    values
) {

    if (
        !box ||
        !list ||
        !Array.isArray(values) ||
        values.length === 0
    ) {

        hide(box);

        return;
    }


    list.innerHTML = "";


    values.forEach(
        function (value) {

            const li =
                document.createElement(
                    "li"
                );


            if (
                value &&
                typeof value === "object"
            ) {

                li.textContent =
                    value.text ||
                    value.claim ||
                    value.title ||
                    JSON.stringify(
                        value
                    );

            } else {

                li.textContent =
                    value;
            }


            list.appendChild(li);
        }
    );


    show(box);
}


/* =========================================================
   ERROR
========================================================= */

function showErrorResult(message) {

    if (!resultBox) {
        return;
    }


    resultBox.classList.remove(
        "real",
        "fake",
        "misleading"
    );


    show(resultBox);


    verdictText.textContent =
        "ERROR";

    verdictIcon.textContent =
        "!";


    resultHeadline.textContent =
        currentHeadline;


    resultMode.textContent =
        "Verification Error";


    hide(publisherRow);
    hide(ratingRow);
    hide(sourcesBox);

    hide(verifiedBox);
    hide(disputedBox);


    show(reasonBox);


    resultReason.textContent =
        message ||
        "Something went wrong.";
}


/* =========================================================
   FORMAT MODE
========================================================= */

function formatMode(mode) {

    if (!mode) {
        return "Unknown";
    }


    const map = {

        verified:
            "Trusted Source Verified",

        fact_checked:
            "Fact Checked",

        flagged:
            "Rule-Based Detection",

        llm_flagged:
            "AI Plausibility Check",

        unverified:
            "ML Model Prediction"
    };


    if (map[mode]) {
        return map[mode];
    }


    return String(mode)
        .replaceAll("_", " ")
        .replace(
            /\b\w/g,
            char =>
                char.toUpperCase()
        );
}


/* =========================================================
   FORMAT CONFIDENCE
========================================================= */

function formatConfidence(value) {

    let number =
        Number(value);


    if (Number.isNaN(number)) {

        return String(value);
    }


    if (number <= 1) {

        number *= 100;
    }


    return (
        number.toFixed(1) +
        "%"
    );
}


/* =========================================================
   CHAT CONTEXT
========================================================= */

function buildChatContext(data) {

    let context =
        `The user just checked a news headline.
Headline: "${data.headline || currentHeadline}".
Verdict: ${data.verdict || data.prediction || "UNKNOWN"}.
Detection mode: ${formatMode(data.mode)}.`;


    if (
        data.confidence !== undefined &&
        data.confidence !== null
    ) {

        context +=
            ` Confidence: ${formatConfidence(
                data.confidence
            )}.`;
    }


    if (data.publisher) {

        context +=
            ` Publisher/fact checker: ${data.publisher}.`;
    }


    if (data.rating) {

        context +=
            ` Rating: ${data.rating}.`;
    }


    if (data.reason) {

        context +=
            ` Reason: ${data.reason}.`;
    }


    return context;
}


/* =========================================================
   EXPLAIN BUTTON
========================================================= */

if (explainBtn) {

    explainBtn.addEventListener(
        "click",
        async function (event) {

            event.preventDefault();
            event.stopPropagation();


            if (!currentHeadline) {

                showExplainError(
                    "Please verify a headline first."
                );

                return;
            }


            hide(explainError);
            hide(explainResult);

            show(explainLoading);

            explainBtn.disabled = true;


            try {

                const method =
                    explainMethod
                        ? explainMethod.value
                        : "lime";


                const response =
                    await fetch(
                        "/api/explain",
                        {
                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body: JSON.stringify({

                                headline:
                                    currentHeadline,

                                method:
                                    method
                            })
                        }
                    );


                const data =
                    await response.json();


                if (!response.ok) {

                    throw new Error(
                        data.error ||
                        "Explanation failed."
                    );
                }


                renderExplanation(data);

            } catch (error) {

                console.error(
                    "Explain error:",
                    error
                );

                showExplainError(
                    error.message
                );

            } finally {

                hide(explainLoading);

                explainBtn.disabled =
                    false;
            }

        }
    );
}


/* =========================================================
   EXPLANATION RENDER
========================================================= */

function renderExplanation(data) {

    if (!wordImportance) {
        return;
    }


    wordImportance.innerHTML = "";


    const words =
        Array.isArray(data.words)
            ? data.words
            : [];


    if (words.length === 0) {

        wordImportance.textContent =
            "No word-level explanation was returned.";

        show(explainResult);

        return;
    }


    words.forEach(
        function (item) {

            const word =
                document.createElement(
                    "div"
                );


            const weight =
                Number(item.weight);


            word.className =
                "word-chip " +
                (
                    weight >= 0
                        ? "real-word"
                        : "fake-word"
                );


            const wordText =
                document.createElement(
                    "span"
                );

            wordText.textContent =
                item.word ||
                "";


            const weightText =
                document.createElement(
                    "small"
                );


            if (Number.isNaN(weight)) {

                weightText.textContent =
                    "Weight unavailable";

            } else {

                weightText.textContent =
                    (
                        weight >= 0
                            ? "REAL +"
                            : "FAKE "
                    ) +
                    Math.abs(weight)
                        .toFixed(4);
            }


            word.appendChild(wordText);

            word.appendChild(weightText);

            wordImportance.appendChild(word);
        }
    );


    show(explainResult);
}


/* =========================================================
   EXPLAIN ERROR
========================================================= */

function showExplainError(message) {

    if (!explainError) {
        return;
    }


    explainError.textContent =
        message ||
        "Explanation failed.";


    show(explainError);
}


/* =========================================================
   CHAT OPEN / CLOSE
========================================================= */

if (chatToggle) {

    chatToggle.addEventListener(
        "click",
        function (event) {

            event.preventDefault();
            event.stopPropagation();


            if (!chatWindow) {
                return;
            }


            chatWindow.classList.toggle(
                "hidden"
            );


            if (
                !chatWindow.classList.contains(
                    "hidden"
                )
            ) {

                setTimeout(
                    function () {

                        if (chatInput) {
                            chatInput.focus();
                        }

                    },
                    100
                );
            }

        }
    );
}


if (chatClose) {

    chatClose.addEventListener(
        "click",
        function (event) {

            event.preventDefault();
            event.stopPropagation();

            hide(chatWindow);
        }
    );
}


/* =========================================================
   CHAT MESSAGE
========================================================= */

function addChatMessage(
    text,
    type
) {

    if (!chatMessages) {
        return;
    }


    const message =
        document.createElement(
            "div"
        );


    message.className =
        "chat-message " +
        (
            type === "user"
                ? "user"
                : "bot"
        );


    message.textContent =
        escapeText(text);


    chatMessages.appendChild(
        message
    );


    chatMessages.scrollTop =
        chatMessages.scrollHeight;
}


/* =========================================================
   CHAT SEND
========================================================= */

if (chatForm) {

    chatForm.addEventListener(
        "submit",
        async function (event) {

            event.preventDefault();
            event.stopPropagation();


            const message =
                chatInput.value.trim();


            if (!message) {
                return;
            }


            addChatMessage(
                message,
                "user"
            );


            chatInput.value = "";

            chatInput.disabled = true;


            addChatMessage(
                "Thinking...",
                "bot"
            );


            const thinking =
                chatMessages.lastElementChild;


            try {

                const response =
                    await fetch(
                        "/api/chat",
                        {
                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body: JSON.stringify({

                                messages: [

                                    {
                                        role: "user",

                                        content:
                                            message
                                    }

                                ],

                                context:
                                    currentChatContext
                            })
                        }
                    );


                const data =
                    await response.json();


                if (thinking) {
                    thinking.remove();
                }


                if (
                    data &&
                    data.reply
                ) {

                    addChatMessage(
                        data.reply,
                        "bot"
                    );

                } else {

                    addChatMessage(
                        "Sorry, I couldn't generate a response.",
                        "bot"
                    );
                }


            } catch (error) {

                console.error(
                    "Chat error:",
                    error
                );


                if (thinking) {
                    thinking.remove();
                }


                addChatMessage(
                    "Chat service is unavailable right now. Please try again.",
                    "bot"
                );


            } finally {

                chatInput.disabled =
                    false;

                chatInput.focus();
            }

        }
    );
}


/* =========================================================
   LOAD STATS
========================================================= */

async function loadStats() {

    try {

        const response =
            await fetch(
                "/api/stats"
            );


        const data =
            await response.json();


        if (!response.ok) {
            throw new Error(
                data.error ||
                "Could not load stats."
            );
        }


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
                    ? (
                        data.by_verdict.REAL ??
                        0
                    )
                    : 0
            );


        const fake =
            data.fake ??
            data.fake_count ??
            (
                data.by_verdict
                    ? (
                        data.by_verdict.FAKE ??
                        0
                    )
                    : 0
            );


        if (statTotal) {
            statTotal.textContent =
                total;
        }


        if (statReal) {
            statReal.textContent =
                real;
        }


        if (statFake) {
            statFake.textContent =
                fake;
        }


    } catch (error) {

        console.error(
            "Stats error:",
            error
        );
    }
}


/* =========================================================
   LOAD LIVE FEED
========================================================= */

async function loadLiveFeed() {

    if (!liveFeed) {
        return;
    }


    liveFeed.innerHTML = `
        <div class="feed-empty">
            Loading live headlines...
        </div>
    `;


    try {

        const response =
            await fetch(
                "/api/live-feed"
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.error ||
                "Could not load live feed."
            );
        }


        renderLiveFeed(
            data.results ||
            data.feed ||
            []
        );


    } catch (error) {

        console.error(
            "Live feed error:",
            error
        );


        liveFeed.innerHTML = `
            <div class="feed-empty">
                Could not load live news.
            </div>
        `;
    }
}


/* =========================================================
   RENDER LIVE FEED
========================================================= */

function renderLiveFeed(results) {

    if (!liveFeed) {
        return;
    }


    liveFeed.innerHTML = "";


    if (
        !Array.isArray(results) ||
        results.length === 0
    ) {

        liveFeed.innerHTML = `
            <div class="feed-empty">
                No live headlines available.
            </div>
        `;

        return;
    }


    results.forEach(
        function (item) {

            const row =
                document.createElement(
                    "div"
                );

            row.className =
                "feed-item";


            const top =
                document.createElement(
                    "div"
                );

            top.className =
                "feed-top";


            const title =
                document.createElement(
                    "div"
                );

            title.className =
                "feed-title";


            title.textContent =
                item.headline ||
                item.title ||
                "Unknown headline";


            const verdict =
                String(
                    item.prediction ||
                    item.verdict ||
                    "UNKNOWN"
                ).toUpperCase();


            const badge =
                document.createElement(
                    "div"
                );


            badge.className =
                "feed-verdict " +
                (
                    verdict === "REAL"
                        ? "real"
                        : verdict === "FAKE"
                            ? "fake"
                            : ""
                );


            badge.textContent =
                verdict;


            top.appendChild(title);
            top.appendChild(badge);

            row.appendChild(top);


            if (
                item.confidence !== undefined &&
                item.confidence !== null
            ) {

                const meta =
                    document.createElement(
                        "div"
                    );


                meta.className =
                    "feed-meta";


                meta.textContent =
                    "Model confidence: " +
                    formatConfidence(
                        item.confidence
                    );


                row.appendChild(meta);
            }


            liveFeed.appendChild(row);
        }
    );
}


/* =========================================================
   LOAD HISTORY
========================================================= */

async function loadHistory() {

    if (!historyList) {
        return;
    }


    historyList.innerHTML = `
        <div class="history-empty">
            Loading history...
        </div>
    `;


    try {

        const response =
            await fetch(
                "/api/history"
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.error ||
                "Could not load history."
            );
        }


        renderHistory(
            data.history ||
            data.results ||
            []
        );


    } catch (error) {

        console.error(
            "History error:",
            error
        );


        historyList.innerHTML = `
            <div class="history-empty">
                Could not load history.
            </div>
        `;
    }
}


/* =========================================================
   RENDER HISTORY
========================================================= */

function renderHistory(history) {

    if (!historyList) {
        return;
    }


    historyList.innerHTML = "";


    if (
        !Array.isArray(history) ||
        history.length === 0
    ) {

        historyList.innerHTML = `
            <div class="history-empty">
                No verification history yet.
            </div>
        `;

        return;
    }


    history.forEach(
        function (item) {

            const row =
                document.createElement(
                    "div"
                );

            row.className =
                "history-item";


            const head =
                document.createElement(
                    "div"
                );

            head.className =
                "history-head";


            const headline =
                document.createElement(
                    "div"
                );

            headline.className =
                "history-headline";


            headline.textContent =
                item.headline ||
                "Unknown headline";


            const actions =
                document.createElement(
                    "div"
                );

            actions.className =
                "history-actions";


            const verdict =
                String(
                    item.verdict ||
                    item.prediction ||
                    "UNKNOWN"
                ).toUpperCase();


            const verdictElement =
                document.createElement(
                    "div"
                );


            verdictElement.className =
                "history-verdict " +
                (
                    verdict === "REAL"
                        ? "real"
                        : verdict === "FAKE"
                            ? "fake"
                            : ""
                );


            verdictElement.textContent =
                verdict;


            const deleteButton =
                document.createElement(
                    "button"
                );


            deleteButton.type =
                "button";

            deleteButton.className =
                "delete-history-btn";

            deleteButton.textContent =
                "Delete";

            deleteButton.title =
                "Delete this history item";


            if (item.id !== undefined) {

                deleteButton.dataset.id =
                    item.id;
            }


            deleteButton.addEventListener(
                "click",
                async function (event) {

                    event.preventDefault();
                    event.stopPropagation();


                    const checkId =
                        deleteButton.dataset.id;


                    if (!checkId) {

                        alert(
                            "History record ID is missing."
                        );

                        return;
                    }


                    const confirmed =
                        window.confirm(
                            "Are you sure you want to delete this history item?"
                        );


                    if (!confirmed) {
                        return;
                    }


                    deleteButton.disabled =
                        true;

                    deleteButton.textContent =
                        "Deleting...";


                    try {

                        const response =
                            await fetch(
                                `/api/history/${encodeURIComponent(checkId)}`,
                                {
                                    method:
                                        "DELETE"
                                }
                            );


                        const data =
                            await response.json();


                        if (!response.ok) {

                            throw new Error(
                                data.error ||
                                "Could not delete history item."
                            );
                        }


                        row.remove();


                        loadStats();


                        if (
                            historyList.querySelectorAll(
                                ".history-item"
                            ).length === 0
                        ) {

                            historyList.innerHTML = `
                                <div class="history-empty">
                                    No verification history yet.
                                </div>
                            `;
                        }


                    } catch (error) {

                        console.error(
                            "Delete history error:",
                            error
                        );


                        deleteButton.disabled =
                            false;

                        deleteButton.textContent =
                            "Delete";


                        alert(
                            error.message ||
                            "Could not delete history item."
                        );
                    }

                }
            );


            actions.appendChild(
                verdictElement
            );

            actions.appendChild(
                deleteButton
            );


            head.appendChild(
                headline
            );

            head.appendChild(
                actions
            );


            row.appendChild(
                head
            );


            const meta =
                document.createElement(
                    "div"
                );

            meta.className =
                "history-meta";


            const mode =
                item.mode ||
                "unknown";


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


            row.appendChild(
                meta
            );


            historyList.appendChild(
                row
            );
        }
    );
}


/* =========================================================
   LIVE FEED SIDEBAR
========================================================= */

function openLiveFeed() {

    show(liveFeedPanel);


    if (liveFeedToggle) {

        liveFeedToggle.classList.add(
            "active"
        );
    }


    if (verifyNavBtn) {

        verifyNavBtn.classList.remove(
            "active"
        );
    }


    loadLiveFeed();
}


function closeLiveFeedPanel() {

    hide(liveFeedPanel);


    if (liveFeedToggle) {

        liveFeedToggle.classList.remove(
            "active"
        );
    }


    if (verifyNavBtn) {

        verifyNavBtn.classList.add(
            "active"
        );
    }
}


if (liveFeedToggle) {

    liveFeedToggle.addEventListener(
        "click",
        function (event) {

            event.preventDefault();

            openLiveFeed();
        }
    );
}


if (closeLiveFeed) {

    closeLiveFeed.addEventListener(
        "click",
        function (event) {

            event.preventDefault();

            closeLiveFeedPanel();
        }
    );
}


if (verifyNavBtn) {

    verifyNavBtn.addEventListener(
        "click",
        function (event) {

            event.preventDefault();

            closeLiveFeedPanel();

            window.scrollTo({
                top: 0,
                behavior: "smooth"
            });
        }
    );
}


/* =========================================================
   REFRESH LIVE FEED
========================================================= */

if (refreshFeedBtn) {

    refreshFeedBtn.addEventListener(
        "click",
        function (event) {

            event.preventDefault();

            loadLiveFeed();
        }
    );
}


/* =========================================================
   INITIAL LOAD
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    function () {

        loadStats();

        loadHistory();

        /*
         * Feed is loaded in background.
         * It is displayed only when LIVE FEED
         * button is opened.
         */
        loadLiveFeed();
    }
);