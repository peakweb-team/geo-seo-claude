#!/usr/bin/env python3
"""
Tests for action_plan_generator.py
===================================
Validates that the deterministic prioritisation logic produces sensible,
consistent results. These tests do not call any LLM — they test the
ranking engine only.

Run with:
    python3 -m pytest tests/test_action_plan_generator.py -v
    # or
    python3 tests/test_action_plan_generator.py
"""

import json
import os
import sys
import unittest

# Allow running from project root or tests/ directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts"))

from action_plan_generator import (
    ACTION_CATALOG,
    PRIORITY_WEIGHTS,
    compute_priority_score,
    detect_platform_from_html,
    detect_business_type_from_audit,
    map_findings_to_actions,
    rank_action_items,
    enrich_with_platform_context,
    generate_roadmap_markdown,
)

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_fixture(name: str) -> dict:
    with open(os.path.join(FIXTURES_DIR, name), "r") as f:
        return json.load(f)


def _get_ids(action_items: list) -> list:
    return [a["id"] for a in action_items]


class TestPriorityScoring(unittest.TestCase):
    """Unit tests for compute_priority_score()."""

    def test_unblock_crawlers_scores_very_high(self):
        """Blocking AI crawlers is a critical, direct, immediate, foundational fix."""
        item = ACTION_CATALOG["unblock_ai_crawlers"]
        score = compute_priority_score(item)
        self.assertGreater(score, 85,
            f"unblock_ai_crawlers should score > 85, got {score}")

    def test_wikipedia_scores_low(self):
        """Wikipedia is indirect, very_high difficulty, long-term — should rank low."""
        item = ACTION_CATALOG["build_wikipedia_presence"]
        score = compute_priority_score(item)
        self.assertLess(score, 30,
            f"build_wikipedia_presence should score < 30, got {score}")

    def test_publish_llms_txt_scores_moderate(self):
        """llms.txt is direct, low difficulty, but low impact and near-term."""
        item = ACTION_CATALOG["publish_llms_txt"]
        score = compute_priority_score(item)
        self.assertGreater(score, 25,
            f"publish_llms_txt should score > 25, got {score}")
        self.assertLess(score, 60,
            f"publish_llms_txt should score < 60 (low impact), got {score}")

    def test_wikidata_scores_above_wikipedia(self):
        """Wikidata is indirect but medium difficulty — should beat Wikipedia."""
        wiki_score = compute_priority_score(ACTION_CATALOG["build_wikipedia_presence"])
        wikidata_score = compute_priority_score(ACTION_CATALOG["build_wikidata_entity"])
        self.assertGreater(wikidata_score, wiki_score,
            f"Wikidata ({wikidata_score}) should rank above Wikipedia ({wiki_score})")

    def test_implement_ssr_scores_very_high(self):
        """SSR is direct control, very_high impact, foundational, immediate."""
        item = ACTION_CATALOG["implement_ssr"]
        score = compute_priority_score(item)
        self.assertGreater(score, 70,
            f"implement_ssr should score > 70, got {score}")

    def test_score_range_0_to_100(self):
        """All catalog items should produce scores in 0-100."""
        for action_id, item in ACTION_CATALOG.items():
            score = compute_priority_score(item)
            self.assertGreaterEqual(score, 0, f"{action_id} score < 0: {score}")
            self.assertLessEqual(score, 100, f"{action_id} score > 100: {score}")

    def test_direct_control_beats_indirect_same_impact(self):
        """All else equal, direct control should score higher than indirect."""
        direct = {**ACTION_CATALOG["add_organization_schema"],
                  "controlLevel": "direct", "estimatedScoreImpact": "high",
                  "timeHorizon": "immediate", "difficultyLevel": "low",
                  "isFoundational": False, "affectedPlatforms": [], "peakwebFit": "advisory_only"}
        indirect = {**direct, "controlLevel": "indirect"}
        self.assertGreater(compute_priority_score(direct),
                           compute_priority_score(indirect))

    def test_immediate_beats_long_term_same_everything(self):
        """Immediate timeline should beat long-term, all else equal."""
        base = {**ACTION_CATALOG["add_organization_schema"],
                "controlLevel": "direct", "estimatedScoreImpact": "high",
                "difficultyLevel": "low", "isFoundational": False,
                "affectedPlatforms": [], "peakwebFit": "advisory_only"}
        immediate = {**base, "timeHorizon": "immediate"}
        long_term = {**base, "timeHorizon": "long_term"}
        self.assertGreater(compute_priority_score(immediate),
                           compute_priority_score(long_term))


