
## License for the Python wrapper
## ==============================

## Copyright (c) 2004 David M. Cooke <cookedm@physics.mcmaster.ca>

## Permission is hereby granted, free of charge, to any person obtaining a copy of
## this software and associated documentation files (the "Software"), to deal in
## the Software without restriction, including without limitation the rights to
## use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
## of the Software, and to permit persons to whom the Software is furnished to do
## so, subject to the following conditions:

## The above copyright notice and this permission notice shall be included in all
## copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
## IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
## FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
## AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
## LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
## OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
## SOFTWARE.

## Modifications by Travis Oliphant and Enthought, Inc.  for inclusion in SciPy

from numpy import zeros, float64, array, int32
import _lbfgsb
import optimize
from numpy.compat import asbytes

__all__ = ['fmin_l_bfgs_b']


approx_fprime = optimize.approx_fprime

def fmin_l_bfgs_b(func, x0, fprime=None, args=(),
                  approx_grad=0,
                  bounds=None, m=10, factr=1e7, pgtol=1e-5,
                  epsilon=1e-8,
                  iprint=-1, maxfun=15000, disp=None):
    """
    Minimize a function func using the L-BFGS-B algorithm.

    Parameters
    ----------
    func : callable f(x, *args)
        Function to minimise.
    x0 : ndarray
        Initial guess.
    fprime : callable fprime(x, *args)
        The gradient of `func`.  If None, then `func` returns the function
        value and the gradient (``f, g = func(x, *args)``), unless
        `approx_grad` is True in which case `func` returns only ``f``.
    args : tuple
        Arguments to pass to `func` and `fprime`.
    approx_grad : bool
        Whether to approximate the gradient numerically (in which case
        `func` returns only the function value).
    bounds : list
        ``(min, max)`` pairs for each element in ``x``, defining
        the bounds on that parameter. Use None for one of ``min`` or
        ``max`` when there is no bound in that direction.
    m : int
        The maximum number of variable metric corrections
        used to define the limited memory matrix. (The limited memory BFGS
        method does not store the full hessian but uses this many terms in an
        approximation to it.)
    factr : float
        The iteration stops when
        ``(f^k - f^{k+1})/max{|f^k|,|f^{k+1}|,1} <= factr * eps``,
        where ``eps`` is the machine precision, which is automatically
        generated by the code. Typical values for `factr` are: 1e12 for
        low accuracy; 1e7 for moderate accuracy; 10.0 for extremely
        high accuracy.
    pgtol : float
        The iteration will stop when
        ``max{|proj g_i | i = 1, ..., n} <= pgtol``
        where ``pg_i`` is the i-th component of the projected gradient.
    epsilon : float
        Step size used when `approx_grad` is True, for numerically
        calculating the gradient
    iprint : int
        Controls the frequency of output. ``iprint < 0`` means no output.
    disp : int, optional
        If zero, then no output.  If positive number, then this over-rides
        `iprint`.
    maxfun : int
        Maximum number of function evaluations.

    Returns
    -------
    x : ndarray
        Estimated position of the minimum.
    f : float
        Value of `func` at the minimum.
    d : dict
        Information dictionary.

        * d['warnflag'] is
          - 0 if converged,
          - 1 if too many function evaluations,
          - 2 if stopped for another reason, given in d['task']

        * d['grad'] is the gradient at the minimum (should be 0 ish)
        * d['funcalls'] is the number of function calls made.

    Notes
    -----
    License of L-BFGS-B (Fortran code):

    The version included here (in fortran code) is 2.1 (released in 1997).
    It was written by Ciyou Zhu, Richard Byrd, and Jorge Nocedal
    <nocedal@ece.nwu.edu>. It carries the following condition for use:

    This software is freely available, but we expect that all publications
    describing work using this software , or all commercial products using it,
    quote at least one of the references given below.

    References
    ----------
    * R. H. Byrd, P. Lu and J. Nocedal. A Limited Memory Algorithm for Bound
      Constrained Optimization, (1995), SIAM Journal on Scientific and
      Statistical Computing , 16, 5, pp. 1190-1208.
    * C. Zhu, R. H. Byrd and J. Nocedal. L-BFGS-B: Algorithm 778: L-BFGS-B,
      FORTRAN routines for large scale bound constrained optimization (1997),
      ACM Transactions on Mathematical Software, Vol 23, Num. 4, pp. 550 - 560.

    """
    n = len(x0)

    if bounds is None:
        bounds = [(None,None)] * n
    if len(bounds) != n:
        raise ValueError('length of x0 != length of bounds')

    if disp is not None:
        if disp == 0:
            iprint = -1
        else:
            iprint = disp

    if approx_grad:
        def func_and_grad(x):
            f = func(x, *args)
            g = approx_fprime(x, func, epsilon, *args)
            return f, g
    elif fprime is None:
        def func_and_grad(x):
            f, g = func(x, *args)
            return f, g
    else:
        def func_and_grad(x):
            f = func(x, *args)
            g = fprime(x, *args)
            return f, g

    nbd = zeros((n,), int32)
    low_bnd = zeros((n,), float64)
    upper_bnd = zeros((n,), float64)
    bounds_map = {(None, None): 0,
              (1, None) : 1,
              (1, 1) : 2,
              (None, 1) : 3}
    for i in range(0, n):
        l,u = bounds[i]
        if l is not None:
            low_bnd[i] = l
            l = 1
        if u is not None:
            upper_bnd[i] = u
            u = 1
        nbd[i] = bounds_map[l, u]

    x = array(x0, float64)
    f = array(0.0, float64)
    g = zeros((n,), float64)
    wa = zeros((2*m*n+4*n + 12*m**2 + 12*m,), float64)
    iwa = zeros((3*n,), int32)
    task = zeros(1, 'S60')
    csave = zeros(1,'S60')
    lsave = zeros((4,), int32)
    isave = zeros((44,), int32)
    dsave = zeros((29,), float64)

    task[:] = 'START'

    n_function_evals = 0
    while 1:
