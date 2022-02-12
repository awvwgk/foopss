:sd_hide_title: true

Using objects across language boundaries
========================================

.. card::
   :class-header: sd-text-white sd-fs-3 sd-font-weight-bold sd-border-0 sd-text-center
   :class-card: sd-border-0 sd-bg-danger sd-px-3 sd-py-1 sd-rounded-3
   :class-body: sd-text-white sd-fs-5 sd-border-0 sd-text-center
   :shadow: none

   Using objects across language boundaries

   ^^^

   Exploring the limits of language intercompatibility and consistent API design

.. article-info::
   :avatar: _static/catcher.png
   :avatar-link: https://github.com/awvwgk
   :avatar-outline: muted
   :author: Sebastian Ehlert
   :date: 17th February 2022
   :class-container: sd-p-2 sd-rounded-3


Motivation
----------

- scientific libraries are not a closed ecosystem
- need for (easy) interfacing with other projects and robust dependency management
- more flexibility when interfacing via APIs rather than IO
- we already have enough incompatible / undocumented ASCII file formats for data exchange

.. image:: _static/c-intercompatibility.png
   :align: center
   :width: 50%

Language intercompatibility
~~~~~~~~~~~~~~~~~~~~~~~~~~~

- not all libraries share the same programming language
- C is the *lingua franca* for communication between languages
- *bind(c)* with *iso_c_binding* for definition in Fortran

  - allows manipulation of C data types in Fortran
  - Fortran language constructs are easily accessible
    (*e.g.*, using modules, pointer, class(*), etc.)

- *ISO_Fortran_binding.h* for definition in C

  - allows manipulation of Fortran data types in C
  - provides a stable API for C, but does not guarantee ABI compatibility

.. margin::

   Join the discussion on a proposal for enabling ABI compatibility at `fortran_proposals#247 <https://github.com/j3-fortran/fortran_proposals/issues/247>`_.

.. grid:: 2
   :gutter: 0

   .. grid-item-card::
      :class-card: sd-border-0 sd-p-0
      :shadow: none

      .. code-block:: c
         :caption: ``CFI_dim_t`` in Intel Fortran / NAG Fortran

         typedef struct
         {
             CFI_index_t extent;
             CFI_index_t sm;
             CFI_index_t lower_bound;
         } CFI_dim_t;

   .. grid-item-card::
      :class-card: sd-border-0 sd-p-0
      :shadow: none

      .. code-block:: c
         :caption: ``CFI_dim_t`` in GCC Fortran / LLVM Flang

         typedef struct
         {
             CFI_index_t lower_bound;
             CFI_index_t extent;
             CFI_index_t sm;
         } CFI_dim_t;

- we can only see symbols and pointers from other languages
- generic interfaces, overloaded operators, ... are not available
  (compile-time dispatch requires a compiler)
- API bindings are not necessarily part of the upstream project
  (relying on semantic versioning conventions)


Object-oriented patterns for stable APIs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- adding new features does not break function signatures
- individual procedures can be simpler

.. margin::

   `NLopt <https://nlopt.readthedocs.io>`_ is a prime example of a library with interfaces and bindings in many languages.

   It can be used from C, C++, Fortran, Matlab, Octave, Python, Guile, Julia,
   R, Lua, OCaml, or Rust.

.. grid:: 2
   :gutter: 0

   .. grid-item-card::
      :class-card: sd-border-0 sd-p-0
      :shadow: none

      .. code-block:: c
         :caption: Procedural API in NLopt 1.x

         nlopt_result
         nlopt_minimize(
           nlopt_algorithm algorithm,
           int n,
           nlopt_func f,
           void* f_data,
           const double* lb,
           const double* ub,
           double* x,
           double* minf,
           double minf_max,
           double ftol_rel,
           double ftol_abs,
           double xtol_rel,
           const double* xtol_abs,
           int maxeval,
           double maxtime
         );

   .. grid-item-card::
      :class-card: sd-border-0 sd-p-0
      :shadow: none

      .. code-block:: c
         :caption: Object-oriented API in NLopt 2.x

         typedef struct nlopt_opt_s* nlopt_opt;

         nlopt_opt
         nlopt_create(nlopt_algorithm algorithm,
                      unsigned n);

         nlopt_result
         nlopt_set_min_objective(nlopt_opt opt,
                                 nlopt_func f,
                                 void* f_data);

         nlopt_result
         nlopt_optimize(nlopt_opt opt,
                        double* x,
                        double* opt_f);

         void
         nlopt_destroy(nlopt_opt opt);