class TestLocalBusinessMissingBasics(unittest.TestCase):
    """
    Local business: AI crawlers blocked, no LocalBusiness schema, no llms.txt.
    Expected: unblock_ai_crawlers is #1, publish_llms_txt and add_local_business_schema
    are in top 5, all three are immediate.
    """

    def setUp(self):
        findings = _load_fixture("local_business_missing_basics.json")
        items = map_findings_to_actions(findings)
        self.items = rank_action_items(items)
        self.ids = _get_ids(self.items)

    def test_unblock_ai_crawlers_is_rank_1(self):
        self.assertEqual(self.ids[0], "unblock_ai_crawlers",
            f"Expected unblock_ai_crawlers at rank 1, got: {self.ids[:3]}")

    def test_publish_llms_txt_in_plan(self):
        """llms.txt should be in the action plan (but not necessarily top 5 since low impact)."""
        self.assertIn("publish_llms_txt", self.ids,
            f"publish_llms_txt not in action plan: {self.ids}")

    def test_local_business_schema_in_top_5(self):
        self.assertIn("add_local_business_schema", self.ids[:5],
            f"add_local_business_schema not in top 5: {self.ids[:5]}")

    def test_critical_actions_are_immediate(self):
        """High-impact foundational actions should be immediate."""
        for action_id in ["unblock_ai_crawlers", "add_local_business_schema"]:
            item = next(a for a in self.items if a["id"] == action_id)
            self.assertEqual(item["timeHorizon"], "immediate",
                f"{action_id} should be 'immediate', got '{item['timeHorizon']}'")
        # llms.txt is near-term (low impact, intentionally downgraded)
        llms = next(a for a in self.items if a["id"] == "publish_llms_txt")
        self.assertEqual(llms["timeHorizon"], "near_term")

    def test_no_software_application_schema_for_local(self):
        """Local business should not trigger SaaS-specific actions."""
        self.assertNotIn("add_software_application_schema", self.ids,
            "add_software_application_schema should not appear for a local business")

    def test_claim_google_business_profile_present(self):
        """GBP should be included for local business without one."""
        self.assertIn("claim_google_business_profile", self.ids,
            "claim_google_business_profile should be in action plan for local business")

    def test_all_items_have_priority_scores(self):
        for item in self.items:
            self.assertIn("priorityScore", item,
                f"Item {item['id']} missing priorityScore")
            self.assertGreaterEqual(item["priorityScore"], 0)
            self.assertLessEqual(item["priorityScore"], 100)

    def test_items_are_sorted_descending(self):
        scores = [a["priorityScore"] for a in self.items]
        self.assertEqual(scores, sorted(scores, reverse=True),
            "Items should be sorted by priorityScore descending")


class TestSaaSWeakEEAT(unittest.TestCase):
    """
    SaaS company with weak E-E-A-T: no author pages, no original research,
    missing SoftwareApplication schema. No local signals.
    """

    def setUp(self):
        findings = _load_fixture("saas_weak_eeat.json")
        items = map_findings_to_actions(findings)
        self.items = rank_action_items(items)
        self.ids = _get_ids(self.items)

    def test_create_author_pages_present(self):
        self.assertIn("create_author_pages", self.ids,
            "create_author_pages should be in action plan for SaaS with no author pages")

    def test_software_application_schema_present(self):
        self.assertIn("add_software_application_schema", self.ids,
            "add_software_application_schema should appear for SaaS site")

    def test_create_original_research_present(self):
        self.assertIn("create_original_research", self.ids,
            "create_original_research should be in plan when no original data detected")

    def test_no_local_business_schema_for_saas(self):
        self.assertNotIn("add_local_business_schema", self.ids,
            "add_local_business_schema should not appear for a SaaS site (not local)")

    def test_no_google_business_profile_for_saas(self):
        self.assertNotIn("claim_google_business_profile", self.ids,
            "claim_google_business_profile should not appear for a non-local SaaS site")

    def test_no_crawlers_blocked_so_unblock_absent(self):
        self.assertNotIn("unblock_ai_crawlers", self.ids,
            "unblock_ai_crawlers should not appear when no crawlers are blocked")

    def test_faq_schema_present_in_plan(self):
        """SaaS site without FAQPage schema should get this action."""
        self.assertIn("add_faq_schema", self.ids)


