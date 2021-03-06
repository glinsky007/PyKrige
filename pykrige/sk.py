__doc__ = """Code by Michael Glinsky
glinsky@qitech.biz

Dependencies:
    numpy
    scipy
    matplotlib
    Cython

Classes:
    SimpleKriging: Convenience class for easy access to 2D Simple Kriging.

References:
    P.K. Kitanidis, Introduction to Geostatistcs: Applications in Hydrogeology,
    (Cambridge University Press, 1997) 272 p.

Copyright (c) 2015 Benjamin S. Murphy
"""

import numpy as np
import scipy.linalg
from scipy.spatial.distance import cdist
import matplotlib.pyplot as plt
import variogram_models
import core


class SimpleKriging:
    """class SimpleKriging
    Convenience class for easy access to 2D simple Kriging

    Dependencies:
        numpy
        scipy
        matplotlib

    Inputs:
        X (array-like): X-coordinates of data points.
        Y (array-like): Y-coordinates of data points.
        Z (array-like): Values at data points.

        variogram_model (string, optional): Specified which variogram model to use;
            may be one of the following: linear, power, gaussian, spherical,
            exponential. Default is linear variogram model. To utilize as custom variogram
            model, specify 'custom'; you must also provide variogram_parameters and
            variogram_function.
        variogram_parameters (list, optional): Parameters that define the
            specified variogram model. If not provided, parameters will be automatically
            calculated such that the root-mean-square error for the fit variogram
            function is minimized.
                linear - [slope, nugget] (only for variogram analysis)
                power - [scale, exponent, nugget] (only for variogram analysis)
                gaussian - [sill, range, nugget]
                spherical - [sill, range, nugget]
                exponential - [sill, range, nugget]
            For a custom variogram model, the parameters are required, as custom variogram
            models currently will not automatically be fit to the data. The code does not
            check that the provided list contains the appropriate number of parameters for
            the custom variogram model, so an incorrect parameter list in such a case will
            probably trigger an esoteric exception someplace deep in the code.
        variogram_function (callable, optional): A callable function that must be provided
            if variogram_model is specified as 'custom'. The function must take only two
            arguments: first, a list of parameters for the variogram model; second, the
            distances at which to calculate the variogram model. The list provided in
            variogram_parameters will be passed to the function as the first argument.
        nlags (int, optional): Number of averaging bins for the semivariogram.
            Default is 6.
        weight (int, optional): If weight=1, semivariance at smaller lags
            is weighted more heavily when automatically calculating variogram model.  The
            weight is 1/lag.  If weight=2, then fit is weighted by the error in the estimate 
            of the semivariogram.  If weight=3, the the old scheme of weighting by (n_bins-bin_number)
            If weight=0, no weights will be applied.  Default is 0.
        anisotropy_scaling (float, optional): Scalar stretching value to take
            into account anisotropy. Default is 1 (effectively no stretching).
            Scaling is applied in the y-direction in the rotated data frame
            (i.e., after adjusting for the anisotropy_angle, if anisotropy_angle
            is not 0).
        anisotropy_angle (float, optional): CCW angle (in degrees) by which to
            rotate coordinate system in order to take into account anisotropy.
            Default is 0 (no rotation). Note that the coordinate system is rotated.
        verbose (Boolean, optional): Enables program text output to monitor
            kriging process. Default is False (off).
        enable_plotting (Boolean, optional): Enables plotting to display
            variogram. Default is False (off).
        enable_statistics (Boolean, optional). Default is False

    Callable Methods:
        display_variogram_model(): Displays semivariogram and variogram model.

        update_variogram_model(variogram_model, variogram_parameters=None, nlags=6,
            anisotropy_scaling=1.0, anisotropy_angle=0.0):
            Changes the variogram model and variogram parameters for
            the kriging system.
            Inputs:
                variogram_model (string): May be any of the variogram models
                    listed above. May also be 'custom', in which case variogram_parameters
                    and variogram_function must be specified.
                variogram_parameters (list, optional): List of variogram model
                    parameters, as listed above. If not provided, a best fit model
                    will be calculated as described above.
                variogram_function (callable, optional): A callable function that must be
                    provided if variogram_model is specified as 'custom'. See above for
                    more information.
                nlags (int, optional): Number of averaging bins for the semivariogram.
                    Defualt is 6.
                weight (int, optional): If weight=1, semivariance at smaller lags
                    is weighted more heavily when automatically calculating variogram model.  The
                    weight is 1/lag.  If weight=2, then fit is weighted by the error in the estimate 
                    of the semivariogram.  If weight=3, the the old scheme of weighting by (n_bins-bin_number)
                    If weight=0, no weights will be applied.  Default is 0.
                anisotropy_scaling (float, optional): Scalar stretching value to
                    take into account anisotropy. Default is 1 (effectively no
                    stretching). Scaling is applied in the y-direction.
                anisotropy_angle (float, optional): CCW angle (in degrees) by which to
                    rotate coordinate system in order to take into account
                    anisotropy. Default is 0 (no rotation).

        switch_verbose(): Enables/disables program text output. No arguments.
        switch_plotting(): Enables/disable variogram plot display. No arguments.

        get_epsilon_residuals(): Returns the epsilon residuals of the
            variogram fit. No arguments.
        plot_epsilon_residuals(): Plots the epsilon residuals of the variogram
            fit in the order in which they were calculated. No arguments.

        get_statistics(): Returns the Q1, Q2, and cR statistics for the
            variogram fit (in that order). No arguments.

        print_statistics(): Prints out the Q1, Q2, and cR statistics for
            the variogram fit. NOTE that ideally Q1 is close to zero,
            Q2 is close to 1, and cR is as small as possible.

        execute(style, xpoints, ypoints, mask=None): Calculates a kriged grid.
            Inputs:
                style (string): Specifies how to treat input kriging points.
                    Specifying 'grid' treats xpoints and ypoints as two arrays of
                    x and y coordinates that define a rectangular grid.
                    Specifying 'points' treats xpoints and ypoints as two arrays
                    that provide coordinate pairs at which to solve the kriging system.
                    Specifying 'masked' treats xpoints and ypoints as two arrays of)
                    x and y coordinates that define a rectangular grid and uses mask
                    to only evaluate specific points in the grid.
                xpoints (array-like, dim Nx1): If style is specific as 'grid' or 'masked',
                    x-coordinates of MxN grid. If style is specified as 'points',
                    x-coordinates of specific points at which to solve kriging system.
                ypoints (array-like, dim Mx1): If style is specified as 'grid' or 'masked',
                    y-coordinates of MxN grid. If style is specified as 'points',
                    y-coordinates of specific points at which to solve kriging system.
                mask (boolean array, dim MxN, optional): Specifies the points in the rectangular
                    grid defined by xpoints and ypoints that are to be excluded in the
                    kriging calculations. Must be provided if style is specified as 'masked'.
                    False indicates that the point should not be masked; True indicates that
                    the point should be masked.
                backend (string, optional): Specifies which approach to use in kriging.
                    Specifying 'vectorized' will solve the entire kriging problem at once in a
                    vectorized operation. This approach is faster but also can consume a
                    significant amount of memory for large grids and/or large datasets.
                    Specifying 'loop' will loop through each point at which the kriging system
                    is to be solved. This approach is slower but also less memory-intensive.
                    Specifying 'C' will utilize a loop in Cython.
                    Default is 'vectorized'.
                n_closest_points (int, optional): For kriging with a moving window, specifies the number
                    of nearby points to use in the calculation. This can speed up the calculation for large
                    datasets, but should be used with caution. As Kitanidis notes, kriging with a moving
                    window can produce unexpected oddities if the variogram model is not carefully chosen.
            Outputs:
                zvalues (numpy array, dim MxN or dim Nx1): Z-values of specified grid or at the
                    specified set of points. If style was specified as 'masked', zvalues will
                    be a numpy masked array.
                sigmasq (numpy array, dim MxN or dim Nx1): Variance at specified grid points or
                    at the specified set of points. If style was specified as 'masked', sigmasq
                    will be a numpy masked array.

    References:
        P.K. Kitanidis, Introduction to Geostatistcs: Applications in Hydrogeology,
        (Cambridge University Press, 1997) 272 p.
    """

    eps = 1.e-10   # Cutoff for comparison to zero
    variogram_dict = {'linear': variogram_models.linear_variogram_model,
                      'power': variogram_models.power_variogram_model,
                      'gaussian': variogram_models.gaussian_variogram_model,
                      'spherical': variogram_models.spherical_variogram_model,
                      'exponential': variogram_models.exponential_variogram_model}

    def __init__(self, x, y, z, variogram_model='linear', variogram_parameters=None,
                 variogram_function=None, nlags=6, weight=0, anisotropy_scaling=1.0,
                 anisotropy_angle=0.0, verbose=False, enable_plotting=False,
                 enable_statistics=False, min_theta=None, max_theta=None):

        # Code assumes 1D input arrays. Ensures that any extraneous dimensions
        # don't get in the way. Copies are created to avoid any problems with
        # referencing the original passed arguments.
        self.X_ORIG = np.atleast_1d(np.squeeze(np.array(x, copy=True)))
        self.Y_ORIG = np.atleast_1d(np.squeeze(np.array(y, copy=True)))
        self.Z = np.atleast_1d(np.squeeze(np.array(z, copy=True)))

        self.verbose = verbose
        self.enable_plotting = enable_plotting
        if self.enable_plotting and self.verbose:
            print "Plotting Enabled\n"

        self.XCENTER = (np.amax(self.X_ORIG) + np.amin(self.X_ORIG))/2.0
        self.YCENTER = (np.amax(self.Y_ORIG) + np.amin(self.Y_ORIG))/2.0
        self.anisotropy_scaling = anisotropy_scaling
        self.anisotropy_angle = anisotropy_angle
        if self.verbose:
            print "Adjusting data for anisotropy..."
        self.X_ADJUSTED, self.Y_ADJUSTED = \
            core.adjust_for_anisotropy(np.copy(self.X_ORIG), np.copy(self.Y_ORIG),
                                       self.XCENTER, self.YCENTER,
                                       self.anisotropy_scaling, self.anisotropy_angle)

        self.variogram_model = variogram_model
        if self.variogram_model not in self.variogram_dict.keys() and self.variogram_model != 'custom':
            raise ValueError("Specified variogram model '%s' is not supported." % variogram_model)
        elif self.variogram_model == 'custom':
            if variogram_function is None or not callable(variogram_function):
                raise ValueError("Must specify callable function for custom variogram model.")
            else:
                self.variogram_function = variogram_function
        else:
            self.variogram_function = self.variogram_dict[self.variogram_model]
        if self.verbose:
            print "Initializing variogram model..."
        self.lags, self.semivariance, self.semivariance_error, self.variogram_model_parameters = \
            core.initialize_variogram_model(self.X_ADJUSTED, self.Y_ADJUSTED, self.Z,
                                            self.variogram_model, variogram_parameters,
                                            self.variogram_function, nlags, weight, min_theta, max_theta)
        if self.verbose:
            if self.variogram_model == 'linear':
                print "Using '%s' Variogram Model" % 'linear'
                print "Slope:", self.variogram_model_parameters[0]
                print "Nugget:", self.variogram_model_parameters[1], '\n'
            elif self.variogram_model == 'power':
                print "Using '%s' Variogram Model" % 'power'
                print "Scale:", self.variogram_model_parameters[0]
                print "Exponent:", self.variogram_model_parameters[1]
                print "Nugget:", self.variogram_model_parameters[2], '\n'
            elif self.variogram_model == 'custom':
                print "Using Custom Variogram Model"
            else:
                print "Using '%s' Variogram Model" % self.variogram_model
                print "Sill:", self.variogram_model_parameters[0]
                print "Range:", self.variogram_model_parameters[1]
                print "Nugget:", self.variogram_model_parameters[2], '\n'
        if self.enable_plotting:
            self.display_variogram_model()

        if enable_statistics:
            if self.verbose:
                print "Calculating statistics on variogram model fit..."
            self.delta, self.sigma, self.epsilon = core.find_statistics(self.X_ADJUSTED, self.Y_ADJUSTED,
                                                                        self.Z, self.variogram_function,
                                                                        self.variogram_model_parameters)
            self.Q1 = core.calcQ1(self.epsilon)
            self.Q2 = core.calcQ2(self.epsilon)
            self.cR = core.calc_cR(self.Q2, self.sigma)
            if self.verbose:
                print "Q1 =", self.Q1
                print "Q2 =", self.Q2
                print "cR =", self.cR, '\n'
        else:
            self.delta, self.sigma, self.epsilon, self.Q1, self.Q2, self.cR = [None]*6

    def update_variogram_model(self, variogram_model, variogram_parameters=None,
                               variogram_function=None, nlags=6, weight=False,
                               anisotropy_scaling=1.0, anisotropy_angle=0.0):
        """Allows user to update variogram type and/or variogram model parameters."""

        if anisotropy_scaling != self.anisotropy_scaling or \
           anisotropy_angle != self.anisotropy_angle:
            if self.verbose:
                print "Adjusting data for anisotropy..."
            self.anisotropy_scaling = anisotropy_scaling
            self.anisotropy_angle = anisotropy_angle
            self.X_ADJUSTED, self.Y_ADJUSTED = \
                core.adjust_for_anisotropy(np.copy(self.X_ORIG),
                                           np.copy(self.Y_ORIG),
                                           self.XCENTER, self.YCENTER,
                                           self.anisotropy_scaling,
                                           self.anisotropy_angle)

        self.variogram_model = variogram_model
        if self.variogram_model not in self.variogram_dict.keys() and self.variogram_model != 'custom':
            raise ValueError("Specified variogram model '%s' is not supported." % variogram_model)
        elif self.variogram_model == 'custom':
            if variogram_function is None or not callable(variogram_function):
                raise ValueError("Must specify callable function for custom variogram model.")
            else:
                self.variogram_function = variogram_function
        else:
            self.variogram_function = self.variogram_dict[self.variogram_model]
        if self.verbose:
            print "Updating variogram mode..."
        self.lags, self.semivariance, self.semivariance_error, self.variogram_model_parameters = \
            core.initialize_variogram_model(self.X_ADJUSTED, self.Y_ADJUSTED, self.Z,
                                            self.variogram_model, variogram_parameters,
                                            self.variogram_function, nlags, weight)
        if self.verbose:
            if self.variogram_model == 'linear':
                print "Using '%s' Variogram Model" % 'linear'
                print "Slope:", self.variogram_model_parameters[0]
                print "Nugget:", self.variogram_model_parameters[1], '\n'
            elif self.variogram_model == 'power':
                print "Using '%s' Variogram Model" % 'power'
                print "Scale:", self.variogram_model_parameters[0]
                print "Exponent:", self.variogram_model_parameters[1]
                print "Nugget:", self.variogram_model_parameters[2], '\n'
            elif self.variogram_model == 'custom':
                print "Using Custom Variogram Model"
            else:
                print "Using '%s' Variogram Model" % self.variogram_model
                print "Sill:", self.variogram_model_parameters[0]
                print "Range:", self.variogram_model_parameters[1]
                print "Nugget:", self.variogram_model_parameters[2], '\n'
        if self.enable_plotting:
            self.display_variogram_model()

        if self.verbose:
            print "Calculating statistics on variogram model fit..."
        self.delta, self.sigma, self.epsilon = core.find_statistics(self.X_ADJUSTED, self.Y_ADJUSTED,
                                                                    self.Z, self.variogram_function,
                                                                    self.variogram_model_parameters)
        self.Q1 = core.calcQ1(self.epsilon)
        self.Q2 = core.calcQ2(self.epsilon)
        self.cR = core.calc_cR(self.Q2, self.sigma)
        if self.verbose:
            print "Q1 =", self.Q1
            print "Q2 =", self.Q2
            print "cR =", self.cR, '\n'

    def display_variogram_model(self):
        """Displays variogram model with the actual binned data"""
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.errorbar(self.lags, self.semivariance, fmt='ro', yerr=self.semivariance_error, label='calculated')
        ax.plot(self.lags,
                self.variogram_function(self.variogram_model_parameters, self.lags), 'k-', label='fit')
        if self.variogram_model == 'linear':
            plt.title('Variogram(' + self.variogram_model + '): slope = ' + ('%.2f' % self.variogram_model_parameters[0]) + 
                            ', nugget = ' + ('%.2f' % self.variogram_model_parameters[1]) + '\nazimuth = ' + 
                            ('%.1f' % -self.anisotropy_angle) + ', scaling = ' +
                            ('%.1f' % self.anisotropy_scaling))
        elif self.variogram_model == 'power':
            plt.title('Variogram(' + self.variogram_model + '): scale = ' + ('%.3f' % self.variogram_model_parameters[0]) + 
                            ', nugget = ' + ('%.2f' % self.variogram_model_parameters[2]) + '\nazimuth = ' + 
                            ('%.1f' % -self.anisotropy_angle) + ', exponent = ' + 
                            ('%.3f' % self.variogram_model_parameters[1]) + ', scaling = ' +
                            ('%.1f' % self.anisotropy_scaling))
        elif self.variogram_model == 'custom':
            plt.title('Variogram(' + self.variogram_model + '):\n' + 
                            '\nazimuth = ' + ('%.1f' % -self.anisotropy_angle) + ', scaling = ' + 
                            ('%.1f' % self.anisotropy_scaling))
        else:
            plt.title('Variogram(' + self.variogram_model + '): sill = ' + ('%.2f' % self.variogram_model_parameters[0]) + 
                            ', nugget = ' + ('%.2f' % self.variogram_model_parameters[2]) + '\nazimuth = ' + 
                            ('%.1f' % -self.anisotropy_angle) + ', range-X = ' + 
                            ('%.1f' % self.variogram_model_parameters[1]) + ', range-Y = ' +
                            ('%.1f' % (self.variogram_model_parameters[1] / self.anisotropy_scaling)))
        plt.xlabel('lag (distance)')
        plt.ylabel('variance (distance^2)')
        plt.legend(loc='best')
        plt.show()

    def switch_verbose(self):
        """Allows user to switch code talk-back on/off. Takes no arguments."""
        self.verbose = not self.verbose

    def switch_plotting(self):
        """Allows user to switch plot display on/off. Takes no arguments."""
        self.enable_plotting = not self.enable_plotting

    def get_epsilon_residuals(self):
        """Returns the epsilon residuals for the variogram fit."""
        return self.epsilon

    def plot_epsilon_residuals(self):
        """Plots the epsilon residuals for the variogram fit."""
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.scatter(range(self.epsilon.size), self.epsilon, c='k', marker='*')
        ax.axhline(y=0.0)
        plt.show()

    def get_statistics(self):
        return self.Q1, self.Q2, self.cR

    def print_statistics(self):
        print "Q1 =", self.Q1
        print "Q2 =", self.Q2
        print "cR =", self.cR

    def _get_kriging_matrix(self, n):
        """Assembles the kriging matrix."""

        xy = np.concatenate((self.X_ADJUSTED[:, np.newaxis], self.Y_ADJUSTED[:, np.newaxis]), axis=1)
        d = cdist(xy, xy, 'euclidean')
        a = np.zeros((n, n))
        a[:,:] = self.variogram_model_parameters[0] - self.variogram_function(self.variogram_model_parameters, d)

        return a

    def _exec_vector(self, a, bd, mask):
        """Solves the kriging system as a vectorized operation. This method
        can take a lot of memory for large grids and/or large datasets."""

        npt = bd.shape[0]
        n = self.X_ADJUSTED.shape[0]
        #zero_index = None
        #zero_value = False

        a_inv = scipy.linalg.inv(a)

        b = np.zeros((npt, n, 1))
        b[:, :, 0] = self.variogram_model_parameters[0] - self.variogram_function(self.variogram_model_parameters, bd)

        if (~mask).any():
            mask_b = np.repeat(mask[:, np.newaxis, np.newaxis], n, axis=1)
            b = np.ma.array(b, mask=mask_b)

        x = np.dot(a_inv, b.reshape((npt, n)).T).reshape((1, n, npt)).T
        zvalues = np.sum(x[:, :, 0] * self.Z, axis=1)
        sigmasq = self.variogram_model_parameters[0] - np.sum(x[:, :, 0] * b[:, :, 0], axis=1)

        return zvalues, sigmasq

    def _exec_loop(self, a, bd_all, mask):
        """Solves the kriging system by looping over all specified points.
        Less memory-intensive, but involves a Python-level loop."""

        npt = bd_all.shape[0]
        n = self.X_ADJUSTED.shape[0]
        zvalues = np.zeros(npt)
        sigmasq = np.zeros(npt)

        a_inv = scipy.linalg.inv(a)

        for j in np.nonzero(~mask)[0]:   # Note that this is the same thing as range(npt) if mask is not defined,
            bd = bd_all[j]               # otherwise it takes the non-masked elements.

            b = np.zeros((n, 1))
            b[:, 0] = self.variogram_model_parameters[0] -  self.variogram_function(self.variogram_model_parameters, bd)
            x = np.dot(a_inv, b)
            zvalues[j] = np.sum(x[:, 0] * self.Z)
            sigmasq[j] = self.variogram_model_parameters[0] - np.sum(x[:, 0] * b[:, 0])

        return zvalues, sigmasq

    def _exec_loop_moving_window(self, a_all, bd_all, mask, bd_idx):
        """Solves the kriging system by looping over all specified points.
        Less memory-intensive, but involves a Python-level loop."""
        import scipy.linalg.lapack

        npt = bd_all.shape[0]
        n = bd_idx.shape[1]
        zvalues = np.zeros(npt)
        sigmasq = np.zeros(npt)

        for i in np.nonzero(~mask)[0]:   # Note that this is the same thing as range(npt) if mask is not defined,
            b_selector = bd_idx[i]       # otherwise it takes the non-masked elements.
            bd = bd_all[i]

            a_selector = np.concatenate((b_selector, np.array([a_all.shape[0] - 1])))
            a = a_all[a_selector[:, None], a_selector]

            b = np.zeros((n, 1))
            b[:, 0] = self.variogram_model_parameters[0] -  self.variogram_function(self.variogram_model_parameters, bd)

            x = scipy.linalg.solve(a, b)

            zvalues[i] = x[:, 0].dot(self.Z[b_selector])
            sigmasq[i] = self.variogram_model_parameters[0] -  x[:, 0].dot(b[:, 0])

        return zvalues, sigmasq

    def execute(self, style, xpoints, ypoints, mask=None, backend='vectorized', n_closest_points=None):
        """Calculates a kriged grid and the associated variance.

        This is now the method that performs the main kriging calculation. Note that currently
        measurements (i.e., z values) are considered 'exact'. This means that, when a specified
        coordinate for interpolation is exactly the same as one of the data points, the variogram
        evaluated at the point is forced to be zero. Also, the diagonal of the kriging matrix is
        also always forced to be zero. In forcing the variogram evaluated at data points to be zero,
        we are effectively saying that there is no variance at that point (no uncertainty,
        so the value is 'exact').

        In the future, the code may include an extra 'exact_values' boolean flag that can be
        adjusted to specify whether to treat the measurements as 'exact'. Setting the flag
        to false would indicate that the variogram should not be forced to be zero at zero distance
        (i.e., when evaluated at data points). Instead, the uncertainty in the point will be
        equal to the nugget. This would mean that the diagonal of the kriging matrix would be set to
        the nugget instead of to zero.

        Inputs:
            style (string): Specifies how to treat input kriging points.
                Specifying 'grid' treats xpoints and ypoints as two arrays of
                x and y coordinates that define a rectangular grid.
                Specifying 'points' treats xpoints and ypoints as two arrays
                that provide coordinate pairs at which to solve the kriging system.
                Specifying 'masked' treats xpoints and ypoints as two arrays of
                x and y coordinates that define a rectangular grid and uses mask
                to only evaluate specific points in the grid.
            xpoints (array-like, dim N): If style is specific as 'grid' or 'masked',
                x-coordinates of MxN grid. If style is specified as 'points',
                x-coordinates of specific points at which to solve kriging system.
            ypoints (array-like, dim M): If style is specified as 'grid' or 'masked',
                y-coordinates of MxN grid. If style is specified as 'points',
                y-coordinates of specific points at which to solve kriging system.
                Note that in this case, xpoints and ypoints must have the same dimensions
                (i.e., M = N).
            mask (boolean array, dim MxN, optional): Specifies the points in the rectangular
                grid defined by xpoints and ypoints that are to be excluded in the
                kriging calculations. Must be provided if style is specified as 'masked'.
                False indicates that the point should not be masked, so the kriging system
                will be solved at the point.
                True indicates that the point should be masked, so the kriging system should
                will not be solved at the point.
            backend (string, optional): Specifies which approach to use in kriging.
                Specifying 'vectorized' will solve the entire kriging problem at once in a
                vectorized operation. This approach is faster but also can consume a
                significant amount of memory for large grids and/or large datasets.
                Specifying 'loop' will loop through each point at which the kriging system
                is to be solved. This approach is slower but also less memory-intensive.
                Specifying 'C' will utilize a loop in Cython.
                Default is 'vectorized'.
            n_closest_points (int, optional): For kriging with a moving window, specifies the number
                of nearby points to use in the calculation. This can speed up the calculation for large
                datasets, but should be used with caution. As Kitanidis notes, kriging with a moving
                window can produce unexpected oddities if the variogram model is not carefully chosen.
        Outputs:
            zvalues (numpy array, dim MxN or dim Nx1): Z-values of specified grid or at the
                specified set of points. If style was specified as 'masked', zvalues will
                be a numpy masked array.
            sigmasq (numpy array, dim MxN or dim Nx1): Variance at specified grid points or
                at the specified set of points. If style was specified as 'masked', sigmasq
                will be a numpy masked array.
        """

        if self.verbose:
            print "Executing Simple Kriging...\n"

        if self.variogram_model == 'linear' or self.variogram_model == 'power':
            raise ValueError("for simple kriging variogram must have well behaved correlation")

        if style != 'grid' and style != 'masked' and style != 'points':
            raise ValueError("style argument must be 'grid', 'points', or 'masked'")

        xpts = np.atleast_1d(np.squeeze(np.array(xpoints, copy=True)))
        ypts = np.atleast_1d(np.squeeze(np.array(ypoints, copy=True)))
        n = self.X_ADJUSTED.shape[0]
        nx = xpts.size
        ny = ypts.size
        a = self._get_kriging_matrix(n)

        if style in ['grid', 'masked']:
            if style == 'masked':
                if mask is None:
                    raise IOError("Must specify boolean masking array when style is 'masked'.")
                if mask.shape[0] != ny or mask.shape[1] != nx:
                    if mask.shape[0] == nx and mask.shape[1] == ny:
                        mask = mask.T
                    else:
                        raise ValueError("Mask dimensions do not match specified grid dimensions.")
                mask = mask.flatten()
            npt = ny*nx
            grid_x, grid_y = np.meshgrid(xpts, ypts)
            xpts = grid_x.flatten()
            ypts = grid_y.flatten()

        elif style == 'points':
            if xpts.size != ypts.size:
                raise ValueError("xpoints and ypoints must have same dimensions "
                                 "when treated as listing discrete points.")
            npt = nx
        else:
            raise ValueError("style argument must be 'grid', 'points', or 'masked'")

        xpts, ypts = core.adjust_for_anisotropy(xpts, ypts, self.XCENTER, self.YCENTER,
                                                self.anisotropy_scaling, self.anisotropy_angle)

        if style != 'masked':
            mask = np.zeros(npt, dtype='bool')

        xy_points = np.concatenate((xpts[:, np.newaxis], ypts[:, np.newaxis]), axis=1)
        xy_data = np.concatenate((self.X_ADJUSTED[:, np.newaxis], self.Y_ADJUSTED[:, np.newaxis]), axis=1)

        c_pars = None
