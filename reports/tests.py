from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Report


class ReportModelTestCase(TestCase):
    def setUp(self):
        self.reporter = User.objects.create_user(username='reporter', password='testpass123')
        self.target = User.objects.create_user(username='target', password='testpass123')

    def test_report_creation(self):
        report = Report.objects.create(
            reporter=self.reporter,
            reported_user=self.target,
            reason=Report.SPAM,
            description='This is spam'
        )
        self.assertEqual(report.reporter, self.reporter)
        self.assertEqual(report.reported_user, self.target)
        self.assertEqual(report.reason, Report.SPAM)
        self.assertEqual(report.status, 'pending')
        self.assertIsNotNone(report.created_at)

    def test_report_str(self):
        report = Report.objects.create(
            reporter=self.reporter,
            reported_user=self.target,
            reason=Report.HARASSMENT,
            description='Harassing behavior'
        )
        self.assertIn('reporter', str(report))
        self.assertIn('harassment', str(report))

    def test_report_default_status(self):
        report = Report.objects.create(
            reporter=self.reporter,
            reported_user=self.target,
            reason=Report.INAPPROPRIATE,
            description='Inappropriate content'
        )
        self.assertEqual(report.status, 'pending')

    def test_report_clean_no_target(self):
        report = Report(
            reporter=self.reporter,
            reason=Report.OTHER,
            description='No target specified'
        )
        with self.assertRaises(Exception):
            report.full_clean()


class ReportViewTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass123',
            email='test@example.com'
        )
        self.user.profile.email_verified = True
        self.user.save()
        self.target = User.objects.create_user(username='target', password='testpass123')
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    def test_report_user_view(self):
        response = self.client.post(
            reverse('reports:report_user', args=['target']),
            {'reason': 'spam', 'description': 'Spam account'},
            secure=True
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Report.objects.filter(reporter=self.user, reported_user=self.target).exists()
        )

    def test_admin_reports_view_requires_staff(self):
        response = self.client.get(reverse('reports:admin_reports'), secure=True)
        self.assertEqual(response.status_code, 302)

    def test_admin_reports_view_staff(self):
        self.user.is_staff = True
        self.user.save()
        Report.objects.create(
            reporter=self.target,
            reported_user=self.user,
            reason=Report.SPAM,
            description='Test report'
        )
        response = self.client.get(reverse('reports:admin_reports'), secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.target.username)

    def test_resolve_report(self):
        self.user.is_staff = True
        self.user.save()
        report = Report.objects.create(
            reporter=self.target,
            reported_user=self.user,
            reason=Report.SPAM,
            description='Test report'
        )
        response = self.client.post(
            reverse('reports:resolve_report', args=[report.id]),
            {'action': 'resolved'},
            secure=True
        )
        self.assertEqual(response.status_code, 302)
        report.refresh_from_db()
        self.assertEqual(report.status, 'resolved')
        self.assertEqual(report.resolved_by, self.user)