class TestNoWikipediaStrongOnsite(unittest.TestCase):
    """
    Business with strong on-site foundations but no Wikipedia/Wikidata.
    Tests that Wikipedia is present but NOT in top 3, and Wikidata ranks above Wikipedia.
    """

    def setUp(self):
        findings = _load_fixture("business_no_wikipedia.json")
        items = map_findings_to_actions(findings)
        self.items = rank_action_items(items)
        self.ids = _get_ids(self.items)

    def test_wikipedia_present_in_plan(self):
        self.assertIn("build_wikipedia_presence", self.ids,
            "build_wikipedia_presence should appear when no Wikipedia found")

    def test_wikipedia_not_in_top_3(self):
        self.assertNotIn("build_wikipedia_presence", self.ids[:3],
            f"build_wikipedia_presence should NOT be in top 3 for a site with strong foundations: {self.ids[:3]}")

    def test_wikidata_above_wikipedia(self):
        if "build_wikidata_entity" not in self.ids or "build_wikipedia_presence" not in self.ids:
            self.skipTest("One or both items not in plan")
        wiki_rank = self.ids.index("build_wikipedia_presence")
        wikidata_rank = self.ids.index("build_wikidata_entity")
        self.assertLess(wikidata_rank, wiki_rank,
            f"Wikidata (rank {wikidata_rank}) should rank above Wikipedia (rank {wiki_rank})")

    def test_wikipedia_is_long_term(self):
        item = next((a for a in self.items if a["id"] == "build_wikipedia_presence"), None)
        if item is None:
            self.skipTest("build_wikipedia_presence not in plan")
        self.assertEqual(item["timeHorizon"], "long_term",
            f"Wikipedia should have timeHorizon='long_term', got '{item['timeHorizon']}'")

    def test_no_schema_actions_for_already_present_schemas(self):
        """LocalBusiness and Organization schema are present — don't re-add them."""
        self.assertNotIn("add_local_business_schema", self.ids,
            "add_local_business_schema should not appear when schema already present")
        self.assertNotIn("add_organization_schema", self.ids,
            "add_organization_schema should not appear when org schema already present")

    def test_no_llms_txt_action_when_present(self):
        self.assertNotIn("publish_llms_txt", self.ids,
            "publish_llms_txt should not appear when llms.txt is already present")


class TestJSHeavySite(unittest.TestCase):
    """
    SaaS site where content is behind JS / no SSR.
    implement_ssr should be rank #1 or #2, with very_high impact.
    """

    def setUp(self):
        findings = _load_fixture("js_heavy_site.json")
        items = map_findings_to_actions(findings)
        self.items = rank_action_items(items)
        self.ids = _get_ids(self.items)

    def test_implement_ssr_in_top_2(self):
        self.assertIn("implement_ssr", self.ids[:2],
            f"implement_ssr should be rank 1 or 2 for JS-heavy site, got: {self.ids[:3]}")

    def test_implement_ssr_has_very_high_impact(self):
        item = next(a for a in self.items if a["id"] == "implement_ssr")
        self.assertEqual(item["estimatedScoreImpact"], "very_high",
            f"implement_ssr should have very_high impact, got '{item['estimatedScoreImpact']}'")

    def test_implement_ssr_priority_above_60(self):
        item = next(a for a in self.items if a["id"] == "implement_ssr")
        self.assertGreater(item["priorityScore"], 60,
            f"implement_ssr priority should be > 60, got {item['priorityScore']}")

    def test_implement_ssr_is_immediate(self):
        item = next(a for a in self.items if a["id"] == "implement_ssr")
        self.assertEqual(item["timeHorizon"], "immediate")

    def test_publish_llms_txt_also_present(self):
        self.assertIn("publish_llms_txt", self.ids,
            "publish_llms_txt should also be in plan when not present")

    def test_no_local_business_actions_for_saas(self):
        self.assertNotIn("add_local_business_schema", self.ids)
        self.assertNotIn("claim_google_business_profile", self.ids)