ABI compatibility nightmares
~~~~~~~~~~~~~~~~~~~~~~~~~~~~


On the Fortran side
^^^^^^^^^^^^^^^^^^^

.. margin::

   ABI issues can be ignored in the case of static linking.

   However, dynamic linking remains preferred in the case of shared libraries which should be loaded into other languages.

- object-oriented APIs can leak symbols into dependent libraries

  - transient dependencies become full dependencies

- no ABI conventions, easy to break ABI with API-compatible changes

  - changes in class definition result in ABI breakage
  - renaming functions in generic interfaces breaks ABI
  - adding (optional) arguments to procedures is breaking the ABI
  - so does changing the compiler
  - ...

- vigilance required when linking dynamically

  - very tight version pinning in package managers
  - large rebuild cascades in case of incompatible version changes

- failures happen when compiling or linking incompatible versions


On the C side
^^^^^^^^^^^^^

- most stable ABI available to build on
- ABI issues can be hidden behind opaque pointers
- objects must not be exchanged between libraries

  - each library must work only on its own objects
  - do not blindly cast typdef-ed pointers (generally a bad idea)

- potential data redundancy and needless copying of the data is needed
  (if objects own their data)


In C
----



Emulating objects in C
~~~~~~~~~~~~~~~~~~~~~~

- objects are represented as opaque pointers (``void *``)
- typedef-ed pointers for better readability and some type safety
- C11 ``_Generic`` can be used to dispatch at compile time


What makes a classy object
^^^^^^^^^^^^^^^^^^^^^^^^^^

- Fortran standard does not specify implementation of class objects
- simple design model are C structs with overlapping fields and procedure pointers

.. margin::

   If you need a quick refresher in C try the `cdecl translator <https://www.cdecl.org/>`_.

.. tab-set::

   .. tab-item:: Fortran

      .. code-block:: fortran
         :caption: Crude (and possibly incorrect) Fortran class model

         type :: a_cls
           character(len=:), allocatable :: label
           integer :: ndim = 0
           real(wp), allocatable :: bounds(:)
         contains
           procedure :: set_bounds
           procedure :: get_bounds
         end type

         type, extends(a_cls) :: b_cls
         ! character(len=:), allocatable :: label
         ! integer :: ndim = 0
         ! real(wp), allocatable :: bounds(:)
         ! procedure, pointer :: set_bounds
         ! procedure, pointer :: get_bounds
           real(wp) :: scale = 1.0_wp
         contains
           procedure :: set_scale
         end type

   .. tab-item:: C

      .. code-block:: c
         :caption: Emulating class objects in C

         struct a_cls {
           char* label;
           int ndim;
           double* bounds;

           void (* set_bounds)(struct a_cls*, const double*);
           void (* get_bounds)(struct a_cls*, double*);
         };

         struct b_cls {
           char* label;
           int ndim;
           double* bounds;
           void (* set_bounds)(struct a_cls*, const double*);
           void (* get_bounds)(struct a_cls*, double*);
           double scale;

           void (* set_scale)(struct b_cls*, double);
         };


- C-ish way of polymorphism builds on memory layout and casting pointers

  - procedure pointers provide a way to dispatch at runtime
  - casting around pointers probably worse than ``select type`` in Fortran

.. important::

   Objects do not have to be transparent to be usable


