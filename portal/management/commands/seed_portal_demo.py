import shutil
from datetime import date, datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from portal.constants import (
    DocumentType,
    InterventionType,
    OperationStatus,
    ProcessRole,
)
from portal.models import (
    Intervention,
    Message,
    MessageThread,
    ParcelPhoto,
    Process,
    ProcessDocument,
    ProcessMembership,
    ScheduledOperation,
)


class Command(BaseCommand):
    help = "Create an idempotent, realistic landlord portal demo."

    def add_arguments(self, parser):
        parser.add_argument("--email", default="demo@antarr.pt")

    def handle(self, *args, **options):
        email = options["email"]
        User = get_user_model()
        user, _ = User.objects.get_or_create(
            username=email,
            defaults={
                "email": email,
                "first_name": "Miguel",
                "last_name": "Almeida",
            },
        )
        if user.has_usable_password():
            user.set_unusable_password()
            user.save(update_fields=["password"])

        manager, _ = User.objects.get_or_create(
            username="gestora@antarr.pt",
            defaults={
                "email": "gestora@antarr.pt",
                "first_name": "Marta",
                "last_name": "Ferreira",
                "is_staff": True,
            },
        )
        process, _ = Process.objects.update_or_create(
            reference_code="ANT-2026-014",
            defaults={
                "name": "Herdade da Ribeira",
                "description": "Gestão integrada de montado e proteção do solo.",
                "location": "Coruche, Santarém",
                "area_hectares": "42.80",
                "progress_percent": 68,
                "manager": manager,
            },
        )
        ProcessMembership.objects.get_or_create(
            process=process,
            user=user,
            defaults={"role": ProcessRole.OWNER},
        )

        documents = (
            (
                DocumentType.CONTRACT,
                "Contrato de gestão florestal",
                "contrato.txt",
            ),
            (
                DocumentType.FOREST_MANAGEMENT_PLAN,
                "Plano de gestão florestal 2026–2036",
                "plano-gestao.txt",
            ),
            (
                DocumentType.ANNUAL_REPORT,
                "Balanço anual 2025",
                "balanco-2025.txt",
            ),
            (DocumentType.INVOICE, "Fatura FT 2026/043", "fatura-043.txt"),
        )
        private_root = Path(settings.PRIVATE_MEDIA_ROOT)
        for document_type, title, filename in documents:
            storage_key = f"{process.reference_code}/{filename}"
            file_path = private_root / storage_key
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(
                f"{title}\n\nDocumento demonstrativo do processo "
                f"{process.reference_code}.\n",
                encoding="utf-8",
            )
            ProcessDocument.objects.update_or_create(
                process=process,
                title=title,
                defaults={
                    "document_type": document_type,
                    "storage_key": storage_key,
                    "file_size_bytes": file_path.stat().st_size,
                    "uploaded_by": manager,
                },
            )

        interventions = (
            (
                InterventionType.SURVEY,
                "Levantamento e diagnóstico inicial",
                "Inventário florestal, análise do solo e delimitação das parcelas.",
                date(2026, 2, 14),
            ),
            (
                InterventionType.PRUNING,
                "Poda de formação",
                "Intervenção seletiva na parcela norte, com remoção de sobrantes.",
                date(2026, 4, 9),
            ),
            (
                InterventionType.THINNING,
                "Desbaste sanitário",
                "Remoção de exemplares debilitados e controlo de densidade.",
                date(2026, 6, 18),
            ),
        )
        for intervention_type, title, description, performed_at in interventions:
            Intervention.objects.get_or_create(
                process=process,
                title=title,
                defaults={
                    "intervention_type": intervention_type,
                    "description": description,
                    "performed_at": performed_at,
                },
            )

        today = timezone.localdate()
        ScheduledOperation.objects.get_or_create(
            process=process,
            title="Limpeza seletiva de mato",
            defaults={
                "description": "Redução de carga combustível e manutenção de acessos.",
                "scheduled_start": today + timedelta(days=12),
                "scheduled_end": today + timedelta(days=14),
                "location_notes": "Parcelas Poente e Sul",
                "status": OperationStatus.CONFIRMED,
            },
        )
        ScheduledOperation.objects.get_or_create(
            process=process,
            title="Monitorização fitossanitária",
            defaults={
                "description": "Visita de acompanhamento e atualização fotográfica.",
                "scheduled_start": today + timedelta(days=48),
                "location_notes": "Toda a propriedade",
                "status": OperationStatus.PLANNED,
            },
        )

        for offset, parcel, caption in (
            (150, "Parcela Norte", "Antes da poda de formação"),
            (100, "Parcela Norte", "Após a intervenção"),
            (54, "Parcela Poente", "Acompanhamento de primavera"),
            (8, "Parcela Sul", "Visita técnica de julho"),
        ):
            captured_at = timezone.make_aware(
                datetime.combine(today - timedelta(days=offset), datetime.min.time())
            )
            storage_key = f"{process.reference_code}/photos/{offset}.png"
            target = private_root / storage_key
            target.parent.mkdir(parents=True, exist_ok=True)
            source = settings.PROJECT_DIR / "static/images/antarr-montado-hero.png"
            shutil.copyfile(source, target)
            ParcelPhoto.objects.update_or_create(
                process=process,
                parcel_label=parcel,
                captured_at=captured_at,
                defaults={
                    "caption": caption,
                    "storage_key": storage_key,
                },
            )

        thread, _ = MessageThread.objects.get_or_create(
            process=process,
            subject="Próxima intervenção",
        )
        if not thread.messages.exists():
            Message.objects.create(
                thread=thread,
                author=manager,
                body=(
                    "Bom dia, Miguel. A limpeza seletiva está confirmada. "
                    "Partilharemos fotografias assim que a operação terminar."
                ),
            )
            Message.objects.create(
                thread=thread,
                author=user,
                body="Obrigado pela atualização. Fico a aguardar.",
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Portal demo ready for {email} ({process.reference_code})."
            )
        )
