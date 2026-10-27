import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import User
from items.models import Category, ItemReport, ItemMatch, ReportReview, AdminContactLog, AuditLog
from items.services.ai_matching import run_ai_matching_for_report
from claims.models import OwnershipClaim, RecoveryRecord
from notifications.models import Notification


class Command(BaseCommand):
    help = "Seeds database with default campus categories, demo users, sample reports, and AI matches."

    def handle(self, *args, **options):
        self.stdout.write("Seeding database...")

        # 1. Categories
        categories_data = [
            ("Electronics & Gadgets", "electronics", "bi-laptop", "Laptops, phones, tablets, smartwatches, chargers, headphones"),
            ("Wallets, Bags & Backpacks", "wallets-bags", "bi-bag", "Backpacks, handbags, purses, wallets, cardholders"),
            ("Campus IDs & Documents", "ids-cards", "bi-person-badge", "Student roll cards, faculty IDs, library cards, driver licenses"),
            ("Keys & Keychains", "keys", "bi-key", "Room keys, bicycle keys, vehicle keys, locker keys"),
            ("Books & Study Materials", "books", "bi-book", "Textbooks, notebooks, binders, scientific calculators"),
            ("Apparel & Accessories", "clothing", "bi-sunglasses", "Jackets, hoodies, caps, umbrellas, watches, glasses"),
            ("Sports & Fitness", "sports", "bi-trophy", "Sports gear, gym bottles, racquets, athletic wear"),
            ("Other Miscellaneous", "other", "bi-box-seam", "Miscellaneous campus belongings"),
        ]

        categories = {}
        for name, slug, icon, desc in categories_data:
            cat, _ = Category.objects.get_or_create(
                slug=slug,
                defaults={'name': name, 'icon': icon, 'description': desc}
            )
            categories[slug] = cat

        self.stdout.write(self.style.SUCCESS(f"Created {len(categories)} categories."))

        # 2. Users
        # Admin Superuser
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@campus.edu',
                'first_name': 'Dr. Robert',
                'last_name': 'Vance',
                'role': 'ADMIN',
                'is_staff': True,
                'is_superuser': True,
                'is_verified': True,
                'department': 'Campus Security & Administration',
            }
        )
        if created:
            admin_user.set_password('admin12345')
            admin_user.save()

        # Staff user
        staff_user, created = User.objects.get_or_create(
            username='security_officer',
            defaults={
                'email': 'security@campus.edu',
                'first_name': 'Marcus',
                'last_name': 'Kane',
                'role': 'STAFF',
                'is_staff': True,
                'is_verified': True,
                'department': 'Central Campus Security Desk',
            }
        )
        if created:
            staff_user.set_password('officer12345')
            staff_user.save()

        # Student A
        student_arjun, created = User.objects.get_or_create(
            username='arjun_patel',
            defaults={
                'email': 'arjun.p@campus.edu',
                'first_name': 'Arjun',
                'last_name': 'Patel',
                'role': 'STUDENT',
                'student_id': 'CS-2023-042',
                'phone_number': '+1-555-0192',
                'department': 'Computer Science & Engineering',
                'is_verified': True,
            }
        )
        if created:
            student_arjun.set_password('student12345')
            student_arjun.save()

        # Student B
        student_priya, created = User.objects.get_or_create(
            username='priya_sharma',
            defaults={
                'email': 'priya.s@campus.edu',
                'first_name': 'Priya',
                'last_name': 'Sharma',
                'role': 'STUDENT',
                'student_id': 'EC-2024-118',
                'phone_number': '+1-555-0248',
                'department': 'Electronics & Communication',
                'is_verified': True,
            }
        )
        if created:
            student_priya.set_password('student12345')
            student_priya.save()

        # Student C
        student_rahul, created = User.objects.get_or_create(
            username='rahul_verma',
            defaults={
                'email': 'rahul.v@campus.edu',
                'first_name': 'Rahul',
                'last_name': 'Verma',
                'role': 'STUDENT',
                'student_id': 'ME-2023-089',
                'phone_number': '+1-555-0319',
                'department': 'Mechanical Engineering',
                'is_verified': True,
            }
        )
        if created:
            student_rahul.set_password('student12345')
            student_rahul.save()

        self.stdout.write(self.style.SUCCESS("Demo users created: admin/admin12345, security_officer/officer12345, arjun_patel/student12345, priya_sharma/student12345, rahul_verma/student12345."))

        # 3. Sample Reports
        today = timezone.now().date()

        # Report 1: LOST - Dell XPS 15 (PENDING - Submitted by Arjun, awaiting review)
        rep_lost_xps, _ = ItemReport.objects.get_or_create(
            title="Dell XPS 15 9520 Silver Laptop",
            reporter=student_arjun,
            defaults={
                'report_type': 'LOST',
                'category': categories['electronics'],
                'subcategory': 'Laptop',
                'description': "Silver Dell XPS 15 laptop with carbon fiber palm rest and Intel Evo sticker. Left in library.",
                'distinctive_marks': "Scratch near bottom left hinge; NASA sticker on back lid; wallpaper is James Webb Telescope deep field.",
                'date_occurred': today - datetime.timedelta(days=2),
                'location_name': "Central Library 2nd Floor",
                'location_details': "Desk 14 in Quiet Study Zone B",
                'contact_phone': '+1-555-0192',
                'contact_email': 'arjun.p@campus.edu',
                'approval_status': 'PENDING',
                'is_publicly_visible': False,
            }
        )

        # Report 2: FOUND - Dell Laptop (PENDING - Found by Priya, compatible match!)
        rep_found_xps, _ = ItemReport.objects.get_or_create(
            title="Silver Dell Laptop found in Study Hall",
            reporter=student_priya,
            defaults={
                'report_type': 'FOUND',
                'category': categories['electronics'],
                'subcategory': 'Laptop',
                'description': "Found a premium silver Dell 15-inch laptop on desk after closing time. Turned in to security desk.",
                'distinctive_marks': "Has space/astronomy sticker on lid; scratch near lower hinge.",
                'date_occurred': today - datetime.timedelta(days=2),
                'location_name': "Central Library 2nd Floor",
                'location_details': "Quiet reading carrels, 2nd floor west wing",
                'contact_phone': '+1-555-0248',
                'contact_email': 'priya.s@campus.edu',
                'approval_status': 'PENDING',
                'is_publicly_visible': False,
            }
        )

        # Report 3: APPROVED - Brown Leather Wallet (APPROVED - in public listing)
        rep_found_wallet, _ = ItemReport.objects.get_or_create(
            title="Brown Leather Tommy Hilfiger Wallet",
            reporter=student_rahul,
            defaults={
                'report_type': 'FOUND',
                'category': categories['wallets-bags'],
                'subcategory': 'Wallet',
                'description': "Brown bi-fold leather wallet found near cafeteria cashier counter.",
                'distinctive_marks': "Contains student ID ending in 042, some cash, metro transit pass.",
                'date_occurred': today - datetime.timedelta(days=3),
                'location_name': "Student Cafeteria",
                'location_details': "Table near payment terminal #2",
                'contact_phone': '+1-555-0319',
                'contact_email': 'rahul.v@campus.edu',
                'approval_status': 'APPROVED',
                'is_publicly_visible': True,
                'reviewed_by': admin_user,
                'reviewed_at': timezone.now() - datetime.timedelta(days=2),
            }
        )

        # Report 4: APPROVED - Scientific Calculator (APPROVED - in public listing)
        rep_found_calc, _ = ItemReport.objects.get_or_create(
            title="Casio fx-991EX Scientific Calculator",
            reporter=student_priya,
            defaults={
                'report_type': 'FOUND',
                'category': categories['books'],
                'subcategory': 'Calculator',
                'description': "Black ClassWiz Casio scientific calculator found on bench.",
                'distinctive_marks': "Initials 'R.V.' engraved on the sliding protective cover.",
                'date_occurred': today - datetime.timedelta(days=4),
                'location_name': "Engineering Block C",
                'location_details': "Lecture Hall C-204, row 3",
                'contact_phone': '+1-555-0248',
                'contact_email': 'priya.s@campus.edu',
                'approval_status': 'APPROVED',
                'is_publicly_visible': True,
                'reviewed_by': admin_user,
                'reviewed_at': timezone.now() - datetime.timedelta(days=3),
            }
        )

        # Report 5: NEEDS_INFORMATION - Set of Bike Keys
        rep_lost_keys, _ = ItemReport.objects.get_or_create(
            title="Ring of 3 Brass Keys with Red Lanyard",
            reporter=student_rahul,
            defaults={
                'report_type': 'LOST',
                'category': categories['keys'],
                'subcategory': 'Keys',
                'description': "Lost bicycle and hostel room keys somewhere between gym and sports ground.",
                'distinctive_marks': "Red woven lanyard with small metal whistle.",
                'date_occurred': today - datetime.timedelta(days=1),
                'location_name': "Sports Complex",
                'location_details': "Bicycle parking stand #4",
                'contact_phone': '+1-555-0319',
                'contact_email': 'rahul.v@campus.edu',
                'approval_status': 'NEEDS_INFORMATION',
                'rejection_reason': "Please specify bicycle lock brand (e.g. MasterLock, Kryptonite) and hostel room block.",
                'is_publicly_visible': False,
                'reviewed_by': staff_user,
                'reviewed_at': timezone.now() - datetime.timedelta(hours=12),
            }
        )

        # Run AI matching on the reports
        for rep in [rep_lost_xps, rep_found_xps, rep_found_wallet, rep_found_calc, rep_lost_keys]:
            run_ai_matching_for_report(rep)

        # Create an administrative contact log for the XPS laptop match
        match_xps = ItemMatch.objects.filter(lost_report=rep_lost_xps, found_report=rep_found_xps).first()
        if match_xps:
            AdminContactLog.objects.get_or_create(
                match=match_xps,
                admin=admin_user,
                contact_target=student_arjun,
                defaults={
                    'contact_method': 'EMAIL',
                    'contact_details_used': 'arjun.p@campus.edu',
                    'response_received': True,
                    'outcome': 'CONFIRMED_CONSISTENT',
                    'notes': "Contacted student Arjun to verify sticker details and screen wallpaper. Student accurately confirmed James Webb wallpaper and hinge scratch.",
                }
            )

        # Add sample notification
        Notification.objects.get_or_create(
            recipient=student_arjun,
            title="High Probability Match Under Review",
            defaults={
                'message': "Admin Vance is reviewing a potential match for your reported Dell XPS 15 laptop. Please keep your contact channels open.",
                'notification_type': 'MATCH_FOUND',
                'link': f"/items/report/{rep_lost_xps.report_id}/",
                'is_read': False,
            }
        )

        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))