C compatible wrapping
^^^^^^^^^^^^^^^^^^^^^

- class polymorphic cannot be pointed to by a C-pointer
- use thin wrapper type around Fortran objects

  - metadata can be attached to the wrapper
  - can store class polymorphic objects and preserve their state
  - allocation status of components is available

.. margin::

   Setup on the Fortran side is quite verbose and very explicit about every step.

   This could be templated with a preprocessor like ``fypp``.

.. code-block:: fortran

   module foopss_api
     use, intrinsic :: iso_c_binding, only : c_ptr, c_loc, &
       & c_f_pointer, c_associated, c_null_ptr
     use foopss_structure, only : structure_type
     implicit none

     type :: vp_structure
       type(structure_type) :: raw
     end type vp_structure

   contains

     function foopss_new_structure() result(new) bind(c)
       type(c_ptr) :: new
       type(vp_structure), pointer :: struc

       allocate(struc)
       new = c_loc(struc)
     end function foopss_new_structure

     subroutine foopss_delete_structure(ptr) bind(c)
       type(c_ptr), intent(inout) :: ptr
       type(vp_structure), pointer :: struc

       if (c_associated(ptr)) then
         call c_f_pointer(ptr, struc)
         deallocate(struc)
         ptr = c_null_ptr  ! ensure repeated calls to delete become no-ops
       end if
     end subroutine foopss_delete_structure
   end module foopss_api

.. margin::

   Automatic wrapper tools might impose preferences.

- deconstructor can either take the pointer by value or by reference

  - by value: C side has to invalidate the (dangling) pointer by assigning ``NULL``
  - by reference: Fortran side can nullify C pointer

.. code-block:: c

   typedef struct foopss_structure* foopss_structure;

   extern foopss_structure
   foopss_new_structure(void);

   extern void
   foopss_delete_structure(foopss_structure* /* struc */);


Bad practice C
^^^^^^^^^^^^^^

- nobody stops our users from accidentally passing the wrong objects (there will be warnings)

.. margin::

   Usage of ``-Werror`` only gets you so far.

   New compiler versions can introduce new warnings which negate the benefits of always failing on warnings.

   Also, Fortran compilers can produce lots of spurious warnings.

.. code-block:: text

   app/main.c:16:29: warning: initialization of ‘foopss_structure’ {aka ‘struct foopss_structure *’} from incompatible pointer type ‘foopss_context’ {aka ‘struct foopss_context *’} [-Wincompatible-pointer-types]
      16 |    foopss_structure struc = ctx;
         |                             ^~~

.. code-block:: text

   app/main.c:17:28: warning: passing argument 1 of ‘foopss_delete_structure’ from incompatible pointer type [-Wincompatible-pointer-types]
      17 |    foopss_delete_structure(&ctx);
         |                            ^~~~
         |                            |
         |                            struct foopss_context **
   In file included from app/main.c:4:
   ./include/foopss.h:28:25: note: expected ‘struct foopss_structure **’ but argument is of type ‘struct foopss_context **’
      28 | foopss_delete_structure(foopss_structure*);
         |                         ^~~~~~~~~~~~~~~~~

