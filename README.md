# unittest-fixtures: A small library for loading unittest fixtures

## Description

unittest-fixtures spun off from my [Gentoo Build
Publisher](https://github.com/enku/gentoo-build-publisher) project. I use
[unittest](https://docs.python.org/3/library/unittest.html), the test
framework in the Python standard library, where it's customary to define a
TestCase's fixtures in the `.setUp()` method. Having done it this way for
years, it occurred to me one day that this goes against
[OCP](https://en.wikipedia.org/wiki/Open%E2%80%93closed_principle). What if
instead of cracking open the `.setUp()` method to add a fixture to a TestCase
one could instead add a decorator?  That's what unittest-fixtures allows one
to do.

```python
from unittest_fixtures import given

@given(dog)
class MyTest(TestCase):
    def test_method(self, fixtures):
        dog = fixtures.dog
```

In the above example, `dog` is a fixture function. Fixture functions are
passed to the `given` decorator. When the test method is run, the fixtures are
"instantiated" and attached to the `fixtures` keyword argument of the test
method.


## Fixture functions

Fixture functions are functions that one defines that return a "fixture". For
example the above dog fixture might look like this:

```python
from unittest_fixtures import fixture

@fixture()
def dog(fixtures):
    return Dog(name="Fido")
```

Fixture functions are always passed a `Fixtures` argument. Because fixtures
can depend on other fixtures. For example:

```python
@fixture(dog)
def person(fixtures):
    p = Person(name="Jane")
    p.pet = fixtures.dog
    return p
```

Fixture functions **can** have keyword parameters, but those parameters
**must** have defaults.

```python
@fixture
def dog(fixtures, name="Fido"):
    return Dog(name=name)
```

Then one's TestCase can use the `where` decorator to passed the parameter:


```python
from unittest_fixtures import given, where

@given(dog)
@where(dog__name="Buddy")
class MyTest(TestCase):
    def test_method(self, fixtures):
        dog = fixtures.dog
        self.assertEqual("Buddy", dog.name)
```

## Duplicating fixtures

The unittest-fixtures library allows one to use a fixture more than once. This
can be done by passing the fixture as a keyword argument giving different
names to the same fixture. Different parameters can be passed to them:

```python
@given(fido=dog, buddy=dog)
@where(fido__name="Fido", buddy__name="Buddy")
class MyTest(TestCase):
    def test_method(self, fixtures):
        self.assertEqual("Buddy", fixtures.buddy.name)
        self.assertEqual("Fido", fixtures.fido.name)
```

Fixture-depending fixtures will all use the same fixture, but only if they
have the same name. So in the above example, if we also gave the TestCase the
`person` fixture, that person would have a different dog because it depends on
a fixture called "dog". However this will work:

```python
@given(dog, person)
class MyTest(TestCase):
    def test_method(self, fixtures):
        dog = fixtures.dog
        person = fixtures.person
        self.assertIs(person.pet, dog)
```

## `@where` (fixture parameters)

The `where` decorator can be used to pass parameters to a fixture function.
Fixture functions are not required to take arguments. To pass a parameter to a
function, for example pass `name` to the `dog` fixture it's the name of the
function, followed by `__` followed by the parameter name. For example:
`dog__name`.  Fixture functions can also have a parameter that is the same
name as the fixture itself. For example:

```python
@given(settings)
@where(settings={"DEBUG": True, "SECRET": "sauce"})
class MyTest(TestCase):
    ...
```

There are times when one may desire to pass a fixture parameter that uses the
value of another fixture, however that value does not get calculated until
each test is run. The `Param` type allows one to accomplish this:

```python
from unittest_fixtures import Param, given, where


@given(person)
@where(person__name=Param(lambda fixtures: fixtures.name))
@given(name=random_choice)
@where(name__choices=["Liam", "Noah", "Jack", "Oliver"])
class MyTest(TestCase):
    ...
```

> [!NOTE]
> In the above example, fixture ordering is important. Given that `person`
> *implicitly* depends on `name`, the `name` fixture needs to be set up first.
> We do this by declaring it before (lower vertically in the list of
> decorators) than the `person` fixture.

## Fixtures as context managers

Sometimes a fixture will need a setup and teardown process. If
unittest-fixtures is supposed to remove the need to open `setUp()`, then it
must also remove the need to open `tearDown()`. And it does this by by
defining itself as a generator function. For example:

```python
import tempfile

@fixture()
def tmpdir(fixtures):
    with tempfile.TemporaryDirectory() as tempdir:
        yield tempdir
```

Using the `unittest.mock` library is another good example of using context
manager fixtures.


## fixture-depending fixtures

As stated above, fixtures can depend on other fitures. This is done by
"declaring" the dependencies in the `fixture` decorator.  Fixtures are then
passed as an argument to the fixture function:

```python
@fixture(settings, tmpdir)
def jenkins(fixtures, root=None):
    root = root or fixtures.tmpdir
    settings = replace(fixtures.settings, STORAGE_PATH=root)
    return Jenkins.from_settings(settings)
```

The above example shows that one can get pretty fancy... or creative with
one's fixture definitions.

Fixtures can also have named dependencies. So in the above example, if one
wanted a different `tmpdir` than the "global" one:

```python
@fixture(settings, jenkins_root=tmpdir)
def jenkins(fixtures, root=None):
    root = root or fixtures.jenkins_root
    settings = replace(fixtures.settings, STORAGE_PATH=root)
    return Jenkins.from_settings(settings)
```

If a TestCase used both `jenkins` and `tmpdir`:

```python
@given(tmpdir, jenkins)
class MyTest(TestCase):
   def test_something(self, fixtures):
       self.assertNotEqual(fixtures.jenkins.root, fixtures.tmpdir)
```

Again if the two fixtures have different names then they are two separate
fixtures.  In general one should not use named fixtures unless one wants
multiple fixtures of the same type.


## `@params` (parametrized tests)

Not to be confused with `@parametrized` (below) which works similarly. The `params`
decorator turns a TestCase's methods into parametrized tests, however, unlike
`@parametrized`, the parameters are passed into the fixtures argument instead of
additional arguments to the test method.  For example:

```python
from unittest_fixtures import params

@params(number=[1, 2, 3], square=[1, 4, 9])
class MyTest(TestCase):
    def test(self, fixtures):
        self.assertEqual(fixtures.number**2, fixtures.square)
```

In the above example, the `test` method is called three times. With each iteration the
`fixtures` parameter has the values:

1. `Fixtures(number=1, square=1)`
2. `Fixtures(number=2, square=4)`
3. `Fixtures(number=3, square=9)`

Using this method, and `Param` above, a parameterized tests can use a test parameter as
a parameter in a fixture. Consider the example:

```python
@given(dog)
@params(name=["Fido", "Spot", "Rex"])
@where(dog__name=Param(lambda fixtures: f"{fixtures.name} Woofington"))
class MyTest(TestCase):
    def test(self, fixtures):
        print(fixtures.dog.name)
```

When run this test produces the output:

```
Fido Woofington
Spot Woofington
Rex Woofington
```

## `@parametrized`

The `@parametrized` decorator that acts as a wrapper for unittest's
[subtests](https://docs.python.org/3/library/unittest.html#distinguishing-test-iterations-using-subtests).
Unlike `@params` above, this decorator is to be applied to `TestCase` methods rather
than tests themselves.  In this case extra parameters are passed to the test method.
This can be used if you only want to parameterize a specific test method in a `TestCase`
rather than all test methods.

For example:

```python
from unittest_fixtures import parametrized

class ParametrizeTests(TestCase):
    @parametrized([[1, 1], [2, 4], [3, 9]])
    def test(self, number, square):
        self.assertEqual(number**2, square)
```

## `@combine` (parametrized tests using the product of values)

The `combine` decorator turns a TestCase's methods into parametrized tests similar to
`@params`, however, the parameters are combined as taking a cartesian product of the
parameters. For example:

```python
@combine(first=["Spuds", "Rin", "Old"], last=["MacKenzie", "Tin Tin", "Yeller"])
class MyTest(TestCase):
    def test(self, fixtures):
        print(f"{fixtures.first} {fixtures.last}")
```

When run this test produces the output:

```
Spuds MacKenzie
Spuds Tin Tin
Spuds Yeller
Rin MacKenzie
Rin Tin Tin
Rin Yeller
Old MacKenzie
Old Tin Tin
Old Yeller
```

The `@combine` decorator can also be used in combination with `@params` and, of course,
`@given` fixtures.


## The `fixtures` kwarg may be overridden

The `fixtures` keyword argument is automatically passed to TestCase methods
when the test is run. The name of the keyword argument can be overridden as
follows:

```python
@given(dog)
class MyTest(TestCase):
    unittest_fixtures_kwarg = "fx"

    def test_method(self, fx):
        dog = fx.dog
```


## Recipes

The following are real-world examples of using unittest-fixtures.

### Random Number Generator

From [larry](https://github.com/enku/larry):

```python
import random as stdlib_random
from unittest import mock

from unittest-fixtures import fixture


@fixture()
def random(fixtures, target="larry.color.random", seed=1):
    _random = stdlib_random.Random(seed)
    with mock.patch(target, new=_random):
        yield _random
```


### Temporary Directory

Also from [larry](https://github.com/enku/larry):

```python
import tempfile

from unittest-fixtures import fixture


@fixture()
def tmpdir(fixtures):
    with tempfile.TemporaryDirectory() as tempdir:
        yield tempdir
```


### Mock Environment Variables

From [gbp-webhook-playsound](https://github.com/enku/gbp-webhook-playsound):

```python
import os


@fixture()
def environ(fixtures, environ=None, clear=True):
    with mock.patch.dict(os.environ, clear=clear):
        os.environ.update(environ or {})
        yield os.environ
```

### Local Timezone

From [gbpcli](https://github.com/enku/gbpcli):

```python
import datetime as dt
from unittest import mock


LOCAL_TIMEZONE = dt.timezone(dt.timedelta(days=-1, seconds=61200), "PDT")


@fixture()
def local_timezone(fixtures, local_timezone=LOCAL_TIMEZONE):
    with mock.patch("gbpcli.render.LOCAL_TIMEZONE", new=local_timezone):
        yield local_timezone
```

### Django HttpRequest

From [gbp-feeds](https://github.com/enku/gbp-feeds):

```python
from django.http import HttpRequest


@fixture()
def request(fixtures, path="/feed.atom", server_name="testserver", server_port=80):
    request = HttpRequest()
    request.path = path
    request.META["SERVER_NAME"] = server_name
    request.META["SERVER_PORT"] = server_port

    return request
```


### `sys.argv`

From [gbp-webhook](https://github.com/enku/gbp-webhook):

```python
import mock
import sys


@fixture()
def argv(fixtures, argv=None):
    argv = ["gbp", "webhook", "serve"] if argv is None else list(argv)

    with mock.patch.object(sys, "argv", new=argv):
        yield argv
```


### `mock.patch`

Instead of applying `mock.patch` and/or `mock.patch.object` decorators to a `TestCase`,
one can instead use a fixture. This way mocked objects appear as part of the `fixtures`
test parameter instead of having separate arguments for mocks. The following recipe
demonstrates how this can be done.

From
[gbp-testkit](https://github.com/enku/gentoo-build-publisher/tree/master/src/gbp_testkit)
(a component of gentoo-build-publisher):

```python
NO_OBJECT = object()  # sentinel value

@fixture()
def patch(_, target="", object=NO_OBJECT, **kwargs):
    if not target:
        patcher = None
        fake = mock.Mock(**kwargs)
    elif object is _NO_OBJECT:
        patcher = mock.patch(target, **kwargs)
        fake = patcher.start()
    else:
        patcher = mock.patch.object(object, target, **kwargs)
        fake = patcher.start()

    yield fake

    if patcher:
        patcher.stop()
```

So with this the above `sys.argv` fixture can be replaced with:

```python
@given(argv=patch)
@where(argv__object=sys, argv__target="argv", argv__new=["gbp", "webhook", "serve"])
class MyTest(TestCase)
    def test_method(self, fixtures):
         status_code = main()

         self.assertEqual(status_code, 0)
```

Alternatively, insteady of passing the `sys` object one could also:

```python
@where(argv__target="sys.argv", argv__new=["gbp", "webhook", "serve"])
```