class TestPlatformDetection(unittest.TestCase):
    """Tests for detect_platform_from_html()."""

    def test_detects_wordpress(self):
        html = '<html><head><meta name="generator" content="WordPress 6.4" /></head></html>'
        self.assertEqual(detect_platform_from_html(html), "wordpress")

    def test_detects_wordpress_via_wp_content(self):
        html = '<html><body><script src="/wp-content/themes/mytheme/script.js"></script></body></html>'
        self.assertEqual(detect_platform_from_html(html), "wordpress")

    def test_detects_shopify(self):
        html = '<html><body><script src="https://cdn.shopify.com/s/assets/storefront.js"></script></body></html>'
        self.assertEqual(detect_platform_from_html(html), "shopify")

    def test_detects_wix(self):
        html = '<html><body><img src="https://static.wixstatic.com/media/logo.png" /></body></html>'
        self.assertEqual(detect_platform_from_html(html), "wix")

    def test_unknown_platform(self):
        html = '<html><body><h1>Custom site</h1></body></html>'
        self.assertEqual(detect_platform_from_html(html), "unknown")

    def test_empty_html(self):
        self.assertEqual(detect_platform_from_html(""), "unknown")
        self.assertEqual(detect_platform_from_html(None), "unknown")


class TestBusinessTypeDetection(unittest.TestCase):
    """Tests for detect_business_type_from_audit()."""

    def test_detects_local(self):
        text = "Business Type: Local Service\nAddress: 123 Main St"
        self.assertEqual(detect_business_type_from_audit(text), "local")

    def test_detects_saas(self):
        text = "Business Type: SaaS\nThe platform offers a free trial and dashboard access."
        self.assertEqual(detect_business_type_from_audit(text), "saas")

    def test_detects_ecommerce(self):
        text = "E-commerce store with Shopify. Multiple add to cart buttons detected."
        self.assertEqual(detect_business_type_from_audit(text), "ecommerce")

    def test_detects_local_from_heuristic(self):
        text = "The site appears to be a dentist practice in Austin, TX."
        self.assertEqual(detect_business_type_from_audit(text), "local")

    def test_returns_unknown_for_empty(self):
        self.assertEqual(detect_business_type_from_audit(""), "unknown")
        self.assertEqual(detect_business_type_from_audit(None), "unknown")


class TestPlatformEnrichment(unittest.TestCase):
    """Tests for enrich_with_platform_context()."""

    def test_wordpress_notes_added(self):
        findings = {**_load_fixture("local_business_missing_basics.json"), "platform": "wordpress"}
        items = map_findings_to_actions(findings)
        items = enrich_with_platform_context(items, findings)
        schema_item = next((a for a in items if a["id"] == "add_local_business_schema"), None)
        if schema_item:
            self.assertIn("platformSpecificNotes", schema_item,
                "WordPress-specific notes should be added to add_local_business_schema")

    def test_unknown_platform_no_extra_notes(self):
        findings = {**_load_fixture("saas_weak_eeat.json"), "platform": "unknown"}
        items = map_findings_to_actions(findings)
        pre_count = sum(1 for a in items if "platformSpecificNotes" in a)
        items = enrich_with_platform_context(items, findings)
        post_count = sum(1 for a in items if "platformSpecificNotes" in a)
        # Should not add more notes for unknown platform
        self.assertEqual(pre_count, post_count,
            "No platform notes should be added for unknown platform")


