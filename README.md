# Python Framework for FEMM (currently Windows only)

Work in progress, commands are being added as the wrapper is used,
therefore not all commands have been wrapped.

## Introduction

FEMM is a handy piece of software, although I felt it's API is not as user-friendly as it could be. The motivation
behind this light framework is to improve the usability of the FEMM API and also to add some additional features,
such as hot reloading of the model definition to aid rapid model design and multiprocessing to speed up the running
of the analysis stage when solving for many different models.

Currently the wrapper is designed to use the magnetics mode of FEMM (`mi_` and `mo_` prefixes). As further development
goes on the other three modes will be properly incorporated.

All command names are the same as shown in the FEMM manual with the
exception of correct Python naming. For example `addnode` becomes `add_node`.

This framework's API is not a one for one mapping of the FEMM API, I have made some design choices to make it easier
to use and debug. The main difference is opting for the use of named arguments over position arguments. When using
positional arguments I found myself consistently going back and forth between my FEMM code and the documentation. During
the time I have spent using this framework I have has to do this far less often. The example below illustrates this:

```python
# This is how to set a block's properties in pyFEMM.
femm.mi_setblockprop("my block name", 0, 10, "some circuit name", 0, "<None>", 100)


# This is how to set a block's properties using python-femm.
femm.set_block_prop(
    block_name='my block name',
    auto_mesh=False,
    mesh_size=10,
    in_circuit='some circuit name',
    mag_direction=0,
    # Notice if we want to set an argument to "<None>" we just don't 
    # give it a value here, i.e. I am choosing to leave out ``group``.
    turns=100,
)
```

In the example above we can see that, to use the FEMM API we need to remember not only the names of all the arguments
but also their positions in the list of arguments. This framework's API relieves the user of having to remember the
order of the arguments as named arguments do not depend on the order in which they are passed to the function. Also the
code becomes self documenting to any other person looking over the code, they don't need to refer to the FEMM manual to
find out what 4th positional argument of the function call is actually defining. An additional benefit of using named
arguments is that code editors can provide code hints.

## Defining a model

To define a model you must extend the `BaseRunner` class in a file called `model.py` (must be in the project
root directory). A model has five methods, two of which are defined already in `BaseRunner`, so you don't need to define them yourself unless
you need to. The other three will raise a `NotImplementedError` if they have not been defined and are called.

### The `pre` method

The `pre` method is responsible for drawing the model. This is also the method that is re-run when the `model.py` file changes
thanks to the hot reloader. The `Runner` class will have access to the `FEMMSession` via `self.session`.

Here's a quick example where a circle is drawn:

```python
class Runner(BaseRunner):

    def pre(self):
        # Start a new document in magnetics mode. This will mean
        # that all future commands will have 'm' prefixed to them
        # when the FEMM script is run. This means we don't have to
        # always write the 'mi_' or 'mo_' bits of each command.
        self.session.new_document('magnetics')
        
        # Define some geometry. Here ``self.session.pre`` is how we
        # access all of the magnetics preprocessor commands. All methods
        # run from ``self.session.pre`` will have 'i' prefixed to them.
        self.session.pre.draw_circle(points=[[10, 10]])

```

FEMM's way of defining points works but can be a little messy. In `python-femm` a standardised method of defining points is used.
Every command that requires positional information such as `(x, y)` or `(x1, y1), (x2, y2)` will accept a named parameter
called `points`. The structure of `points` is a "list of lists", i.e. `points=[[1, 2], [3, 4]]` would relate to `x1 = 1`, `y1
= 2`, `x2 = 3` and `y2 = 4`. Note, this structure is still used for a single set of points, i.e. `points=[[1, 2]]` would
relate to `x = 1` and `y = 2`. Defining points this way means that the same approach is used for every single command
that needs positional information, this enables to use of the patterning feature that will be mentioned later.

A more clear example is given below:

```python
def pre(self):
    # Define an arc from (0, 0) to (5, 5).
    self.session.pre.draw_arc(points=[[0, 0], [5, 5]], angle=30, max_seg=1)
    
    # Define a polygon which vertices at (0, 0), (1, 0), (1, 1) and (0, 1).
    self.session.pre.draw_polygon(points=[[0, 0], [1, 0], [1, 1], [0, 1]])
    
    # Define a node at (4, 4).
    self.session.add_node(points=[[4, 5]])
```

`python-femm` provides a very easy method of adding elements to groups as they are defined. You no longer need to draw an
element, select it, set it's group and then deselect it. You can just pass the group number when you define it like so:

```python
def pre(self):
    # Define an arc from (0, 0) to (5, 5) and set it to be in group 2.
    self.session.pre.draw_arc(points=[[0, 0], [5, 5]], angle=30, max_seg=1, group=2)
    #                                                                       ^^^^^^^ We just define the group here.
```

Much easier. 

What is hot reloading then? Hot reloading is a development tool that makes incremental development much less
painful by listening to the `model.py` file for changes. When you make a change and save, `python-femm` will re-run the
`pre` method with the changes and update the FEMM model automatically. No more having to run commands after every change.

### The `solve` method

The `solve` method contains code that is pertinent to the analysis stage. A simple example illustrates this:

```python
def solve(self):
    # Analyse, zoom to fit and then load the solution.
    self.session.pre.analyze()
    self.session.pre.zoom_natural()
    self.session.pre.load_solution()
```

### The `post` method

The `post` method contains code that tells `python-femm` how you want to use the FEMM postprocessor. Another simple
example explains this:

```python
def post(self):
    # Select a block by position and then run a block integral.
    self.session.post.select_block(points=[[10, 10]])
    value = self.session.post.block_integral(19)  # Using an integral type of 19.
    return value
```

It should be reiterated that the `pre`, `solve` and `post` methods are all defined on the `Runner` class. I have combined
the examples above to illustrate what a complete model definition might look like:

```python
class Runner(BaseRunner):

    def pre(self):
        # Define an arc from (0, 0) to (5, 5) and set it to be in group 2.
        self.session.pre.draw_arc(points=[[0, 0], [5, 5]], group=2)

    def solve(self):
        # Analyse, zoom to fit and then load the solution.
        self.session.pre.analyze()
        self.session.pre.zoom_natural()
        self.session.pre.load_solution()
        
    def post(self):
        # Select a block by position and then run a block integral.
        self.session.post.select_block(points=[[10, 10]])
        value = self.session.post.block_integral(19)  # Using an integral type of 19.
        return value
```

Note that you will not ever run these commands yourself, this brings us onto the management commands.

## Management commands

Once you have a valid (valid doesn't mean completed) model definition you can begin to use the management commands.
There are several management commands that aid you in working with FEMM more effectively.

These commands are run from the terminal like so (the working directory must be the root of the project):

```
python manage.py <command_name>
```

There are five management commands:

- `pre`: this will run the `pre` method in the model definition once and wait until either FEMM closes or you press
`CTRL + C`.

- `dev`: this will run the `pre` method with the hot reloader. Again, it will close when you press `CTRL + C`. 

- `solve`: this will run the `pre` method and then the `solve` method of your model definition.

- `post`: this will run the `pre` method, the `solve` method and then the `post` method of your model definition.

- `scene`: (work in progress) this will run a scene where the `post` (and all proceeding methods) will be run iteratively
for a range of values. This will run each analysis concurrently providing a large speed up compared with running them
sequentially.