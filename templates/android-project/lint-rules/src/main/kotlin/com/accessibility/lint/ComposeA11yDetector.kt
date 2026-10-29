@file:Suppress("UnstableApiUsage", "OPT_IN_USAGE")

package com.accessibility.lint

import com.android.tools.lint.detector.api.*
import com.intellij.psi.PsiMethod
import org.jetbrains.kotlin.psi.KtCallElement
import org.jetbrains.uast.*

@Suppress("UnstableApiUsage")
class ComposeA11yDetector : Detector(), SourceCodeScanner {

    companion object {
        private val CATEGORY = Category.A11Y
        private val IMPLEMENTATION = Implementation(
            ComposeA11yDetector::class.java,
            Scope.JAVA_FILE_SCOPE,
        )

        val ISSUE_ICON_NULL_CD: Issue = Issue.create(
            id = "ComposeIconNullContentDescription",
            briefDescription = "Icon() has contentDescription = null",
            explanation = """
                An `Icon()` composable has `contentDescription = null`. If this icon is \
                inside a clickable element (IconButton, clickable modifier), screen readers \
                cannot announce its purpose. Provide a descriptive string or explicitly mark \
                it as decorative only when it adds no information to the user.
            """,
            category = CATEGORY,
            priority = 8,
            severity = Severity.WARNING,
            implementation = IMPLEMENTATION,
        )

        val ISSUE_ICON_MISSING_CD: Issue = Issue.create(
            id = "ComposeIconMissingContentDescription",
            briefDescription = "Icon() missing contentDescription parameter",
            explanation = """
                An `Icon()` composable does not include a `contentDescription` parameter. \
                Screen readers require this parameter to describe the icon to users with \
                visual impairments. Pass a descriptive string or explicitly pass `null` \
                for icons that are purely decorative.
            """,
            category = CATEGORY,
            priority = 9,
            severity = Severity.ERROR,
            implementation = IMPLEMENTATION,
        )

        val ISSUE_IMAGE_NULL_CD: Issue = Issue.create(
            id = "ComposeImageNullContentDescription",
            briefDescription = "Image() has contentDescription = null",
            explanation = """
                An `Image()` composable has `contentDescription = null`. Ensure this \
                image is purely decorative and conveys no information. If the image \
                communicates meaning, provide a descriptive string instead.
            """,
            category = CATEGORY,
            priority = 6,
            severity = Severity.WARNING,
            implementation = IMPLEMENTATION,
        )

        val ISSUE_IMAGE_MISSING_CD: Issue = Issue.create(
            id = "ComposeImageMissingContentDescription",
            briefDescription = "Image() missing contentDescription parameter",
            explanation = """
                An `Image()` composable does not include a `contentDescription` parameter. \
                Screen readers require this parameter to describe the image.
            """,
            category = CATEGORY,
            priority = 9,
            severity = Severity.ERROR,
            implementation = IMPLEMENTATION,
        )

        val ISSUE_TEXTFIELD_LABEL: Issue = Issue.create(
            id = "ComposeTextFieldMissingLabel",
            briefDescription = "TextField() missing label parameter",
            explanation = """
                A `TextField` or `OutlinedTextField` composable does not have a `label` \
                parameter. Without a visible label, assistive technology cannot identify \
                this input field's purpose to users with visual impairments.
            """,
            category = CATEGORY,
            priority = 7,
            severity = Severity.WARNING,
            implementation = IMPLEMENTATION,
        )
    }

    override fun getApplicableMethodNames(): List<String> = listOf(
        "Icon", "Image", "TextField", "OutlinedTextField",
    )

    override fun visitMethodCall(context: JavaContext, node: UCallExpression, method: PsiMethod) {
        // Guard: only process files that use Jetpack Compose
        val sourceText = context.getContents() ?: return
        if ("import androidx.compose" !in sourceText && "@Composable" !in sourceText) return

        when (node.methodName) {
            "Icon" -> checkContentDescription(
                context, node, method, "Icon",
                ISSUE_ICON_MISSING_CD, ISSUE_ICON_NULL_CD,
            )
            "Image" -> checkContentDescription(
                context, node, method, "Image",
                ISSUE_IMAGE_MISSING_CD, ISSUE_IMAGE_NULL_CD,
            )
            "TextField", "OutlinedTextField" -> checkTextFieldLabel(context, node, method)
        }
    }

    // ── Content-description check ────────────────────────────────────────────

    private fun checkContentDescription(
        context: JavaContext,
        call: UCallExpression,
        method: PsiMethod,
        component: String,
        missingIssue: Issue,
        nullIssue: Issue,
    ) {
        // contentDescription is the 2nd parameter of every Icon and Image overload
        val cd = argumentFor(context, call, method, "contentDescription", positionalIndex = 1)

        if (cd == null) {
            context.report(
                missingIssue, call, context.getNameLocation(call),
                "`$component()` is missing a `contentDescription` — " +
                    "screen readers cannot describe this element.",
            )
            return
        }

        if (cd.isNullLiteral()) {
            context.report(
                nullIssue, call, context.getNameLocation(call),
                "`$component()` has `contentDescription = null` — " +
                    "provide a description or ensure the element is purely decorative.",
            )
        }
    }

    // ── TextField label check ────────────────────────────────────────────────

    private fun checkTextFieldLabel(context: JavaContext, call: UCallExpression, method: PsiMethod) {
        val label = argumentFor(context, call, method, "label")

        if (label == null || label.isNullLiteral()) {
            context.report(
                ISSUE_TEXTFIELD_LABEL, call, context.getNameLocation(call),
                "`${call.methodName}()` has no `label` — " +
                    "assistive technology cannot identify this input field's purpose.",
            )
        }
    }

    /**
     * The argument passed for parameter [name], named or positional, or null when it is not passed.
     *
     * Kotlin named arguments are plain expressions in UAST (UNamedExpression is only used for
     * annotation attributes), so the argument → parameter mapping of the resolved call is used.
     * If that mapping is unavailable, the names are read from the Kotlin PSI of the call, and
     * [positionalIndex] (when given) accepts an unnamed argument at that position.
     */
    private fun argumentFor(
        context: JavaContext,
        call: UCallExpression,
        method: PsiMethod,
        name: String,
        positionalIndex: Int? = null,
    ): UExpression? {
        val mapping = context.evaluator.computeArgumentMapping(call, method)
        if (mapping.isNotEmpty()) {
            return mapping.entries.firstOrNull { it.value.name == name }?.key
        }

        val ktCall = call.sourcePsi as? KtCallElement ?: return null
        val ktArgs = ktCall.valueArguments
        val ktArg = ktArgs.firstOrNull { it.getArgumentName()?.asName?.asString() == name }
            ?: positionalIndex?.let { i -> ktArgs.getOrNull(i)?.takeIf { !it.isNamed() } }
            ?: return null
        val expression = ktArg.getArgumentExpression() ?: return null
        return call.valueArguments.firstOrNull { it.sourcePsi == expression }
            ?: expression.toUElementOfType<UExpression>()
    }

    // ── Helpers ──────────────────────────────────────────────────────────────

    private fun UExpression.isNullLiteral(): Boolean = when (this) {
        is UParenthesizedExpression -> expression.isNullLiteral()
        is ULiteralExpression -> isNull
        else -> false
    }
}
