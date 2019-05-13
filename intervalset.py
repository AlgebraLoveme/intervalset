"""Interval set abstract type"""
import datetime
import collections

__version__ = "0.1.5"


_InternalInterval = collections.namedtuple("Interval", ["begin", "end"])


class Interval(_InternalInterval):
    """Represent an immutable interval, with beginning and ending value.

    To create a new interval:

        Interval(0, 10)

    Begin and end values must be immutable ordered types.

    Especially useful with datetime instances:

        begin = datetime.datetime(...)
        end = datetime.datetime(...)
        Interval(begin, end)

    These are closed intervals, and the beginning value must be smaller than the ending value.
    Intervals with the same starting and ending value are considered empty, and are represented with
    EMPTY_INTERVAL. The EMPTY_INTERVAL constant is a singleton, and its boolean value is False.
    All other intervals are True. The EMPTY_INTERVAL is smaller than any other non-empty interval.

    Operators for intervals:

        "&" - intersection
        "|" - unification, but it can only be applied to overlapping or touching non-empty intervals.
        "in" - if an interval contains another interval completely.

    """
    def __new__(cls, begin, end):
        """Create a new instance of Interval(begin, end)"""
        global EMPTY_INTERVAL

        if EMPTY_INTERVAL is not None and begin is None or end is None or end < begin:
            return EMPTY_INTERVAL
        else:
            return _InternalInterval.__new__(cls, begin, end)

    def __bool__(self):
        return self is not EMPTY_INTERVAL

    def __and__(self, other):
        """Return the intersection of this interval and another.

        A zero-length intersection

        When there is no intersection, it returns EMPTY_INTERVAl."""
        global EMPTY_INTERVAL
        if not self or not other or self.end <= other.begin or other.end <= self.begin:
            return EMPTY_INTERVAL
        elif self.begin >= other.begin and self.end <= other.end:
            # This interval is completely within the other.
            return self
        elif other.begin >= self.begin and other.end <= self.end:
            # The other interval is completely within this
            return other
        else:
            # They overlap proper.
            if self.begin > other.begin:
                begin = self.begin
            else:
                begin = other.begin
            if self.end < other.end:
                end = self.end
            else:
                end = other.end
            return Interval(begin, end)

    def __or__(self, other):
        """Unify two overlapping intervals. When called with non-overlapping intervals, raises ValueError."""
        if not self or not other or self.end < other.begin or other.end < self.begin:
            raise ValueError(
                "Cannot unify non-overlapping intervals. (Use interval sets for that.)")
        elif self.begin >= other.begin and self.end <= other.end:
            # This interval is completely within the other.
            return other
        elif other.begin >= self.begin and other.end <= self.end:
            # The other interval is completely within this
            return self
        else:
            # They overlap proper.
            if self.begin > other.begin:
                begin = other.begin
            else:
                begin = self.begin
            if self.end < other.end:
                end = other.end
            else:
                end = self.end
            return Interval(begin, end)

    def __contains__(self, other):
        if not self:
            # An empty interval does not contain anything, even another empty interval.
            return False
        elif not other:
            return False  # This is an interesting question... is an empty interval inside a non-empty one?
        else:
            return other.begin >= self.begin and other.end <= self.end

    def is_before_than(self, other):
        """Tells if this interval is completely before the other. (Empty intervals are before everything.)"""
        return (self is EMPTY_INTERVAL) or (other is EMPTY_INTERVAL) or self.end < other.begin

    def is_after_than(self, other):
        """Tells if this interval is completely after the other. (Empty intervals are before everything.)"""
        if self is EMPTY_INTERVAL or other is EMPTY_INTERVAL:
            return False
        else:
            return other.end < self.begin

    def __str__(self):
        """Human-readable representation."""
        name = self.__class__.__name__
        if self:
            if isinstance(self.begin, datetime.datetime):
                w = 8
                res = str(self.begin.date()) + " " + \
                    str(self.begin.time())[:w] + "->"
                if self.begin.date() != self.end.date():
                        res += str(self.end.date())
                res += str(self.end.time())[:w]
            else:
                res = "%s, %s" % (self.begin, self.end)
            return "%s(%s)" % (name, res)
        else:
            return "%s(<empty>)" % name


EMPTY_INTERVAL = None  # Define it so that __new__ can check it.
EMPTY_INTERVAL = Interval(None, None)


