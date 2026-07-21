from django.db import models


class DocumentType(models.TextChoices):
    CONTRACT = "contract", "Contrato"
    FOREST_MANAGEMENT_PLAN = "forest_plan", "Plano de gestão florestal"
    ANNUAL_REPORT = "annual_report", "Balanço anual"
    INVOICE = "invoice", "Faturação"
    OTHER = "other", "Outro"


class ProcessRole(models.TextChoices):
    OWNER = "owner", "Senhorio"
    CO_OWNER = "co_owner", "Co-proprietário"
    HEIR = "heir", "Herdeiro"
    ACCOUNTANT = "accountant", "Contabilista"
    MANAGER = "manager", "Gestor de processo (interno)"


class InterventionType(models.TextChoices):
    THINNING = "thinning", "Desbaste"
    PLANTING = "planting", "Plantação"
    PRUNING = "pruning", "Poda"
    SURVEY = "survey", "Levantamento"
    OTHER = "other", "Outra"


class ProcessStatus(models.TextChoices):
    PLANNING = "planning", "Em planeamento"
    ACTIVE = "active", "Em curso"
    MONITORING = "monitoring", "Em acompanhamento"
    COMPLETED = "completed", "Concluído"


class OperationStatus(models.TextChoices):
    PLANNED = "planned", "Planeada"
    CONFIRMED = "confirmed", "Confirmada"
    COMPLETED = "completed", "Concluída"
    POSTPONED = "postponed", "Adiada"
