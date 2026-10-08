"""Role-based applicability gate for EU AI Act articles.

The EU AI Act assigns obligations to specific roles: providers, deployers,
GPAI providers, etc. Without a role-based gate, scoring every article on
every repo produces misleading results — e.g. Art. 27 (Fundamental Rights
Impact Assessment for deployers) flagged as critical-FAIL on a Python
library that has no deployer obligations at all.

This module captures, per article, which declared roles the article applies
to. Article checks consult `is_applicable(article, role)` and emit `N/A`
results for non-applicable articles. N/A results do not contribute to the
compliance score and are not surfaced in the Critical Failures banner.

Roles
-----
- provider:       built / trained / placed the AI system on the EU market
- deployer:       uses the AI system under its own authority
- both:           same legal entity is both provider and deployer
- gpai:           provider of a general-purpose AI model
- gpai_systemic:  provider of a GPAI model with systemic risk (Art. 51, 55)
- library:        an OSS library — no deployed system; only Art. 5 + 6 apply
- tool:           internal tooling (e.g. red-team, evals) — only Art. 5 + 6 apply
- undeclared:     no role provided; universal and provider-side articles run,
                  with an INDICATIVE banner. Deployer-only (Art. 26, 27) and
                  GPAI-model (Art. 53, 55) obligations are NOT scored: a
                  codebase can evidence what its provider built, but not
                  whether anyone deploys it or whether it is a GPAI model.
"""

from __future__ import annotations

# Article identifier here matches the `ComplianceCheck.article` field
# ("Article 5", "Article 9", etc.). Each entry lists the declared roles
# for which the article is in scope. The sentinel "all" applies to every
# role (universal obligations like prohibited practices).
ARTICLE_APPLICABILITY: dict[str, list[str]] = {
    "Article 5": ["all"],   # Prohibited practices apply to everyone
    "Article 6": ["all"],   # Classification rules — universal
    "Article 8": ["provider", "both"],
    "Article 9": ["provider", "both"],
    "Article 10": ["provider", "both"],
    "Article 11": ["provider", "both"],
    "Article 12": ["provider", "both"],
    "Article 13": ["provider", "both"],
    "Article 14": ["provider", "both"],
    "Article 15": ["provider", "both"],
    "Article 16": ["provider", "both"],
    "Article 17": ["provider", "both"],
    "Article 26": ["deployer", "both"],
    "Article 27": ["deployer", "both"],
    "Article 50": ["provider", "deployer", "both", "gpai"],
    "Article 53": ["gpai", "gpai_systemic"],
    "Article 55": ["gpai_systemic"],
    "Article 72": ["provider", "both"],
}

# Roles that limit the assessment to universal obligations (Art. 5, 6).
_LIBRARY_LIKE_ROLES = frozenset({"library", "tool"})

# All recognised roles. Anything outside this set is normalised to "undeclared".
_KNOWN_ROLES = frozenset({
    "provider", "deployer", "both", "gpai", "gpai_systemic",
    "library", "tool", "undeclared",
})


def normalise_role(role: str | None) -> str:
    """Return a known role string or 'undeclared' for anything else."""
    if not role:
        return "undeclared"
    role = role.strip().lower()
    return role if role in _KNOWN_ROLES else "undeclared"


def is_applicable(article: str, role: str) -> bool:
    """True if `article` is in scope for the declared `role`.

    - "library" / "tool"  → only Art. 5 + 6 apply
    - "undeclared"        → universal + provider-side articles only (caller
                            is responsible for surfacing the INDICATIVE
                            banner); unknown articles run unconditionally
    - anything else       → consult ARTICLE_APPLICABILITY
    """
    role = normalise_role(role)

    if role in _LIBRARY_LIKE_ROLES:
        return article in ("Article 5", "Article 6")

    if role == "undeclared":
        if article not in ARTICLE_APPLICABILITY:
            return True
        return is_applicable(article, "provider")

    applicable_roles = ARTICLE_APPLICABILITY.get(article, [])
    return "all" in applicable_roles or role in applicable_roles


def applies_to_roles(article: str) -> list[str]:
    """Return the declared roles an article applies to (empty if unknown)."""
    return list(ARTICLE_APPLICABILITY.get(article, []))


def applicable_articles_for_role(role: str) -> list[str]:
    """Return the sorted list of article identifiers in scope for `role`."""
    return sorted(a for a in ARTICLE_APPLICABILITY if is_applicable(a, role))


def non_applicable_articles_for_role(role: str) -> list[str]:
    """Return the sorted list of article identifiers NOT in scope for `role`."""
    return sorted(a for a in ARTICLE_APPLICABILITY if not is_applicable(a, role))
