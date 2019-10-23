import os
import win32com.client
import numpy as np

DOCTYPE_MAPPING = {
    'magnetics': 1,
    'electrostatics': 2,
    'heat': 3,
    'current': 4,
}

DOCTYPE_PREFIX_MAPPING = {
    0: 'm',
    'magnetics': 'm',
    1: 'e',
    'electrostatics': 'e',
    2: 'h',
    'heat': 'h',
    3: 'c',
    'current': 'c',
}

PREFIX_DOCTYPE_MAPPING = {
    'm': 'magnetics',
    'e': 'electrostatics',
    'h': 'heat',
    'c': 'current',
}


class FEMMSession:
    """A simple wrapper around FEMM 4.2."""

    doctype_prefix = None

    def __init__(self):
        self.__to_femm = win32com.client.Dispatch('femm.ActiveFEMM')
        self.set_current_directory()
        self.pre = PreprocessorAPI(self)
        self.post = PostProcessorAPI(self)

    def _add_doctype_prefix(self, string):
        return self.doctype_prefix + string

    def call_femm(self, string, add_doctype_prefix=False):
        """Call a given command string using ``mlab2femm``."""

        if add_doctype_prefix:
            res = self.__to_femm.mlab2femm(self._add_doctype_prefix(string))
        else:
            res = self.__to_femm.mlab2femm(string)
        if len(res) == 0:
            res = []
        elif res[0] == 'e':
            raise Exception(res)
        else:
            try:
                res = eval(res)
            except SyntaxError:
                # TODO: Look into this.
                pass
        if len(res) == 1:
            res = res[0]
        return res

    def call_femm_noeval(self, string):
        """Call a given command string using ``mlab2femm`` without eval."""

        self.__to_femm(string)

    def call_femm_with_args(self, command, *args, add_doctype_prefix=True, **kwargs):
        """Call a given command string using ``mlab2femm`` and parse the args."""

        if add_doctype_prefix:
            return self.call_femm(self._add_doctype_prefix(command) + self._parse_args(args))
        return self.call_femm(command + self._parse_args(args), **kwargs)

    @staticmethod
    def _fix_path(path):
        """Replace \\ and // with a single forward slash."""

        return path.replace('\\', '/').replace('//', '/')

    def _parse_args(self, args):
        """Convert each argument into a string and then join them by commas."""

        parsed_args = []
        for arg in args:
            if isinstance(arg, str):
                parsed_args.append(self._quote(arg))
            elif isinstance(arg, bool):
                parsed_args.append('1' if arg else '0')
            elif arg is None:
                parsed_args.append(self._quote('<None>'))
            else:
                parsed_args.append(str(arg))
        args_string = ', '.join(parsed_args)
        return f'({args_string})'

    @staticmethod
    def _quote(string):
        return f'"{string}"'

    def set_current_directory(self, path=None):
        """Set the current working directory using ``os.getcwd()``."""

        path_of_current_directory = self._fix_path(os.getcwd() if path is None else path)
        self.call_femm(f'setcurrentdirectory({self._quote(path_of_current_directory)})')

    def new_document(self, doctype):
        """Creates a new preprocessor document and opens up a new preprocessor window. Specify doctype
        to be 0 for a magnetics problem, 1 for an electrostatics problem, 2 for a heat flow problem,
        or 3 for a current flow problem. An alternative syntax for this command is create(doctype)."""

        mode = DOCTYPE_MAPPING[doctype] if isinstance(doctype, str) else doctype
        self.call_femm(f'newdocument({mode})')
        self.set_mode(mode)

    def quit(self):
        """Close all documents and exit the the Interactive Shell at the end of
        the currently executing Lua script."""

        self.call_femm('quit()')

    def set_mode(self, doctype):
        self.doctype_prefix = DOCTYPE_PREFIX_MAPPING[doctype]

    @property
    def mode(self):
        return PREFIX_DOCTYPE_MAPPING[self.doctype_prefix]


