package com.accessibility.test

import android.graphics.Rect
import android.os.Build
import android.view.accessibility.AccessibilityNodeInfo
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.lifecycle.Lifecycle
import androidx.test.espresso.Espresso
import androidx.test.espresso.Espresso.onView
import androidx.test.espresso.action.GeneralLocation
import androidx.test.espresso.action.GeneralSwipeAction
import androidx.test.espresso.action.Press
import androidx.test.espresso.action.Swipe
import androidx.test.espresso.matcher.ViewMatchers.isRoot
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.google.android.apps.common.testing.accessibility.framework.AccessibilityCheckResult.AccessibilityCheckResultType
import com.google.android.apps.common.testing.accessibility.framework.AccessibilityHierarchyCheck
import com.google.android.apps.common.testing.accessibility.framework.AccessibilityHierarchyCheckResult
import com.google.android.apps.common.testing.accessibility.framework.Parameters
import com.google.android.apps.common.testing.accessibility.framework.checks.SpeakableTextPresentCheck
import com.google.android.apps.common.testing.accessibility.framework.checks.TextContrastCheck
import com.google.android.apps.common.testing.accessibility.framework.checks.TouchTargetSizeCheck
import com.google.android.apps.common.testing.accessibility.framework.uielement.AccessibilityHierarchyAndroid
import com.google.android.apps.common.testing.accessibility.framework.uielement.ViewHierarchyElement
import com.google.android.apps.common.testing.accessibility.framework.utils.contrast.BitmapImage
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.util.Locale

/**
 * Instrumented accessibility test — requires a real Android device connected via ADB.
 *
 * Runs Google's Accessibility Test Framework (ATF) checks on the AccessibilityNodeInfo tree
 * (UiAutomation.rootInActiveWindow). Espresso's AccessibilityChecks.enable() cannot be used for
 * Jetpack Compose: it walks the View hierarchy, where AndroidComposeView has no child views, and
 * ATF itself reports Compose content as NOT_RUN there. A hierarchy built from
 * AccessibilityNodeInfo is populated by Compose's semantics and is supported by ATF.
 *
 * Checks (ATF implementations, default thresholds):
 *   SpeakableTextPresentCheck — focusable element with no speakable text. ATF counts the text of
 *                               non-focusable descendants, as TalkBack does (e.g. Button { Text() }).
 *   TouchTargetSizeCheck      — clickable element smaller than 48dp x 48dp.
 *   TextContrastCheck         — text contrast estimated from a screenshot, because node infos do
 *                               not expose text colors.
 *
 * Counted results: every ATF ERROR ("clearly an accessibility bug"), plus the screenshot contrast
 * result RESULT_ID_TEXTVIEW_HEURISTIC_CONTRAST_NOT_SUFFICIENT. ATF can only estimate contrast for
 * Compose text, so it reports that result as a WARNING; it means the estimated ratio is below the
 * required one (3:1 when the text size is unknown). The "borderline" contrast warning and all other
 * WARNING/INFO results are not counted.
 *
 * Strategy: wait until Compose has populated the accessibility tree, then check each scroll
 * position (slow, overlapping steps until the content stops moving) without throwing, and throw
 * once at the end. "[DIAG]" lines after the list describe each pass; they are not issues.
 * The test always fails, even with 0 issues: the failure message is the only channel back to the
 * pipeline, and the per-pass diagnostics are the evidence that the screen was actually read.
 */
@RunWith(AndroidJUnit4::class)
class AccessibilityInstrumentedTest {

    @get:Rule
    val composeTestRule = createAndroidComposeRule<MainActivity>()

    private val checks: List<AccessibilityHierarchyCheck> = listOf(
        SpeakableTextPresentCheck(),
        TouchTargetSizeCheck(),
        TextContrastCheck(),
    )

    private fun counts(result: AccessibilityHierarchyCheckResult): Boolean =
        result.type == AccessibilityCheckResultType.ERROR ||
            (result.sourceCheckClass == TextContrastCheck::class.java &&
                result.resultId == TextContrastCheck.RESULT_ID_TEXTVIEW_HEURISTIC_CONTRAST_NOT_SUFFICIENT)

