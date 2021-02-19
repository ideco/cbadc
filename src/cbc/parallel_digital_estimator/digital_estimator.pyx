# distutils: language = c++
from cbc.digital_estimator.offline_computations import care
from scipy.linalg import expm, solve
from scipy.integrate import solve_ivp
from numpy import dot as dot_product, eye, zeros, int8, double, roll, array
from numpy.linalg import eig, inv
from cbc.parallel_digital_estimator.c_digital_estimator import C_Digital_Estimator

class DigitalEstimator(C_Digital_Estimator):

    def __init__(self, controlSignalSequence, analogSystem, digitalControl, eta2, K1, K2 = 0, stop_after_number_of_iterations = 0):
        # Check inputs
        if (stop_after_number_of_iterations < 0):
            raise "stop_after_number_of_iterations must be non negative"
        self._size = stop_after_number_of_iterations
        if (K1 < 1):
            raise "K1 must be a positive integer"
        if (K2 < 0):
            raise "K2 must be a non negative integer"
        self._s = controlSignalSequence
        super().__init__(analogSystem, digitalControl, eta2, K1, K2)

    def __iter__(self):
        return self
    
    def __next__(self):
        if(self._size and self._size < self._iteration ):
            raise StopIteration
        if (not self.empty()):
            return self.output()
        while(not self.full()):
           self.input(next(self._s))
        self.compute_batch()
        return self.__next__()

    def number_of_controls(self):
        return self._filter.number_of_controls()

    def number_of_states(self):
        return self._filter.number_of_states()

    def number_of_inputs(self):
        return self._filter.number_of_inputs()