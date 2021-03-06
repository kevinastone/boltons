# -*- coding: utf-8 -*-
""":mod:`itertools` is full of great examples of Python generator
usage. However, there are still some critical gaps. ``iterutils``
fills many of those gaps with featureful, tested, and Pythonic
solutions.

Many of the functions below have two versions, one which
returns an iterator (denoted by the ``*_iter`` naming pattern), and a
shorter-named convenience form that returns a list. Some of the
following are based on examples in itertools docs.
"""

__all__ = ['is_iterable', 'is_scalar', 'split', 'split_iter', 'chunked',
           'chunked_iter', 'windowed', 'windowed_iter', 'bucketize',
           'partition', 'unique', 'unique_iter', 'one', 'first']

import math
import itertools

try:
    from itertools import izip
except ImportError:
    # Python 3 compat
    basestring = (str, bytes)
    izip, xrange = zip, range


def is_iterable(obj):
    """Similar in nature to :func:`callable`, ``is_iterable`` returns
    ``True`` if an object is `iterable`_, ``False`` if not.

    >>> is_iterable([])
    True
    >>> is_iterable(object())
    False

    .. _iterable: https://docs.python.org/2/glossary.html#term-iterable
    """
    try:
        iter(obj)
    except TypeError:
        return False
    return True


def is_scalar(obj):
    """A near-mirror of :func:`is_iterable`. Returns ``False`` if an
    object is an iterable container type. Strings are considered
    scalar as well, because strings are more often treated as whole
    values as opposed to iterables of 1-character substrings.

    >>> is_scalar(object())
    True
    >>> is_scalar(range(10))
    False
    >>> is_scalar('hello')
    True
    """
    return not is_iterable(obj) or isinstance(obj, basestring)


def is_collection(obj):
    """The opposite of :func:`is_scalar`.  Returns ``True`` if an object
    is an iterable other than a string.

    >>> is_collection(object())
    False
    >>> is_collection(range(10))
    True
    >>> is_collection('hello')
    False
    """
    return is_iterable(obj) and not isinstance(obj, basestring)


def split(src, sep=None, maxsplit=None):
    """Splits an iterable based on a separator. Like :meth:`str.split`,
    but for all iterables. Returns a list of lists.

    >>> split(['hi', 'hello', None, None, 'sup', None, 'soap', None])
    [['hi', 'hello'], ['sup'], ['soap']]

    See :func:`split_iter` docs for more info.
    """
    return list(split_iter(src, sep, maxsplit))


def split_iter(src, sep=None, maxsplit=None):
    """Splits an iterable based on a separator, *sep*, a max of
    *maxsplit* times (no max by default). *sep* can be:

      * a single value
      * an iterable of separators
      * a single-argument callable that returns True when a separator is
        encountered

    ``split_iter()`` yields lists of non-separator values. A separator will
    never appear in the output.

    >>> list(split_iter(['hi', 'hello', None, None, 'sup', None, 'soap', None]))
    [['hi', 'hello'], ['sup'], ['soap']]

    Note that ``split_iter`` is based on :func:`str.split`, so if
    *sep* is ``None``, ``split()`` **groups** separators. If empty lists
    are desired between two contiguous ``None`` values, simply use
    ``sep=[None]``:

    >>> list(split_iter(['hi', 'hello', None, None, 'sup', None]))
    [['hi', 'hello'], ['sup']]
    >>> list(split_iter(['hi', 'hello', None, None, 'sup', None], sep=[None]))
    [['hi', 'hello'], [], ['sup'], []]

    Using a callable separator:

    >>> falsy_sep = lambda x: not x
    >>> list(split_iter(['hi', 'hello', None, '', 'sup', False], falsy_sep))
    [['hi', 'hello'], [], ['sup'], []]

    See :func:`split` for a list-returning version.

    """
    if not is_iterable(src):
        raise TypeError('expected an iterable')

    if maxsplit is not None:
        maxsplit = int(maxsplit)
        if maxsplit == 0:
            yield [src]
            return

    if callable(sep):
        sep_func = sep
    elif not is_scalar(sep):
        sep = frozenset(sep)
        sep_func = lambda x: x in sep
    else:
        sep_func = lambda x: x == sep

    cur_group = []
    split_count = 0
    for s in src:
        if maxsplit is not None and split_count >= maxsplit:
            sep_func = lambda x: False
        if sep_func(s):
            if sep is None and not cur_group:
                # If sep is none, str.split() "groups" separators
                # check the str.split() docs for more info
                continue
            split_count += 1
            yield cur_group
            cur_group = []
        else:
            cur_group.append(s)

    if cur_group or sep is not None:
        yield cur_group
    return


