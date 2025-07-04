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


## `@parametrized`

Not so much a fixtures tool, however unittest-fixtures also comes with a
`@parametrized` decorator that acts as a wrapper for unittest's
[subtests](https://docs.python.org/3/library/unittest.html#distinguishing-test-iterations-using-subtests).
A rather contrived example comes from unittest-fixtures own tests:


```python
from unittest_fixtures import parametrized

class ParametrizeTests(TestCase):
    values = {1, 2}

    @parametrized([[1, values], [2, values], [None, values]])
    def test(self, value, values):
        if value is not None:
            self.assertIn(value, values)
            values.discard(value)
            return
        self.assertEqual(set(), values)
```

## Conclusion

Creating unittest fixtures is clean and fun with unittest-fixtures.
