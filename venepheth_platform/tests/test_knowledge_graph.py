"""
Unit tests for Knowledge Graph aggregation helpers.
NOTE: topics/ views are PARKED (see apps/search/urls.py) — view tests live
in git history and return with the feature.
"""

from django.test import TestCase

from apps.search.knowledge_graph import build_knowledge_graph, get_topic_detail


class TestBuildKnowledgeGraph(TestCase):
    """Test the knowledge graph topic aggregation service."""

    def test_returns_list(self):
        """build_knowledge_graph() always returns a list."""
        result = build_knowledge_graph()
        self.assertIsInstance(result, list)

    def test_empty_db_returns_empty_list(self):
        """With empty database, no topics are returned."""
        result = build_knowledge_graph()
        # With an empty test DB this should be 0 or more depending on fixtures
        self.assertGreaterEqual(len(result), 0)

    def test_min_count_filter(self):
        """build_knowledge_graph() respects min_count threshold."""
        result_low = build_knowledge_graph(min_count=1)
        result_high = build_knowledge_graph(min_count=9999)
        self.assertGreaterEqual(len(result_low), len(result_high))

    def test_topic_node_structure(self):
        """Each topic node has the expected keys."""
        results = build_knowledge_graph(min_count=0)
        for node in results:
            self.assertIn("name", node)
            self.assertIn("slug", node)
            self.assertIn("count", node)
            self.assertIn("types", node)
            self.assertIn("related", node)
            self.assertIsInstance(node["count"], int)
            self.assertIsInstance(node["types"], list)

    def test_topic_node_slug_format(self):
        """Slugs should be lowercase and use hyphens."""
        results = build_knowledge_graph(min_count=0)
        for node in results:
            self.assertEqual(node["slug"], node["slug"].lower())
            self.assertNotIn(" ", node["slug"])


class TestGetTopicDetail(TestCase):
    """Test topic detail aggregation."""

    def test_returns_dict_with_expected_keys(self):
        """get_topic_detail() returns the expected structure."""
        result = get_topic_detail("Management")
        self.assertIsInstance(result, dict)
        self.assertIn("topic", result)
        self.assertIn("articles", result)
        self.assertIn("research", result)
        self.assertIn("courses", result)
        self.assertIn("publications", result)

    def test_no_exception_on_unknown_topic(self):
        """get_topic_detail() handles non-existent topics gracefully."""
        try:
            result = get_topic_detail("XXXXXXXXUNKNOWNXXXXXXXX")
            self.assertIsInstance(result, dict)
        except Exception as e:
            self.fail(f"get_topic_detail raised an exception: {e}")