class TestMarkdownGeneration(unittest.TestCase):
    """Smoke tests for generate_roadmap_markdown()."""

    def _get_roadmap(self, fixture_name: str) -> tuple:
        findings = _load_fixture(fixture_name)
        items = map_findings_to_actions(findings)
        items = rank_action_items(items)
        md = generate_roadmap_markdown(items, findings)
        return items, md

    def test_markdown_contains_required_sections(self):
        _, md = self._get_roadmap("local_business_missing_basics.json")
        required_sections = [
            "AI Visibility Roadmap",
            "Executive Summary",
            "How to Read This Roadmap",
            "Top Priorities",
            "Quick Wins",
            "Full Ranked Action Plan",
            "What Peakweb Can Implement",
            "GEO Readiness Score Breakdown",
            "AI Answer Share Score",
        ]
        for section in required_sections:
            self.assertIn(section, md, f"Section '{section}' missing from roadmap markdown")

    def test_markdown_contains_brand_name(self):
        findings = _load_fixture("local_business_missing_basics.json")
        items = rank_action_items(map_findings_to_actions(findings))
        md = generate_roadmap_markdown(items, findings)
        self.assertIn("Acme Plumbing", md,
            "Brand name should appear in roadmap markdown")

    def test_markdown_contains_geo_score(self):
        findings = _load_fixture("saas_weak_eeat.json")
        items = rank_action_items(map_findings_to_actions(findings))
        md = generate_roadmap_markdown(items, findings)
        self.assertIn("54", md, "GEO score should appear in markdown")

    def test_markdown_not_empty(self):
        for fixture in ["local_business_missing_basics.json", "saas_weak_eeat.json",
                        "business_no_wikipedia.json", "js_heavy_site.json"]:
            _, md = self._get_roadmap(fixture)
            self.assertGreater(len(md), 500,
                f"Roadmap markdown for {fixture} should be substantial (>500 chars)")

    def test_no_prompt_chasing_language(self):
        """Roadmap should not use 'ranking for prompt' framing."""
        for fixture in ["local_business_missing_basics.json", "js_heavy_site.json"]:
            _, md = self._get_roadmap(fixture)
            self.assertNotIn("ranking for prompt", md.lower())
            self.assertNotIn("rank for the query", md.lower())


class TestActionCatalogIntegrity(unittest.TestCase):
    """Validate that the ACTION_CATALOG has correct, complete metadata."""

    REQUIRED_FIELDS = [
        "id", "title", "category", "scoreComponent", "controlLevel",
        "difficultyLevel", "estimatedScoreImpact", "timeHorizon",
        "peakwebFit", "isFoundational", "affectedPlatforms",
        "implementationNotes",
    ]

    VALID_ENUMS = {
        "category": {"technical", "schema", "content", "brand", "platform"},
        "controlLevel": {"direct", "mixed", "indirect"},
        "difficultyLevel": {"low", "medium", "high", "very_high"},
        "estimatedScoreImpact": {"low", "medium", "high", "very_high"},
        "timeHorizon": {"immediate", "near_term", "long_term"},
        "peakwebFit": {"direct_service", "partner_referral", "advisory_only"},
    }

    def test_all_catalog_items_have_required_fields(self):
        for action_id, item in ACTION_CATALOG.items():
            for field in self.REQUIRED_FIELDS:
                self.assertIn(field, item,
                    f"ACTION_CATALOG['{action_id}'] missing field '{field}'")

    def test_all_enum_values_are_valid(self):
        for action_id, item in ACTION_CATALOG.items():
            for field, valid_values in self.VALID_ENUMS.items():
                value = item.get(field)
                self.assertIn(value, valid_values,
                    f"ACTION_CATALOG['{action_id}'].{field} = '{value}' not in {valid_values}")

    def test_id_matches_key(self):
        for action_id, item in ACTION_CATALOG.items():
            self.assertEqual(item["id"], action_id,
                f"ACTION_CATALOG key '{action_id}' doesn't match item id '{item['id']}'")

    def test_no_duplicate_ids(self):
        ids = [item["id"] for item in ACTION_CATALOG.values()]
        self.assertEqual(len(ids), len(set(ids)), "Duplicate IDs found in ACTION_CATALOG")

    def test_priority_weights_sum_sensibly(self):
        """Max possible raw score should equal PRIORITY_WEIGHTS['raw_max']."""
        w = PRIORITY_WEIGHTS
        max_raw = (
            max(w["impact"].values()) +
            max(w["control"].values()) +
            max(w["speed"].values()) +
            w["foundational_bonus"] +
            w["multi_platform_bonus"] +
            w["peakweb_bonus"]
            # difficulty_penalty min is 0 (low), so no penalty at max
        )
        self.assertEqual(max_raw, w["raw_max"],
            f"PRIORITY_WEIGHTS['raw_max'] = {w['raw_max']}, but actual max = {max_raw}. Update raw_max.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