    @Test
    fun checkAccessibility() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val context         = instrumentation.targetContext
        val appPackage      = context.packageName
        // Connect UiAutomation first: Compose only starts exposing its semantics tree once an
        // accessibility client is attached, so a tree read right after connecting comes back empty.
        val uiAutomation    = instrumentation.uiAutomation

        // ── 1. Wait for activity to be stable ────────────────────────────────
        // A locked or dark phone keeps the activity STOPPED: turn the screen on and show the
        // activity above the lock screen (the pipeline also wakes the device before the test).
        composeTestRule.activityRule.scenario.onActivity { activity ->
            if (Build.VERSION.SDK_INT >= 27) {
                activity.setShowWhenLocked(true)
                activity.setTurnScreenOn(true)
            }
        }
        composeTestRule.activityRule.scenario.moveToState(Lifecycle.State.RESUMED)
        composeTestRule.waitForIdle()
        try { Espresso.closeSoftKeyboard() } catch (_: Exception) {}
        composeTestRule.waitForIdle()

        // Poll until the window has focus (Android 16 grants focus asynchronously).
        val deadline = System.currentTimeMillis() + 8_000L
        var hasFocus = false
        while (!hasFocus && System.currentTimeMillis() < deadline) {
            composeTestRule.activityRule.scenario.onActivity { activity ->
                hasFocus = activity.window.decorView.hasWindowFocus()
            }
            if (!hasFocus) Thread.sleep(300)
        }
        composeTestRule.waitForIdle()

        // Fingerprint of the app's visible accessibility nodes: used to wait until the tree is
        // populated and stable, and to tell when scrolling no longer changes the screen.
        fun snapshot(): List<String> {
            val root = uiAutomation.rootInActiveWindow ?: return emptyList()
            val out = mutableListOf<String>()
            fun walk(node: AccessibilityNodeInfo) {
                if (node.packageName?.toString() == appPackage && node.isVisibleToUser) {
                    val b = Rect()
                    node.getBoundsInScreen(b)
                    out.add("${node.className}|${node.text}|${node.contentDescription}@${b.top}")
                }
                for (i in 0 until node.childCount) node.getChild(i)?.let { walk(it); it.recycle() }
            }
            walk(root)
            root.recycle()
            return out
        }

        fun waitForStableTree(): List<String> {
            val end = System.currentTimeMillis() + 10_000L
            var last = snapshot()
            while (System.currentTimeMillis() < end) {
                Thread.sleep(300)
                composeTestRule.waitForIdle()
                val now = snapshot()
                if (now.size > 1 && now == last) return now
                last = now
            }
            return last
        }

        // ── 2. Check accessibility issues across scroll positions ─────────────
        val allIssues   = mutableListOf<String>()
        val diagnostics = mutableListOf<String>()
        val seen        = mutableSetOf<String>()

        // An element cut by the edge of its scrolling container is reported with clipped bounds
        // (and without the children that are out of view), which produces false results. It is
        // skipped here and checked again in a pass where it is fully visible (passes overlap).
        fun scrollingAncestor(element: ViewHierarchyElement): ViewHierarchyElement? {
            var parent = element.parentView
            while (parent != null) {
                if (parent.isScrollable == true) return parent
                parent = parent.parentView
            }
            return null
        }

        fun isCutByScrollEdge(element: ViewHierarchyElement): Boolean {
            val v = scrollingAncestor(element)?.boundsInScreen ?: return false
            val b = element.boundsInScreen
            return b.top <= v.top || b.bottom >= v.bottom
        }

        // Top of every identifiable element (text or description, once on screen) that sits inside
        // a scrolling container, read from the same hierarchy the checks run on.
        fun scrollingTops(hierarchy: AccessibilityHierarchyAndroid): Map<String, Int> =
            hierarchy.activeWindow.allViews
                .filter { it.isVisibleToUser == true && scrollingAncestor(it) != null &&
                          (it.text != null || it.contentDescription != null) }
                .groupBy { "${it.className}|${it.text}|${it.contentDescription}" }
                .filterValues { it.size == 1 }
                .mapValues { (_, views) -> views[0].boundsInScreen.top }