class BaseAPI:
    mode_prefix = None

    def __init__(self, session):
        self.session = session

    def _add_mode_prefix(self, string):
        return f'{self.mode_prefix}_{string}'

    def _call_femm(self, string, **kwargs):
        return self.session.call_femm(f'{self._add_mode_prefix(string)}()', **kwargs)

    def _call_femm_with_args(self, string, *args, **kwargs):
        return self.session.call_femm_with_args(self._add_mode_prefix(string), *args, **kwargs)


class PreprocessorAPI(BaseAPI):
    """Preprocessor API."""

    mode_prefix = 'i'

    def close(self):
        """Closes current magnetics preprocessor document and
        destroys magnetics preprocessor window."""

        self._call_femm('close', add_doctype_prefix=True)

    # Utilities

    @staticmethod
    def draw_pattern(commands=None, center=None, repeat=None):
        change_in_angle = (2 * np.pi) / repeat
        ret = []
        for command, kwargs in commands:
            command_ret = [kwargs['points']]
            for i in range(repeat):
                if i == 0:
                    try:
                        command(i=i, **kwargs)
                    except TypeError:
                        command(**kwargs)
                else:
                    points = kwargs['points']
                    pattern_angle = change_in_angle * i
                    rotation_matrix = np.array([[np.cos(pattern_angle), -np.sin(pattern_angle)],
                                                [np.sin(pattern_angle), np.cos(pattern_angle)]])
                    # Transform all points to center rotation about the origin.
                    new_points = [point - np.array(center) for point in points]
                    # Rotate all points by ``pattern_angle``.
                    new_points = [np.dot(rotation_matrix, np.array(point).reshape(2, 1)).reshape(2) for point in
                                  new_points]
                    # Transform all points back to their original center.
                    new_points = [point + np.array(center) for point in new_points]
                    new_points = [np.round(point, decimals=5).tolist() for point in new_points]
                    command_ret.append(new_points)
                    try:
                        command(points=new_points, i=i,
                                **{key: kwargs[key] for key in kwargs.keys() if not key == 'points'})
                    except TypeError:
                        command(points=new_points,
                                **{key: kwargs[key] for key in kwargs.keys() if not key in ('points', 'i')})
            ret.append(command_ret)
        return ret

    # Object Add/Remove Commands

    def add_node(self, points=None, group=None):
        """Add a new node at x, y."""

        x, y = points[0]
        self._call_femm_with_args('addnode', x, y)
        if group is not None:
            self.select_node(points=points)
            self.set_group(group)
            self.clear_selected()

    def add_segment(self, points=None, group=None):
        """Add a new line segment from node closest to (x1, y1) to node closest to (x2, y2)."""

        x1, y1 = points[0]
        x2, y2 = points[1]
        self._call_femm_with_args('addsegment', x1, y1, x2, y2)
        if group is not None:
            self.select_segment(points=points)
            self.set_segment_prop(group=group)
            self.clear_selected()

    def add_block_label(self, points=None, block_name=None, in_circuit=None, i=None, **kwargs):
        """Add a new block label at (x, y)."""

        x, y = points[0]
        self._call_femm_with_args('addblocklabel', x, y)
        if block_name is not None:
            self.select_label(points=points)
            self.set_block_prop(block_name=block_name, in_circuit=in_circuit.format(i=i + 1), **kwargs)
            self.clear_selected()

    def add_arc(self, points=None, angle=None, max_seg=None, group=None):
        """Add a new arc segment from the nearest node to (x1, y1) to the nearest node to
        (x2, y2) with angle ‘angle’ divided into ‘max_seg’ segments."""

        self._call_femm_with_args('addarc', *points[0], *points[1], angle, max_seg)
        if group is not None:
            self.select_arc_segment(points=points)
            self.set_group(group)
            self.clear_selected()

    def draw_line(self, points=None, group=None):
        """Adds nodes at (x1,y1) and (x2,y2) and adds a line between the nodes."""

        self.add_node(points=[points[0]], group=group)
        self.add_node(points=[points[1]], group=group)
        self.add_segment(points=points, group=group)

    def draw_polyline(self, points=None, group=None):
        """Adds nodes at each of the specified points and connects them with segments.
        ``points`` will look something like [[x1, y1], [x2, y2], ...]"""

        for i, current_point in enumerate(points):
            # Add each node.
            self.add_node(points=[current_point], group=group)
            if 0 < i < len(points):
                # Draw lines between each node.
                previous_point = points[i - 1]
                self.draw_line(points=[previous_point, current_point], group=group)

    def draw_polygon(self, points=None, group=None):
        """Adds nodes at each of the specified points and connects them with
        segments to form a closed contour."""

        self.draw_polyline(points=points, group=group)
        # Connect the first and the last nodes.
        self.draw_line(points=[points[0], points[::-1][0]], group=group)

    def draw_arc(self, points=None, angle=None, max_seg=None, group=None):
        """Adds nodes at (x1,y1) and (x2,y2) and adds an arc of the specified
        angle and discretization connecting the nodes."""

        self.add_node(points=[points[0]], group=group)
        self.add_node(points=[points[1]], group=group)
        self.add_arc(points=points, angle=angle, max_seg=max_seg, group=group)

    def draw_circle(self, points=None, radius=None, max_seg=None, group=None):
        """Adds nodes at the top and bottom points of a circle centred at
        (x1, y1) with the provided radius."""

        x, y = points[0]
        top_point = (x, y + (radius / 1))
        bottom_point = (x, y - (radius / 1))
        self.draw_arc(points=[top_point, bottom_point], angle=180, max_seg=max_seg, group=group)
        self.draw_arc(points=[bottom_point, top_point], angle=180, max_seg=max_seg, group=group)

    def draw_annulus(self, points=None, inner_radius=None, outer_radius=None, max_seg=None, group=None):
        """Creates two concentric circles with the outer and inner radii provided.
        The same ``max_seg`` value is used for both circles."""

        self.draw_circle(points=points, radius=inner_radius, max_seg=max_seg, group=group)
        self.draw_circle(points=points, radius=outer_radius, max_seg=max_seg, group=group)

    def draw_rectangle(self, points=None, group=None):
        """Adds nodes at the corners of a rectangle defined by the points (x1, y1) and
        (x2, y2), then adds segments connecting the corners of the rectangle."""

        self.draw_line(points=points, group=group)
        self.draw_line(points=points, group=group)
        self.draw_line(points=points, group=group)
        self.draw_line(points=points, group=group)

    def delete_selected(self):
        """Delete all selected objects."""

        self._call_femm('deleteselected')

    def delete_selected_nodes(self):
        """Delete selected nodes."""

        self._call_femm('deleteselectednodes')

    def delete_selected_labels(self):
        """Delete selected labels."""

        self._call_femm('deleteselectedlabels', add_doctype_prefix=True)

    def delete_selected_segments(self):
        """Delete selected segments."""

        self._call_femm('deleteselectedsegments')

    def delete_selected_arc_segments(self):
        """Delete selected arc segments."""

        self._call_femm('deleteselectedarcsegments')

    # Geometry Selection Commands

    def clear_selected(self):
        """Clear all selected nodes, blocks, segments and arc segments."""

        self._call_femm('clearselected', add_doctype_prefix=True)

    def select_segment(self, points=None):
        """Select the line segment closest to (x, y)."""

        x1, y1 = points[0]
        x2, y2 = points[1]
        x_mid = x1 + ((x2 - x1) / 2)
        y_mid = y1 + ((y2 - y1) / 2)
        self._call_femm_with_args('selectsegment', x_mid, y_mid)

    def select_node(self, points=None):
        """Select the node closest to (x,y). Returns the coordinates of the selected node."""

        x, y = points[0]
        self._call_femm_with_args('selectnode', x, y, with_eval=False)

    def select_label(self, points=None):
        """Select the label closet to (x,y). Returns the coordinates of the selected label."""

        x, y = points[0]
        self._call_femm_with_args('selectlabel', x, y)

    def select_arc_segment(self, points=None):
        """Select the arc segment closest to (x, y)."""

        x1, y1 = points[0]
        x2, y2 = points[1]
        x_mid = x1 + ((x2 - x1) / 2)
        y_mid = y1 + ((y2 - y1) / 2)
        self._call_femm_with_args('selectarcsegment', x_mid, y_mid)

    def select_group(self, group):
        """Select the nth group of nodes, segments, arc segments and blocklabels. This
        function will clear all previously selected elements and leave the editmode in
        4 (group)."""

        self._call_femm_with_args('selectgroup', group)

    # Object Labeling Commands

    def set_node_prop(self, prop_name=None, group=None):
        """Set the selected nodes to have the nodal property
        ``prop_name`` and group ``group``."""

        self._call_femm_with_args('setnodeprop', prop_name, group)

    def set_block_prop(self, block_name=None, auto_mesh=False, mesh_size=None, in_circuit=None, mag_direction=False,
                       group=None, turns=None):
        """ Set the selected block labels to have the properties:

            – Block property ``block_name``;
            – ``auto_mesh``: ``False`` = mesher defers to mesh size constraint defined in ``mesh_size``,
              ``True`` = mesher automatically chooses the mesh density;
            – ``mesh_size``: size constraint on the mesh in the block marked by this label;
            – Block is a member of the circuit named ``in_circuit``;
            – The magnetization is directed along an angle in measured in degrees denoted by the
              parameter ``mag_direction``. Alternatively, ``mag_direction`` can be a string containing a
              formula that prescribes the magnetization direction as a function of element position.
              In this formula theta and R denotes the angle in degrees of a line connecting the center
              each element with the origin and the length of this line, respectively; x and y denote
              the x- and y-position of the center of the each element. For axisymmetric problems, r
              and z should be used in place of x and y;
            – A member of group number group;
            – The number of turns associated with this label is denoted by turns."""

        self._call_femm_with_args('setblockprop', block_name, auto_mesh, mesh_size, in_circuit, mag_direction, group,
                                  turns)

    def set_segment_prop(self, prop_name=None, element_size=None, auto_mesh=False, hide=False, group=None):
        """Set the select segments to have:

            – Boundary property ``prop_name``;
            – Local element size along segment no greater than ``element_size``;
            – ``auto_mesh``: ``False`` = mesher defers to the element constraint defined by element_size,
              ``True`` = mesher automatically chooses mesh size along the selected segments;
            – ``hide``: ``False`` = not hidden in post-processor, ``True`` = hidden in post-processor;
            – A member of group number group."""

        self._call_femm_with_args('setsegmentprop', prop_name, element_size, auto_mesh, hide, group)

    def set_arc_segment_prop(self, max_seg_deg=None, prop_name=None, hide=None, group=None):
        """Set the select segments to have:
            – Boundary property ``prop_name``;
            – Local element size along segment no greater than ``element_size``;
            – ``auto_mesh``: ``False`` = mesher defers to the element constraint defined by ``element_size``,
              ``True`` = mesher automatically chooses mesh size along the selected segments;
            – ``hide``: ``False`` = not hidden in post-processor, ``True`` == hidden in post-processor;
            – A member of group number ``group``."""

    def set_group(self, group):
        """Set the group associated of the selected items to ``group``."""

        self._call_femm_with_args('setgroup', group)

    # Problem Commands

    def problem_definition(self, frequency=None, units=None, problem_type=None, precision=None, depth=None,
                           minimum_angle=None, ac_solver=None):
        """Changes the problem definition. Set frequency to the desired frequency in Hertz.
        The units parameter specifies the units used for measuring length in the problem domain.
        Valid "units" entries are "inches", "millimeters", "centimeters", "mils", "meters, and
        "micrometers". Set the parameter problemtype to "planar" for a 2-D planar problem, or to
        "axi" for an axisymmetric problem. The precision parameter dictates the precision required
        by the solver. For example, entering 1E-8 requires the RMS of the residual to be less than 10−8.
        A fifth parameter, representing the depth of the problem in the into-the-page direction for
        2-D planar problems, can also also be specified. A sixth parameter represents the minimum
        angle constraint sent to the mesh generator. A seventh parameter specifies the solver type to
        be used for AC problems."""

        self._call_femm_with_args('probdef', frequency, units, problem_type, precision, depth, minimum_angle, ac_solver)

    def analyze(self, minimized=False):
        """Runs fkern to solve the problem. ``minimized`` determines whether or not to
        minmise the fkern window during solving."""

        self._call_femm_with_args('analyze', '1' if minimized else '0')

    def load_solution(self):
        """Loads and displays the solution corresponding to the current geometry."""

        self._call_femm('loadsolution', add_doctype_prefix=True)

    def save_as(self, filename):
        """Saves the file with name "filename". Note if you use a path you
        must use two backslashes e.g. 'c:\\temp\\myfemmfile.fem'."""

        parsed_filename = filename.replace('/', '\\')
        self._call_femm_with_args('saveas', parsed_filename)

    # Mesh Commands

    def create_mesh(self):
        """Runs triangle to create a mesh. Note that this is not a necessary
        precursor of performing an analysis, as mi analyze() will make sure
        the mesh is up to date before running an analysis. The number of
        elements in the mesh is pushed back onto the lua stack."""

        self._call_femm('createmesh', add_doctype_prefix=True)

    def show_mesh(self):
        """Shows the mesh."""

        self._call_femm('showmesh', add_doctype_prefix=True)

    # Editing Commands

    # Zoom Commands

    def zoom_natural(self):
        """Zooms to a “natural” view with sensible extents."""

        self._call_femm('zoomnatural', add_doctype_prefix=True)

    def zoom_out(self):
        """Zoom out by a factor of 50%."""

        self._call_femm('zoomout', add_doctype_prefix=True)

    def zoom_in(self):
        """Zoom in by a factor of 200%."""

        self._call_femm('zoomin', add_doctype_prefix=True)

    def zoom(self, x1, y1, x2, y2):
        """Set the display area to be from the bottom left corner specified by
        (x1, y1) to the top right corner specified by (x2, y2)."""

        self._call_femm_with_args('zoom', x1, y1, x2, y2)

    # View Commands

    # Object Properties

    def get_material(self, material_name):
        """Fetches the material specified by ``material_name`` from materials library."""

        self._call_femm_with_args('getmaterial', material_name)

    def add_material(self, material_name, material_data=None):
        """Adds a new material with called ``material_name`` with the
        material properties defined in ``material_data``."""

        self._call_femm_with_args(
            'addmaterial',
            material_name,
            material_data.get('mu_x'),
            material_data.get('mu_y'),
            material_data.get('h_c'),
            material_data.get('j'),
            material_data.get('c_duct'),
            material_data.get('lam_d'),
            material_data.get('phi_hmax'),
            material_data.get('lam_fill'),
            material_data.get('lam_type'),
            material_data.get('phi_hx'),
            material_data.get('phi_hy'),
            material_data.get('number_of_strands'),
            material_data.get('wire_diameter'),
        )

    def add_circuit_prop(self, circuit_name=None, current=None, circuit_type=None):
        """Adds a new circuit property with name ``circuit_name`` with a prescribed current. The ``circuit_type``
        parameter is 0 for a parallel-connected circuit and 1 for a series-connected circuit."""

        circuit_type_number = 1 if circuit_type == 'series' else 0
        self._call_femm_with_args('addcircprop', circuit_name, current, circuit_type_number)

    def modify_point_prop(self, point_name=None, prop_number=None, value=None):
        """This function allows for modification of a point property. The point property to be modified
        is specified by "PointName". The next parameter is the number of the property to be set. The last
        number is the value to be applied to the specified property. The various properties that can be
        modified are listed below: 0: PointName, 1: A or 2: J."""

        self._call_femm_with_args('modifypointprop', point_name, prop_number, value)

    def modify_circuit_prop(self, circuit_name=None, prop_number=None, value=None):
        """This function allows for modification of a point property. The point property to be modified
        is specified by "PointName". The next parameter is the number of the property to be set. The last
        number is the value to be applied to the specified property. The various properties that can be
        modified are listed below: 0: CircName, 1: i or 2: CircType."""

        self._call_femm_with_args('modifycircprop', circuit_name, prop_number, value)

    def set_current(self, circuit_name=None, current=None):
        self._call_femm_with_args('setcurrent', circuit_name, current)

    # Miscellaneous

    def make_abc(self, points=None, number_of_shells=None, radius=None, boundary_condition_type=None):
        """Creates a series of circular shells that emulate the impedance of
        an unbounded domain (i.e. an Inprovised Asymptotic Boundary Condition). The n parameter
        contains the number of shells to be used (should be between 1 and 10), R is the radius of the
        solution domain, and (x,y) denotes the center of the solution domain. The bc parameter
        should be specified as 0 for a Dirichlet outer edge or 1 for a Neumann outer edge. If the
        function is called without all the parameters, the function makes up reasonable values for the
        missing parameters."""

        if points is None and number_of_shells is None and radius is None and boundary_condition_type is None:
            self._call_femm('makeABC', add_doctype_prefix=True)
        else:
            x, y = points[0]
            self._call_femm_with_args('makeABC', number_of_shells, radius, x, y, boundary_condition_type)


