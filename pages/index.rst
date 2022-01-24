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


Object oriented patterns for stable APIs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- adding new features does not break function signatures
- individual procedures can be simpler

.. margin::

   `NLopt <https://nlopt.readthedocs.io>`_ is a prime example for a library with interfaces and bindings in many languages.

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

   ABI issues can be ignored in case of static linking.

   However, dynamic linking remains preferred in case of shared libraries which should be loaded into other languages.

- object-oriented APIs can leak symbols into dependent libraries

  - transient dependencies become full dependencies

- changes in the class result in ABI breakage
- vigilance required when linking dynamically

  - very tight version pinning in package managers
  - large rebuild cascades in case of incompatible version changes

- failures happen when compiling or linking incompatible versions


On the C side
^^^^^^^^^^^^^

- ABI issues can be hidden behind opaque pointers
- objects must not be exchanged between libraries
  (each library must work only on its own objects)
- potential data redundancy and needless copying of the data is needed


In C
----


Emulating objects in C
~~~~~~~~~~~~~~~~~~~~~~

- objects are represented as opaque pointers (``void *``)
- typedef-ed pointers for better readability and some type safety
- C11 ``_Generic`` can be used to dispatch at compile time


C compatible wrapping
^^^^^^^^^^^^^^^^^^^^^

- class polymorphic cannot be pointed to by a C-pointer
- use thin wrapper type around Fortran objects

  - metadata can be attacted to the wrapper
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

- deconstructor can either take the pointer by value or by reference

  - by value: C side has to invalidate the (dangling) pointer by assigning ``NULL``
  - by reference: Fortran side can nullify C pointer

.. margin::

   Adding named arguments in the prototype is considered part of the API, changing the argument name is therefore a breaking API change.

.. code-block:: c

   typedef struct foopss_structure* foopss_structure;

   extern foopss_structure
   foopss_new_structure(void);

   extern void
   foopss_delete_structure(foopss_structure* /* struc */);


Bad practice C
^^^^^^^^^^^^^^

- nobody stops our users from accidentally passing the wrong objects (there will be warnings)

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


Beyond ``void *``
~~~~~~~~~~~~~~~~~

- C builds around the concept of pointers to chunks of memory
- difficult to protect from dangling pointers or pointers to wrong objects


Dispatching objects
~~~~~~~~~~~~~~~~~~~

Recovering object information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
   FOOPSS_API_ENTRY foopss_context
   foopss_new_context(void) FOOPSS_API__V_1_0;

   /// Delete calculation context
   FOOPSS_API_ENTRY void
   foopss_delete_context(foopss_context* /* ctx */) FOOPSS_API__V_1_0;

   /// Set custom logger function
   FOOPSS_API_ENTRY void
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
  - many more abandonded projects and tools

- low-level plumbing possible via Python header (Fortran bindings available with `forpy <https://github.com/ylikx/forpy>`_)
- more (stable) option to wrap C from Python than wrapping Fortran from Python

  - most projects need C API anyway


From a C-ish to a Pythonic API
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Layer-on-layer build a framework on top
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Installing software at advanced difficulty
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Summary
-------

What can we do?
~~~~~~~~~~~~~~~

What would we like?
~~~~~~~~~~~~~~~~~~~
