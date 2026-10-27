import datetime
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from accounts.models import User
from items.models import Category, ItemReport, ItemMatch
from items.services.ai_matching import (
    evaluate_report_pair,
    run_ai_matching_for_report,
    compute_text_similarity,
    compute_category_similarity,
    compute_date_similarity
)


class AIMatchingEngineTests(TestCase):
    def setUp(self):
        self.category_elec = Category.objects.create(name="Electronics", slug="electronics")
        self.category_bags = Category.objects.create(name="Bags & Wallets", slug="bags")

        self.user1 = User.objects.create_user(username='u1', password='p1', email='u1@campus.edu')
        self.user2 = User.objects.create_user(username='u2', password='p2', email='u2@campus.edu')

        self.today = timezone.now().date()

        self.lost_iphone = ItemReport.objects.create(
            report_type='LOST',
            title='Black Apple iPhone 14 Pro Max',
            category=self.category_elec,
            subcategory='Smartphone',
            description='Black iPhone 14 Pro Max with clear case and shattered corner.',
            distinctive_marks='Wallpaper is Golden Gate Bridge; serial ending in 98X.',
            date_occurred=self.today - datetime.timedelta(days=1),
            location_name='Central Library 2nd Floor',
            reporter=self.user1
        )

        self.found_iphone = ItemReport.objects.create(
            report_type='FOUND',
            title='Black Apple iPhone 14 Pro',
            category=self.category_elec,
            subcategory='Smartphone',
            description='Found black Apple iPhone in clear case near library study tables.',
            distinctive_marks='Has bridge wallpaper on lock screen.',
            date_occurred=self.today - datetime.timedelta(days=1),
            location_name='Central Library 2nd Floor',
            reporter=self.user2
        )

        self.lost_wallet = ItemReport.objects.create(
            report_type='LOST',
            title='Brown Leather Bi-fold Wallet',
            category=self.category_bags,
            description='Brown leather wallet lost in cafeteria.',
            date_occurred=self.today,
            location_name='Cafeteria',
            reporter=self.user1
        )

    def test_text_similarity_computation(self):
        """Text similarity score should be high for similar strings."""
        score_high = compute_text_similarity(
            "Black Apple iPhone 14 Pro Max with case",
            "Black Apple iPhone 14 Pro in clear case"
        )
        self.assertGreaterEqual(score_high, 50.0)

        score_low = compute_text_similarity(
            "Black Apple iPhone 14 Pro Max",
            "Red wool winter scarf apparel"
        )
        self.assertLess(score_low, 20.0)

    def test_evaluation_prohibits_same_types_or_self(self):
        """AI engine must strictly prohibit Lost-Lost, Found-Found, or self-comparison."""
        # Self comparison
        with self.assertRaises(ValueError):
            evaluate_report_pair(self.lost_iphone, self.lost_iphone)

        # Lost with Lost
        with self.assertRaises(ValueError):
            evaluate_report_pair(self.lost_iphone, self.lost_wallet)

    def test_composite_similarity_score_and_reasons(self):
        """Evaluate matching results, subscores, and explanatory reasons."""
        result = evaluate_report_pair(self.lost_iphone, self.found_iphone)

        self.assertGreaterEqual(result['similarity_score'], 60.0)
        self.assertGreaterEqual(result['text_similarity'], 40.0)
        self.assertEqual(result['category_similarity'], 100.0)
        self.assertGreater(len(result['matching_reasons']), 0)

        # Check for category reason in reasons list
        cat_matched = any('category' in r.lower() for r in result['matching_reasons'])
        self.assertTrue(cat_matched)

    def test_match_creation_and_duplicate_prevention(self):
        """Running AI matching saves ItemMatch and prevents duplicate pair entries."""
        matches = run_ai_matching_for_report(self.lost_iphone)
        self.assertEqual(len(matches), 1)

        match_record = ItemMatch.objects.get(
            lost_report=self.lost_iphone,
            found_report=self.found_iphone
        )
        self.assertGreaterEqual(match_record.similarity_score, 50.0)
        self.assertTrue(match_record.is_active)

        # Running again updates existing record, does not create duplicate
        matches2 = run_ai_matching_for_report(self.lost_iphone)
        self.assertEqual(ItemMatch.objects.filter(
            lost_report=self.lost_iphone,
            found_report=self.found_iphone
        ).count(), 1)

    def test_database_unique_constraint(self):
        """ItemMatch unique constraint on (lost_report, found_report) raises IntegrityError on duplicate insert."""
        ItemMatch.objects.create(
            lost_report=self.lost_iphone,
            found_report=self.found_iphone,
            similarity_score=75.0
        )
        with self.assertRaises(IntegrityError):
            ItemMatch.objects.create(
                lost_report=self.lost_iphone,
                found_report=self.found_iphone,
                similarity_score=80.0
            )