class PostProcessorAPI(BaseAPI):
    """Postprocessor API."""

    mode_prefix = 'o'

    def line_integral(self, integral_type):
        """Calculate the line integral for the defined contour. Returns typically two (possibly
        complex) values as results. For force and torque results, the 2× results are only relevant
        for problems where ω 6= 0. The 1× results are only relevant for incremental permeability
        AC problems. The 1× results represent the force and torque interactions between the
        steady-state and the incremental AC solution"""

        return self._call_femm_with_args('lineintegral', integral_type)

    def block_integral(self, integral_type):
        """Calculate a block integral for the selected blocks. This function returns one
        (possibly complex) value, e.g.: volume = mo_blockintegral(10)."""

        return self._call_femm_with_args('blockintegral', integral_type)

    def get_point_values(self, x, y):
        """Get the values associated with the point at x,y return values in order"""

        return self._call_femm_with_args('getpointvalues', x, y)

    # Selection Commands.

    def set_edit_mode(self, mode):
        """Sets the mode of the postprocessor to point, contour, or area mode.
        Valid entries for mode are "point", "contour", and "area"."""

        self._call_femm_with_args('seteditmode', mode)

    def select_block(self, points=None):
        """Select the block that contains point (x,y)."""
        import femm
        x, y = points[0]
        self._call_femm_with_args('selectblock', x, y)

    def group_select_block(self, group=None):
        """Selects all of the blocks that are labeled by block labels that are
        members of group n. If no number is specified (i.e. mo_groupselectblock()),
        all blocks are selected."""

        self._call_femm_with_args('groupselectblock', group)

    # View Commands.

    def show_density_plot(self, legend=None, grey_scale=None, lower_bound=None, upper_bound=None, plot_type=None):
        """Shows the flux density plot with options:
            – legend Set to 0 to hide the plot legend or 1 to show the plot legend.
            – gscale Set to 0 for a colour density plot or 1 for a grey scale density plot.
            – upper_B Sets the upper display limit for the density plot.
            – lower_B Sets the lower display limit for the density plot.
            – type Type of density plot to display. Valid entries are "bmag", "breal", and "bimag"
                for magnitude, real component, and imaginary component of flux density (B), respectively;
                "hmag", "hreal", and "himag" for magnitude, real component, and imaginary
                component of field intensity (H); and "jmag", "jreal", and "jimag" for magnitude,
                real component, and imaginary component of current density (J).

        If legend is set to -1 all parameters are ignored and default values are used e.g.:
        mo_showdensityplot(-1)."""

        legend_value = ('1' if grey_scale else '0') if not grey_scale == -1 else -1
        grey_scale_value = '1' if grey_scale else '0'
        self._call_femm_with_args('showdensityplot', legend_value, grey_scale_value, upper_bound, lower_bound,
                                  plot_type)