def chunked(src, size, count=None, **kw):
    """Returns a list of *count* chunks, each with *size* elements,
    generated from iterable *src*. If *src* is not evenly divisible by
    *size*, the final chunk will have fewer than *size* elements.
    Provide the *fill* keyword argument to provide a pad value and
    enable padding, otherwise no padding will take place.

    >>> chunked(range(10), 3)
    [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]
    >>> chunked(range(10), 3, fill=None)
    [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, None, None]]
    >>> chunked(range(10), 3, count=2)
    [[0, 1, 2], [3, 4, 5]]

    See :func:`chunked_iter` for more info.
    """
    chunk_iter = chunked_iter(src, size, **kw)
    if count is None:
        return list(chunk_iter)
    else:
        return list(itertools.islice(chunk_iter, count))


def chunked_iter(src, size, **kw):
    """Generates *size*-sized chunks from *src* iterable. Unless the
    optional *fill* keyword argument is provided, iterables not even
    divisible by *size* will have a final chunk that is smaller than
    *size*.

    >>> list(chunked_iter(range(10), 3))
    [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]
    >>> list(chunked_iter(range(10), 3, fill=None))
    [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, None, None]]

    Note that ``fill=None`` in fact uses ``None`` as the fill value.
    """
    # TODO: add count kwarg?
    if not is_iterable(src):
        raise TypeError('expected an iterable')
    size = int(size)
    if size <= 0:
        raise ValueError('expected a positive integer chunk size')
    do_fill = True
    try:
        fill_val = kw.pop('fill')
    except KeyError:
        do_fill = False
        fill_val = None
    if kw:
        raise ValueError('got unexpected keyword arguments: %r' % kw.keys())
    if not src:
        return
    postprocess = lambda chk: chk
    if isinstance(src, basestring):
        postprocess = lambda chk, _sep=type(src)(): _sep.join(chk)
    cur_chunk = []
    i = 0
    for item in src:
        cur_chunk.append(item)
        i += 1
        if i % size == 0:
            yield postprocess(cur_chunk)
            cur_chunk = []
    if cur_chunk:
        if do_fill:
            lc = len(cur_chunk)
            cur_chunk[lc:] = [fill_val] * (size - lc)
        yield postprocess(cur_chunk)
    return


def pairwise(src, count=None, **kw):
    """Convenience function for calling :func:`chunked` with *size* set to
    2.
    """
    return chunked(src, 2, count, **kw)


def pairwise_iter(src, **kw):
    """Convenience function for calling :func:`chunked_iter` with *size*
    set to 2.
    """
    return chunked_iter(src, 2, **kw)


def windowed(src, size):
    """Returns tuples with exactly length *size*. If the iterable is
    too short to make a window of length *size*, no tuples are
    returned. See :func:`windowed_iter` for more.
    """
    return list(windowed_iter(src, size))


def windowed_iter(src, size):
    """Returns tuples with length *size* which represent a sliding
    window over iterable *src*.

    >>> list(windowed_iter(range(7), 3))
    [(0, 1, 2), (1, 2, 3), (2, 3, 4), (3, 4, 5), (4, 5, 6)]

    If the iterable is too short to make a window of length *size*,
    then no window tuples are returned.

    >>> list(windowed_iter(range(3), 5))
    []
    """
    # TODO: lists? (for consistency)
    tees = itertools.tee(src, size)
    try:
        for i, t in enumerate(tees):
            for _ in xrange(i):
                next(t)
    except StopIteration:
        return izip([])
    return izip(*tees)


def xfrange(stop, start=None, step=1.0):
    """Same as :func:`frange`, but generator-based instead of returning a
    list.

    >>> tuple(xfrange(1, 3, step=0.75))
    (1.0, 1.75, 2.5)

    See :func:`frange` for more details.
    """
    if not step:
        raise ValueError('step must be non-zero')
    if start is None:
        start, stop = 0.0, stop * 1.0
    else:
        # swap when all args are used
        stop, start = start * 1.0, stop * 1.0
    cur = start
    while cur < stop:
        yield cur
        cur += step


