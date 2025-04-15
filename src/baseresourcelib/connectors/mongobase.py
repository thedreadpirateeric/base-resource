"""Mixin classes and other functions for models."""
import math

from mongoengine.queryset import DoesNotExist
from mongoengine.queryset import MultipleObjectsReturned
from mongoengine.queryset import QuerySet

from baseresourcelib.errors.errors import NothingFound404


class BaseQuerySet(QuerySet):
    """Mongoengine's queryset extended with handy extras."""

    def get_or_404(self, *args: tuple, **kwargs: dict) -> QuerySet:
        """Get a document and raise a 404 Not Found error if not found."""
        try:
            return self.get(*args, **kwargs)
        except (MultipleObjectsReturned, DoesNotExist) as exc:
            raise NothingFound404() from exc

    def first_or_404(self):
        """Get a document and raise a 404 Not Found error if not found."""
        obj = self.first()
        if obj is None:
            raise NothingFound404()

        return obj

    def paginate(self, page: int, per_page: int, **kwargs: dict) -> QuerySet:
        # pylint: disable=W0613
        """Return a paginated response.

        Paginate the QuerySet with a certain number of docs per page
        and return docs for a given page.

        """
        return Pagination(self, page, per_page)


class Pagination:
    # pylint: disable=W0613,W0212
    """Main pagination."""

    def __init__(self, iterable: iter, page: int, per_page: int) -> None:
        """Create pagination instance."""
        if page < 1:
            raise NothingFound404()

        self.iterable = iterable
        self.page = page
        self.per_page = per_page

        if isinstance(iterable, QuerySet):
            self.total = iterable.count()
        else:
            self.total = len(iterable)

        start_index = (page - 1) * per_page
        end_index = page * per_page

        self.items = iterable[start_index:end_index]
        if isinstance(self.items, QuerySet):
            self.items = self.items.select_related()
        if not self.items and page != 1:
            raise NothingFound404()

    @property
    def pages(self) -> int:
        """Return total number of pages."""
        return int(math.ceil(self.total / float(self.per_page)))

    def prev(self, error_out: bool = False) -> object:
        """Return a :class:`Pagination` object for the previous page."""
        assert self.iterable is not None, ('an object is required '
                                           'for this method to work')
        iterable = self.iterable
        if isinstance(iterable, QuerySet):
            iterable._skip = None
            iterable._limit = None
        return self.__class__(iterable, self.page - 1, self.per_page)

    @property
    def prev_num(self) -> int:
        """Return Number of the previous page."""
        return self.page - 1

    @property
    def has_prev(self) -> bool:
        """Return True if a previous page exists."""
        return self.page > 1

    def next(self, error_out: bool = False) -> object:
        """Return a :class:`Pagination` object for the next page."""
        assert self.iterable is not None, ('an object is required '
                                           'for this method to work')
        iterable = self.iterable
        if isinstance(iterable, QuerySet):
            iterable._skip = None
            iterable._limit = None
        return self.__class__(iterable, self.page + 1, self.per_page)

    @property
    def has_next(self) -> bool:
        """Return True if a next page exists."""
        return self.page < self.pages

    @property
    def next_num(self) -> int:
        """Return Number of the next page."""
        return self.page + 1

    def iter_pages(self, left_edge: int = 2, left_current: int = 2,
                   right_current: int = 5, right_edge: int = 2) -> iter:
        # pylint: disable=R1716
        """Iterate over the page numbers in the pagination.

        The four parameters control the thresholds how many numbers should be
        produced from the sides.  Skipped page numbers are represented as
        `None`. This is how you could render such a pagination in the
        templates:

        .. sourcecode:: html+jinja

            {% macro render_pagination(pagination, endpoint) %}
              <div class=pagination>
              {%- for page in pagination.iter_pages() %}
                {% if page %}
                  {% if page != pagination.page %}
                    <a href="{{ url_for(endpoint, page=page) }}">{{ page }}</a>
                  {% else %}
                    <strong>{{ page }}</strong>
                  {% endif %}
                {% else %}
                  <span class=ellipsis>…</span>
                {% endif %}
              {%- endfor %}
              </div>
            {% endmacro %}

        """
        last = 0
        for num in range(1, self.pages + 1):
            if (num <= left_edge or
                    num > self.pages - right_edge or
                    (num >= self.page - left_current and
                     num <= self.page + right_current)):
                if last + 1 != num:
                    yield None
                yield num
                last = num
        if last != self.pages:
            yield None


BASE_META = {}
BASE_META['strict'] = False
BASE_META['ordered'] = True
BASE_META['index_background'] = True
BASE_META['auto_create_index'] = False
BASE_META['queryset_class'] = BaseQuerySet
BASE_META['indexes'] = []
