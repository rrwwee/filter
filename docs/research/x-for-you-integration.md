# X For You integration: source-backed feasibility

Research for [Investigate reliable access to X For You posts](https://github.com/rrwwee/filter/issues/4), part of [Find the way to a local X feed filter](https://github.com/rrwwee/filter/issues/1). Researched 2026-10-19. This is planning evidence, not an implementation or a live compatibility certification.

## Answer

An isolated-world Chrome content script reading rendered posts and reversibly hiding their timeline containers is a credible starting integration. Existing extension source demonstrates selectors, quote extraction, tab detection, timeline replacement observation, and CSS hiding. It also demonstrates how much undocumented structure requires maintenance. No signed-in X session was inspected, so current layout, performance, post identity, DOM reuse, and zero-gap hiding remain unverified.

Prefer a DOM-first adapter as the candidate for a bounded validation prototype. Keep page-world React access or response interception as explicit fallback options, not assumed requirements. The first version can classify the text visible in For You; it cannot honestly promise to understand all content behind a click.

## Evidence and its limits

- **Verified documentation:** Chrome describes content-script access, navigation events, and service-worker termination. X describes its feed at a product level.
- **Verified source inspection:** Control Panel for Twitter at commit `7e6a8b07c38aa18903db5ca505578343ef35faf1` (package version 4.25.1). Its implementation was read, not executed. The conclusions below say what code does or attempts; they do not establish that every selector works for Rory today.
- **Unverified:** No authenticated page observation, captured DOM fixtures, installed extension trial, memory measurement, or network trace. Actual element recycling must be tested rather than inferred from infinite scrolling.

## Integration choices

| Candidate | Evidence and tradeoff | Assessment |
| --- | --- | --- |
| Rendered DOM in isolated content script | Shares the DOM while separating JavaScript state from X. Can read text and alter styling without accessing X internals. Limited to rendered context. | First candidate to validate. |
| Page-world script accessing React data | Control Panel injects a page script and reads React properties for some features. Could expose additional context but relies on private object shape and shares the page execution environment. | Escalate only for a demonstrated missing requirement. |
| Observe/intercept X response data | Chrome webRequest exposes request lifecycle and headers, not a general response-body editing interface. A page fetch/XHR wrapper would be a different mechanism, requiring its own validation, payload parsing, and DOM association. | No evidence this is necessary for first scope. |
| Independently fetch an API feed | No authenticated For You API contract was established by this pass. A separate feed would additionally need to match the items and ordering shown in X. | Not a supported foundation from this evidence. |

Chrome documents DOM reading, modification, messaging, isolated execution, static URL matching, and programmatic injection. Its `document_start` timing does not promise that an asynchronous model finishes before a post paints. A static script on `https://x.com/*` is a plausible host boundary; runtime checks must restrict actual filtering to For You. Matching only `/home` risks missing entry from another SPA route. Static injection need not request `scripting`; programmatic injection does. Do not request cookies, debugger, or network interception for the DOM-only candidate. Settings need storage; other permissions depend on runtime choices. [Chrome content scripts](https://developer.chrome.com/docs/extensions/develop/concepts/content-scripts)

Control Panel's [MV3 manifest](https://github.com/insin/control-panel-for-twitter/blob/7e6a8b07c38aa18903db5ca505578343ef35faf1/manifest.mv3.json) uses site-matched content scripts at document start, storage permission, and a web-accessible page script. Its [content script](https://github.com/insin/control-panel-for-twitter/blob/7e6a8b07c38aa18903db5ca505578343ef35faf1/content.js) injects that script and bridges settings. This is a useful reference, not a minimum permission prescription for this project.

Chrome's documented webRequest API requires its permission plus host access and exposes events such as request, response headers, and completion. It does not offer a response-body field for reading a timeline JSON payload. [Chrome webRequest](https://developer.chrome.com/docs/extensions/reference/api/webRequest)

## Feed boundary and available context

X documents that For You includes recommendations, followed accounts/topics, and potentially promoted posts or reposts. It is distinct from Following, and X remembers the selected tab. Opening post text can take the user to a detail page with additional information. This supports checking tab state as well as route and treating previews as incomplete. [X timeline help](https://help.x.com/en/using-x/x-timeline)

Control Panel source uses `/home`, a primary-column timeline selector, `[data-testid="tweet"]`, and selected tab state. Its first-tab interpretation of For You is evidence of a working strategy the author intends, not a stable X contract. Labels can be localized; positions can change or include pinned lists. Require a positive For You match, not merely a URL or absence of Following. Source references: [paths and selectors](https://github.com/insin/control-panel-for-twitter/blob/7e6a8b07c38aa18903db5ca505578343ef35faf1/script.js#L2238-L2267), [home tab/timeline observation](https://github.com/insin/control-panel-for-twitter/blob/7e6a8b07c38aa18903db5ca505578343ef35faf1/script.js#L7543-L7580), [tab interpretation](https://github.com/insin/control-panel-for-twitter/blob/7e6a8b07c38aa18903db5ca505578343ef35faf1/script.js#L7731-L7754).

The candidate extraction record should distinguish:

- Outer post identity/permalink and author, visible text, links/cards, and visible media description when present.
- Quoted post text and attribution in separate fields; unavailable quotes explicitly marked unavailable.
- Repost/social context separately from the author and text being classified.
- Truncation/show-more indicators and missing content, rather than pretending the preview is complete.

These are proposed requirements, not all verified extractors. Control Panel reads quote author, time, and text with emoji image alt text; it separately recognizes quote, unavailable quote, repost, and promoted containers. Its selectors depend on nested markup and localized quote text. A single `textContent` call over the outer item would mix author names, counters, controls, and quoted text. [Quote extraction and item typing](https://github.com/insin/control-panel-for-twitter/blob/7e6a8b07c38aa18903db5ca505578343ef35faf1/script.js#L5620-L5695)

For “hide posts that require clicking before they get to the point,” visible text can support a presentation judgment, but cannot prove what an external article, thread, video, image, or collapsed long post eventually says. Decide whether this means judging the preview alone. No automatic clicking or external-page fetching is proposed here.

## Hiding, restoration, scrolling, and reuse

Control Panel observes timeline additions, replacement of tabbed timelines, and replacement of their parent loading container. It loops through timeline children, finds a post, computes a decision, and toggles a class on the item's first child. The class uses `display: none !important`. [Timeline observer](https://github.com/insin/control-panel-for-twitter/blob/7e6a8b07c38aa18903db5ca505578343ef35faf1/script.js#L3844-L3953), [item processing and class toggling](https://github.com/insin/control-panel-for-twitter/blob/7e6a8b07c38aa18903db5ca505578343ef35faf1/script.js#L6135-L6333), [hide selector](https://github.com/insin/control-panel-for-twitter/blob/7e6a8b07c38aa18903db5ca505578343ef35faf1/script.js#L4344-L4350), [hide rule](https://github.com/insin/control-panel-for-twitter/blob/7e6a8b07c38aa18903db5ca505578343ef35faf1/script.js#L5190-L5195)

This demonstrates reversible styling, not proof that this exact target leaves no gap under all virtualized layouts. CSS `display: none` removes that element's box; a parent with fixed sizing or translated positioning may still reserve space. [MDN display](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/display#none)

Proposed validation invariants:

1. Never delete React-owned nodes as the initial strategy. Apply a namespaced reversible style to the experimentally correct container; restore on disable, scope exit, or changed decision.
2. Key decisions by post identity plus content/instruction/model versions, not element object or timeline index alone. Re-read identity before applying any asynchronous result.
3. Observe added and replaced descendants and relevant text/attribute changes. Detach observers and cancel or ignore stale work when a timeline leaves scope. A reused node must not inherit another post's hidden state.
4. Batch reads and writes, bound queued inference, and test heavy filtering near the feed end. Empty visible space must not stop X from loading more posts or cause an endless load/classify cycle.
5. Exclude non-post modules deliberately. Verify reposts, ads, quote cards, connected thread items, and unavailable content rather than treating every timeline child as one ordinary post.

MutationObserver can watch child lists, descendants, attributes, and character data, with explicit configuration. The need to observe identity changes inside existing nodes is a design precaution; source inspection did not prove X reuses nodes in that specific way. [MDN observer configuration](https://developer.mozilla.org/en-US/docs/Web/API/MutationObserver/observe)

## Navigation, execution, and lifecycle

The Chrome webNavigation API supplies `onHistoryStateUpdated` for history changes and requires the `webNavigation` permission. DOM tab changes still need their own detection. Browser back/forward cache restoration can occur without DOMContentLoaded. Prefer a deliberate combination of scope checks, tab/timeline observation, and navigation handling; do not rely on initial load alone. [Chrome navigation](https://developer.chrome.com/docs/extensions/reference/api/webNavigation)

Control Panel handles route versus modal-underlying-page differences, app rerenders, title changes, and tab/timeline replacements. Some route logic walks private React fiber data. Our narrower scope should first test whether simpler visible-state detection suffices. [Route logic](https://github.com/insin/control-panel-for-twitter/blob/7e6a8b07c38aa18903db5ca505578343ef35faf1/script.js#L2694-L2719), [rerender/title observers](https://github.com/insin/control-panel-for-twitter/blob/7e6a8b07c38aa18903db5ca505578343ef35faf1/script.js#L3554-L3606). The same source explicitly records prior breakage in a React-property helper: [private props helper](https://github.com/insin/control-panel-for-twitter/blob/7e6a8b07c38aa18903db5ca505578343ef35faf1/script.js#L5697-L5714).

DOM extraction and hide/restore belong with the page content script; model-host location remains a separate runtime decision. Do not store the only queue, cache index, or pending-result ownership in a service worker's globals. Chrome normally terminates an inactive extension worker after 30 seconds, with other execution limits, and warns that globals are lost. Messages and requests must tolerate restarts and stale/disconnected tabs. [Chrome worker lifecycle](https://developer.chrome.com/docs/extensions/develop/concepts/service-workers/lifecycle)

## Minimum next experiment and decisions

A later, explicitly authorized prototype needs a signed-in desktop Chrome X session (Rory's ordinary access; no credential sharing). It should use fixed keep/hide results initially so DOM correctness is isolated from model quality. Save sanitized local fixtures and measurements only with user consent.

- Verify For You recognition after direct load, Following switch, profile/detail/modal navigation, back/forward, reload, and return from a suspended/background tab. Out-of-scope posts must regain their ordinary appearance.
- Sample ordinary text, emoji, link cards, media-only posts, reposts, quotes, unavailable quotes, long previews, connected thread items, promoted content, and non-post modules. Verify outer permalink identity independently of quoted permalink identity.
- Scroll through several loading batches and back; hold an asynchronous decision while navigating or changing an item; verify no stale hide result transfers to a different post.
- Hide most and then all visible posts. Measure gaps, scroll jumps, loading continuity, DOM/observer counts, and restoration when filtering is disabled or the instruction changes.
- Repeat at least for Rory's actual locale, zoom, window size, and other feed-modifying extensions. This pass establishes no mobile compatibility commitment.

Precise newly available questions:

1. **Prototype:** Which reversible container/style combination hides and restores posts without layout gaps or broken infinite scrolling in Rory's For You feed?
2. **Grilling:** Does “withholds the point until I click” mean judging only what appears in the feed preview, and how should media-only or incomplete posts behave?
3. **Grilling:** When For You or post identity cannot be recognized confidently, should filtering stop with a visible extension status and keep the feed readable?

The adapter's selector set and fixture suite should be versioned separately from model behavior. A selector mismatch must be distinguishable from “no matches”; otherwise silent site breakage would look like a permissive filtering instruction. These are design recommendations pending the above decisions and prototype, not completed product decisions.