class IntervalSet(object):
    """A set of intervals.

    IntervalSet is also immutable. To create a new set, pass elements to the constructor:

        IntervalSet( interval1, interval2, interval3... )

    Arguments should be Interval objects. The order is insignificant - they will automatically be unified and ordered
    by the constructor. Empty intervals will be simply ignored (and absent from the set). Sets can be iterated
    over.

    Operators on interval sets:

    * | union
    * & intersection
    * - difference
    * ^ symmetric difference
    * "in" - containment for an element
    * "in" - containment for a set

    """

    def __init__(self, *items):
        self._fill_items(items)
        self._hash = None

    def _fill_items(self, items):
        _items = []
        if items:
            it = iter(sorted(items))
            # Get first non-empty interval
            i1 = None
            for i1 in it:
                if i1:
                    break
            # Unify with other items
            for i2 in it:
                if i1.is_before_than(i2):
                    # Next item is completely before the current one. Store the current.
                    _items.append(i1)
                    i1 = i2
                elif i1 & i2 or i1.end == i2.begin:
                    # Next item overlaps with the current item. Unify them.
                    i1 = i1 | i2
                else:
                    # This should never happen when items are sorted.
                    raise Exception("Internal error")
            # Add last remaining item
            if i1:
                _items.append(i1)
        # Make it immutable, hashable
        self._items = tuple(_items)

    def __hash__(self):
        if self._hash is None:
            self._hash = hash(self._items)
        return self._hash

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)

    def __and__(self, other):
        """Make a intersections of this interval set and another."""
        # Intersection with an empty set is empty.
        if not self:
            return self
        if not other:
            return other
        # We know that items are sorted, so we can do this incrementally in O(N) time.
        new_items = []
        it1 = iter(self)
        it2 = iter(other)
        i1 = next(it1)
        i2 = next(it2)
        try:
            while True:
                if i1.is_before_than(i2):
                    i1 = next(it1)
                elif i2.is_before_than(i1):
                    i2 = next(it2)
                else:
                    i3 = i1 & i2
                    if i3:
                        new_items.append(i3)
                    if i1.end < i2.end:
                        i1 = next(it1)
                    else:
                        i2 = next(it2)
        except StopIteration:
            pass
        return IntervalSet(*new_items)

    def __or__(self, other):
        """Make a union of two interval sets."""
        # Union with an empty set...
        if not self:
            return other
        if not other:
            return self
        # We know that items are sorted, so we can do this incrementally in O(N) time.
        new_items = []
        it1 = iter(self)
        it2 = iter(other)
        i1 = next(it1)
        i2 = next(it2)
        remaining = None
        while True:
            if i1.is_before_than(i2):
                new_items.append(i1)
                try:
                    i1 = next(it1)
                except StopIteration:
                    new_items.append(i2)
                    remaining = it2
                    break
            elif i2.is_before_than(i1):
                new_items.append(i2)
                try:
                    i2 = next(it2)
                except StopIteration:
                    new_items.append(i1)
                    remaining = it1
                    break
            else:
                # They overlap, create a new unified item.
                new_items.append(i1 | i2)
                try:
                    i1 = next(it1)
                except StopIteration:
                    remaining = it2
                    break
                try:
                    i2 = next(it2)
                except StopIteration:
                    new_items.append(i1)
                    break
        if remaining:
            new_items += list(remaining)
        return IntervalSet(*new_items)

    def __sub__(self, other):
        """Substract other set from this set."""
        if not self:
            return self
        if not other:
            return self
        # We know that items are sorted, so we can do this incrementally in O(N) time.
        new_items = []
        it1 = iter(self)
        it2 = iter(other)
        b1, e1 = next(it1)
        b2, e2 = next(it2)
        try:
            while True:
                # If i1 became empty, advance to next item.
                if b1 >= e1:
                    b1, e1 = None, None
                    b1, e1 = next(it1)
                    continue

                if e1 <= b2:  # i1 is completely before i2
                    new_items.append(Interval(b1, e1))
                    b1, e1 = None, None
                    b1, e1 = next(it1)
                    continue

                if e2 <= b1:  # i2 is completely before i1
                    b2, e2 = next(it2)
                    continue

                if b1 < b2 <= e1 <= e2:  # overlap, i1 starts sooner
                    new_items.append(Interval(b1, b2))
                    b1, e1 = None, None
                    b1, e1 = next(it1)
                    continue

                if b2 <= b1 <= e2 < e1:  # overlap, i2 starts sooner
                    # You might think that (e2, e1) can be added, but it cannot yet.
                    # There can be other items in it2 that needs to be substracted from (e2, e1)
                    b1 = e2
                    b2, e2 = next(it2)
                    continue

                if b2 <= b1 <= e1 <= e2:  # i2 contains i1
                    b1, e1 = None, None
                    b1, e1 = next(it1)
                    continue

                if b1 < b2 <= e2 <= e1:  # i1 contains i2
                    new_items.append(Interval(b1, b2))
                    b1 = e2

        except StopIteration:
            pass

        # Add the last item, if available.
        if b1 and e1 and b1 < e1:
            new_items.append(Interval(b1, e1))

        return IntervalSet(*new_items)

    def __xor__(self, other):
        """Simmetric difference."""
        return (self | other) - (self & other)

    def __contains__(self, other):
        """Containment relation.

        Tell if `other` is contained *completely* in this set. The argument can either be an Interval or an
        IntervalSet.
        """
        if isinstance(other, Interval):
            # TODO: use binary search instead of linear search.
            for item in self:
                if other in item:
                    return True
            return False
        else:
            # Contains the other set completely.
            return (self & other) == other

    def __getitem__(self, index):
        """Get element by its index. (IntervalSet stores elements in an increasing order!)"""
        return self._items[index]

    def min(self):
        """Return the smallest element in the set.

        For empty sets, returns None."""
        if self._items:
            return self._items[0]

    def max(self):
        """Return the biggest element in the set.

        For empty sets, returns None."""
        if self._items:
            return self._items[-1]

    def __str__(self):
        """Human-readable representation."""
        name = self.__class__.__name__
        if self:
            if len(self) < 10:
                parts = []
                if isinstance(self._items[0].begin, datetime.datetime):
                    w = 8
                    last_date = None
                    for item in self:
                        sitem = "["
                        if not last_date or last_date != item.begin.date():
                            last_date = item.begin.date()
                            sitem += str(last_date) + " "
                        sitem += str(item.begin.time())[:w] + " -> "
                        if last_date != item.end.date():
                            last_date = item.end.date()
                            sitem += str(last_date) + " "
                        sitem += str(item.end.time())[:w] + "]"
                        parts.append(sitem)
                else:
                    parts = ["[%s -> %s]" %
                             (item.begin, item.end) for item in self]
                return "%s(%s)" % (name, ",".join(parts))
            else:
                return "%s(%d items between %s and %s)" % (name, len(self), self._items[0], self._items[-1])
        else:
            return "%s(<empty>)" % name
