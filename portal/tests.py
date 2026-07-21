from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from portal.constants import DocumentType, ProcessRole
from portal.models import (
    MessageThread,
    Process,
    ProcessDocument,
    ProcessMembership,
)
from portal.services.storage import (
    InvalidDownloadToken,
    PrivateObjectStorage,
    StoredObjectNotFound,
)


def _download_token(url: str) -> str:
    return parse_qs(urlsplit(url).query)["token"][0]


class PrivateObjectStorageTests(SimpleTestCase):
    def test_signed_download_opens_file_beneath_private_root(self):
        with TemporaryDirectory() as directory:
            file_path = Path(directory) / "process" / "contract.txt"
            file_path.parent.mkdir()
            file_path.write_text("Private contract", encoding="utf-8")
            storage = PrivateObjectStorage(root=directory)

            signed = storage.get_download_url("process/contract.txt")
            stored_object = storage.open_signed_download(_download_token(signed.url))

            try:
                self.assertEqual(stored_object.stream.read(), b"Private contract")
                self.assertEqual(stored_object.filename, "contract.txt")
                self.assertEqual(stored_object.storage_key, "process/contract.txt")
            finally:
                stored_object.stream.close()

    def test_expired_download_is_rejected(self):
        with TemporaryDirectory() as directory:
            file_path = Path(directory) / "contract.txt"
            file_path.write_text("Private contract", encoding="utf-8")
            storage = PrivateObjectStorage(
                root=directory,
                ttl=timedelta(seconds=15),
            )
            with patch("django.core.signing.time.time", return_value=100):
                signed = storage.get_download_url("contract.txt")

            with (
                patch("django.core.signing.time.time", return_value=116),
                self.assertRaises(InvalidDownloadToken),
            ):
                storage.open_signed_download(_download_token(signed.url))

    def test_download_cannot_escape_private_root(self):
        with TemporaryDirectory() as directory:
            private_root = Path(directory) / "private"
            private_root.mkdir()
            (Path(directory) / "outside.txt").write_text("secret", encoding="utf-8")
            storage = PrivateObjectStorage(root=private_root)
            signed = storage.get_download_url("../outside.txt")

            with self.assertRaises(StoredObjectNotFound):
                storage.open_signed_download(_download_token(signed.url))

    def test_tampered_download_is_rejected(self):
        with TemporaryDirectory() as directory:
            storage = PrivateObjectStorage(root=directory)

            with self.assertRaises(InvalidDownloadToken):
                storage.open_signed_download("not-a-valid-token")


class PortalAccessTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(
            username="owner@example.com",
            email="owner@example.com",
            password=None,
        )
        self.other_owner = User.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password=None,
        )
        self.process = Process.objects.create(
            name="Herdade da Ribeira",
            reference_code="ANT-2026-014",
            location="Coruche, Santarém",
            area_hectares="42.80",
            progress_percent=68,
        )
        self.other_process = Process.objects.create(
            name="Quinta do Vale",
            reference_code="ANT-2026-099",
        )
        ProcessMembership.objects.create(
            process=self.process,
            user=self.owner,
            role=ProcessRole.OWNER,
        )
        ProcessMembership.objects.create(
            process=self.other_process,
            user=self.other_owner,
            role=ProcessRole.OWNER,
        )
        self.document = ProcessDocument.objects.create(
            process=self.process,
            document_type=DocumentType.CONTRACT,
            title="Contrato de gestão",
            storage_key="ANT-2026-014/contrato.pdf",
        )
        self.other_document = ProcessDocument.objects.create(
            process=self.other_process,
            document_type=DocumentType.INVOICE,
            title="Fatura reservada",
            storage_key="ANT-2026-099/fatura.pdf",
        )

    def test_anonymous_user_is_redirected_to_authkit(self):
        response = self.client.get(reverse("portal:dashboard"))
        self.assertRedirects(
            response,
            reverse("workos_login"),
            fetch_redirect_response=False,
        )

    def test_dashboard_only_lists_membership_processes(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("portal:dashboard"))
        self.assertContains(response, self.process.name)
        self.assertNotContains(response, self.other_process.name)

    def test_documents_are_tenant_scoped(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("portal:documents"))
        self.assertContains(response, self.document.title)
        self.assertNotContains(response, self.other_document.title)

    def test_foreign_document_cannot_be_downloaded(self):
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse(
                "portal:document_download",
                kwargs={"document_id": self.other_document.pk},
            )
        )
        self.assertEqual(response.status_code, 404)
        security_response = self.client.get(
            reverse("portal:security"),
            {"process": self.process.pk},
        )
        self.assertContains(security_response, "Sem acessos registados")

    def test_allowed_download_returns_file_and_appears_in_access_history(self):
        self.client.force_login(self.owner)
        with TemporaryDirectory() as directory:
            document_path = Path(directory) / self.document.storage_key
            document_path.parent.mkdir(parents=True)
            document_path.write_text("Private contract", encoding="utf-8")
            with self.settings(PRIVATE_MEDIA_ROOT=directory):
                response = self.client.get(
                    reverse(
                        "portal:document_download",
                        kwargs={"document_id": self.document.pk},
                    )
                )
                self.assertEqual(response.status_code, 302)
                self.assertIn("/portal/files/signed/?token=", response.url)
                file_response = self.client.get(response.url)
                self.assertEqual(file_response.status_code, 200)
                self.assertEqual(
                    b"".join(file_response.streaming_content), b"Private contract"
                )
        security_response = self.client.get(
            reverse("portal:security"),
            {"process": self.process.pk},
        )
        self.assertContains(security_response, "Document · download_requested")
        self.assertContains(security_response, "Document · downloaded")

    def test_user_can_reply_to_thread_in_accessible_process(self):
        self.client.force_login(self.owner)
        thread = MessageThread.objects.create(
            process=self.process,
            subject="Intervenção de verão",
        )
        response = self.client.post(
            reverse("portal:send_message"),
            {"process": self.process.pk, "thread": thread.pk, "body": "Obrigado."},
            follow=True,
        )
        self.assertContains(response, "Obrigado.")

    def test_reply_to_thread_from_another_process_is_rejected(self):
        self.client.force_login(self.owner)
        foreign_thread = MessageThread.objects.create(
            process=self.other_process,
            subject="Processo reservado",
        )

        response = self.client.post(
            reverse("portal:send_message"),
            {
                "process": self.process.pk,
                "thread": foreign_thread.pk,
                "body": "Mensagem deslocada",
            },
        )

        self.assertEqual(response.status_code, 404)

    def test_new_conversation_with_blank_subject_uses_a_visible_default(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("portal:send_message"),
            {
                "process": self.process.pk,
                "subject": "   ",
                "body": "Tenho uma questão sobre o processo.",
            },
            follow=True,
        )

        self.assertContains(response, "Nova mensagem")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_new_document_emails_process_members_after_commit(self):
        with self.captureOnCommitCallbacks(execute=True):
            ProcessDocument.objects.create(
                process=self.process,
                document_type=DocumentType.ANNUAL_REPORT,
                title="Novo balanço anual",
                storage_key="ANT-2026-014/balanco.txt",
            )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.owner.email])
        self.assertIn("Novo documento", mail.outbox[0].subject)