#        if backend == 'C':
#            try:
#                from .lib.cok import _c_exec_loop, _c_exec_loop_moving_window
#            except ImportError:
#                print('Warning: failed to load Cython extensions.\n'\
#                      '   See https://github.com/bsmurphy/PyKrige/issues/8 \n'\
#                      '   Falling back to a pure python backend...')
#                backend = 'loop'
#            except:
#                raise RuntimeError("Unknown error in trying to load Cython extension.")
#
#            c_pars = {key: getattr(self, key) for key in ['Z', 'eps', 'variogram_model_parameters',
#                                                          'variogram_function']}

        if n_closest_points is not None:
            from scipy.spatial import cKDTree
            tree = cKDTree(xy_data)
            bd, bd_idx = tree.query(xy_points, k=n_closest_points, eps=0.0)

            if backend == 'loop':
                zvalues, sigmasq = self._exec_loop_moving_window(a, bd, mask, bd_idx)
            #elif backend == 'C':
            #    zvalues, sigmasq = _c_exec_loop_moving_window(a, bd, mask.astype('int8'),
            #                                                  bd_idx, self.X_ADJUSTED.shape[0], c_pars)
            else:
                raise ValueError('Specified backend {} for a moving window is not supported.'.format(backend))
        else:
            bd = cdist(xy_points,  xy_data, 'euclidean')
            if backend == 'vectorized':
                zvalues, sigmasq = self._exec_vector(a, bd, mask)
            elif backend == 'loop':
                zvalues, sigmasq = self._exec_loop(a, bd, mask)
            #elif backend == 'C':
            #    zvalues, sigmasq = _c_exec_loop(a, bd, mask.astype('int8'), self.X_ADJUSTED.shape[0],  c_pars)
            else:
                raise ValueError('Specified backend {} is not supported for 2D ordinary kriging.'.format(backend))

        if style == 'masked':
            zvalues = np.ma.array(zvalues, mask=mask)
            sigmasq = np.ma.array(sigmasq, mask=mask)

        if style in ['masked', 'grid']:
            zvalues = zvalues.reshape((ny, nx))
            sigmasq = sigmasq.reshape((ny, nx))

        return zvalues, sigmasq
