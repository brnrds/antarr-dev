from datetime import date

from wagtail.models import Page, Site
from wagtail.test.utils import WagtailPageTestCase

from home.models import ArticlePage, HomePage


class HomeTests(WagtailPageTestCase):
    """
    Tests for homepage functionality and rendering.
    """

    def setUp(self):
        """
        Create a homepage instance for testing.
        """
        root_page = Page.get_first_root_node()
        Site.objects.create(
            hostname="testsite",
            root_page=root_page,
            is_default_site=True,
        )
        self.homepage = HomePage(title="Home")
        root_page.add_child(instance=self.homepage)

    def test_homepage_is_renderable(self):
        self.assertPageIsRenderable(self.homepage)

    def test_visitor_can_read_an_editorial_article(self):
        article = ArticlePage(
            title="Cuidar do montado no verão",
            publication_date=date(2026, 7, 19),
            summary="Uma nota breve sobre prevenção e acompanhamento.",
            body="<p>Conteúdo editorial.</p>",
        )
        self.homepage.add_child(instance=article)

        response = self.client.get(article.url)

        self.assertContains(response, "Cuidar do montado no verão")
        self.assertContains(response, "Conteúdo editorial.")