#        x, f, g, wa, iwa, task, csave, lsave, isave, dsave = \
        _lbfgsb.setulb(m, x, low_bnd, upper_bnd, nbd, f, g, factr,
                       pgtol, wa, iwa, task, iprint, csave, lsave,
                       isave, dsave)
        task_str = task.tostring()
        if task_str.startswith(asbytes('FG')):
            # minimization routine wants f and g at the current x
            n_function_evals += 1
            # Overwrite f and g:
            f, g = func_and_grad(x)
        elif task_str.startswith(asbytes('NEW_X')):
            # new iteration
            if n_function_evals > maxfun:
                task[:] = 'STOP: TOTAL NO. of f AND g EVALUATIONS EXCEEDS LIMIT'
        else:
            break

    task_str = task.tostring().strip(asbytes('\x00')).strip()
    if task_str.startswith(asbytes('CONV')):
        warnflag = 0
    elif n_function_evals > maxfun:
        warnflag = 1
    else:
        warnflag = 2


    d = {'grad' : g,
         'task' : task_str,
         'funcalls' : n_function_evals,
         'warnflag' : warnflag
        }
    return x, f, d

if __name__ == '__main__':
    def func(x):
        f = 0.25*(x[0]-1)**2
        for i in range(1, x.shape[0]):
            f += (x[i] - x[i-1]**2)**2
        f *= 4
        return f
    def grad(x):
        g = zeros(x.shape, float64)
        t1 = x[1] - x[0]**2
        g[0] = 2*(x[0]-1) - 16*x[0]*t1
        for i in range(1, g.shape[0]-1):
            t2 = t1
            t1 = x[i+1] - x[i]**2
            g[i] = 8*t2 - 16*x[i]*t1
        g[-1] = 8*t1
        return g

    factr = 1e7
    pgtol = 1e-5

    n=25
    m=10

    bounds = [(None,None)] * n
    for i in range(0, n, 2):
        bounds[i] = (1.0, 100)
    for i in range(1, n, 2):
        bounds[i] = (-100, 100)

    x0 = zeros((n,), float64)
    x0[:] = 3

    x, f, d = fmin_l_bfgs_b(func, x0, fprime=grad, m=m,
                            factr=factr, pgtol=pgtol)
    print x
    print f
    print d
    x, f, d = fmin_l_bfgs_b(func, x0, approx_grad=1,
                            m=m, factr=factr, pgtol=pgtol)
    print x
    print f
    print d