        // scrolled: total distance the content has moved up since the first pass, measured on the
        // hierarchy each pass checks (a separate snapshot can come from a stale node cache and miss a
        // scroll, which counted the same element twice). Elements inside a scrolling container are
        // keyed by their position in the content, so an element seen again on a later (overlapping)
        // pass is not counted twice.
        var scrolled = 0
        var previousTops: Map<String, Int>? = null

        // Returns false when the content did not move since the previous pass (its end was reached).
        // screenChanged: whether the node snapshot changed, used only when the scrolling content has
        // no identifiable element to measure the scroll with.
        fun collectIssues(pass: Int, nodes: Int, screenChanged: Boolean = true): Boolean {
            val rootNode   = uiAutomation.rootInActiveWindow ?: run { diagnostics.add("pass $pass: no window"); return false }
            val screenshot = uiAutomation.takeScreenshot()

            val hierarchy  = AccessibilityHierarchyAndroid.newBuilder(rootNode, context).build()
            val tops       = scrollingTops(hierarchy)
            val before     = previousTops
            val delta      = if (before == null) 0 else before.keys.intersect(tops.keys)
                .map { before.getValue(it) - tops.getValue(it) }
                .groupingBy { it }.eachCount()
                .maxByOrNull { it.value }?.key ?: 0
            previousTops = tops
            if (before != null && delta == 0 && tops == before && (tops.isNotEmpty() || !screenChanged)) {
                diagnostics.add("pass $pass: content did not move, stopping")
                rootNode.recycle()
                screenshot?.recycle()
                return false
            }
            scrolled += delta
            val parameters = Parameters()
            if (screenshot != null) parameters.putScreenCapture(BitmapImage(screenshot))

            var found = 0
            var cut   = 0
            for (check in checks) {
                val checkName = check.javaClass.simpleName
                for (result in check.runCheckOnHierarchy(hierarchy, null, parameters)) {
                    if (!counts(result)) continue
                    val element = result.element
                    if (element != null && isCutByScrollEdge(element)) { cut++; continue }
                    val bounds  = element?.boundsInScreen?.toShortString() ?: "[?]"
                    val place   = element?.boundsInScreen?.let { b ->
                        val dy = if (scrollingAncestor(element) != null) scrolled else 0
                        "${b.left},${b.top + dy},${b.right},${b.bottom + dy}"
                    } ?: "?"
                    val key = "$checkName:${result.resultId}@$place"
                    if (!seen.add(key)) continue
                    found++
                    val cls     = element?.className?.toString()?.substringAfterLast('.') ?: "View"
                    val message = result.getMessage(Locale.ENGLISH).toString()
                        .replace(Regex("\\s+"), " ").trim()
                    allIssues.add("[${result.type.name}] $checkName: $cls at $bounds — $message")
                }
            }
            diagnostics.add("pass $pass: $nodes nodes, scrolled ${scrolled}px, $found new result(s), $cut skipped at scroll edge")

            rootNode.recycle()
            screenshot?.recycle()
            return true
        }

        // Slow swipe over 40% of the screen: little fling, so consecutive passes overlap and
        // every element is fully visible in at least one of them.
        val scrollStep = GeneralSwipeAction(
            Swipe.SLOW,
            GeneralLocation.translate(GeneralLocation.CENTER, 0f, 0.2f),
            GeneralLocation.translate(GeneralLocation.CENTER, 0f, -0.2f),
            Press.FINGER,
        )

        var screen = waitForStableTree()
        collectIssues(1, screen.size)
        for (pass in 2..12) {
            try {
                onView(isRoot()).perform(scrollStep)
            } catch (_: Exception) {
                break
            }
            composeTestRule.waitForIdle()
            val next = waitForStableTree()
            if (!collectIssues(pass, next.size, next != screen)) break   // the end of the content was reached
            screen = next
        }

        // ── 3. Report: throw once with the numbered list and the diagnostics ─
        val numbered = allIssues.mapIndexed { i, msg -> "${i + 1}. $msg" }.joinToString("\n")
        val diag     = diagnostics.joinToString("\n") { "[DIAG] $it" }
        throw AssertionError(
            "There were ${allIssues.size} accessibility check failure(s):\n\n$numbered\n\n$diag"
        )
    }
}