def frange(stop, start=None, step=1.0):
    """A :func:`range` clone for float-based ranges.

    >>> frange(5)
    [0.0, 1.0, 2.0, 3.0, 4.0]
    >>> frange(6, step=1.25)
    [0.0, 1.25, 2.5, 3.75, 5.0]
    >>> frange(100.5, 101.5, 0.25)
    [100.5, 100.75, 101.0, 101.25]
    >>> frange(5, 0)
    []
    >>> frange(5, 0, step=-1.25)
    [5.0, 3.75, 2.5, 1.25]
    """
    if not step:
        raise ValueError('step must be non-zero')
    if start is None:
        start, stop = 0.0, stop * 1.0
    else:
        # swap when all args are used
        stop, start = start * 1.0, stop * 1.0
    count = int(math.ceil((stop - start) / step))
    ret = [None] * count
    if not ret:
        return ret
    ret[0] = start
    for i in xrange(1, count):
        ret[i] = ret[i - 1] + step
    return ret


def backoff(start, stop, count=None, factor=2):
    """Returns a list of geometrically-increasing floating-point numbers,
    suitable for usage with `exponential backoff`_. Exactly like
    :func:`backoff_iter`, but without the ``'repeat'`` option for
    *count*. See :func:`backoff_iter` for more details.

    .. _exponential backoff: https://en.wikipedia.org/wiki/Exponential_backoff

    >>> backoff(1, 10)
    [1.0, 2.0, 4.0, 8.0, 10.0]
    """
    if count == 'repeat':
        raise ValueError("'repeat' supported in backoff_iter, not backoff")
    return list(backoff_iter(start, stop, count=count, factor=factor))


def backoff_iter(start, stop, count=None, factor=2):
    """Generates a sequence of geometrically-increasing floats, suitable
    for usage with `exponential backoff`_. Starts with *start*,
    increasing by *factor* until *stop* is reached, optionally
    stopping iteration once *count* numbers are yielded. *factor*
    defaults to 2. In general retrying with properly-configured
    backoff creates a better-behaved component for a larger service
    ecosystem.

    .. _exponential backoff: https://en.wikipedia.org/wiki/Exponential_backoff

    >>> list(backoff_iter(1.0, 10.0, count=5))
    [1.0, 2.0, 4.0, 8.0, 10.0]
    >>> list(backoff_iter(1.0, 10.0, count=8))
    [1.0, 2.0, 4.0, 8.0, 10.0, 10.0, 10.0, 10.0]
    >>> list(backoff_iter(0.25, 100.0, factor=10))
    [0.25, 2.5, 25.0, 100.0]

    A simplified usage example:

    .. code-block:: python

      for timeout in backoff_iter(0.25, 5.0):
          try:
              res = network_call()
              break
          except Exception as e:
              log(e)
              time.sleep(timeout)

    An enhancement for large-scale systems would be to add variation
    ("jitter") to the timeout value. This is done to avoid a
    thundering herd on the receiving end of the network call.

    Finally, for *count*, the special value ``'repeat'`` can be passed to
    continue yielding indefinitely.

    """
    if start == 0:
        raise ValueError('start must be >= 0, not %r' % start)
    if not start < (start * factor):
        raise ValueError('start * factor should be greater than start')
    stop = float(stop)
    if count is None:
        count = 1 + math.ceil(math.log(stop/start, factor))
    if count != 'repeat' and count < 0:
        raise ValueError('count must be greater than 0, not %r' % count)
    cur, i = float(start), 0
    while count == 'repeat' or i < count:
        yield cur
        i += 1
        if cur < stop:
            cur *= factor
            if cur > stop:
                cur = stop
    return


def bucketize(src, key=None):
    """Group values in the *src* iterable by the value returned by *key*,
    which defaults to :class:`bool`, grouping values by
    truthiness.

    >>> bucketize(range(5))
    {False: [0], True: [1, 2, 3, 4]}
    >>> is_odd = lambda x: x % 2 == 1
    >>> bucketize(range(5), is_odd)
    {False: [0, 2, 4], True: [1, 3]}

    Value lists are not deduplicated:

    >>> bucketize([None, None, None, 'hello'])
    {False: [None, None, None], True: ['hello']}

    Note in these examples there were at most two keys, ``True`` and
    ``False``, and each key present has a list with at least one
    item. See :func:`partition` for a version specialized for binary
    use cases.
    """
    if not is_iterable(src):
        raise TypeError('expected an iterable')
    if key is None:
        key = bool
    if not callable(key):
        raise TypeError('expected callable key function')

    ret = {}
    for val in src:
        keyval = key(val)
        ret.setdefault(keyval, []).append(val)
    return ret


