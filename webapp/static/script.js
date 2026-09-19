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
   FULL PAGE VIEW (History / Analytics / Dashboard / Verify)
========================================================= */

function setFullPageSection(sectionName) {
    var sections = [
        "dashboardSection",
        "verifySection",
        "explainSection",
        "layersSection",
        "analyticsSection",
        "historySection"
    ];

    // default: show all for scroll layout unless full-page mode requested
    var fullOnly = ["analytics", "history"];

    if (fullOnly.indexOf(sectionName) !== -1) {
        sections.forEach(function(id) {
            var el = document.getElementById(id);
            if (!el) return;
            if (
                (sectionName === "analytics" && id === "analyticsSection") ||
                (sectionName === "history" && id === "historySection")
            ) {
                el.style.display = "block";
                el.classList.add("full-page-view");
            } else {
                el.style.display = "none";
                el.classList.remove("full-page-view");
            }
        });
        window.scrollTo({ top: 0, behavior: "smooth" });
        return;
    }

    // restore normal multi-section view
    sections.forEach(function(id) {
        var el = document.getElementById(id);
        if (!el) return;
        el.style.display = "";
        el.classList.remove("full-page-view");
    });
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
const historyRefreshBtn = $("historyRefreshBtn");


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
   SIDEBAR
========================================================= */

const sidebarToggle = $("sidebarToggle");
const sidebarClose = $("sidebarClose");
const appSidebar = $("appSidebar");
const sidebarOverlay = $("sidebarOverlay");
const sidebarItems =
    document.querySelectorAll(".sidebar-item");


/* =========================================================
   ADVANCED SETTINGS PANEL
========================================================= */

const settingsPanel = $("settingsPanel");
const settingsToggle = $("settingsToggle");
const closeSettings = $("closeSettings");

const layerLive = $("layerLive");
const layerFactcheck = $("layerFactcheck");
const layerRedflag = $("layerRedflag");
const layerLlm = $("layerLlm");
const layerModel = $("layerModel");

const dotLayerLive = $("dotLayerLive");
const dotLayerFactcheck = $("dotLayerFactcheck");
const dotLayerRedflag = $("dotLayerRedflag");
const dotLayerLlm = $("dotLayerLlm");
const dotLayerModel = $("dotLayerModel");

const fallbackModel = $("fallbackModel");
const llmProvider = $("llmProvider");
const settingsExplainMethod = $("settingsExplainMethod");

const thresholdSlider = $("thresholdSlider");
const thresholdValue = $("thresholdValue");

const autoRefreshFeed = $("autoRefreshFeed");
const resetSettingsBtn = $("resetSettingsBtn");

let liveFeedAutoRefreshTimer = null;


/* =========================================================
   SECTIONS
========================================================= */

const dashboardSection =
    $("dashboardSection");

const verifySection =
    $("verifySection");

const explainSection =
    $("explainSection");

const analyticsSection =
    $("analyticsSection");

const historySection =
    $("historySection");


/* =========================================================
   SIDEBAR OPEN
========================================================= */

function openSidebar() {

    if (!appSidebar) {
        return;
    }

    appSidebar.classList.add("open");

    if (sidebarOverlay) {
        sidebarOverlay.classList.add("visible");
    }

    if (sidebarToggle) {
        sidebarToggle.classList.add("open");

        sidebarToggle.setAttribute(
            "aria-expanded",
            "true"
        );
    }

    document.body.classList.add(
        "sidebar-open"
    );
}


/* =========================================================
   SIDEBAR CLOSE
========================================================= */

function closeSidebar() {

    if (appSidebar) {
        appSidebar.classList.remove("open");
    }

    if (sidebarOverlay) {
        sidebarOverlay.classList.remove(
            "visible"
        );
    }

    if (sidebarToggle) {
        sidebarToggle.classList.remove(
            "open"
        );

        sidebarToggle.setAttribute(
            "aria-expanded",
            "false"
        );
    }

    document.body.classList.remove(
        "sidebar-open"
    );
}


/* =========================================================
   SIDEBAR TOGGLE
========================================================= */

if (sidebarToggle) {

    sidebarToggle.addEventListener(
        "click",
        function(event) {

            event.preventDefault();
            event.stopPropagation();

            if (
                appSidebar &&
                appSidebar.classList.contains(
                    "open"
                )
            ) {

                closeSidebar();

            } else {

                openSidebar();
            }
        }
    );
}


/* =========================================================
   SIDEBAR CLOSE BUTTON
========================================================= */

if (sidebarClose) {

    sidebarClose.addEventListener(
        "click",
        function(event) {

            event.preventDefault();

            closeSidebar();
        }
    );
}


/* =========================================================
   SIDEBAR OVERLAY
========================================================= */

if (sidebarOverlay) {

    sidebarOverlay.addEventListener(
        "click",
        function() {

            closeSidebar();
        }
    );
}


/* =========================================================
   ACTIVE SIDEBAR ITEM
========================================================= */

function setActiveSidebarItem(
    sectionName
) {

    sidebarItems.forEach(
        function(item) {

            const itemSection =
                item.dataset.section;

            item.classList.toggle(
                "active",
                itemSection === sectionName
            );
        }
    );
}


/* =========================================================
   SCROLL TO SECTION
========================================================= */

function scrollToSection(
    element,
    behavior = "smooth"
) {

    if (!element) {
        return;
    }

    element.scrollIntoView({
        behavior: behavior,
        block: "start"
    });
}


/* =========================================================
   SIDEBAR NAVIGATION
========================================================= */

sidebarItems.forEach(
    function(item) {

        item.addEventListener(
            "click",
            function(event) {

                event.preventDefault();

                const section =
                    item.dataset.section;


                setActiveSidebarItem(
                    section
                );


                /* -----------------------------------------
                   DASHBOARD
                ----------------------------------------- */

                if (
                    section ===
                    "dashboard"
                ) {

                    closeLiveFeedPanel();

                    closeSettingsPanel();

                    closeSidebar();

                    setFullPageSection("dashboard");

                    window.scrollTo({
                        top: 0,
                        behavior: "smooth"
                    });

                    return;
                }


                /* -----------------------------------------
                   VERIFY
                ----------------------------------------- */

                if (
                    section ===
                    "verify"
                ) {

                    closeLiveFeedPanel();

                    closeSettingsPanel();

                    closeSidebar();

                    setFullPageSection("verify");

                    scrollToSection(
                        verifySection
                    );

                    return;
                }


                /* -----------------------------------------
                   LIVE FEED
                ----------------------------------------- */

                if (
                    section ===
                    "live"
                ) {

                    closeSettingsPanel();

                    closeSidebar();

                    openLiveFeed();

                    return;
                }


                /* -----------------------------------------
                   EXPLAINABLE AI
                ----------------------------------------- */

                if (
                    section ===
                    "explain"
                ) {

                    closeLiveFeedPanel();

                    closeSettingsPanel();

                    closeSidebar();

                    scrollToSection(
                        explainSection
                    );

                    return;
                }


                /* -----------------------------------------
                   ANALYTICS
                ----------------------------------------- */

                if (
                    section ===
                    "analytics"
                ) {

                    closeLiveFeedPanel();

                    closeSettingsPanel();

                    closeSidebar();

                    setFullPageSection("analytics");

                    if (typeof loadStats === "function") loadStats();

                    return;
                }


                /* -----------------------------------------
                   HISTORY
                ----------------------------------------- */

                if (
                    section ===
                    "history"
                ) {

                    closeLiveFeedPanel();

                    closeSettingsPanel();

                    closeSidebar();

                    setFullPageSection("history");

                    if (typeof loadHistory === "function") loadHistory();

                    return;
                }


                /* -----------------------------------------
                   CHAT
                ----------------------------------------- */

                if (
                    section ===
                    "chat"
                ) {

                    closeLiveFeedPanel();

                    closeSettingsPanel();

                    closeSidebar();

                    openChat();

                    return;
                }


                /* -----------------------------------------
                   ADVANCED SETTINGS
                ----------------------------------------- */

                if (
                    section ===
                    "settings"
                ) {

                    closeLiveFeedPanel();

                    closeSidebar();

                    openSettingsPanel();

                    return;
                }

            }
        );
    }
);


/* =========================================================
   QUICK CARDS
========================================================= */

const quickCards =
    document.querySelectorAll(
        ".quick-card"
    );


quickCards.forEach(
    function(card) {

        card.addEventListener(
            "click",
            function(event) {

                event.preventDefault();

                const section =
                    card.dataset.section;


                setActiveSidebarItem(
                    section
                );


                if (
                    section ===
                    "verify"
                ) {

                    scrollToSection(
                        verifySection
                    );

                } else if (
                    section ===
                    "live"
                ) {

                    openLiveFeed();

                } else if (
                    section ===
                    "analytics"
                ) {

                    scrollToSection(
                        analyticsSection
                    );

                } else if (
                    section ===
                    "history"
                ) {

                    scrollToSection(
                        historySection
                    );
                }

            }
        );
    }
);


/* =========================================================
   CHARACTER COUNTER
========================================================= */

if (headlineInput) {

    headlineInput.addEventListener(
        "input",
        function() {

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
        function(event) {

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
        async function(event) {

            event.preventDefault();
            event.stopPropagation();


            const headline =
                headlineInput.value.trim();


            if (!headline) {

                headlineInput.focus();

                return;
            }


            currentHeadline =
                headline;


            hide(resultBox);
            hide(explainResult);
            hide(explainError);


            verifyBtn.disabled =
                true;


            if (verifyBtnText) {

                verifyBtnText.textContent =
                    "Verifying...";
            }


            show(verifySpinner);
            show(verifyLoading);


            resetVerificationSteps();


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

                                headline:
                                    headline,

                                advanced_settings:
                                    getAdvancedSettings()
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


                await animationPromise;


                displayVerificationResult(
                    data
                );


                currentChatContext =
                    buildChatContext(
                        data
                    );


                loadStats();
                loadHistory();


                setTimeout(
                    function() {

                        if (resultBox) {

                            resultBox.scrollIntoView({
                                behavior:
                                    "smooth",

                                block:
                                    "nearest"
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

                verifyBtn.disabled =
                    false;


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
        function(step) {

            step.classList.remove(
                "active",
                "done"
            );


            const status =
                step.querySelector(
                    ".step-status"
                );


            if (status) {

                status.textContent =
                    "";
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


        step.classList.add(
            "active"
        );


        if (loadingTitle) {

            loadingTitle.textContent =
                titles[i];
        }


        if (loadingSubtitle) {

            loadingSubtitle.textContent =
                `Verification layer ${i + 1} of 5`;
        }


        await sleep(700);


        step.classList.remove(
            "active"
        );

        step.classList.add(
            "done"
        );
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

function displayVerificationResult(
    data
) {

    if (!resultBox) {
        return;
    }


    resultBox.classList.remove(
        "real",
        "fake",
        "misleading",
        "error"
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


    let scoreNumber =
        "—";


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


    /* VERDICT */

    if (verdict === "REAL") {

        resultBox.classList.add(
            "real"
        );

        verdictText.textContent =
            "REAL NEWS";

        verdictIcon.textContent =
            "✓";


    } else if (
        verdict === "FAKE"
    ) {

        resultBox.classList.add(
            "fake"
        );

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


    /* BASIC DATA */

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


    /* PUBLISHER */

    if (data.publisher) {

        show(publisherRow);

        if (resultPublisher) {

            resultPublisher.textContent =
                data.publisher;
        }

    } else {

        hide(publisherRow);
    }


    /* RATING */

    if (data.rating) {

        show(ratingRow);

        if (resultRating) {

            resultRating.textContent =
                data.rating;
        }

    } else {

        hide(ratingRow);
    }


    /* REASON */

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


    /* SOURCES */

    if (
        Array.isArray(data.sources) &&
        data.sources.length > 0
    ) {

        show(sourcesBox);

        sourcesList.innerHTML =
            "";


        data.sources.forEach(
            function(source) {

                const li =
                    document.createElement(
                        "li"
                    );


                if (
                    source &&
                    typeof source ===
                    "object"
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


                sourcesList.appendChild(
                    li
                );
            }
        );

    } else {

        hide(sourcesBox);
    }


    /* VERIFIED / DISPUTED */

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


    list.innerHTML =
        "";


    values.forEach(
        function(value) {

            const li =
                document.createElement(
                    "li"
                );


            if (
                value &&
                typeof value ===
                "object"
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


            list.appendChild(
                li
            );
        }
    );


    show(box);
}


/* =========================================================
   ERROR
========================================================= */

function showErrorResult(
    message
) {

    if (!resultBox) {
        return;
    }


    resultBox.classList.remove(
        "real",
        "fake",
        "misleading"
    );


    resultBox.classList.add(
        "error"
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

function formatConfidence(
    value
) {

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

function buildChatContext(
    data
) {

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
        async function(event) {

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


            explainBtn.disabled =
                true;


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


                renderExplanation(
                    data
                );


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

function renderExplanation(
    data
) {

    if (!wordImportance) {
        return;
    }


    wordImportance.innerHTML =
        "";


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
        function(item) {

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


            if (
                Number.isNaN(weight)
            ) {

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


            word.appendChild(
                wordText
            );

            word.appendChild(
                weightText
            );

            wordImportance.appendChild(
                word
            );
        }
    );


    show(explainResult);
}


/* =========================================================
   EXPLAIN ERROR
========================================================= */

function showExplainError(
    message
) {

    if (!explainError) {
        return;
    }


    explainError.textContent =
        message ||
        "Explanation failed.";


    show(explainError);
}


/* =========================================================
   OPEN CHAT
========================================================= */

function openChat() {

    if (!chatWindow) {
        return;
    }


    var cb = document.getElementById("chatbot"); if (cb) cb.classList.add("fullpage-mode"); show(chatWindow);


    setTimeout(
        function() {

            if (chatInput) {
                chatInput.focus();
            }

        },
        100
    );
}


/* =========================================================
   CHAT OPEN / CLOSE
========================================================= */

if (chatToggle) {

    chatToggle.addEventListener(
        "click",
        function(event) {

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

                setActiveSidebarItem(
                    "chat"
                );


                setTimeout(
                    function() {

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
        function(event) {

            event.preventDefault();
            event.stopPropagation();

            var cb = document.getElementById("chatbot"); if (cb) cb.classList.remove("fullpage-mode"); hide(chatWindow);
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
        async function(event) {

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


            chatInput.value =
                "";


            chatInput.disabled =
                true;


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
                                        role:
                                            "user",

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
        try { updateAnalyticsProUI(statTotal.textContent, statReal && statReal.textContent, statFake && statFake.textContent); } catch(e) {}
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

function renderLiveFeed(
    results
) {

    if (!liveFeed) {
        return;
    }


    liveFeed.innerHTML =
        "";


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
        function(item) {

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


            top.appendChild(
                title
            );

            top.appendChild(
                badge
            );

            row.appendChild(
                top
            );


            if (
                item.confidence !==
                    undefined &&
                item.confidence !==
                    null
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


                row.appendChild(
                    meta
                );
            }


            liveFeed.appendChild(
                row
            );
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

function renderHistory(
    history
) {

    if (!historyList) {
        return;
    }


    historyList.innerHTML =
        "";


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
        function(item) {

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


            deleteButton.className = "delete-history-btn history-delete-btn";


            deleteButton.textContent = "×";


            deleteButton.title =
                "Delete this history item";


            if (
                item.id !== undefined
            ) {

                deleteButton.dataset.id =
                    item.id;
            }


            deleteButton.addEventListener(
                "click",
                async function(event) {

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


                    // Direct delete - no confirm


                    deleteButton.disabled =
                        true;


                    deleteButton.textContent = "…";


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


                        deleteButton.textContent = "×";


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
                        ? " • " +
                          timestamp
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
   OPEN LIVE FEED
========================================================= */

function openLiveFeed() {

    closeSettingsPanel();

    if (liveFeedPanel) liveFeedPanel.classList.add("fullpage-mode");
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


    setActiveSidebarItem(
        "live"
    );


    loadLiveFeed();

    startLiveFeedAutoRefresh();
}


/* =========================================================
   CLOSE LIVE FEED
========================================================= */

function closeLiveFeedPanel() {

    if (liveFeedPanel) liveFeedPanel.classList.remove("fullpage-mode");
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


    if (
        !appSidebar ||
        !appSidebar.classList.contains(
            "open"
        )
    ) {

        setActiveSidebarItem(
            "verify"
        );
    }


    stopLiveFeedAutoRefresh();
}


/* =========================================================
   LIVE FEED TOP BUTTON
========================================================= */

if (liveFeedToggle) {

    liveFeedToggle.addEventListener(
        "click",
        function(event) {

            event.preventDefault();

            openLiveFeed();
        }
    );
}


/* =========================================================
   CLOSE LIVE FEED
========================================================= */

if (closeLiveFeed) {

    closeLiveFeed.addEventListener(
        "click",
        function(event) {

            event.preventDefault();

            closeLiveFeedPanel();
        }
    );
}


/* =========================================================
   VERIFY TOP BUTTON
========================================================= */

if (verifyNavBtn) {

    verifyNavBtn.addEventListener(
        "click",
        function(event) {

            event.preventDefault();

            closeLiveFeedPanel();

            closeSettingsPanel();

            setActiveSidebarItem(
                "verify"
            );

            scrollToSection(
                verifySection
            );
        }
    );
}


/* =========================================================
   REFRESH LIVE FEED
========================================================= */

if (refreshFeedBtn) {

    refreshFeedBtn.addEventListener(
        "click",
        function(event) {

            event.preventDefault();

            loadLiveFeed();
        }
    );
}


/* =========================================================
   HISTORY REFRESH
========================================================= */

if (historyRefreshBtn) {

    historyRefreshBtn.addEventListener(
        "click",
        function(event) {

            event.preventDefault();

            loadHistory();
            loadStats();
        }
    );
}


/* =========================================================
   ADVANCED SETTINGS — OPEN / CLOSE
========================================================= */

function openSettingsPanel() {
    if (settingsPanel) settingsPanel.classList.add("fullpage-mode");

    var cb = document.getElementById("chatbot"); if (cb) cb.classList.remove("fullpage-mode"); hide(chatWindow);

    hide(liveFeedPanel);

    if (liveFeedToggle) {

        liveFeedToggle.classList.remove(
            "active"
        );
    }


    show(settingsPanel);


    if (settingsToggle) {

        settingsToggle.classList.add(
            "active"
        );
    }


    setActiveSidebarItem(
        "settings"
    );
}


function closeSettingsPanel() {
    if (settingsPanel) settingsPanel.classList.remove("fullpage-mode");

    hide(settingsPanel);


    if (settingsToggle) {

        settingsToggle.classList.remove(
            "active"
        );
    }
}


if (settingsToggle) {

    settingsToggle.addEventListener(
        "click",
        function(event) {

            event.preventDefault();

            if (
                settingsPanel &&
                !settingsPanel.classList.contains(
                    "hidden"
                )
            ) {

                closeSettingsPanel();

            } else {

                openSettingsPanel();
            }
        }
    );
}


if (closeSettings) {

    closeSettings.addEventListener(
        "click",
        function(event) {

            event.preventDefault();

            closeSettingsPanel();
        }
    );
}


/* =========================================================
   ADVANCED SETTINGS — LAYER TOGGLES
========================================================= */

function wireLayerToggle(
    checkbox,
    dot
) {

    if (!checkbox || !dot) {
        return;
    }

    checkbox.addEventListener(
        "change",
        function() {

            dot.classList.toggle(
                "on",
                checkbox.checked
            );

            dot.classList.toggle(
                "off",
                !checkbox.checked
            );
        }
    );
}


wireLayerToggle(layerLive, dotLayerLive);
wireLayerToggle(layerFactcheck, dotLayerFactcheck);
wireLayerToggle(layerRedflag, dotLayerRedflag);
wireLayerToggle(layerLlm, dotLayerLlm);
wireLayerToggle(layerModel, dotLayerModel);


/* =========================================================
   ADVANCED SETTINGS — THRESHOLD SLIDER
========================================================= */

if (thresholdSlider && thresholdValue) {

    thresholdSlider.addEventListener(
        "input",
        function() {

            thresholdValue.textContent =
                thresholdSlider.value +
                "%";
        }
    );
}


/* =========================================================
   ADVANCED SETTINGS — AUTO-REFRESH LIVE FEED
========================================================= */

function startLiveFeedAutoRefresh() {

    stopLiveFeedAutoRefresh();

    const enabled =
        !autoRefreshFeed ||
        autoRefreshFeed.checked;

    if (!enabled) {
        return;
    }

    liveFeedAutoRefreshTimer =
        setInterval(
            function() {

                if (
                    liveFeedPanel &&
                    !liveFeedPanel.classList.contains(
                        "hidden"
                    )
                ) {

                    loadLiveFeed();
                }

            },
            30000
        );
}


function stopLiveFeedAutoRefresh() {

    if (liveFeedAutoRefreshTimer) {

        clearInterval(
            liveFeedAutoRefreshTimer
        );

        liveFeedAutoRefreshTimer =
            null;
    }
}


if (autoRefreshFeed) {

    autoRefreshFeed.addEventListener(
        "change",
        function() {

            if (
                liveFeedPanel &&
                !liveFeedPanel.classList.contains(
                    "hidden"
                )
            ) {

                startLiveFeedAutoRefresh();
            }
        }
    );
}


/* =========================================================
   ADVANCED SETTINGS — COLLECT CURRENT VALUES
========================================================= */

function getAdvancedSettings() {

    return {

        layers: {

            live_verification:
                layerLive
                    ? layerLive.checked
                    : true,

            fact_check:
                layerFactcheck
                    ? layerFactcheck.checked
                    : true,

            red_flag:
                layerRedflag
                    ? layerRedflag.checked
                    : true,

            llm_reasoning:
                layerLlm
                    ? layerLlm.checked
                    : false,

            model_fallback:
                layerModel
                    ? layerModel.checked
                    : true
        },

        fallback_model:
            fallbackModel
                ? fallbackModel.value
                : "auto",

        llm_provider:
            llmProvider
                ? llmProvider.value
                : "gemini",

        explain_method:
            settingsExplainMethod
                ? settingsExplainMethod.value
                : "lime",

        confidence_threshold:
            thresholdSlider
                ? Number(thresholdSlider.value)
                : 60
    };
}


/* =========================================================
   ADVANCED SETTINGS — RESET
========================================================= */

if (resetSettingsBtn) {

    resetSettingsBtn.addEventListener(
        "click",
        function(event) {

            event.preventDefault();


            if (layerLive) {
                layerLive.checked = true;
            }

            if (layerFactcheck) {
                layerFactcheck.checked = true;
            }

            if (layerRedflag) {
                layerRedflag.checked = true;
            }

            if (layerLlm) {
                layerLlm.checked = false;
            }

            if (layerModel) {
                layerModel.checked = true;
            }


            [
                [layerLive, dotLayerLive],
                [layerFactcheck, dotLayerFactcheck],
                [layerRedflag, dotLayerRedflag],
                [layerLlm, dotLayerLlm],
                [layerModel, dotLayerModel]
            ].forEach(
                function(pair) {

                    const checkbox = pair[0];
                    const dot = pair[1];

                    if (!checkbox || !dot) {
                        return;
                    }

                    dot.classList.toggle(
                        "on",
                        checkbox.checked
                    );

                    dot.classList.toggle(
                        "off",
                        !checkbox.checked
                    );
                }
            );


            if (fallbackModel) {
                fallbackModel.value = "auto";
            }

            if (llmProvider) {
                llmProvider.value = "gemini";
            }

            if (settingsExplainMethod) {
                settingsExplainMethod.value = "lime";
            }

            if (thresholdSlider) {
                thresholdSlider.value = 60;
            }

            if (thresholdValue) {
                thresholdValue.textContent = "60%";
            }

            if (autoRefreshFeed) {
                autoRefreshFeed.checked = true;
            }
        }
    );
}


/* =========================================================
   ESC KEY
========================================================= */

document.addEventListener(
    "keydown",
    function(event) {

        if (
            event.key ===
            "Escape"
        ) {

            closeSidebar();

            closeLiveFeedPanel();

            closeSettingsPanel();

            var cb = document.getElementById("chatbot"); if (cb) cb.classList.remove("fullpage-mode"); hide(chatWindow);
        }
    }
);


/* =========================================================
   SCROLL ACTIVE SECTION
========================================================= */

const sectionObserver =
    new IntersectionObserver(
        function(entries) {

            let visibleEntry =
                null;


            entries.forEach(
                function(entry) {

                    if (
                        entry.isIntersecting
                    ) {

                        visibleEntry =
                            entry;
                    }
                }
            );


            if (!visibleEntry) {
                return;
            }


            const id =
                visibleEntry.target.id;


            const sectionMap = {

                dashboardSection:
                    "dashboard",

                verifySection:
                    "verify",

                explainSection:
                    "explain",

                analyticsSection:
                    "analytics",

                historySection:
                    "history"
            };


            if (
                sectionMap[id]
            ) {

                setActiveSidebarItem(
                    sectionMap[id]
                );
            }

        },
        {
            root: null,

            threshold: 0.25
        }
    );


[
    dashboardSection,
    verifySection,
    explainSection,
    analyticsSection,
    historySection
]
.forEach(
    function(section) {

        if (section) {

            sectionObserver.observe(
                section
            );
        }
    }
);


/* =========================================================
   INITIAL LOAD
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    function() {

        loadStats();

        loadHistory();

        /*
         * Feed is loaded in background.
         * It opens only when requested.
         */
        loadLiveFeed();


        setActiveSidebarItem(
            "dashboard"
        );
    }
);


/* =========================================================
   THEME + SAVE SETTINGS
========================================================= */

function applyTheme(theme) {
    if (theme === "light") {
        document.body.classList.add("light-theme");
    } else {
        document.body.classList.remove("light-theme");
    }
    localStorage.setItem("veriquest_theme", theme);

    var darkBtn = document.getElementById("themeDarkBtn");
    var lightBtn = document.getElementById("themeLightBtn");
    if (darkBtn) darkBtn.classList.toggle("active", theme === "dark");
    if (lightBtn) lightBtn.classList.toggle("active", theme === "light");
}

(function initTheme() {
    var saved = localStorage.getItem("veriquest_theme") || "dark";
    applyTheme(saved);
})();

var themeDarkBtn = document.getElementById("themeDarkBtn");
var themeLightBtn = document.getElementById("themeLightBtn");
if (themeDarkBtn) {
    themeDarkBtn.addEventListener("click", function() { applyTheme("dark"); });
}
if (themeLightBtn) {
    themeLightBtn.addEventListener("click", function() { applyTheme("light"); });
}

function saveSettingsToStorage() {
    var settings = {
        layerLive: document.getElementById("layerLive") ? document.getElementById("layerLive").checked : true,
        layerFactcheck: document.getElementById("layerFactcheck") ? document.getElementById("layerFactcheck").checked : true,
        layerRedflag: document.getElementById("layerRedflag") ? document.getElementById("layerRedflag").checked : true,
        layerLlm: document.getElementById("layerLlm") ? document.getElementById("layerLlm").checked : false,
        layerModel: document.getElementById("layerModel") ? document.getElementById("layerModel").checked : true,
        fallbackModel: document.getElementById("fallbackModel") ? document.getElementById("fallbackModel").value : "auto",
        llmProvider: document.getElementById("llmProvider") ? document.getElementById("llmProvider").value : "gemini",
        explainMethod: document.getElementById("settingsExplainMethod") ? document.getElementById("settingsExplainMethod").value : "lime",
        threshold: document.getElementById("thresholdSlider") ? document.getElementById("thresholdSlider").value : "60",
        autoRefreshFeed: document.getElementById("autoRefreshFeed") ? document.getElementById("autoRefreshFeed").checked : true,
        theme: localStorage.getItem("veriquest_theme") || "dark"
    };
    localStorage.setItem("veriquest_settings", JSON.stringify(settings));
    return settings;
}

function loadSettingsFromStorage() {
    try {
        var raw = localStorage.getItem("veriquest_settings");
        if (!raw) return;
        var s = JSON.parse(raw);
        function setCheck(id, val) {
            var el = document.getElementById(id);
            if (el && typeof val === "boolean") {
                el.checked = val;
                el.dispatchEvent(new Event("change"));
            }
        }
        setCheck("layerLive", s.layerLive);
        setCheck("layerFactcheck", s.layerFactcheck);
        setCheck("layerRedflag", s.layerRedflag);
        setCheck("layerLlm", s.layerLlm);
        setCheck("layerModel", s.layerModel);
        if (document.getElementById("fallbackModel") && s.fallbackModel) document.getElementById("fallbackModel").value = s.fallbackModel;
        if (document.getElementById("llmProvider") && s.llmProvider) document.getElementById("llmProvider").value = s.llmProvider;
        if (document.getElementById("settingsExplainMethod") && s.explainMethod) document.getElementById("settingsExplainMethod").value = s.explainMethod;
        if (document.getElementById("thresholdSlider") && s.threshold) {
            document.getElementById("thresholdSlider").value = s.threshold;
            var tv = document.getElementById("thresholdValue");
            if (tv) tv.textContent = s.threshold + "%";
        }
        setCheck("autoRefreshFeed", s.autoRefreshFeed);
        if (s.theme) applyTheme(s.theme);
    } catch (e) {
        console.warn("Could not load settings", e);
    }
}

var saveSettingsBtn = document.getElementById("saveSettingsBtn");
if (saveSettingsBtn) {
    saveSettingsBtn.addEventListener("click", function() {
        saveSettingsToStorage();
        var prev = saveSettingsBtn.textContent;
        saveSettingsBtn.textContent = "Saved ✓";
        setTimeout(function() { saveSettingsBtn.textContent = prev; }, 1500);
    });
}

document.addEventListener("DOMContentLoaded", function() {
    loadSettingsFromStorage();
});


/* =========================================================
   ANALYTICS PRO UI UPDATE
========================================================= */

function updateAnalyticsProUI(total, real, fake) {
    total = Number(total) || 0;
    real = Number(real) || 0;
    fake = Number(fake) || 0;

    var elTotal = document.getElementById("statTotal");
    var elReal = document.getElementById("statReal");
    var elFake = document.getElementById("statFake");
    if (elTotal) elTotal.textContent = total;
    if (elReal) elReal.textContent = real;
    if (elFake) elFake.textContent = fake;

    var realPct = total > 0 ? (real / total) * 100 : 0;
    var fakePct = total > 0 ? (fake / total) * 100 : 0;

    var acc = document.getElementById("accuracyPct");
    if (acc) acc.textContent = total > 0 ? (realPct.toFixed(1) + "%") : "—";

    var lr = document.getElementById("legendReal");
    var lrp = document.getElementById("legendRealPct");
    var lf = document.getElementById("legendFake");
    var lfp = document.getElementById("legendFakePct");
    if (lr) lr.textContent = real;
    if (lrp) lrp.textContent = realPct.toFixed(1) + "%";
    if (lf) lf.textContent = fake;
    if (lfp) lfp.textContent = fakePct.toFixed(1) + "%";

    // donut: circumference ~ 2*pi*48 ≈ 301.6
    var circ = 301.6;
    var donut = document.getElementById("donutReal");
    if (donut) {
        var realLen = (realPct / 100) * circ;
        donut.setAttribute("stroke-dasharray", realLen + " " + circ);
    }

    var tip = document.getElementById("accuracyTip");
    if (tip) {
        if (total === 0) {
            tip.textContent = "Run more checks to see accuracy insights.";
        } else if (realPct >= 60) {
            tip.textContent = "Great job! Most of your verified headlines are classified as real.";
        } else {
            tip.textContent = "Many headlines were flagged as fake or disputed — review sources carefully.";
        }
    }

    var overall = document.getElementById("overallPerf");
    if (overall) {
        overall.textContent = total > 0 ? (Math.round((realPct * 0.5 + 50)) + "%") : "—";
    }
}


(function watchStats() {
    function sync() {
        var t = document.getElementById("statTotal");
        var r = document.getElementById("statReal");
        var f = document.getElementById("statFake");
        if (t && r && f && typeof updateAnalyticsProUI === "function") {
            updateAnalyticsProUI(t.textContent, r.textContent, f.textContent);
        }
    }
    setInterval(sync, 1500);
})();