- even worse: the binding language to C cannot distinguish between different typdef-ed objects (*e.g.* Python's ctypes)


Compile time dispatch in C
^^^^^^^^^^^^^^^^^^^^^^^^^^

- ``_Generic`` allows us to dispatch typedef-ed pointers at compile time

  - usually defined as a type generic macro
  - difficult to use outside of C

.. code-block:: c
   :caption: C11 equivalent to the Fortran interface

   _Generic((obj),
            foopss_context: foopss_delete_context,
            foopss_structure: foopss_delete_structure,
            foopss_calculator: foopss_delete_calculator,
            foopss_result: foopss_delete_result,
           )(&obj)


Handling errors
^^^^^^^^^^^^^^^

.. margin::

   Projects like libcurl are most strict about error handling and reporting.
   Even out-of-memory errors are handled gracefully and reported.

- well-behaving libraries must never stop under any circumstances
- errors should be propagated up, the caller must be able to handle them gracefully
- runtime must not be left in an undefined state (do not throw exceptions through foreign languages)
- rich error reporting is preferable over plain error codes

  - can include error message and context more easily
  - implemented via opaque pointer or C-compatible struct
  - API for both querying (and creating) error context


.. code-block:: c
   :caption: Minimalistic error handle API

   /// Error instance
   typedef struct foopss_error* foopss_error;

   /// Create new error handle
   extern foopss_error
   foopss_new_error(void);

   /// Delete an error handle
   extern void
   foopss_delete_error(foopss_error* /* error */);

   /// Check error handle status
   extern int
   foopss_check_error(foopss_error /* error */);

   /// Get error message from error handle
   extern void
   foopss_get_error(foopss_error /* error */,
                    char* /* buffer */,
                    const int* /* buffersize */);


Callback mechanism
^^^^^^^^^^^^^^^^^^

- IO features should be implemented in native language (logging, error reporting, ...)
- hooks deep inside algorithm need to communicate or exchange data

.. code-block:: fortran
   :caption: Fortran implementation of the callback mechanism

   module foopss_api
     use, intrinsic :: iso_c_binding
     use foopss_context_type, only : context_type, context_logger
     implicit none

     !> Void pointer to manage calculation context
     type :: vp_context
       !> Actual payload
       type(context_type) :: raw
     end type vp_context

     abstract interface
       !> Interface for callbacks used in custom logger
       subroutine callback(msg, len, udata)
         import :: c_char, c_ptr, c_int
         !> Message payload to be displayed
         character(kind=c_char) :: msg(*)
         !> Length of the message
         integer(c_int) :: len
         !> Data pointer for callback
         type(c_ptr), value :: udata
       end subroutine callback
     end interface

     !> Custom logger for calculation context to display messages
     type, extends(context_logger) :: callback_logger
       !> Data pointer for callback
       type(c_ptr) :: udata = c_null_ptr
       !> Custom callback function to display messages
       procedure(callback), pointer, nopass :: callback => null()
     contains
       !> Entry point for context instance to log message
       procedure :: message
     end type callback_logger

   contains

     ! ...

     !> Create a new custom logger for the calculation context
     subroutine foopss_set_context_logger(vctx, vproc, vdata) bind(c)
       type(c_ptr), value :: vctx
       type(vp_context), pointer :: ctx
       type(c_funptr), value :: vproc
       procedure(callback), pointer :: fptr
       type(c_ptr), value :: vdata

       if (.not.c_associated(vctx)) return
       call c_f_pointer(vctx, ctx)

       if (allocated(ctx%raw%io)) deallocate(ctx%raw%io)
       if (c_associated(vproc)) then
         call c_f_procpointer(vproc, fptr)
         ctx%raw%io = new_callback_logger(fptr, vdata)
       end if
     end subroutine set_context_logger_api

     !> Create a new custom logger
     function new_callback_logger(fptr, udata) result(self)
       !> Actual function used to display messages
       procedure(callback) :: fptr
       !> Data pointer used inside the callback function
       type(c_ptr), intent(in) :: udata
       !> New instance of the custom logger
       type(callback_logger) :: self

       self%callback => fptr
       self%udata = udata
     end function new_callback_logger

     !> Entry point for context type logger, transfers message from context to callback
     subroutine message(self, msg)
       !> Instance of the custom logger with the actual logger callback function
       class(callback_logger), intent(inout) :: self
       !> Message payload from the calculation context
       character(len=*), intent(in) :: msg
       character(kind=c_char) :: charptr(len(msg))

       charptr = transfer(msg, charptr)
       call self%callback(charptr, size(charptr, kind=c_int), self%udata)
     end subroutine message
   end module foopss_api

- cannot directly use C procedure pointer due to conversion from Fortran to C string
- call back needs to be wrapped twice in Fortran for robustness
- string need not be ``NUL`` terminated when passing length as an argument

.. code-block:: c
   :caption: Exported C API for the callback mechanism

   /// Context manager for the library usage
   typedef struct _foopss_context* foopss_context;

   /// Define callback function for use in custom logger
   typedef void (*foopss_logger_callback)(char*, int, void*);

   // ...

   /// Set custom logger function
   void
   foopss_set_context_logger(foopss_context /* ctx */,
                             foopss_logger_callback /* callback */,
                             void* /* userdata */);

   // ...

   /// Example for a callback function
   void
   example_callback(char* msg, int len, void* udata) {
     /* print len chars from msg, since it need not NUL terminated */
     printf("[callback] %.*s\n", msg, len);
   }

- can use callback mechanism to implement new classes via API
- user data can be carried around via opaque pointer


Practical tips
~~~~~~~~~~~~~~

- C macros can help a lot with reducing repetitive boilerplate in the C header

.. margin::

   Checkout your systems OpenCL headers for inspiration

.. code-block:: c
   :caption: Possible macros for C API header

   #ifdef __cplusplus
   #  define FOOPSS_API_ENTRY extern "C"
   #else
   #  define FOOPSS_API_ENTRY extern
   #endif

   /* for attributes or DLL export stuff on Windows */
   #define FOOPSS_API_CALL

   /* Labels to keep track of version introducing API */
   #define FOOPSS_API__V_1_0
   #define FOOPSS_API__V_1_0_DEPRECATED
   #define FOOPSS_API__V_1_1
   #define FOOPSS_API__V_1_2

   // ...

   /// Context manager for the library usage
   typedef struct foopss_context* foopss_context;

   /// Define callback function for use in custom logger
   typedef void (*foopss_logger_callback)(char*, void*) FOOPSS_API__V_1_2;

   /// Create new calculation environment object
   FOOPSS_API_ENTRY foopss_context FOOPSS_API_CALL
   foopss_new_context(void) FOOPSS_API__V_1_0;

   /// Delete calculation context
   FOOPSS_API_ENTRY void FOOPSS_API_CALL
   foopss_delete_context(foopss_context* /* ctx */) FOOPSS_API__V_1_0;

   /// Set custom logger function
   FOOPSS_API_ENTRY void FOOPSS_API_CALL
   foopss_set_context_logger(foopss_context /* ctx */,
                             foopss_logger_callback /* callback */,
                             void* /* userdata */) FOOPSS_API__V_1_2;

- users can statically check whether an API feature is available by checking whether a macro is defined


In Python
---------

Directly from Fortran to Python?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- several automatic wrapper generators are available

  - `numpy.f2py <https://numpy.org/doc/stable/f2py/usage.html>`_: is mainly targeting legacy Fortran code (objects are not supported)
  - `f90wrap <https://github.com/jameskermode/f90wrap>`_: is a wrapper generator for Fortran 90
  - `gfort2py <https://github.com/rjfarmer/gfort2py>`_: GFortran module file based wrapper generator
  - many more abandoned projects and tools

- low-level plumbing possible via Python header (Fortran bindings available with `forpy <https://github.com/ylikx/forpy>`_)
- more (stable) option to wrap C from Python than wrapping Fortran from Python

  - most projects need/want C API anyway


Python ctypes
^^^^^^^^^^^^^

- `ctypes <https://docs.python.org/3/library/ctypes.html>`_: low-level Python interface to C
- dynamic loading of shared libraries via dlopen

  - requires definition of signatures in Python (duplication)
  - library name is platform dependent and logic must be handled in Python
  - no type safety for opaque pointers (all declared as ``c_void_p``)

- no automatic deconstruction available for objects

  - manual deconstruction best wrapped by a context manager
    (``__enter__`` and ``__exit__`` hooks)

- `numpy.ctypeslib <https://numpy.org/doc/stable/reference/routines.ctypeslib.html>`_ provides convenience functions

  - numpy objects pass through API without additional effort (``numpy.ctypeslib.as_array``)

- no compiled dependencies in your Python package
- no additional dependencies in Python


.. code-block:: python
   :caption: Example usage of ctypes

   import ctypes as ct
   import numpy as np
   import os.path as op

   # layout when installed in same $PREFIX is usually (not true on Windows)
   # $PREFIX/lib/libfoopss.*
   # $PREFIX/lib/python3.x/site-packages/foopss.py
   _foopss = np.ctypeslib.load_library('libfoopss', op.dirname(__file__).parent.parent)

   # Can only declare opaque handle, but not typedef it
   _foopss.foopss_new_context.restype = ct.c_void_p

   # For ctypes passing the void* by value might be preferable
   _foopss.foopss_delete_context.argtypes = [ct.POINTER(ct.c_void_p)]

   # Prototype for callback function, pass-through PyObject
   logger_callback = ct.CFUNCTYPE(None, ct.c_char_p, ct.c_int, ct.py_object)

   # Some type safety for callback signatures, user-data
   _foopss.foopss_set_context_logger.argtypes = [ct.c_void_p, logger_callback, ct.py_object]
   _foopss.foopss_set_context_logger.restype = None

   # ...


Foreign function interface
^^^^^^^^^^^^^^^^^^^^^^^^^^

- `cffi <https://cffi.readthedocs.org>`_ module allows different access modes

  - in-line ABI level mode similar to Python ctypes (but allows typdefs)
  - out-of-line API mode most useful for creating standalone extension modules
  - runtime requirement on cffi module

- C parser is very limited, manual preprocessing of headers required

  - preprocessed header can produce complete extension module source code
  - low effort solution for creating the actual glue code and defining the extension module


.. margin::

   The `pkgconfig <https://github.com/matze/pkgconfig>`_ module can produce cffi compatible ``kwargs`` and ``cflags`` directly from a pc file

.. code-block:: python
   :caption: ffibuilder.py

   import os
   import subprocess
   import cffi

   library = "foopss"
   include_header = f'#include "{library}.h"'
   prefix_var = library.upper() + "_PREFIX"
   if prefix_var not in os.environ:
       prefix_var = "CONDA_PREFIX"
   module_name = f"{library}._lib{library}"

   # Detection logic must provide:
   # - dict with libraries to link as well as include, library and runtime directories
   # - additional flags for C-compiler to find headers
   kwargs = dict(libraries=[library])
   cflags = []
   if prefix_var in os.environ:
       prefix = os.environ[prefix_var]
       kwargs.update(
           include_dirs=[os.path.join(prefix, "include")],
           library_dirs=[os.path.join(prefix, "lib")],
           runtime_library_dirs=[os.path.join(prefix, "lib")],
       )
       cflags.append("-I" + os.path.join(prefix, "include"))

   # pycparser cannot handle preprocessor gracefully
   # - manual preprocessing required via C compiler or cpp required
   cc = os.environ["CC"] if "CC" in os.environ else "cc"
   p = subprocess.Popen(
       [cc, *cflags, "-E", "-"],
       stdin=subprocess.PIPE,
       stdout=subprocess.PIPE,
       stderr=subprocess.PIPE,
   )
   out, err = p.communicate(include_header.encode())

   # Definitions of API from header
   cdefs = out.decode()

   # Final construction extension module source
   # - distutils/setuptools handle this automatically
   # - manual run has to write the C source
   ffibuilder = cffi.FFI()
   ffibuilder.set_source(module_name, include_header, **kwargs)
   ffibuilder.cdef(cdefs)
   if __name__ == "__main__":
      ffibuilder.distutils_extension(".")


From errors to exceptions
^^^^^^^^^^^^^^^^^^^^^^^^^

- ctypes or cffi wrapped C-libraries still look and feel like C when used in Python
- create convenience wrappers for creating (and deleting) objects

  - cffi can setup proper a garbage collection routine for any object

- use a decorator for transforming library errors to exception

.. margin::

   With a consistent design of the API, *i.e.* always passing the error handle as first element, wrapping of library functions becomes much easier

.. code-block:: python
   :caption: foopss/library.py

   import functools
   from ._libfoopss import ffi, lib

   def _delete_error(err):
       """Delete an error handle object"""
       ptr = ffi.new("foopss_error *")
       ptr[0] = err
       lib.foopss_delete_error(ptr)


   def new_error():
       """Create new error handle object"""
       return ffi.gc(lib.foopss_new_error(), _delete_error)


   def error_check(func):
       """Handle errors for library functions that require an error handle"""

       @functools.wraps(func)
       def handle_error(*args, **kwargs):
           """Run function and than compare context"""
           _err = new_error()
           value = func(_err, *args, **kwargs)
           if lib.foopss_check_error(_err):
               _message = ffi.new("char[]", 512)
               lib.foopss_get_error(_err, _message, ffi.NULL)
               raise RuntimeError(ffi.string(_message).decode())
           return value

       return handle_error


From a C-ish to a Pythonic API
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- thin wrappers still retain C-ish handling for objects

  - okay for procedural APIs
  - different expectations between object-oriented C and Python

- another layer needed to make Pythonic classes and objects

.. code-block:: python

   import numpy as np

   from . import library


   class Structure:
       """
       Represents a wrapped structure object in foopss.

       Example
       -------
       >>> from foopss.interface import Structure
       >>> import numpy as np
       >>> mol = Structure(
       ...     positions=np.array([
       ...         [+0.00000000000000, +0.00000000000000, -0.73578586109551],
       ...         [+1.44183152868459, +0.00000000000000, +0.36789293054775],
       ...         [-1.44183152868459, +0.00000000000000, +0.36789293054775],
       ...     ]),
       ...     numbers = np.array([8, 1, 1]),
       ... )
       ...
       """

       _mol = library.ffi.NULL

       def __init__(self, numbers, positions, lattice, periodic):
           _numbers = np.ascontiguousarray(numbers, dtype="i4")
           _positions = np.ascontiguousarray(positions, dtype="float")
           _lattice = np.ascontiguousarray(lattice, dtype="float")
           _periodic = np.ascontiguousarray(periodic, dtype="bool")

           self._mol = library.new_structure(
               self._natoms,
               _cast("int*", _numbers)
               _cast("double*", _positions),
               _cast("double*", _lattice),
               _cast("bool*", _periodic),
           )

   def _cast(ctype, array):
       """Cast a numpy array to a FFI pointer"""
       return (
           library.ffi.NULL
           if array is None
           else library.ffi.cast(ctype, array.ctypes.data)
       )


Installing software at advanced difficulty
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- language-specific build systems (setuptools, fpm, ...) have shortcomings for interlanguage bindings

  - cross-compilation for bindings or extensions usually poorly supported (if at all)
  - particularities of foreign language must be accounted for in the build system
  - distribution model of language might be not flexible enough (Python wheels, ...)

- start with general-purpose build system (meson, cmake, ...)

  - clean support for handling multiple languages
  - possibility to split build into multiple projects (useful for distributions)


Summary
-------

What can we do?
~~~~~~~~~~~~~~~

- opaque pointers and callbacks allow emulating Fortran classes


What would we like?
~~~~~~~~~~~~~~~~~~~

- mechanism to dispatch or recover type information of opaque pointers

  - runtime type checking, *e.g.* recover mixed up arguments
  - dispatching in generic routines, *e.g.* deconstruction


Further reading
~~~~~~~~~~~~~~~

- `Crafting Interpreters <https://craftinginterpreters.com/>`_ by Robert Nystrom


Discussion
----------

.. raw:: html

   <script
      type="text/javascript"
      src="https://utteranc.es/client.js"
      async="async"
      repo="awvwgk/foopss"
      issue-number="2"
      theme="github-light"
      crossorigin="anonymous"
   />