def partition(src, key=None):
    """No relation to :meth:`str.partition`, ``partition`` is like
    :func:`bucketize`, but for added convenience returns a tuple of
    ``(truthy_values, falsy_values)``.

    >>> nonempty, empty = partition(['', '', 'hi', '', 'bye'])
    >>> nonempty
    ['hi', 'bye']

    *key* defaults to :class:`bool`, but can be carefully overridden to
    use any function that returns either ``True`` or ``False``.

    >>> import string
    >>> is_digit = lambda x: x in string.digits
    >>> decimal_digits, hexletters = partition(string.hexdigits, is_digit)
    >>> ''.join(decimal_digits), ''.join(hexletters)
    ('0123456789', 'abcdefABCDEF')
    """
    bucketized = bucketize(src, key)
    return bucketized.get(True, []), bucketized.get(False, [])


def unique(src, key=None):
    """``unique()`` returns a list of unique values, as determined by
    *key*, in the order they first appeared in the input iterable,
    *src*.

    >>> ones_n_zeros = '11010110001010010101010'
    >>> ''.join(unique(ones_n_zeros))
    '10'

    See :func:`unique_iter` docs for more details.
    """
    return list(unique_iter(src, key))


def unique_iter(src, key=None):
    """Yield unique elements from the iterable, *src*, based on *key*,
    in the order in which they first appeared in *src*.

    >>> repetitious = [1, 2, 3] * 10
    >>> list(unique_iter(repetitious))
    [1, 2, 3]

    By default, *key* is the object itself, but *key* can either be a
    callable or, for convenience, a string name of the attribute on
    which to uniqueify objects, falling back on identity when the
    attribute is not present.

    >>> pleasantries = ['hi', 'hello', 'ok', 'bye', 'yes']
    >>> list(unique_iter(pleasantries, key=lambda x: len(x)))
    ['hi', 'hello', 'bye']
    """
    if not is_iterable(src):
        raise TypeError('expected an iterable, not %r' % type(src))
    if key is None:
        key_func = lambda x: x
    elif callable(key):
        key_func = key
    elif isinstance(key, basestring):
        key_func = lambda x: getattr(x, key, x)
    else:
        raise TypeError('"key" expected a string or callable, not %r' % key)
    seen = set()
    for i in src:
        k = key_func(i)
        if k not in seen:
            seen.add(k)
            yield i
    return


def one(src, default=None, key=None):
    """Along the same lines as builtins, :func:`all` and :func:`any`, and
    similar to :func:`first`, ``one()`` returns the single object in
    the given iterable *src* that evaluates to ``True``, as determined
    by callable *key*. If unset, *key* defaults to :class:`bool`. If
    no such objects are found, *default* is returned. If *default* is
    not passed, ``None` is returned.

    If *src* has more than one object that evaluates to ``True``, or
    if there is no object that fulfills such condition, return
    ``False``. It's like an `XOR`_ over an iterable.

    >>> one((True, False, False))
    True
    >>> one((True, False, True))
    >>> one((0, 0, 'a'))
    'a'
    >>> one((0, False, None))
    >>> one((True, True), default=False)
    False
    >>> bool(one(('', 1)))
    True
    >>> one((10, 20, 30, 42), key=lambda i: i > 40)
    42

    See `Martín Gaitán's original repo`_ for further use cases.

    .. _Martín Gaitán's original repo: https://github.com/mgaitan/one
    .. _XOR: https://en.wikipedia.org/wiki/Exclusive_or

    """
    the_one = default
    for i in src:
        if key(i) if key else i:
            if the_one:
                return default
            the_one = i
    return the_one


def first(iterable, default=None, key=None):
    """Return first element of *iterable* that evaluates to ``True``, else
    return ``None`` or optional *default*. Similar to :func:`one`.

    >>> first([0, False, None, [], (), 42])
    42
    >>> first([0, False, None, [], ()]) is None
    True
    >>> first([0, False, None, [], ()], default='ohai')
    'ohai'
    >>> import re
    >>> m = first(re.match(regex, 'abc') for regex in ['b.*', 'a(.*)'])
    >>> m.group(1)
    'bc'

    The optional *key* argument specifies a one-argument predicate function
    like that used for *filter()*.  The *key* argument, if supplied, should be
    in keyword form. For example, finding the first even number in an iterable:

    >>> first([1, 1, 3, 4, 5], key=lambda x: x % 2 == 0)
    4

    Contributed by Hynek Schlawack, author of `the original standalone module`_.

    .. _the original standalone module: https://github.com/hynek/first
    """
    if key is None:
        for el in iterable:
            if el:
                return el
    else:
        for el in iterable:
            if key(el):
                return el

    return default


from collections import Mapping, Sequence, Set, ItemsView

try:
    from typeutils import make_sentinel
    _EXIT = make_sentinel('_EXIT')
except ImportError:
    _EXIT = object()


