from django.db import models
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.images import get_image_model_string
from wagtail.models import Page


class HomePage(Page):
    """Editable institutional landing page for Antarr."""

    hero_eyebrow = models.CharField(
        max_length=120,
        default="Gestão florestal com visão de futuro",
    )
    hero_title = models.CharField(
        max_length=180,
        default="Cuidamos da sua terra. Valorizamos o seu futuro.",
    )
    hero_intro = models.TextField(
        default=(
            "Gestão florestal próxima, transparente e responsável — da análise "
            "inicial ao acompanhamento de cada intervenção."
        )
    )
    approach_title = models.CharField(
        max_length=160,
        default="Uma relação de confiança, construída no terreno.",
    )
    approach_body = RichTextField(
        default=(
            "<p>Gerimos propriedades florestais com rigor técnico, proximidade e "
            "uma visão de longo prazo. Cada decisão é documentada e cada senhorio "
            "acompanha o seu processo com total clareza.</p>"
        ),
        features=["bold", "italic", "link"],
    )
    contact_email = models.EmailField(default="geral@antarr.pt")
    subpage_types = ["home.ArticlePage"]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["latest_articles"] = (
            ArticlePage.objects.child_of(self)
            .live()
            .public()
            .order_by("-publication_date")[:3]
        )
        return context

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("hero_eyebrow"),
                FieldPanel("hero_title"),
                FieldPanel("hero_intro"),
            ],
            heading="Destaque principal",
        ),
        MultiFieldPanel(
            [FieldPanel("approach_title"), FieldPanel("approach_body")],
            heading="A nossa abordagem",
        ),
        FieldPanel("contact_email"),
    ]


class ArticlePage(Page):
    """Editorial publication managed by the Antarr team in Wagtail."""

    publication_date = models.DateField("Data de publicação")
    summary = models.TextField("Resumo", max_length=320)
    body = RichTextField("Conteúdo")
    hero_image = models.ForeignKey(
        get_image_model_string(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="Imagem de destaque",
    )

    parent_page_types = ["home.HomePage"]
    subpage_types = []

    content_panels = Page.content_panels + [
        FieldPanel("publication_date"),
        FieldPanel("summary"),
        FieldPanel("hero_image"),
        FieldPanel("body"),
    ]