def default_visit(key, value):
    # print('visit(%r, %r)' % (key, value))
    return key, value


def default_enter(key, value):
    # print('enter(%r, %r)' % (key, value))
    try:
        iter(value)
    except TypeError:
        return value, False
    if isinstance(value, basestring):
        return value, False
    elif isinstance(value, Mapping):
        return value.__class__(), ItemsView(value)
    elif isinstance(value, Sequence):
        return value.__class__(), enumerate(value)
    elif isinstance(value, Set):
        return value.__class__(), enumerate(value)
    return value, False


def default_exit(new_items, new_parent, old_parent):
    # print('exit(%r, %r, %r)' % (new_items, new_parent, old_collection))
    ret = new_parent
    if isinstance(new_parent, Mapping):
        new_parent.update(new_items)
    elif isinstance(new_parent, Sequence):
        vals = [v for i, v in new_items]
        try:
            new_parent.extend(vals)
        except AttributeError:
            ret = new_parent.__class__(vals)  # tuples
    elif isinstance(new_parent, Set):
        vals = [v for i, v in new_items]
        try:
            new_parent.update(new_items)
        except AttributeError:
            ret = new_parent.__class__(vals)  # frozensets
    else:
        raise RuntimeError('unexpected iterable type: %r' % type(new_parent))
    return ret


def remap(root, visit=default_visit, enter=default_enter, exit=default_exit,
          reraise_visit=True):
    # TODO: documentation
    # TODO: enter() returns preopulated collection
    # TODO: enter() takes a fully-qualified key (aka path)
    # TODO: enter() return (False, items) to continue traverse but cancel copy?
    if not callable(visit):
        raise TypeError('visit expected callable, not: %r' % visit)
    if not callable(enter):
        raise TypeError('enter expected callable, not: %r' % enter)
    if not callable(exit):
        raise TypeError('exit expected callable, not: %r' % exit)

    stack = [(None, root)]
    registry = {}
    new_items_stack = []
    while stack:
        key, value = stack.pop()
        id_value = id(value)
        if key is _EXIT:
            key, new_parent, old_parent = value
            id_value = id(old_parent)
            value = exit(new_items_stack.pop(), new_parent, old_parent)
            registry[id_value] = value
            if not new_items_stack:
                continue
        elif id_value in registry:
            value = registry[id_value]
        else:
            res = enter(key, value)
            try:
                new_parent, new_items = res
            except TypeError:
                # TODO: handle False?
                raise TypeError('enter should return a tuple of (new_parent,'
                                ' items_iterator), not: %r' % res)
            if new_items is not False:
                # traverse unless False is explicitly passed
                registry[id_value] = new_parent
                new_items_stack.append([])
                stack.append((_EXIT, (key, new_parent, value)))
                if new_items:
                    stack.extend(reversed(list(new_items)))
                continue
        try:
            visited_item = visit(key, value)
        except:
            if reraise_visit:
                raise
            visited_item = True
        if visited_item is False:
            continue  # drop
        elif visited_item is True:
            visited_item = (key, value)
        # TODO: typecheck?
        #    raise TypeError('expected (key, value) from visit(),'
        #                    ' not: %r' % visited_item)
        try:
            new_items_stack[-1].append(visited_item)
        except IndexError:
            raise TypeError('expected remappable root, not: %r' % root)
    return value


"""The marker approach to solving self-reference problems in remap
won't work because we can't rely on exit returning a
traversable, mutable object. We may know that the marker is in the
items going into exit but there's no guarantee it's not being
filtered out or being made otherwise inaccessible for other reasons.

On the other hand, having enter return the new parent instance
before it's populated is a pretty workable solution. The division of
labor stays clear and exit still has some override powers. Also
note that only mutable structures can have self references (unless
getting really nasty with the Python C API). The downside is that
enter must do a bit more work and in the case of immutable
collections, the new collection is discarded, as a new one has to be
created from scratch by exit. The code is still pretty clear
overall.

Not that remap is supposed to be a speed demon, but here are some
thoughts on performance. Memorywise, the registry grows linearly with
the number of collections. The stack of course grows in proportion to
the depth of the data. Many intermediate lists are created, but for
most data list comprehensions are much faster than generators (and
generator expressions). The ABC isinstance checks are going to be dog
slow. As soon as a couple large enough use case cross my desk, I'll be
sure to profile and optimize. It's not a question of if isinstance+ABC
is slow, it's which pragmatic alternative passes tests while being
faster.

TODO Examples:

  * sort all lists
  * normalize all keys
  * convert all dicts to OrderedDicts
  * drop all Nones

"""
